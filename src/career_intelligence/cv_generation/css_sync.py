"""Synchronise canonical CV print CSS into standalone Master HTML.

``assets/cv_print.css`` is the single presentation source. The Master CV HTML
embeds that CSS between markers so the file remains standalone (no external
stylesheet dependency for Edge/print).
"""

from __future__ import annotations

import re
from pathlib import Path

from career_intelligence.cv_generation.errors import CvHtmlRenderError
from career_intelligence.cv_generation.html_renderer import (
    clear_cv_print_css_cache,
    load_cv_print_css,
)

CSS_BEGIN = "<!-- CV_PRINT_CSS_BEGIN -->"
CSS_END = "<!-- CV_PRINT_CSS_END -->"

_STYLE_BLOCK_RE = re.compile(
    re.escape(CSS_BEGIN) + r".*?" + re.escape(CSS_END),
    re.DOTALL,
)


def default_master_cv_html_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[3]
    return root / "career-documents" / "cv" / "master_ai_engineer_cv.html"


def build_embedded_css_block(css: str | None = None) -> str:
    """Return the marker-wrapped ``<style>`` block for Master HTML."""
    body = (css if css is not None else load_cv_print_css()).rstrip() + "\n"
    return (
        f"{CSS_BEGIN}\n"
        '<style id="cv-print-css">\n'
        f"{body}"
        "</style>\n"
        f"{CSS_END}"
    )


def inject_cv_print_css(html: str, *, css: str | None = None) -> str:
    """Replace the Master HTML CSS marker block with the canonical stylesheet."""
    if CSS_BEGIN not in html or CSS_END not in html:
        raise CvHtmlRenderError(
            "Master CV HTML is missing CV_PRINT_CSS_BEGIN/END markers"
        )
    block = build_embedded_css_block(css)
    updated, count = _STYLE_BLOCK_RE.subn(block, html, count=1)
    if count != 1:
        raise CvHtmlRenderError(
            "Failed to inject canonical CV print CSS into Master HTML"
        )
    return updated


def extract_embedded_cv_print_css(html: str) -> str:
    """Return CSS text embedded between Master HTML markers."""
    match = _STYLE_BLOCK_RE.search(html)
    if match is None:
        raise CvHtmlRenderError(
            "Master CV HTML is missing CV_PRINT_CSS_BEGIN/END markers"
        )
    style_match = re.search(
        r"<style[^>]*>(.*?)</style>",
        match.group(0),
        re.DOTALL | re.IGNORECASE,
    )
    if style_match is None:
        raise CvHtmlRenderError("Master CV HTML CSS markers lack a <style> block")
    return style_match.group(1).strip() + "\n"


def master_html_uses_canonical_css(html: str, *, css: str | None = None) -> bool:
    embedded = extract_embedded_cv_print_css(html).strip()
    canonical = (css if css is not None else load_cv_print_css()).strip()
    return embedded == canonical


def sync_master_cv_html(
    path: Path | None = None,
    *,
    css: str | None = None,
) -> Path:
    """Write canonical CSS into the Master CV HTML file. Returns the path."""
    target = path or default_master_cv_html_path()
    original = target.read_text(encoding="utf-8")
    updated = inject_cv_print_css(original, css=css)
    if updated != original:
        target.write_text(updated, encoding="utf-8", newline="\n")
    clear_cv_print_css_cache()
    return target
