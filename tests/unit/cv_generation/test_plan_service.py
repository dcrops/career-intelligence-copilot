"""Unit tests for TailoringPlanService gates and trust boundary."""

from __future__ import annotations

import pytest

from career_intelligence.cv_generation import (
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanGateError,
    TailoringPlanService,
    TailoringPlanValidationError,
)
from tests.unit.cv_generation.helpers import (
    bronze_strategy,
    make_plan,
    minimal_profile,
    strategy_from_payload,
)


def test_service_requires_owner_approved_to_tailor() -> None:
    service = TailoringPlanService(DeterministicTailoringPlanner())
    with pytest.raises(TailoringPlanGateError, match="owner_approved_to_tailor"):
        service.plan(
            strategy_from_payload(),
            minimal_profile(),
            options=TailoringOptions(owner_approved_to_tailor=False),
        )


def test_service_refuses_bronze_without_override() -> None:
    service = TailoringPlanService(DeterministicTailoringPlanner())
    with pytest.raises(TailoringPlanGateError, match="Material-benefit"):
        service.plan(
            bronze_strategy(),
            minimal_profile(),
            options=TailoringOptions(owner_approved_to_tailor=True),
        )


def test_service_allows_bronze_with_explicit_override() -> None:
    plan = make_plan(
        strategy=bronze_strategy(),
        override_material_benefit=True,
    )
    assert plan.material_benefit_override is True
    assert any("overridden" in item.lower() for item in plan.assumptions)


def test_service_rejects_embedded_job_analysis_in_payload() -> None:
    class BadPlanner:
        def plan(self, strategy, profile, options):  # noqa: ANN001
            return {
                "job_analysis": strategy.job_analysis.model_dump(mode="json"),
                "application_tier": strategy.application_tier,
                "pursuit_posture": strategy.pursuit_posture,
                "jd_priorities": [],
                "projects_to_emphasise": [],
                "skills_to_promote": [],
                "skills_not_emphasised": [],
                "summary_themes": [],
                "experience_guidance": {
                    "kind": "master_cv_only",
                    "rationale": "test",
                    "included_experience_ids": [profile.experience[0].id],
                    "excluded_experience_ids": [],
                },
                "assumptions": [],
                "owner_review_recommended": True,
                "insufficient_evidence": True,
                "material_benefit_override": False,
            }

    service = TailoringPlanService(BadPlanner())
    with pytest.raises(TailoringPlanValidationError) as exc:
        service.plan(
            strategy_from_payload(),
            minimal_profile(),
            options=TailoringOptions(owner_approved_to_tailor=True),
        )
    assert any(detail.loc == ("job_analysis",) for detail in exc.value.errors)


def test_service_returns_trusted_plan_with_bound_analysis() -> None:
    strategy = strategy_from_payload()
    plan = make_plan(strategy=strategy)
    assert plan.job_analysis.posting.raw_text == strategy.job_analysis.posting.raw_text
    assert plan.application_tier == strategy.application_tier
