from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class UserBetLearningProfile:
    user_id: str
    preferred_markets: list[str]
    user_roi: float | None
    frequent_errors: list[dict[str, Any]]
    risk_excess_flags: list[str]
    performance_by_odds: dict[str, Any]
    performance_by_market: dict[str, Any]
    recommendations: list[str]


SETTLED_STATUSES = {"won", "lost", "void"}


def _settled(bets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in bets if item.get("status") in SETTLED_STATUSES]


def _profit(items: list[dict[str, Any]]) -> float:
    return round(sum(float(item.get("result_profit") or 0) for item in items), 4)


def _staked(items: list[dict[str, Any]]) -> float:
    return round(sum(float(item.get("stake") or 0) for item in items), 4)


def _roi(items: list[dict[str, Any]]) -> float | None:
    stake = _staked(items)
    return round(_profit(items) / stake, 4) if items and stake else None


def build_empty_user_learning_profile(user_id: str) -> dict[str, Any]:
    return asdict(
        UserBetLearningProfile(
            user_id=user_id,
            preferred_markets=[],
            user_roi=None,
            frequent_errors=[],
            risk_excess_flags=[],
            performance_by_odds={},
            performance_by_market={},
            recommendations=[
                "Donnees insuffisantes : collecter davantage de paris avant de personnaliser les recommandations."
            ],
        )
    )


def _group_performance(bets: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for bet in _settled(bets):
        raw = bet.get("raw_context") or {}
        value = raw.get(key) if key == "competition" else bet.get(key)
        grouped.setdefault(str(value or "unknown"), []).append(bet)
    return {
        name: {
            "settled_bets": len(items),
            "total_staked": _staked(items),
            "net_profit": _profit(items),
            "roi": _roi(items),
        }
        for name, items in sorted(grouped.items())
    }


def build_user_betting_profile(user_id: str, bets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    bets = bets or []
    settled = _settled(bets)
    if len(settled) < 3:
        return build_empty_user_learning_profile(user_id)
    by_market = _group_performance(bets, "market")
    preferred_markets = [
        market for market, stats in sorted(by_market.items(), key=lambda item: item[1].get("roi") or -999, reverse=True)
        if (stats.get("roi") or 0) > 0
    ]
    return asdict(
        UserBetLearningProfile(
            user_id=user_id,
            preferred_markets=preferred_markets,
            user_roi=_roi(settled),
            frequent_errors=detect_user_weaknesses(user_id, bets),
            risk_excess_flags=detect_risky_patterns(user_id, bets),
            performance_by_odds=_performance_by_odds_band(settled),
            performance_by_market=by_market,
            recommendations=recommend_user_discipline(user_id, bets),
        )
    )


def _performance_by_odds_band(bets: list[dict[str, Any]]) -> dict[str, Any]:
    bands = {"low": [], "medium": [], "high": []}
    for bet in bets:
        odds = float(bet.get("odds_decimal") or 0)
        if odds >= 3:
            bands["high"].append(bet)
        elif odds >= 2:
            bands["medium"].append(bet)
        else:
            bands["low"].append(bet)
    return {
        band: {"settled_bets": len(items), "roi": _roi(items), "net_profit": _profit(items)}
        for band, items in bands.items()
    }


def detect_user_strengths(user_id: str, bets: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    performance = _group_performance(bets or [], "market")
    return [
        {"market": market, **stats}
        for market, stats in performance.items()
        if stats["settled_bets"] >= 2 and (stats.get("roi") or 0) > 0
    ]


def detect_user_weaknesses(user_id: str, bets: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    performance = _group_performance(bets or [], "market")
    return [
        {"market": market, **stats, "message": "Ce marche est historiquement moins rentable. Prudence."}
        for market, stats in performance.items()
        if stats["settled_bets"] >= 2 and (stats.get("roi") or 0) < 0
    ]


def detect_risky_patterns(user_id: str, bets: list[dict[str, Any]] | None = None) -> list[str]:
    settled = _settled(bets or [])
    flags: list[str] = []
    high_odds = [item for item in settled if float(item.get("odds_decimal") or 0) >= 3]
    negative_ev = [item for item in settled if item.get("expected_value") is not None and float(item.get("expected_value") or 0) < 0]
    losses = [item for item in settled if item.get("status") == "lost"]
    if len(high_odds) >= 3 and (_roi(high_odds) or 0) < 0:
        flags.append("Tendance a jouer des cotes elevees non rentables.")
    if len(negative_ev) >= 3 and (_roi(negative_ev) or 0) < 0:
        flags.append("Tendance a jouer sans value positive.")
    if len(losses) >= 3 and sum(float(item.get("stake") or 0) for item in losses[-3:]) > sum(float(item.get("stake") or 0) for item in settled[:3] or losses[-3:]):
        flags.append("Sur-risque possible apres pertes.")
    return flags


def generate_user_betting_insights(user_id: str, bets: list[dict[str, Any]] | None = None) -> list[str]:
    bets = bets or []
    settled = _settled(bets)
    if len(settled) < 3:
        return ["Donnees insuffisantes pour une conclusion fiable."]
    insights = []
    strengths = detect_user_strengths(user_id, bets)
    weaknesses = detect_user_weaknesses(user_id, bets)
    if strengths:
        insights.append(f"Vous etes historiquement plus performant sur {strengths[0]['market']}.")
    if weaknesses:
        insights.append(f"Ce type de pari ressemble a plusieurs paris precedents non rentables ({weaknesses[0]['market']}). Prudence.")
    insights.extend(detect_risky_patterns(user_id, bets))
    positive_ev = [item for item in settled if item.get("expected_value") is not None and float(item.get("expected_value") or 0) > 0]
    negative_ev = [item for item in settled if item.get("expected_value") is not None and float(item.get("expected_value") or 0) < 0]
    if positive_ev:
        insights.append(f"ROI sur paris avec EV positive : {_roi(positive_ev)}.")
    if negative_ev:
        insights.append(f"ROI sur paris avec EV negative : {_roi(negative_ev)}.")
    return insights or ["La value est positive, mais votre historique reste encore limite."]


def recommend_user_discipline(user_id: str, bets: list[dict[str, Any]] | None = None) -> list[str]:
    flags = detect_risky_patterns(user_id, bets)
    if flags:
        return ["Reduire la mise sur les profils detectes a risque.", "Verifier la cote reelle avant tout calcul de value."]
    return ["Maintenir une mise proportionnee au risque.", "Ne pas forcer un pari quand les donnees sont insuffisantes."]


def analyze_user_bets(user_id: str, bets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    bets = bets or []
    return {
        "status": "not_enough_data" if len(_settled(bets)) < 3 else "ok",
        "profile": build_user_betting_profile(user_id, bets),
        "bets_analyzed": len(bets),
        "strengths": detect_user_strengths(user_id, bets),
        "weaknesses": detect_user_weaknesses(user_id, bets),
        "risky_patterns": detect_risky_patterns(user_id, bets),
        "insights": generate_user_betting_insights(user_id, bets),
        "discipline": recommend_user_discipline(user_id, bets),
    }
