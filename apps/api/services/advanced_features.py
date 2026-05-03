from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


FEATURE_SET_VERSION = "pre-match-advanced-v1"

ADVANCED_FEATURE_COLUMNS = [
    "home_recent_points_per_match",
    "away_recent_points_per_match",
    "form_points_delta",
    "home_recent_goals_for_avg",
    "away_recent_goals_for_avg",
    "attack_recent_delta",
    "home_recent_goals_against_avg",
    "away_recent_goals_against_avg",
    "defense_recent_delta",
    "home_recent_win_rate",
    "away_recent_win_rate",
    "win_rate_delta",
    "home_recent_unbeaten_rate",
    "away_recent_unbeaten_rate",
    "unbeaten_rate_delta",
    "home_recent_matches_count",
    "away_recent_matches_count",
    "home_recent_home_points_avg",
    "home_recent_home_goals_for_avg",
    "home_recent_home_goals_against_avg",
    "away_recent_away_points_avg",
    "away_recent_away_goals_for_avg",
    "away_recent_away_goals_against_avg",
    "home_rest_days",
    "away_rest_days",
    "rest_days_delta",
    "home_matches_last_7d",
    "home_matches_last_14d",
    "home_matches_last_21d",
    "away_matches_last_7d",
    "away_matches_last_14d",
    "away_matches_last_21d",
    "schedule_density_delta_14d",
    "home_win_streak",
    "home_unbeaten_streak",
    "home_loss_streak",
    "away_win_streak",
    "away_unbeaten_streak",
    "away_loss_streak",
]


def parse_kickoff(match: dict[str, Any]) -> datetime | None:
    value = match.get("kickoff") or match.get("utcDate")
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _match_key(match: dict[str, Any]) -> str | None:
    value = match.get("match_id") or match.get("id") or match.get("slug")
    return str(value) if value else None


def is_finished_before(candidate_match: dict[str, Any], target_match: dict[str, Any]) -> bool:
    if str(candidate_match.get("status", "")).upper() != "FINISHED":
        return False
    candidate_kickoff = parse_kickoff(candidate_match)
    target_kickoff = parse_kickoff(target_match)
    if candidate_kickoff is None or target_kickoff is None:
        return False
    return candidate_kickoff < target_kickoff


def _team_in_match(team_name: str, match: dict[str, Any], home_away: str | None = None) -> bool:
    home_team = str(match.get("home_team") or "")
    away_team = str(match.get("away_team") or "")
    if home_away == "home":
        return home_team == team_name
    if home_away == "away":
        return away_team == team_name
    return home_team == team_name or away_team == team_name


def team_recent_matches(
    team_name: str,
    target_match: dict[str, Any],
    all_matches: list[dict[str, Any]],
    limit: int = 5,
    home_away: str | None = None,
) -> list[dict[str, Any]]:
    target_key = _match_key(target_match)
    rows = [
        match
        for match in all_matches or []
        if _match_key(match) != target_key
        and _team_in_match(team_name, match, home_away=home_away)
        and is_finished_before(match, target_match)
        and extract_score(match) is not None
    ]
    return sorted(rows, key=lambda item: parse_kickoff(item) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:limit]


def extract_score(match: dict[str, Any]) -> tuple[int, int] | None:
    try:
        home = match.get("score_full_time_home")
        away = match.get("score_full_time_away")
        if home is None or away is None:
            score = match.get("score") or {}
            full_time = score.get("fullTime") if isinstance(score, dict) else {}
            if isinstance(full_time, dict):
                home = full_time.get("home")
                away = full_time.get("away")
        if home is None or away is None:
            return None
        return int(home), int(away)
    except (TypeError, ValueError):
        return None


def _team_result(team_name: str, match: dict[str, Any]) -> tuple[int, int, int, int] | None:
    score = extract_score(match)
    if score is None:
        return None
    home_goals, away_goals = score
    is_home = str(match.get("home_team") or "") == team_name
    goals_for = home_goals if is_home else away_goals
    goals_against = away_goals if is_home else home_goals
    points = 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0
    return points, goals_for, goals_against, goals_for - goals_against


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0


