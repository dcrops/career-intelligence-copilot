"""Public service boundary for durable Opportunity persistence (M1)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis, JobPosting
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch

from .errors import ErrorDetail, OpportunityValidationError
from .identity import build_identity
from .models import Opportunity, StrategySummary
from .store import OpportunityStore
from .yaml_store import YamlDirectoryOpportunityStore

DEFAULT_OPPORTUNITIES_ROOT = (
    Path(__file__).resolve().parents[3] / "data" / "opportunities"
)


class OpportunityService:
    """Stable interface for creating and retrieving persisted opportunities."""

    def __init__(self, store: OpportunityStore | None = None) -> None:
        self._store = store or YamlDirectoryOpportunityStore(_configured_root())

    @classmethod
    def from_path(cls, root: Path) -> OpportunityService:
        """Compose the service for an explicit opportunities directory."""
        return cls(store=YamlDirectoryOpportunityStore(root))

    def get(self, opportunity_id: str) -> Opportunity:
        return self._store.get(opportunity_id)

    def list_opportunities(self) -> list[Opportunity]:
        return self._store.list_opportunities()

    def create_from_strategy(
        self,
        *,
        posting: JobPosting,
        job_analysis: JobAnalysis,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        strategy: ApplicationStrategy,
    ) -> Opportunity:
        """Persist a new opportunity from trusted FR-002–FR-005 artifacts.

        Does not call OpenAI, re-assess, change strategy fields, record owner
        decisions, or enforce duplicate detection.
        """
        now = datetime.now(UTC)
        identity = build_identity(posting, job_analysis=job_analysis, created_at=now)
        summary = StrategySummary(
            pursuit_posture=strategy.pursuit_posture,
            application_tier=strategy.application_tier,
            practical_value=strategy.practical_value,
            technical_fit=assessment.technical_fit.judgment,
            commercial_fit=assessment.commercial_fit.judgment,
            portfolio_fit=assessment.portfolio_fit.judgment,
        )
        try:
            opportunity = Opportunity(
                identity=identity,
                status="assessed",
                decision=None,
                outcome=None,
                strategy_summary=summary,
                artifact_paths={},
                updated_at=now,
            )
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

        return self._store.create(
            opportunity,
            posting=posting,
            job_analysis=job_analysis,
            assessment=assessment,
            portfolio_match=portfolio_match,
            strategy=strategy,
        )


def _configured_root() -> Path:
    configured = os.getenv("CIC_OPPORTUNITIES_DIR")
    return Path(configured) if configured else DEFAULT_OPPORTUNITIES_ROOT
