import math


def poisson_probability(lambda_value, goals):
    safe_lambda = max(0.1, float(lambda_value or 1.2))
    safe_goals = max(0, int(goals))
    return math.exp(-safe_lambda) * (safe_lambda**safe_goals) / math.factorial(safe_goals)


def build_score_matrix(home_lambda, away_lambda, max_goals=6):
    matrix = []
    for home_goals in range(max_goals + 1):
        row = []
        for away_goals in range(max_goals + 1):
            row.append(
                {
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "probability": poisson_probability(home_lambda, home_goals)
                    * poisson_probability(away_lambda, away_goals),
                }
            )
        matrix.append(row)
    return matrix


def _pct(value: float) -> int:
    return max(0, min(100, round(value * 100)))


def calculate_goal_probabilities(home_lambda, away_lambda):
    safe_home = round(max(0.4, min(3.4, float(home_lambda or 1.35))), 2)
    safe_away = round(max(0.3, min(3.2, float(away_lambda or 1.15))), 2)
    matrix = build_score_matrix(safe_home, safe_away)
    flat = [cell for row in matrix for cell in row]
    most_likely = max(flat, key=lambda cell: cell["probability"])

    over_1_5 = sum(cell["probability"] for cell in flat if cell["home_goals"] + cell["away_goals"] > 1.5)
    over_2_5 = sum(cell["probability"] for cell in flat if cell["home_goals"] + cell["away_goals"] > 2.5)
    over_3_5 = sum(cell["probability"] for cell in flat if cell["home_goals"] + cell["away_goals"] > 3.5)
    btts = sum(cell["probability"] for cell in flat if cell["home_goals"] > 0 and cell["away_goals"] > 0)

    return {
        "expected_home": safe_home,
        "expected_away": safe_away,
        "most_likely_score": f"{most_likely['home_goals']}-{most_likely['away_goals']}",
        "over_1_5": _pct(over_1_5),
        "over_2_5": _pct(over_2_5),
        "over_3_5": _pct(over_3_5),
        "btts": _pct(btts),
    }
