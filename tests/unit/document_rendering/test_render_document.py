"""Tests for render-only Markdown → HTML → PDF (no generation)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from career_intelligence.document_rendering import (
    DocumentRenderInputError,
    UnsupportedDocumentTypeError,
    render_document_from_markdown,
)
from career_intelligence.document_rendering.cover_letter_markdown import (
    parse_cover_letter_markdown,
)


_COVER_LETTER_MD = """# David Cropper

**AI Engineer - Example Corp**

---

Hello,

Owner-edited opening paragraph with a unique token ALPHA_EDIT_TOKEN.

Second paragraph about architecture and delivery.

Third paragraph inviting a technical conversation.

Kind regards,

David Cropper

djcropster@gmail.com
0400 811 545
Melbourne, VIC
**LinkedIn:** [www.linkedin.com/in/david-cropper](https://www.linkedin.com/in/david-cropper/)
**Portfolio:** [journey.chaseriskandcompliance.com.au](https://journey.chaseriskandcompliance.com.au/)
**GitHub:** [github.com/dcrops](https://github.com/dcrops)
"""

_CV_MD = """# David Cropper

Melbourne, VIC · [djcropster@gmail.com](mailto:djcropster@gmail.com) · [0400 811 545](tel:+61400811545)
LinkedIn: [https://www.linkedin.com/in/david-cropper/](https://www.linkedin.com/in/david-cropper/)
Portfolio: [https://journey.chaseriskandcompliance.com.au/](https://journey.chaseriskandcompliance.com.au/)
GitHub: [https://github.com/dcrops](https://github.com/dcrops)

**AI Engineer**

---

## Professional Summary

CV owner-edited summary with unique token BETA_EDIT_TOKEN.

## Selected Engineering Highlights

- Built production AI systems with clear engineering accountability.
- Published portfolio demonstrations.

## Core Skills

**Python** · **FastAPI**

**Also:** Docker · Git

## Professional Experience

### AI Engineer — Independent

*Jan 2025 – Present · Independent engineering · Melbourne, VIC*

- Delivered reviewable AI systems.
- Validated with evidence.

**Technologies:** **Python**, FastAPI

## Featured AI Projects

### Sample Project

**Overview:** A small demonstration system.

**Engineering Highlights:**

- Deterministic decision support

**Technology Stack:** Python · FastAPI
"""


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def test_cover_letter_markdown_renders_html_pdf_and_preserves_edits(
    tmp_path: Path,
) -> None:
    md = _write(
        tmp_path / "cover-letters" / "generated" / "example.md",
        _COVER_LETTER_MD,
    )
    before = md.read_text(encoding="utf-8")
    result = render_document_from_markdown(md)
    assert result.kind == "cover_letter"
    assert result.markdown_unchanged is True
    assert md.read_text(encoding="utf-8") == before
    html = result.html_path.read_text(encoding="utf-8")
    assert "ALPHA_EDIT_TOKEN" in html
    assert 'href="https://www.linkedin.com/in/david-cropper/"' in html
    assert 'href="mailto:djcropster@gmail.com"' in html
    assert html.lstrip().lower().startswith("<!doctype html>")
    pdf = result.pdf_path.read_bytes()
    assert pdf.startswith(b"%PDF")


def test_cv_markdown_renders_html_pdf_and_preserves_edits(tmp_path: Path) -> None:
    md = _write(tmp_path / "cv" / "generated" / "example.md", _CV_MD)
    before = md.read_text(encoding="utf-8")
    result = render_document_from_markdown(md)
    assert result.kind == "cv"
    assert md.read_text(encoding="utf-8") == before
    html = result.html_path.read_text(encoding="utf-8")
    assert "BETA_EDIT_TOKEN" in html
    assert 'href="https://github.com/dcrops"' in html
    assert "Professional Summary" in html
    pdf = result.pdf_path.read_bytes()
    assert pdf.startswith(b"%PDF")


def test_missing_markdown_fails_clearly(tmp_path: Path) -> None:
    missing = tmp_path / "cover-letters" / "generated" / "missing.md"
    with pytest.raises(DocumentRenderInputError, match="not found"):
        render_document_from_markdown(missing)


def test_unsupported_document_type_fails(tmp_path: Path) -> None:
    md = _write(tmp_path / "notes" / "random.md", "# Notes\n\nNot a CV or letter.\n")
    with pytest.raises(UnsupportedDocumentTypeError):
        render_document_from_markdown(md)


def test_render_only_never_calls_planner_composer_or_openai(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    md = _write(
        tmp_path / "cover-letters" / "generated" / "guard.md",
        _COVER_LETTER_MD,
    )

    import ast

    import career_intelligence.document_rendering.service as service_mod

    tree = ast.parse(Path(service_mod.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
            imported.add(node.module)
    for banned in (
        "openai",
        "career_intelligence.cover_letter.composer",
        "career_intelligence.cover_letter.deterministic_planner",
        "career_intelligence.cv_generation.deterministic_planner",
        "career_intelligence.job_analysis",
        "career_intelligence.opportunity_assessment",
        "career_intelligence.portfolio_matching",
        "career_intelligence.application_strategy",
    ):
        assert banned not in imported
        assert not any(item.startswith(banned + ".") for item in imported)

    called = {"planner": False, "composer": False, "openai": False}

    def mark_planner(*_a, **_k):  # noqa: ANN001
        called["planner"] = True
        raise AssertionError("planner executed")

    def mark_composer(*_a, **_k):  # noqa: ANN001
        called["composer"] = True
        raise AssertionError("composer executed")

    monkeypatch.setattr(
        "career_intelligence.cover_letter.deterministic_planner."
        "DeterministicCoverLetterPlanner.plan",
        mark_planner,
        raising=False,
    )
    monkeypatch.setattr(
        "career_intelligence.cover_letter.composer.compose_cover_letter_paragraphs",
        mark_composer,
        raising=False,
    )

    class _Boom:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
            called["openai"] = True
            raise AssertionError("OpenAI executed")

    monkeypatch.setitem(__import__("sys").modules, "openai", MagicMock(OpenAI=_Boom))

    result = render_document_from_markdown(md)
    assert result.pdf_path.is_file()
    assert called == {"planner": False, "composer": False, "openai": False}


def test_parse_cover_letter_preserves_paragraph_text() -> None:
    parsed = parse_cover_letter_markdown(_COVER_LETTER_MD)
    assert parsed.company == "Example Corp"
    assert any("ALPHA_EDIT_TOKEN" in paragraph for paragraph in parsed.paragraphs)
    assert parsed.contact["github_url"] == "https://github.com/dcrops"
