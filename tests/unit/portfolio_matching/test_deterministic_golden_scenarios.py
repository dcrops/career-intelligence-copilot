"""Golden-profile scenario coverage for DeterministicMatcher product behaviour."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_data_engineer,
    posting_no_technologies,
    posting_working_rights,
)
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.portfolio_matching.service import PortfolioMatchingService
from career_intelligence.profile import CareerProfile, CareerProfileService

_AI_LEAD_GROUP = {
    "governance-document-rag",
    "operational-intelligence-copilot",
}


def _golden_profile() -> CareerProfile:
    path = Path(__file__).parents[2] / "fixtures" / "golden" / "career_profile.yaml"
    return CareerProfileService.from_path(path).load()


def _analyse(posting_builder: object):
    return JobAnalysisService(FixtureExtractor()).analyse(posting_builder())  # type: ignore[operator]


def _rank_ids(match) -> list[str]:
    return [entry.project_id for entry in match.ranked_projects]


def test_ai_engineer_ranks_rag_and_ops_strongly() -> None:
    profile = _golden_profile()
    match = PortfolioMatchingService(DeterministicMatcher()).match(
        _analyse(posting_ai_engineer),
        profile,
    )

    assert match.insufficient_evidence is False
    assert _rank_ids(match)[0] == "governance-document-rag"
    assert "operational-intelligence-copilot" in _rank_ids(match)[:3]
    lead = match.ranked_projects[0]
    assert "preferred_technology" in {factor.kind for factor in lead.factors}
    assert any(
        ref.ref == "project:governance-document-rag"
        for factor in lead.factors
        for ref in factor.profile_evidence
    )


def test_applied_ai_ranks_ops_and_rag_in_top_group() -> None:
    match = PortfolioMatchingService(DeterministicMatcher()).match(
        _analyse(posting_applied_ai_engineer),
        _golden_profile(),
    )

    top_two = set(_rank_ids(match)[:2])
    assert top_two == _AI_LEAD_GROUP
    assert match.ranked_projects[0].project_id == "operational-intelligence-copilot"
    assert any(
        factor.kind == "demonstrates_overlap"
        for factor in match.ranked_projects[0].factors
    )


def test_data_engineer_does_not_uniquely_prefer_rag() -> None:
    match = PortfolioMatchingService(DeterministicMatcher()).match(
        _analyse(posting_data_engineer),
        _golden_profile(),
    )

    assert match.insufficient_evidence is False
    assert len(match.ranked_projects) == 4
    tie_groups = {entry.tie_group for entry in match.ranked_projects}
    assert tie_groups == {1}
    # With only shared Python hits, ordering is stable project_id — not RAG preference.
    assert _rank_ids(match) == sorted(_rank_ids(match))
    lead_kinds = {factor.kind for factor in match.ranked_projects[0].factors}
    assert lead_kinds == {"required_technology"}
    assert "preferred_technology" not in lead_kinds


def test_no_technologies_uses_responsibility_only_ranking() -> None:
    match = PortfolioMatchingService(DeterministicMatcher()).match(
        _analyse(posting_no_technologies),
        _golden_profile(),
    )

    assert match.insufficient_evidence is False
    assert match.ranked_projects
    assert _rank_ids(match)[0] == "operational-intelligence-copilot"
    assert "public-holiday-entitlements" in match.unranked_project_ids
    assert all(
        factor.kind in {"responsibility_overlap", "demonstrates_overlap"}
        for entry in match.ranked_projects
        for factor in entry.factors
    )


def test_working_rights_sparse_job_is_insufficient_evidence() -> None:
    match = PortfolioMatchingService(DeterministicMatcher()).match(
        _analyse(posting_working_rights),
        _golden_profile(),
    )

    assert match.insufficient_evidence is True
    assert match.ranked_projects == []
    assert set(match.unranked_project_ids) == {
        "operational-intelligence-copilot",
        "governance-document-rag",
        "payroll-diagnostics-engine",
        "public-holiday-entitlements",
    }


def test_zero_overlap_projects_are_unranked_on_no_tech_scenario() -> None:
    match = PortfolioMatchingService(DeterministicMatcher()).match(
        _analyse(posting_no_technologies),
        _golden_profile(),
    )

    ranked = set(_rank_ids(match))
    unranked = set(match.unranked_project_ids)
    assert ranked.isdisjoint(unranked)
    assert ranked | unranked == {
        "operational-intelligence-copilot",
        "governance-document-rag",
        "payroll-diagnostics-engine",
        "public-holiday-entitlements",
    }
    assert unranked  # at least one project lacks usable overlap


def test_evidence_factors_resolve_through_service_for_ai_fixtures() -> None:
    service = PortfolioMatchingService(DeterministicMatcher())
    profile = _golden_profile()
    for posting_builder in (posting_ai_engineer, posting_applied_ai_engineer):
        match = service.match(_analyse(posting_builder), profile)
        for entry in match.ranked_projects:
            for factor in entry.factors:
                assert factor.job_evidence
                assert factor.profile_evidence
                assert any(
                    ref.ref == f"project:{entry.project_id}"
                    for ref in factor.profile_evidence
                )
