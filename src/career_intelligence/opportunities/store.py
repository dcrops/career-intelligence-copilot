"""Persistence boundary for durable opportunities."""

from __future__ import annotations

from pathlib import Path
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

    def save(self, opportunity: Opportunity) -> Opportunity:
        """Update an existing index row without touching artifact snapshots."""

    def create_index_only(self, opportunity: Opportunity) -> Opportunity:
        """Persist an index row without artifact snapshots (legacy import)."""

    def resolve_artifact_path(self, relative_path: str) -> Path:
        """Resolve a store-relative artifact path to an absolute filesystem path."""
