"""Functional acceptance tests for FR-004 Portfolio Matching (public service boundary)."""

from __future__ import annotations

from pathlib import Path

import career_intelligence.portfolio_matching as portfolio_matching_api
import pytest
from career_intelligence.job_analysis import JobAnalysis, JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_no_technologies,
    posting_working_rights,
)
from career_intelligence.job_analysis.models import JobAnalysis as JobAnalysisModel
from career_intelligence.portfolio_matching import (
    PortfolioMatch,
    PortfolioMatchingError,
    PortfolioMatchingService,
    PortfolioMatchingValidationError,
)
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.portfolio_matching.fixture_matcher import FixtureMatcher
from career_intelligence.portfolio_matching.fixtures import (
    MARKER_PORTFOLIO_TIE,
    match_ai_engineer,
)
from career_intelligence.portfolio_matching.matcher import PortfolioMatchPayload
from career_intelligence.profile import CareerProfile, CareerProfileService

_FORBIDDEN_OUTPUT_FIELD_NAMES = frozenset(
    {
        "tier",
        "platinum",
        "gold",
        "silver",
        "skip",
        "apply",
        "defer",
        "effort",
        "quota",
        "application_target",
        "interview_probability",
        "percentage",
        "score",
        "portfolio_fit",
        "technical_fit",
        "commercial_fit",
        "cv",
        "cover_letter",
        "outreach",
    }
)

_GOLDEN_PROJECT_IDS = {
    "operational-intelligence-copilot",
    "governance-document-rag",
    "payroll-diagnostics-engine",
    "public-holiday-entitlements",
}

_AI_LEAD_GROUP = {
    "governance-document-rag",
    "operational-intelligence-copilot",
}


def _collect_field_names(value: object) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            names.add(str(key).lower())
            names |= _collect_field_names(nested)
    elif isinstance(value, list):
        for item in value:
            names |= _collect_field_names(item)
    return names


def _job_analysis_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def _deterministic_service() -> PortfolioMatchingService:
    return PortfolioMatchingService(DeterministicMatcher())


def _fixture_service() -> PortfolioMatchingService:
    return PortfolioMatchingService(FixtureMatcher())


def _golden_profile(golden_profile_path: Path) -> CareerProfile:
    return CareerProfileService.from_path(golden_profile_path).load()


def _analyse(posting_builder: object) -> JobAnalysis:
    return _job_analysis_service().analyse(posting_builder())  # type: ignore[operator]


