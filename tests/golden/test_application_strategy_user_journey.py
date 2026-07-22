"""Golden journeys: CareerProfile → … → ApplicationStrategy (offline).

Proves FR-001 through FR-005 service composition through real public boundaries.
Fixture planners/matchers/assessors validate contract composition; deterministic
planners assert production recommendation behaviour where noted.
"""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_strategy import (
    ApplicationStrategy,
    ApplicationStrategyService,
    SearchOperatingContext,
)
from career_intelligence.application_strategy.deterministic_planner import (
    DeterministicStrategyPlanner,
)
from career_intelligence.application_strategy.fixture_planner import FixtureStrategyPlanner
from career_intelligence.job_analysis import JobAnalysis, JobAnalysisService, JobPosting
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER,
    MARKER_APPLIED_AI,
    MARKER_DATA_ENGINEER,
    MARKER_NO_TECHNOLOGIES,
    MARKER_WORKING_RIGHTS,
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_data_engineer,
    posting_no_technologies,
    posting_working_rights,
)
from career_intelligence.opportunity_assessment import (
    OpportunityAssessment,
    OpportunityAssessmentService,
)
from career_intelligence.opportunity_assessment.fixture_assessor import FixtureAssessor
from career_intelligence.portfolio_matching import PortfolioMatch, PortfolioMatchingService
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.portfolio_matching.fixture_matcher import FixtureMatcher
from career_intelligence.profile import CareerProfile, CareerProfileService

_FORBIDDEN_SERIALISED_TOKENS = frozenset(
    {
        "cover_letter_body",
        "cv_body",
        "outreach",
        "submit_application",
        "interview_probability",
        "percentage_score",
        "apply_decision",
        "browser_automation",
    }
)


def _golden_profile(golden_profile_path: Path) -> CareerProfile:
    return CareerProfileService.from_path(golden_profile_path).load()


def _job_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def _assessment_service() -> OpportunityAssessmentService:
    return OpportunityAssessmentService(FixtureAssessor())


def _fixture_match_service() -> PortfolioMatchingService:
    return PortfolioMatchingService(FixtureMatcher())


def _deterministic_match_service() -> PortfolioMatchingService:
    return PortfolioMatchingService(DeterministicMatcher())


def _fixture_strategy_service() -> ApplicationStrategyService:
    return ApplicationStrategyService(FixtureStrategyPlanner())


def _deterministic_strategy_service() -> ApplicationStrategyService:
    return ApplicationStrategyService(DeterministicStrategyPlanner())


def _run_fixture_composition(
    posting: JobPosting,
    profile: CareerProfile,
    *,
    operating_context: SearchOperatingContext | None = None,
) -> tuple[JobAnalysis, OpportunityAssessment, PortfolioMatch, ApplicationStrategy]:
    job_analysis = _job_service().analyse(posting)
    assessment = _assessment_service().assess(job_analysis, profile)
    match = _fixture_match_service().match(job_analysis, profile)
    strategy = _fixture_strategy_service().plan(
        assessment,
        match,
        profile,
        operating_context=operating_context,
    )
    return job_analysis, assessment, match, strategy


def _run_production_strategy(
    posting: JobPosting,
    profile: CareerProfile,
    *,
    operating_context: SearchOperatingContext | None = None,
) -> tuple[JobAnalysis, OpportunityAssessment, PortfolioMatch, ApplicationStrategy]:
    job_analysis = _job_service().analyse(posting)
    assessment = _assessment_service().assess(job_analysis, profile)
    match = _deterministic_match_service().match(job_analysis, profile)
    strategy = _deterministic_strategy_service().plan(
        assessment,
        match,
        profile,
        operating_context=operating_context,
    )
    return job_analysis, assessment, match, strategy


def _assert_strategy_artifact(
    strategy: ApplicationStrategy,
    *,
    job_analysis: JobAnalysis,
) -> None:
    assert isinstance(strategy, ApplicationStrategy)
    assert strategy.job_analysis.posting.raw_text == job_analysis.posting.raw_text
    assert strategy.owner_review_required is True
    assert strategy.summary
    assert strategy.reasons
    assert strategy.next_actions
    assert all(action.kind.startswith("consider_") for action in strategy.next_actions)

    dumped = strategy.model_dump(mode="json")
    assert "opportunity_assessment" not in dumped
    assert "portfolio_match" not in dumped
    assert "career_profile" not in dumped
    assert "profile" not in dumped
    assert "job_analysis" in dumped

    serialised = str(dumped).lower()
    for token in _FORBIDDEN_SERIALISED_TOKENS:
        assert token not in serialised


