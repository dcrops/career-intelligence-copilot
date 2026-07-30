"""Derived opportunity recommendations (FR-009 M4).

Recommendations are computed on every call from persisted Opportunities. They never
replace owner decisions — they answer "what deserves attention next?" with
deterministic order and an explainable rationale.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from career_intelligence.application_strategy.models import (
    ApplicationTier,
    PracticalValue,
    PursuitPosture,
)

PriorityBand = Literal["immediate", "high", "standard", "low"]
UrgencyKind = Literal["due", "upcoming", "process", "none"]
RecommendedNextAction = Literal[
    "record_owner_decision",
    "re_review_expired_defer",
    "wait_until_defer_date",
    "prepare_application_package",
    "continue_package_preparation",
    "track_application_pipeline",
    "prepare_for_interview",
    "decide_on_offer",
    "review_opportunity",
]

PRIORITY_BANDS: tuple[PriorityBand, ...] = (
    "immediate",
    "high",
    "standard",
    "low",
)
URGENCY_KINDS: tuple[UrgencyKind, ...] = ("due", "upcoming", "process", "none")


class RecommendationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class OpportunityRecommendation(RecommendationModel):
    """One prioritised Opportunity with structured, deterministic explanation."""

    rank: int = Field(ge=1)
    opportunity_id: str
    company: str | None = None
    title: str | None = None
    priority_band: PriorityBand
    urgency: UrgencyKind
    recommended_next_action: RecommendedNextAction
    pursuit_posture: PursuitPosture | None = None
    practical_value: PracticalValue | None = None
    application_tier: ApplicationTier | None = None
    fit_strength: int = Field(ge=0)
    pinned: bool = False
    duplicate_group_size: int | None = Field(default=None, ge=2)
    positives: tuple[str, ...] = ()
    negatives: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    ranking_reasons: tuple[str, ...] = ()
    trade_offs: tuple[str, ...] = ()


class RecommendationReport(RecommendationModel):
    """Derived prioritisation of Opportunities for owner attention."""

    generated_at: datetime
    reference_date: date
    scope: Literal["awaiting_review", "active"]
    items: tuple[OpportunityRecommendation, ...] = ()
    excluded_count: int = Field(ge=0)
    owner_review_required: bool = True

    @property
    def opportunity_ids(self) -> list[str]:
        return [item.opportunity_id for item in self.items]

    @property
    def included_count(self) -> int:
        return len(self.items)
