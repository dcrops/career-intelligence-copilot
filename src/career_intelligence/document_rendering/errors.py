"""Errors for the render-only Markdown → HTML → PDF pipeline."""

from __future__ import annotations


class DocumentRenderError(Exception):
    """Base error for document rendering failures."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DocumentRenderInputError(DocumentRenderError):
    """Raised when the Markdown input is missing or unreadable."""


class UnsupportedDocumentTypeError(DocumentRenderError):
    """Raised when the document cannot be classified as CV or cover letter."""


class DocumentRenderHtmlError(DocumentRenderError):
    """Raised when HTML rendering fails."""


class DocumentRenderPdfError(DocumentRenderError):
    """Raised when PDF rendering fails."""
