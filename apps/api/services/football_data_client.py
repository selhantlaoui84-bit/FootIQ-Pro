import logging
import os
import re
import unicodedata
from datetime import date, timedelta
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("footiq.football_data")

BASE_URL = "https://api.football-data.org/v4"
TIMEOUT_SECONDS = 8

COMPETITION_LABELS = {
    "FL1": "Ligue 1",
    "PL": "Premier League",
    "PD": "Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "DED": "Eredivisie",
    "PPL": "Liga Portugal",
    "CL": "Ligue des champions",
    "WC": "Coupe du monde",
}


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


def _winner_from_score(winner, home_score, away_score):
    if winner:
        return winner
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return "HOME_TEAM"
    if away_score > home_score:
        return "AWAY_TEAM"
    return "DRAW"


def normalize_match(raw_match, competition_label):
    home_team_name = raw_match.get("homeTeam", {}).get("name") or raw_match.get("homeTeam", {}).get("shortName") or "Home"
    away_team_name = raw_match.get("awayTeam", {}).get("name") or raw_match.get("awayTeam", {}).get("shortName") or "Away"
    slug = f"{slugify(home_team_name)}-{slugify(away_team_name)}"
    score = raw_match.get("score") if isinstance(raw_match.get("score"), dict) else {}
    full_time = score.get("fullTime") if isinstance(score, dict) else {}
    half_time = score.get("halfTime") if isinstance(score, dict) else {}
    raw_status = raw_match.get("status", "SCHEDULED")
    status = str(raw_status or "SCHEDULED").upper()
    full_time_home = _score_value(full_time, "home")
    full_time_away = _score_value(full_time, "away")
    winner = _winner_from_score(score.get("winner") if isinstance(score, dict) else None, full_time_home, full_time_away)

    return {
        "id": slug,
        "match_id": slug,
        "slug": slug,
        "home_team": home_team_name,
        "away_team": away_team_name,
        "competition": competition_label,
        "kickoff": raw_match.get("utcDate"),
        "status": status,
        "raw_status": raw_status,
        "source": "football-data.org",
        "score": score,
        "score_full_time_home": full_time_home,
        "score_full_time_away": full_time_away,
        "score_half_time_home": _score_value(half_time, "home"),
        "score_half_time_away": _score_value(half_time, "away"),
        "winner": winner,
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
    today = date.today()
    params = urlencode({
        "dateFrom": (today - timedelta(days=365)).isoformat(),
        "dateTo": (today + timedelta(days=30)).isoformat(),
    })
    data = get_json(f"/competitions/{competition_code}/matches?{params}")
    if not data:
        return []

    return [normalize_match(match, competition_label) for match in data.get("matches", [])]


def _get_teams(competition_code: str, competition_label: str):
    data = get_json(f"/competitions/{competition_code}/teams")
    if not data:
        return []

    return [normalize_team(team, competition_label) for team in data.get("teams", [])]


def configured_competition_codes():
    raw = os.getenv("FOOTIQ_COMPETITIONS", "FL1,CL")
    codes = []
    for item in raw.split(","):
        code = item.strip().upper()
        if code and code not in codes:
            codes.append(code)
    return codes or ["FL1", "CL"]


def competition_label(code: str):
    return COMPETITION_LABELS.get(code.upper(), code.upper())


def get_configured_competitions_data():
    matches = []
    teams = []
    warnings = []

    for code in configured_competition_codes():
        label = competition_label(code)
        competition_matches = _get_matches(code, label)
        competition_teams = _get_teams(code, label)
        if not competition_matches and not competition_teams:
            warnings.append(f"{label}: aucune donnée récupérée ou compétition non disponible avec le plan actuel.")
            continue
        matches.extend(competition_matches)
        teams.extend(competition_teams)

    return {
        "matches": _deduplicate(matches),
        "teams": _deduplicate(teams),
        "competitions": configured_competition_codes(),
        "competition_labels": [competition_label(code) for code in configured_competition_codes()],
        "warnings": warnings,
    }


def _deduplicate(items):
    deduped = {}
    for item in items:
        key = item.get("id") or item.get("match_id") or item.get("slug") or item.get("name")
        if key:
            deduped[key] = item
    return list(deduped.values())


def get_ligue1_matches():
    return _get_matches("FL1", "Ligue 1")


def get_champions_league_matches():
    return _get_matches("CL", "Champions League")


def get_ligue1_teams():
    return _get_teams("FL1", "Ligue 1")


def get_champions_league_teams():
    return _get_teams("CL", "Champions League")
