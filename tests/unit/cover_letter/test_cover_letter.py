"""Unit tests for FR-007 Cover Letter Generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from career_intelligence.cover_letter import (
    CoverLetterGenerationGateError,
    CoverLetterGenerationOptions,
    CoverLetterGenerationService,
    CoverLetterPlanGateError,
    CoverLetterPlanOptions,
    CoverLetterPlanService,
    DeterministicCoverLetterPlanner,
    default_generated_dir,
    render_html,
    write_cover_letter_drafts,
)
from career_intelligence.profile import CareerProfileService
from tests.unit.cover_letter.helpers import (
    bronze_strategy,
    make_letter,
    make_plan,
    minimal_profile,
    strategy_from_payload,
)
from tests.unit.application_strategy.helpers import job_analysis


_FORBIDDEN = (
    "i am writing to apply",
    "i am excited to apply",
    "please find attached",
    "dear sir or madam",
    "to whom it may concern",
    "most relevant portfolio evidence",
    "my background is directly relevant",
    "the brief emphasises",
    "relevant evidence",
    "application strategy",
)


def test_plan_requires_owner_approval() -> None:
    service = CoverLetterPlanService(DeterministicCoverLetterPlanner())
    with pytest.raises(CoverLetterPlanGateError, match="owner_approved_to_plan"):
        service.plan(
            strategy_from_payload(),
            minimal_profile(),
            options=CoverLetterPlanOptions(owner_approved_to_plan=False),
        )


def test_material_benefit_gate_blocks_bronze_without_override() -> None:
    service = CoverLetterPlanService(DeterministicCoverLetterPlanner())
    with pytest.raises(CoverLetterPlanGateError, match="consider_cover_letter"):
        service.plan(
            bronze_strategy(),
            minimal_profile(),
            options=CoverLetterPlanOptions(owner_approved_to_plan=True),
        )


def test_material_benefit_override_allows_bronze() -> None:
    plan = make_plan(strategy=bronze_strategy(), override_material_benefit=True)
    assert plan.material_benefit_override is True
    assert plan.owner_review_recommended is True
    assert plan.company_alignment.company
    assert plan.role_motivation.role_title


def test_platinum_tier_allows_without_override() -> None:
    plan = make_plan(strategy=strategy_from_payload())
    assert plan.material_benefit_override is False
    assert plan.company_alignment.company
    assert plan.role_motivation.role_title


def test_generate_requires_plan_approval() -> None:
    plan = make_plan()
    with pytest.raises(CoverLetterGenerationGateError, match="cover_letter_plan_approved"):
        CoverLetterGenerationService().generate(
            strategy_from_payload(),
            minimal_profile(),
            plan,
            options=CoverLetterGenerationOptions(cover_letter_plan_approved=False),
        )


def test_letter_references_company_role_and_portfolio() -> None:
    letter = make_letter()
    body = " ".join(letter.paragraphs).casefold()
    assert letter.company.casefold() in body or letter.company in letter.rendered_markdown
    assert letter.role_title
    assert letter.company in letter.rendered_markdown
    assert letter.role_title in letter.rendered_markdown
    assert letter.owner_review_required is True
    assert letter.composition_source == "deterministic_composition"
    plan = make_plan()
    if plan.strongest_projects:
        assert any(
            project.project_name.casefold() in body
            for project in plan.strongest_projects
        )


def test_letter_avoids_generic_and_planner_boilerplate() -> None:
    letter = make_letter()
    plain = letter.rendered_markdown.casefold()
    for phrase in _FORBIDDEN:
        assert phrase not in plain
    assert "what drew me" in plain
    assert "kind regards" in plain
    assert "shaping the future" not in plain
    assert "demonstrates operational intelligence capability" not in plain


def test_opening_reads_as_attraction_not_jd_dump() -> None:
    letter = make_letter()
    opening = letter.paragraphs[0]
    assert opening.startswith("What drew me")
    assert "the brief" not in opening.casefold()
    assert "the role emphasises" not in opening.casefold()
    assert "chance to Build" not in opening
    assert "chance to Design" not in opening


def test_letter_includes_collaboration_philosophy_and_portfolio_body() -> None:
    letter = make_letter()
    body = " ".join(letter.paragraphs).casefold()
    assert "collaborat" in body
    assert "architecture-first" in body
    assert "portfolio" in body
    assert "journey.chaseriskandcompliance.com.au" in body
    assert "working software" in body or "live demonstration" in body
    assert "—" not in letter.rendered_markdown
    assert "–" not in letter.rendered_markdown


def test_projects_explained_in_plain_english_when_profile_known() -> None:
    try:
        profile = CareerProfileService().load()
    except Exception:
        pytest.skip("Career Profile YAML not available")
    if not any(p.id == "operational-intelligence-copilot" for p in profile.projects):
        pytest.skip("Expected portfolio projects not present")
    strategy = strategy_from_payload()
    letter = make_letter(
        profile=profile,
        strategy=strategy,
        override_material_benefit=True,
    )
    body = " ".join(letter.paragraphs).casefold()
    assert "demonstrates operational intelligence capability" not in body
    assert "the business value is" not in body
    assert "this demonstrates" not in body
    assert "maps directly" not in body
    assert "—" not in " ".join(letter.paragraphs)
    # Engineering-first framing should surface for known projects.
    assert "engineering" in body or "deterministic" in body or "llm" in body


def test_project_selection_prefers_jd_fit_over_default_order() -> None:
    try:
        profile = CareerProfileService().load()
    except Exception:
        pytest.skip("Career Profile YAML not available")
    required = {
        "payroll-diagnostics-engine",
        "public-holiday-entitlements",
        "governance-document-rag",
        "career-intelligence-copilot",
    }
    if not required.issubset({p.id for p in profile.projects}):
        pytest.skip("Expected portfolio projects not present")

    compliance = strategy_from_payload(
        job_analysis=job_analysis(
            responsibilities=[
                {
                    "description": (
                        "Build deterministic payroll compliance rules engines "
                        "and entitlement checks for HR teams"
                    ),
                    "evidence": [
                        {
                            "excerpt": "deterministic payroll compliance rules",
                            "section": "responsibilities",
                        }
                    ],
                }
            ],
            technologies=[
                {
                    "name": "Python",
                    "level": "required",
                    "evidence": [
                        {"excerpt": "Python required", "section": "requirements"}
                    ],
                }
            ],
            posting={
                "raw_text": (
                    "Compliance Engineer. Deterministic business rules, payroll "
                    "diagnostics, public holiday entitlements, HR compliance."
                ),
                "title": "Compliance Rules Engineer",
                "company": "Rules Co",
            },
        )
    )
    llm = strategy_from_payload(
        job_analysis=job_analysis(
            responsibilities=[
                {
                    "description": (
                        "Design LLM and agentic workflows with RAG over "
                        "governance documents"
                    ),
                    "evidence": [
                        {
                            "excerpt": "LLM and agentic workflows with RAG",
                            "section": "responsibilities",
                        }
                    ],
                }
            ],
            technologies=[
                {
                    "name": "LangChain",
                    "level": "required",
                    "evidence": [
                        {"excerpt": "LangChain", "section": "requirements"}
                    ],
                },
                {
                    "name": "OpenAI",
                    "level": "required",
                    "evidence": [{"excerpt": "OpenAI", "section": "requirements"}],
                },
            ],
            posting={
                "raw_text": (
                    "AI Engineer. LLM applications, agentic workflows, RAG, "
                    "document intelligence, governance, evaluation."
                ),
                "title": "LLM Application Engineer",
                "company": "Agent Co",
            },
        )
    )
    compliance_plan = make_plan(profile=profile, strategy=compliance)
    llm_plan = make_plan(profile=profile, strategy=llm)
    compliance_ids = [p.project_id for p in compliance_plan.strongest_projects]
    llm_ids = [p.project_id for p in llm_plan.strongest_projects]
    assert compliance_ids != llm_ids
    assert any(
        pid in {"payroll-diagnostics-engine", "public-holiday-entitlements"}
        for pid in compliance_ids
    )
    assert any(
        pid
        in {
            "career-intelligence-copilot",
            "governance-document-rag",
            "operational-intelligence-copilot",
        }
        for pid in llm_ids
    )
    for project in compliance_plan.strongest_projects:
        assert project.selection_reason
        assert project.business_outcome
        assert project.fit_focus



def test_letter_includes_signature_block() -> None:
    letter = make_letter()
    markdown = letter.rendered_markdown
    assert "Kind regards," in markdown
    assert "linkedin.com/in/david-cropper" in markdown.casefold()
    assert "journey.chaseriskandcompliance.com.au" in markdown.casefold()
    assert "github.com/dcrops" in markdown.casefold()


def test_composition_is_deterministic() -> None:
    strategy = strategy_from_payload()
    profile = minimal_profile()
    first = make_letter(profile=profile, strategy=strategy)
    second = make_letter(profile=profile, strategy=strategy)
    assert first.paragraphs == second.paragraphs
    assert first.rendered_markdown == second.rendered_markdown


def test_draft_writer_writes_markdown_html_and_json(tmp_path: Path) -> None:
    letter = make_letter()
    plan = make_plan()
    result = write_cover_letter_drafts(letter, plan, output_dir=tmp_path)
    assert result.markdown_path.exists()
    assert result.html_path is not None and result.html_path.exists()
    assert result.json_path.exists()
    assert result.plan_json_path.exists()
    markdown = result.markdown_path.read_text(encoding="utf-8")
    html_document = result.html_path.read_text(encoding="utf-8")
    assert letter.company in markdown
    assert letter.role_title in markdown
    assert "Owner review required" in markdown
    assert "<!DOCTYPE html>" in html_document
    assert letter.full_name in html_document
    assert "cover-letter" in html_document
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert payload["owner_review_required"] is True


def test_html_renderer_matches_markdown_content() -> None:
    letter = make_letter()
    document = render_html(letter)
    assert letter.full_name in document
    assert letter.company in document
    assert letter.role_title in document
    for paragraph in letter.paragraphs:
        assert paragraph[:40] in document


def test_default_generated_dir_under_cover_letters() -> None:
    path = default_generated_dir(Path("/repo"))
    assert path.as_posix().endswith("career-documents/cover-letters/generated")


def test_live_profile_bluefin_style_plan_has_projects() -> None:
    """Smoke against the real Career Profile when available."""
    try:
        profile = CareerProfileService().load()
    except Exception:
        pytest.skip("Career Profile YAML not available")
    if not profile.projects:
        pytest.skip("Profile has no projects")
    strategy = strategy_from_payload()
    if strategy.portfolio_emphasis:
        letter = make_letter(profile=profile, strategy=strategy, override_material_benefit=True)
        assert letter.paragraphs
        plain = letter.rendered_markdown.casefold()
        assert "i am writing to apply" not in plain
        assert "most relevant portfolio evidence" not in plain
