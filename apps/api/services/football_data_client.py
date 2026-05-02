import logging
import os
import re
import unicodedata

import httpx

logger = logging.getLogger("footiq.football_data")

BASE_URL = "https://api.football-data.org/v4"
TIMEOUT_SECONDS = 8


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "unknown"


def get_json(path: str):
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        return None

    try:
        response = httpx.get(
            f"{BASE_URL}{path}",
            headers={"X-Auth-Token": api_key, "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        if "application/json" not in response.headers.get("content-type", ""):
            logger.warning("football-data.org returned non-JSON response")
            return None

        return response.json()
    except Exception as exc:
        logger.warning("football-data.org request failed: %s", exc)
        return None


def _score_value(score_part, key):
    if not isinstance(score_part, dict):
        return None
    return score_part.get(key)


def normalize_match(raw_match, competition_label):
    home_team_name = raw_match.get("homeTeam", {}).get("name") or raw_match.get("homeTeam", {}).get("shortName") or "Home"
    away_team_name = raw_match.get("awayTeam", {}).get("name") or raw_match.get("awayTeam", {}).get("shortName") or "Away"
    slug = f"{slugify(home_team_name)}-{slugify(away_team_name)}"
    score = raw_match.get("score") if isinstance(raw_match.get("score"), dict) else {}
    full_time = score.get("fullTime") if isinstance(score, dict) else {}
    half_time = score.get("halfTime") if isinstance(score, dict) else {}

    return {
        "id": slug,
        "match_id": slug,
        "slug": slug,
        "home_team": home_team_name,
        "away_team": away_team_name,
        "competition": competition_label,
        "kickoff": raw_match.get("utcDate"),
        "status": raw_match.get("status", "SCHEDULED"),
        "source": "football-data.org",
        "score": score,
        "score_full_time_home": _score_value(full_time, "home"),
        "score_full_time_away": _score_value(full_time, "away"),
        "score_half_time_home": _score_value(half_time, "home"),
        "score_half_time_away": _score_value(half_time, "away"),
        "winner": score.get("winner") if isinstance(score, dict) else None,
        "raw_json": raw_match,
    }


def normalize_team(raw_team, competition_label):
    team_name = raw_team.get("name") or raw_team.get("shortName") or "Unknown"
    slug = slugify(team_name)

    return {
        "id": slug,
        "slug": slug,
        "name": team_name,
        "competition": competition_label,
        "source": "football-data.org",
    }


def _get_matches(competition_code: str, competition_label: str):
    data = get_json(f"/competitions/{competition_code}/matches")
    if not data:
        return []

    return [normalize_match(match, competition_label) for match in data.get("matches", [])]


def _get_teams(competition_code: str, competition_label: str):
    data = get_json(f"/competitions/{competition_code}/teams")
    if not data:
        return []

    return [normalize_team(team, competition_label) for team in data.get("teams", [])]


def get_ligue1_matches():
    return _get_matches("FL1", "Ligue 1")


def get_champions_league_matches():
    return _get_matches("CL", "Champions League")


def get_ligue1_teams():
    return _get_teams("FL1", "Ligue 1")


def get_champions_league_teams():
    return _get_teams("CL", "Champions League")

