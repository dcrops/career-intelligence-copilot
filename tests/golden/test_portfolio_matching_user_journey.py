"""Golden journeys: CareerProfile → JobAnalysis → PortfolioMatch (offline).

Proves FR-001 / FR-002 / FR-004 service composition through real public boundaries
with deterministic extractors and matchers. Not a duplicate of the FR-004
functional acceptance suite.
"""

from __future__ import annotations

from pathlib import Path

from career_intelligence.job_analysis import JobAnalysis, JobAnalysisService, JobPosting
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER,
    MARKER_APPLIED_AI,
    MARKER_NO_TECHNOLOGIES,
    MARKER_WORKING_RIGHTS,
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_no_technologies,
    posting_working_rights,
)
from career_intelligence.portfolio_matching import PortfolioMatch, PortfolioMatchingService
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.portfolio_matching.fixture_matcher import FixtureMatcher
from career_intelligence.portfolio_matching.fixtures import MARKER_PORTFOLIO_TIE
from career_intelligence.profile import CareerProfile, CareerProfileService

_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "tier",
        "platinum",
        "gold",
        "silver",
        "skip",
        "apply",
        "defer",
        "quota",
        "obligation",
        "effort",
        "interview_probability",
        "jobseeker",
        "portfolio_fit",
        "technical_fit",
        "commercial_fit",
        "percentage",
        "outreach",
    }
)

_AI_LEAD_GROUP = {
    "governance-document-rag",
    "operational-intelligence-copilot",
}


def _golden_profile(golden_profile_path: Path) -> CareerProfile:
    return CareerProfileService.from_path(golden_profile_path).load()


def _job_analysis_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def _deterministic_match_service() -> PortfolioMatchingService:
    return PortfolioMatchingService(DeterministicMatcher())


def _fixture_match_service() -> PortfolioMatchingService:
    return PortfolioMatchingService(FixtureMatcher())


def _run_deterministic_journey(
    posting: JobPosting,
    profile: CareerProfile,
) -> tuple[JobAnalysis, PortfolioMatch]:
    job_analysis = _job_analysis_service().analyse(posting)
    match = _deterministic_match_service().match(job_analysis, profile)
    return job_analysis, match


def _assert_portfolio_match(
    match: PortfolioMatch,
    *,
    job_analysis: JobAnalysis,
    profile: CareerProfile,
) -> None:
    assert isinstance(match, PortfolioMatch)
    assert match.job_analysis is job_analysis
    assert match.summary

    ranked_ids = {entry.project_id for entry in match.ranked_projects}
    unranked_ids = set(match.unranked_project_ids)
    profile_ids = {entry.id for entry in profile.projects}
    assert ranked_ids.isdisjoint(unranked_ids)
    assert ranked_ids | unranked_ids == profile_ids

    for entry in match.ranked_projects:
        assert entry.factors
        for factor in entry.factors:
            assert factor.job_evidence
            assert factor.profile_evidence
            assert any(
                ref.ref == f"project:{entry.project_id}"
                for ref in factor.profile_evidence
            )

    dumped = match.model_dump(mode="json")
    serialised = str(dumped).lower()
    for token in _FORBIDDEN_FIELD_NAMES:
        assert token not in serialised
    assert "job_analysis" in dumped
    assert "profile" not in dumped
    assert "career_profile" not in dumped
    assert "portfolio_fit" not in dumped


def test_profile_loads_through_career_profile_service(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)

    assert isinstance(profile, CareerProfile)
    assert profile.identity.target_role
    assert len(profile.projects) == 4


