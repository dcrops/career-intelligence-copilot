"""Unit tests for the FR-005 application-strategy domain contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.application_strategy.models import (
    ApplicationStrategy,
    NextAction,
    NextActionKind,
    StrategyEvidenceRef,
)

from .helpers import (
    assessment_evidence,
    job_analysis,
    valid_strategy_payload,
)


def _valid_strategy(**overrides: object) -> ApplicationStrategy:
    payload = valid_strategy_payload(**overrides)
    payload["job_analysis"] = job_analysis()
    return ApplicationStrategy.model_validate(payload)


def test_valid_application_strategy_parses() -> None:
    strategy = _valid_strategy()

    assert strategy.application_tier == "platinum"
    assert strategy.pursuit_posture == "prioritise"
    assert strategy.effort_level == "full"
    assert strategy.owner_review_required is True
    assert strategy.insufficient_information is False


def test_bronze_replaces_skip_as_lowest_tier() -> None:
    strategy = _valid_strategy(
        application_tier="bronze",
        pursuit_posture="do_not_prioritise",
        practical_value="acceptable_opportunity",
        effort_level="none",
        next_actions=[
            {
                "kind": "consider_logging_and_deprioritising",
                "summary": "Consider logging and deprioritising this opportunity.",
                "evidence": [assessment_evidence(dimension="technical", judgment="weak")],
            }
        ],
        reasons=[
            {
                "kind": "priority",
                "summary": "Outside current AI Engineering priority.",
                "importance": "material",
                "evidence": [assessment_evidence(dimension="technical", judgment="weak")],
            }
        ],
        portfolio_emphasis=[],
    )

    assert strategy.application_tier == "bronze"
    assert strategy.effort_level == "none"


@pytest.mark.parametrize(
    ("tier", "effort"),
    [
        ("platinum", "full"),
        ("gold", "targeted"),
        ("silver", "minimal"),
        ("bronze", "none"),
    ],
)
def test_tier_effort_consistency_accepted(tier: str, effort: str) -> None:
    next_actions: list[dict[str, object]]
    posture: str
    practical: str
    if tier == "bronze":
        posture = "do_not_prioritise"
        practical = "acceptable_opportunity"
        next_actions = [
            {
                "kind": "consider_logging_and_deprioritising",
                "summary": "Consider logging and deprioritising.",
                "evidence": [assessment_evidence()],
            }
        ]
    elif tier in {"platinum", "gold"}:
        posture = "prioritise" if tier == "platinum" else "pursue"
        practical = "career_priority"
        next_actions = [
            {
                "kind": "consider_owner_review",
                "summary": "Review before acting.",
                "evidence": [assessment_evidence()],
            }
        ]
    else:
        posture = "consider"
        practical = "acceptable_opportunity"
        next_actions = [
            {
                "kind": "consider_owner_review",
                "summary": "Review before acting.",
                "evidence": [assessment_evidence()],
            }
        ]

    strategy = _valid_strategy(
        application_tier=tier,
        pursuit_posture=posture,
        practical_value=practical,
        effort_level=effort,
        next_actions=next_actions,
        portfolio_emphasis=[] if tier == "bronze" else valid_strategy_payload()[
            "portfolio_emphasis"
        ],
    )
    assert strategy.effort_level == effort


def test_tier_effort_mismatch_rejected() -> None:
    with pytest.raises(ValidationError, match="effort_level"):
        _valid_strategy(application_tier="platinum", effort_level="none")


def test_silver_targeted_allowed_with_consider_posture() -> None:
    strategy = _valid_strategy(
        application_tier="silver",
        pursuit_posture="consider",
        practical_value="acceptable_opportunity",
        effort_level="targeted",
        next_actions=[
            {
                "kind": "consider_owner_review",
                "summary": "Review before acting.",
                "evidence": [assessment_evidence()],
            }
        ],
    )
    assert strategy.effort_level == "targeted"
    assert strategy.application_tier == "silver"


def test_silver_targeted_rejected_without_consider_posture() -> None:
    with pytest.raises(ValidationError, match="targeted"):
        _valid_strategy(
            application_tier="silver",
            pursuit_posture="pursue",
            practical_value="career_priority",
            effort_level="targeted",
        )


def test_owner_review_required_must_be_true() -> None:
    with pytest.raises(ValidationError):
        _valid_strategy(owner_review_required=False)


def test_insufficient_information_matches_posture() -> None:
    with pytest.raises(ValidationError, match="insufficient_information"):
        _valid_strategy(
            pursuit_posture="insufficient_information",
            insufficient_information=False,
            application_tier="bronze",
            effort_level="none",
            practical_value="deferred_pending_information",
            next_actions=[
                {
                    "kind": "consider_gathering_missing_job_information",
                    "summary": "Consider gathering missing job information.",
                    "evidence": [assessment_evidence(judgment="unknown")],
                }
            ],
            portfolio_emphasis=[],
        )


def test_volume_obligation_requires_compatible_posture() -> None:
    with pytest.raises(ValidationError, match="volume_obligation"):
        _valid_strategy(
            practical_value="volume_obligation",
            pursuit_posture="prioritise",
        )


def test_next_actions_max_length() -> None:
    actions = [
        {
            "kind": "consider_owner_review",
            "summary": f"Review step {index}.",
            "evidence": [assessment_evidence()],
        }
        for index in range(6)
    ]
    with pytest.raises(ValidationError):
        _valid_strategy(next_actions=actions)


def test_related_project_id_only_for_emphasise_kind() -> None:
    with pytest.raises(ValidationError, match="related_project_id"):
        NextAction.model_validate(
            {
                "kind": "consider_owner_review",
                "summary": "Review the strategy.",
                "related_project_id": "example-project",
                "evidence": [assessment_evidence()],
            }
        )


def test_cv_tailoring_only_for_platinum_or_gold() -> None:
    with pytest.raises(ValidationError, match="consider_cv_tailoring"):
        _valid_strategy(
            application_tier="silver",
            pursuit_posture="consider",
            practical_value="acceptable_opportunity",
            effort_level="minimal",
            next_actions=[
                {
                    "kind": "consider_cv_tailoring",
                    "summary": "Consider CV tailoring.",
                    "evidence": [assessment_evidence()],
                }
            ],
            portfolio_emphasis=[],
        )


def test_low_effort_action_requires_posture() -> None:
    with pytest.raises(ValidationError, match="consider_low_effort_application"):
        _valid_strategy(
            application_tier="silver",
            pursuit_posture="consider",
            practical_value="acceptable_opportunity",
            effort_level="minimal",
            next_actions=[
                {
                    "kind": "consider_low_effort_application",
                    "summary": "Consider a low-effort application.",
                    "evidence": [assessment_evidence()],
                }
            ],
            portfolio_emphasis=[],
        )


def test_next_action_kinds_are_recommendation_oriented() -> None:
    kinds = set(NextActionKind.__args__)  # type: ignore[attr-defined]
    assert all(kind.startswith("consider_") for kind in kinds)
    assert "prepare_low_effort_submission" not in kinds
    assert "log_and_deprioritise" not in kinds


def test_strategy_evidence_origin_consistency() -> None:
    with pytest.raises(ValidationError, match="job_analysis evidence"):
        StrategyEvidenceRef.model_validate(
            {
                "origin": "job_analysis",
                "assessment_dimension": "technical",
            }
        )


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        _valid_strategy(interview_probability=0.8)


def test_skip_tier_rejected() -> None:
    with pytest.raises(ValidationError):
        _valid_strategy(application_tier="skip", effort_level="none")