def calculate_team_form_features(team_name: str, target_match: dict[str, Any], all_matches: list[dict[str, Any]]) -> dict[str, Any]:
    recent = team_recent_matches(team_name, target_match, all_matches, limit=5)
    results = [_team_result(team_name, match) for match in recent]
    rows = [item for item in results if item is not None]
    count = len(rows)
    if count == 0:
        return {
            "recent_points_per_match": 0,
            "recent_goals_for_avg": 0,
            "recent_goals_against_avg": 0,
            "recent_goal_diff_avg": 0,
            "recent_win_rate": 0,
            "recent_unbeaten_rate": 0,
            "recent_matches_count": 0,
        }
    return {
        "recent_points_per_match": _avg([item[0] for item in rows]),
        "recent_goals_for_avg": _avg([item[1] for item in rows]),
        "recent_goals_against_avg": _avg([item[2] for item in rows]),
        "recent_goal_diff_avg": _avg([item[3] for item in rows]),
        "recent_win_rate": round(sum(1 for item in rows if item[0] == 3) / count * 100),
        "recent_unbeaten_rate": round(sum(1 for item in rows if item[0] >= 1) / count * 100),
        "recent_matches_count": count,
    }


def _venue_metrics(team_name: str, target_match: dict[str, Any], all_matches: list[dict[str, Any]], venue: str) -> dict[str, Any]:
    recent = team_recent_matches(team_name, target_match, all_matches, limit=5, home_away=venue)
    rows = [_team_result(team_name, match) for match in recent]
    valid = [item for item in rows if item is not None]
    return {
        "points_avg": _avg([item[0] for item in valid]),
        "goals_for_avg": _avg([item[1] for item in valid]),
        "goals_against_avg": _avg([item[2] for item in valid]),
    }


def calculate_home_away_features(home_team: str, away_team: str, target_match: dict[str, Any], all_matches: list[dict[str, Any]]) -> dict[str, Any]:
    home = _venue_metrics(home_team, target_match, all_matches, "home")
    away = _venue_metrics(away_team, target_match, all_matches, "away")
    return {
        "home_recent_home_points_avg": home["points_avg"],
        "home_recent_home_goals_for_avg": home["goals_for_avg"],
        "home_recent_home_goals_against_avg": home["goals_against_avg"],
        "away_recent_away_points_avg": away["points_avg"],
        "away_recent_away_goals_for_avg": away["goals_for_avg"],
        "away_recent_away_goals_against_avg": away["goals_against_avg"],
    }


