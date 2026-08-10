"""FR-006/FR-007 quality refinements from Mars Recruitment dogfooding."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.cover_letter import (
    CoverLetterPlanOptions,
    DeterministicCoverLetterPlanner,
)
from career_intelligence.cover_letter.composer import (
    _as_chance_clause,
    _employer_voice,
    _independent_portfolio_years,
    compose_cover_letter_paragraphs,
)
from career_intelligence.cover_letter.deterministic_planner import (
    _is_usable_attraction_hook,
)
from career_intelligence.cover_letter.project_selection import select_projects_for_letter
from career_intelligence.cv_generation.deterministic_planner import (
    DeterministicTailoringPlanner,
    _classify_against_profile,
)
from career_intelligence.cv_generation.options import TailoringOptions
from career_intelligence.cv_generation.summary_intelligence import (
    compose_summary_intelligence,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile import CareerProfileService
from tests.unit.application_strategy.helpers import job_analysis
from tests.unit.cover_letter.helpers import (
    default_contact,
    make_letter,
    make_plan,
    strategy_from_payload,
)
from tests.unit.cv_generation.helpers import rich_job_analysis


_REPO = Path(__file__).resolve().parents[2]
_MASTER_LIKE_SUMMARY = (
    "Experienced engineer with 10+ years across testing, automation, data "
    "engineering and applied AI engineering. Applies software engineering "
    "discipline to build end-to-end AI applications with Python, FastAPI, Docker, "
    "and OpenAI APIs, with independent AI Engineering portfolio work across "
    "retrieval systems, operational intelligence, explainable AI, and enterprise "
    "decision support. Applies a disciplined AI Engineering methodology — "
    "architecture-first design, evidence-based validation, and human-in-the-loop "
    "review — to build AI systems with traceable, reviewable outputs for "
    "operational decision-making."
)


def _real_profile():
    try:
        return CareerProfileService().load()
    except Exception:
        pytest.skip("Career Profile YAML not available")


def test_chance_clause_rejects_recruiting_person_blurb() -> None:
    clause = _as_chance_clause(
        "an experienced AI Engineer to join a well-established Australian "
        "financial services organisation investing heavily in Generative AI"
    )
    assert "contribute to an experienced" not in clause.casefold()
    assert "build production ai systems" in clause.casefold()


def test_chance_clause_keeps_engineering_verb_themes() -> None:
    clause = _as_chance_clause(
        "Designing and building production-ready AI applications and intelligent automation"
    )
    assert clause.startswith("design")
    assert "contribute to" not in clause.casefold()


def test_attraction_hook_rejects_hiring_ad_blurbs() -> None:
    assert not _is_usable_attraction_hook(
        "an experienced AI Engineer to join a well-established Australian "
        "financial services organisation",
        company="Mars Recruitment",
        role_title="AI Engineer",
    )
    assert not _is_usable_attraction_hook(
        "An exciting opportunity has become available for an experienced AI Engineer",
        company="Mars Recruitment",
        role_title="AI Engineer",
    )
    assert _is_usable_attraction_hook(
        "Designing and building production-ready AI applications and intelligent automation",
        company="Mars Recruitment",
        role_title="AI Engineer",
    )


def test_recruiter_employer_voice_uses_client_wording() -> None:
    strategy = strategy_from_payload(
        job_analysis=job_analysis(
            posting={
                "raw_text": (
                    "Mars Recruitment is hiring an AI Engineer for our client, "
                    "a financial services organisation investing in Generative AI."
                ),
                "title": "AI Engineer",
                "company": "Mars Recruitment",
            }
        )
    )
    plan = make_plan(strategy=strategy, override_material_benefit=True)
    voice = _employer_voice(plan)
    assert voice["mode"] == "recruiter"
    assert "advertised through" in voice["opening_subject"].casefold()
    assert "your client" in voice["challenge_owner"].casefold()

    paragraphs = compose_cover_letter_paragraphs(
        plan,
        _real_profile(),
        contact=default_contact().model_dump(),
    )
    body = " ".join(paragraphs).casefold()
    assert "advertised through mars recruitment" in body
    assert "your client" in body
    assert "mars recruitment's technical challenges" not in body
    assert "contribute to an experienced" not in body
    assert "has become available" not in body


def test_portfolio_years_derived_from_ai_experience_dates() -> None:
    profile = _real_profile()
    assert _independent_portfolio_years(profile) == "year"


def test_azure_jd_promotes_azure_data_factory() -> None:
    support, matched = _classify_against_profile(
        "Azure",
        ["Azure Data Factory", "Python", "Docker", "REST APIs"],
    )
    assert support == "related"
    assert matched == "Azure Data Factory"


def test_summary_does_not_repeat_traceable_reviewable_close() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Python", "FastAPI", "Azure", "RAG"],
        promoted_skills=["Python", "FastAPI", "Azure Data Factory", "Docker"],
    )
    folded = summary.replace("**", "").casefold()
    assert folded.count("traceable, reviewable") <= 1
    assert "python" in folded or "fastapi" in folded


def test_ai_family_ranks_cic_above_public_holiday_when_both_emphasised() -> None:
    profile = _real_profile()
    if not all(
        any(project.id == project_id for project in profile.projects)
        for project_id in (
            "career-intelligence-copilot",
            "public-holiday-entitlements",
            "governance-document-rag",
        )
    ):
        pytest.skip("Expected portfolio projects missing")

    analysis = rich_job_analysis()
    # REST-heavy AI JD — previously favoured Public Holiday on API overlap alone.
    payload = analysis.model_dump(mode="python")
    payload["role_family"] = {
        "family": "ai_engineering",
        "evidence": [{"excerpt": "AI Engineer building production AI systems"}],
    }
    payload["technologies"] = [
        {
            "name": "Python",
            "level": "required",
            "evidence": [{"excerpt": "Python required", "section": "requirements"}],
        },
        {
            "name": "REST APIs",
            "level": "required",
            "evidence": [{"excerpt": "REST APIs", "section": "requirements"}],
        },
        {
            "name": "LLMs",
            "level": "required",
            "evidence": [{"excerpt": "LLMs", "section": "requirements"}],
        },
        {
            "name": "Azure",
            "level": "preferred",
            "evidence": [{"excerpt": "Azure preferred", "section": "requirements"}],
        },
    ]
    strategy = strategy_from_payload(
        job_analysis=JobAnalysis.model_validate(payload),
        portfolio_emphasis=[
            {
                "project_id": "public-holiday-entitlements",
                "source_rank": 1,
                "summary": "Lead with public-holiday-entitlements.",
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": "public-holiday-entitlements",
                    }
                ],
            },
            {
                "project_id": "governance-document-rag",
                "source_rank": 2,
                "summary": "Then governance-document-rag.",
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": "governance-document-rag",
                    }
                ],
            },
            {
                "project_id": "career-intelligence-copilot",
                "source_rank": 3,
                "summary": "Then career-intelligence-copilot.",
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": "career-intelligence-copilot",
                    }
                ],
            },
        ],
        next_actions=[
            {
                "kind": "consider_cv_tailoring",
                "summary": "Consider CV tailoring.",
                "evidence": [
                    {
                        "origin": "opportunity_assessment",
                        "assessment_dimension": "technical",
                        "assessment_judgment": "strong",
                    }
                ],
            }
        ],
    )
    plan_payload = DeterministicTailoringPlanner().plan(
        strategy,
        profile,
        TailoringOptions(owner_approved_to_tailor=True),
    )
    order = [item["project_id"] for item in plan_payload["projects_to_emphasise"]]
    assert "career-intelligence-copilot" in order
    assert "public-holiday-entitlements" in order
    assert order.index("career-intelligence-copilot") < order.index(
        "public-holiday-entitlements"
    )

    # Cover letter selection should also prefer AI systems evidence.
    selected = select_projects_for_letter(profile, strategy, max_projects=3)
    selected_ids = [item.project.id for item in selected]
    assert "career-intelligence-copilot" in selected_ids or any(
        item.project.id
        in {
            "governance-document-rag",
            "operational-intelligence-copilot",
            "career-intelligence-copilot",
        }
        for item in selected
    )
    if (
        "career-intelligence-copilot" in selected_ids
        and "public-holiday-entitlements" in selected_ids
    ):
        assert selected_ids.index("career-intelligence-copilot") < selected_ids.index(
            "public-holiday-entitlements"
        )


def test_mars_like_cover_letter_opening_is_grammatically_complete() -> None:
    profile = _real_profile()
    analysis = job_analysis(
        posting={
            "raw_text": (
                "Mars Recruitment\nAI Engineer\nAn exciting opportunity has become "
                "available for an experienced AI Engineer to join a well-established "
                "Australian financial services organisation investing heavily in "
                "Generative AI.\nDesigning and building production-ready AI applications "
                "and intelligent automation.\nAzure preferred. REST APIs. Docker."
            ),
            "title": "AI Engineer",
            "company": "Mars Recruitment",
        },
        role_family={
            "family": "ai_engineering",
            "evidence": [
                {
                    "excerpt": (
                        "an experienced AI Engineer to join a well-established "
                        "Australian financial services organisation investing heavily "
                        "in Generative AI"
                    ),
                    "section": "title",
                }
            ],
        },
        responsibilities=[
            {
                "description": (
                    "Designing and building production-ready AI applications and "
                    "intelligent automation"
                ),
                "evidence": [
                    {
                        "excerpt": (
                            "Designing and building production-ready AI applications "
                            "and intelligent automation"
                        ),
                        "section": "responsibilities",
                    }
                ],
            }
        ],
    )
    strategy = strategy_from_payload(job_analysis=analysis)
    plan_payload = DeterministicCoverLetterPlanner().plan(
        strategy,
        profile,
        CoverLetterPlanOptions(
            owner_approved_to_plan=True,
            override_material_benefit=True,
        ),
    )
    hook = plan_payload["company_alignment"]["alignment_hook"]
    # Planner must not keep the hiring-person blurb as the attraction hook.
    assert "experienced ai engineer to join" not in str(hook).casefold()

    letter = make_letter(
        profile=profile,
        strategy=strategy,
        override_material_benefit=True,
    )
    opening = letter.paragraphs[0]
    assert "contribute to an experienced" not in opening.casefold()
    assert "has become available" not in opening.casefold()
    assert not opening.rstrip().endswith((" in.", " for.", " to.", " and."))
    body = " ".join(letter.paragraphs).casefold()
    assert "over the past year" in body
    assert "your client" in body or "advertised through" in body
    assert "what drew me" not in opening.casefold()
    assert "owner review required before any external use" not in letter.rendered_markdown.casefold()
    assert "repositories ." not in letter.rendered_markdown
    assert "github" in body
    assert "portfolio" in body


def test_opening_strategies_are_deterministic_and_varied() -> None:
    from career_intelligence.cover_letter.opening_strategies import (
        select_opening_strategy,
    )

    profile = _real_profile()
    mars = make_plan(
        profile=profile,
        strategy=strategy_from_payload(
            job_analysis=job_analysis(
                posting={
                    "raw_text": (
                        "AI Engineer via Mars Recruitment. Our client needs "
                        "Python FastAPI Docker Azure."
                    ),
                    "title": "AI Engineer",
                    "company": "Mars Recruitment",
                },
                role_family={
                    "family": "ai_engineering",
                    "evidence": [{"excerpt": "AI Engineer", "section": "title"}],
                },
            )
        ),
    )
    forever = make_plan(
        profile=profile,
        strategy=strategy_from_payload(
            job_analysis=job_analysis(
                posting={
                    "raw_text": (
                        "Forever New Clothing fashion retail. Senior AI Automation "
                        "Engineer. Python SQL Databricks RAG."
                    ),
                    "title": "Senior AI Automation Engineer – Digital",
                    "company": "Forever New Clothing",
                },
                role_family={
                    "family": "ai_engineering",
                    "evidence": [
                        {"excerpt": "AI Automation Engineer", "section": "title"}
                    ],
                },
            )
        ),
    )
    a = select_opening_strategy(mars, profile, employer_mode="recruiter")
    b = select_opening_strategy(mars, profile, employer_mode="recruiter")
    c = select_opening_strategy(forever, profile, employer_mode="direct")
    assert a == b
    assert a != c


def test_portfolio_note_avoids_em_dash_fragments() -> None:
    from career_intelligence.cover_letter.composer import _compose_portfolio_body_note

    plan = make_plan()
    note = _compose_portfolio_body_note(
        plan,
        contact=default_contact().model_dump(exclude_none=True),
    )
    assert note is not None
    assert "—" not in note
    assert "repositories ." not in note
    assert "github" in note.casefold()
    assert "slideware" in note.casefold()
