"""Focused tests for the Slice 2 bounded cover-letter evidence boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.application_package.prose_guard import (
    should_preserve_owner_markdown,
)
from career_intelligence.cover_letter import (
    CoverLetterGenerationGateError,
    CoverLetterGenerationOptions,
    CoverLetterGenerationService,
    CoverLetterGenerationValidationError,
)
from career_intelligence.cover_letter.bounded_composer import (
    CoverLetterExtraction,
    FixtureCoverLetterComposer,
    load_cover_letter_instructions,
)
from career_intelligence.cover_letter.bounded_generation import (
    BoundedCoverLetterService,
    experiment_stem,
    validate_composed_paragraphs,
    write_evidence_pack,
    write_truth_report,
)
from career_intelligence.cover_letter.evidence_pack import build_cover_letter_evidence_pack
from career_intelligence.cover_letter.html_renderer import render_html
from career_intelligence.cover_letter.render_markdown import render_markdown
from career_intelligence.profile.models import CareerProfile
from tests.unit.cover_letter.helpers import (
    default_contact,
    make_letter,
    make_plan,
    minimal_profile,
    strategy_from_payload,
)


class _InventingComposer:
    def __init__(self, paragraphs: list[str]) -> None:
        self._paragraphs = paragraphs

    def compose(self, pack: object) -> CoverLetterExtraction:
        return CoverLetterExtraction(paragraphs=self._paragraphs)


def _independent_profile() -> CareerProfile:
    profile = minimal_profile()
    payload = profile.model_dump(mode="json")
    payload["experience"] = [
        {
            "id": "independent-ai",
            "kind": "independent_engineering",
            "organisation": "Chase Risk & Compliance",
            "title": "AI Engineer - Independent Research & Development",
            "start_date": "2025-12-01",
            "end_date": None,
            "location": "Melbourne",
            "highlights": [
                "Built independent AI portfolio systems with reviewable outputs."
            ],
            "technologies": ["Python", "OpenAI APIs"],
        },
        {
            "id": "example-role",
            "kind": "employment",
            "organisation": "Example Company",
            "title": "Data Engineer",
            "start_date": "2022-01-01",
            "end_date": "2023-01-01",
            "location": "Melbourne",
            "highlights": ["Built validated data pipelines."],
            "technologies": ["Python"],
        },
        {
            "id": "example-test-role",
            "kind": "employment",
            "organisation": "Test Org",
            "title": "Test Analyst",
            "start_date": "2018-01-01",
            "end_date": "2019-01-01",
            "location": "Melbourne",
            "highlights": ["Designed a Selenium automation framework."],
            "technologies": ["Selenium"],
        },
    ]
    payload["projects"] = [
        payload["projects"][0],
        {
            "id": "other-project",
            "name": "Operational Intelligence Copilot",
            "summary": "Turns operational data into explainable insights.",
            "technologies": ["FastAPI"],
            "outcomes": ["Decision makers get faster checkable insights."],
            "url": None,
            "demonstrates": ["Operational intelligence"],
        },
    ]
    return CareerProfile.model_validate(payload)


def _trajectory_profile() -> CareerProfile:
    """Data Engineer mentions automated testing; genuine Test Analyst exists earlier."""
    profile = _independent_profile()
    payload = profile.model_dump(mode="json")
    payload["identity"]["summary"] = (
        "Experienced engineer with 10+ years across testing, automation, "
        "data engineering and applied AI engineering."
    )
    payload["experience"] = [
        {
            "id": "independent-ai",
            "kind": "independent_engineering",
            "organisation": "Chase Risk & Compliance",
            "title": "AI Engineer - Independent Research & Development",
            "start_date": "2025-12-01",
            "end_date": None,
            "location": "Melbourne",
            "highlights": [
                "Built independent AI portfolio systems with reviewable outputs."
            ],
            "technologies": ["Python", "OpenAI APIs"],
        },
        {
            "id": "example-role",
            "kind": "employment",
            "organisation": "Example Company",
            "title": "Data Engineer",
            "start_date": "2020-03-01",
            "end_date": "2023-10-01",
            "location": "Melbourne",
            "highlights": [
                "Developed enterprise data pipelines with Git and automated testing practices."
            ],
            "technologies": ["Python", "SQL"],
        },
        {
            "id": "short-test-return",
            "kind": "employment",
            "organisation": "Brief Testing Co",
            "title": "Test Analyst",
            "start_date": "2019-08-01",
            "end_date": "2019-09-01",
            "location": "Melbourne",
            "highlights": ["Returned for a short engagement."],
            "technologies": [],
        },
        {
            "id": "example-test-role",
            "kind": "employment",
            "organisation": "Test Org",
            "title": "Test Analyst",
            "start_date": "2015-01-01",
            "end_date": "2018-10-01",
            "location": "Melbourne",
            "highlights": ["Designed and implemented an automation framework."],
            "technologies": ["Selenium"],
        },
    ]
    return CareerProfile.model_validate(payload)


def test_data_engineer_mentioning_automated_testing_is_not_testing_role() -> None:
    profile = _trajectory_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    pack = build_cover_letter_evidence_pack(
        profile=profile,
        strategy=strategy,
        plan=plan,
        contact=default_contact(),
    )
    testing_ids = [
        item.id
        for item in pack.experience
        if item.chapter == "commercial_testing_automation"
    ]
    de_ids = [
        item.id
        for item in pack.experience
        if item.chapter == "commercial_data_engineering"
    ]
    assert "example-role" not in testing_ids
    assert "example-role" in de_ids
    assert testing_ids[0] == "example-test-role"
    assert all(
        item.chapter != "commercial_testing_automation"
        for item in pack.experience
        if item.id == "example-role"
    )


def test_genuine_testing_employment_preserves_commercial_chronology() -> None:
    profile = _trajectory_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    pack = build_cover_letter_evidence_pack(
        profile=profile,
        strategy=strategy,
        plan=plan,
        contact=default_contact(),
    )
    chapter_names = [item.name for item in pack.career_trajectory.chapters]
    assert chapter_names == [
        "commercial_testing_automation",
        "commercial_data_engineering",
        "independent_ai_engineering",
    ]
    testing = next(
        item for item in pack.experience if item.id == "example-test-role"
    )
    data = next(item for item in pack.experience if item.id == "example-role")
    independent = next(
        item for item in pack.experience if item.id == "independent-ai"
    )
    assert testing.start_date < data.start_date < independent.start_date
    assert testing.relationship == "commercial_employment"
    assert data.relationship == "commercial_employment"
    assert independent.relationship == "independent_rd"
    claim = pack.career_trajectory.authorised_duration_claim or ""
    assert "10+" in claim
    assert "across" in claim.casefold()
    assert "testing" in claim.casefold()
    assert any("authorised duration" in item.casefold() for item in pack.constraints)
    assert any("do not imply 10+" in item.casefold() for item in pack.constraints)


def test_evidence_pack_contains_only_supported_experience_and_projects() -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    pack = build_cover_letter_evidence_pack(
        profile=profile,
        strategy=strategy,
        plan=plan,
        contact=default_contact(),
    )
    experience_ids = {item.id for item in pack.experience}
    assert "independent-ai" in experience_ids
    assert "example-role" in experience_ids
    assert "example-test-role" in experience_ids
    independent = next(item for item in pack.experience if item.id == "independent-ai")
    assert independent.relationship == "independent_rd"
    commercial = next(item for item in pack.experience if item.id == "example-role")
    assert commercial.relationship == "commercial_employment"
    assert pack.commercial_ai_employment is False
    assert pack.candidate_has_ml_expertise is False
    packed_projects = {item.id for item in pack.projects}
    assert "example-project" in packed_projects
    assert "other-project" not in packed_projects
    assert "Operational Intelligence Copilot" not in pack.allowed_project_names
    assert "TensorFlow" not in pack.allowed_technologies
    assert pack.contact.portfolio_url == default_contact().portfolio_url
    assert pack.contact.github_url == default_contact().github_url


def test_unsupported_project_and_ml_claims_are_not_supplied_and_are_rejected() -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    pack = build_cover_letter_evidence_pack(
        profile=profile,
        strategy=strategy,
        plan=plan,
        contact=default_contact(),
    )
    errors = validate_composed_paragraphs(
        [
            "I used TensorFlow at Google to productionise Operational Intelligence Copilot.",
            "That was commercial AI engineering employment.",
            "I would welcome a conversation.",
        ],
        pack,
        profile=profile,
    )
    assert any("tensorflow" in item.casefold() for item in errors)
    assert any("operational intelligence copilot" in item.casefold() for item in errors)


def test_independent_rd_is_distinguishable_from_commercial_employment() -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    pack = build_cover_letter_evidence_pack(
        profile=profile,
        strategy=strategy,
        plan=plan,
        contact=default_contact(),
    )
    independent = next(item for item in pack.experience if item.relationship == "independent_rd")
    assert "independent" in independent.title.casefold()
    errors = validate_composed_paragraphs(
        [
            "Example AI Co needs an AI Engineer.",
            "I was employed as an AI Engineer at Chase Risk & Compliance.",
            "Example Project helps teams inspect evidence.",
            "I would welcome a conversation.",
        ],
        pack,
        profile=profile,
    )
    assert any("commercial" in item for item in errors)


def test_contact_links_are_supplied_when_authoritative() -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    result = BoundedCoverLetterService(FixtureCoverLetterComposer()).compose(
        strategy,
        profile,
        plan,
        options=CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=default_contact(),
        ),
    )
    markdown = result.letter.rendered_markdown
    assert result.pack.contact.portfolio_url
    assert result.pack.contact.github_url
    assert result.pack.contact.portfolio_url in markdown
    assert result.pack.contact.github_url in markdown
    assert "**Portfolio:**" in markdown
    assert "**GitHub:**" in markdown
    body = "\n".join(result.letter.paragraphs)
    assert result.pack.contact.portfolio_url not in body
    assert result.pack.contact.github_url not in body
    assert any("portfolio" in paragraph.casefold() for paragraph in result.letter.paragraphs)
    assert any("github" in paragraph.casefold() for paragraph in result.letter.paragraphs)
    signature = markdown[markdown.casefold().index("kind regards,") :]
    assert "candidate@example.com" not in signature
    assert markdown.count("mailto:candidate@example.com") == 1
    html = render_html(result.letter)
    assert html.count("mailto:candidate@example.com") == 1
    signature_html = html[html.casefold().index('class="signature"') :]
    assert "mailto:" not in signature_html
    assert "github.com" not in signature_html


def test_evidence_pack_and_prompt_require_specific_open_close_and_portfolio_signpost() -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    pack = build_cover_letter_evidence_pack(
        profile=profile,
        strategy=strategy,
        plan=plan,
        contact=default_contact(),
    )
    constraints = " ".join(pack.constraints).casefold()
    assert "portfolio" in constraints and "github" in constraints
    assert "do not paste" in constraints
    assert "generic relevance" in constraints
    assert "generic conversation-request" in constraints
    assert pack.contact.portfolio_url
    assert pack.contact.github_url
    prompt = load_cover_letter_instructions().casefold()
    assert "portfolio / github" in prompt or "portfolio and github" in prompt
    assert "do not paste the urls" in prompt or "do not dump them" in prompt
    assert "generic relevance" in prompt
    assert "background-fit" in prompt
    assert "one or two sentences" in prompt
    assert "do not repeat the opening" in prompt


def test_bounded_generator_persists_distinct_artefact(tmp_path: Path) -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    service = BoundedCoverLetterService(FixtureCoverLetterComposer())
    result = service.compose(
        strategy,
        profile,
        plan,
        options=CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=default_contact(),
        ),
    )
    from career_intelligence.cover_letter import write_cover_letter_drafts

    opportunity_id = "opp_01KZQJY6AX3EGX7TGYTHR3ABG1"
    stem = experiment_stem(opportunity_id)
    assert stem != opportunity_id
    live_path = tmp_path / f"{opportunity_id}.md"
    live_path.write_text("LIVE PACKAGE MUST NOT CHANGE\n", encoding="utf-8")
    drafts = write_cover_letter_drafts(
        result.letter,
        plan,
        output_dir=tmp_path,
        stem=stem,
    )
    pack_path = tmp_path / f"{stem}.evidence_pack.json"
    write_evidence_pack(pack_path, result.pack)
    assert drafts.markdown_path != live_path
    assert live_path.read_text(encoding="utf-8") == "LIVE PACKAGE MUST NOT CHANGE\n"
    assert drafts.markdown_path.is_file()
    assert pack_path.is_file()
    assert result.letter.composition_source == "bounded_llm_composition"
    assert result.letter.owner_review_required is True


def test_truth_validation_runs_and_fails_closed(tmp_path: Path) -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    service = BoundedCoverLetterService(FixtureCoverLetterComposer())
    composed = service.compose(
        strategy,
        profile,
        plan,
        options=CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=default_contact(),
        ),
    )
    invented = (
        composed.letter.rendered_markdown.rstrip()
        + "\n\nI used TensorFlow in production.\n"
    )
    assessment = service.assess_truth(
        markdown=invented,
        profile=profile,
        artefact_path=str(tmp_path / "invented.md"),
        opportunity_id=None,
    )
    write_truth_report(tmp_path / "invented.truth.json", assessment.report)
    assert assessment.report.detection_performed is True
    assert assessment.report.validation_performed is True
    assert assessment.external_use_allowed is False
    assert assessment.report.outcome in {"fail", "review_required"}


def test_owner_edit_protection_remains_intact(tmp_path: Path) -> None:
    path = tmp_path / "letter.md"
    path.write_text("generated\n", encoding="utf-8")
    fingerprint = "abc123"
    assert should_preserve_owner_markdown(path, fingerprint, regenerate=False) is True
    matching = __import__(
        "career_intelligence.application_package.prose_guard",
        fromlist=["markdown_sha256"],
    ).markdown_sha256(path)
    assert should_preserve_owner_markdown(path, matching, regenerate=False) is False
    assert should_preserve_owner_markdown(path, matching, regenerate=True) is False


def test_legacy_cover_letter_service_remains_deterministic() -> None:
    letter = make_letter()
    assert letter.composition_source == "deterministic_composition"
    with pytest.raises(CoverLetterGenerationGateError, match="cover_letter_plan_approved"):
        BoundedCoverLetterService(FixtureCoverLetterComposer()).compose(
            strategy_from_payload(),
            minimal_profile(),
            make_plan(),
            options=CoverLetterGenerationOptions(cover_letter_plan_approved=False),
        )
    again = CoverLetterGenerationService().generate(
        strategy_from_payload(),
        minimal_profile(),
        make_plan(),
        options=CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=default_contact(),
        ),
    )
    assert again.composition_source == "deterministic_composition"


def test_inventing_composer_fails_closed_without_persist() -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    service = BoundedCoverLetterService(
        _InventingComposer(
            [
                "I am excited to apply and used slideware.",
                "I was employed as an AI Engineer shipping TensorFlow.",
                "Operational Intelligence Copilot was client delivery.",
            ]
        )
    )
    with pytest.raises(CoverLetterGenerationValidationError):
        service.compose(
            strategy,
            profile,
            plan,
            options=CoverLetterGenerationOptions(
                cover_letter_plan_approved=True,
                contact=default_contact(),
            ),
        )


def test_fixture_composer_letter_renders() -> None:
    profile = _independent_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    result = BoundedCoverLetterService(FixtureCoverLetterComposer()).compose(
        strategy,
        profile,
        plan,
        options=CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=default_contact(),
        ),
    )
    markdown = render_markdown(result.letter)
    assert result.letter.company in markdown
    assert result.letter.role_title in markdown
    assert "independent" in " ".join(result.letter.paragraphs).casefold()
    assert "slideware" not in markdown.casefold()
    assert "prototype theatre" not in markdown.casefold()
