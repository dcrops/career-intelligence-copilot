"""Unit tests for the FR-004 portfolio-matching domain contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.portfolio_matching.models import (
    JobEvidenceRef,
    PortfolioMatch,
    ProfileEvidenceRef,
    RankedPortfolioProject,
    RankingFactor,
)


def _posting(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "raw_text": "Senior AI Engineer. Python required. Hybrid Melbourne.",
        "title": "Senior AI Engineer",
        "company": "Example AI Co",
    }
    payload.update(overrides)
    return payload


def _job_analysis(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "posting": _posting(),
        "role_family": {
            "family": "ai_engineering",
            "evidence": [{"excerpt": "Senior AI Engineer", "section": "title"}],
        },
        "seniority": {
            "level": "senior",
            "ambiguous": False,
            "evidence": [{"excerpt": "Senior AI Engineer", "section": "title"}],
        },
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [{"excerpt": "Python required", "section": "requirements"}],
            }
        ],
        "responsibilities": [
            {
                "description": "Build LLM applications",
                "evidence": [
                    {
                        "excerpt": "Build LLM applications",
                        "section": "responsibilities",
                    }
                ],
            }
        ],
        "compensation": {"clarity": "unstated"},
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [{"excerpt": "Hybrid Melbourne", "section": "location"}],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "evidence": [{"excerpt": "Hybrid Melbourne", "section": "location"}],
        },
        "employment": {},
        "experience_requirements": [],
    }
    payload.update(overrides)
    return payload


def _factor(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": "required_technology",
        "summary": "Project uses required Python.",
        "job_evidence": [
            {
                "source": "technology",
                "item_index": 0,
                "name": "Python",
                "excerpt": "Python required",
            }
        ],
        "profile_evidence": [
            {"source": "project", "ref": "project:example-project"}
        ],
    }
    payload.update(overrides)
    return payload


def _ranked_project(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "rank": 1,
        "project_id": "example-project",
        "rationale": "Strongest technology overlap for this role.",
        "factors": [_factor()],
    }
    payload.update(overrides)
    return payload


def _valid_match(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "job_analysis": _job_analysis(),
        "ranked_projects": [_ranked_project()],
        "unranked_project_ids": [],
        "summary": "Lead with example-project based on required Python overlap.",
        "insufficient_evidence": False,
    }
    payload.update(overrides)
    return payload


def test_valid_portfolio_match_parses() -> None:
    match = PortfolioMatch.model_validate(_valid_match())

    assert match.ranked_projects[0].rank == 1
    assert match.ranked_projects[0].project_id == "example-project"
    assert match.summary.startswith("Lead with")
    assert match.insufficient_evidence is False
    assert isinstance(match.job_analysis, JobAnalysis)


def test_empty_ranked_list_is_allowed_for_insufficient_evidence() -> None:
    match = PortfolioMatch.model_validate(
        _valid_match(
            ranked_projects=[],
            unranked_project_ids=["example-project"],
            summary="No usable job signals for portfolio ranking.",
            insufficient_evidence=True,
        )
    )

    assert match.ranked_projects == []
    assert match.unranked_project_ids == ["example-project"]
    assert match.insufficient_evidence is True


def test_technology_job_evidence_requires_item_index() -> None:
    with pytest.raises(ValidationError):
        JobEvidenceRef.model_validate({"source": "technology", "name": "Python"})


def test_ranking_factor_requires_job_and_profile_evidence() -> None:
    with pytest.raises(ValidationError):
        RankingFactor.model_validate(
            {
                "kind": "required_technology",
                "summary": "Missing evidence.",
                "job_evidence": [],
                "profile_evidence": [
                    {"source": "project", "ref": "project:example-project"}
                ],
            }
        )

    with pytest.raises(ValidationError):
        RankingFactor.model_validate(
            {
                "kind": "required_technology",
                "summary": "Missing evidence.",
                "job_evidence": [{"source": "technology", "item_index": 0}],
                "profile_evidence": [],
            }
        )


def test_profile_evidence_source_is_project_only() -> None:
    with pytest.raises(ValidationError):
        ProfileEvidenceRef.model_validate(
            {"source": "skill", "ref": "skill:Python"}
        )


def test_tie_group_requires_tie_break_reason() -> None:
    with pytest.raises(ValidationError):
        RankedPortfolioProject.model_validate(
            _ranked_project(tie_group=1, tie_break_reason=None)
        )


def test_tie_break_reason_requires_tie_group() -> None:
    with pytest.raises(ValidationError):
        RankedPortfolioProject.model_validate(
            _ranked_project(tie_break_reason="stable project_id order")
        )


def test_valid_tie_fields_parse() -> None:
    project = RankedPortfolioProject.model_validate(
        _ranked_project(
            tie_group=1,
            tie_break_reason="Equal primary signals; ordered by project_id.",
        )
    )

    assert project.tie_group == 1
    assert project.tie_break_reason is not None


def test_duplicate_ranked_project_ids_are_rejected() -> None:
    with pytest.raises(ValidationError):
        PortfolioMatch.model_validate(
            _valid_match(
                ranked_projects=[
                    _ranked_project(rank=1),
                    _ranked_project(rank=2),
                ]
            )
        )


def test_project_cannot_be_both_ranked_and_unranked() -> None:
    with pytest.raises(ValidationError):
        PortfolioMatch.model_validate(
            _valid_match(unranked_project_ids=["example-project"])
        )


def test_ranks_must_be_contiguous_and_ordered() -> None:
    second = _ranked_project(
        rank=2,
        project_id="other-project",
        factors=[
            _factor(
                profile_evidence=[
                    {"source": "project", "ref": "project:other-project"}
                ]
            )
        ],
    )

    with pytest.raises(ValidationError):
        PortfolioMatch.model_validate(
            _valid_match(
                ranked_projects=[
                    _ranked_project(rank=1),
                    {**second, "rank": 3},
                ],
                unranked_project_ids=[],
            )
        )

    with pytest.raises(ValidationError):
        PortfolioMatch.model_validate(
            _valid_match(
                ranked_projects=[second, _ranked_project(rank=1)],
            )
        )


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        PortfolioMatch.model_validate(_valid_match(match_score=87))

    with pytest.raises(ValidationError):
        RankedPortfolioProject.model_validate(_ranked_project(percentage=0.9))
