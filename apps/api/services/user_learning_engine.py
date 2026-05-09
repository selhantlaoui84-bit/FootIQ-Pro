from __future__ import annotations

from dataclasses import dataclass, asdict
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
                "Collecter les paris utilisateur avant d'activer les recommandations personnalisées."
            ],
        )
    )


def analyze_user_bets(user_id: str, bets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "status": "not_enough_data" if not bets else "pending_implementation",
        "profile": build_empty_user_learning_profile(user_id),
        "bets_analyzed": len(bets or []),
        "note": "Structure prête pour apprendre des marchés, cotes, ROI et erreurs utilisateur sans modifier le produit actuel.",
    }