def test_ai_engineer_portfolio_matching_journey(golden_profile_path: Path) -> None:
    """Senior AI Engineer: Profile → JobAnalysis → PortfolioMatch."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_ai_engineer()
    assert MARKER_AI_ENGINEER in posting.raw_text

    job_analysis, match = _run_deterministic_journey(posting, profile)

    assert job_analysis.posting is posting
    assert job_analysis.role_family.family == "ai_engineering"
    assert {tech.name for tech in job_analysis.technologies} >= {"Python", "LangChain"}

    _assert_portfolio_match(match, job_analysis=job_analysis, profile=profile)
    assert match.insufficient_evidence is False
    assert match.ranked_projects[0].project_id == "governance-document-rag"
    assert "preferred_technology" in {
        factor.kind for factor in match.ranked_projects[0].factors
    }
    assert "operational-intelligence-copilot" in [
        entry.project_id for entry in match.ranked_projects
    ]

    second = _deterministic_match_service().match(job_analysis, profile)
    assert second.model_dump(mode="json") == match.model_dump(mode="json")


def test_applied_ai_portfolio_matching_journey(golden_profile_path: Path) -> None:
    """Applied AI Engineer: ops and RAG form the lead group."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_applied_ai_engineer()
    assert MARKER_APPLIED_AI in posting.raw_text

    job_analysis, match = _run_deterministic_journey(posting, profile)

    assert {tech.name for tech in job_analysis.technologies} >= {"Python", "FastAPI"}
    _assert_portfolio_match(match, job_analysis=job_analysis, profile=profile)
    assert {entry.project_id for entry in match.ranked_projects[:2]} == _AI_LEAD_GROUP
    assert match.ranked_projects[0].project_id == "operational-intelligence-copilot"


def test_responsibility_only_portfolio_matching_journey(
    golden_profile_path: Path,
) -> None:
    """No named technologies: ranking still proceeds from responsibilities."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_no_technologies()
    assert MARKER_NO_TECHNOLOGIES in posting.raw_text

    job_analysis, match = _run_deterministic_journey(posting, profile)

    assert job_analysis.technologies == []
    assert job_analysis.responsibilities
    _assert_portfolio_match(match, job_analysis=job_analysis, profile=profile)
    assert match.insufficient_evidence is False
    assert match.ranked_projects[0].project_id == "operational-intelligence-copilot"
    assert "public-holiday-entitlements" in match.unranked_project_ids


def test_insufficient_evidence_portfolio_matching_journey(
    golden_profile_path: Path,
) -> None:
    """Working-rights sparse advert: no usable ranking signals."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_working_rights()
    assert MARKER_WORKING_RIGHTS in posting.raw_text

    job_analysis, match = _run_deterministic_journey(posting, profile)

    assert job_analysis.technologies == []
    assert job_analysis.responsibilities == []
    _assert_portfolio_match(match, job_analysis=job_analysis, profile=profile)
    assert match.insufficient_evidence is True
    assert match.ranked_projects == []


def test_tie_behaviour_via_fixture_matcher_composition(
    golden_profile_path: Path,
) -> None:
    """FixtureMatcher isolates service composition for an explicit tie contract."""
    profile = _golden_profile(golden_profile_path)
    posting = JobPosting(
        raw_text=f"{MARKER_PORTFOLIO_TIE}\nPython required for tie scenario.",
        title="Portfolio Tie Fixture",
    )
    # Synthetic analysis aligned to the canned tie fixture evidence indexes.
    job_analysis = JobAnalysis.model_validate(
        {
            "posting": posting.model_dump(mode="python"),
            "role_family": {"family": "unknown"},
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": [
                {
                    "name": "Python",
                    "level": "required",
                    "evidence": [
                        {"excerpt": "Python required", "section": "requirements"}
                    ],
                }
            ],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "location": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
            "employment": {},
            "experience_requirements": [],
        }
    )

    match = _fixture_match_service().match(job_analysis, profile)

    _assert_portfolio_match(match, job_analysis=job_analysis, profile=profile)
    assert [entry.project_id for entry in match.ranked_projects] == [
        "governance-document-rag",
        "operational-intelligence-copilot",
    ]
    assert match.ranked_projects[0].tie_group == match.ranked_projects[1].tie_group == 1
    assert match.ranked_projects[0].tie_break_reason is not None


def test_fr004_journey_does_not_require_opportunity_assessment(
    golden_profile_path: Path,
) -> None:
    profile = _golden_profile(golden_profile_path)
    job_analysis, match = _run_deterministic_journey(
        posting_applied_ai_engineer(),
        profile,
    )

    _assert_portfolio_match(match, job_analysis=job_analysis, profile=profile)
    dumped = match.model_dump(mode="json")
    assert "portfolio_fit" not in dumped
    assert "OpportunityAssessment" not in type(match).__name__
