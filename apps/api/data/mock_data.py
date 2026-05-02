from services.prediction_engine import generate_mock_prediction

BASE_MATCHES = [
    {
        "id": "psg-lyon",
        "match_id": "psg-lyon",
        "slug": "psg-lyon",
        "home_team": "PSG",
        "away_team": "Lyon",
        "competition": "Ligue 1",
        "kickoff": "2026-05-05T20:00:00Z",
        "probabilities": {"home": 61, "draw": 23, "away": 16},
        "goals": {"expected_home": 2.1, "expected_away": 1.2, "over_2_5": 58, "btts": 54},
        "confidence_score": 78,
        "recommendation": "Exploitable",
        "main_prediction": "PSG ou nul avec avantage domicile",
        "explanation": [
            "Superiorite offensive nette a domicile",
            "Lyon concede davantage d'occasions a l'exterieur",
            "Les signaux recents sont coherents",
        ],
        "risks": ["Rotation possible", "Fatigue europeenne moderee"],
    },
    {
        "id": "marseille-rennes",
        "match_id": "marseille-rennes",
        "slug": "marseille-rennes",
        "home_team": "Marseille",
        "away_team": "Rennes",
        "competition": "Ligue 1",
        "kickoff": "2026-05-06T18:45:00Z",
        "probabilities": {"home": 43, "draw": 29, "away": 28},
        "goals": {"expected_home": 1.5, "expected_away": 1.2, "over_2_5": 46, "btts": 57},
        "confidence_score": 54,
        "recommendation": "Prudence",
        "main_prediction": "Match serre, nul fortement plausible",
        "explanation": [
            "Ecart de niveau faible sur les dernieres semaines",
            "Rennes reste dangereux en transition",
            "Probabilite de nul elevee, lisibilite reduite",
        ],
        "risks": ["Forme recente irreguliere", "Pression du contexte", "High draw probability"],
    },
    {
        "id": "real-madrid-arsenal",
        "match_id": "real-madrid-arsenal",
        "slug": "real-madrid-arsenal",
        "home_team": "Real Madrid",
        "away_team": "Arsenal",
        "competition": "Champions League",
        "kickoff": "2026-05-07T20:00:00Z",
        "probabilities": {"home": 44, "draw": 27, "away": 29},
        "goals": {"expected_home": 1.8, "expected_away": 1.5, "over_2_5": 61, "btts": 62},
        "confidence_score": 64,
        "recommendation": "Prudence",
        "main_prediction": "Real Madrid avantage leger, match ouvert",
        "explanation": [
            "Deux attaques capables de creer un volume eleve",
            "Arsenal conserve une forte capacite de pressing",
            "La marge entre les issues reste moderee",
        ],
        "risks": ["Qualite individuelle adverse", "Transitions rapides", "BTTS eleve"],
    },
    {
        "id": "lille-monaco",
        "match_id": "lille-monaco",
        "slug": "lille-monaco",
        "home_team": "Lille",
        "away_team": "Monaco",
        "competition": "Ligue 1",
        "kickoff": "2026-05-08T19:00:00Z",
        "probabilities": {"home": 36, "draw": 31, "away": 33},
        "goals": {"expected_home": 1.2, "expected_away": 1.3, "over_2_5": 44, "btts": 55},
        "confidence_score": 48,
        "recommendation": "À éviter",
        "main_prediction": "Aucune direction claire",
        "explanation": [
            "Probabilites tres proches entre les trois issues",
            "Deux blocs capables de neutraliser le rythme",
            "Donnees recentes contradictoires, confiance reduite",
        ],
        "risks": ["Inconsistent recent form", "High draw probability", "Faible volume d'occasions"],
    },
    {
        "id": "lens-nice",
        "match_id": "lens-nice",
        "slug": "lens-nice",
        "home_team": "Lens",
        "away_team": "Nice",
        "competition": "Ligue 1",
        "kickoff": "2026-05-09T17:00:00Z",
        "probabilities": {"home": 41, "draw": 30, "away": 29},
        "goals": {"expected_home": 1.4, "expected_away": 1.2, "over_2_5": 43, "btts": 52},
        "confidence_score": 56,
        "recommendation": "Prudence",
        "main_prediction": "Lens leger avantage domicile",
        "explanation": [
            "Lens garde un petit avantage territorial a domicile",
            "Nice limite bien les occasions concedees",
            "Le nul reste un scenario significatif",
        ],
        "risks": ["Efficacite offensive variable", "High draw probability", "Rythme potentiellement ferme"],
    },
]

MATCHES = [generate_mock_prediction(match) for match in BASE_MATCHES]

TEAMS = [
    {"id": "psg", "slug": "psg", "name": "PSG", "competition": "Ligue 1", "elo": 1884, "form": "V V N V V", "goals_for": 72, "goals_against": 29, "trend": "rising", "source": "mock"},
    {"id": "marseille", "slug": "marseille", "name": "Marseille", "competition": "Ligue 1", "elo": 1712, "form": "V N D V N", "goals_for": 54, "goals_against": 41, "trend": "stable", "source": "mock"},
    {"id": "lyon", "slug": "lyon", "name": "Lyon", "competition": "Ligue 1", "elo": 1668, "form": "D V V N D", "goals_for": 49, "goals_against": 46, "trend": "stable", "source": "mock"},
    {"id": "monaco", "slug": "monaco", "name": "Monaco", "competition": "Ligue 1", "elo": 1761, "form": "V V D V N", "goals_for": 61, "goals_against": 39, "trend": "rising", "source": "mock"},
    {"id": "lille", "slug": "lille", "name": "Lille", "competition": "Ligue 1", "elo": 1739, "form": "N V V N D", "goals_for": 52, "goals_against": 34, "trend": "stable", "source": "mock"},
    {"id": "lens", "slug": "lens", "name": "Lens", "competition": "Ligue 1", "elo": 1695, "form": "V D N V D", "goals_for": 47, "goals_against": 38, "trend": "declining", "source": "mock"},
    {"id": "rennes", "slug": "rennes", "name": "Rennes", "competition": "Ligue 1", "elo": 1644, "form": "D N V D N", "goals_for": 43, "goals_against": 44, "trend": "declining", "source": "mock"},
    {"id": "nice", "slug": "nice", "name": "Nice", "competition": "Ligue 1", "elo": 1688, "form": "N V N D V", "goals_for": 39, "goals_against": 31, "trend": "stable", "source": "mock"},
    {"id": "arsenal", "slug": "arsenal", "name": "Arsenal", "competition": "Champions League", "elo": 1859, "form": "V V V N V", "goals_for": 68, "goals_against": 28, "trend": "rising", "source": "mock"},
    {"id": "real-madrid", "slug": "real-madrid", "name": "Real Madrid", "competition": "Champions League", "elo": 1917, "form": "V N V V V", "goals_for": 74, "goals_against": 32, "trend": "rising", "source": "mock"},
]

PERFORMANCE = {
    "tracked": 1248,
    "highConfidenceHitRate": "64%",
    "averageConfidence": "68",
    "calibration": "Stable",
    "brierScore": "0.184",
    "modelVersion": "FootIQ-Pro v0.5",
    "lastUpdated": "2026-05-02T08:00:00Z",
}


def get_match(match_id: str):
    return next(
        (match for match in MATCHES if match["id"] == match_id or match["match_id"] == match_id or match["slug"] == match_id),
        None,
    )


def get_prediction(match_id: str):
    return get_match(match_id)


def get_team(team_id: str):
    return next((team for team in TEAMS if team["id"] == team_id or team["slug"] == team_id), None)
