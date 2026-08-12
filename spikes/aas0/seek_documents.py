"""SEEK Choose Documents helpers for AAS-0 (spike-only)."""

from __future__ import annotations

from pathlib import Path

from .metrics import SpikeMetrics
from .state_progress import (
    CoverLetterGateError,
    assert_cover_letter_radio_checked,
    assert_may_continue_documents_step,
    detect_validation_messages,
    fingerprint_from_text,
)

COVER_LETTER_UPLOAD_LABEL = "Upload a cover letter"


def page_body_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception:  # noqa: BLE001
        return ""


def capture_fingerprint(page, *, marker: str = ""):
    return fingerprint_from_text(
        url=getattr(page, "url", "") or "",
        body_text=page_body_text(page),
        marker=marker,
    )


def cover_letter_method_radios_present(page) -> bool:
    radio = page.get_by_role("radio", name=COVER_LETTER_UPLOAD_LABEL)
    try:
        return radio.count() > 0
    except Exception:  # noqa: BLE001
        return False


def is_cover_letter_upload_radio_checked(page) -> bool:
    radio = page.get_by_role("radio", name=COVER_LETTER_UPLOAD_LABEL)
    try:
        if radio.count() == 0:
            return False
        return bool(radio.first.is_checked())
    except Exception:  # noqa: BLE001
        return False


def select_cover_letter_upload_method(page, metrics: SpikeMetrics) -> bool:
    """Select and verify the Upload cover-letter radio. Returns True if checked."""
    radio = page.get_by_role("radio", name=COVER_LETTER_UPLOAD_LABEL)
    if radio.count() == 0:
        metrics.add_note("Cover-letter upload radio not present on page")
        return False
    try:
        radio.first.check(timeout=5_000)
    except Exception:
        try:
            radio.first.click(timeout=5_000)
        except Exception as error:  # noqa: BLE001
            metrics.add_failure(f"cover_letter_radio_select_failed: {error}")
            return False
    page.wait_for_timeout(400)
    checked = is_cover_letter_upload_radio_checked(page)
    if checked:
        metrics.add_note("Cover-letter upload radio checked and verified")
    else:
        metrics.add_failure(
            "Cover-letter upload radio click did not result in checked state"
        )
    return checked


def cover_letter_file_input(page):
    return page.locator(
        'input[type=file][data-automation*="cover"], '
        'input[type=file][id*="cover"], '
        'input[type=file][name*="cover"], '
        'input[type=file][aria-label*="cover"], '
        'input[type=file][data-automation*="Cover"], '
        'input[type=file][id*="Cover"]'
    )


def resume_file_input(page):
    return page.locator(
        'input[type=file][data-automation*="resume"], '
        'input[type=file][id*="resume"], '
        'input[type=file][name*="resume"], '
        'input[type=file][aria-label*="resume"], '
        'input[type=file][data-automation*="Resume"]'
    )


def cover_letter_filename_visible(page, filename: str) -> bool:
    stem = Path(filename).name
    try:
        loc = page.get_by_text(stem, exact=False)
        return loc.count() > 0 and loc.first.is_visible()
    except Exception:  # noqa: BLE001
        return False


def prepare_and_upload_documents(
    page,
    *,
    cv_pdf: Path,
    cl_pdf: Path,
    metrics: SpikeMetrics,
) -> bool:
    """Upload CV/CL only after cover-letter method radio is verified when present."""
    uploaded_any = False
    radios_present = cover_letter_method_radios_present(page)
    if radios_present:
        checked = select_cover_letter_upload_method(page, metrics)
        try:
            assert_cover_letter_radio_checked(checked)
        except CoverLetterGateError as error:
            metrics.add_failure(str(error))
            return False
        cover_inputs = cover_letter_file_input(page)
        try:
            if cover_inputs.count() == 0:
                metrics.add_failure(
                    "Cover-letter file input not available after radio selection"
                )
                return False
        except Exception as error:  # noqa: BLE001
            metrics.add_failure(f"cover_letter_input_probe_failed: {error}")
            return False

    # Resume upload (skip avatar). Prefer resume-named inputs; else skip if already selected.
    resume_inputs = resume_file_input(page)
    if resume_inputs.count() > 0:
        try:
            resume_inputs.first.set_input_files(str(cv_pdf))
            metrics.documents_uploaded.append(f"cv:{cv_pdf.name}")
            metrics.record_field(
                "upload:resume",
                "auto",
                detail="cv",
                value_preview=cv_pdf.name,
            )
            uploaded_any = True
            metrics.add_note(f"Uploaded cv via resume input: {cv_pdf.name}")
            page.wait_for_timeout(800)
        except Exception as error:  # noqa: BLE001
            metrics.add_failure(f"upload_failed[cv]: {error}")

    if radios_present:
        cover_inputs = cover_letter_file_input(page)
        try:
            cover_inputs.first.set_input_files(str(cl_pdf))
            page.wait_for_timeout(1000)
            if not cover_letter_filename_visible(page, cl_pdf.name):
                # Some SEEK UIs show a generic "Cover letter uploaded" without filename.
                body = page_body_text(page).lower()
                if "cover letter" not in body:
                    metrics.add_failure(
                        f"Cover-letter PDF not visible after upload: {cl_pdf.name}"
                    )
                    return uploaded_any
            metrics.documents_uploaded.append(f"cover_letter:{cl_pdf.name}")
            metrics.record_field(
                "upload:cover_letter",
                "auto",
                detail="cover_letter",
                value_preview=cl_pdf.name,
            )
            uploaded_any = True
            metrics.add_note(f"Uploaded cover_letter via cover input: {cl_pdf.name}")
        except Exception as error:  # noqa: BLE001
            metrics.add_failure(f"upload_failed[cover_letter]: {error}")
            return uploaded_any

    return uploaded_any


def documents_step_ready_to_continue(page) -> None:
    """Raise CoverLetterGateError when Choose Documents must not Continue."""
    body = page_body_text(page)
    messages = detect_validation_messages(body)
    radios_present = cover_letter_method_radios_present(page)
    checked = (
        is_cover_letter_upload_radio_checked(page) if radios_present else True
    )
    assert_may_continue_documents_step(
        radio_checked=checked,
        validation_messages=messages,
    )
