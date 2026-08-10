"""Unit tests for FR-006c Summary Intelligence composition."""

from __future__ import annotations

from career_intelligence.cv_generation.summary_intelligence import (
    compose_summary_intelligence,
    gather_summary_evidence,
)
from career_intelligence.cv_generation.theme_aware_summary import (
    compose_theme_aware_summary,
)
from career_intelligence.profile.models import Skill
from tests.unit.cv_generation.helpers import (
    make_cv,
    make_plan,
    minimal_profile,
    rich_job_analysis,
    strategy_from_payload,
)

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

_OVERALL_POSITIONING = (
    "Experienced engineer with 10+ years across testing, automation, data "
    "engineering and applied AI engineering"
)


def _plain(summary: str) -> str:
    return summary.replace("**", "")


def _paragraphs(summary: str) -> list[str]:
    return [part.strip() for part in summary.split("\n\n") if part.strip()]


def test_compose_avoids_mechanical_background_and_strengths_phrasing() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["AI Engineer", "Python", "FastAPI"],
        promoted_skills=["Python", "FastAPI", "OpenAI APIs"],
    )
    folded = _plain(summary).casefold()
    assert "background:" not in folded
    assert "strengths in" not in folded
    assert "experience includes" not in folded
    assert "builds" in folded
    assert "python" in folded
    assert "fastapi" in folded
    assert "10+ years across" in folded
    assert "3.5 years" not in folded
    assert "retrieval systems" in folded


def test_compose_is_deterministic() -> None:
    kwargs = {
        "source_summary": _MASTER_LIKE_SUMMARY,
        "target_role": "AI Engineer",
        "themes": ["Python", "REST APIs", "Operational intelligence"],
        "promoted_skills": ["Python", "FastAPI", "REST APIs"],
    }
    assert compose_summary_intelligence(**kwargs) == compose_summary_intelligence(
        **kwargs
    )


def test_compose_adapts_to_api_backend_emphasis() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Python", "REST APIs", "FastAPI"],
        promoted_skills=["Python", "REST APIs", "FastAPI"],
    )
    folded = _plain(summary).casefold()
    assert "rest apis" in folded or "fastapi" in folded
    assert "background:" not in folded


def test_compose_adapts_to_governance_explainability_emphasis() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="Applied AI Engineer",
        themes=["Explainable AI", "Governance", "Python"],
        promoted_skills=["Python", "OpenAI APIs"],
    )
    paragraphs = _paragraphs(summary)
    first = _plain(paragraphs[0]).casefold()
    assert first.startswith("experienced engineer with")
    assert "as an applied ai engineer" not in first
    assert "3.5 years" not in first
    body = _plain("\n\n".join(paragraphs[1:])).casefold()
    assert "explainable ai" in body or "governance" in body
    assert "background:" not in summary.casefold()


def test_compose_adapts_to_platform_deployment_emphasis() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Platform Engineer",
        themes=["Docker", "AWS", "Python"],
        promoted_skills=["Python", "Docker", "AWS"],
    )
    paragraphs = _paragraphs(summary)
    assert _plain(paragraphs[0]).casefold().startswith("experienced engineer with")
    folded = _plain(summary).casefold()
    assert "docker" in folded or "aws" in folded
    assert len(_plain(summary).split()) <= 200


def test_compose_adapts_to_consulting_operational_emphasis() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Consultant",
        themes=["Operational intelligence", "Enterprise decision support", "Python"],
        promoted_skills=["Python", "FastAPI"],
    )
    folded = _plain(summary).casefold()
    assert _plain(_paragraphs(summary)[0]).casefold().startswith(
        "experienced engineer with"
    )
    assert "operational intelligence" in folded or "enterprise decision support" in folded


def test_compose_adapts_to_data_engineer_with_ai_responsibilities() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="Data Engineer",
        themes=["SQL", "AWS", "Python"],
        promoted_skills=["Python", "SQL", "AWS"],
    )
    folded = _plain(summary).casefold()
    assert _plain(_paragraphs(summary)[0]).casefold().startswith(
        "experienced engineer with"
    )
    assert "sql" in folded or "aws" in folded
    assert "3.5 years" not in folded
    assert "10+ years across" in folded


def test_compose_does_not_invent_years_or_forbidden_phrases() -> None:
    summary = compose_summary_intelligence(
        source_summary="Builds evidence-backed systems.",
        target_role="AI Engineer",
        themes=["Python"],
        promoted_skills=["Python"],
    )
    assert "years" not in _plain(summary).casefold()
    assert "background:" not in summary.casefold()
    assert "python" in _plain(summary).casefold()


def test_compose_returns_source_when_no_emphasis() -> None:
    source = "Builds evidence-backed systems."
    assert (
        compose_summary_intelligence(
            source_summary=source,
            target_role="AI Engineer",
            themes=[],
            promoted_skills=[],
        )
        == source
    )


def test_theme_aware_entry_point_delegates_to_summary_intelligence() -> None:
    via_theme = compose_theme_aware_summary(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Python", "FastAPI"],
        promoted_skills=["Python", "FastAPI"],
    )
    via_intel = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Python", "FastAPI"],
        promoted_skills=["Python", "FastAPI"],
    )
    assert via_theme == via_intel


