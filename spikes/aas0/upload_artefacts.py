"""Fail-closed checks that AAS upload paths are employer-facing export PDFs.

Internal CIC artefacts remain ``opp_<ULID>.pdf`` under career-documents.
AAS must upload only package ``export/`` copies with human-readable names.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

# Crockford ULID (same alphabet as career_intelligence.opportunities.ulid).
_INTERNAL_OPP_PDF = re.compile(r"^opp_[0-9A-HJKMNP-TV-Z]{26}\.pdf$", re.I)
_OPP_MARKER = re.compile(r"opp_[0-9A-HJKMNP-TV-Z]{26}", re.I)


class UnsafeUploadArtefactError(RuntimeError):
    """AAS must not upload this path. Callers must not substitute another file."""


def is_internal_opp_pdf_filename(filename: str | None) -> bool:
    """True when the basename is a CIC internal opportunity PDF stem."""
    name = Path(filename or "").name.strip()
    return bool(name) and bool(_INTERNAL_OPP_PDF.match(name))


def validate_external_upload_pdf(
    path: Path,
    *,
    kind: Literal["cv", "cover_letter"],
) -> str | None:
    """Return an error message if ``path`` is not a safe external upload PDF.

    Does not require the file to exist (so unit tests can check names/parents).
    """
    candidate = Path(path)
    name = candidate.name.strip()
    if not name:
        return "upload artefact path has an empty filename"
    if is_internal_opp_pdf_filename(name):
        return (
            f"refusing internal CIC artefact filename (opp_<ULID>.pdf): {name}"
        )
    if _OPP_MARKER.search(name) or "opp_" in name.lower():
        return f"upload filename contains an opportunity-id marker: {name}"
    if candidate.suffix.lower() != ".pdf":
        return f"upload artefact must be a PDF: {name}"
    if candidate.parent.name != "export":
        return (
            "upload artefact must live under the package export/ directory: "
            f"{candidate}"
        )
    lowered = name.lower()
    if kind == "cv":
        if not lowered.endswith(" - cv.pdf"):
            return (
                "CV upload filename is not the human-readable export shape "
                f"(… - CV.pdf): {name}"
            )
    else:
        if not lowered.endswith(" - cover letter.pdf"):
            return (
                "Cover-letter upload filename is not the human-readable export "
                f"shape (… - Cover Letter.pdf): {name}"
            )
    return None


def assert_safe_external_upload_pdf(
    path: Path,
    *,
    kind: Literal["cv", "cover_letter"],
    must_exist: bool = True,
) -> Path:
    """Raise ``UnsafeUploadArtefactError`` rather than substituting another path."""
    candidate = Path(path)
    error = validate_external_upload_pdf(candidate, kind=kind)
    if error:
        raise UnsafeUploadArtefactError(error)
    if must_exist and not candidate.is_file():
        raise UnsafeUploadArtefactError(f"upload artefact is missing: {candidate}")
    return candidate
