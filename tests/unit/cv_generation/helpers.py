"""Shared builders for FR-006 Phase A/B unit tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.cv_generation import (
    CvGenerationOptions,
    CvGenerationService,
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlan,
    TailoringPlanService,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile import CareerProfile, CareerProfileService
from career_intelligence.profile.models import ExperienceEntry

from tests.unit.application_strategy.helpers import (
    job_analysis,
    valid_strategy_payload,
)


def fixtures_dir() -> Path:
    return Path(__file__).parents[2] / "fixtures"


def minimal_profile() -> CareerProfile:
    return CareerProfileService.from_path(
        fixtures_dir() / "minimal_valid_profile.yaml"
    ).load()


def strategy_from_payload(**overrides: object) -> ApplicationStrategy:
    analysis = overrides.pop("job_analysis", None)
    if analysis is None:
        analysis = job_analysis()
    elif isinstance(analysis, dict):
        analysis = JobAnalysis.model_validate(analysis)
    payload = valid_strategy_payload(**overrides)
    payload["job_analysis"] = analysis
    return ApplicationStrategy.model_validate(payload)


def bronze_strategy(**overrides: object) -> ApplicationStrategy:
    payload_overrides: dict[str, object] = {
        "application_tier": "bronze",
        "pursuit_posture": "do_not_prioritise",
        "practical_value": "deferred_pending_information",
        "effort_level": "none",
        "next_actions": [
            {
                "kind": "consider_owner_review",
                "summary": "Review this strategy before taking any external action.",
                "evidence": [
                    {
                        "origin": "opportunity_assessment",
                        "assessment_dimension": "technical",
                        "assessment_judgment": "strong",
                    }
                ],
            }
        ],
        "portfolio_emphasis": [],
    }
    payload_overrides.update(overrides)
    return strategy_from_payload(**payload_overrides)


def make_plan(
    *,
    profile: CareerProfile | None = None,
    strategy: ApplicationStrategy | None = None,
    include_extended_history: bool = False,
    override_material_benefit: bool = False,
) -> TailoringPlan:
    bound_profile = profile or minimal_profile()
    bound_strategy = strategy or strategy_from_payload()
    service = TailoringPlanService(DeterministicTailoringPlanner())
    return service.plan(
        bound_strategy,
        bound_profile,
        options=TailoringOptions(
            owner_approved_to_tailor=True,
            include_extended_history=include_extended_history,
            override_material_benefit=override_material_benefit,
        ),
    )


def make_cv(
    *,
    profile: CareerProfile | None = None,
    strategy: ApplicationStrategy | None = None,
    plan: TailoringPlan | None = None,
    tailoring_plan_approved: bool = True,
):
    bound_profile = profile or minimal_profile()
    bound_strategy = strategy or strategy_from_payload()
    bound_plan = plan or make_plan(profile=bound_profile, strategy=bound_strategy)
    service = CvGenerationService()
    return service.generate(
        bound_strategy,
        bound_profile,
        bound_plan,
        options=CvGenerationOptions(tailoring_plan_approved=tailoring_plan_approved),
    )


def profile_with_extended_history() -> CareerProfile:
    """Minimal profile plus one extended-history experience id."""
    profile = minimal_profile()
    extended = ExperienceEntry.model_validate(
        {
            "id": "bakers-delight-test-analyst-2009",
            "kind": "employment",
            "organisation": "Bakers Delight",
            "title": "Test Analyst",
            "start_date": "2009-03",
            "end_date": "2012-06",
            "location": "Melbourne",
            "highlights": [],
            "technologies": [],
        }
    )
    return profile.model_copy(
        update={"experience": [*profile.experience, extended]}
    )


def rich_job_analysis() -> JobAnalysis:
    return job_analysis(
        technologies=[
            {
                "name": "Python",
                "level": "required",
                "evidence": [{"excerpt": "Python required", "section": "requirements"}],
            },
            {
                "name": "FastAPI",
                "level": "required",
                "evidence": [
                    {"excerpt": "FastAPI experience", "section": "requirements"}
                ],
            },
            {
                "name": "Docker",
                "level": "preferred",
                "evidence": [
                    {"excerpt": "Docker preferred", "section": "requirements"}
                ],
            },
            {
                "name": "TensorFlow",
                "level": "preferred",
                "evidence": [
                    {"excerpt": "TensorFlow nice to have", "section": "requirements"}
                ],
            },
        ],
        responsibilities=[
            {
                "description": "Build production AI services and APIs",
                "evidence": [
                    {
                        "excerpt": "Build production AI services and APIs",
                        "section": "responsibilities",
                    }
                ],
            }
        ],
    )
