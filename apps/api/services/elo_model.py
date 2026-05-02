import math


def _score(match: dict) -> tuple[int | None, int | None]:
    score = match.get("score") or {}
    full_time = score.get("fullTime") if isinstance(score, dict) else None
    if isinstance(full_time, dict):
        home = full_time.get("home")
        away = full_time.get("away")
        if isinstance(home, int) and isinstance(away, int):
            return home, away

    home = match.get("home_score")
    away = match.get("away_score")
    if isinstance(home, int) and isinstance(away, int):
        return home, away

    return None, None


def _is_finished(match: dict) -> bool:
    home_score, away_score = _score(match)
    return match.get("status") in {"FINISHED", "AWARDED"} and home_score is not None and away_score is not None


def _expected(home_rating: float, away_rating: float) -> float:
    return 1 / (1 + math.pow(10, (away_rating - home_rating) / 400))


def calculate_team_elos(matches: list[dict]) -> dict:
    ratings: dict[str, float] = {}

    for match in matches:
        home = match.get("home_team")
        away = match.get("away_team")
        if home:
            ratings.setdefault(home, 1500.0)
        if away:
            ratings.setdefault(away, 1500.0)

    for match in matches:
        if not _is_finished(match):
            continue

        home = match.get("home_team")
        away = match.get("away_team")
        if not home or not away:
            continue

        home_score, away_score = _score(match)
        home_rating = ratings.get(home, 1500.0)
        away_rating = ratings.get(away, 1500.0)
        expected_home = _expected(home_rating + 60, away_rating)
        actual_home = 1.0 if home_score > away_score else 0.5 if home_score == away_score else 0.0
        delta = 24 * (actual_home - expected_home)
        ratings[home] = home_rating + delta
        ratings[away] = away_rating - delta

    return {team: round(rating) for team, rating in ratings.items()}


def get_elo_features(home_team: str, away_team: str, elo_ratings: dict) -> dict:
    home_elo = int(elo_ratings.get(home_team, 1500))
    away_elo = int(elo_ratings.get(away_team, 1500))
    elo_delta = home_elo + 60 - away_elo
    home_win_probability = 1 / (1 + math.pow(10, -elo_delta / 400))

    return {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "elo_delta": round(elo_delta),
        "elo_home_win_probability": round(home_win_probability, 3),
    }