def test_profile_loads_through_career_profile_service(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    assert isinstance(profile, CareerProfile)
    assert profile.identity.target_role
    assert len(profile.projects) == 4


def test_strong_applied_ai_fixture_composition_journey(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    posting = posting_applied_ai_engineer()
    assert MARKER_APPLIED_AI in posting.raw_text

    job_analysis, assessment, match, strategy = _run_fixture_composition(
        posting, profile
    )

    assert assessment.technical_fit.judgment == "strong"
    assert match.ranked_projects
    _assert_strategy_artifact(strategy, job_analysis=job_analysis)
    assert strategy.pursuit_posture == "prioritise"
    assert strategy.application_tier == "platinum"
    assert strategy.portfolio_emphasis
    assert strategy.portfolio_emphasis[0].project_id == "operational-intelligence-copilot"


def test_strong_applied_ai_production_policy_journey(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    posting = posting_applied_ai_engineer()

    job_analysis, _assessment, match, strategy = _run_production_strategy(
        posting, profile
    )

    _assert_strategy_artifact(strategy, job_analysis=job_analysis)
    # Fixture applied-AI posting is Sydney hybrid: soft location mismatch reduces
    # an otherwise strong AI opportunity from prioritise/platinum to pursue/gold.
    assert strategy.pursuit_posture in {"prioritise", "pursue"}
    assert strategy.application_tier in {"platinum", "gold"}
    assert strategy.effort_level in {"full", "targeted"}
    assert strategy.practical_value == "career_priority"
    assert match.ranked_projects
    assert strategy.portfolio_emphasis
    assert strategy.pursuit_posture != "do_not_prioritise"

    second = _deterministic_strategy_service().plan(
        _assessment_service().assess(job_analysis, profile),
        match,
        profile,
    )
    assert second.model_dump(mode="json") == strategy.model_dump(mode="json")


def test_ai_engineer_portfolio_emphasis_fixture_journey(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    posting = posting_ai_engineer()
    assert MARKER_AI_ENGINEER in posting.raw_text

    job_analysis, _assessment, match, strategy = _run_fixture_composition(
        posting, profile
    )

    _assert_strategy_artifact(strategy, job_analysis=job_analysis)
    assert strategy.pursuit_posture == "pursue"
    assert strategy.application_tier == "gold"
    assert strategy.portfolio_emphasis
    assert strategy.portfolio_emphasis[0].project_id == "governance-document-rag"
    assert match.ranked_projects[0].project_id == "governance-document-rag"


def test_data_engineer_outside_target_fixture_and_production(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    posting = posting_data_engineer()
    assert MARKER_DATA_ENGINEER in posting.raw_text

    _job, _assessment, _match, fixture_strategy = _run_fixture_composition(
        posting, profile
    )
    assert fixture_strategy.pursuit_posture == "do_not_prioritise"
    assert fixture_strategy.application_tier == "bronze"
    assert "never apply" not in fixture_strategy.summary.casefold()

    job_analysis, _assessment2, _match2, production_strategy = _run_production_strategy(
        posting, profile
    )
    _assert_strategy_artifact(production_strategy, job_analysis=job_analysis)
    assert production_strategy.pursuit_posture == "do_not_prioritise"
    assert production_strategy.application_tier == "bronze"
    assert production_strategy.effort_level == "none"


def test_working_rights_insufficient_information_journey(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    posting = posting_working_rights()
    assert MARKER_WORKING_RIGHTS in posting.raw_text

    job_analysis, assessment, match, fixture_strategy = _run_fixture_composition(
        posting, profile
    )
    assert assessment.technical_fit.judgment == "unknown"
    assert match.insufficient_evidence is True
    _assert_strategy_artifact(fixture_strategy, job_analysis=job_analysis)
    assert fixture_strategy.pursuit_posture == "insufficient_information"
    assert fixture_strategy.portfolio_emphasis == []
    assert any(
        action.kind == "consider_verifying_working_rights"
        for action in fixture_strategy.next_actions
    )

    _job2, _assessment2, _match2, production_strategy = _run_production_strategy(
        posting, profile
    )
    assert production_strategy.pursuit_posture == "insufficient_information"
    assert production_strategy.insufficient_information is True


def test_volume_enabled_low_effort_journey(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    posting = posting_data_engineer()
    context = SearchOperatingContext(volume_applications_enabled=True)

    job_analysis, _assessment, _match, fixture_strategy = _run_fixture_composition(
        posting,
        profile,
        operating_context=context,
    )
    _assert_strategy_artifact(fixture_strategy, job_analysis=job_analysis)
    assert fixture_strategy.pursuit_posture == "low_effort_submit"
    assert fixture_strategy.application_tier == "silver"
    assert fixture_strategy.practical_value == "volume_obligation"

    _job2, _assessment2, _match2, production_strategy = _run_production_strategy(
        posting,
        profile,
        operating_context=context,
    )
    assert production_strategy.pursuit_posture == "low_effort_submit"
    assert production_strategy.practical_value == "volume_obligation"
    assert any(
        action.kind == "consider_low_effort_application"
        for action in production_strategy.next_actions
    )


def test_no_technologies_portfolio_emphasis_present_journey(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    posting = posting_no_technologies()
    assert MARKER_NO_TECHNOLOGIES in posting.raw_text

    job_analysis, _assessment, match, strategy = _run_fixture_composition(
        posting, profile
    )

    _assert_strategy_artifact(strategy, job_analysis=job_analysis)
    assert match.ranked_projects
    assert strategy.portfolio_emphasis
    assert strategy.portfolio_emphasis[0].project_id == "operational-intelligence-copilot"


def test_strategy_does_not_embed_upstream_artifacts(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    _job, assessment, match, strategy = _run_fixture_composition(
        posting_applied_ai_engineer(),
        profile,
    )
    dumped = strategy.model_dump(mode="json")
    assert "opportunity_assessment" not in dumped
    assert "portfolio_match" not in dumped
    assert dumped["job_analysis"]["posting"]["raw_text"] == assessment.job_analysis.posting.raw_text
    assert match.ranked_projects
    assert "ranked_projects" not in dumped
