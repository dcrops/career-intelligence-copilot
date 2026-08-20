"""AAS-0.1 bounded SEEK résumé rotation: Default protected, oldest disposable."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.document_gates import (  # noqa: E402
    evaluate_cv_upload_wait_tick,
    evaluate_expected_cv_selection,
)
from aas0.resume_lifecycle import (  # noqa: E402
    SeekResumeEntry,
    SeekResumeSnapshot,
    build_seek_resume_snapshot,
    select_cleanup_candidate,
)
from aas0.resume_rotation import (  # noqa: E402
    SEEK_RESUME_DELETE_ACTION,
    SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
    SEEK_RESUME_DELETE_CONFIRMATION_CLOSE,
    SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
    SEEK_RESUME_DELETE_CONFIRMATION_PROMPT,
    SEEK_RESUME_DELETE_MENU_LABELS,
    ResumeRowMenu,
    build_delete_confirmation_observation,
    confirmation_accessible_name,
    confirmation_planner_branch,
    empty_delete_confirmation_observation,
    evaluate_deletion_verification,
    evaluate_rotation_decision,
    evaluate_rotation_trigger,
    explain_cleanup_skips,
    normalise_confirmation_action_name,
    perform_one_resume_deletion,
    plan_resume_delete_click,
    plan_resume_delete_confirmation,
    refuse_unobserved_resume_deletion,
    seek_delete_menu_is_observed,
    wait_until_deletion_verified,
)
from aas0.session_handoff import build_final_review_handoff  # noqa: E402
from aas0.submit_guard import ControlClass, PageSignals, classify_control  # noqa: E402

PROTECTED_DEFAULT = "David Cropper - AI Engineer CV.pdf"
OPP_NEW = "opp_01M0CBFRA0SQR1769T6KTKJ6RK.pdf"
OPP_MID = "opp_01KZQJY6AX3EGX7TGYTHR3ABG1.pdf"
OPP_OLD = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA.pdf"
NOVIGI_CV = "David Cropper - Novigi Pty Ltd - Senior AI Engineer - CV.pdf"
G360_CV = "David Cropper - Global 360 - AI Engineer - Applied - CV.pdf"
G360_CL = "David Cropper - Global 360 - AI Engineer - Applied - Cover Letter.pdf"
FORWARD_DEPLOYED = "David Cropper Forward Deployed AI Engineer CV.pdf"
EXPECTED_G360 = G360_CV
DUP = "duplicate-name.pdf"
LIVE_DELETE_ACCESSIBLE_NAME = "\u2060Delete"
LIVE_CONFIRM_ACTIONS = (
    LIVE_DELETE_ACCESSIBLE_NAME,
    SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
    SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
)


def _observed_confirm_actions(*extra: str) -> tuple[str, ...]:
    return (
        SEEK_RESUME_DELETE_ACTION,
        SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
        SEEK_RESUME_DELETE_CONFIRMATION_CLOSE,
    ) + extra


def _entry(
    filename: str,
    *,
    is_default: bool = False,
    is_selected: bool = False,
    index: int = 0,
    added_ago_minutes: int | None = None,
) -> SeekResumeEntry:
    return SeekResumeEntry(
        filename=filename,
        is_default=is_default,
        is_selected=is_selected,
        index=index,
        added_ago_minutes=added_ago_minutes,
    )


def _snapshot(entries: tuple[SeekResumeEntry, ...]) -> SeekResumeSnapshot:
    defaults = [entry.filename for entry in entries if entry.is_default]
    unique = list(dict.fromkeys(defaults))
    selected = next((entry.filename for entry in entries if entry.is_selected), None)
    return SeekResumeSnapshot(
        entries=entries,
        default_filename=unique[0] if len(unique) == 1 else None,
        default_observable=len(unique) == 1,
        selected_filename=selected,
        ambiguous_default=len(unique) > 1,
    )


def _full_inventory() -> tuple[SeekResumeEntry, ...]:
    return (
        _entry(PROTECTED_DEFAULT, is_default=True, index=0),
        _entry(OPP_NEW, index=1),
        _entry(OPP_MID, index=2),
        _entry(OPP_OLD, index=3),
        _entry(NOVIGI_CV, is_selected=True, index=4),
        _entry(G360_CV, index=5),
    )


class FakeResumeDeleteDriver:
    def __init__(
        self,
        rows: tuple[ResumeRowMenu, ...],
        *,
        confirmation_mode: str = "observed",
        confirmation_before: bool = False,
    ) -> None:
        self.rows = list(rows)
        self.opened: list[int] = []
        self.clicked: list[str] = []
        self.confirmation_clicked: list[str] = []
        self.cancel_clicked: list[str] = []
        self.close_clicked: list[str] = []
        self.dismiss_clicked: list[str] = []
        self.confirmation_mode = confirmation_mode
        self._confirm = confirmation_before
        self._opened_index: int | None = None

    def confirmation_dialog_visible(self) -> bool:
        return self._confirm

    def _opened_filename(self) -> str | None:
        if self._opened_index is None:
            return None
        for row in self.rows:
            if row.index == self._opened_index:
                return row.filename
        return None

    def observe_delete_confirmation(
        self, candidate_filename: str | None = None
    ):
        if not self._confirm:
            return empty_delete_confirmation_observation()
        opened = self._opened_filename()
        mode = self.confirmation_mode
        if mode == "unknown":
            return build_delete_confirmation_observation(
                dialog_count=1,
                dialog_text="Please confirm this action.\nDelete\nCancel",
                candidate_filename=candidate_filename,
                action_names=_observed_confirm_actions(),
            )
        if mode == "mismatch":
            return build_delete_confirmation_observation(
                dialog_count=1,
                dialog_text=(
                    f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n"
                    f"{NOVIGI_CV}\nDelete\nCancel"
                ),
                candidate_filename=candidate_filename,
                action_names=_observed_confirm_actions(),
            )
        if mode == "missing_filename":
            return build_delete_confirmation_observation(
                dialog_count=1,
                dialog_text=f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\nDelete\nCancel",
                candidate_filename=candidate_filename,
                action_names=_observed_confirm_actions(),
            )
        if mode == "multiple_delete":
            return build_delete_confirmation_observation(
                dialog_count=1,
                dialog_text=(
                    f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{opened}\nDelete\nDelete\nCancel"
                ),
                candidate_filename=candidate_filename,
                action_names=(
                    SEEK_RESUME_DELETE_ACTION,
                    SEEK_RESUME_DELETE_ACTION,
                    SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
                    SEEK_RESUME_DELETE_CONFIRMATION_CLOSE,
                ),
            )
        if mode == "multiple_dialogs":
            return build_delete_confirmation_observation(
                dialog_count=2,
                dialog_text=(
                    f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{opened}\nDelete\nCancel"
                ),
                candidate_filename=candidate_filename,
                action_names=_observed_confirm_actions(),
            )
        if mode == "extra_action":
            return build_delete_confirmation_observation(
                dialog_count=1,
                dialog_text=(
                    f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{opened}\nDelete\nCancel"
                ),
                candidate_filename=candidate_filename,
                action_names=_observed_confirm_actions("Continue"),
            )
        if mode == "live":
            return build_delete_confirmation_observation(
                dialog_count=1,
                dialog_text=(
                    f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{opened}\n"
                    f"{LIVE_DELETE_ACCESSIBLE_NAME}\nCancel"
                ),
                candidate_filename=candidate_filename,
                action_names=LIVE_CONFIRM_ACTIONS,
            )
        return build_delete_confirmation_observation(
            dialog_count=1,
            dialog_text=(
                f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{opened}\nDelete\nCancel"
            ),
            candidate_filename=candidate_filename,
            action_names=_observed_confirm_actions(),
        )

    def row_menus(self) -> tuple[ResumeRowMenu, ...]:
        return tuple(self.rows)

    def open_overflow(self, row_index: int) -> str:
        self.opened.append(row_index)
        self._opened_index = row_index
        updated: list[ResumeRowMenu] = []
        for row in self.rows:
            if row.index == row_index:
                updated.append(
                    ResumeRowMenu(
                        filename=row.filename,
                        index=row.index,
                        is_default=row.is_default,
                        overflow_control_count=row.overflow_control_count,
                        menu_open=True,
                        menu_actions=("Download", "Delete"),
                    )
                )
            else:
                updated.append(
                    ResumeRowMenu(
                        filename=row.filename,
                        index=row.index,
                        is_default=row.is_default,
                        overflow_control_count=row.overflow_control_count,
                        menu_open=False,
                        menu_actions=(),
                    )
                )
        self.rows = updated
        return "opened"

    def click_exact_delete(self) -> str:
        self.clicked.append(SEEK_RESUME_DELETE_ACTION)
        if self.confirmation_mode != "none":
            self._confirm = True
        return "clicked"

    def click_confirmation_delete(self) -> str:
        self.confirmation_clicked.append(SEEK_RESUME_DELETE_ACTION)
        self._confirm = False
        return "clicked"


def _row_menu(
    filename: str,
    *,
    index: int,
    is_default: bool = False,
    overflow: int = 1,
    menu_open: bool = False,
    actions: tuple[str, ...] = (),
) -> ResumeRowMenu:
    return ResumeRowMenu(
        filename=filename,
        index=index,
        is_default=is_default,
        overflow_control_count=overflow,
        menu_open=menu_open,
        menu_actions=actions,
    )


def test_1_oldest_non_default_selected() -> None:
    entries = _full_inventory()
    candidate = select_cleanup_candidate(entries)
    assert candidate.selected is True
    assert candidate.filename == G360_CV
    assert candidate.index == 5
    assert candidate.reason == "oldest_non_default_last_in_newest_first_list"
    skips = {skip.filename: skip.reason for skip in explain_cleanup_skips(entries)}
    assert skips == {PROTECTED_DEFAULT: "structurally_default"}


def test_global_360_cover_letter_cannot_be_rotation_candidate() -> None:
    snapshot = build_seek_resume_snapshot(
        [
            (f"{PROTECTED_DEFAULT}\nDefault", True),
            (NOVIGI_CV, False),
            (G360_CV, False),
            ("Don't include a résumé", False),
            (G360_CL, False),
            (f"Upload a cover letter\n{G360_CL}", False),
        ]
    )
    names = [entry.filename for entry in snapshot.entries]
    assert names == [PROTECTED_DEFAULT, NOVIGI_CV, G360_CV]
    assert G360_CL not in names
    candidate = select_cleanup_candidate(snapshot.entries)
    assert candidate.filename == G360_CV
    assert candidate.filename != G360_CL
    assert candidate.reason == "oldest_non_default_last_in_newest_first_list"


def test_all_eligible_rows_with_age_use_oldest_by_age() -> None:
    entries = (
        _entry(PROTECTED_DEFAULT, is_default=True, index=0, added_ago_minutes=10),
        _entry(OPP_NEW, index=1, added_ago_minutes=0),
        _entry(NOVIGI_CV, index=2, added_ago_minutes=41),
        _entry(FORWARD_DEPLOYED, index=3, added_ago_minutes=7 * 1440),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.filename == FORWARD_DEPLOYED
    assert candidate.index == 3
    assert candidate.reason == "oldest_non_default_by_added_age"


def test_2_oldest_human_readable_is_eligible() -> None:
    entries = (
        _entry(PROTECTED_DEFAULT, is_default=True, index=0),
        _entry(OPP_NEW, index=1),
        _entry(FORWARD_DEPLOYED, index=2),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.filename == FORWARD_DEPLOYED
    assert candidate.index == 2


def test_3_oldest_opp_ulid_is_eligible() -> None:
    entries = (
        _entry(PROTECTED_DEFAULT, is_default=True, index=0),
        _entry(NOVIGI_CV, index=1),
        _entry(OPP_OLD, index=2),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.filename == OPP_OLD
    assert candidate.index == 2


def test_4_default_is_oldest_overall_so_next_oldest_chosen() -> None:
    entries = (
        _entry(OPP_NEW, index=0),
        _entry(NOVIGI_CV, index=1),
        _entry(PROTECTED_DEFAULT, is_default=True, index=2),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.filename == NOVIGI_CV
    assert candidate.index == 1
    skips = explain_cleanup_skips(entries)
    assert skips[0].filename == PROTECTED_DEFAULT
    assert skips[0].reason == "structurally_default"


def test_5_duplicate_filenames_select_oldest_row() -> None:
    entries = (
        _entry(PROTECTED_DEFAULT, is_default=True, index=0),
        _entry(DUP, index=1),
        _entry(DUP, index=2),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.filename == DUP
    assert candidate.index == 2
    rows = (
        _row_menu(PROTECTED_DEFAULT, index=0, is_default=True),
        _row_menu(DUP, index=1),
        _row_menu(DUP, index=2),
    )
    plan = plan_resume_delete_click(
        candidate_filename=DUP, candidate_index=2, rows=rows
    )
    assert plan.action == "open_overflow"
    assert plan.target_index == 2
    assert plan.reason != "row_association_ambiguous"


def test_mixed_age_and_duplicate_filenames_use_last_eligible_row() -> None:
    entries = (
        _entry(PROTECTED_DEFAULT, is_default=True, index=0, added_ago_minutes=10),
        _entry(DUP, index=1, added_ago_minutes=7 * 1440),
        _entry(DUP, index=2, added_ago_minutes=None),
    )
    candidate = select_cleanup_candidate(entries)
    assert candidate.selected is True
    assert candidate.filename == DUP
    assert candidate.index == 2
    assert candidate.reason == "oldest_non_default_last_in_newest_first_list"
    plan = plan_resume_delete_click(
        candidate_filename=DUP,
        candidate_index=candidate.index,
        rows=(
            _row_menu(PROTECTED_DEFAULT, index=0, is_default=True),
            _row_menu(DUP, index=1),
            _row_menu(DUP, index=2),
        ),
    )
    assert plan.target_index == 2
    assert plan.reason != "row_association_ambiguous"


def test_6_row_local_delete_for_chosen_duplicate() -> None:
    rows = (
        _row_menu(DUP, index=1),
        _row_menu(DUP, index=2),
    )
    driver = FakeResumeDeleteDriver(rows)
    status = perform_one_resume_deletion(
        driver, candidate_filename=DUP, candidate_index=2
    )
    assert status == "clicked_delete"
    assert driver.opened == [2]
    assert driver.clicked == ["Delete"]
    assert driver.confirmation_clicked == ["Delete"]
    assert driver.cancel_clicked == []


def test_7_wrong_row_deleted_stops() -> None:
    before = _snapshot(_full_inventory())
    after_entries = tuple(
        entry for entry in before.entries if entry.filename != NOVIGI_CV
    )
    after = _snapshot(after_entries)
    result = evaluate_deletion_verification(
        before=before,
        after=after,
        deleted_filename=G360_CV,
        deleted_index=5,
    )
    assert result.should_stop is True
    assert result.reason == "wrong_row_disappeared"


def test_8_exactly_one_row_deleted_success() -> None:
    before = _snapshot(_full_inventory())
    after_entries = tuple(entry for entry in before.entries if entry.index != 5)
    after = _snapshot(after_entries)
    result = evaluate_deletion_verification(
        before=before,
        after=after,
        deleted_filename=G360_CV,
        deleted_index=5,
    )
    assert result.should_stop is False
    assert result.reason == "deletion_verified"
    assert result.default_before == PROTECTED_DEFAULT
    assert result.default_after == PROTECTED_DEFAULT


def test_9_default_change_stops() -> None:
    before = _snapshot(_full_inventory())
    after_entries = []
    for entry in before.entries:
        if entry.index == 5:
            continue
        if entry.filename == NOVIGI_CV:
            after_entries.append(
                _entry(NOVIGI_CV, is_default=True, is_selected=True, index=entry.index)
            )
            continue
        if entry.filename == PROTECTED_DEFAULT:
            after_entries.append(
                _entry(PROTECTED_DEFAULT, is_default=False, index=entry.index)
            )
            continue
        after_entries.append(entry)
    after = _snapshot(tuple(after_entries))
    result = evaluate_deletion_verification(
        before=before,
        after=after,
        deleted_filename=G360_CV,
        deleted_index=5,
    )
    assert result.should_stop is True
    assert result.reason == "default_changed_after_deletion"


def test_10_default_unobservable_before_or_after_stops() -> None:
    entries = _full_inventory()
    before_decision = evaluate_rotation_decision(
        entries=entries,
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=False,
        menu_observed=True,
        default_observable_before=False,
    )
    assert before_decision.action == "stop"
    assert before_decision.reason == "default_not_observable_before_deletion"
    before = _snapshot(entries)
    after_entries = []
    for entry in before.entries:
        if entry.index == 5:
            continue
        if entry.filename == PROTECTED_DEFAULT:
            after_entries.append(
                _entry(PROTECTED_DEFAULT, is_default=False, index=entry.index)
            )
            continue
        after_entries.append(entry)
    after = _snapshot(tuple(after_entries))
    result = evaluate_deletion_verification(
        before=before,
        after=after,
        deleted_filename=G360_CV,
        deleted_index=5,
    )
    assert result.should_stop is True
    assert result.reason == "default_unobservable_after_deletion"


def test_11_unknown_confirmation_dialog_stops() -> None:
    open_menu = (
        _row_menu(
            G360_CV,
            index=5,
            menu_open=True,
            actions=("Download", "Delete"),
        ),
    )
    blocked = plan_resume_delete_click(
        candidate_filename=G360_CV,
        candidate_index=5,
        rows=open_menu,
        confirmation_dialog_visible=True,
    )
    assert blocked.action == "stop"
    assert blocked.reason == "resume_delete_confirmation_unobserved"
    driver = FakeResumeDeleteDriver(
        (_row_menu(G360_CV, index=5),),
        confirmation_mode="unknown",
    )
    status = perform_one_resume_deletion(
        driver, candidate_filename=G360_CV, candidate_index=5
    )
    assert status == "resume_delete_confirmation_unobserved"
    assert driver.clicked == ["Delete"]
    assert driver.confirmation_clicked == []
    assert driver.cancel_clicked == []


def _observed_dialog(
    *,
    candidate: str,
    dialog_filename: str | None = None,
    dialog_count: int = 1,
    include_prompt: bool = True,
    delete_count: int = 1,
    extra_actions: tuple[str, ...] = (),
) -> object:
    shown = candidate if dialog_filename is None else dialog_filename
    lines = []
    if include_prompt:
        lines.append(SEEK_RESUME_DELETE_CONFIRMATION_PROMPT)
    if shown:
        lines.append(shown)
    actions = tuple([SEEK_RESUME_DELETE_ACTION] * delete_count) + (
        SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
        SEEK_RESUME_DELETE_CONFIRMATION_CLOSE,
    ) + extra_actions
    return build_delete_confirmation_observation(
        dialog_count=dialog_count,
        dialog_text="\n".join(lines) + "\nDelete\nCancel",
        candidate_filename=candidate,
        action_names=actions,
    )


def test_observed_confirmation_matching_filename_clicks_dialog_delete() -> None:
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="observed",
    )
    status = perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert status == "clicked_delete"
    assert driver.clicked == ["Delete"]
    assert driver.confirmation_clicked == ["Delete"]
    assert driver.cancel_clicked == []
    assert driver.close_clicked == []
    observation = _observed_dialog(candidate=FORWARD_DEPLOYED)
    plan = plan_resume_delete_confirmation(
        candidate_filename=FORWARD_DEPLOYED,
        observation=observation,
    )
    assert plan.action == "click_confirm_delete"
    assert observation.extra_action_names == ()
    assert observation.delete_action_count == 1


def test_live_word_joiner_delete_and_dismiss_clicks_confirm() -> None:
    observation = build_delete_confirmation_observation(
        dialog_count=1,
        dialog_text=(
            f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{FORWARD_DEPLOYED}\n"
            f"{LIVE_DELETE_ACCESSIBLE_NAME}\nCancel"
        ),
        candidate_filename=FORWARD_DEPLOYED,
        action_names=LIVE_CONFIRM_ACTIONS,
    )
    assert observation.delete_action_count == 1
    assert observation.cancel_action_count == 1
    assert observation.extra_action_names == ()
    assert observation.action_names_raw == LIVE_CONFIRM_ACTIONS
    assert observation.action_names_normalised == (
        SEEK_RESUME_DELETE_ACTION,
        SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
        SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
    )
    plan = plan_resume_delete_confirmation(
        candidate_filename=FORWARD_DEPLOYED,
        observation=observation,
    )
    assert plan.action == "click_confirm_delete"
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="live",
    )
    status = perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert status == "clicked_delete"
    assert driver.confirmation_clicked == ["Delete"]
    assert driver.dismiss_clicked == []
    assert driver.cancel_clicked == []
    assert driver.close_clicked == []


def test_word_joiner_and_whitespace_normalise_to_delete() -> None:
    assert normalise_confirmation_action_name("\u2060Delete") == "Delete"
    assert normalise_confirmation_action_name(" \u2060Delete\u2060 ") == "Delete"
    observation = build_delete_confirmation_observation(
        dialog_count=1,
        dialog_text=(
            f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{FORWARD_DEPLOYED}"
        ),
        candidate_filename=FORWARD_DEPLOYED,
        action_names=(
            " \u2060Delete\u2060 ",
            SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
            SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
        ),
    )
    assert observation.delete_action_count == 1
    assert plan_resume_delete_confirmation(
        candidate_filename=FORWARD_DEPLOYED,
        observation=observation,
    ).action == "click_confirm_delete"


def test_confirmation_dismiss_present_is_never_clicked() -> None:
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="live",
    )
    perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert SEEK_RESUME_DELETE_CONFIRMATION_DISMISS not in driver.clicked
    assert SEEK_RESUME_DELETE_CONFIRMATION_DISMISS not in driver.confirmation_clicked
    assert driver.dismiss_clicked == []


def test_two_normalised_delete_controls_stop() -> None:
    observation = build_delete_confirmation_observation(
        dialog_count=1,
        dialog_text=(
            f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{FORWARD_DEPLOYED}"
        ),
        candidate_filename=FORWARD_DEPLOYED,
        action_names=(
            LIVE_DELETE_ACCESSIBLE_NAME,
            SEEK_RESUME_DELETE_ACTION,
            SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
            SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
        ),
    )
    plan = plan_resume_delete_confirmation(
        candidate_filename=FORWARD_DEPLOYED,
        observation=observation,
    )
    assert observation.delete_action_count == 2
    assert plan.action == "stop"
    assert plan.reason == "resume_delete_confirmation_multiple_delete_actions"


def test_confirmation_close_present_is_never_clicked() -> None:
    driver = FakeResumeDeleteDriver((_row_menu(FORWARD_DEPLOYED, index=4),))
    perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert SEEK_RESUME_DELETE_CONFIRMATION_CLOSE not in driver.clicked
    assert SEEK_RESUME_DELETE_CONFIRMATION_CLOSE not in driver.confirmation_clicked
    assert driver.close_clicked == []
    observation = build_delete_confirmation_observation(
        dialog_count=1,
        dialog_text=(
            f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{FORWARD_DEPLOYED}\n"
            "Delete\nCancel"
        ),
        candidate_filename=FORWARD_DEPLOYED,
        action_names=_observed_confirm_actions(),
    )
    plan = plan_resume_delete_confirmation(
        candidate_filename=FORWARD_DEPLOYED,
        observation=observation,
    )
    assert plan.action == "click_confirm_delete"
    assert SEEK_RESUME_DELETE_CONFIRMATION_CLOSE not in observation.extra_action_names


def test_confirmation_filename_mismatch_stops() -> None:
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="mismatch",
    )
    status = perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert status == "resume_delete_confirmation_filename_mismatch"
    assert driver.confirmation_clicked == []
    assert driver.cancel_clicked == []


def test_confirmation_missing_filename_stops() -> None:
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="missing_filename",
    )
    status = perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert status == "resume_delete_confirmation_filename_missing"
    assert driver.confirmation_clicked == []
    assert driver.cancel_clicked == []


def test_confirmation_multiple_delete_actions_stop() -> None:
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="multiple_delete",
    )
    status = perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert status == "resume_delete_confirmation_multiple_delete_actions"
    assert driver.confirmation_clicked == []
    assert driver.cancel_clicked == []


def test_confirmation_multiple_dialogs_stop() -> None:
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="multiple_dialogs",
    )
    status = perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert status == "resume_delete_confirmation_multiple_dialogs"
    assert driver.confirmation_clicked == []
    assert driver.cancel_clicked == []
    assert driver.close_clicked == []


def test_confirmation_unknown_extra_action_stops() -> None:
    observation = _observed_dialog(
        candidate=FORWARD_DEPLOYED, extra_actions=("Continue",)
    )
    plan = plan_resume_delete_confirmation(
        candidate_filename=FORWARD_DEPLOYED,
        observation=observation,
    )
    assert plan.action == "stop"
    assert plan.reason == "resume_delete_confirmation_unobserved"
    assert "Continue" in observation.extra_action_names
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="extra_action",
    )
    status = perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert status == "resume_delete_confirmation_unobserved"
    assert driver.confirmation_clicked == []
    assert driver.cancel_clicked == []
    assert driver.close_clicked == []


def test_confirmation_diagnostic_dump_records_planner_branch(tmp_path: Path) -> None:
    path = tmp_path / "delete_confirmation_observation.json"
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="extra_action",
    )
    status = perform_one_resume_deletion(
        driver,
        candidate_filename=FORWARD_DEPLOYED,
        candidate_index=4,
        diagnostic_path=path,
    )
    assert status == "resume_delete_confirmation_unobserved"
    assert driver.confirmation_clicked == []
    payload = json.loads(path.read_text(encoding="utf-8"))
    stages = [snapshot["stage"] for snapshot in payload["snapshots"]]
    assert "pre_overflow" in stages
    assert "post_overflow" in stages
    assert "post_menu_delete" in stages
    post = next(
        snapshot
        for snapshot in payload["snapshots"]
        if snapshot["stage"] == "post_menu_delete"
    )
    assert post["planner_branch"] == "extra_actions"
    assert "Continue" in post["extra_action_names"]
    assert post["candidate_filename"] == FORWARD_DEPLOYED
    assert post["plan_reason"] == "resume_delete_confirmation_unobserved"


def test_confirmation_diagnostic_dump_does_not_change_click_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "delete_confirmation_observation.json"
    driver = FakeResumeDeleteDriver((_row_menu(FORWARD_DEPLOYED, index=4),))
    status = perform_one_resume_deletion(
        driver,
        candidate_filename=FORWARD_DEPLOYED,
        candidate_index=4,
        diagnostic_path=path,
    )
    assert status == "clicked_delete"
    assert driver.confirmation_clicked == ["Delete"]
    assert driver.cancel_clicked == []
    assert driver.close_clicked == []
    payload = json.loads(path.read_text(encoding="utf-8"))
    post = next(
        snapshot
        for snapshot in payload["snapshots"]
        if snapshot["stage"] == "post_menu_delete"
    )
    assert post["planner_branch"] == "click_observed_confirm_delete"
    assert payload["snapshots"][-1]["stage"] == "confirm_click"


def test_live_confirmation_diagnostic_exposes_raw_and_normalised(
    tmp_path: Path,
) -> None:
    path = tmp_path / "delete_confirmation_observation.json"
    driver = FakeResumeDeleteDriver(
        (_row_menu(FORWARD_DEPLOYED, index=4),),
        confirmation_mode="live",
    )
    status = perform_one_resume_deletion(
        driver,
        candidate_filename=FORWARD_DEPLOYED,
        candidate_index=4,
        diagnostic_path=path,
    )
    assert status == "clicked_delete"
    payload = json.loads(path.read_text(encoding="utf-8"))
    post = next(
        snapshot
        for snapshot in payload["snapshots"]
        if snapshot["stage"] == "post_menu_delete"
    )
    assert post["action_names_raw"] == list(LIVE_CONFIRM_ACTIONS)
    assert post["action_names_normalised"] == [
        SEEK_RESUME_DELETE_ACTION,
        SEEK_RESUME_DELETE_CONFIRMATION_CANCEL,
        SEEK_RESUME_DELETE_CONFIRMATION_DISMISS,
    ]
    assert post["extra_action_names"] == []
    assert post["planner_branch"] == "click_observed_confirm_delete"
    assert post["plan_action"] == "click_confirm_delete"


def test_confirmation_planner_branch_ids_match_stop_reasons() -> None:
    empty = empty_delete_confirmation_observation()
    assert confirmation_planner_branch(empty, FORWARD_DEPLOYED) == "dialog_count_0"
    extra = _observed_dialog(
        candidate=FORWARD_DEPLOYED, extra_actions=("Continue",)
    )
    assert confirmation_planner_branch(extra, FORWARD_DEPLOYED) == "extra_actions"
    observed = _observed_dialog(candidate=FORWARD_DEPLOYED)
    assert (
        confirmation_planner_branch(observed, FORWARD_DEPLOYED)
        == "click_observed_confirm_delete"
    )


def test_confirmation_never_clicks_cancel() -> None:
    driver = FakeResumeDeleteDriver((_row_menu(FORWARD_DEPLOYED, index=4),))
    perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert SEEK_RESUME_DELETE_CONFIRMATION_CANCEL not in driver.clicked
    assert SEEK_RESUME_DELETE_CONFIRMATION_CANCEL not in driver.confirmation_clicked
    assert driver.cancel_clicked == []
    assert driver.close_clicked == []
    assert driver.dismiss_clicked == []


def test_delete_identified_by_accessible_name_not_inner_text() -> None:
    assert confirmation_accessible_name(aria_label="Close", inner_text="") == "Close"
    assert (
        confirmation_accessible_name(aria_label="Delete", inner_text="🗑 Delete")
        == "Delete"
    )
    observation = build_delete_confirmation_observation(
        dialog_count=1,
        dialog_text=(
            f"{SEEK_RESUME_DELETE_CONFIRMATION_PROMPT}\n{FORWARD_DEPLOYED}"
        ),
        candidate_filename=FORWARD_DEPLOYED,
        action_names=(
            confirmation_accessible_name(aria_label="Delete", inner_text="🗑"),
            confirmation_accessible_name(aria_label="Cancel", inner_text="Cancel"),
            confirmation_accessible_name(aria_label="Close", inner_text=""),
        ),
    )
    plan = plan_resume_delete_confirmation(
        candidate_filename=FORWARD_DEPLOYED,
        observation=observation,
    )
    assert plan.action == "click_confirm_delete"
    assert observation.delete_action_count == 1


def test_successful_confirmation_still_requires_post_delete_verification() -> None:
    driver = FakeResumeDeleteDriver((_row_menu(FORWARD_DEPLOYED, index=4),))
    status = perform_one_resume_deletion(
        driver, candidate_filename=FORWARD_DEPLOYED, candidate_index=4
    )
    assert status == "clicked_delete"
    before = _snapshot(
        (
            _entry(PROTECTED_DEFAULT, is_default=True, index=0),
            _entry(NOVIGI_CV, is_selected=True, index=1),
            _entry(FORWARD_DEPLOYED, index=4),
        )
    )
    still_present = _snapshot(before.entries)
    unverified = evaluate_deletion_verification(
        before=before,
        after=still_present,
        deleted_filename=FORWARD_DEPLOYED,
        deleted_index=4,
    )
    assert unverified.should_stop is True
    after = _snapshot(
        (
            _entry(PROTECTED_DEFAULT, is_default=True, index=0),
            _entry(NOVIGI_CV, is_selected=True, index=1),
        )
    )
    verified = evaluate_deletion_verification(
        before=before,
        after=after,
        deleted_filename=FORWARD_DEPLOYED,
        deleted_index=4,
    )
    assert verified.should_stop is False
    assert verified.reason == "deletion_verified"
    assert verified.default_after == PROTECTED_DEFAULT


def test_post_delete_poll_waits_while_candidate_still_present() -> None:
    before = _snapshot(
        (
            _entry(PROTECTED_DEFAULT, is_default=True, index=0),
            _entry(NOVIGI_CV, is_selected=True, index=1),
            _entry(FORWARD_DEPLOYED, index=4),
        )
    )
    still = before
    gone = _snapshot(
        (
            _entry(PROTECTED_DEFAULT, is_default=True, index=0),
            _entry(NOVIGI_CV, is_selected=True, index=1),
        )
    )
    snapshots = iter((still, still, gone))
    waited = wait_until_deletion_verified(
        lambda: next(snapshots),
        before=before,
        deleted_filename=FORWARD_DEPLOYED,
        deleted_index=4,
        timeout_ms=5_000,
        poll_ms=400,
        wait=lambda _ms: None,
    )
    assert waited.action == "verified"
    assert waited.reason == "deletion_verified"
    assert waited.poll_count == 3


def test_post_delete_poll_timeout_when_candidate_never_leaves() -> None:
    before = _snapshot(
        (
            _entry(PROTECTED_DEFAULT, is_default=True, index=0),
            _entry(FORWARD_DEPLOYED, index=4),
        )
    )
    waited = wait_until_deletion_verified(
        lambda: before,
        before=before,
        deleted_filename=FORWARD_DEPLOYED,
        deleted_index=4,
        timeout_ms=800,
        poll_ms=400,
        wait=lambda _ms: None,
    )
    assert waited.action == "stop"
    assert waited.reason == "resume_delete_verification_timeout"
    assert waited.poll_count >= 1


def test_post_delete_poll_stops_if_wrong_row_disappears() -> None:
    before = _snapshot(_full_inventory())
    after = _snapshot(
        tuple(entry for entry in before.entries if entry.filename != NOVIGI_CV)
    )
    waited = wait_until_deletion_verified(
        lambda: after,
        before=before,
        deleted_filename=G360_CV,
        deleted_index=5,
        timeout_ms=5_000,
        poll_ms=400,
        wait=lambda _ms: None,
    )
    assert waited.action == "stop"
    assert waited.reason == "wrong_row_disappeared"


def test_post_delete_poll_stops_if_default_changes() -> None:
    before = _snapshot(_full_inventory())
    after_entries = []
    for entry in before.entries:
        if entry.filename == NOVIGI_CV:
            after_entries.append(
                _entry(NOVIGI_CV, is_default=True, is_selected=True, index=entry.index)
            )
            continue
        if entry.filename == PROTECTED_DEFAULT:
            after_entries.append(
                _entry(PROTECTED_DEFAULT, is_default=False, index=entry.index)
            )
            continue
        after_entries.append(entry)
    after = _snapshot(tuple(after_entries))
    waited = wait_until_deletion_verified(
        lambda: after,
        before=before,
        deleted_filename=G360_CV,
        deleted_index=5,
        timeout_ms=5_000,
        poll_ms=400,
        wait=lambda _ms: None,
    )
    assert waited.action == "stop"
    assert waited.reason == "default_changed_after_deletion"


def test_verified_confirmation_allows_exactly_one_cv_retry() -> None:
    decision = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=False,
        menu_observed=True,
        deletion_verified=True,
        retry_attempted=False,
        default_observable_before=True,
    )
    assert decision.action == "retry_upload_once"
    second = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=True,
        retry_attempted=True,
        retry_expected_cv_selected=False,
        default_observable_before=True,
    )
    assert second.action == "stop"
    assert second.reason == "retry_failed_no_second_deletion"


def test_default_change_after_confirmed_delete_still_stops() -> None:
    before = _snapshot(_full_inventory())
    after_entries = []
    for entry in before.entries:
        if entry.index == 5:
            continue
        if entry.filename == NOVIGI_CV:
            after_entries.append(
                _entry(NOVIGI_CV, is_default=True, is_selected=True, index=entry.index)
            )
            continue
        if entry.filename == PROTECTED_DEFAULT:
            after_entries.append(
                _entry(PROTECTED_DEFAULT, is_default=False, index=entry.index)
            )
            continue
        after_entries.append(entry)
    after = _snapshot(tuple(after_entries))
    result = evaluate_deletion_verification(
        before=before,
        after=after,
        deleted_filename=G360_CV,
        deleted_index=5,
    )
    assert result.should_stop is True
    assert result.reason == "default_changed_after_deletion"


def test_12_verified_deletion_exactly_one_retry() -> None:
    decision = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="resume_capacity_blocked",
        rotation_already_attempted=False,
        menu_observed=True,
        deletion_verified=True,
        retry_attempted=False,
        default_observable_before=True,
    )
    assert decision.action == "retry_upload_once"
    already = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=True,
        menu_observed=True,
        deletion_verified=True,
        retry_attempted=False,
    )
    assert already.action == "stop"
    assert already.reason == "rotation_already_attempted"


def test_13_retry_succeeds_expected_cv_selected() -> None:
    decision = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=False,
        menu_observed=True,
        deletion_verified=True,
        retry_attempted=True,
        retry_expected_cv_selected=True,
        default_observable_before=True,
    )
    assert decision.action == "continue"
    assert decision.reason == "retry_expected_cv_selected"


def test_14_retry_fails_no_second_deletion() -> None:
    decision = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=False,
        menu_observed=True,
        deletion_verified=True,
        retry_attempted=True,
        retry_expected_cv_selected=False,
        default_observable_before=True,
    )
    assert decision.action == "stop"
    assert decision.reason == "retry_failed_no_second_deletion"
    follow_up = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=True,
        menu_observed=True,
        deletion_verified=True,
        retry_attempted=True,
        retry_expected_cv_selected=False,
    )
    assert follow_up.action == "stop"
    assert follow_up.reason == "retry_failed_no_second_deletion"


def test_15_previous_opportunity_cv_selected_stops() -> None:
    snapshot = _snapshot(
        (
            _entry(PROTECTED_DEFAULT, is_default=True, index=0),
            _entry(NOVIGI_CV, is_selected=True, index=1),
        )
    )
    outcome = evaluate_cv_upload_wait_tick(
        snapshot=snapshot,
        expected_filename=EXPECTED_G360,
        spinner_active=True,
        elapsed_ms=15_000,
        timeout_ms=15_000,
    )
    assert outcome.action == "stop"
    assert outcome.observed_selected == NOVIGI_CV
    assert outcome.selected is False


def test_16_expected_cv_already_selected_does_not_rotate() -> None:
    idle = evaluate_rotation_trigger(
        upload_failure_reason="expected_cv_selected",
        rotation_already_attempted=False,
    )
    assert idle.should_attempt is False
    assert idle.reason == "no_upload_failure_trigger"
    selected = _snapshot(
        (
            _entry(PROTECTED_DEFAULT, is_default=True, index=0),
            _entry(EXPECTED_G360, is_selected=True, index=1),
        )
    )
    gate = evaluate_expected_cv_selection(selected, EXPECTED_G360)
    assert gate.selected is True
    assert gate.should_stop is False


def test_17_automation_never_clicks_submit() -> None:
    handoff = build_final_review_handoff(final_submit_control_visible=True)
    assert handoff.submit_clicked_by_automation is False
    page = PageSignals(looks_like_review_or_confirmation=True)
    assert classify_control("Submit application", page=page) is ControlClass.FINAL_SUBMIT
    decision = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=False,
        menu_observed=True,
        deletion_verified=True,
        retry_attempted=False,
    )
    assert decision.action == "retry_upload_once"
    assert decision.action != "submit"


def test_only_default_inventory_has_no_candidate() -> None:
    entries = (_entry(PROTECTED_DEFAULT, is_default=True, is_selected=True, index=0),)
    candidate = select_cleanup_candidate(entries)
    assert candidate.selected is False
    assert candidate.reason == "no_non_default_resume"
    decision = evaluate_rotation_decision(
        entries=entries,
        upload_failure_reason="expected_cv_not_present",
        rotation_already_attempted=False,
        menu_observed=True,
    )
    assert decision.action == "stop"
    assert decision.reason == "no_non_default_resume"


def test_does_not_open_default_row_menu() -> None:
    rows = (_row_menu(PROTECTED_DEFAULT, index=0, is_default=True),)
    plan = plan_resume_delete_click(
        candidate_filename=PROTECTED_DEFAULT,
        candidate_index=0,
        rows=rows,
    )
    assert plan.action == "stop"
    assert plan.reason == "default_row_protected"


def test_exact_delete_not_download() -> None:
    rows = (
        _row_menu(
            G360_CV,
            index=5,
            menu_open=True,
            actions=("Download", "Delete"),
        ),
    )
    plan = plan_resume_delete_click(
        candidate_filename=G360_CV, candidate_index=5, rows=rows
    )
    assert plan.action == "click_delete"
    assert plan.menu_action == "Delete"


def test_other_row_menu_cannot_be_used() -> None:
    rows = (
        _row_menu(G360_CV, index=5),
        _row_menu(
            NOVIGI_CV,
            index=4,
            menu_open=True,
            actions=("Download", "Delete"),
        ),
    )
    plan = plan_resume_delete_click(
        candidate_filename=G360_CV, candidate_index=5, rows=rows
    )
    assert plan.action == "stop"
    assert plan.reason == "other_resume_menu_open"


def test_delete_menu_is_observed_as_exact_delete() -> None:
    assert SEEK_RESUME_DELETE_MENU_LABELS == ("Delete",)
    assert seek_delete_menu_is_observed() is True
    assert refuse_unobserved_resume_deletion(OPP_OLD, candidate_index=3) == "menu_observed"


def test_rotation_trigger_is_only_concrete_upload_failure() -> None:
    for reason in (
        "expected_cv_not_present",
        "resume_upload_spinner_timeout",
        "resume_upload_still_processing",
        "resume_capacity_blocked",
    ):
        trigger = evaluate_rotation_trigger(
            upload_failure_reason=reason,
            rotation_already_attempted=False,
        )
        assert trigger.should_attempt is True
    for reason in (
        "no_filechooser_event",
        "chooser_set_files_threw",
        "resume_upload_button_not_associated",
        "no_saved_resume_selected_for_upload",
    ):
        trigger = evaluate_rotation_trigger(
            upload_failure_reason=reason,
            rotation_already_attempted=False,
        )
        assert trigger.should_attempt is False
        assert trigger.reason == "no_upload_failure_trigger"


def test_capacity_does_not_rotate_when_expected_cv_already_present() -> None:
    trigger = evaluate_rotation_trigger(
        upload_failure_reason="resume_capacity_blocked",
        rotation_already_attempted=False,
        expected_cv_present=True,
    )
    assert trigger.should_attempt is False
    assert trigger.reason == "expected_cv_already_present_no_rotation"
    decision = evaluate_rotation_decision(
        entries=_full_inventory(),
        upload_failure_reason="resume_capacity_blocked",
        rotation_already_attempted=False,
        menu_observed=True,
        expected_cv_present=True,
    )
    assert decision.action == "stop"
    assert decision.reason == "expected_cv_already_present_no_rotation"
