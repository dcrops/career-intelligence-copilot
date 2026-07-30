"""Builders for FR-009 M1 review-queue tests.

Reuses the M4 comparison builder so ranking inputs stay identical to the frozen
baseline, then layers the FR-009 M0 review/duplicate contracts on top.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from career_intelligence.opportunities.models import (
    DuplicateRelation,
    Opportunity,
    OpportunityReview,
)
from tests.unit.opportunity_comparison.helpers import make_opportunity

REFERENCE_DATE = date(2026, 7, 30)
STAMP = datetime(2026, 7, 30, 9, 0, 0, tzinfo=UTC)


def queue_opportunity(
    opportunity_id: str,
    *,
    review: OpportunityReview | None = None,
    duplicate_of: str | None = None,
    **kwargs: object,
) -> Opportunity:
    """An Opportunity with optional review metadata / confirmed duplicate link."""
    base = make_opportunity(opportunity_id, **kwargs)  # type: ignore[arg-type]
    updates: dict[str, object] = {}
    if review is not None:
        updates["review"] = review
    if duplicate_of is not None:
        updates["duplicate"] = DuplicateRelation(
            duplicate_of=duplicate_of,
            confirmed_at=STAMP,
            evidence=("owner_judgment",),
        )
    if not updates:
        return base
    return base.model_copy(update=updates, deep=True)
