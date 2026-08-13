"""AAS spike: content-based PDF freshness vs Markdown (not mtime-only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from career_intelligence.cover_letter.html_renderer import (
    CoverLetterHtmlView,
    render_html_from_view,
)
from career_intelligence.document_rendering.cover_letter_markdown import (
    parse_cover_letter_markdown,
)
from career_intelligence.document_rendering.cv_markdown import (
    render_cv_html_from_markdown,
)
from career_intelligence.document_rendering.detect import detect_document_kind


class PdfFreshnessStatus(str, Enum):
    OK = "ok"
    MTIME_TOUCH_ONLY = "mtime_touch_only"
    CONTENT_DRIFT = "content_drift"
    HTML_MISSING = "html_missing"


@dataclass(frozen=True)
class PdfFreshnessResult:
    status: PdfFreshnessStatus
    message: str
    blocking: bool


def render_html_from_markdown_text(markdown_path: Path, markdown: str) -> str:
    """Render HTML via existing CIC render helpers without writing artefacts."""
    kind = detect_document_kind(markdown_path, markdown)
    if kind == "cover_letter":
        presentation = parse_cover_letter_markdown(markdown)
        view = CoverLetterHtmlView(
            full_name=presentation.full_name,
            role_title=presentation.role_title,
            company=presentation.company,
            salutation=presentation.salutation,
            paragraphs=presentation.paragraphs,
            contact=presentation.contact or None,
        )
        return render_html_from_view(view)
    if kind == "cv":
        return render_cv_html_from_markdown(markdown)
    raise ValueError(f"Unsupported document kind for freshness check: {kind}")


def assess_markdown_pdf_freshness(
    *,
    markdown_path: Path,
    pdf_path: Path,
    html_path: Path | None = None,
    label: str = "document",
) -> PdfFreshnessResult:
    """Classify whether a PDF may be stale relative to current Markdown.

    When Markdown mtime is newer than PDF, compare freshly rendered HTML to the
    on-disk sibling HTML. PDF byte equality is intentionally not used.
    """
    sibling_html = html_path if html_path is not None else pdf_path.with_suffix(".html")
    md_newer = markdown_path.stat().st_mtime > pdf_path.stat().st_mtime
    if not md_newer:
        return PdfFreshnessResult(
            status=PdfFreshnessStatus.OK,
            message=(
                f"{label}: Markdown is not newer than PDF "
                f"({markdown_path.name} / {pdf_path.name})."
            ),
            blocking=False,
        )

    if not sibling_html.is_file():
        return PdfFreshnessResult(
            status=PdfFreshnessStatus.HTML_MISSING,
            message=(
                f"{label}: Markdown mtime is newer than PDF and authoritative HTML "
                f"is missing ({sibling_html.name}). Document content may have drifted; "
                "run render-only refresh + truth validation before live AAS."
            ),
            blocking=True,
        )

    markdown = markdown_path.read_text(encoding="utf-8")
    fresh_html = render_html_from_markdown_text(markdown_path, markdown)
    on_disk_html = sibling_html.read_text(encoding="utf-8")
    if fresh_html == on_disk_html:
        return PdfFreshnessResult(
            status=PdfFreshnessStatus.MTIME_TOUCH_ONLY,
            message=(
                f"{label}: Markdown mtime is newer than PDF, but deterministic HTML "
                "content is unchanged (touch/save false positive)."
            ),
            blocking=False,
        )

    return PdfFreshnessResult(
        status=PdfFreshnessStatus.CONTENT_DRIFT,
        message=(
            f"{label}: Markdown mtime is newer than PDF and freshly rendered HTML "
            f"differs from on-disk {sibling_html.name}. Document content may have "
            "drifted; run render-only refresh + truth validation before live AAS."
        ),
        blocking=True,
    )