def calculate_rest_features(home_team: str, away_team: str, target_match: dict[str, Any], all_matches: list[dict[str, Any]]) -> dict[str, Any]:
    target_kickoff = parse_kickoff(target_match)
    if target_kickoff is None:
        return {"home_rest_days": None, "away_rest_days": None, "rest_days_delta": 0}

    def rest_days(team: str) -> int | None:
        recent = team_recent_matches(team, target_match, all_matches, limit=1)
        if not recent:
            return None
        kickoff = parse_kickoff(recent[0])
        if kickoff is None:
            return None
        return max(0, int((target_kickoff - kickoff).total_seconds() // 86400))

    home_rest = rest_days(home_team)
    away_rest = rest_days(away_team)
    return {
        "home_rest_days": home_rest,
        "away_rest_days": away_rest,
        "rest_days_delta": (home_rest or 0) - (away_rest or 0),
    }


def calculate_schedule_density_features(home_team: str, away_team: str, target_match: dict[str, Any], all_matches: list[dict[str, Any]]) -> dict[str, Any]:
    target_kickoff = parse_kickoff(target_match)
    if target_kickoff is None:
        return {
            "home_matches_last_7d": 0,
            "home_matches_last_14d": 0,
            "home_matches_last_21d": 0,
            "away_matches_last_7d": 0,
            "away_matches_last_14d": 0,
            "away_matches_last_21d": 0,
            "schedule_density_delta_14d": 0,
        }

    def count_recent(team: str, days: int) -> int:
        rows = team_recent_matches(team, target_match, all_matches, limit=50)
        return sum(
            1
            for match in rows
            if (kickoff := parse_kickoff(match)) is not None
            and 0 <= (target_kickoff - kickoff).total_seconds() <= days * 86400
        )

    home_14 = count_recent(home_team, 14)
    away_14 = count_recent(away_team, 14)
    return {
        "home_matches_last_7d": count_recent(home_team, 7),
        "home_matches_last_14d": home_14,
        "home_matches_last_21d": count_recent(home_team, 21),
        "away_matches_last_7d": count_recent(away_team, 7),
        "away_matches_last_14d": away_14,
        "away_matches_last_21d": count_recent(away_team, 21),
        "schedule_density_delta_14d": home_14 - away_14,
    }


def _streak(team_name: str, target_match: dict[str, Any], all_matches: list[dict[str, Any]], kind: str) -> int:
    count = 0
    for match in team_recent_matches(team_name, target_match, all_matches, limit=20):
        result = _team_result(team_name, match)
        if result is None:
            break
        points = result[0]
        if kind == "win" and points == 3:
            count += 1
        elif kind == "unbeaten" and points >= 1:
            count += 1
        elif kind == "loss" and points == 0:
            count += 1
        else:
            break
    return count


def calculate_streak_features(home_team: str, away_team: str, target_match: dict[str, Any], all_matches: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "home_win_streak": _streak(home_team, target_match, all_matches, "win"),
        "home_unbeaten_streak": _streak(home_team, target_match, all_matches, "unbeaten"),
        "home_loss_streak": _streak(home_team, target_match, all_matches, "loss"),
        "away_win_streak": _streak(away_team, target_match, all_matches, "win"),
        "away_unbeaten_streak": _streak(away_team, target_match, all_matches, "unbeaten"),
        "away_loss_streak": _streak(away_team, target_match, all_matches, "loss"),
    }


def build_advanced_pre_match_features(match: dict[str, Any], all_matches: list[dict[str, Any]]) -> dict[str, Any]:
    home_team = str(match.get("home_team") or "")
    away_team = str(match.get("away_team") or "")
    home_form = calculate_team_form_features(home_team, match, all_matches)
    away_form = calculate_team_form_features(away_team, match, all_matches)
    features = {
        "home_recent_points_per_match": home_form["recent_points_per_match"],
        "away_recent_points_per_match": away_form["recent_points_per_match"],
        "form_points_delta": round(home_form["recent_points_per_match"] - away_form["recent_points_per_match"], 3),
        "home_recent_goals_for_avg": home_form["recent_goals_for_avg"],
        "away_recent_goals_for_avg": away_form["recent_goals_for_avg"],
        "attack_recent_delta": round(home_form["recent_goals_for_avg"] - away_form["recent_goals_for_avg"], 3),
        "home_recent_goals_against_avg": home_form["recent_goals_against_avg"],
        "away_recent_goals_against_avg": away_form["recent_goals_against_avg"],
        "defense_recent_delta": round(away_form["recent_goals_against_avg"] - home_form["recent_goals_against_avg"], 3),
        "home_recent_win_rate": home_form["recent_win_rate"],
        "away_recent_win_rate": away_form["recent_win_rate"],
        "win_rate_delta": home_form["recent_win_rate"] - away_form["recent_win_rate"],
        "home_recent_unbeaten_rate": home_form["recent_unbeaten_rate"],
        "away_recent_unbeaten_rate": away_form["recent_unbeaten_rate"],
        "unbeaten_rate_delta": home_form["recent_unbeaten_rate"] - away_form["recent_unbeaten_rate"],
        "home_recent_matches_count": home_form["recent_matches_count"],
        "away_recent_matches_count": away_form["recent_matches_count"],
    }
    features.update(calculate_home_away_features(home_team, away_team, match, all_matches))
    features.update(calculate_rest_features(home_team, away_team, match, all_matches))
    features.update(calculate_schedule_density_features(home_team, away_team, match, all_matches))
    features.update(calculate_streak_features(home_team, away_team, match, all_matches))
    return {name: features.get(name, 0) for name in ADVANCED_FEATURE_COLUMNS}
