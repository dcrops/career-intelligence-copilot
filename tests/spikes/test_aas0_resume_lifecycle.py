"""AAS-0.1 résumé ownership, Default change, cleanup candidate, capacity."""

from __future__ import annotations

import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.resume_lifecycle import (  # noqa: E402
    CvRotationClass,
    SeekResumeEntry,
    build_seek_resume_snapshot,
    checkbox_outcome_from_settle,
    classify_checkbox_settle_tick,
    classify_seek_cv_for_rotation,
    detect_resume_capacity_message,
    evaluate_default_change,
    evaluate_default_checkbox_guard,
    extract_pdf_filename,
    looks_like_cover_letter_pdf_filename,
    may_auto_delete_seek_cv,
    parse_seek_added_ago_minutes,
    application_cv_is_structural_default,
    committed_structural_default_checkbox_locked,
    locked_structural_default_checkbox_outcome,
    row_is_structurally_default,
    select_cleanup_candidate,
    select_resume_row_text,
    should_skip_resume_radio_row,
)

PROTECTED_DEFAULT = "David Cropper - AI Engineer CV.pdf"
G360_CV = "David Cropper - Global 360 - AI Engineer - Applied - CV.pdf"
G360_CL = "David Cropper - Global 360 - AI Engineer - Applied - Cover Letter.pdf"
NOVIGI_CV = "David Cropper - Novigi Pty Ltd - Senior AI Engineer - CV.pdf"
OLD_CV = "David Cropper Attribute Group AI Deployment Engineer CV.pdf"


def test_non_default_filenames_are_disposable() -> None:
    names = (
        "opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf",
        "David Cropper - AI Engineer CV.pdf",
        "David Cropper Attribute Group AI Deployment Engineer CV.pdf",
        "David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf",
        "David_Cropper_Repurpose_It_AI_Engineer_CV.pdf",
        "David Cropper CV.pdf",
    )
    for name in names:
        assert classify_seek_cv_for_rotation(name) is CvRotationClass.DISPOSABLE
        assert may_auto_delete_seek_cv(name)
        assert classify_seek_cv_for_rotation(name, is_default=True) is CvRotationClass.PROTECT
        assert not may_auto_delete_seek_cv(name, is_default=True)


def test_default_badge_is_structural_not_filename() -> None:
    assert row_is_structurally_default(
        "opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf\nDefault\nMake this my default résumé"
    )
    assert not row_is_structurally_default(
        "David Cropper Attribute Group AI Deployment Engineer CV.pdf\n"
        "Make this my default résumé"
    )
    # Recruiter-discovery name is Default only when the badge is present.
    assert row_is_structurally_default("David Cropper - AI Engineer CV.pdf\nDefault")
    assert not row_is_structurally_default("David Cropper - AI Engineer CV.pdf")


