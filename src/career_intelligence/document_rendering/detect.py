"""Detect CV vs cover-letter generated Markdown for render-only workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from career_intelligence.document_rendering.errors import UnsupportedDocumentTypeError

DocumentKind = Literal["cover_letter", "cv"]


def detect_document_kind(markdown_path: Path, markdown: str) -> DocumentKind:
    """Classify a generated Markdown draft as cover letter or CV.

    Prefers path conventions under ``career-documents/``, then content sniffing.
    """
    parts = {part.casefold() for part in markdown_path.parts}
    if "cover-letters" in parts or "cover_letters" in parts:
        return "cover_letter"
    if "cv" in parts and "generated" in parts:
        return "cv"

    folded = markdown.casefold()
    if "## professional summary" in folded or "## featured ai projects" in folded:
        return "cv"
    if "kind regards" in folded and "**" in markdown and " - " in markdown:
        return "cover_letter"
    if folded.lstrip().startswith("# ") and "hello," in folded:
        return "cover_letter"

    raise UnsupportedDocumentTypeError(
        f"Unsupported document type for render-only: {markdown_path}. "
        "Expected a generated CV or cover-letter Markdown under "
        "career-documents/cv/generated/ or career-documents/cover-letters/generated/."
    )
