"""AAS-0.1 Default-checkbox diagnostic dump — serialization only, no SEEK."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.default_checkbox_observation import (  # noqa: E402
    CHOSEN_VIA_LOCATOR_FIRST,
    DEFAULT_CHECKBOX_OBSERVATION_FILENAME,
    LOCATOR_EXACT_NAME,
    LOCATOR_REGEX_FALLBACK,
    STAGE_AFTER_400MS_WAIT,
    STAGE_AFTER_EXPECTED_CV_APPEARS,
    STAGE_AFTER_UNCHECK_RETURN_OR_THROW,
    STAGE_BEFORE_DOCUMENT_UPLOAD,
    STAGE_BEFORE_UNCHECK,
    STAGE_CHECKBOX_GUARD_DECISION,
    STAGE_CHECKBOX_SETTLE_POLL,
    STAGE_STRUCTURAL_DEFAULT_REOBSERVED,
    append_default_checkbox_diagnostic,
    build_default_checkbox_observation_snapshot,
    diagnostic_has_stage,
)
from aas0.metrics import SpikeMetrics  # noqa: E402
from aas0.resume_lifecycle import evaluate_default_checkbox_guard  # noqa: E402
from aas0.session_handoff import build_final_review_handoff  # noqa: E402
from aas0.submit_guard import ControlClass, PageSignals, classify_control  # noqa: E402
from aas0.document_gates import (  # noqa: E402
    evaluate_review_document_gate,
    parse_review_document_filenames,
)
from aas0.seek_documents import (  # noqa: E402
    capture_default_checkbox_observation,
    dump_expected_cv_appeared_once,
    inspect_default_checkbox_matches,
    resolve_default_resume_checkbox,
    uncheck_default_checkbox_if_checked,
)

CSK_CV = "David Cropper - CSK Nexus Pty Ltd - Senior AI Engineer - AWS Bedrock - CV.pdf"
PROTECTED_DEFAULT = "David Cropper - AI Engineer CV.pdf"
G360_CV = "David Cropper - Global 360 - AI Engineer - Applied - CV.pdf"
NOVIGI_CV = "David Cropper - Novigi Pty Ltd - Senior AI Engineer - CV.pdf"
HATCH_CV = "David Cropper - Hatch - AI Trainer - CV.pdf"
THIRD_CV = "David Cropper - Other Employer - AI Engineer - CV.pdf"
CHECKBOX_NAME = "Make this my default résumé"
UNCHECK_STATE_ERROR = "Clicking the checkbox did not change its state"


class FakeCheckbox:
    def __init__(
        self,
        *,
        is_checked: bool = False,
        visible: bool = True,
        enabled: bool = True,
        tag_name: str = "input",
        input_type: str = "checkbox",
        role: str = "checkbox",
        accessible_name: str = CHECKBOX_NAME,
        aria_label: str = CHECKBOX_NAME,
        aria_checked: str | None = None,
        checked_attribute: str | None = None,
        checked_property: bool | None = None,
        wrapper_tag: str = "label",
        wrapper_class: str = "braid-checkbox",
        wrapper_role: str = "",
        uncheck_error: Exception | None = None,
        checked_after_wait: bool | None = None,
    ) -> None:
        self._checked = is_checked
        self._visible = visible
        self._enabled = enabled
        self.tag_name = tag_name
        self.input_type = input_type
        self.role = role
        self.accessible_name = accessible_name
        self.aria_label = aria_label
        self.aria_checked = aria_checked
        self.checked_attribute = checked_attribute
        self.checked_property = (
            is_checked if checked_property is None else checked_property
        )
        self.wrapper_tag = wrapper_tag
        self.wrapper_class = wrapper_class
        self.wrapper_role = wrapper_role
        self._uncheck_error = uncheck_error
        self._checked_after_wait = checked_after_wait
        self.uncheck_calls = 0

    def is_checked(self) -> bool:
        return bool(self._checked)

    def is_visible(self) -> bool:
        return bool(self._visible)

    def is_enabled(self) -> bool:
        return bool(self._enabled)

    def get_attribute(self, name: str):
        mapping = {
            "aria-checked": self.aria_checked,
            "checked": self.checked_attribute,
            "aria-label": self.aria_label,
            "role": self.role,
            "type": self.input_type,
        }
        return mapping.get(name)

    def evaluate(self, script: str):
        if "aria-labelledby" in script:
            return self.accessible_name
        return {
            "tag_name": self.tag_name,
            "input_type": self.input_type,
            "role": self.role,
            "aria_label": self.aria_label,
            "aria_checked": self.aria_checked,
            "checked_attribute": self.checked_attribute,
            "checked_property": self.checked_property,
            "wrapper_tag": self.wrapper_tag,
            "wrapper_class": self.wrapper_class,
            "wrapper_role": self.wrapper_role,
            "wrapper_data_automation": "",
        }

    def uncheck(self, timeout: int = 0) -> None:  # noqa: ARG002
        self.uncheck_calls += 1
        if self._uncheck_error is not None:
            self._enabled = False
            raise self._uncheck_error
        self._checked = False

    def click(self) -> None:
        raise AssertionError("Default restore click must not occur")


class FakeLocator:
    def __init__(self, nodes: list) -> None:
        self._nodes = list(nodes)
        self.first = self._nodes[0] if self._nodes else self

    def count(self) -> int:
        return len(self._nodes)

    def nth(self, index: int):
        return self._nodes[index]

    def is_checked(self) -> bool:
        return bool(self._nodes and self._nodes[0].is_checked())

    def uncheck(self, timeout: int = 0) -> None:
        if not self._nodes:
            raise RuntimeError("no checkbox")
        self._nodes[0].uncheck(timeout=timeout)

    def is_visible(self) -> bool:
        return bool(self._nodes and self._nodes[0].is_visible())

    def is_enabled(self) -> bool:
        return bool(self._nodes and self._nodes[0].is_enabled())


class FakeRadio:
    def __init__(self, text: str, *, selected: bool) -> None:
        self._text = text
        self._selected = selected
        self.clicks = 0

    def is_visible(self) -> bool:
        return True

    def is_checked(self) -> bool:
        return self._selected

    def is_enabled(self) -> bool:
        return True

    def evaluate(self, script: str):  # noqa: ARG002
        return [self._text]

    def click(self) -> None:
        self.clicks += 1
        raise AssertionError("Default restore click must not occur")


class FakeCheckboxPage:
    def __init__(
        self,
        *,
        exact_boxes: list[FakeCheckbox] | None = None,
        regex_boxes: list[FakeCheckbox] | None = None,
        radios: list[FakeRadio] | None = None,
        settle_after_waits: list[dict] | None = None,
    ) -> None:
        self.exact_boxes = list(exact_boxes or [])
        self.regex_boxes = list(regex_boxes if regex_boxes is not None else self.exact_boxes)
        self.radios = list(radios or [])
        self.wait_ms: list[int] = []
        self.settle_after_waits = list(settle_after_waits or [])
        self._settle_i = 0
        self.restore_clicks = 0

    def get_by_role(self, role: str, name=None):
        if role == "checkbox":
            if isinstance(name, str):
                return FakeLocator(self.exact_boxes)
            return FakeLocator(self.regex_boxes)
        if role == "radio":
            return FakeLocator(self.radios)
        return FakeLocator([])

    def wait_for_timeout(self, ms: int) -> None:
        self.wait_ms.append(ms)
        if self.settle_after_waits:
            if self._settle_i < len(self.settle_after_waits):
                self._apply_settle_state(self.settle_after_waits[self._settle_i])
                self._settle_i += 1
            return
        for box in [*self.exact_boxes, *self.regex_boxes]:
            if box._checked_after_wait is not None:
                box._checked = box._checked_after_wait

    def _apply_settle_state(self, state: dict) -> None:
        box = self.exact_boxes[0] if self.exact_boxes else None
        if box is not None:
            if "checked" in state:
                box._checked = bool(state["checked"])
            if "enabled" in state:
                box._enabled = bool(state["enabled"])
        if "radios" in state:
            self.radios = list(state["radios"])


def _g360_selected_default_radios() -> list[FakeRadio]:
    return [
        FakeRadio(f"Default\n{G360_CV}\nAdded less than a minute ago", selected=True),
        FakeRadio(NOVIGI_CV, selected=False),
        FakeRadio(PROTECTED_DEFAULT, selected=False),
    ]


def _csk_selected_as_committed_default_radios() -> list[FakeRadio]:
    return [
        FakeRadio(f"Default\n{CSK_CV}", selected=True),
        FakeRadio(HATCH_CV, selected=False),
        FakeRadio(PROTECTED_DEFAULT, selected=False),
    ]


def _hatch_selected_generic_default_radios() -> list[FakeRadio]:
    return [
        FakeRadio(HATCH_CV, selected=True),
        FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False),
    ]


def _before_upload_radios() -> list[FakeRadio]:
    return [
        FakeRadio(NOVIGI_CV, selected=True),
        FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False),
    ]


def _hatch_selected_as_default_radios() -> list[FakeRadio]:
    return [
        FakeRadio(f"Default\n{HATCH_CV}\nAdded less than a minute ago", selected=True),
        FakeRadio(f"{PROTECTED_DEFAULT}", selected=False),
        FakeRadio(NOVIGI_CV, selected=False),
    ]


def _hatch_selected_default_restored_radios() -> list[FakeRadio]:
    return [
        FakeRadio(f"{HATCH_CV}\nAdded less than a minute ago", selected=True),
        FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False),
        FakeRadio(NOVIGI_CV, selected=False),
    ]


def _third_default_radios() -> list[FakeRadio]:
    return [
        FakeRadio(f"Default\n{THIRD_CV}", selected=False),
        FakeRadio(f"{HATCH_CV}\nAdded less than a minute ago", selected=True),
        FakeRadio(PROTECTED_DEFAULT, selected=False),
    ]


def _no_default_hatch_selected_radios() -> list[FakeRadio]:
    return [
        FakeRadio(f"{HATCH_CV}\nAdded less than a minute ago", selected=True),
        FakeRadio(PROTECTED_DEFAULT, selected=False),
        FakeRadio(NOVIGI_CV, selected=False),
    ]


def _assert_no_restore(page: FakeCheckboxPage) -> None:
    assert page.restore_clicks == 0
    for radio in page.radios:
        assert radio.clicks == 0


def test_multiple_checkbox_matches_are_serialized() -> None:
    snapshot = build_default_checkbox_observation_snapshot(
        stage=STAGE_BEFORE_UNCHECK,
        locator_source=LOCATOR_EXACT_NAME,
        matches=(
            {
                "index": 0,
                "tag_name": "input",
                "is_checked": True,
                "visible": False,
                "checked_property": True,
                "aria_checked": None,
            },
            {
                "index": 1,
                "tag_name": "div",
                "role": "checkbox",
                "is_checked": False,
                "visible": True,
                "checked_property": None,
                "aria_checked": "false",
            },
        ),
        chosen_index=0,
        chosen_via=CHOSEN_VIA_LOCATOR_FIRST,
        structural_default_filename=G360_CV,
        selected_filename=G360_CV,
    )
    assert snapshot["match_count"] == 2
    assert snapshot["chosen_index"] == 0
    assert snapshot["chosen_via"] == CHOSEN_VIA_LOCATOR_FIRST
    assert snapshot["matches"][0]["tag_name"] == "input"
    assert snapshot["matches"][1]["visible"] is True
    assert snapshot["matches"][0]["index"] == 0
    assert snapshot["matches"][1]["index"] == 1


def test_native_checked_property_vs_aria_checked_are_separate_fields() -> None:
    snapshot = build_default_checkbox_observation_snapshot(
        stage=STAGE_AFTER_400MS_WAIT,
        locator_source=LOCATOR_EXACT_NAME,
        matches=(
            {
                "is_checked": True,
                "checked_property": True,
                "checked_attribute": None,
                "aria_checked": "false",
            },
        ),
        chosen_index=0,
        chosen_via=CHOSEN_VIA_LOCATOR_FIRST,
    )
    match = snapshot["matches"][0]
    assert match["checked_property"] is True
    assert match["aria_checked"] == "false"
    assert match["checked_attribute"] is None
    assert match["is_checked"] is True


def test_exact_vs_regex_locator_source() -> None:
    exact_page = FakeCheckboxPage(exact_boxes=[FakeCheckbox(is_checked=True)])
    locator, source = resolve_default_resume_checkbox(exact_page)
    assert source == LOCATOR_EXACT_NAME
    assert locator.count() == 1

    regex_page = FakeCheckboxPage(
        exact_boxes=[],
        regex_boxes=[FakeCheckbox(is_checked=True)],
    )
    locator, source = resolve_default_resume_checkbox(regex_page)
    assert source == LOCATOR_REGEX_FALLBACK
    assert locator.count() == 1
    assert isinstance(re.compile(r"make this my default r", re.I), re.Pattern)


def test_inspect_does_not_assume_first_is_the_visible_control() -> None:
    hidden = FakeCheckbox(is_checked=True, visible=False, tag_name="input")
    visible = FakeCheckbox(
        is_checked=False,
        visible=True,
        tag_name="div",
        role="checkbox",
        aria_checked="false",
        checked_property=None,
    )
    matches = inspect_default_checkbox_matches(FakeLocator([hidden, visible]))
    assert len(matches) == 2
    assert matches[0]["visible"] is False
    assert matches[0]["is_checked"] is True
    assert matches[1]["visible"] is True
    assert matches[1]["is_checked"] is False
    assert matches[1]["aria_checked"] == "false"


def test_uncheck_success_dump_does_not_change_guard(tmp_path: Path) -> None:
    path = tmp_path / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    box = FakeCheckbox(is_checked=True, checked_after_wait=False)
    page = FakeCheckboxPage(exact_boxes=[box], radios=_g360_selected_default_radios())
    without = uncheck_default_checkbox_if_checked(page, SpikeMetrics(opportunity_id="opp_01KZQK08P757DCAE1RM5GPPKC6"))
    box_with = FakeCheckbox(is_checked=True, checked_after_wait=False)
    page_with = FakeCheckboxPage(
        exact_boxes=[box_with], radios=_g360_selected_default_radios()
    )
    with_dump = uncheck_default_checkbox_if_checked(
        page_with,
        SpikeMetrics(opportunity_id="opp_01KZQK08P757DCAE1RM5GPPKC6"),
        diagnostic_path=path,
        expected_cv_filename=G360_CV,
    )
    expected = evaluate_default_checkbox_guard(
        present=True,
        was_checked=True,
        still_checked=False,
        uncheck_attempted=True,
    )
    assert without.should_stop is False
    assert with_dump.should_stop is False
    assert with_dump.reason == expected.reason == "checkbox_unchecked"
    assert with_dump.uncheck_succeeded is True
    assert with_dump.uncheck_returned is True
    assert with_dump.uncheck_threw is False
    payload = json.loads(path.read_text(encoding="utf-8"))
    stages = [item["stage"] for item in payload["snapshots"]]
    assert STAGE_BEFORE_UNCHECK in stages
    assert STAGE_AFTER_UNCHECK_RETURN_OR_THROW in stages
    assert STAGE_CHECKBOX_SETTLE_POLL in stages
    assert STAGE_AFTER_400MS_WAIT not in stages
    assert STAGE_CHECKBOX_GUARD_DECISION in stages
    settle = next(
        item
        for item in payload["snapshots"]
        if item["stage"] == STAGE_CHECKBOX_SETTLE_POLL
    )
    assert settle["uncheck_returned"] is True
    assert settle["uncheck_threw"] is False
    assert page_with.wait_ms == []
    _assert_no_restore(page_with)


def test_uncheck_exception_is_recorded_then_settles_or_times_out(tmp_path: Path) -> None:
    path = tmp_path / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    box = FakeCheckbox(
        is_checked=True,
        uncheck_error=TimeoutError("checkbox not becoming unchecked"),
    )
    page = FakeCheckboxPage(exact_boxes=[box], radios=_g360_selected_default_radios())
    outcome = uncheck_default_checkbox_if_checked(
        page,
        SpikeMetrics(opportunity_id="opp_01KZQK08P757DCAE1RM5GPPKC6"),
        diagnostic_path=path,
        expected_cv_filename=G360_CV,
        timeout_ms=0,
        poll_ms=400,
    )
    assert outcome.should_stop is True
    assert outcome.reason == "default_checkbox_settle_timeout"
    assert outcome.uncheck_threw is True
    assert outcome.uncheck_returned is False
    assert page.wait_ms == []
    payload = json.loads(path.read_text(encoding="utf-8"))
    after = next(
        item
        for item in payload["snapshots"]
        if item["stage"] == STAGE_AFTER_UNCHECK_RETURN_OR_THROW
    )
    assert after["uncheck_attempted"] is True
    assert after["uncheck_returned"] is False
    assert after["uncheck_threw"] is True
    assert after["uncheck_exception_type"] == "TimeoutError"
    assert "not becoming unchecked" in after["uncheck_exception_message"]
    stages = [item["stage"] for item in payload["snapshots"]]
    assert STAGE_AFTER_400MS_WAIT not in stages
    assert STAGE_CHECKBOX_SETTLE_POLL in stages


def test_structural_default_and_selected_are_separate_fields() -> None:
    before = build_default_checkbox_observation_snapshot(
        stage=STAGE_BEFORE_DOCUMENT_UPLOAD,
        locator_source=LOCATOR_EXACT_NAME,
        structural_default_filename=PROTECTED_DEFAULT,
        selected_filename=NOVIGI_CV,
        expected_cv_filename=G360_CV,
        expected_cv_present=False,
    )
    after = build_default_checkbox_observation_snapshot(
        stage=STAGE_STRUCTURAL_DEFAULT_REOBSERVED,
        locator_source=LOCATOR_EXACT_NAME,
        structural_default_filename=G360_CV,
        selected_filename=G360_CV,
        expected_cv_filename=G360_CV,
        expected_cv_present=True,
    )
    assert before["structural_default_filename"] == PROTECTED_DEFAULT
    assert before["selected_filename"] == NOVIGI_CV
    assert before["structural_default_filename"] != before["selected_filename"]
    assert after["structural_default_filename"] == G360_CV
    assert after["selected_filename"] == G360_CV
    assert "Make this my default" not in (
        after["structural_default_filename"] or ""
    )


def test_live_capture_records_structural_default_from_badge_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    page = FakeCheckboxPage(
        exact_boxes=[FakeCheckbox(is_checked=False)],
        radios=_before_upload_radios(),
    )
    capture_default_checkbox_observation(
        page,
        path=path,
        stage=STAGE_BEFORE_DOCUMENT_UPLOAD,
        expected_cv_filename=G360_CV,
    )
    page.radios = _g360_selected_default_radios()
    capture_default_checkbox_observation(
        page,
        path=path,
        stage=STAGE_STRUCTURAL_DEFAULT_REOBSERVED,
        expected_cv_filename=G360_CV,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    before, after = payload["snapshots"]
    assert before["structural_default_filename"] == PROTECTED_DEFAULT
    assert before["selected_filename"] == NOVIGI_CV
    assert after["structural_default_filename"] == G360_CV
    assert after["selected_filename"] == G360_CV
    assert after["expected_cv_present"] is True


def test_diagnostic_written_before_stop(tmp_path: Path) -> None:
    path = tmp_path / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    box = FakeCheckbox(
        is_checked=True,
        uncheck_error=TimeoutError(UNCHECK_STATE_ERROR),
        checked_after_wait=True,
    )
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_g360_selected_default_radios(),
    )
    outcome = uncheck_default_checkbox_if_checked(
        page,
        SpikeMetrics(opportunity_id="opp_01KZQK08P757DCAE1RM5GPPKC6"),
        diagnostic_path=path,
        expected_cv_filename=G360_CV,
        timeout_ms=0,
        poll_ms=400,
    )
    assert outcome.should_stop is True
    assert outcome.reason == "default_checkbox_settle_timeout"
    assert path.exists()
    capture_default_checkbox_observation(
        page,
        path=path,
        stage=STAGE_STRUCTURAL_DEFAULT_REOBSERVED,
        expected_cv_filename=G360_CV,
        was_checked=outcome.was_checked,
        uncheck_attempted=outcome.uncheck_attempted,
        guard=outcome,
    )
    assert diagnostic_has_stage(path, STAGE_BEFORE_UNCHECK)
    assert diagnostic_has_stage(path, STAGE_CHECKBOX_GUARD_DECISION)
    assert diagnostic_has_stage(path, STAGE_STRUCTURAL_DEFAULT_REOBSERVED)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["snapshots"][-1]["stage"] == STAGE_STRUCTURAL_DEFAULT_REOBSERVED
    assert payload["snapshots"][-1]["guard_should_stop"] is True


def test_expected_cv_appeared_dump_does_not_wait(tmp_path: Path) -> None:
    path = tmp_path / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    page = FakeCheckboxPage(
        exact_boxes=[FakeCheckbox(is_checked=True)],
        radios=_g360_selected_default_radios(),
    )
    dumped = [False]
    dump_expected_cv_appeared_once(
        page,
        path=path,
        expected_cv_filename=G360_CV,
        dumped_flag=dumped,
    )
    dump_expected_cv_appeared_once(
        page,
        path=path,
        expected_cv_filename=G360_CV,
        dumped_flag=dumped,
    )
    assert dumped == [True]
    assert page.wait_ms == []
    payload = json.loads(path.read_text(encoding="utf-8"))
    stages = [item["stage"] for item in payload["snapshots"]]
    assert stages.count(STAGE_AFTER_EXPECTED_CV_APPEARS) == 1


def test_append_keeps_stage_order(tmp_path: Path) -> None:
    path = tmp_path / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    for stage in (
        STAGE_BEFORE_DOCUMENT_UPLOAD,
        STAGE_AFTER_EXPECTED_CV_APPEARS,
        STAGE_BEFORE_UNCHECK,
    ):
        append_default_checkbox_diagnostic(
            path,
            build_default_checkbox_observation_snapshot(
                stage=stage,
                locator_source=LOCATOR_EXACT_NAME,
                structural_default_filename=PROTECTED_DEFAULT,
                selected_filename=NOVIGI_CV,
            ),
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert [item["stage"] for item in payload["snapshots"]] == [
        STAGE_BEFORE_DOCUMENT_UPLOAD,
        STAGE_AFTER_EXPECTED_CV_APPEARS,
        STAGE_BEFORE_UNCHECK,
    ]


def _hatch_uncheck(page: FakeCheckboxPage, path: Path | None = None, **extra):
    return uncheck_default_checkbox_if_checked(
        page,
        SpikeMetrics(opportunity_id="opp_01M0CTP2ZJ754YG5G7YA7X3ZMA"),
        diagnostic_path=path,
        expected_cv_filename=HATCH_CV,
        baseline_default_filename=PROTECTED_DEFAULT,
        baseline_default_observable=True,
        **extra,
    )


def test_hatch_live_uncheck_throw_then_async_restore_is_success(tmp_path: Path) -> None:
    """Exact proven Hatch sequence: uncheck throws, then Default restores asynchronously."""
    path = tmp_path / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    box = FakeCheckbox(
        is_checked=True,
        enabled=True,
        uncheck_error=TimeoutError(UNCHECK_STATE_ERROR),
    )
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_hatch_selected_as_default_radios(),
        settle_after_waits=[
            {
                "checked": True,
                "enabled": False,
                "radios": _hatch_selected_as_default_radios(),
            },
            {
                "checked": False,
                "enabled": True,
                "radios": _hatch_selected_default_restored_radios(),
            },
        ],
    )
    metrics = SpikeMetrics(opportunity_id="opp_01M0CTP2ZJ754YG5G7YA7X3ZMA")
    outcome = uncheck_default_checkbox_if_checked(
        page,
        metrics,
        diagnostic_path=path,
        expected_cv_filename=HATCH_CV,
        baseline_default_filename=PROTECTED_DEFAULT,
        baseline_default_observable=True,
    )
    assert outcome.should_stop is False
    assert outcome.uncheck_succeeded is True
    assert outcome.reason == "checkbox_unchecked"
    assert outcome.uncheck_threw is True
    assert outcome.uncheck_returned is False
    assert outcome.uncheck_exception_message == UNCHECK_STATE_ERROR
    assert outcome.still_checked is False
    assert outcome.baseline_default_filename == PROTECTED_DEFAULT
    assert outcome.settled_default_filename == PROTECTED_DEFAULT
    assert outcome.settle_poll_count == 3
    assert page.wait_ms == [400, 400]
    assert box.uncheck_calls == 1
    assert metrics.failures == []
    assert page.radios[0]._selected is True
    assert HATCH_CV in page.radios[0]._text
    assert "Default" not in page.radios[0]._text
    _assert_no_restore(page)
    payload = json.loads(path.read_text(encoding="utf-8"))
    polls = [
        item
        for item in payload["snapshots"]
        if item["stage"] == STAGE_CHECKBOX_SETTLE_POLL
    ]
    assert len(polls) == 3
    assert polls[0]["checkbox_enabled"] is False
    assert polls[0]["structural_default_filename"] == HATCH_CV
    assert polls[0]["selected_filename"] == HATCH_CV
    assert polls[1]["checkbox_enabled"] is False
    assert polls[1]["structural_default_filename"] == HATCH_CV
    assert polls[2]["checkbox_enabled"] is True
    assert polls[2]["structural_default_filename"] == PROTECTED_DEFAULT
    assert polls[2]["selected_filename"] == HATCH_CV
    guard = next(
        item
        for item in payload["snapshots"]
        if item["stage"] == STAGE_CHECKBOX_GUARD_DECISION
    )
    assert guard["guard_should_stop"] is False
    assert guard["guard_uncheck_succeeded"] is True
    assert metrics.default_checkbox_uncheck_threw is True
    assert metrics.default_checkbox_baseline == PROTECTED_DEFAULT
    assert metrics.default_checkbox_settled_default == PROTECTED_DEFAULT
    assert metrics.default_checkbox_settle_poll_count == 3


def test_uncheck_returns_then_state_settles_success() -> None:
    box = FakeCheckbox(is_checked=True)
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_hatch_selected_as_default_radios(),
        settle_after_waits=[
            {
                "checked": False,
                "enabled": True,
                "radios": _hatch_selected_default_restored_radios(),
            }
        ],
    )
    outcome = _hatch_uncheck(page)
    assert outcome.should_stop is False
    assert outcome.uncheck_succeeded is True
    assert outcome.uncheck_returned is True
    assert outcome.uncheck_threw is False
    assert outcome.reason == "checkbox_unchecked"
    assert outcome.settled_default_filename == PROTECTED_DEFAULT
    assert page.wait_ms == [400]
    assert box.uncheck_calls == 1
    _assert_no_restore(page)


def test_uncheck_throws_then_state_settles_success() -> None:
    box = FakeCheckbox(
        is_checked=True,
        uncheck_error=TimeoutError(UNCHECK_STATE_ERROR),
    )
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_hatch_selected_as_default_radios(),
        settle_after_waits=[
            {
                "checked": False,
                "enabled": True,
                "radios": _hatch_selected_default_restored_radios(),
            }
        ],
    )
    outcome = _hatch_uncheck(page)
    assert outcome.should_stop is False
    assert outcome.uncheck_threw is True
    assert outcome.uncheck_returned is False
    assert outcome.reason == "checkbox_unchecked"
    assert box.uncheck_calls == 1
    _assert_no_restore(page)


def test_checkbox_unchecked_but_default_stays_application_cv_times_out() -> None:
    box = FakeCheckbox(is_checked=True)
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_hatch_selected_as_default_radios(),
    )
    outcome = _hatch_uncheck(page, timeout_ms=0)
    assert outcome.should_stop is True
    assert outcome.still_checked is False
    assert outcome.settled_default_filename == HATCH_CV
    assert outcome.reason == "default_checkbox_settle_timeout"
    assert page.wait_ms == []
    _assert_no_restore(page)


def test_default_restored_but_checkbox_remains_checked_times_out() -> None:
    box = FakeCheckbox(
        is_checked=True,
        uncheck_error=TimeoutError(UNCHECK_STATE_ERROR),
    )
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_hatch_selected_default_restored_radios(),
    )
    outcome = _hatch_uncheck(page, timeout_ms=0)
    assert outcome.should_stop is True
    assert outcome.still_checked is True
    assert outcome.settled_default_filename == PROTECTED_DEFAULT
    assert outcome.reason == "default_checkbox_settle_timeout"
    assert page.wait_ms == []
    _assert_no_restore(page)


def test_unexpected_third_default_stops_immediately() -> None:
    box = FakeCheckbox(
        is_checked=True,
        uncheck_error=TimeoutError(UNCHECK_STATE_ERROR),
    )
    page = FakeCheckboxPage(exact_boxes=[box], radios=_third_default_radios())
    outcome = _hatch_uncheck(page)
    assert outcome.should_stop is True
    assert outcome.reason == "default_changed_unexpectedly"
    assert outcome.settled_default_filename == THIRD_CV
    assert page.wait_ms == []
    assert box.uncheck_calls == 1
    _assert_no_restore(page)


def test_default_unobservable_through_timeout_stops() -> None:
    box = FakeCheckbox(
        is_checked=True,
        uncheck_error=TimeoutError(UNCHECK_STATE_ERROR),
    )
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_no_default_hatch_selected_radios(),
    )
    outcome = _hatch_uncheck(page, timeout_ms=0)
    assert outcome.should_stop is True
    assert outcome.reason == "default_unobservable_after_uncheck"
    assert page.wait_ms == []
    _assert_no_restore(page)


def test_committed_default_disabled_checkbox_stops_without_uncheck(tmp_path: Path) -> None:
    path = tmp_path / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    box = FakeCheckbox(is_checked=True, enabled=False)
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_csk_selected_as_committed_default_radios(),
    )
    metrics = SpikeMetrics(opportunity_id="opp_01M0E6GQ9XQH9DK9N5T0MS67N0")
    outcome = uncheck_default_checkbox_if_checked(
        page,
        metrics,
        diagnostic_path=path,
        expected_cv_filename=CSK_CV,
        baseline_default_filename=CSK_CV,
        baseline_default_observable=True,
        timeout_ms=15_000,
        poll_ms=400,
    )
    assert outcome.should_stop is True
    assert outcome.reason == "structural_default_checkbox_locked"
    assert outcome.uncheck_attempted is False
    assert outcome.uncheck_threw is False
    assert outcome.uncheck_returned is False
    assert outcome.settle_poll_count == 0
    assert outcome.settle_wait_ms == 0
    assert outcome.still_checked is True
    assert box.uncheck_calls == 0
    assert page.wait_ms == []
    assert metrics.default_checkbox_reason == "structural_default_checkbox_locked"
    _assert_no_restore(page)
    payload = json.loads(path.read_text(encoding="utf-8"))
    stages = [item["stage"] for item in payload["snapshots"]]
    assert STAGE_BEFORE_UNCHECK in stages
    assert STAGE_CHECKBOX_GUARD_DECISION in stages
    assert STAGE_AFTER_UNCHECK_RETURN_OR_THROW not in stages
    assert STAGE_CHECKBOX_SETTLE_POLL not in stages
    guard = next(
        item
        for item in payload["snapshots"]
        if item["stage"] == STAGE_CHECKBOX_GUARD_DECISION
    )
    assert guard["uncheck_attempted"] is False
    assert guard["checkbox_enabled"] is False
    assert guard["guard_reason"] == "structural_default_checkbox_locked"
    assert guard["selected_filename"] == CSK_CV
    assert guard["structural_default_filename"] == CSK_CV
    assert not any(
        "Clicking the checkbox did not change its state" in (item.get("uncheck_exception_message") or "")
        for item in payload["snapshots"]
    )


def test_non_default_selected_enabled_unchecked_does_not_uncheck() -> None:
    box = FakeCheckbox(is_checked=False, enabled=True)
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_hatch_selected_generic_default_radios(),
    )
    outcome = uncheck_default_checkbox_if_checked(
        page,
        SpikeMetrics(opportunity_id="opp_01M0CTP2ZJ754YG5G7YA7X3ZMA"),
        expected_cv_filename=HATCH_CV,
        baseline_default_filename=PROTECTED_DEFAULT,
        baseline_default_observable=True,
    )
    assert outcome.should_stop is False
    assert outcome.reason == "checkbox_already_unchecked"
    assert outcome.uncheck_attempted is False
    assert box.uncheck_calls == 0
    assert page.wait_ms == []
    _assert_no_restore(page)


def test_new_upload_enabled_checked_still_unchecks() -> None:
    box = FakeCheckbox(is_checked=True, enabled=True)
    page = FakeCheckboxPage(
        exact_boxes=[box],
        radios=_hatch_selected_as_default_radios(),
        settle_after_waits=[
            {
                "checked": False,
                "enabled": True,
                "radios": _hatch_selected_default_restored_radios(),
            }
        ],
    )
    outcome = _hatch_uncheck(page)
    assert outcome.should_stop is False
    assert outcome.reason == "checkbox_unchecked"
    assert box.uncheck_calls == 1
    assert outcome.settled_default_filename == PROTECTED_DEFAULT
    assert HATCH_CV in page.radios[0]._text
    assert page.radios[0]._selected is True
    assert "Default" in page.radios[1]._text
    _assert_no_restore(page)


def test_review_and_submit_gates_unchanged_by_default_checkbox_lock() -> None:
    hatch_cl = "David Cropper - Hatch - AI Trainer - Cover Letter.pdf"
    observation = parse_review_document_filenames(
        "Documents included\n"
        f"Résumé\n{HATCH_CV}\n"
        f"Cover letter\n{hatch_cl}\n"
        "Submit application\n"
    )
    gate = evaluate_review_document_gate(
        expected_cv=HATCH_CV,
        expected_cover_letter=hatch_cl,
        observation=observation,
    )
    assert gate.allow_owner_handoff is True
    handoff = build_final_review_handoff(final_submit_control_visible=True)
    assert handoff.submit_clicked_by_automation is False
    page = PageSignals(looks_like_review_or_confirmation=True)
    assert classify_control("Submit application", page=page) is ControlClass.FINAL_SUBMIT
