"""Unit tests for portfolio-matching referential integrity checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.portfolio_matching.errors import PortfolioMatchingValidationError
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.portfolio_matching.refs import validate_references
from career_intelligence.profile import CareerProfile, CareerProfileService


def _minimal_profile() -> CareerProfile:
    path = Path(__file__).parents[2] / "fixtures" / "minimal_valid_profile.yaml"
    return CareerProfileService.from_path(path).load()


def _job_analysis(**overrides: object) -> JobAnalysis:
    payload: dict[str, object] = {
        "posting": {
            "raw_text": "Senior AI Engineer. Python required. Build LLM apps.",
            "title": "Senior AI Engineer",
        },
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
            },
            {
                "name": "LangChain",
                "level": "preferred",
                "evidence": [
                    {"excerpt": "LangChain preferred", "section": "requirements"}
                ],
            },
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
        "location": {"clarity": "unstated"},
        "work_arrangement": {"arrangement": "unspecified"},
        "employment": {},
        "experience_requirements": [],
    }
    payload.update(overrides)
    return JobAnalysis.model_validate(payload)


def _valid_match(**overrides: object) -> PortfolioMatch:
    payload: dict[str, object] = {
        "job_analysis": _job_analysis(),
        "ranked_projects": [
            {
                "rank": 1,
                "project_id": "example-project",
                "rationale": "Required Python overlap.",
                "factors": [
                    {
                        "kind": "required_technology",
                        "summary": "Project uses required Python.",
                        "job_evidence": [
                            {
                                "source": "technology",
                                "item_index": 0,
                                "name": "Python",
                            }
                        ],
                        "profile_evidence": [
                            {
                                "source": "project",
                                "ref": "project:example-project",
                            }
                        ],
                    }
                ],
            }
        ],
        "unranked_project_ids": [],
        "summary": "Lead with example-project.",
        "insufficient_evidence": False,
    }
    payload.update(overrides)
    return PortfolioMatch.model_validate(payload)


def test_valid_references_pass() -> None:
    validate_references(_valid_match(), _minimal_profile())


def test_missing_project_coverage_fails() -> None:
    match = _valid_match(
        ranked_projects=[],
        unranked_project_ids=[],
        summary="Nothing ranked or unranked.",
        insufficient_evidence=True,
    )

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        validate_references(match, _minimal_profile())

    assert any("missing project id" in error.msg for error in raised.value.errors)


def test_unknown_ranked_project_id_fails() -> None:
    match = PortfolioMatch.model_validate(
        {
            "job_analysis": _job_analysis(),
            "ranked_projects": [
                {
                    "rank": 1,
                    "project_id": "not-in-profile",
                    "rationale": "Unknown project.",
                    "factors": [
                        {
                            "kind": "required_technology",
                            "summary": "Claims unknown project.",
                            "job_evidence": [
                                {"source": "technology", "item_index": 0}
                            ],
                            "profile_evidence": [
                                {
                                    "source": "project",
                                    "ref": "project:not-in-profile",
                                }
                            ],
                        }
                    ],
                }
            ],
            "unranked_project_ids": ["example-project"],
            "summary": "Includes unknown project.",
            "insufficient_evidence": False,
        }
    )

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        validate_references(match, _minimal_profile())

    assert any("absent from the bound career profile" in error.msg for error in raised.value.errors)


def test_factor_must_cite_own_project_ref() -> None:
    golden_path = (
        Path(__file__).parents[2] / "fixtures" / "golden" / "career_profile.yaml"
    )
    profile = CareerProfileService.from_path(golden_path).load()
    match = PortfolioMatch.model_validate(
        {
            "job_analysis": _job_analysis(),
            "ranked_projects": [
                {
                    "rank": 1,
                    "project_id": "governance-document-rag",
                    "rationale": "Wrong profile citation.",
                    "factors": [
                        {
                            "kind": "required_technology",
                            "summary": "Cites a different project.",
                            "job_evidence": [
                                {"source": "technology", "item_index": 0}
                            ],
                            "profile_evidence": [
                                {
                                    "source": "project",
                                    "ref": "project:operational-intelligence-copilot",
                                }
                            ],
                        }
                    ],
                }
            ],
            "unranked_project_ids": [
                "operational-intelligence-copilot",
                "payroll-diagnostics-engine",
                "public-holiday-entitlements",
            ],
            "summary": "Factor cites the wrong project.",
            "insufficient_evidence": False,
        }
    )

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        validate_references(match, profile)

    assert any(
        "must cite profile evidence 'project:governance-document-rag'" in error.msg
        for error in raised.value.errors
    )


def test_namespace_mismatch_fails() -> None:
    match = _valid_match(
        ranked_projects=[
            {
                "rank": 1,
                "project_id": "example-project",
                "rationale": "Bad namespace.",
                "factors": [
                    {
                        "kind": "required_technology",
                        "summary": "Wrong namespace.",
                        "job_evidence": [{"source": "technology", "item_index": 0}],
                        "profile_evidence": [
                            {"source": "project", "ref": "skill:Python"}
                        ],
                    }
                ],
            }
        ]
    )

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        validate_references(match, _minimal_profile())

    assert any("requires ref namespace 'project'" in error.msg for error in raised.value.errors)


def test_technology_name_mismatch_fails() -> None:
    match = _valid_match(
        ranked_projects=[
            {
                "rank": 1,
                "project_id": "example-project",
                "rationale": "Name mismatch.",
                "factors": [
                    {
                        "kind": "required_technology",
                        "summary": "Wrong technology name for index.",
                        "job_evidence": [
                            {
                                "source": "technology",
                                "item_index": 0,
                                "name": "LangChain",
                            }
                        ],
                        "profile_evidence": [
                            {
                                "source": "project",
                                "ref": "project:example-project",
                            }
                        ],
                    }
                ],
            }
        ]
    )

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        validate_references(match, _minimal_profile())

    assert any("does not match" in error.msg for error in raised.value.errors)


def test_out_of_range_responsibility_index_fails() -> None:
    match = _valid_match(
        ranked_projects=[
            {
                "rank": 1,
                "project_id": "example-project",
                "rationale": "Bad responsibility index.",
                "factors": [
                    {
                        "kind": "responsibility_overlap",
                        "summary": "Out of range responsibility.",
                        "job_evidence": [
                            {"source": "responsibility", "item_index": 5}
                        ],
                        "profile_evidence": [
                            {
                                "source": "project",
                                "ref": "project:example-project",
                            }
                        ],
                    }
                ],
            }
        ]
    )

    with pytest.raises(PortfolioMatchingValidationError) as raised:
        validate_references(match, _minimal_profile())

    assert any("out of range" in error.msg for error in raised.value.errors)
