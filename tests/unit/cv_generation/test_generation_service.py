"""Unit tests for CvGenerationService, fidelity, and Markdown rendering."""

from __future__ import annotations

import json

import pytest

from career_intelligence.cv_generation import (
    ContactDetails,
    CvGenerationGateError,
    CvGenerationOptions,
    CvGenerationService,
    CvGenerationValidationError,
    render_markdown,
)
from career_intelligence.cv_generation.fidelity import validate_fidelity
from career_intelligence.profile.models import Skill
from tests.unit.cv_generation.helpers import (
    make_cv,
    make_plan,
    minimal_profile,
    profile_with_extended_history,
    rich_job_analysis,
    strategy_from_payload,
)


def test_generation_requires_tailoring_plan_approved() -> None:
    with pytest.raises(CvGenerationGateError, match="tailoring_plan_approved"):
        make_cv(tailoring_plan_approved=False)


def test_generation_is_pure_render_of_plan_order() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="FastAPI", evidence=None),
                        Skill(name="Spark", evidence=None),
                    ]
                }
            )
        }
    )
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    cv = make_cv(profile=profile, strategy=strategy, plan=plan)

    assert [item.project_id for item in cv.projects] == [
        item.project_id for item in plan.projects_to_emphasise
    ]
    assert [item.skill_name for item in cv.skills if item.emphasised] == [
        item.skill_name for item in plan.skills_to_promote
    ]
    assert cv.owner_review_required is True
    assert cv.tailoring_plan_approved is True


def test_markdown_emphasises_promoted_skills_and_lead_project() -> None:
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
    cv = make_cv(profile=profile, strategy=strategy)
    markdown = cv.rendered_markdown
    assert "### Emphasised" in markdown
    assert "Python" in markdown
    assert "FastAPI" in markdown
    assert "Docker" in markdown
    assert "Example Project" in markdown
    assert "Owner review required" in markdown


def test_fidelity_rejects_reordered_projects() -> None:
    profile = minimal_profile()
    second = profile.projects[0].model_copy(
        update={"id": "second-project", "name": "Second Project"}
    )
    profile = profile.model_copy(update={"projects": [*profile.projects, second]})
    strategy = strategy_from_payload(
        portfolio_emphasis=[
            {
                "project_id": "example-project",
                "source_rank": 1,
                "summary": "Lead with example-project.",
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": "example-project",
                    }
                ],
            },
            {
                "project_id": "second-project",
                "source_rank": 2,
                "summary": "Then second-project.",
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": "second-project",
                    }
                ],
            },
        ],
    )
    plan = make_plan(profile=profile, strategy=strategy)
    cv = make_cv(profile=profile, strategy=strategy, plan=plan)
    tampered = cv.model_copy(update={"projects": list(reversed(cv.projects))})
    with pytest.raises(CvGenerationValidationError) as exc:
        validate_fidelity(tampered, plan)
    assert any("project order" in detail.msg for detail in exc.value.errors)


def test_master_cv_filter_excludes_extended_history_by_default() -> None:
    profile = profile_with_extended_history()
    plan = make_plan(profile=profile)
    cv = make_cv(profile=profile, plan=plan)
    ids = [entry.experience_id for entry in cv.experience]
    assert "bakers-delight-test-analyst-2009" not in ids
    assert "example-role" in ids
    assert cv.experience_guidance_kind == "master_cv_only"


def test_extended_history_opt_in_includes_pre_master_cv_entries() -> None:
    profile = profile_with_extended_history()
    plan = make_plan(profile=profile, include_extended_history=True)
    cv = make_cv(profile=profile, plan=plan)
    ids = [entry.experience_id for entry in cv.experience]
    assert "bakers-delight-test-analyst-2009" in ids
    assert cv.experience_guidance_kind == "include_extended_history"


def test_experience_kinds_remain_truthful() -> None:
    profile = minimal_profile()
    independent = profile.experience[0].model_copy(
        update={
            "id": "chase-risk-compliance-ai-engineer",
            "kind": "independent_engineering",
            "organisation": "Chase Risk & Compliance",
            "title": "AI Engineer - Independent Research & Development",
        }
    )
    profile = profile.model_copy(update={"experience": [independent]})
    cv = make_cv(profile=profile)
    assert cv.experience[0].kind == "independent_engineering"
    assert "`independent_engineering`" in cv.rendered_markdown
    assert cv.experience[0].kind != "employment"


def test_phase_b_copies_profile_summary_without_rewriting() -> None:
    profile = minimal_profile()
    cv = make_cv(profile=profile)
    assert cv.summary == profile.identity.summary
    assert any("rewrite_summary=False" in item for item in cv.assumptions)
    assert cv.summary_source == "profile_copy"


def test_contact_overlay_is_caller_supplied_only() -> None:
    strategy = strategy_from_payload()
    profile = minimal_profile()
    plan = make_plan(profile=profile, strategy=strategy)
    cv = CvGenerationService().generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            contact=ContactDetails(email="owner@example.com", phone=None),
        ),
    )
    assert cv.contact == {"email": "owner@example.com"}
    assert "owner@example.com" in cv.rendered_markdown


def test_tailored_cv_serialises_to_typed_json() -> None:
    cv = make_cv()
    payload = json.loads(cv.model_dump_json())
    assert payload["owner_review_required"] is True
    assert "rendered_markdown" in payload
    assert payload["tailoring_plan_approved"] is True


def test_render_markdown_is_deterministic() -> None:
    cv = make_cv()
    assert render_markdown(cv) == cv.rendered_markdown
