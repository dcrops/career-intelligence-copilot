"""Shared builders for opportunity persistence (M1) tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_strategy import ApplicationStrategy, ApplicationStrategyService
from career_intelligence.job_analysis.models import JobAnalysis, JobPosting
from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile import CareerProfile
from tests.unit.application_strategy.helpers import (
    job_analysis,
    minimal_profile,
    opportunity_assessment,
    portfolio_match,
    valid_strategy_payload,
)


class _StaticPayloadPlanner:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def plan(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        profile: CareerProfile,
        operating_context: object,
    ) -> dict[str, object]:
        _ = assessment, portfolio_match, profile, operating_context
        return self._payload


def trusted_pipeline(
    *,
    source_url: str | None = "https://au.seek.com/job/93487188",
    title: str = "Senior AI Engineer",
    company: str = "Example AI Co",
) -> tuple[
    JobPosting,
    JobAnalysis,
    OpportunityAssessment,
    PortfolioMatch,
    ApplicationStrategy,
]:
    analysis = job_analysis(
        posting={
            "raw_text": "Senior AI Engineer. Python required. Hybrid Melbourne.",
            "title": title,
            "company": company,
            **({"source_url": source_url} if source_url else {}),
        }
    )
    assessment = opportunity_assessment(analysis)
    match = portfolio_match(analysis)
    profile = minimal_profile()
    strategy = ApplicationStrategyService(
        _StaticPayloadPlanner(valid_strategy_payload())
    ).plan(assessment, match, profile)
    return analysis.posting, analysis, assessment, match, strategy


def create_opportunity(tmp_path: Path, **pipeline_kwargs: object):
    posting, analysis, assessment, match, strategy = trusted_pipeline(**pipeline_kwargs)
    service = OpportunityService.from_path(tmp_path)
    opportunity = service.create_from_strategy(
        posting=posting,
        job_analysis=analysis,
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    return service, opportunity, (posting, analysis, assessment, match, strategy)
