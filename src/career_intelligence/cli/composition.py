"""CLI composition root for FR-018 discovery workflow wiring.

This module is the **sole in-package composition root** allowed to construct
concrete FR-002 extractors and FR-003 assessors for ``cic opportunity discover``
/ ``discover-email``. Downstream packages and CLI command handlers must depend
on public services / injected ``WorkflowDependencies`` only — not on extractor
or assessor implementation modules.

FR-002 / FR-003 acceptance scans path-allow this file explicitly (parallel to
out-of-package ``scripts/run_fr008_workflow_manual.py`` wiring).
"""

from __future__ import annotations

import os
from pathlib import Path

from career_intelligence.application_strategy import ApplicationStrategyService
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.job_analysis import JobAnalysisService

# Canonical offline marker — imported only in this composition root so command
# handlers never touch ``job_analysis.fixtures``. Must stay aligned with
# FixtureExtractor matching.
from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER as OFFLINE_DISCOVERY_FIXTURE_MARKER,
)
from career_intelligence.opportunities import OpportunityService
from career_intelligence.opportunity_assessment import OpportunityAssessmentService
from career_intelligence.orchestration import (
    ApplicationWorkflowRunner,
    JsonDirectoryCheckpointStore,
    WorkflowDependencies,
)
from career_intelligence.portfolio_matching import PortfolioMatchingService
from career_intelligence.portfolio_matching.deterministic_matcher import (
    DeterministicMatcher,
)
from career_intelligence.profile import CareerProfileService

__all__ = [
    "OFFLINE_DISCOVERY_FIXTURE_MARKER",
    "offline_discovery_fixture_marker",
    "workflow_runner_for_discovery",
]


def offline_discovery_fixture_marker(*, offline_fixtures: bool) -> str | None:
    """Marker injected into acquired raw_text when ``--offline-fixtures`` is set."""
    return OFFLINE_DISCOVERY_FIXTURE_MARKER if offline_fixtures else None


def workflow_runner_for_discovery(
    *,
    opportunities_dir: Path | None,
    checkpoint_dir: Path | None,
    profile_path: Path | None,
    offline_fixtures: bool,
) -> ApplicationWorkflowRunner:
    """Build ``ApplicationWorkflowRunner`` for discover (live or offline fixtures)."""
    profile_service = (
        CareerProfileService.from_path(profile_path)
        if profile_path
        else CareerProfileService()
    )
    profile = profile_service.load()
    opportunities = (
        OpportunityService.from_path(opportunities_dir)
        if opportunities_dir
        else OpportunityService()
    )
    store = JsonDirectoryCheckpointStore(
        checkpoint_dir or Path("data") / "workflow_runs"
    )

    if offline_fixtures:
        from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
        from career_intelligence.opportunity_assessment.fixture_assessor import (
            FixtureAssessor,
        )

        job_analysis = JobAnalysisService(FixtureExtractor())
        assessment = OpportunityAssessmentService(FixtureAssessor())
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit(
                "OPENAI_API_KEY is not set. Pass --offline-fixtures for smoke, "
                "or set the key for live FR-002/FR-003 analysis."
            )
        try:
            import truststore

            truststore.inject_into_ssl()
        except ImportError:
            pass
        from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor
        from career_intelligence.opportunity_assessment.openai_assessor import OpenAIAssessor

        job_analysis = JobAnalysisService(OpenAIJobExtractor())
        assessment = OpportunityAssessmentService(OpenAIAssessor())

    deps = WorkflowDependencies(
        profile=profile,
        job_analysis=job_analysis,
        assessment=assessment,
        portfolio_matching=PortfolioMatchingService(DeterministicMatcher()),
        application_strategy=ApplicationStrategyService(DeterministicStrategyPlanner()),
        store=store,
        opportunities=opportunities,
    )
    return ApplicationWorkflowRunner(deps)
