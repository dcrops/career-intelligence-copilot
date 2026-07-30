"""Read-only duplicate review projections (FR-009 M3).

Mirrors the FR-009 M1/M2 split: this service only reads and derives, while
``DuplicateReviewService`` owns the owner-confirmed writes. Nothing here mutates a
record, so repeated scans are safe at any time.
"""

from __future__ import annotations

from datetime import UTC, datetime

from career_intelligence.opportunities.models import Opportunity
from career_intelligence.opportunities.service import OpportunityService

from .canonical import recommend_canonical
from .detection import detect_candidates
from .groups import build_groups, group_for
from .models import (
    CanonicalRecommendation,
    DuplicateCandidate,
    DuplicateCandidateReport,
    DuplicateGroup,
)


class DuplicateDetectionService:
    """Derive duplicate candidates, confirmed groups, and canonical suggestions."""

    def __init__(self, opportunities: OpportunityService) -> None:
        self._opportunities = opportunities

    @property
    def opportunities(self) -> OpportunityService:
        return self._opportunities

    def list_candidates(
        self,
        *,
        generated_at: datetime | None = None,
    ) -> DuplicateCandidateReport:
        """Unresolved suggestions, strongest evidence first.

        Excludes pairs the owner already confirmed or rejected, so the report shrinks
        as review progresses instead of re-asking settled questions.
        """
        records = self._opportunities.list_opportunities()
        return DuplicateCandidateReport(
            generated_at=generated_at or datetime.now(UTC),
            candidates=detect_candidates(records),
        )

    def candidates_for(
        self,
        opportunity_id: str,
        *,
        generated_at: datetime | None = None,
    ) -> tuple[DuplicateCandidate, ...]:
        """Unresolved suggestions involving one record."""
        report = self.list_candidates(generated_at=generated_at)
        return tuple(
            candidate
            for candidate in report.candidates
            if opportunity_id in candidate.pair
        )

    def list_groups(self) -> tuple[DuplicateGroup, ...]:
        """Owner-confirmed duplicate groups derived from ``duplicate`` links."""
        return build_groups(self._opportunities.list_opportunities())

    def group_for(self, opportunity_id: str) -> DuplicateGroup | None:
        """The confirmed group containing ``opportunity_id``, if any."""
        return group_for(opportunity_id, self._opportunities.list_opportunities())

    def recommend_canonical(self, opportunity_id: str) -> CanonicalRecommendation:
        """Recommend a canonical record for the group containing ``opportunity_id``.

        Advisory: the owner still confirms via
        ``DuplicateReviewService.confirm_canonical``.
        """
        records = self._opportunities.list_opportunities()
        group = group_for(opportunity_id, records)
        if group is None:
            record = self._opportunities.get(opportunity_id)
            return recommend_canonical([record])
        by_id: dict[str, Opportunity] = {
            record.opportunity_id: record for record in records
        }
        members = [by_id[item] for item in group.opportunity_ids if item in by_id]
        return recommend_canonical(members)
