from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from services.backtesting import calculate_backtest_report
from services.shadow_backtesting import calculate_shadow_backtest_report
from services.hybrid_engine import build_hybrid_engine_decision


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def get_period_start(period: str) -> datetime | None:
    now = datetime.now(timezone.utc)

    if period == "7d":
        return now - timedelta(days=7)

    if period == "30d":
        return now - timedelta(days=30)

    if period == "90d":
        return now - timedelta(days=90)

    return None


def is_finished_match(match: dict[str, Any]) -> bool:
    return str(match.get("status", "")).upper() == "FINISHED"


def filter_matches_by_period(matches: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
    start = get_period_start(period)

    filtered = []

    for match in matches:
        if not is_finished_match(match):
            continue

        kickoff = parse_datetime(match.get("kickoff"))

        if not kickoff:
            continue

        if start is not None and kickoff < start:
            continue

        filtered.append(match)

    return filtered


def safe_rate(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0

    return round((numerator / denominator) * 100)


def _match_keys(match: dict[str, Any]) -> set[str]:
    return {
        str(value)
        for value in [
            match.get("id"),
            match.get("match_id"),
            match.get("slug"),
        ]
        if value
    }


def _prediction_key(prediction: dict[str, Any]) -> str | None:
    for key in ["match_id", "id", "slug"]:
        value = prediction.get(key)
        if value:
            return str(value)

    return None


def _filter_predictions_for_matches(
    predictions: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    allowed = set()

    for match in matches:
        allowed.update(_match_keys(match))

    result = []

    for prediction in predictions:
        keys = {
            str(value)
            for value in [
                prediction.get("id"),
                prediction.get("match_id"),
                prediction.get("slug"),
            ]
            if value
        }

        if keys.intersection(allowed):
            result.append(prediction)

    return result


def build_official_monitoring(
    matches: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    period: str = "30d",
) -> dict[str, Any]:
    period_matches = filter_matches_by_period(matches, period)
    period_predictions = _filter_predictions_for_matches(predictions, period_matches)

    report = calculate_backtest_report(period_matches, period_predictions)

    reliable_count = 0
    medium_count = 0
    avoid_count = 0
    trap_match_count = 0

    for prediction in period_predictions:
        confidence = prediction.get("confidence") or {}
        status = str(confidence.get("status", "")).upper()
        flags = prediction.get("flags") or {}

        if status == "FIABLE":
            reliable_count += 1
        elif status == "MOYEN":
            medium_count += 1
        elif status in {"A EVITER", "À ÉVITER", "Ã€ Ã‰VITER"}:
            avoid_count += 1

        if flags.get("trap_match"):
            trap_match_count += 1

    average_brier = report.get("average_brier_score")
    if average_brier == 0 and report.get("evaluated_matches", 0) == 0:
        average_brier = None

    return {
        "period": period,
        "evaluated_matches": report.get("evaluated_matches", 0),
        "result_accuracy": report.get("result_accuracy", 0),
        "average_brier_score": average_brier,
        "average_confidence": report.get("average_confidence", 0),
        "calibration_score": report.get("calibration_score", 0),
        "reliable_count": reliable_count,
        "medium_count": medium_count,
        "avoid_count": avoid_count,
        "trap_match_count": trap_match_count,
        "competition_breakdown": report.get("competition_breakdown", {}),
    }


def build_shadow_monitoring(
    matches: list[dict[str, Any]],
    shadow_records: list[dict[str, Any]],
    period: str = "30d",
) -> dict[str, Any]:
    period_matches = filter_matches_by_period(matches, period)
    report = calculate_shadow_backtest_report(period_matches, shadow_records)

    return {
        "period": period,
        "evaluated_matches": report.get("evaluated_matches", 0),
        "production_accuracy": report.get("production_accuracy", 0),
        "shadow_accuracy": report.get("shadow_accuracy", 0),
        "production_average_brier": report.get("production_average_brier"),
        "shadow_average_brier": report.get("shadow_average_brier"),
        "disagreement_count": report.get("disagreement_count", 0),
        "high_disagreement_count": report.get("high_disagreement_count", 0),
        "shadow_wins_on_disagreement": report.get("shadow_wins_on_disagreement", 0),
        "production_wins_on_disagreement": report.get("production_wins_on_disagreement", 0),
        "activation_recommendation": report.get("activation_recommendation", "insufficient_data"),
    }


def _prediction_in_period(prediction: dict[str, Any], period: str) -> bool:
    start = get_period_start(period)

    if start is None:
        return True

    kickoff = parse_datetime(prediction.get("kickoff"))

    if not kickoff:
        return False

    return kickoff >= start


def build_hybrid_monitoring(
    predictions: list[dict[str, Any]],
    period: str = "30d",
    limit: int = 300,
) -> dict[str, Any]:
    selected = [
        prediction
        for prediction in predictions
        if _prediction_in_period(prediction, period)
    ][:limit]

    counts = {
        "strong": 0,
        "medium": 0,
        "weak": 0,
        "avoid": 0,
        "unknown": 0,
    }

    for prediction in selected:
        decision = prediction.get("hybrid_engine")

        if not decision:
            try:
                decision = build_hybrid_engine_decision(prediction, prediction.get("shadow"))
            except Exception:
                decision = {}

        level = decision.get("decision_level", "unknown")

        if level not in counts:
            level = "unknown"

        counts[level] += 1

    total = len(selected)

    return {
        "period": period,
        "processed_predictions": total,
        "strong_count": counts["strong"],
        "medium_count": counts["medium"],
        "weak_count": counts["weak"],
        "avoid_count": counts["avoid"],
        "unknown_count": counts["unknown"],
        "strong_rate": safe_rate(counts["strong"], total),
        "avoid_rate": safe_rate(counts["avoid"], total),
    }


def _trend_direction(newer: Any, older: Any, lower_is_better: bool = False) -> str:
    if newer is None or older is None:
        return "unknown"

    try:
        newer_value = float(newer)
        older_value = float(older)
    except Exception:
        return "unknown"

    delta = newer_value - older_value

    if abs(delta) < 1:
        return "stable"

    if lower_is_better:
        return "better" if delta < 0 else "worse"

    return "up" if delta > 0 else "down"


def _build_alerts(periods: dict[str, Any]) -> list[dict[str, str]]:
    alerts = []

    thirty = periods.get("30d", {})
    official = thirty.get("official", {})
    shadow = thirty.get("shadow", {})

    evaluated = official.get("evaluated_matches", 0)
    accuracy = official.get("result_accuracy", 0)
    brier = official.get("average_brier_score")

    if evaluated < 10:
        alerts.append(
            {
                "level": "warning",
                "message": "Échantillon 30 jours faible. Les tendances doivent être lues avec prudence.",
            }
        )

    if evaluated >= 10 and accuracy < 45:
        alerts.append(
            {
                "level": "risk",
                "message": "Accuracy 30 jours faible sur les matchs évalués.",
            }
        )

    if brier is not None and brier > 0.75:
        alerts.append(
            {
                "level": "risk",
                "message": "Score Brier élevé. Les probabilités semblent moins bien calibrées.",
            }
        )

    if shadow.get("high_disagreement_count", 0) >= 10:
        alerts.append(
            {
                "level": "watch",
                "message": "Nombre élevé de désaccords forts entre modèle officiel et ML shadow.",
            }
        )

    return alerts[:10]


def build_monitoring_report(
    matches: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    shadow_records: list[dict[str, Any]],
    periods: list[str] | None = None,
) -> dict[str, Any]:
    selected_periods = periods or ["7d", "30d", "90d", "all"]
    allowed = {"7d", "30d", "90d", "all"}
    selected_periods = [period for period in selected_periods if period in allowed] or ["30d"]

    period_reports = {}

    for period in selected_periods:
        period_reports[period] = {
            "official": build_official_monitoring(matches, predictions, period),
            "shadow": build_shadow_monitoring(matches, shadow_records, period),
            "hybrid": build_hybrid_monitoring(predictions, period),
        }

    seven = period_reports.get("7d", {}).get("official", {})
    thirty = period_reports.get("30d", {}).get("official", {})
    shadow_thirty = period_reports.get("30d", {}).get("shadow", {})

    accuracy_direction = _trend_direction(
        seven.get("result_accuracy"),
        thirty.get("result_accuracy"),
    )

    brier_direction = _trend_direction(
        seven.get("average_brier_score"),
        thirty.get("average_brier_score"),
        lower_is_better=True,
    )

    shadow_accuracy = shadow_thirty.get("shadow_accuracy", 0)
    production_accuracy = shadow_thirty.get("production_accuracy", 0)

    if shadow_thirty.get("evaluated_matches", 0) == 0:
        shadow_edge = "unknown"
    elif shadow_accuracy >= production_accuracy + 3:
        shadow_edge = "positive"
    elif production_accuracy >= shadow_accuracy + 3:
        shadow_edge = "negative"
    else:
        shadow_edge = "neutral"

    alerts = _build_alerts(period_reports)

    evaluated_30d = thirty.get("evaluated_matches", 0)

    if evaluated_30d < 10:
        monitoring_status = "insufficient_data"
    elif any(alert.get("level") == "risk" for alert in alerts):
        monitoring_status = "risk"
    elif alerts:
        monitoring_status = "watch"
    else:
        monitoring_status = "healthy"

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_model_version": "elo-poisson-calibrated-v1",
        "candidate_model_version": "ml-candidate-v1",
        "candidate_is_production": False,
        "periods": period_reports,
        "trend_summary": {
            "accuracy_direction": accuracy_direction,
            "brier_direction": brier_direction,
            "shadow_edge": shadow_edge,
            "monitoring_status": monitoring_status,
        },
        "alerts": alerts,
        "note": "Le monitoring suit les performances observées sans activer le ML en production.",
    }
