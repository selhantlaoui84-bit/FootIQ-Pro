from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

import httpx

BASE_URL = "https://api.football-data.org/v4"


def _api_key() -> str | None:
    value = os.getenv("FOOTBALL_DATA_API_KEY")
    if not value:
        return None
    value = value.strip()
    return value or None


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def get_json(path: str) -> dict[str, Any] | None:
    key = _api_key()
    if not key:
        return None

    try:
        response = httpx.get(
            f"{BASE_URL}{path}",
            headers={"X-Auth-Token": key},
            timeout=8.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def normalize_match(raw_match: dict[str, Any], competition_label: str) -> dict[str, Any] | None:
    home = raw_match.get("homeTeam", {}).get("name")
    away = raw_match.get("awayTeam", {}).get("name")
    kickoff = raw_match.get("utcDate")
    status = raw_match.get("status", "SCHEDULED")

    if not home or not away:
        return None

    slug = f"{slugify(home)}-{slugify(away)}"

    return {
        "id": slug,
        "match_id": slug,
        "slug": slug,
        "home_team": home,
        "away_team": away,
        "competition": competition_label,
        "kickoff": kickoff,
        "status": status,
        "source": "football-data.org",
    }


def normalize_team(raw_team: dict[str, Any], competition_label: str) -> dict[str, Any] | None:
    name = raw_team.get("name")
    if not name:
        return None

    slug = slugify(name)

    return {
        "id": slug,
        "slug": slug,
        "name": name,
        "competition": competition_label,
        "source": "football-data.org",
    }


def get_competition_matches(code: str, competition_label: str) -> list[dict[str, Any]]:
    data = get_json(f"/competitions/{code}/matches")
    if not data:
        return []

    results: list[dict[str, Any]] = []

    for raw_match in data.get("matches", []):
        match = normalize_match(raw_match, competition_label)
        if match:
            results.append(match)

    return results


def get_competition_teams(code: str, competition_label: str) -> list[dict[str, Any]]:
    data = get_json(f"/competitions/{code}/teams")
    if not data:
        return []

    results: list[dict[str, Any]] = []

    for raw_team in data.get("teams", []):
        team = normalize_team(raw_team, competition_label)
        if team:
            results.append(team)

    return results


def get_ligue1_matches() -> list[dict[str, Any]]:
    return get_competition_matches("FL1", "Ligue 1")


def get_champions_league_matches() -> list[dict[str, Any]]:
    return get_competition_matches("CL", "Champions League")


def get_ligue1_teams() -> list[dict[str, Any]]:
    return get_competition_teams("FL1", "Ligue 1")


def get_champions_league_teams() -> list[dict[str, Any]]:
    return get_competition_teams("CL", "Champions League")
