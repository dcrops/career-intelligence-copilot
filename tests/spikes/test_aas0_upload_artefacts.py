"""Fail-closed AAS upload-path enforcement."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.upload_artefacts import (  # noqa: E402
    UnsafeUploadArtefactError,
    assert_safe_external_upload_pdf,
    is_internal_opp_pdf_filename,
    validate_external_upload_pdf,
)


def test_recognises_internal_opp_ulid_pdf() -> None:
    assert is_internal_opp_pdf_filename("opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf")
    assert is_internal_opp_pdf_filename(
        r"C:\tmp\career-documents\cv\generated\opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf"
    )
    assert not is_internal_opp_pdf_filename(
        "David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf"
    )
    assert not is_internal_opp_pdf_filename("David Cropper - AI Engineer CV.pdf")


def test_valid_export_cv_and_cover_letter(tmp_path: Path) -> None:
    export = tmp_path / "application_packages" / "opp_x" / "export"
    export.mkdir(parents=True)
    cv = export / "David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf"
    cl = export / "David Cropper - REPURPOSE IT PL - AI Engineer - Cover Letter.pdf"
    cv.write_bytes(b"%PDF")
    cl.write_bytes(b"%PDF")
    assert validate_external_upload_pdf(cv, kind="cv") is None
    assert validate_external_upload_pdf(cl, kind="cover_letter") is None
    assert assert_safe_external_upload_pdf(cv, kind="cv") == cv
    assert assert_safe_external_upload_pdf(cl, kind="cover_letter") == cl


def test_rejects_internal_opp_pdf_without_substitution(tmp_path: Path) -> None:
    export = tmp_path / "export"
    export.mkdir()
    internal = export / "opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf"
    internal.write_bytes(b"%PDF")
    error = validate_external_upload_pdf(internal, kind="cv")
    assert error is not None
    assert "opp_<ULID>" in error
    with pytest.raises(UnsafeUploadArtefactError, match="opp_<ULID>"):
        assert_safe_external_upload_pdf(internal, kind="cv")


def test_rejects_path_not_under_export(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    generated.mkdir()
    cv = generated / "David Cropper - Acme - Role - CV.pdf"
    error = validate_external_upload_pdf(cv, kind="cv")
    assert error is not None
    assert "export/" in error


def test_rejects_wrong_suffix_shape(tmp_path: Path) -> None:
    export = tmp_path / "export"
    export.mkdir()
    cv = export / "David Cropper - Acme - Role - Resume.pdf"
    error = validate_external_upload_pdf(cv, kind="cv")
    assert error is not None
    assert "human-readable export shape" in error
