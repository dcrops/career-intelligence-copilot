"""Render-only pipeline for owner-edited generated documents.

Document generation (planner → composer → Markdown) is separate from document
rendering (Markdown → HTML → PDF). This package never invokes planners,
composers, job analysis, assessment, matching, strategy, or OpenAI.
"""

from __future__ import annotations

from career_intelligence.document_rendering.detect import (
    DocumentKind,
    detect_document_kind,
)
from career_intelligence.document_rendering.errors import (
    DocumentRenderError,
    DocumentRenderHtmlError,
    DocumentRenderInputError,
    DocumentRenderPdfError,
    UnsupportedDocumentTypeError,
)
from career_intelligence.document_rendering.service import (
    DocumentRenderResult,
    render_document_from_markdown,
)

__all__ = [
    "DocumentKind",
    "DocumentRenderError",
    "DocumentRenderHtmlError",
    "DocumentRenderInputError",
    "DocumentRenderPdfError",
    "DocumentRenderResult",
    "UnsupportedDocumentTypeError",
    "detect_document_kind",
    "render_document_from_markdown",
]
