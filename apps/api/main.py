from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
except ImportError as exc:
    raise RuntimeError("FastAPI not installed. Run: python -m pip install -r requirements.txt") from exc

from redis.asyncio import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("footiq.api")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("ENV", "development")
    debug: bool = _env_bool("DEBUG")
    database_url: str | None = os.getenv("DATABASE_URL")
    redis_url: str | None = os.getenv("REDIS_URL")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    cache_ttl_seconds: int = _env_int("CACHE_TTL_SECONDS", 300, minimum=300, maximum=900)
    external_timeout_seconds: float = _env_float("EXTERNAL_TIMEOUT_SECONDS", 5)


settings = Settings()

if settings.env not in {"development", "staging", "production", "test"}:
    raise RuntimeError("ENV must be one of: development, staging, production, test")


async def run_with_timeout(
    operation: Callable[[], Awaitable[Any]],
    fallback: Any = None,
    timeout: float | None = None,
) -> Any:
    try:
        return await asyncio.wait_for(operation(), timeout or settings.external_timeout_seconds)
    except Exception:
        logger.exception("External operation failed")
        return fallback


def _prediction_cache_key(request: Request) -> str | None:
    match_id = request.path_params.get("match_id") or request.query_params.get("match_id")
    if match_id is None:
        match = re.search(r"/(?:predictions?|matches)/([^/?#]+)", request.url.path.lower())
        if match:
            match_id = match.group(1)
    if match_id is None:
        return None
    return f"prediction:{match_id}"


def _is_prediction_request(request: Request) -> bool:
    return request.method == "GET" and "prediction" in request.url.path.lower()


async def _check_database() -> None:
    if not settings.database_url:
        logger.warning("DATABASE_URL is not configured; skipping DB startup check")
        return

    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        logger.info("Database startup check passed")
    except SQLAlchemyError as exc:
        logger.exception("Database startup check failed")
        raise RuntimeError("Database unavailable") from exc


async def _connect_redis() -> Redis | None:
    if not settings.redis_url:
        logger.warning("REDIS_URL is not configured; Redis cache disabled")
        return None

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
        logger.info("Redis startup check passed")
        return redis
    except Exception as exc:
        await redis.close()
        logger.exception("Redis startup check failed")
        raise RuntimeError("Redis unavailable") from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _check_database()
    app.state.redis = await _connect_redis()
    try:
        yield
    finally:
        redis: Redis | None = getattr(app.state, "redis", None)
        if redis is not None:
            await redis.close()


app = FastAPI(debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_and_prediction_cache(request: Request, call_next):
    start = time.perf_counter()
    cache_key = _prediction_cache_key(request) if _is_prediction_request(request) else None
    redis: Redis | None = getattr(request.app.state, "redis", None)

    if redis is not None and cache_key is not None:
        cached = await redis.get(cache_key)
        if cached is not None:
            logger.info("cache_hit method=%s path=%s key=%s", request.method, request.url.path, cache_key)
            return Response(content=cached, media_type="application/json")

    try:
        response: Response = await call_next(request)
    except Exception:
        logger.exception("request_error method=%s path=%s", request.method, request.url.path)
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    if redis is not None and cache_key is not None and response.status_code == 200:
        body = b"".join([chunk async for chunk in response.body_iterator])
        await redis.set(cache_key, body.decode("utf-8"), ex=settings.cache_ttl_seconds)
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
