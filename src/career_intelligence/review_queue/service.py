"""Public query service for the derived opportunity review queue (FR-009 M1)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunity_comparison import OpportunityComparisonService

from .eligibility import evaluate_eligibility
from .models import QueueEligibility, QueueScope, ReviewQueue


class ReviewQueueService:
    """Project persisted Opportunities into a ranked owner-review queue.

    Owns no storage of its own: it reads through ``OpportunityService`` (the
    system of record) and orders eligible records with the frozen FR-012 M4
    comparison logic. Queries never mutate stored Opportunities.
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
        """Records that still need a first apply / skip / defer decision."""
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
        excluded = sorted(
            (verdict for verdict in verdicts if not verdict.eligible),
            key=_by_opportunity_id,
        )
        return ReviewQueue(
            generated_at=comparison.generated_at,
            reference_date=as_at,
            scope=scope,
            items=comparison.items,
            excluded=excluded,
            owner_review_required=True,
        )


def _by_opportunity_id(verdict: QueueEligibility) -> str:
    return verdict.opportunity_id
