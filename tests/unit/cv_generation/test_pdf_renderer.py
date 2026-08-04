"""Unit tests for HTML→PDF renderer (shared CV / cover-letter path)."""

from __future__ import annotations

import pytest

from career_intelligence.cv_generation.pdf_renderer import (
    PdfRenderError,
    render_pdf_from_html,
)


def test_render_pdf_from_html_produces_pdf_bytes() -> None:
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><title>T</title>
<style>@page { size: A4; margin: 18mm; } a { color: blue; }</style>
</head><body>
<h1>David Cropper</h1>
<p><a href="https://example.com/portfolio">Portfolio</a></p>
<p>AI Engineer applying for a calibrated role.</p>
</body></html>
"""
    pdf = render_pdf_from_html(html)
    assert pdf.startswith(b"%PDF")
    assert b"/URI" in pdf or b"example.com" in pdf or len(pdf) > 500


def test_render_pdf_rejects_empty_and_incomplete_html() -> None:
    with pytest.raises(PdfRenderError, match="empty"):
        render_pdf_from_html("")
    with pytest.raises(PdfRenderError, match="complete HTML"):
        render_pdf_from_html("<html><body>no doctype</body></html>")
