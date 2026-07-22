"""Unit tests for application-strategy referential integrity checks."""

from __future__ import annotations

import pytest
from career_intelligence.application_strategy.errors import (
    ApplicationStrategyValidationError,
)
from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.application_strategy.refs import validate_references

from .helpers import (
    assessment_evidence,
    job_analysis,
    minimal_profile,
    opportunity_assessment,
    portfolio_match,
    portfolio_project_evidence,
    valid_strategy_payload,
)


def _strategy(**overrides: object) -> ApplicationStrategy:
    payload = valid_strategy_payload(**overrides)
    payload["job_analysis"] = job_analysis()
    return ApplicationStrategy.model_validate(payload)


def test_valid_references_pass() -> None:
    analysis = job_analysis()
    strategy = _strategy()
    validate_references(
        strategy,
        opportunity_assessment(analysis),
        portfolio_match(analysis),
        minimal_profile(),
    )


def test_invalid_assessment_judgment_rejected() -> None:
    analysis = job_analysis()
    strategy = _strategy(
        reasons=[
            {
                "kind": "alignment",
                "summary": "Claims weak technical fit incorrectly.",
                "importance": "material",
                "evidence": [
                    assessment_evidence(dimension="technical", judgment="weak")
                ],
            }
        ]
    )
    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        validate_references(
            strategy,
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )
    assert any("assessment_judgment" in error.loc for error in exc_info.value.errors)


def test_unknown_portfolio_project_evidence_rejected() -> None:
    analysis = job_analysis()
    strategy = _strategy(
        reasons=[
            {
                "kind": "alignment",
                "summary": "Cites unknown project.",
                "importance": "material",
                "evidence": [portfolio_project_evidence("missing-project")],
            }
        ]
    )
    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        validate_references(
            strategy,
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )
    assert any("portfolio_project_id" in error.loc for error in exc_info.value.errors)


def test_related_project_id_must_exist_on_portfolio_match() -> None:
    analysis = job_analysis()
    strategy = _strategy(
        next_actions=[
            {
                "kind": "consider_emphasising_portfolio_projects",
                "summary": "Consider emphasising a missing project.",
                "related_project_id": "missing-project",
                "evidence": [assessment_evidence()],
            }
        ],
        portfolio_emphasis=[],
    )
    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        validate_references(
            strategy,
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )
    assert any("related_project_id" in error.loc for error in exc_info.value.errors)


def test_portfolio_emphasis_source_rank_must_match() -> None:
    analysis = job_analysis()
    strategy = _strategy(
        portfolio_emphasis=[
            {
                "project_id": "example-project",
                "source_rank": 2,
                "summary": "Wrong rank.",
                "evidence": [portfolio_project_evidence()],
            }
        ]
    )
    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        validate_references(
            strategy,
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )
    assert any("source_rank" in error.loc for error in exc_info.value.errors)


def test_invalid_profile_ref_rejected() -> None:
    analysis = job_analysis()
    strategy = _strategy(
        reasons=[
            {
                "kind": "alignment",
                "summary": "Bad profile ref.",
                "importance": "material",
                "evidence": [
                    {
                        "origin": "career_profile",
                        "profile_evidence": {
                            "source": "skill",
                            "ref": "skill:DoesNotExist",
                        },
                    }
                ],
            }
        ]
    )
    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        validate_references(
            strategy,
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )
    assert any("ref" in error.loc for error in exc_info.value.errors)


def test_job_evidence_item_index_out_of_range() -> None:
    analysis = job_analysis()
    strategy = _strategy(
        reasons=[
            {
                "kind": "alignment",
                "summary": "Bad technology index.",
                "importance": "material",
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {
                            "source": "technology",
                            "item_index": 9,
                            "name": "Python",
                        },
                    }
                ],
            }
        ]
    )
    with pytest.raises(ApplicationStrategyValidationError) as exc_info:
        validate_references(
            strategy,
            opportunity_assessment(analysis),
            portfolio_match(analysis),
            minimal_profile(),
        )
    assert any("item_index" in error.loc for error in exc_info.value.errors)
