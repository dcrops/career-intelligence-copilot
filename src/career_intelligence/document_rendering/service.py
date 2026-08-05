"""Render-only service: existing Markdown → HTML → PDF.

Does not invoke planners, composers, OpenAI, or upstream intelligence services.
Does not modify the source Markdown file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from career_intelligence.cover_letter.html_renderer import (
    CoverLetterHtmlRenderError,
    CoverLetterHtmlView,
    render_html_from_view,
)
from career_intelligence.cv_generation.errors import CvHtmlRenderError
from career_intelligence.cv_generation.pdf_renderer import (
    PdfRenderError,
    render_pdf_from_html,
)
from career_intelligence.document_rendering.cover_letter_markdown import (
    parse_cover_letter_markdown,
)
from career_intelligence.document_rendering.cv_markdown import (
    render_cv_html_from_markdown,
)
from career_intelligence.document_rendering.detect import (
    DocumentKind,
    detect_document_kind,
)
from career_intelligence.document_rendering.errors import (
    DocumentRenderHtmlError,
    DocumentRenderInputError,
    DocumentRenderPdfError,
    UnsupportedDocumentTypeError,
)


@dataclass(frozen=True)
class DocumentRenderResult:
    """Paths written by a render-only pass (Markdown is left unchanged)."""

    kind: DocumentKind
    markdown_path: Path
    html_path: Path
    pdf_path: Path
    markdown_unchanged: bool = True


def render_document_from_markdown(
    markdown_path: Path,
    *,
    kind: DocumentKind | None = None,
    html_path: Path | None = None,
    pdf_path: Path | None = None,
) -> DocumentRenderResult:
    """Render HTML and PDF beside an existing generated Markdown draft."""
    path = Path(markdown_path)
    if not path.is_file():
        raise DocumentRenderInputError(f"Markdown file not found: {path}")
    if path.suffix.casefold() != ".md":
        raise DocumentRenderInputError(
            f"Expected a .md Markdown file, got: {path.name}"
        )

    try:
        original = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocumentRenderInputError(f"Could not read Markdown: {path}: {exc}") from exc
    if not original.strip():
        raise DocumentRenderInputError(f"Markdown file is empty: {path}")

    resolved_kind = kind or detect_document_kind(path, original)
    html_document = _render_html(resolved_kind, original)

    try:
        pdf_bytes = render_pdf_from_html(html_document)
    except PdfRenderError as exc:
        raise DocumentRenderPdfError(str(exc)) from exc

    target_html = html_path or path.with_suffix(".html")
    target_pdf = pdf_path or path.with_suffix(".pdf")
    _atomic_write_text(target_html, html_document)
    _atomic_write_bytes(target_pdf, pdf_bytes)

    after = path.read_text(encoding="utf-8")
    if after != original:
        raise DocumentRenderInputError(
            f"Markdown was modified during render (unexpected): {path}"
        )

    return DocumentRenderResult(
        kind=resolved_kind,
        markdown_path=path,
        html_path=target_html,
        pdf_path=target_pdf,
        markdown_unchanged=True,
    )


def _render_html(kind: DocumentKind, markdown: str) -> str:
    try:
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
    except UnsupportedDocumentTypeError:
        raise
    except DocumentRenderInputError:
        raise
    except (CoverLetterHtmlRenderError, CvHtmlRenderError) as exc:
        raise DocumentRenderHtmlError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise DocumentRenderHtmlError(f"HTML rendering failed: {exc}") from exc
    raise UnsupportedDocumentTypeError(f"Unsupported document kind: {kind}")


def _atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
