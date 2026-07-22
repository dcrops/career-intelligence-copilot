"""Unit tests for FixtureMatcher and canned portfolio-match fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from career_intelligence.job_analysis import JobAnalysisService
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
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.portfolio_matching import (
    PortfolioMatch,
    PortfolioMatchingError,
    PortfolioMatchingService,
)
from career_intelligence.portfolio_matching.fixture_matcher import FixtureMatcher
from career_intelligence.portfolio_matching.fixtures import (
    MARKER_PORTFOLIO_TIE,
    MATCH_FIXTURE_BUILDERS,
    match_ai_engineer,
    match_applied_ai,
    match_data_engineer,
    match_no_technologies,
    match_portfolio_tie,
    match_working_rights_insufficient,
)
from career_intelligence.profile import CareerProfile, CareerProfileService

_GOLDEN_PROJECT_IDS = {
    "operational-intelligence-copilot",
    "governance-document-rag",
    "payroll-diagnostics-engine",
    "public-holiday-entitlements",
}


def _golden_profile() -> CareerProfile:
    path = Path(__file__).parents[2] / "fixtures" / "golden" / "career_profile.yaml"
    return CareerProfileService.from_path(path).load()


def _job_analysis_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def _fixture_match_service() -> PortfolioMatchingService:
    return PortfolioMatchingService(FixtureMatcher())


def _tie_job_analysis() -> JobAnalysis:
    return JobAnalysis.model_validate(
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
                    "evidence": [{"excerpt": "Python required", "section": "requirements"}],
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


def test_all_match_fixture_builders_return_serialisable_payloads() -> None:
    for marker, builder in MATCH_FIXTURE_BUILDERS.items():
        payload = builder()
        assert isinstance(payload, dict)
        assert "job_analysis" not in payload
        assert "profile" not in payload
        assert "career_profile" not in payload
        assert "ranked_projects" in payload
        assert "unranked_project_ids" in payload
        assert "summary" in payload
        assert "insufficient_evidence" in payload
        assert marker


def test_known_marker_dispatch() -> None:
    matcher = FixtureMatcher()
    profile = _golden_profile()
    cases = [
        (posting_ai_engineer(), match_ai_engineer),
        (posting_applied_ai_engineer(), match_applied_ai),
        (posting_data_engineer(), match_data_engineer),
        (posting_no_technologies(), match_no_technologies),
        (posting_working_rights(), match_working_rights_insufficient),
    ]
    for posting, expected_builder in cases:
        job_analysis = _job_analysis_service().analyse(posting)
        assert matcher.match(job_analysis, profile) == expected_builder()


def test_portfolio_tie_marker_dispatch() -> None:
    payload = FixtureMatcher().match(_tie_job_analysis(), _golden_profile())
    assert payload == match_portfolio_tie()


def test_unknown_marker_raises_clear_error() -> None:
    job_analysis = JobAnalysis.model_validate(
        {
            "posting": {"raw_text": "No fixture marker present."},
            "role_family": {"family": "unknown"},
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": [],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
        }
    )

    with pytest.raises(PortfolioMatchingError, match="No fixture portfolio match"):
        FixtureMatcher().match(job_analysis, _golden_profile())


def test_payload_shape_and_project_coverage() -> None:
    for builder in MATCH_FIXTURE_BUILDERS.values():
        payload = builder()
        ranked_ids = {entry["project_id"] for entry in payload["ranked_projects"]}
        unranked_ids = set(payload["unranked_project_ids"])
        assert ranked_ids.isdisjoint(unranked_ids)
        assert ranked_ids | unranked_ids == _GOLDEN_PROJECT_IDS
        for entry in payload["ranked_projects"]:
            assert entry["factors"]
            for factor in entry["factors"]:
                assert factor["job_evidence"]
                assert factor["profile_evidence"]
                assert any(
                    ref["ref"] == f"project:{entry['project_id']}"
                    for ref in factor["profile_evidence"]
                )


def test_repeated_fixture_output_is_deterministic() -> None:
    matcher = FixtureMatcher()
    profile = _golden_profile()
    job_analysis = _job_analysis_service().analyse(posting_applied_ai_engineer())

    first = matcher.match(job_analysis, profile)
    second = matcher.match(job_analysis, profile)

    assert first == second
    assert first == match_applied_ai()


def test_no_embedded_trusted_inputs() -> None:
    for builder in MATCH_FIXTURE_BUILDERS.values():
        payload = builder()
        assert "job_analysis" not in payload
        assert "profile" not in payload
        assert "career_profile" not in payload


def test_service_validates_fixture_output_for_supported_markers() -> None:
    profile = _golden_profile()
    service = _fixture_match_service()
    cases = [
        posting_ai_engineer(),
        posting_applied_ai_engineer(),
        posting_data_engineer(),
        posting_no_technologies(),
        posting_working_rights(),
    ]
    for posting in cases:
        job_analysis = _job_analysis_service().analyse(posting)
        match = service.match(job_analysis, profile)
        assert isinstance(match, PortfolioMatch)
        assert match.job_analysis is job_analysis
        covered = {entry.project_id for entry in match.ranked_projects} | set(
            match.unranked_project_ids
        )
        assert covered == _GOLDEN_PROJECT_IDS


def test_service_validates_portfolio_tie_fixture() -> None:
    match = _fixture_match_service().match(_tie_job_analysis(), _golden_profile())

    assert [entry.project_id for entry in match.ranked_projects] == [
        "governance-document-rag",
        "operational-intelligence-copilot",
    ]
    assert match.ranked_projects[0].tie_group == match.ranked_projects[1].tie_group == 1
    assert match.ranked_projects[0].tie_break_reason is not None
    assert "project_id" in match.ranked_projects[0].tie_break_reason


def test_fixture_markers_are_documented_constants() -> None:
    assert MARKER_AI_ENGINEER in MATCH_FIXTURE_BUILDERS
    assert MARKER_APPLIED_AI in MATCH_FIXTURE_BUILDERS
    assert MARKER_DATA_ENGINEER in MATCH_FIXTURE_BUILDERS
    assert MARKER_NO_TECHNOLOGIES in MATCH_FIXTURE_BUILDERS
    assert MARKER_WORKING_RIGHTS in MATCH_FIXTURE_BUILDERS
    assert MARKER_PORTFOLIO_TIE in MATCH_FIXTURE_BUILDERS
