"""Public service for ranked comparison of open opportunities (M4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import ValidationError

from career_intelligence.opportunities.models import Opportunity

from .errors import ErrorDetail, OpportunityComparisonValidationError
from .models import OpportunityComparison
from .ranking import is_open_opportunity, rank_open_opportunities


class OpportunityComparisonService:
    """Deterministic comparison boundary — does not persist or call OpenAI.

    Consumes trusted Opportunity aggregates (from OpportunityService). Ranking
    logic lives in ``ranking``; this service validates and wraps the result.
    """

    def compare_open(
        self,
        opportunities: Sequence[Opportunity],
        *,
        generated_at: datetime | None = None,
    ) -> OpportunityComparison:
        """Rank open opportunities; exclude terminal/skipped and closed statuses."""
        items = list(opportunities)
        open_items = [item for item in items if is_open_opportunity(item)]
        ranked = rank_open_opportunities(items)
        try:
            return OpportunityComparison(
                generated_at=generated_at or datetime.now(UTC),
                open_only=True,
                open_count=len(open_items),
                excluded_count=len(items) - len(open_items),
                items=ranked,
                owner_review_required=True,
            )
        except ValidationError as error:
            raise OpportunityComparisonValidationError(
                [ErrorDetail.from_pydantic(detail) for detail in error.errors()]
            ) from error
