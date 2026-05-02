from services.calibration import calibrate_probabilities, derive_calibration_profile
from services.elo_model import calculate_team_elos, get_elo_features
from services.feature_engineering import build_match_features
from services.poisson_model import build_score_matrix, calculate_goal_probabilities

MODEL_VERSION = "elo-poisson-calibrated-v1"


def slugify(value: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "unknown"


def match_slug(home_team: str, away_team: str) -> str:
    return f"{slugify(home_team)}-{slugify(away_team)}"


def calculate_status(confidence_score: int) -> str:
    if confidence_score >= 78:
        return "FIABLE"
    if confidence_score >= 55:
        return "MOYEN"
    return "A EVITER"


def detect_trap_match(probabilities: dict, confidence_score: int) -> bool:
    favorite_probability = max(probabilities.get("home", 0), probabilities.get("draw", 0), probabilities.get("away", 0))
    return favorite_probability >= 55 and confidence_score < 60


def _normalize_probabilities(home: float, draw: float, away: float) -> dict:
    values = [max(1, home), max(1, draw), max(1, away)]
    total = sum(values)
    home_pct = round(values[0] / total * 100)
    draw_pct = round(values[1] / total * 100)
    away_pct = 100 - home_pct - draw_pct
    return {"home": home_pct, "draw": draw_pct, "away": away_pct}


def _result_probabilities_from_poisson(home_lambda: float, away_lambda: float) -> dict:
    matrix = build_score_matrix(home_lambda, away_lambda)
    flat = [cell for row in matrix for cell in row]
    home = sum(cell["probability"] for cell in flat if cell["home_goals"] > cell["away_goals"])
    draw = sum(cell["probability"] for cell in flat if cell["home_goals"] == cell["away_goals"])
    away = sum(cell["probability"] for cell in flat if cell["home_goals"] < cell["away_goals"])
    return _normalize_probabilities(home * 100, draw * 100, away * 100)


def _blend_probabilities(elo_home_probability: float, poisson_probabilities: dict, features: dict) -> dict:
    elo_home = elo_home_probability * 100
    elo_away = (1 - elo_home_probability) * 100
    elo_draw = 24 + features["draw_risk_score"] * 16
    feature_home_boost = features["form_delta"] * 12 + features["attack_delta"] * 4 + features["defense_delta"] * 4
    home = poisson_probabilities["home"] * 0.55 + elo_home * 0.35 + feature_home_boost
    draw = poisson_probabilities["draw"] * 0.7 + elo_draw * 0.3
    away = poisson_probabilities["away"] * 0.55 + elo_away * 0.35 - feature_home_boost
    return _normalize_probabilities(home, draw, away)


def _lambdas(features: dict, elo_features: dict) -> tuple[float, float]:
    elo_delta = elo_features["elo_delta"]
    home_lambda = 1.35 + features["attack_delta"] * 0.18 + features["defense_delta"] * 0.2 + elo_delta / 900
    away_lambda = 1.15 - features["defense_delta"] * 0.16 - features["form_delta"] * 0.22 - elo_delta / 1100
    return max(0.45, min(3.2, home_lambda)), max(0.35, min(3.0, away_lambda))


def _confidence(probabilities: dict, features: dict, confidence_penalty: int = 0) -> int:
    sorted_probs = sorted(probabilities.values(), reverse=True)
    spread = sorted_probs[0] - sorted_probs[1]
    score = 43 + spread * 0.62 + features["data_quality_score"] * 16 - features["draw_risk_score"] * 17 - confidence_penalty
    if probabilities["draw"] >= 30:
        score -= 5
    return max(32, min(84, round(score)))


def _risk_scores(probabilities: dict, confidence_score: int, features: dict) -> tuple[int, int]:
    favorite = max(probabilities.values())
    risk = 100 - confidence_score + round(features["draw_risk_score"] * 20) + (8 if probabilities["draw"] >= 30 else 0)
    trap = max(0, round((favorite - 50) * 1.8 + (60 - confidence_score) + features["draw_risk_score"] * 20))
    return max(0, min(100, risk)), max(0, min(100, trap))


def _recommendation(confidence_score: int, risk_score: int) -> str:
    if confidence_score >= 78 and risk_score < 42:
        return "Exploitable"
    if confidence_score >= 55 and risk_score < 65:
        return "Prudence"
    return "A eviter"


def _main_prediction(home_team: str, away_team: str, probabilities: dict) -> str:
    winner = max(probabilities, key=probabilities.get)
    if winner == "home":
        return f"{home_team} pr?sente l'avantage probabiliste principal"
    if winner == "away":
        return f"{away_team} pr?sente l'avantage probabiliste principal"
    return "Le nul ressort comme un sc?nario significatif"


def _explanation(features: dict, elo_features: dict, probabilities: dict, goals: dict) -> list[str]:
    items = []
    if abs(elo_features["elo_delta"]) >= 80:
        leader = "domicile" if elo_features["elo_delta"] > 0 else "ext?rieur"
        items.append(f"L'?cart Elo donne un avantage mesur? au camp {leader}.")
    else:
        items.append("Les ratings Elo restent proches, ce qui limite la certitude du signal.")

    if abs(features["form_delta"]) >= 0.15:
        side = "domicile" if features["form_delta"] > 0 else "ext?rieur"
        items.append(f"La dynamique r?cente penche l?g?rement c?t? {side}.")
    else:
        items.append("La forme r?cente ne cr?e pas de rupture nette entre les ?quipes.")

    items.append(f"Le mod?le Poisson projette un score le plus probable de {goals['most_likely_score']}.")
    if probabilities["draw"] >= 30:
        items.append("La probabilit? de nul reste ?lev?e, ce qui r?duit la lisibilit?.")
    return items[:4]


def _risks(features: dict, probabilities: dict, risk_score: int) -> list[str]:
    risks = []
    if features["data_quality_score"] < 0.55:
        risks.append("Historique exploitable limit?: prudence sur la calibration.")
    if probabilities["draw"] >= 30:
        risks.append("Nul statistiquement significatif.")
    if risk_score >= 65:
        risks.append("Score de risque ?lev? malgr? le favori apparent.")
    risks.append("Compositions, blessures et contexte de calendrier non int?gr?s.")
    return risks


def generate_prediction_from_match(match: dict, all_matches: list[dict] | None = None, elo_ratings: dict | None = None) -> dict:
    all_matches = all_matches or [match]
    home_team = match.get("home_team", "")
    away_team = match.get("away_team", "")
    slug = match.get("slug") or match.get("match_id") or match_slug(home_team, away_team)
    features = build_match_features(match, all_matches)
    elo_ratings = elo_ratings or calculate_team_elos(all_matches)
    elo_features = get_elo_features(home_team, away_team, elo_ratings)
    home_lambda, away_lambda = _lambdas(features, elo_features)
    goals = calculate_goal_probabilities(home_lambda, away_lambda)
    poisson_probabilities = _result_probabilities_from_poisson(home_lambda, away_lambda)
    raw_probabilities = _blend_probabilities(elo_features["elo_home_win_probability"], poisson_probabilities, features)
    calibration_profile = derive_calibration_profile(None)
    probabilities = calibrate_probabilities(raw_probabilities, calibration_profile)
    confidence_score = _confidence(probabilities, features, calibration_profile["confidence_penalty"])
    risk_score, trap_match_score = _risk_scores(probabilities, confidence_score, features)
    trap_match = detect_trap_match(probabilities, confidence_score) or trap_match_score >= 65

    return {
        "id": slug,
        "match_id": slug,
        "slug": slug,
        "home_team": home_team,
        "away_team": away_team,
        "competition": match.get("competition", "Football"),
        "kickoff": match.get("kickoff"),
        "status": match.get("status", "SCHEDULED"),
        "source": match.get("source", "mock"),
        "model_version": MODEL_VERSION,
        "probabilities": probabilities,
        "calibration": {
            "applied": True,
            "method": "conservative_probability_smoothing",
            "overconfidence_factor": calibration_profile["overconfidence_factor"],
            "draw_adjustment": calibration_profile["draw_adjustment"],
            "confidence_penalty": calibration_profile["confidence_penalty"],
        },
        "goals": goals,
        "confidence": {"score": confidence_score, "status": calculate_status(confidence_score)},
        "features": {
            "elo_delta": elo_features["elo_delta"],
            "form_delta": features["form_delta"],
            "attack_delta": features["attack_delta"],
            "defense_delta": features["defense_delta"],
            "draw_risk_score": features["draw_risk_score"],
            "data_quality_score": features["data_quality_score"],
        },
        "flags": {"trap_match": trap_match, "risk": risk_score >= 65 or confidence_score < 55},
        "risk_score": risk_score,
        "trap_match_score": trap_match_score,
        "recommendation": _recommendation(confidence_score, risk_score),
        "main_prediction": _main_prediction(home_team, away_team, probabilities),
        "explanation": _explanation(features, elo_features, probabilities, goals),
        "risks": _risks(features, probabilities, risk_score),
        "disclaimer": "Mod?le probabilistique. Aucune garantie de r?sultat.",
    }


def generate_mock_prediction(match: dict) -> dict:
    return generate_prediction_from_match({**match, "source": match.get("source", "mock")}, [match])