def _tie_job_analysis() -> JobAnalysis:
    return JobAnalysisModel.model_validate(
        {
            "posting": {
                "raw_text": f"{MARKER_PORTFOLIO_TIE}\nPython required for tie scenario.",
                "title": "Portfolio Tie Fixture",
            },
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


class _StaticPayloadMatcher:
    def __init__(self, payload: PortfolioMatchPayload) -> None:
        self._payload = payload

    def match(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> PortfolioMatchPayload:
        _ = job_analysis, profile
        return self._payload


class _FailingMatcher:
    def match(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> PortfolioMatchPayload:
        _ = job_analysis, profile
        raise PortfolioMatchingError("matcher failed")


def _assert_complete_coverage(match: PortfolioMatch, profile: CareerProfile) -> None:
    ranked_ids = {entry.project_id for entry in match.ranked_projects}
    unranked_ids = set(match.unranked_project_ids)
    profile_ids = {entry.id for entry in profile.projects}
    assert ranked_ids.isdisjoint(unranked_ids)
    assert ranked_ids | unranked_ids == profile_ids


def _assert_valid_evidence(match: PortfolioMatch) -> None:
    for entry in match.ranked_projects:
        assert entry.factors
        for factor in entry.factors:
            assert factor.job_evidence
            assert factor.profile_evidence
            assert any(
                ref.ref == f"project:{entry.project_id}"
                for ref in factor.profile_evidence
            )


def _assert_no_forbidden_output_fields(match: PortfolioMatch) -> None:
    field_names = _collect_field_names(match.model_dump(mode="json"))
    forbidden_present = field_names & _FORBIDDEN_OUTPUT_FIELD_NAMES
    assert not forbidden_present, f"forbidden fields present: {sorted(forbidden_present)}"


def test_public_api_exports_service_contract_only() -> None:
    assert hasattr(portfolio_matching_api, "PortfolioMatchingService")
    assert hasattr(portfolio_matching_api, "PortfolioMatch")
    assert not hasattr(portfolio_matching_api, "DeterministicMatcher")
    assert not hasattr(portfolio_matching_api, "FixtureMatcher")


def test_service_requires_an_explicit_matcher() -> None:
    with pytest.raises(TypeError):
        PortfolioMatchingService()  # type: ignore[call-arg]


def test_ai_engineer_ranking_through_public_service(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    match = _deterministic_service().match(job_analysis, profile)

    assert isinstance(match, PortfolioMatch)
    assert match.job_analysis is job_analysis
    assert match.insufficient_evidence is False
    assert match.ranked_projects[0].project_id == "governance-document-rag"
    assert "operational-intelligence-copilot" in [
        entry.project_id for entry in match.ranked_projects[:3]
    ]
    _assert_complete_coverage(match, profile)
    _assert_valid_evidence(match)
    _assert_no_forbidden_output_fields(match)


def test_applied_ai_ranking_through_public_service(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    match = _deterministic_service().match(job_analysis, profile)

    top_two = {entry.project_id for entry in match.ranked_projects[:2]}
    assert top_two == _AI_LEAD_GROUP
    assert match.ranked_projects[0].project_id == "operational-intelligence-copilot"
    _assert_valid_evidence(match)
    _assert_no_forbidden_output_fields(match)


def test_responsibility_only_ranking(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_no_technologies)
    profile = _golden_profile(golden_profile_path)

    match = _deterministic_service().match(job_analysis, profile)

    assert match.insufficient_evidence is False
    assert match.ranked_projects
    assert match.ranked_projects[0].project_id == "operational-intelligence-copilot"
    assert "public-holiday-entitlements" in match.unranked_project_ids
    assert all(
        factor.kind in {"responsibility_overlap", "demonstrates_overlap"}
        for entry in match.ranked_projects
        for factor in entry.factors
    )
    _assert_complete_coverage(match, profile)


def test_insufficient_evidence_behaviour(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_working_rights)
    profile = _golden_profile(golden_profile_path)

    match = _deterministic_service().match(job_analysis, profile)

    assert match.insufficient_evidence is True
    assert match.ranked_projects == []
    assert set(match.unranked_project_ids) == _GOLDEN_PROJECT_IDS
    _assert_no_forbidden_output_fields(match)


def test_tie_behaviour_through_fixture_composition(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)
    match = _fixture_service().match(_tie_job_analysis(), profile)

    assert [entry.project_id for entry in match.ranked_projects] == [
        "governance-document-rag",
        "operational-intelligence-copilot",
    ]
    assert match.ranked_projects[0].tie_group == match.ranked_projects[1].tie_group == 1
    assert match.ranked_projects[0].tie_break_reason is not None
    assert "project_id" in match.ranked_projects[0].tie_break_reason
    _assert_complete_coverage(match, profile)
    _assert_valid_evidence(match)


def test_caller_owned_job_analysis_is_bound(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    match = _deterministic_service().match(job_analysis, profile)

    assert match.job_analysis is job_analysis


@pytest.mark.parametrize("embedded_key", ["job_analysis", "profile", "career_profile"])
def test_embedded_caller_inputs_in_matcher_payload_are_rejected(
    golden_profile_path: Path,
    embedded_key: str,
) -> None:
    job_analysis = _analyse(posting_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    payload = dict(match_ai_engineer())
    payload[embedded_key] = {"injected": True}
    service = PortfolioMatchingService(_StaticPayloadMatcher(payload))

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        service.match(job_analysis, profile)

    assert any(error.loc == (embedded_key,) for error in raised.value.errors)


def test_fr004_does_not_depend_on_opportunity_assessment(
    golden_profile_path: Path,
) -> None:
    """FR-004 public flow uses Profile + JobAnalysis only — no OpportunityAssessment."""
    import career_intelligence.opportunity_assessment as opportunity_assessment_api

    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    match = _deterministic_service().match(job_analysis, profile)

    dumped = match.model_dump(mode="json")
    assert "portfolio_fit" not in dumped
    assert "technical_fit" not in dumped
    assert "commercial_fit" not in dumped
    assert "OpportunityAssessment" not in dir(portfolio_matching_api)
    # Sibling package exists but is not required as an input to FR-004.
    assert hasattr(opportunity_assessment_api, "OpportunityAssessment")
    assert not isinstance(match, opportunity_assessment_api.OpportunityAssessment)


def test_fixture_matcher_supports_service_composition_isolation(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    match = _fixture_service().match(job_analysis, profile)

    assert match.ranked_projects[0].project_id == "governance-document-rag"
    assert match.job_analysis is job_analysis
    _assert_complete_coverage(match, profile)
    _assert_valid_evidence(match)


def test_inputs_are_not_mutated(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    before_job = job_analysis.model_dump(mode="json")
    before_profile = profile.model_dump(mode="json")

    _deterministic_service().match(job_analysis, profile)

    assert job_analysis.model_dump(mode="json") == before_job
    assert profile.model_dump(mode="json") == before_profile


def test_repeated_match_is_deterministic(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    service = _deterministic_service()

    first = service.match(job_analysis, profile).model_dump(mode="json")
    second = service.match(job_analysis, profile).model_dump(mode="json")

    assert first == second


def test_matcher_errors_propagate(golden_profile_path: Path) -> None:
    service = PortfolioMatchingService(_FailingMatcher())

    with pytest.raises(PortfolioMatchingError, match="matcher failed"):
        service.match(_analyse(posting_ai_engineer), _golden_profile(golden_profile_path))


def test_schema_validation_failures_raise_validation_error(
    golden_profile_path: Path,
) -> None:
    service = PortfolioMatchingService(
        _StaticPayloadMatcher(
            {
                "ranked_projects": [],
                "unranked_project_ids": [],
                "insufficient_evidence": False,
            }
        )
    )

    with pytest.raises(PortfolioMatchingValidationError):
        service.match(
            _analyse(posting_ai_engineer),
            _golden_profile(golden_profile_path),
        )