def test_gather_evidence_extracts_overall_positioning_and_portfolio() -> None:
    evidence = gather_summary_evidence(
        source_summary=_MASTER_LIKE_SUMMARY,
        themes=["Python"],
        promoted_skills=["Python", "FastAPI"],
    )
    assert evidence.overall_positioning is not None
    assert "10+ years across" in evidence.overall_positioning
    assert evidence.commercial_years is None
    assert evidence.portfolio_domains is not None
    assert "retrieval systems" in evidence.portfolio_domains
    assert evidence.builds_end_to_end is True


def test_compose_uses_stable_paragraph_story_structure() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Python", "FastAPI", "Explainable AI"],
        promoted_skills=["Python", "FastAPI", "OpenAI APIs"],
    )
    paragraphs = _paragraphs(summary)
    assert 3 <= len(paragraphs) <= 4
    first = _plain(paragraphs[0]).casefold()
    assert first.startswith("experienced engineer with")
    assert "10+ years across" in first
    assert "3.5 years" not in first
    assert first.index("10+ years") < first.index("builds")
    second = _plain(paragraphs[1]).casefold()
    assert "designs and delivers" in second or "python" in second
    assert any(
        "architecture-first" in _plain(part).casefold()
        or "ai engineering methodology" in _plain(part).casefold()
        for part in paragraphs[2:]
    )


def test_compose_preserves_recruiter_bold_emphasis() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Python", "FastAPI", "Docker"],
        promoted_skills=["Python", "FastAPI", "Docker", "OpenAI APIs"],
    )
    assert "**Python**" in summary or "**python**" in summary
    assert "**FastAPI**" in summary or "**fastapi**" in summary
    assert f"**{_OVERALL_POSITIONING}**" in summary
    bold_count = summary.count("**") // 2
    assert 3 <= bold_count <= 16


def test_opening_paragraph_is_stable_personal_brand() -> None:
    variants = [
        (["Python", "REST APIs"], ["Python", "REST APIs", "FastAPI"]),
        (["Explainable AI", "Governance"], ["Python", "OpenAI APIs"]),
        (["Docker", "AWS"], ["Python", "Docker", "AWS"]),
        (["Operational intelligence"], ["Python", "FastAPI"]),
    ]
    openings: set[str] = set()
    for themes, skills in variants:
        summary = compose_summary_intelligence(
            source_summary=_MASTER_LIKE_SUMMARY,
            target_role="AI Engineer",
            themes=themes,
            promoted_skills=skills,
        )
        opening = _paragraphs(summary)[0]
        openings.add(opening)
        assert _plain(opening).startswith("Experienced engineer with")
        assert "10+ years across" in opening
        assert "3.5 years" not in opening
    assert len(openings) == 1


def test_primary_theme_promoted_once_not_repeated() -> None:
    summary = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Operational intelligence", "Python"],
        promoted_skills=["Python", "FastAPI"],
    )
    plain = _plain(summary).casefold()
    assert plain.count("operational intelligence") <= 2
    closing = _plain(_paragraphs(summary)[-1]).casefold()
    assert "with emphasis on operational intelligence" not in closing


def test_later_paragraphs_adapt_while_brand_stays_fixed() -> None:
    backend = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Python", "REST APIs"],
        promoted_skills=["Python", "REST APIs", "FastAPI"],
    )
    platform = compose_summary_intelligence(
        source_summary=_MASTER_LIKE_SUMMARY,
        target_role="AI Engineer",
        themes=["Docker", "AWS", "Python"],
        promoted_skills=["Python", "Docker", "AWS"],
    )
    assert _plain(_paragraphs(backend)[0]) == _plain(_paragraphs(platform)[0])
    assert _plain(_paragraphs(backend)[1]) != _plain(_paragraphs(platform)[1])
    assert "rest apis" in _plain(backend).casefold() or "fastapi" in _plain(
        backend
    ).casefold()
    assert "docker" in _plain(platform).casefold() or "aws" in _plain(platform).casefold()


def test_service_summary_intelligence_path_for_rich_profile() -> None:
    profile = minimal_profile()
    profile = profile.model_copy(
        update={
            "identity": profile.identity.model_copy(
                update={"summary": _MASTER_LIKE_SUMMARY}
            ),
            "skills": profile.skills.model_copy(
                update={
                    "technical": [
                        Skill(name="Python", evidence="experience:example-role"),
                        Skill(name="FastAPI", evidence=None),
                        Skill(name="Docker", evidence=None),
                    ]
                }
            ),
        }
    )
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    cv = make_cv(profile=profile, strategy=strategy)
    assert cv.summary_source == "theme_aware_composition"
    assert cv.summary is not None
    folded = _plain(cv.summary).casefold()
    assert "background:" not in folded
    assert "strengths in" not in folded
    assert "experienced engineer with" in folded
    assert "10+ years across" in folded
    assert "3.5 years" not in folded
    assert len(_paragraphs(cv.summary)) >= 3
    assert any("summary intelligence" in item.casefold() for item in cv.assumptions)
    if cv.selected_engineering_highlights:
        assert "portfolio of AI applications" in cv.selected_engineering_highlights[0]


def test_minimal_fixture_still_composes_without_regression() -> None:
    profile = minimal_profile()
    strategy = strategy_from_payload(job_analysis=rich_job_analysis())
    plan = make_plan(profile=profile, strategy=strategy)
    cv = make_cv(profile=profile, strategy=strategy, plan=plan)
    assert cv.summary_source == "theme_aware_composition"
    assert cv.summary is not None