def test_default_row_cannot_be_cleanup_candidate() -> None:
    entries = (
        SeekResumeEntry(
            filename="opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf",
            is_default=True,
            is_selected=True,
            index=0,
        ),
        SeekResumeEntry(
            filename="David Cropper - AI Engineer CV.pdf",
            is_default=False,
            is_selected=False,
            index=1,
        ),
    )
    assert not may_auto_delete_seek_cv(
        "opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf", is_default=True
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.selected is True
    assert candidate.filename == "David Cropper - AI Engineer CV.pdf"
    assert candidate.index == 1


def test_cleanup_candidate_is_last_non_default_when_age_absent() -> None:
    entries = (
        SeekResumeEntry("David Cropper - AI Engineer CV.pdf", True, True, 0),
        SeekResumeEntry("opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf", False, False, 1),
        SeekResumeEntry(
            "David Cropper Attribute Group AI Deployment Engineer CV.pdf",
            False,
            False,
            2,
        ),
        SeekResumeEntry("opp_01ARZ3NDEKTSV4RRFFQ69G5FAA.pdf", False, False, 3),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.selected is True
    assert candidate.filename == "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA.pdf"
    assert candidate.index == 3
    assert candidate.reason == "oldest_non_default_last_in_newest_first_list"


def test_added_ago_parser_and_oldest_by_age() -> None:
    assert parse_seek_added_ago_minutes("Added less than a minute ago") == 0
    assert parse_seek_added_ago_minutes("Added 41 minutes ago") == 41
    assert parse_seek_added_ago_minutes("Added 7 days ago") == 7 * 1440
    assert parse_seek_added_ago_minutes("no age") is None
    entries = (
        SeekResumeEntry("new.pdf", False, True, 0, added_ago_minutes=0),
        SeekResumeEntry("mid.pdf", False, False, 1, added_ago_minutes=41),
        SeekResumeEntry("old.pdf", False, False, 2, added_ago_minutes=7 * 1440),
        SeekResumeEntry("default.pdf", True, False, 3, added_ago_minutes=30 * 1440),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.filename == "old.pdf"
    assert candidate.index == 2
    assert candidate.reason == "oldest_non_default_by_added_age"
    entries = (
        SeekResumeEntry("opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf", False, False, 0),
        SeekResumeEntry("opp_01ARZ3NDEKTSV4RRFFQ69G5FAA.pdf", False, False, 1),
    )
    first = select_cleanup_candidate(entries)
    second = select_cleanup_candidate(entries)
    assert first == second


def test_mixed_age_metadata_falls_back_to_last_non_default() -> None:
    entries = (
        SeekResumeEntry("aged.pdf", False, False, 0, added_ago_minutes=7 * 1440),
        SeekResumeEntry("no-age.pdf", False, False, 1, added_ago_minutes=None),
        SeekResumeEntry("default.pdf", True, False, 2, added_ago_minutes=None),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.selected is True
    assert candidate.filename == "no-age.pdf"
    assert candidate.index == 1
    assert candidate.reason == "oldest_non_default_last_in_newest_first_list"
    assert candidate.reason != "oldest_age_order_ambiguous"


def test_snapshot_parses_default_badge_and_skips_cover_letter_radios() -> None:
    snapshot = build_seek_resume_snapshot(
        [
            (
                "opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf\nDefault\n"
                "Make this my default résumé",
                True,
            ),
            ("David Cropper Attribute Group AI Deployment Engineer CV.pdf", False),
            ("Upload a cover letter", False),
            ("Don't include a résumé", False),
        ]
    )
    assert snapshot.default_observable is True
    assert snapshot.default_filename == "opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf"
    assert snapshot.selected_filename == "opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf"
    assert len(snapshot.entries) == 2


def test_resume_inventory_contains_saved_resume_rows_only() -> None:
    snapshot = build_seek_resume_snapshot(
        [
            (f"{PROTECTED_DEFAULT}\nDefault\nAdded 7 days ago", False),
            (f"{NOVIGI_CV}\nAdded 41 minutes ago", True),
            (f"{G360_CV}\nAdded less than a minute ago", False),
            (f"{OLD_CV}\nAdded 14 days ago", False),
            ("Upload", False),
            ("Don't include a résumé", False),
            ("Upload a cover letter", False),
            (G360_CL, False),
            (f"Upload a cover letter\n{G360_CL}", False),
            ("Write a cover letter", False),
            ("Don't include a cover letter", False),
        ]
    )
    names = [entry.filename for entry in snapshot.entries]
    assert names == [PROTECTED_DEFAULT, NOVIGI_CV, G360_CV, OLD_CV]
    assert snapshot.default_filename == PROTECTED_DEFAULT


def test_cover_letter_filename_elsewhere_on_page_never_enters_inventory() -> None:
    cv_row = select_resume_row_text(
        [
            G360_CV,
            f"{G360_CV}\nAdded 41 minutes ago",
            f"{G360_CV}\nAdded 41 minutes ago\n{G360_CL}\nDon't include a résumé",
        ]
    )
    assert extract_pdf_filename(cv_row) == G360_CV
    snapshot = build_seek_resume_snapshot(
        [
            (f"{PROTECTED_DEFAULT}\nDefault", True),
            (cv_row, False),
            (G360_CL, False),
            (f"Cover letter\n{G360_CL}", False),
        ]
    )
    names = [entry.filename for entry in snapshot.entries]
    assert names == [PROTECTED_DEFAULT, G360_CV]
    assert G360_CL not in names


def test_global_360_cover_letter_cannot_be_rotation_candidate() -> None:
    assert looks_like_cover_letter_pdf_filename(G360_CL)
    assert should_skip_resume_radio_row(G360_CL)
    snapshot = build_seek_resume_snapshot(
        [
            (f"{PROTECTED_DEFAULT}\nDefault", True),
            (NOVIGI_CV, False),
            (G360_CL, False),
            ("Don't include a résumé", False),
        ]
    )
    candidate = select_cleanup_candidate(snapshot.entries)
    assert candidate.selected is True
    assert candidate.filename == NOVIGI_CV
    assert candidate.filename != G360_CL
    slipped = (
        SeekResumeEntry(PROTECTED_DEFAULT, True, True, 0),
        SeekResumeEntry(NOVIGI_CV, False, False, 1),
        SeekResumeEntry(G360_CL, False, False, 2),
    )
    slipped_candidate = select_cleanup_candidate(slipped)
    assert slipped_candidate.filename == NOVIGI_CV
    assert slipped_candidate.index == 1


def test_dont_include_a_resume_is_not_a_rotation_candidate() -> None:
    assert should_skip_resume_radio_row("Don't include a résumé")
    snapshot = build_seek_resume_snapshot(
        [
            (f"{PROTECTED_DEFAULT}\nDefault", True),
            (NOVIGI_CV, False),
            ("Don't include a résumé", False),
            (f"Don't include a résumé\n{G360_CV}", False),
        ]
    )
    names = [entry.filename for entry in snapshot.entries]
    assert names == [PROTECTED_DEFAULT, NOVIGI_CV]
    candidate = select_cleanup_candidate(snapshot.entries)
    assert candidate.filename == NOVIGI_CV


def test_oldest_actual_non_default_resume_selected_when_cover_letter_present() -> None:
    snapshot = build_seek_resume_snapshot(
        [
            (f"{PROTECTED_DEFAULT}\nDefault", True),
            (NOVIGI_CV, False),
            (OLD_CV, False),
            ("Don't include a résumé", False),
            (G360_CL, False),
            (f"Upload a cover letter\n{G360_CL}", False),
        ]
    )
    candidate = select_cleanup_candidate(snapshot.entries)
    assert [entry.filename for entry in snapshot.entries] == [
        PROTECTED_DEFAULT,
        NOVIGI_CV,
        OLD_CV,
    ]
    assert candidate.selected is True
    assert candidate.filename == OLD_CV
    assert candidate.reason == "oldest_non_default_last_in_newest_first_list"


def test_fail_closed_when_default_markers_are_ambiguous() -> None:
    snapshot = build_seek_resume_snapshot(
        [
            ("alpha.pdf\nDefault", False),
            ("beta.pdf\nDefault", True),
        ]
    )
    assert snapshot.ambiguous_default is True
    assert snapshot.default_observable is False
    before = snapshot
    after = build_seek_resume_snapshot([("alpha.pdf\nDefault", True)])
    result = evaluate_default_change(before, after)
    assert result.should_stop is True
    assert result.reason == "pre_upload_default_ambiguous"


def test_default_change_stops_and_does_not_assume_uncheck_restores() -> None:
    before = build_seek_resume_snapshot(
        [("David Cropper - AI Engineer CV.pdf\nDefault", True)]
    )
    after = build_seek_resume_snapshot(
        [
            (
                "David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf\n"
                "Default\nMake this my default résumé",
                True,
            ),
            ("David Cropper - AI Engineer CV.pdf", False),
        ]
    )
    result = evaluate_default_change(before, after)
    assert result.changed is True
    assert result.should_stop is True
    assert result.reason == "default_filename_changed"
    assert result.before == "David Cropper - AI Engineer CV.pdf"
    assert result.after == "David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf"


def test_default_unchanged_does_not_stop() -> None:
    before = build_seek_resume_snapshot(
        [("David Cropper - AI Engineer CV.pdf\nDefault", False)]
    )
    after = build_seek_resume_snapshot(
        [
            ("David Cropper - AI Engineer CV.pdf\nDefault", False),
            ("David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf", True),
        ]
    )
    result = evaluate_default_change(before, after)
    assert result.should_stop is False
    assert result.reason == "default_unchanged"


def test_missing_pre_upload_default_does_not_claim_change() -> None:
    before = build_seek_resume_snapshot([])
    after = build_seek_resume_snapshot(
        [("David Cropper - AI Engineer CV.pdf\nDefault", True)]
    )
    result = evaluate_default_change(before, after)
    assert result.changed is False
    assert result.should_stop is False
    assert result.reason == "pre_upload_default_not_observable"


def test_lost_default_observation_after_upload_stops() -> None:
    before = build_seek_resume_snapshot(
        [("David Cropper - AI Engineer CV.pdf\nDefault", True)]
    )
    after = build_seek_resume_snapshot([])
    result = evaluate_default_change(before, after)
    assert result.should_stop is True
    assert result.reason == "post_upload_default_not_observable"


def test_capacity_message_detection_is_conservative() -> None:
    hit = detect_resume_capacity_message(
        "You have reached the maximum number of résumés"
    )
    assert hit is not None
    assert "maximum" in hit.lower()
    limit = detect_resume_capacity_message("Résumé limit reached")
    assert limit is not None
    assert "limit" in limit.lower()
    assert detect_resume_capacity_message("Resume limit reached") is not None
    assert detect_resume_capacity_message(
        "Please select a résumé to delete from your list and try again."
    ) is not None
    assert detect_resume_capacity_message("Cover letter - Please make a selection") is None
    assert detect_resume_capacity_message("Choose documents") is None


def test_application_cv_must_not_be_accepted_structural_default() -> None:
    expected = "David Cropper - CSK Nexus Pty Ltd - Senior AI Engineer - AWS Bedrock - CV.pdf"
    assert application_cv_is_structural_default(
        default_filename=expected,
        expected_filename=expected,
    )
    assert not application_cv_is_structural_default(
        default_filename="David Cropper - AI Engineer CV.pdf",
        expected_filename=expected,
    )


def test_row_text_includes_default_badge_from_row_container_not_radio_label() -> None:
    """Live defect: radio label was filename-only; badge lived on the row."""
    general = "Candidate - Role CV.pdf"
    other = "Other Employer Role CV.pdf"
    row = select_resume_row_text(
        [
            "",
            general,
            f"Default\n{general}\nAdded 41 minutes ago",
            f"Default\n{general}\n{other}\nDon't include a résumé",
        ]
    )
    assert row_is_structurally_default(row)
    assert extract_pdf_filename(row) == general


def test_fixture_a_default_badge_on_general_cv_other_selected() -> None:
    general = "Candidate - Role CV.pdf"
    other = "Other Employer Role CV.pdf"
    snapshot = build_seek_resume_snapshot(
        [
            (f"Default\n{general}\nAdded 41 minutes ago", False),
            (
                f"{other}\nAdded 7 days ago\nMake this my default résumé",
                True,
            ),
        ]
    )
    assert snapshot.default_observable is True
    assert snapshot.default_filename == general
    assert snapshot.selected_filename == other
    assert snapshot.default_filename != snapshot.selected_filename


def test_fixture_b_after_upload_default_and_selected_are_tailored() -> None:
    tailored = "Candidate - Employer - Role - CV.pdf"
    general = "Candidate - Role CV.pdf"
    snapshot = build_seek_resume_snapshot(
        [
            (
                f"Default\n{tailored}\nAdded less than a minute ago\n"
                "Make this my default résumé",
                True,
            ),
            (f"{general}\nAdded 42 minutes ago", False),
        ]
    )
    assert snapshot.default_filename == tailored
    assert snapshot.selected_filename == tailored
    assert snapshot.default_observable is True


def test_checkbox_uncheck_success_does_not_stop() -> None:
    outcome = evaluate_default_checkbox_guard(
        present=True,
        was_checked=True,
        still_checked=False,
        uncheck_attempted=True,
    )
    assert outcome.should_stop is False
    assert outcome.uncheck_succeeded is True
    assert outcome.reason == "checkbox_unchecked"


def test_checkbox_uncheck_failure_stops() -> None:
    outcome = evaluate_default_checkbox_guard(
        present=True,
        was_checked=True,
        still_checked=True,
        uncheck_attempted=True,
    )
    assert outcome.should_stop is True
    assert outcome.reason == "default_checkbox_remained_checked"


def test_unobservable_default_plus_failed_checkbox_still_stops() -> None:
    before = build_seek_resume_snapshot(
        [("other.pdf", True), ("general.pdf", False)]
    )
    after = build_seek_resume_snapshot(
        [("tailored.pdf", True), ("general.pdf", False)]
    )
    change = evaluate_default_change(before, after)
    assert change.should_stop is False
    assert change.reason == "pre_upload_default_not_observable"
    checkbox = evaluate_default_checkbox_guard(
        present=True,
        was_checked=True,
        still_checked=True,
        uncheck_attempted=True,
    )
    assert checkbox.should_stop is True


HATCH_CV = "David Cropper - Hatch - AI Trainer - CV.pdf"
THIRD_CV = "David Cropper - Other Employer - AI Engineer - CV.pdf"


def _settle(**overrides):
    fields = dict(
        checked=True,
        enabled=False,
        current_default=HATCH_CV,
        default_observable=True,
        baseline_default=PROTECTED_DEFAULT,
        baseline_observable=True,
        application_filename=HATCH_CV,
        elapsed_ms=0,
        timeout_ms=15_000,
    )
    fields.update(overrides)
    return classify_checkbox_settle_tick(**fields)


def test_settle_keeps_waiting_while_application_cv_is_temporary_default() -> None:
    tick = _settle(checked=True, enabled=False, elapsed_ms=400)
    assert tick.action == "keep_waiting"
    assert tick.reason == "checkbox_settle_pending"


def test_settle_success_requires_unchecked_and_original_default() -> None:
    tick = _settle(
        checked=False,
        enabled=True,
        current_default=PROTECTED_DEFAULT,
        elapsed_ms=800,
    )
    assert tick.action == "success"
    assert tick.reason == "checkbox_unchecked"
    outcome = checkbox_outcome_from_settle(
        was_checked=True,
        uncheck_attempted=True,
        tick=tick,
        uncheck_threw=True,
        baseline_default=PROTECTED_DEFAULT,
        poll_count=3,
        elapsed_ms=800,
    )
    assert outcome.should_stop is False
    assert outcome.uncheck_succeeded is True
    assert outcome.still_checked is False
    assert outcome.settled_default_filename == PROTECTED_DEFAULT


def test_settle_success_without_baseline_is_checkbox_only() -> None:
    tick = _settle(
        checked=False,
        baseline_observable=False,
        baseline_default=None,
        current_default=HATCH_CV,
    )
    assert tick.action == "success"
    assert tick.reason == "checkbox_unchecked"


def test_settle_timeout_when_unchecked_but_default_stays_application_cv() -> None:
    tick = _settle(checked=False, elapsed_ms=15_000)
    assert tick.action == "stop"
    assert tick.reason == "default_checkbox_settle_timeout"


def test_settle_timeout_when_default_restored_but_checkbox_stays_checked() -> None:
    tick = _settle(
        checked=True,
        current_default=PROTECTED_DEFAULT,
        elapsed_ms=15_000,
    )
    assert tick.action == "stop"
    assert tick.reason == "default_checkbox_settle_timeout"


def test_settle_stops_on_unexpected_third_default() -> None:
    tick = _settle(current_default=THIRD_CV, elapsed_ms=0)
    assert tick.action == "stop"
    assert tick.reason == "default_changed_unexpectedly"


def test_settle_timeout_when_default_unobservable() -> None:
    tick = _settle(
        default_observable=False,
        current_default=None,
        elapsed_ms=15_000,
    )
    assert tick.action == "stop"
    assert tick.reason == "default_unobservable_after_uncheck"


def test_settle_ignores_enabled_for_success() -> None:
    tick = _settle(
        checked=False,
        enabled=False,
        current_default=PROTECTED_DEFAULT,
    )
    assert tick.action == "success"


def test_successful_upload_autocheck_then_uncheck_restores_baseline() -> None:
    pending = _settle(checked=True, current_default=HATCH_CV, elapsed_ms=0)
    assert pending.action == "keep_waiting"
    restored = _settle(
        checked=False,
        enabled=True,
        current_default=PROTECTED_DEFAULT,
        elapsed_ms=1_200,
    )
    assert restored.action == "success"
    assert restored.reason == "checkbox_unchecked"
    after = build_seek_resume_snapshot(
        [
            (HATCH_CV, True),
            (f"Default\n{PROTECTED_DEFAULT}", False),
        ]
    )
    assert after.selected_filename == HATCH_CV
    assert after.default_filename == PROTECTED_DEFAULT


def test_expected_cv_stays_selected_while_structural_default_restores() -> None:
    after = build_seek_resume_snapshot(
        [
            (HATCH_CV, True),
            (f"Default\n{PROTECTED_DEFAULT}", False),
        ]
    )
    before = build_seek_resume_snapshot(
        [
            (NOVIGI_CV, True),
            (f"Default\n{PROTECTED_DEFAULT}", False),
        ]
    )
    change = evaluate_default_change(before, after)
    assert change.should_stop is False
    assert change.reason == "default_unchanged"
    assert after.selected_filename == HATCH_CV
    assert after.default_filename == PROTECTED_DEFAULT


def test_committed_default_checkbox_requires_disabled_and_selected_equals_default() -> None:
    csk = (
        "David Cropper - CSK Nexus Pty Ltd - Senior AI Engineer - AWS Bedrock - CV.pdf"
    )
    assert committed_structural_default_checkbox_locked(
        checked=True,
        enabled=False,
        selected_filename=csk,
        default_filename=csk,
    )
    assert not committed_structural_default_checkbox_locked(
        checked=True,
        enabled=True,
        selected_filename=HATCH_CV,
        default_filename=HATCH_CV,
    )
    assert not committed_structural_default_checkbox_locked(
        checked=True,
        enabled=False,
        selected_filename=HATCH_CV,
        default_filename=PROTECTED_DEFAULT,
    )
    assert not committed_structural_default_checkbox_locked(
        checked=False,
        enabled=False,
        selected_filename=csk,
        default_filename=csk,
    )
    assert not committed_structural_default_checkbox_locked(
        checked=True,
        enabled=None,
        selected_filename=csk,
        default_filename=csk,
    )
    outcome = locked_structural_default_checkbox_outcome(
        default_filename=csk,
        selected_filename=csk,
    )
    assert outcome.should_stop is True
    assert outcome.uncheck_attempted is False
    assert outcome.reason == "structural_default_checkbox_locked"
    assert outcome.settle_poll_count == 0
    assert outcome.checkbox_enabled is False
