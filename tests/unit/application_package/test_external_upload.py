"""Focused tests for employer-facing application package PDF exports."""

from __future__ import annotations

import os
from pathlib import Path

from career_intelligence.application_package.external_upload import (
    MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN,
    atomic_tmp_path,
    build_external_upload_filename,
    build_external_upload_filenames,
    materialize_external_upload_pdfs,
)
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)

CSK_COMPANY = "CSK Nexus Pty Ltd"
CSK_TITLE = (
    "Senior AI Engineer - AWS Bedrock | Agentic AI | "
    "Chatbots & Customer Support Auto"
)
CSK_OPPORTUNITY_ID = "opp_01M0E6GQ9XQH9DK9N5T0MS67N0"
CSK_CV_AT_PREFIX_130 = (
    "David Cropper - CSK Nexus Pty Ltd - Senior AI Engineer - AWS Bedrock - CV.pdf"
)
CSK_CL_AT_PREFIX_130 = (
    "David Cropper - CSK Nexus Pty Ltd - Senior AI Engineer - AWS Bedrock - "
    "Cover Letter.pdf"
)


def _abs_dir_with_len(length: int) -> Path:
    root = "C:\\" if os.name == "nt" else "/"
    pad = "p" * (length - len(root))
    path = Path(root + pad)
    assert len(str(path)) == length, (len(str(path)), str(path))
    return path


def _assert_dest_and_tmp_fit(export_dir: Path, filename: str) -> Path:
    dest = export_dir / filename
    tmp = atomic_tmp_path(dest)
    assert len(str(dest)) <= MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN, len(str(dest))
    assert len(str(tmp)) <= MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN, len(str(tmp))
    assert filename.endswith(".pdf")
    assert not filename.endswith(".pdf.pdf")
    return dest


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


