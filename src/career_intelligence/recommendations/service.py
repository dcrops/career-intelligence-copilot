"""Read-only opportunity prioritisation recommendations (FR-009 M4).

Composes the review-queue eligibility projection with the calibrated comparison
sort key. Never mutates Opportunities. Owner review, duplicate confirmation, and
canonical selection remain authoritative — this service only recommends attention.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from career_intelligence.duplicates.groups import build_groups
from career_intelligence.opportunities import Opportunity, OpportunityService
from career_intelligence.review_queue import ReviewQueueService
from career_intelligence.review_queue.models import QueueScope

from .explanation import build_recommendation
from .models import OpportunityRecommendation, RecommendationReport


class OpportunityRecommendationService:
    """Derive prioritised, explainable recommendations over persisted Opportunities."""

    def __init__(
        self,
        opportunities: OpportunityService,
        *,
        queue: ReviewQueueService | None = None,
    ) -> None:
        self._opportunities = opportunities
        self._queue = queue or ReviewQueueService(opportunities)

    @property
    def opportunities(self) -> OpportunityService:
        return self._opportunities

    def recommend_awaiting_review(
        self,
        *,
        reference_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> RecommendationReport:
        """Prioritise Opportunities that still need apply / skip / defer."""
        return self._recommend(
            "awaiting_review",
            reference_date=reference_date,
            generated_at=generated_at,
        )

    def recommend_active(
        self,
        *,
        reference_date: date | None = None,
        generated_at: datetime | None = None,
    ) -> RecommendationReport:
        """Prioritise live Opportunities, including those already applied for."""
        return self._recommend(
            "active",
            reference_date=reference_date,
            generated_at=generated_at,
        )

    def _recommend(
        self,
        scope: QueueScope,
        *,
        reference_date: date | None,
        generated_at: datetime | None,
    ) -> RecommendationReport:
        now = generated_at or datetime.now(UTC)
        as_at = reference_date or now.date()
        if scope == "awaiting_review":
            queue = self._queue.list_awaiting_review(
                reference_date=as_at, generated_at=now
            )
        else:
            queue = self._queue.list_active_opportunities(
                reference_date=as_at, generated_at=now
            )

        records = self._opportunities.list_opportunities()
        by_id: dict[str, Opportunity] = {
            record.opportunity_id: record for record in records
        }
        group_size_by_id = _group_sizes(records)

        items: list[OpportunityRecommendation] = []
        for ranked in queue.items:
            record = by_id.get(ranked.opportunity_id)
            if record is None:
                continue
            items.append(
                build_recommendation(
                    ranked,
                    record,
                    reference_date=as_at,
                    group_size=group_size_by_id.get(ranked.opportunity_id),
                )
            )

        return RecommendationReport(
            generated_at=queue.generated_at,
            reference_date=as_at,
            scope=scope,
            items=tuple(items),
            excluded_count=queue.excluded_count,
            owner_review_required=True,
        )


def _group_sizes(records: list[Opportunity]) -> dict[str, int]:
    """Map every group member (and canonical) to the group's size, if size ≥ 2."""
    sizes: dict[str, int] = {}
    for group in build_groups(records):
        size = group.size
        if size < 2:
            continue
        for opportunity_id in group.opportunity_ids:
            sizes[opportunity_id] = size
    return sizes
