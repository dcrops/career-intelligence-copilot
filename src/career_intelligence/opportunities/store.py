"""Persistence boundary for durable opportunities."""

from __future__ import annotations

from typing import Protocol

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis, JobPosting
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch

from .models import Opportunity


class OpportunityStore(Protocol):
    """Replaceable store — no YAML/CSV-specific surface."""

    def get(self, opportunity_id: str) -> Opportunity:
        """Load one opportunity by id."""

    def list_opportunities(self) -> list[Opportunity]:
        """Return all opportunities in deterministic order (newest first)."""

    def create(
        self,
        opportunity: Opportunity,
        *,
        posting: JobPosting,
        job_analysis: JobAnalysis,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        strategy: ApplicationStrategy,
    ) -> Opportunity:
        """Persist opportunity index row and immutable artifact snapshots."""
