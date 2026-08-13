"""Unit tests for AAS-0 Markdown/PDF freshness (HTML content oracle)."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.artefact_freshness import (  # noqa: E402
    PdfFreshnessStatus,
    assess_markdown_pdf_freshness,
    render_html_from_markdown_text,
)

_MINIMAL_CV = """# Test Candidate

**AI Engineer**

## Summary

Builds reliable software.

## Experience

### Example Co

**AI Engineer** | 2020–Present

- Shipped systems
"""


def _touch(path: Path, when: float) -> None:
    os.utime(path, (when, when))


def _write_triplet(
    tmp: Path,
    *,
    md_newer: bool,
    html_content: str | None = None,
    omit_html: bool = False,
) -> tuple[Path, Path, Path | None]:
    generated = tmp / "career-documents" / "cv" / "generated"
    generated.mkdir(parents=True)
    md = generated / "doc.md"
    pdf = generated / "doc.pdf"
    html = generated / "doc.html"
    md.write_text(_MINIMAL_CV, encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4 fake")
    base = time.time() - 100.0
    if omit_html:
        _touch(pdf, base)
        _touch(md, base + 50.0 if md_newer else base - 10.0)
        return md, pdf, None

    if html_content is None:
        html_content = render_html_from_markdown_text(md, md.read_text(encoding="utf-8"))
    html.write_text(html_content, encoding="utf-8", newline="\n")
    _touch(pdf, base)
    _touch(html, base)
    _touch(md, base + 50.0 if md_newer else base - 10.0)
    return md, pdf, html


def test_md_newer_html_identical_is_non_blocking(tmp_path: Path) -> None:
    md, pdf, _html = _write_triplet(tmp_path, md_newer=True)
    result = assess_markdown_pdf_freshness(
        markdown_path=md,
        pdf_path=pdf,
        label="CV",
    )
    assert result.blocking is False
    assert result.status is PdfFreshnessStatus.MTIME_TOUCH_ONLY
    assert "deterministic HTML content is unchanged" in result.message


def test_md_newer_html_mismatch_is_blocking(tmp_path: Path) -> None:
    md, pdf, _html = _write_triplet(
        tmp_path,
        md_newer=True,
        html_content="<html><body>stale sibling</body></html>\n",
    )
    result = assess_markdown_pdf_freshness(
        markdown_path=md,
        pdf_path=pdf,
        label="CV",
    )
    assert result.blocking is True
    assert result.status is PdfFreshnessStatus.CONTENT_DRIFT
    assert "content may have drifted" in result.message
    assert "render-only refresh" in result.message


def test_md_newer_html_missing_is_blocking(tmp_path: Path) -> None:
    md, pdf, _ = _write_triplet(tmp_path, md_newer=True, omit_html=True)
    result = assess_markdown_pdf_freshness(
        markdown_path=md,
        pdf_path=pdf,
        label="CV",
    )
    assert result.blocking is True
    assert result.status is PdfFreshnessStatus.HTML_MISSING
    assert "authoritative HTML is missing" in result.message


def test_md_older_or_equal_preserves_ok(tmp_path: Path) -> None:
    md, pdf, _html = _write_triplet(tmp_path, md_newer=False)
    result = assess_markdown_pdf_freshness(
        markdown_path=md,
        pdf_path=pdf,
        label="CV",
    )
    assert result.blocking is False
    assert result.status is PdfFreshnessStatus.OK
    assert "not newer than PDF" in result.message


def test_pdf_byte_equality_is_not_required(tmp_path: Path) -> None:
    """Freshness must not depend on PDF bytes (non-deterministic renders)."""
    md, pdf, _html = _write_triplet(tmp_path, md_newer=True)
    pdf.write_bytes(b"%PDF-1.4 completely-different-bytes")
    # Keep MD newer than PDF after rewrite.
    _touch(pdf, time.time() - 100.0)
    _touch(md, time.time())
    result = assess_markdown_pdf_freshness(
        markdown_path=md,
        pdf_path=pdf,
        label="CV",
    )
    assert result.blocking is False
    assert result.status is PdfFreshnessStatus.MTIME_TOUCH_ONLY
