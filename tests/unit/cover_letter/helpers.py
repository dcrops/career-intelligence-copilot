"""Shared builders for FR-007 cover letter unit tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.cover_letter import (
    CoverLetter,
    CoverLetterGenerationOptions,
    CoverLetterGenerationService,
    CoverLetterPlan,
    CoverLetterPlanOptions,
    CoverLetterPlanService,
    DeterministicCoverLetterPlanner,
)
from career_intelligence.cv_generation.options import ContactDetails
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile import CareerProfile, CareerProfileService

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


def default_contact() -> ContactDetails:
    return ContactDetails(
        email="candidate@example.com",
        phone="0400 000 000",
        location="Melbourne, VIC",
        linkedin_url="https://www.linkedin.com/in/example/",
        portfolio_url="https://example.com/portfolio/",
        github_url="https://github.com/example",
    )


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
    override_material_benefit: bool = False,
) -> CoverLetterPlan:
    bound_profile = profile or minimal_profile()
    bound_strategy = strategy or strategy_from_payload()
    return CoverLetterPlanService(DeterministicCoverLetterPlanner()).plan(
        bound_strategy,
        bound_profile,
        options=CoverLetterPlanOptions(
            owner_approved_to_plan=True,
            override_material_benefit=override_material_benefit,
        ),
    )


def make_letter(
    *,
    profile: CareerProfile | None = None,
    strategy: ApplicationStrategy | None = None,
    plan: CoverLetterPlan | None = None,
    override_material_benefit: bool = False,
    contact: ContactDetails | None = None,
) -> CoverLetter:
    bound_profile = profile or minimal_profile()
    bound_strategy = strategy or strategy_from_payload()
    bound_plan = plan or make_plan(
        profile=bound_profile,
        strategy=bound_strategy,
        override_material_benefit=override_material_benefit,
    )
    return CoverLetterGenerationService().generate(
        bound_strategy,
        bound_profile,
        bound_plan,
        options=CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=contact if contact is not None else default_contact(),
        ),
    )
