"""Employer-facing upload PDF copies for application packages.

Authoritative CIC drafts remain ``opp_<id>.pdf`` under career-documents.
External/upload copies live under the package directory:

    data/application_packages/<opportunity_id>/export/
        <Name> - <Employer> - <Role> - CV.pdf
        <Name> - <Employer> - <Role> - Cover Letter.pdf

Copies are byte-identical to the authoritative PDFs. Filenames never include
opportunity IDs.

Canonical opportunity company/title stay unchanged on the manifest. Employer-facing
names may use a shorter role (leading segment before marketing delimiters such as
``|``) and, when the resolved absolute destination or atomic ``.tmp`` path would
exceed the Windows-safe budget, further deterministic fitting. Short names that
already fit are left unchanged.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from career_intelligence.application_package.models import ApplicationPackageManifest

_INVALID_FS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_SPACE = re.compile(r"\s+")
_MAX_FILENAME_LEN = 180
# Conservative Windows-safe cap for dest and dest+".tmp" (classic MAX_PATH is ~259).
MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN = 240
_ATOMIC_TMP_EXTRA = 4  # dest.with_suffix(dest.suffix + ".tmp") → ".pdf.tmp"
_CV_SUFFIX = "CV"
_COVER_LETTER_SUFFIX = "Cover Letter"
_HASH_LEN = 6
_ROLE_MARKETING_DELIMS = ("|", "•")


@dataclass(frozen=True)
class ExternalUploadPaths:
    """Filesystem paths of employer-facing PDF copies."""

    export_dir: Path
    cv_pdf: Path
    cover_letter_pdf: Path


@dataclass(frozen=True)
class _UploadIdentity:
    name: str
    employer: str
    role: str


def atomic_tmp_path(dest: Path) -> Path:
    """Temporary path used by atomic copy (``file.pdf`` → ``file.pdf.tmp``)."""
    return dest.with_suffix(dest.suffix + ".tmp")


def build_external_upload_filename(
    *,
    full_name: str,
    company: str,
    title: str,
    kind: Literal["cv", "cover_letter"],
    export_dir: Path | None = None,
) -> str:
    """Deterministic human-readable employer-facing PDF filename.

    CV and cover-letter names share the same fitted identity basis. When
    ``export_dir`` is provided, fitting includes the absolute destination and
    atomic ``.tmp`` paths.
    """
    cv_name, cl_name = build_external_upload_filenames(
        full_name=full_name,
        company=company,
        title=title,
        export_dir=export_dir,
    )
    return cv_name if kind == "cv" else cl_name


def build_external_upload_filenames(
    *,
    full_name: str,
    company: str,
    title: str,
    export_dir: Path | None = None,
) -> tuple[str, str]:
    """Return ``(cv_filename, cover_letter_filename)`` from one fitted identity."""
    identity = _fit_upload_identity(
        full_name=full_name,
        company=company,
        title=title,
        export_dir=export_dir,
    )
    return (
        _compose_filename(identity, _CV_SUFFIX),
        _compose_filename(identity, _COVER_LETTER_SUFFIX),
    )


def package_export_dir(packages_root: Path, opportunity_id: str) -> Path:
    return Path(packages_root) / opportunity_id / "export"


def materialize_external_upload_pdfs(
    manifest: ApplicationPackageManifest,
    *,
    packages_root: Path,
    full_name: str,
) -> ExternalUploadPaths:
    """Copy authoritative PDFs into package ``export/`` with upload filenames.

    Idempotent when destination bytes already match the source. Previous-policy
    employer-facing PDFs in the same ``export/`` directory are removed after the
    new pair is written.
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

    cv_name, cl_name = build_external_upload_filenames(
        full_name=full_name,
        company=company,
        title=title,
        export_dir=export_dir,
    )
    if manifest.opportunity_id in cv_name or manifest.opportunity_id in cl_name:
        raise RuntimeError(
            "External upload filename unexpectedly contains opportunity_id"
        )

    cv_dest = export_dir / cv_name
    cl_dest = export_dir / cl_name
    _copy_identical(cv_src, cv_dest)
    _copy_identical(cl_src, cl_dest)
    _cleanup_stale_export_pdfs(export_dir, keep={cv_name, cl_name})
    return ExternalUploadPaths(
        export_dir=export_dir,
        cv_pdf=cv_dest,
        cover_letter_pdf=cl_dest,
    )


def _sanitize_segment(value: str) -> str:
    text = _INVALID_FS.sub("", value or "")
    text = text.replace("\u2060", "")
    text = _MULTI_SPACE.sub(" ", text).strip(" .")
    return _strip_opp_marker(text)


def _strip_opp_marker(text: str) -> str:
    if "opp_" not in text.lower():
        return text
    cleaned = text.replace("opp_", "").replace("OPP_", "")
    return _MULTI_SPACE.sub(" ", cleaned).strip(" .")


def _employer_facing_role(title: str) -> str:
    """Prefer the stable leading title before marketing/keyword suffixes."""
    text = title or ""
    for delim in _ROLE_MARKETING_DELIMS:
        if delim in text:
            text = text.split(delim, 1)[0]
            break
    return _sanitize_segment(text) or "Role"


