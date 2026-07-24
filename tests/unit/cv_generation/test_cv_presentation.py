"""Presentation-system tests for shared Master / tailored CV CSS."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from career_intelligence.cv_generation import (
    clear_cv_print_css_cache,
    inject_cv_print_css,
    load_cv_print_css,
    master_html_uses_canonical_css,
    render_html,
    sync_master_cv_html,
)
from career_intelligence.cv_generation.css_sync import (
    CSS_BEGIN,
    CSS_END,
    build_embedded_css_block,
)
from career_intelligence.cv_generation.errors import CvHtmlRenderError
from tests.unit.cv_generation.helpers import make_cv
from tests.unit.cv_generation.test_html_renderer import _make_cv_with_contact

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MASTER_HTML = _REPO_ROOT / "career-documents" / "cv" / "master_ai_engineer_cv.html"


def test_canonical_css_has_readable_a4_typography() -> None:
    clear_cv_print_css_cache()
    css = load_cv_print_css()
    assert "@page" in css
    assert "size: A4" in css
    assert re.search(r"@page\s*\{[^}]*margin:\s*1[6-9]mm|2\dmm", css, re.DOTALL)
    assert re.search(r"font-size:\s*11pt", css)
    assert re.search(r"line-height:\s*1\.(4|45|5)", css)
    assert "http://" not in css
    assert "url(" not in css


def test_canonical_css_has_generous_section_and_list_spacing() -> None:
    css = load_cv_print_css()
    # Spacings greater than the previous compressed stylesheet.
    assert "margin: 33px 0 10px" in css  # h2 chapter separation
    assert "margin: 0 0 9px" in css  # paragraphs
    assert "margin: 0 0 6px" in css  # list items
    assert "margin: 0 0 30px" in css  # experience/project separation
    assert "margin: 17px 0 6px" in css  # technology stack breathing room


def test_page_break_rules_allow_long_entries_to_split() -> None:
    css = load_cv_print_css()
    experience_block = re.search(
        r"\.experience,\s*\n\.project\s*\{([^}]+)\}",
        css,
    )
    assert experience_block is not None
    rules = experience_block.group(1)
    assert "page-break-inside: auto" in rules or "break-inside: auto" in rules
    assert "page-break-inside: avoid" not in rules
    assert "break-after: avoid-page" in css or "page-break-after: avoid" in css


def test_master_html_embeds_canonical_css() -> None:
    clear_cv_print_css_cache()
    html = _MASTER_HTML.read_text(encoding="utf-8")
    assert CSS_BEGIN in html and CSS_END in html
    assert master_html_uses_canonical_css(html)
    assert "mailto:djcropster@gmail.com" in html
    assert "end-to-end AI applications" in html


def test_inject_and_sync_keep_master_in_lockstep(tmp_path: Path) -> None:
    clear_cv_print_css_cache()
    sample = (
        "<!DOCTYPE html><html><head>\n"
        f"{build_embedded_css_block('body { font-size: 1pt; }')}\n"
        "</head><body><h1>Sample</h1></body></html>\n"
    )
    path = tmp_path / "master.html"
    path.write_text(sample, encoding="utf-8")
    sync_master_cv_html(path)
    updated = path.read_text(encoding="utf-8")
    assert master_html_uses_canonical_css(updated)
    assert "font-size: 11pt" in updated
    assert "Sample" in updated


def test_tailored_html_uses_same_canonical_css() -> None:
    clear_cv_print_css_cache()
    css = load_cv_print_css()
    document = render_html(make_cv())
    assert css.strip() in document
    assert "size: A4" in document
    assert "font-size: 11pt" in document
    assert 'class="header-rule"' in document


def test_presentation_refactor_does_not_change_tailored_markdown_content() -> None:
    cv = make_cv()
    before = cv.rendered_markdown
    _ = render_html(cv)
    assert cv.rendered_markdown == before


def test_contact_links_remain_clickable_after_presentation_update() -> None:
    cv, _plan = _make_cv_with_contact()
    document = render_html(cv)
    assert 'href="mailto:djcropster@gmail.com"' in document
    assert 'href="tel:+61400811545"' in document
    assert 'href="https://www.linkedin.com/in/david-cropper/"' in document
    assert 'href="https://github.com/dcrops"' in document
    assert "<strong>LinkedIn:</strong>" in document
    assert "<strong>Portfolio:</strong>" in document
    assert "<strong>GitHub:</strong>" in document
    # Do not bold email/phone/location lines via label wrappers.
    assert "<strong>djcropster@gmail.com</strong>" not in document
    assert "<strong>0400 811 545</strong>" not in document


def test_inject_requires_markers() -> None:
    with pytest.raises(CvHtmlRenderError):
        inject_cv_print_css("<html></html>")
