"""Opportunity prioritisation recommendations (FR-009 M4).

Derived, deterministic, and advisory. The owner remains in control of apply / skip /
defer, duplicate confirmation, and canonical selection.
"""

from .explanation import (
    build_recommendation,
    priority_band,
    recommended_next_action,
    urgency_kind,
)
from .models import (
    PRIORITY_BANDS,
    URGENCY_KINDS,
    OpportunityRecommendation,
    PriorityBand,
    RecommendationReport,
    RecommendedNextAction,
    UrgencyKind,
)
from .service import OpportunityRecommendationService

__all__ = [
    "PRIORITY_BANDS",
    "URGENCY_KINDS",
    "OpportunityRecommendation",
    "OpportunityRecommendationService",
    "PriorityBand",
    "RecommendationReport",
    "RecommendedNextAction",
    "UrgencyKind",
    "build_recommendation",
    "priority_band",
    "recommended_next_action",
    "urgency_kind",
]
