def _team_names(match: dict) -> tuple[str, str]:
    return match.get("home_team", ""), match.get("away_team", "")


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


def _finished(match: dict) -> bool:
    home_score, away_score = _score(match)
    return match.get("status") in {"FINISHED", "AWARDED"} and home_score is not None and away_score is not None


def _recent_matches(team: str, all_matches: list[dict], limit: int = 5) -> list[dict]:
    items = [
        match
        for match in all_matches
        if _finished(match) and (match.get("home_team") == team or match.get("away_team") == team)
    ]
    return items[-limit:]


def _form_score(team: str, all_matches: list[dict]) -> float:
    recent = _recent_matches(team, all_matches)
    if not recent:
        return 0.5

    points = 0
    for match in recent:
        home_score, away_score = _score(match)
        is_home = match.get("home_team") == team
        team_score = home_score if is_home else away_score
        opponent_score = away_score if is_home else home_score

        if team_score > opponent_score:
            points += 3
        elif team_score == opponent_score:
            points += 1

    return round(points / (len(recent) * 3), 3)


def _goals_average(team: str, all_matches: list[dict], against: bool) -> float:
    recent = _recent_matches(team, all_matches)
    if not recent:
        return 1.25 if against else 1.35

    goals = []
    for match in recent:
        home_score, away_score = _score(match)
        is_home = match.get("home_team") == team
        if against:
            goals.append(away_score if is_home else home_score)
        else:
            goals.append(home_score if is_home else away_score)

    return round(sum(goals) / len(goals), 2) if goals else (1.25 if against else 1.35)


def build_match_features(match: dict, all_matches: list[dict]) -> dict:
    home_team, away_team = _team_names(match)
    home_form = _form_score(home_team, all_matches)
    away_form = _form_score(away_team, all_matches)
    home_for = _goals_average(home_team, all_matches, against=False)
    away_for = _goals_average(away_team, all_matches, against=False)
    home_against = _goals_average(home_team, all_matches, against=True)
    away_against = _goals_average(away_team, all_matches, against=True)
    finished_count = len([item for item in all_matches if _finished(item)])
    attack_delta = round(home_for - away_for, 2)
    defense_delta = round(away_against - home_against, 2)
    form_delta = round(home_form - away_form, 3)
    balance = abs(form_delta) + abs(attack_delta) / 3 + abs(defense_delta) / 3
    draw_risk = max(0.15, min(0.8, 0.58 - balance / 2))
    data_quality = max(0.35, min(1.0, finished_count / 20))

    return {
        "home_team": home_team,
        "away_team": away_team,
        "competition": match.get("competition", "Football"),
        "home_advantage": 1.0,
        "home_recent_form_score": home_form,
        "away_recent_form_score": away_form,
        "form_delta": form_delta,
        "home_goals_for_avg": home_for,
        "away_goals_for_avg": away_for,
        "home_goals_against_avg": home_against,
        "away_goals_against_avg": away_against,
        "attack_delta": attack_delta,
        "defense_delta": defense_delta,
        "draw_risk_score": round(draw_risk, 3),
        "data_quality_score": round(data_quality, 3),
    }
