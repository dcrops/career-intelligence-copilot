"""Shared builders for FR-008 M1 orchestration tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_strategy import ApplicationStrategyService
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import MARKER_AI_ENGINEER, posting_ai_engineer
from career_intelligence.opportunity_assessment import OpportunityAssessmentService
from career_intelligence.opportunity_assessment.fixture_assessor import FixtureAssessor
from career_intelligence.opportunities import OpportunityService
from career_intelligence.orchestration import (
    ApplicationWorkflowRunner,
    FailureInjection,
    InMemoryCheckpointStore,
    JsonDirectoryCheckpointStore,
    PasteJobInput,
    RetryPolicy,
    WorkflowDependencies,
)
from career_intelligence.portfolio_matching import PortfolioMatchingService
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.profile import CareerProfile, CareerProfileService
from career_intelligence.profile.models import CareerProfile as CareerProfileModel


def fixtures_dir() -> Path:
    return Path(__file__).parents[2] / "fixtures"


def golden_profile() -> CareerProfileModel:
    return CareerProfileService.from_path(
        fixtures_dir() / "golden" / "career_profile.yaml"
    ).load()


def fixture_job_input(**overrides: object) -> PasteJobInput:
    posting = posting_ai_engineer()
    payload = {
        "raw_text": posting.raw_text,
        "title": posting.title,
        "company": posting.company,
        "source_url": "https://example.com/jobs/ai-engineer",
    }
    payload.update(overrides)
    return PasteJobInput(**payload)  # type: ignore[arg-type]


def offline_dependencies(
    store=None,
    *,
    profile: CareerProfile | None = None,
    opportunities: OpportunityService | None = None,
    opportunities_dir: Path | None = None,
) -> WorkflowDependencies:
    if opportunities is None:
        if opportunities_dir is None:
            # Ephemeral in-memory-like isolation: callers should pass tmp_path.
            # Default to a disposable relative path only for unit smoke without disk.
            opportunities = OpportunityService.from_path(
                Path(".pytest_cache") / "orchestration_opportunities_default"
            )
        else:
            opportunities = OpportunityService.from_path(opportunities_dir)
    return WorkflowDependencies(
        profile=profile or golden_profile(),
        job_analysis=JobAnalysisService(FixtureExtractor()),
        assessment=OpportunityAssessmentService(FixtureAssessor()),
        portfolio_matching=PortfolioMatchingService(DeterministicMatcher()),
        application_strategy=ApplicationStrategyService(DeterministicStrategyPlanner()),
        store=store or InMemoryCheckpointStore(),
        opportunities=opportunities,
    )


def offline_runner(
    store=None,
    *,
    opportunities_dir: Path | None = None,
    retry_policy: RetryPolicy | None = None,
    failure_injection: FailureInjection | None = None,
    **kwargs: object,
) -> ApplicationWorkflowRunner:
    return ApplicationWorkflowRunner(
        offline_dependencies(
            store=store,
            opportunities_dir=opportunities_dir,
            **kwargs,
        ),
        retry_policy=retry_policy,
        failure_injection=failure_injection,
    )


def json_runner(tmp_path: Path, **kwargs: object) -> ApplicationWorkflowRunner:
    store = JsonDirectoryCheckpointStore(tmp_path / "workflow_runs")
    return offline_runner(
        store=store,
        opportunities_dir=tmp_path / "opportunities",
        **kwargs,
    )


assert MARKER_AI_ENGINEER in posting_ai_engineer().raw_text
