STRONG_TEAMS = {
    "arsenal",
    "barcelona",
    "bayern",
    "bayern munich",
    "inter",
    "inter milan",
    "liverpool",
    "manchester city",
    "psg",
    "paris saint-germain",
    "real madrid",
}


def slugify(value: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "unknown"


def match_slug(home_team: str, away_team: str) -> str:
    return f"{slugify(home_team)}-{slugify(away_team)}"


def calculate_status(confidence_score: int) -> str:
    if confidence_score >= 75:
        return "FIABLE"
    if confidence_score >= 55:
        return "MOYEN"
    return "À ÉVITER"


def detect_trap_match(probabilities: dict, confidence_score: int) -> bool:
    favorite_probability = max(probabilities.get("home", 0), probabilities.get("draw", 0), probabilities.get("away", 0))
    return favorite_probability >= 55 and confidence_score < 55


def _is_strong(team_name: str) -> bool:
    normalized = team_name.strip().lower()
    return any(strong_team in normalized for strong_team in STRONG_TEAMS)


def _recommendation(confidence_score: int) -> str:
    if confidence_score >= 75:
        return "Exploitable"
    if confidence_score >= 55:
        return "Prudence"
    return "À éviter"


def _goals_from_probabilities(probabilities: dict) -> dict:
    home_edge = probabilities["home"] - probabilities["away"]
    expected_home = round(1.35 + max(home_edge, 0) / 35, 1)
    expected_away = round(1.2 + max(-home_edge, 0) / 42, 1)
    favorite_probability = max(probabilities.values())

    return {
        "expected_home": expected_home,
        "expected_away": expected_away,
        "over_2_5": min(64, 42 + int(favorite_probability / 4)),
        "btts": min(62, 45 + int((100 - abs(home_edge)) / 8)),
    }


def generate_prediction_from_match(match: dict) -> dict:
    home_team = match.get("home_team", "")
    away_team = match.get("away_team", "")
    slug = match.get("slug") or match.get("match_id") or match_slug(home_team, away_team)
    home_strong = _is_strong(home_team)
    away_strong = _is_strong(away_team)

    if home_strong and not away_strong:
        probabilities = {"home": 62, "draw": 23, "away": 15}
        confidence_score = 76
        main_prediction = f"{home_team} avantage domicile"
        explanation = [
            "Equipe a forte reference statistique face a une opposition moins dominante",
            "Le contexte domicile augmente la lisibilite du scenario",
            "La probabilite reste une estimation, pas une certitude",
        ]
    elif away_strong and not home_strong:
        probabilities = {"home": 22, "draw": 25, "away": 53}
        confidence_score = 68
        main_prediction = f"{away_team} avantage leger"
        explanation = [
            "L'equipe exterieure presente un niveau de reference superieur",
            "Le facteur domicile adverse reduit la confiance globale",
            "Le scenario reste sensible au rythme du match",
        ]
    elif home_strong and away_strong:
        probabilities = {"home": 40, "draw": 27, "away": 33}
        confidence_score = 58
        main_prediction = "Match de haut niveau, avantage limite"
        explanation = [
            "Deux equipes fortes reduisent la clarte du signal principal",
            "Le volume offensif attendu reste eleve",
            "La marge entre les issues reste moderee",
        ]
    else:
        probabilities = {"home": 42, "draw": 28, "away": 30}
        confidence_score = 52
        main_prediction = "Match equilibre, prudence recommandee"
        explanation = [
            "Les signaux disponibles ne degagent pas de favori net",
            "Le nul conserve une probabilite significative",
            "La confiance reste limitee sans donnees contextuelles avancees",
        ]

    goals = _goals_from_probabilities(probabilities)
    status = calculate_status(confidence_score)
    trap_match = detect_trap_match(probabilities, confidence_score)

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
        "probabilities": probabilities,
        "goals": goals,
        "confidence": {"score": confidence_score, "status": status},
        "flags": {"trap_match": trap_match, "risk": confidence_score < 55},
        "recommendation": _recommendation(confidence_score),
        "main_prediction": main_prediction,
        "explanation": explanation,
        "risks": [
            "Donnees de composition non integrees",
            "Calendrier et fatigue a surveiller",
            "Probabilite de nul a ne pas negliger",
        ],
        "disclaimer": "Modele probabiliste. Aucune garantie de resultat.",
    }


def generate_mock_prediction(match: dict) -> dict:
    confidence_score = int(match["confidence_score"])
    probabilities = match["probabilities"]
    slug = match.get("slug") or match.get("match_id") or match_slug(match["home_team"], match["away_team"])

    return {
        "id": slug,
        "match_id": slug,
        "slug": slug,
        "home_team": match["home_team"],
        "away_team": match["away_team"],
        "competition": match["competition"],
        "kickoff": match["kickoff"],
        "status": match.get("status", "SCHEDULED"),
        "source": match.get("source", "mock"),
        "probabilities": probabilities,
        "goals": match["goals"],
        "confidence": {"score": confidence_score, "status": calculate_status(confidence_score)},
        "flags": {"trap_match": detect_trap_match(probabilities, confidence_score), "risk": confidence_score < 55},
        "recommendation": match["recommendation"],
        "main_prediction": match["main_prediction"],
        "explanation": match["explanation"],
        "risks": match["risks"],
        "disclaimer": "Modele probabiliste. Aucune garantie de resultat.",
    }