def _role_head_before_dash(role: str) -> str:
    if " - " not in role:
        return role
    return _sanitize_segment(role.split(" - ", 1)[0]) or role


def _compose_filename(identity: _UploadIdentity, suffix: str) -> str:
    filename = f"{identity.name} - {identity.employer} - {identity.role} - {suffix}.pdf"
    if "opp_" in filename.lower():
        filename = _strip_opp_marker(filename)
    return filename


def _budget_bases(export_dir: Path) -> tuple[Path, ...]:
    base = Path(export_dir)
    bases: list[Path] = [base]
    if not base.is_absolute():
        bases.append(Path.cwd() / base)
    try:
        resolved = base.resolve()
        if resolved not in bases:
            bases.append(resolved)
    except OSError:
        pass
    return tuple(bases)


def _max_filename_len_for_dir(export_dir: Path | None) -> int:
    cap = _MAX_FILENAME_LEN
    if export_dir is None:
        return cap
    shortest_abs_budget = cap
    for base in _budget_bases(export_dir):
        prefix = len(str(base)) + 1
        abs_budget = MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN - prefix - _ATOMIC_TMP_EXTRA
        shortest_abs_budget = min(shortest_abs_budget, abs_budget)
    return max(0, shortest_abs_budget)


def _paths_fit(export_dir: Path | None, filename: str) -> bool:
    if len(filename) > _MAX_FILENAME_LEN:
        return False
    if export_dir is None:
        return len(filename) <= _MAX_FILENAME_LEN
    if len(filename) > _max_filename_len_for_dir(export_dir):
        return False
    for base in _budget_bases(export_dir):
        dest = base / filename
        tmp = atomic_tmp_path(dest)
        if len(str(dest)) > MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN:
            return False
        if len(str(tmp)) > MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN:
            return False
    return True


def _identity_fits(identity: _UploadIdentity, export_dir: Path | None) -> bool:
    cv_name = _compose_filename(identity, _CV_SUFFIX)
    cl_name = _compose_filename(identity, _COVER_LETTER_SUFFIX)
    return _paths_fit(export_dir, cv_name) and _paths_fit(export_dir, cl_name)


def _fit_upload_identity(
    *,
    full_name: str,
    company: str,
    title: str,
    export_dir: Path | None,
) -> _UploadIdentity:
    identity = _UploadIdentity(
        name=_sanitize_segment(full_name) or "Candidate",
        employer=_sanitize_segment(company) or "Employer",
        role=_employer_facing_role(title),
    )
    if _identity_fits(identity, export_dir):
        return identity

    shortened_role = _role_head_before_dash(identity.role)
    if shortened_role != identity.role:
        trial = _UploadIdentity(
            name=identity.name, employer=identity.employer, role=shortened_role
        )
        if _identity_fits(trial, export_dir):
            return trial
        identity = trial

    return _shrink_identity(
        identity,
        export_dir=export_dir,
        uniqueness_key=f"{company}\n{title}",
    )


def _truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    if max_len <= 1:
        return value[:max_len]
    return value[: max_len - 1].rstrip() + "…"


def _shrink_identity(
    identity: _UploadIdentity,
    *,
    export_dir: Path | None,
    uniqueness_key: str,
) -> _UploadIdentity:
    token = hashlib.sha256(uniqueness_key.encode("utf-8")).hexdigest()[:_HASH_LEN]

    def trial(employer: str, role: str) -> _UploadIdentity | None:
        hashed_role = role if role.endswith(f"-{token}") else f"{role}-{token}"
        candidate = _UploadIdentity(
            name=identity.name, employer=employer, role=hashed_role
        )
        return candidate if _identity_fits(candidate, export_dir) else None

    for role_len in range(len(identity.role), 3, -1):
        found = trial(identity.employer, _truncate(identity.role, role_len))
        if found is not None:
            return found

    short_role = _truncate(identity.role, 4)
    for emp_len in range(len(identity.employer), 3, -1):
        found = trial(_truncate(identity.employer, emp_len), short_role)
        if found is not None:
            return found

    raise RuntimeError(
        "Cannot fit employer-facing PDF names into the Windows absolute-path "
        f"budget ({MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN} chars including .tmp) "
        f"under {export_dir}"
    )


def _cleanup_stale_export_pdfs(export_dir: Path, *, keep: set[str]) -> None:
    """Remove previous-policy employer-facing PDFs and leftover atomic temps."""
    for path in export_dir.iterdir():
        if not path.is_file():
            continue
        name = path.name
        if name in keep:
            continue
        if name.endswith(".pdf.tmp"):
            path.unlink(missing_ok=True)
            continue
        lowered = name.lower()
        if not (
            lowered.endswith(" - cv.pdf") or lowered.endswith(" - cover letter.pdf")
        ):
            continue
        if "opp_" in lowered:
            continue
        path.unlink(missing_ok=True)


def _copy_identical(source: Path, dest: Path) -> None:
    payload = source.read_bytes()
    if dest.is_file() and dest.read_bytes() == payload:
        return
    tmp = atomic_tmp_path(dest)
    tmp.write_bytes(payload)
    tmp.replace(dest)