def test_short_hatch_filenames_unchanged() -> None:
    assert (
        build_external_upload_filename(
            full_name="David Cropper",
            company="Hatch",
            title="AI Trainer",
            kind="cv",
        )
        == "David Cropper - Hatch - AI Trainer - CV.pdf"
    )
    assert (
        build_external_upload_filename(
            full_name="David Cropper",
            company="Hatch",
            title="AI Trainer",
            kind="cover_letter",
        )
        == "David Cropper - Hatch - AI Trainer - Cover Letter.pdf"
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
    assert "|" not in name
    assert "*" not in name
    assert "?" not in name


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


def test_no_arbitrary_opp_filenames_exposed_externally() -> None:
    cv, cl = build_external_upload_filenames(
        full_name="David Cropper",
        company=f"Acme {CSK_OPPORTUNITY_ID}",
        title=f"Engineer {CSK_OPPORTUNITY_ID}",
    )
    assert CSK_OPPORTUNITY_ID not in cv
    assert CSK_OPPORTUNITY_ID not in cl
    assert "opp_" not in cv.lower()
    assert "opp_" not in cl.lower()
    assert cv.endswith(" - CV.pdf")
    assert cl.endswith(" - Cover Letter.pdf")
    assert not cv.startswith("opp_")
    assert not cl.startswith("opp_")


def test_csk_nexus_long_title_fits_measured_windows_prefix() -> None:
    export_dir = _abs_dir_with_len(130)
    cv, cl = build_external_upload_filenames(
        full_name="David Cropper",
        company=CSK_COMPANY,
        title=CSK_TITLE,
        export_dir=export_dir,
    )
    assert cv == CSK_CV_AT_PREFIX_130
    assert cl == CSK_CL_AT_PREFIX_130
    cv_dest = _assert_dest_and_tmp_fit(export_dir, cv)
    cl_dest = _assert_dest_and_tmp_fit(export_dir, cl)
    assert atomic_tmp_path(cv_dest).name.endswith(".pdf.tmp")
    assert atomic_tmp_path(cl_dest).name.endswith(".pdf.tmp")
    assert cv[: -len(" - CV.pdf")] == cl[: -len(" - Cover Letter.pdf")]
    assert "Senior AI Engineer" in cv
    assert "CSK Nexus" in cv
    assert "|" not in cv
    assert "|" not in cl
    assert "Agentic AI" not in cv
    assert "Customer Support" not in cl


def test_absolute_path_budget_with_long_packages_root() -> None:
    export_dir = _abs_dir_with_len(175)
    cv, cl = build_external_upload_filenames(
        full_name="David Cropper",
        company=CSK_COMPANY,
        title=CSK_TITLE,
        export_dir=export_dir,
    )
    _assert_dest_and_tmp_fit(export_dir, cv)
    _assert_dest_and_tmp_fit(export_dir, cl)
    assert cv[: -len(" - CV.pdf")] == cl[: -len(" - Cover Letter.pdf")]
    assert cv.endswith(" - CV.pdf")
    assert cl.endswith(" - Cover Letter.pdf")
    assert "opp_" not in cv.lower()
    assert len(cv) <= 180
    assert len(cl) <= 180


def test_very_long_employer_and_role_fit_deterministically() -> None:
    export_dir = _abs_dir_with_len(130)
    company = "Very Long Employer " + ("Name " * 40)
    title = "Principal Distinguished Staff " + ("Keyword " * 40) + "| Extra | More"
    cv, cl = build_external_upload_filenames(
        full_name="David Cropper",
        company=company,
        title=title,
        export_dir=export_dir,
    )
    _assert_dest_and_tmp_fit(export_dir, cv)
    _assert_dest_and_tmp_fit(export_dir, cl)
    assert cv[: -len(" - CV.pdf")] == cl[: -len(" - Cover Letter.pdf")]
    assert cv.endswith(" - CV.pdf")
    assert cl.endswith(" - Cover Letter.pdf")
    assert cv != cl
    assert "David Cropper" in cv
    assert "|" not in cv
    assert "opp_" not in cv.lower()
    again_cv, again_cl = build_external_upload_filenames(
        full_name="David Cropper",
        company=company,
        title=title,
        export_dir=export_dir,
    )
    assert (again_cv, again_cl) == (cv, cl)


def test_tmp_suffix_included_in_budget() -> None:
    """Dest can fit 240 while ``.pdf.tmp`` (+4) overflows and must force fitting."""
    export_dir = _abs_dir_with_len(130)
    # Unfitted CL dest = 130 + 1 + (38 + employer + role). Target dest 238 / tmp 242.
    company = "Example Employer Ltd"
    title = (
        "Senior AI Engineer - AWS Bedrock Platform Services | Agentic AI | Extra"
    )
    unfitted_cl = (
        "David Cropper - Example Employer Ltd - "
        "Senior AI Engineer - AWS Bedrock Platform Services - Cover Letter.pdf"
    )
    unfitted_dest = export_dir / unfitted_cl
    unfitted_tmp = atomic_tmp_path(unfitted_dest)
    assert len(str(unfitted_dest)) <= MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN, len(
        str(unfitted_dest)
    )
    assert len(str(unfitted_tmp)) > MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN, len(
        str(unfitted_tmp)
    )
    assert len(str(unfitted_tmp)) == len(str(unfitted_dest)) + 4

    cv, cl = build_external_upload_filenames(
        full_name="David Cropper",
        company=company,
        title=title,
        export_dir=export_dir,
    )
    cl_dest = _assert_dest_and_tmp_fit(export_dir, cl)
    _assert_dest_and_tmp_fit(export_dir, cv)
    assert len(str(atomic_tmp_path(cl_dest))) <= MAX_EXTERNAL_UPLOAD_ABS_PATH_LEN
    assert cl != unfitted_cl
    assert cl.endswith(" - Cover Letter.pdf")
    assert cv[: -len(" - CV.pdf")] == cl[: -len(" - Cover Letter.pdf")]


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
    assert again.cover_letter_pdf.read_bytes() == auth_cl.read_bytes()


def test_rematerialize_removes_stale_previous_policy_export(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path,
        company=CSK_COMPANY,
        title=CSK_TITLE,
    )
    service = package_service(tmp_path, opportunities, profile)
    manifest = service.prepare(opportunity_id, **approved_gate_options())  # type: ignore[arg-type]
    auth_cv = Path(manifest.cv.pdf_path)
    auth_cl = Path(manifest.cover_letter.pdf_path)

    export_dir = tmp_path / "application_packages" / opportunity_id / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    stale_cv = export_dir / (
        "David Cropper - CSK Nexus Pty Ltd - Senior AI Engineer - AWS Bedrock "
        "Agentic AI Leftover - CV.pdf"
    )
    leftover_tmp = export_dir / f"{stale_cv.name}.tmp"
    stale_cv.write_bytes(b"%PDF-stale-cv")
    leftover_tmp.write_bytes(b"%PDF-stale-tmp")
    notes = export_dir / "owner-notes.txt"
    notes.write_text("keep", encoding="utf-8")

    exports = materialize_external_upload_pdfs(
        manifest,
        packages_root=tmp_path / "application_packages",
        full_name="David Cropper",
    )
    assert not stale_cv.exists()
    assert not leftover_tmp.exists()
    assert notes.is_file()
    assert exports.cv_pdf.is_file()
    assert exports.cover_letter_pdf.is_file()
    assert exports.cv_pdf.name.endswith(" - CV.pdf")
    assert exports.cover_letter_pdf.name.endswith(" - Cover Letter.pdf")
    assert exports.cv_pdf.name != stale_cv.name
    assert exports.cv_pdf.read_bytes() == auth_cv.read_bytes()
    assert exports.cover_letter_pdf.read_bytes() == auth_cl.read_bytes()
    remaining_pdfs = sorted(p.name for p in export_dir.glob("*.pdf"))
    assert remaining_pdfs == sorted(
        [exports.cv_pdf.name, exports.cover_letter_pdf.name]
    )
