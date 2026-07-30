"""Typed models for the derived opportunity review queue (FR-009 M1).

Nothing here is persisted. Eligibility and rank position are recomputed from the
Opportunity system of record on every query (ADR-004), so the queue can never
drift from the durable records it describes.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from career_intelligence.opportunity_comparison.models import RankedOpportunity

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

ExclusionReason = Literal[
    "archived",
    "confirmed_duplicate",
    "skipped",
    "deferred",
    "closed",
    "decided",
]

EXCLUSION_REASONS: tuple[ExclusionReason, ...] = get_args(ExclusionReason)

# ``awaiting_review`` answers "what still needs an initial owner decision".
# ``active`` answers "what is still live", including records already applied for.
QueueScope = Literal["awaiting_review", "active"]

QUEUE_SCOPES: tuple[QueueScope, ...] = get_args(QueueScope)


class ReviewQueueModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QueueEligibility(ReviewQueueModel):
    """Whether one Opportunity belongs in a queue scope, and why not."""

    opportunity_id: NonEmptyString
    eligible: bool
    exclusion_reasons: tuple[ExclusionReason, ...] = ()

    @model_validator(mode="after")
    def reasons_match_verdict(self) -> QueueEligibility:
        if self.eligible and self.exclusion_reasons:
            raise ValueError("an eligible record must not carry exclusion reasons")
        if not self.eligible and not self.exclusion_reasons:
            raise ValueError("an excluded record must state at least one reason")
        return self


class ReviewQueue(ReviewQueueModel):
    """One deterministic projection of the Opportunity store for owner review."""

    generated_at: datetime
    reference_date: date
    scope: QueueScope
    items: list[RankedOpportunity]
    excluded: list[QueueEligibility]
    owner_review_required: bool = True

    @property
    def included_count(self) -> int:
        return len(self.items)

    @property
    def excluded_count(self) -> int:
        return len(self.excluded)

    @property
    def opportunity_ids(self) -> list[str]:
        """Ranked opportunity ids, highest priority first."""
        return [item.opportunity_id for item in self.items]
