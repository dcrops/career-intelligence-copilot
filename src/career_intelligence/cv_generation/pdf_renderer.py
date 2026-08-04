"""HTML → PDF renderer for recruiter-ready CV and cover-letter drafts.

Renderer only: consumes a complete standalone HTML document (already produced by
the CV / cover-letter HTML renderers) and writes PDF bytes. No planner, composer,
or content-selection logic lives here.
"""

from __future__ import annotations


class PdfRenderError(RuntimeError):
    """Raised when HTML→PDF conversion fails."""


def render_pdf_from_html(html_document: str) -> bytes:
    """Render a complete HTML document to PDF bytes (A4 via embedded ``@page`` CSS).

    Requires WeasyPrint. The HTML document must already include print CSS
    (``cv_print.css``) so Markdown/HTML/PDF stay presentation-aligned.
    """
    if not html_document or not html_document.strip():
        raise PdfRenderError("HTML document is empty; cannot render PDF")
    if not html_document.lstrip().lower().startswith("<!doctype html>"):
        raise PdfRenderError("PDF renderer requires a complete HTML document")

    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover - dependency declared in pyproject
        raise PdfRenderError(
            "WeasyPrint is required for PDF rendering. "
            "Install project dependencies including weasyprint."
        ) from exc

    try:
        pdf_bytes = HTML(string=html_document, encoding="utf-8").write_pdf()
    except Exception as exc:  # noqa: BLE001 - convert WeasyPrint/system failures
        raise PdfRenderError(f"PDF rendering failed: {exc}") from exc

    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        raise PdfRenderError("PDF renderer did not return a valid PDF document")
    return pdf_bytes
