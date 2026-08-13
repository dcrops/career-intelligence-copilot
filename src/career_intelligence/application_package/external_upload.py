"""Employer-facing upload PDF copies for application packages.

Authoritative CIC drafts remain ``opp_<id>.pdf`` under career-documents.
External/upload copies live under the package directory:

    data/application_packages/<opportunity_id>/export/
        <Name> - <Employer> - <Role> - CV.pdf
        <Name> - <Employer> - <Role> - Cover Letter.pdf

Copies are byte-identical to the authoritative PDFs. Filenames never include
opportunity IDs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from career_intelligence.application_package.models import ApplicationPackageManifest

_INVALID_FS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_SPACE = re.compile(r"\s+")
_MAX_FILENAME_LEN = 180


@dataclass(frozen=True)
class ExternalUploadPaths:
    """Filesystem paths of employer-facing PDF copies."""

    export_dir: Path
    cv_pdf: Path
    cover_letter_pdf: Path


def build_external_upload_filename(
    *,
    full_name: str,
    company: str,
    title: str,
    kind: Literal["cv", "cover_letter"],
) -> str:
    """Deterministic human-readable employer-facing PDF filename."""
    name = _sanitize_segment(full_name) or "Candidate"
    employer = _sanitize_segment(company) or "Employer"
    role = _sanitize_segment(title) or "Role"
    suffix = "CV" if kind == "cv" else "Cover Letter"
    filename = f"{name} - {employer} - {role} - {suffix}.pdf"
    if "opp_" in filename.lower():
        # Defensive: never allow opportunity-id leakage via company/title text.
        filename = filename.replace("opp_", "").replace("OPP_", "")
        filename = _MULTI_SPACE.sub(" ", filename).strip()
    return _fit_filename(filename, name=name, suffix=suffix)


def package_export_dir(packages_root: Path, opportunity_id: str) -> Path:
    return Path(packages_root) / opportunity_id / "export"


def materialize_external_upload_pdfs(
    manifest: ApplicationPackageManifest,
    *,
    packages_root: Path,
    full_name: str,
) -> ExternalUploadPaths:
    """Copy authoritative PDFs into package ``export/`` with upload filenames.

    Idempotent when destination bytes already match the source.
    """
    company = manifest.evidence.acquisition.company or "Employer"
    title = manifest.evidence.acquisition.title or "Role"
    cv_src = Path(manifest.cv.pdf_path) if manifest.cv.pdf_path else None
    cl_src = (
        Path(manifest.cover_letter.pdf_path)
        if manifest.cover_letter.pdf_path
        else None
    )
    if cv_src is None or not cv_src.is_file():
        raise FileNotFoundError(
            f"Authoritative CV PDF missing for {manifest.opportunity_id}"
        )
    if cl_src is None or not cl_src.is_file():
        raise FileNotFoundError(
            f"Authoritative cover-letter PDF missing for {manifest.opportunity_id}"
        )

    export_dir = package_export_dir(packages_root, manifest.opportunity_id)
    export_dir.mkdir(parents=True, exist_ok=True)

    cv_name = build_external_upload_filename(
        full_name=full_name, company=company, title=title, kind="cv"
    )
    cl_name = build_external_upload_filename(
        full_name=full_name, company=company, title=title, kind="cover_letter"
    )
    if manifest.opportunity_id in cv_name or manifest.opportunity_id in cl_name:
        raise RuntimeError(
            "External upload filename unexpectedly contains opportunity_id"
        )

    cv_dest = export_dir / cv_name
    cl_dest = export_dir / cl_name
    _copy_identical(cv_src, cv_dest)
    _copy_identical(cl_src, cl_dest)
    return ExternalUploadPaths(
        export_dir=export_dir,
        cv_pdf=cv_dest,
        cover_letter_pdf=cl_dest,
    )


def _sanitize_segment(value: str) -> str:
    text = _INVALID_FS.sub("", value or "")
    text = text.replace("\u2060", "")
    text = _MULTI_SPACE.sub(" ", text).strip(" .")
    return text


def _fit_filename(filename: str, *, name: str, suffix: str) -> str:
    if len(filename) <= _MAX_FILENAME_LEN:
        return filename
    # Deterministic trim: keep candidate name + suffix; shrink middle.
    reserved = len(f"{name} -  -  - {suffix}.pdf")
    budget = max(12, _MAX_FILENAME_LEN - reserved)
    # Re-parse middle from original pattern "name - employer - role - suffix.pdf"
    parts = filename[: -len(".pdf")].split(" - ")
    if len(parts) >= 4:
        employer = parts[1]
        role = " - ".join(parts[2:-1])
        half = max(4, budget // 2)
        employer = _truncate(employer, half)
        role = _truncate(role, budget - len(employer))
        return f"{name} - {employer} - {role} - {suffix}.pdf"
    return filename[: _MAX_FILENAME_LEN - 4] + ".pdf"


def _truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    if max_len <= 1:
        return value[:max_len]
    return value[: max_len - 1].rstrip() + "…"


def _copy_identical(source: Path, dest: Path) -> None:
    payload = source.read_bytes()
    if dest.is_file() and dest.read_bytes() == payload:
        return
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(dest)
