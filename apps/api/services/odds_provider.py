from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from services.odds_engine import implied_probability_from_odds, normalize_decimal_odds


def is_odds_configured() -> bool:
    return bool(os.getenv("ODDS_PROVIDER") and os.getenv("ODDS_API_KEY") and os.getenv("ODDS_BASE_URL"))


def _config() -> dict[str, Any]:
    return {
        "provider": os.getenv("ODDS_PROVIDER"),
        "api_key": os.getenv("ODDS_API_KEY"),
        "base_url": (os.getenv("ODDS_BASE_URL") or "").rstrip("/"),
        "region": os.getenv("ODDS_REGION") or "eu",
        "markets": os.getenv("ODDS_MARKETS") or "h2h",
        "bookmakers": os.getenv("ODDS_BOOKMAKERS"),
        "ttl": int(os.getenv("ODDS_CACHE_TTL_SECONDS") or "1800"),
    }


def validate_real_odds_payload(raw: Any) -> bool:
    if not raw:
        return False
    if isinstance(raw, list):
        return True
    if isinstance(raw, dict):
        return bool(raw.get("data") or raw.get("events") or raw.get("bookmakers"))
    return False


def map_provider_team_to_internal_team(provider_team_name: str | None) -> str | None:
    return provider_team_name.strip() if isinstance(provider_team_name, str) and provider_team_name.strip() else None


def map_provider_market_to_internal_market(provider_market: str | None) -> str:
    value = str(provider_market or "").lower()
    if value in {"h2h", "1x2", "winner"}:
        return "1X2"
    if value in {"totals", "over_under"}:
        return "over_under"
    if value in {"btts", "both_teams_to_score"}:
        return "btts"
    return provider_market or "unknown"


def _selection_from_outcome(name: str, event: dict[str, Any], market_key: str) -> str | None:
    clean = str(name or "").strip()
    if not clean:
        return None
    home = str(event.get("home_team") or event.get("homeTeam") or "").strip().lower()
    away = str(event.get("away_team") or event.get("awayTeam") or "").strip().lower()
    lowered = clean.lower()
    if market_key == "1X2":
        if lowered in {"draw", "x", "nul"}:
            return "DRAW"
        if home and lowered == home:
            return "HOME_WIN"
        if away and lowered == away:
            return "AWAY_WIN"
    return clean.upper().replace(" ", "_")


def normalize_provider_odds(raw: Any) -> list[dict[str, Any]]:
    if not validate_real_odds_payload(raw):
        return []
    cfg = _config()
    events = raw if isinstance(raw, list) else raw.get("data") or raw.get("events") or [raw]
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=cfg["ttl"])
    normalized: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        match_id = str(event.get("match_id") or event.get("id") or event.get("event_id") or event.get("commence_time") or "")
        bookmakers = event.get("bookmakers") or []
        for bookmaker in bookmakers:
            if not isinstance(bookmaker, dict):
                continue
            bookmaker_name = bookmaker.get("title") or bookmaker.get("key") or bookmaker.get("bookmaker") or "bookmaker"
            for market in bookmaker.get("markets") or []:
                if not isinstance(market, dict):
                    continue
                market_name = map_provider_market_to_internal_market(market.get("key") or market.get("market"))
                provider_market_id = market.get("key") or market.get("id")
                for outcome in market.get("outcomes") or []:
                    if not isinstance(outcome, dict):
                        continue
                    decimal = normalize_decimal_odds(outcome.get("price") or outcome.get("odds") or outcome.get("decimal"))
                    selection = _selection_from_outcome(outcome.get("name") or outcome.get("selection"), event, market_name)
                    if not match_id or not selection or decimal is None:
                        continue
                    normalized.append(
                        {
                            "match_id": match_id,
                            "bookmaker": bookmaker_name,
                            "market": market_name,
                            "selection": selection,
                            "odds_decimal": decimal,
                            "implied_probability": implied_probability_from_odds(decimal),
                            "provider": cfg["provider"],
                            "provider_event_id": str(event.get("id") or event.get("event_id") or match_id),
                            "provider_market_id": provider_market_id,
                            "raw_json": {"event": event, "bookmaker": bookmaker, "market": market, "outcome": outcome},
                            "collected_at": now.isoformat(),
                            "expires_at": expires_at.isoformat(),
                            "stale": False,
                            "source": "real_provider",
                        }
                    )
    return normalized


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_real_odds_for_matches(match_ids: list[str]) -> dict[str, Any]:
    if not is_odds_configured():
        return {"status": "missing_provider_config", "items": [], "detail": "ODDS provider is not configured."}
    cfg = _config()
    params = {
        "apiKey": cfg["api_key"],
        "regions": cfg["region"],
        "markets": cfg["markets"],
    }
    if cfg["bookmakers"]:
        params["bookmakers"] = cfg["bookmakers"]
    if match_ids:
        params["eventIds"] = ",".join(str(item) for item in match_ids)
    url = f"{cfg['base_url']}?{urllib.parse.urlencode(params)}"
    raw = _fetch_json(url)
    return {"status": "ok", "items": normalize_provider_odds(raw), "raw": raw}


def fetch_real_odds_for_match(match_id: str) -> dict[str, Any]:
    return fetch_real_odds_for_matches([match_id])
