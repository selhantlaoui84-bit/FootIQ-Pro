from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware


# =========================
# LOGGING (PROD SAFE)
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("footiq.api")


# =========================
# SETTINGS (SAFE DEFAULTS)
# =========================
def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("ENV", "production")
    debug: bool = _env_bool("DEBUG")
    database_url: str | None = os.getenv("DATABASE_URL")
    redis_url: str | None = os.getenv("REDIS_URL")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")


settings = Settings()


# =========================
# LIFESPAN SAFE STARTUP
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FootIQ API...")
    yield
    logger.info("Stopping FootIQ API...")


# =========================
# APP INIT (SINGLE SOURCE)
# =========================
app = FastAPI(
    debug=settings.debug,
    lifespan=lifespan
)


# =========================
# CORS (PRODUCTION SAFE)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # safe for MVP + Vercel
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# ROUTES
# =========================
@app.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "FootIQ Pro API"
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# =========================
# REQUEST LOGGER MIDDLEWARE
# =========================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()

    response: Response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response