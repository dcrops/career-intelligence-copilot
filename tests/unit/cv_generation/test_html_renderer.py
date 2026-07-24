"""Unit tests for TailoredCv HTML rendering and draft HTML writes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from career_intelligence.cv_generation import (
    ContactDetails,
    CvGenerationOptions,
    CvGenerationService,
    CvHtmlRenderError,
    render_html,
    write_tailored_cv_drafts,
)
from career_intelligence.cv_generation.draft_writer import DraftWriteResult
from tests.unit.cv_generation.helpers import (
    make_cv,
    make_plan,
    minimal_profile,
    strategy_from_payload,
)


def _make_cv_with_contact():
    profile = minimal_profile()
    plan = make_plan(profile=profile)
    strategy = strategy_from_payload()
    return CvGenerationService().generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            contact=ContactDetails(
                email="djcropster@gmail.com",
                phone="0400 811 545",
                location="Melbourne, VIC",
                linkedin_url="https://www.linkedin.com/in/david-cropper/",
                portfolio_url="https://journey.chaseriskandcompliance.com.au/",
                github_url="https://github.com/dcrops",
            ),
        ),
    ), plan


def test_render_html_is_complete_standalone_utf8_document() -> None:
    cv = make_cv()
    document = render_html(cv)
    assert document.startswith("<!DOCTYPE html>")
    assert '<html lang="en">' in document
    assert '<meta charset="utf-8" />' in document
    assert "<title>" in document
    assert cv.full_name in document
    assert "</html>" in document
    document.encode("utf-8")


def test_render_html_headings_lists_bold_and_italic() -> None:
    cv = make_cv()
    cv = cv.model_copy(
        update={
            "summary": "Lead with **Python** and *FastAPI* for AI systems.",
            "selected_engineering_highlights": [
                "Built **FastAPI** services with regression suites."
            ],
        }
    )
    document = render_html(cv)
    assert "<h1>" in document
    assert "<h2>Selected Engineering Highlights</h2>" in document
    assert "<ul>" in document
    assert "<li>" in document
    assert "<strong>Python</strong>" in document
    assert "<em>FastAPI</em>" in document
    assert "<strong>FastAPI</strong>" in document


def test_render_html_contact_links_are_clickable() -> None:
    cv, _plan = _make_cv_with_contact()
    document = render_html(cv)
    assert 'href="mailto:djcropster@gmail.com"' in document
    assert 'href="tel:+61400811545"' in document
    assert 'href="https://www.linkedin.com/in/david-cropper/"' in document
    assert 'href="https://journey.chaseriskandcompliance.com.au/"' in document
    assert 'href="https://github.com/dcrops"' in document
    assert "linkedin.com/in/david-cropper" in document
    assert "journey.chaseriskandcompliance.com.au" in document
    assert "github.com/dcrops" in document
    assert "<strong>LinkedIn:</strong>" in document
    assert "<strong>Portfolio:</strong>" in document
    assert "<strong>GitHub:</strong>" in document


def test_render_html_escapes_unsafe_characters() -> None:
    cv = make_cv()
    cv = cv.model_copy(
        update={
            "summary": 'Use <script>alert("x")</script> & "quotes".',
        }
    )
    document = render_html(cv)
    assert "<script>" not in document
    assert "&lt;script&gt;" in document
    assert "&amp;" in document
    assert "&quot;quotes&quot;" in document


def test_render_html_is_deterministic() -> None:
    cv = make_cv()
    assert render_html(cv) == render_html(cv)


def test_write_tailored_cv_drafts_writes_html_beside_markdown(
    tmp_path: Path,
) -> None:
    cv, plan = _make_cv_with_contact()
    result = write_tailored_cv_drafts(
        cv,
        plan,
        output_dir=tmp_path,
        stem="test_stem",
    )
    assert result.markdown_path == tmp_path / "test_stem.md"
    assert result.html_path == tmp_path / "test_stem.html"
    assert result.json_path == tmp_path / "test_stem.json"
    assert result.plan_json_path == tmp_path / "test_stem.tailoring_plan.json"
    assert result.html_path is not None
    assert result.html_path.is_file()
    assert result.markdown_path.is_file()
    html = result.html_path.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert result.stem == "test_stem"
    assert result.html_path.stem == result.markdown_path.stem


def test_write_tailored_cv_drafts_preserves_markdown_and_json(
    tmp_path: Path,
) -> None:
    plan = make_plan()
    cv = make_cv(plan=plan)
    result = write_tailored_cv_drafts(cv, plan, output_dir=tmp_path, stem="keep")
    assert result.markdown_path.read_text(encoding="utf-8") == cv.rendered_markdown
    assert '"owner_review_required": true' in result.json_path.read_text(
        encoding="utf-8"
    )
    assert result.html_path is not None
    assert result.html_path.is_file()


def test_html_not_written_when_gate_blocks_tailored_cv(tmp_path: Path) -> None:
    """Plan-only / gated drafts expose html_path=None and must not create HTML."""
    stem = "gated_stem"
    plan_path = tmp_path / f"{stem}.tailoring_plan.json"
    plan_path.write_text("{}", encoding="utf-8")
    drafts = DraftWriteResult(
        output_dir=tmp_path,
        stem=stem,
        markdown_path=tmp_path / f"{stem}.md",
        json_path=tmp_path / f"{stem}.json",
        plan_json_path=plan_path,
        html_path=None,
    )
    assert drafts.html_path is None
    assert not (tmp_path / f"{stem}.html").exists()
    assert not drafts.markdown_path.exists()
    assert not drafts.json_path.exists()


def test_write_fails_clearly_when_html_render_breaks(tmp_path: Path) -> None:
    plan = make_plan()
    cv = make_cv(plan=plan)
    with (
        patch(
            "career_intelligence.cv_generation.draft_writer.render_html",
            side_effect=CvHtmlRenderError("boom"),
        ),
        pytest.raises(CvHtmlRenderError, match="boom"),
    ):
        write_tailored_cv_drafts(cv, plan, output_dir=tmp_path, stem="fail")
    assert not (tmp_path / "fail.html").exists()
    assert not (tmp_path / "fail.md").exists()
    assert not (tmp_path / "fail.json").exists()
    assert not (tmp_path / "fail.tailoring_plan.json").exists()
