"""Focused tests for employer-facing application package PDF exports."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_package.external_upload import (
    build_external_upload_filename,
    materialize_external_upload_pdfs,
)
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)


def test_external_filename_normal_employer_role() -> None:
    assert (
        build_external_upload_filename(
            full_name="David Cropper",
            company="Repurpose It",
            title="AI Engineer",
            kind="cv",
        )
        == "David Cropper - Repurpose It - AI Engineer - CV.pdf"
    )
    assert (
        build_external_upload_filename(
            full_name="David Cropper",
            company="Repurpose It",
            title="AI Engineer",
            kind="cover_letter",
        )
        == "David Cropper - Repurpose It - AI Engineer - Cover Letter.pdf"
    )


def test_external_filename_strips_invalid_chars_and_collapses_whitespace() -> None:
    name = build_external_upload_filename(
        full_name="  David   Cropper  ",
        company='Repurpose It P/L<>:"|?*',
        title="AI   Engineer",
        kind="cv",
    )
    assert name == "David Cropper - Repurpose It PL - AI Engineer - CV.pdf"
    assert "/" not in name
    assert ":" not in name
    assert "  " not in name


def test_external_filename_deterministic_and_hides_opportunity_id() -> None:
    a = build_external_upload_filename(
        full_name="David Cropper",
        company="Repurpose It",
        title="AI Engineer",
        kind="cv",
    )
    b = build_external_upload_filename(
        full_name="David Cropper",
        company="Repurpose It",
        title="AI Engineer",
        kind="cv",
    )
    assert a == b
    assert "opp_" not in a.lower()
    assert "01KZ" not in a


def test_materialize_copies_bytes_into_package_export(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    service = package_service(tmp_path, opportunities, profile)
    manifest = service.prepare(opportunity_id, **approved_gate_options())  # type: ignore[arg-type]

    auth_cv = Path(manifest.cv.pdf_path)
    auth_cl = Path(manifest.cover_letter.pdf_path)
    assert auth_cv.name.startswith("opp_")
    assert auth_cl.name.startswith("opp_")

    exports = service.ensure_external_upload_pdfs(manifest)
    expected_dir = tmp_path / "application_packages" / opportunity_id / "export"
    assert exports.export_dir == expected_dir
    assert exports.cv_pdf.parent == expected_dir
    assert exports.cover_letter_pdf.parent == expected_dir
    assert opportunity_id not in exports.cv_pdf.name
    assert opportunity_id not in exports.cover_letter_pdf.name
    assert " - CV.pdf" in exports.cv_pdf.name
    assert " - Cover Letter.pdf" in exports.cover_letter_pdf.name
    assert exports.cv_pdf.read_bytes() == auth_cv.read_bytes()
    assert exports.cover_letter_pdf.read_bytes() == auth_cl.read_bytes()

    # Idempotent: second call keeps bytes identical.
    again = materialize_external_upload_pdfs(
        manifest,
        packages_root=tmp_path / "application_packages",
        full_name=profile.identity.full_name,
    )
    assert again.cv_pdf.read_bytes() == auth_cv.read_bytes()
