"""Functional acceptance tests for FR-006 Phase A/B (offline deterministic)."""

from __future__ import annotations

import pytest

from career_intelligence.cv_generation import (
    CvGenerationGateError,
    CvGenerationOptions,
    CvGenerationService,
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanGateError,
    TailoringPlanService,
)
from career_intelligence.profile.models import Skill
from tests.unit.cv_generation.helpers import (
    bronze_strategy,
    make_cv,
    make_plan,
    minimal_profile,
    profile_with_extended_history,
    rich_job_analysis,
    strategy_from_payload,
)

_FORBIDDEN_CV_FIELDS = frozenset(
    {
        "cover_letter_body",
        "cv_body",
        "openai_prompt",
        "recruiter_message",
    }
)


def test_fr006_phase_a_produces_evidence_backed_tailoring_plan() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="FastAPI", evidence=None),
                        Skill(name="Docker", evidence=None),
                        Skill(name="Spark", evidence=None),
                    ]
                }
            )
        }
    )
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = TailoringPlanService(DeterministicTailoringPlanner()).plan(
        strategy,
        profile,
        options=TailoringOptions(owner_approved_to_tailor=True),
    )

    assert plan.owner_review_recommended is True
    assert plan.jd_priorities[0].label == "Python"
    assert plan.jd_priorities[0].candidate_support == "supported"
    assert plan.jd_priorities[0].evidence
    assert [item.skill_name for item in plan.skills_to_promote] == [
        "Python",
        "FastAPI",
        "Docker",
    ]
    assert any(item.skill_name == "Spark" for item in plan.skills_not_emphasised)
    assert all(
        item.theme.casefold() != "tensorflow" for item in plan.summary_themes
    )
    assert plan.projects_to_emphasise[0].project_id == "example-project"
    assert plan.experience_guidance.kind == "master_cv_only"
    for field in _FORBIDDEN_CV_FIELDS:
        assert field not in plan.model_dump()


def test_fr006_phase_b_renders_cv_faithfully_from_plan() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="FastAPI", evidence=None),
                        Skill(name="Docker", evidence=None),
                    ]
                }
            )
        }
    )
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    cv = CvGenerationService().generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(tailoring_plan_approved=True),
    )

    assert cv.owner_review_required is True
    assert [project.project_id for project in cv.projects] == [
        item.project_id for item in plan.projects_to_emphasise
    ]
    emphasised = [skill.skill_name for skill in cv.skills if skill.emphasised]
    assert emphasised == ["Python", "FastAPI", "Docker"]
    for skill_name in emphasised:
        assert skill_name in cv.rendered_markdown
    assert cv.projects[0].name in cv.rendered_markdown
    assert cv.summary == profile.identity.summary
    for field in _FORBIDDEN_CV_FIELDS:
        assert field not in cv.model_dump()


def test_fr006_distinguishes_tailor_approval_plan_approval_and_final_review() -> None:
    strategy = strategy_from_payload()
    profile = minimal_profile()
    service = TailoringPlanService(DeterministicTailoringPlanner())

    with pytest.raises(TailoringPlanGateError, match="owner_approved_to_tailor"):
        service.plan(
            strategy,
            profile,
            options=TailoringOptions(owner_approved_to_tailor=False),
        )

    plan = service.plan(
        strategy,
        profile,
        options=TailoringOptions(owner_approved_to_tailor=True),
    )
    assert plan.owner_review_recommended is True

    with pytest.raises(CvGenerationGateError, match="tailoring_plan_approved"):
        CvGenerationService().generate(
            strategy,
            profile,
            plan,
            options=CvGenerationOptions(tailoring_plan_approved=False),
        )

    cv = make_cv(profile=profile, strategy=strategy, plan=plan)
    assert cv.tailoring_plan_approved is True
    assert cv.owner_review_required is True


def test_fr006_does_not_invent_skills_or_projects() -> None:
    plan = make_plan()
    promoted = {item.skill_name for item in plan.skills_to_promote}
    profile_skills = {
        skill.name
        for skill in (
            *minimal_profile().skills.technical,
            *minimal_profile().skills.domain,
            *minimal_profile().skills.soft,
        )
    }
    assert promoted <= profile_skills
    for project in plan.projects_to_emphasise:
        assert project.project_id in {p.id for p in minimal_profile().projects}


def test_fr006_material_benefit_gate_and_master_cv_default() -> None:
    with pytest.raises(TailoringPlanGateError, match="Material-benefit"):
        TailoringPlanService(DeterministicTailoringPlanner()).plan(
            bronze_strategy(),
            minimal_profile(),
            options=TailoringOptions(owner_approved_to_tailor=True),
        )

    profile = profile_with_extended_history()
    plan = make_plan(profile=profile)
    assert "bakers-delight-test-analyst-2009" in (
        plan.experience_guidance.excluded_experience_ids
    )
    cv = make_cv(profile=profile, plan=plan)
    assert all(
        entry.experience_id != "bakers-delight-test-analyst-2009"
        for entry in cv.experience
    )
