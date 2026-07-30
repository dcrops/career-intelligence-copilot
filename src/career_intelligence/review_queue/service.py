"""Public query service for the derived opportunity review queue (FR-009)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from career_intelligence.opportunities import Opportunity, OpportunityService
from career_intelligence.opportunity_comparison import OpportunityComparisonService
from career_intelligence.opportunity_comparison.models import RankedOpportunity

from .eligibility import evaluate_eligibility
from .models import QueueEligibility, QueueScope, ReviewQueue

PINNED_REASON = "Pinned by owner"


class ReviewQueueService:
    """Project persisted Opportunities into a ranked owner-review queue.

    Owns no storage of its own: it reads through ``OpportunityService`` (the
    system of record) and orders eligible records with the frozen FR-012 M4
    comparison logic, then applies an owner presentation override (pinned
    first). Queries never mutate stored Opportunities.
    """

    def __init__(
        self,
        opportunities: OpportunityService,
        *,
        comparison: OpportunityComparisonService | None = None,
    ) -> None:
        self._opportunities = opportunities
        self._comparison = comparison or OpportunityComparisonService()

    @property
    def opportunities(self) -> OpportunityService:
        return self._opportunities

    def list_awaiting_review(
        self,
        *,
        reference_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> ReviewQueue:
        """Records that still need a first apply / skip / defer decision.

        ``reviewed_at`` does not remove a record: awaiting review means no owner
        decision yet (FR-009 M2 Policy A).
        """
        return self._project(
            "awaiting_review",
            reference_date=reference_date,
            generated_at=generated_at,
        )

    def list_active_opportunities(
        self,
        *,
        reference_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> ReviewQueue:
        """Records still live for the owner, including those already applied for."""
        return self._project(
            "active",
            reference_date=reference_date,
            generated_at=generated_at,
        )

    def _project(
        self,
        scope: QueueScope,
        *,
        reference_date: date | None,
        generated_at: datetime | None,
    ) -> ReviewQueue:
        now = generated_at or datetime.now(UTC)
        as_at = reference_date or now.date()

        records = self._opportunities.list_opportunities()
        verdicts = [
            evaluate_eligibility(record, reference_date=as_at, scope=scope)
            for record in records
        ]
        eligible_ids = {
            verdict.opportunity_id for verdict in verdicts if verdict.eligible
        }
        eligible = [
            record for record in records if record.opportunity_id in eligible_ids
        ]

        comparison = self._comparison.compare_open(eligible, generated_at=now)
        items = _apply_pin_override(comparison.items, eligible)
        excluded = sorted(
            (verdict for verdict in verdicts if not verdict.eligible),
            key=_by_opportunity_id,
        )
        return ReviewQueue(
            generated_at=comparison.generated_at,
            reference_date=as_at,
            scope=scope,
            items=items,
            excluded=excluded,
            owner_review_required=True,
        )


def _apply_pin_override(
    items: list[RankedOpportunity],
    records: list[Opportunity],
) -> list[RankedOpportunity]:
    """Pinned first, preserving relative M4 order within each partition.

    Prepends ``PINNED_REASON`` so presentation override is distinct from fit.
    Does not change M4 fit values or the underlying comparison sort key.
    """
    by_id = {record.opportunity_id: record for record in records}
    pinned: list[RankedOpportunity] = []
    unpinned: list[RankedOpportunity] = []
    for item in items:
        record = by_id.get(item.opportunity_id)
        if record is not None and record.review.pinned:
            pinned.append(item)
        else:
            unpinned.append(item)

    ordered: list[RankedOpportunity] = []
    for rank, item in enumerate([*pinned, *unpinned], start=1):
        record = by_id.get(item.opportunity_id)
        reasons = list(item.reasons)
        if record is not None and record.review.pinned and PINNED_REASON not in reasons:
            reasons = [PINNED_REASON, *reasons]
        ordered.append(item.model_copy(update={"rank": rank, "reasons": reasons}))
    return ordered


def _by_opportunity_id(verdict: QueueEligibility) -> str:
    return verdict.opportunity_id
