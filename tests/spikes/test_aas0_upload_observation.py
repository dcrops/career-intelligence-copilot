"""AAS-0.1 résumé upload diagnostic dump — serialization only, no SEEK."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.document_gates import DocumentsStepGateError  # noqa: E402
from aas0.metrics import SpikeMetrics  # noqa: E402
from aas0.resume_lifecycle import (  # noqa: E402
    application_cv_is_structural_default,
    build_seek_resume_snapshot,
)
from aas0.resume_rotation import evaluate_rotation_decision, evaluate_rotation_trigger  # noqa: E402
from aas0.seek_documents import (  # noqa: E402
    RESUME_UPLOAD_INTERACTION_FAILURES,
    ResumeUploadInteractionError,
    capture_upload_observation,
    confirm_expected_cv_for_application,
    documents_step_ready_to_continue,
    inspect_file_input_matches,
    prepare_and_upload_documents,
)
from aas0.upload_observation import (  # noqa: E402
    CHOSEN_VIA_EXISTING_SAVED_RESUME,
    CHOSEN_VIA_LOCATOR_FIRST,
    CHOSEN_VIA_RESUME_FILE_ASSOCIATED_UPLOAD,
    STAGE_FIRST_CV_WAIT_FINAL,
    STAGE_FIRST_CV_WAIT_INITIAL,
    STAGE_FIRST_UPLOAD_AFTER,
    STAGE_FIRST_UPLOAD_BEFORE,
    STAGE_RETRY_CV_WAIT_FINAL,
    STAGE_RETRY_CV_WAIT_INITIAL,
    STAGE_RETRY_UPLOAD_AFTER,
    STAGE_RETRY_UPLOAD_BEFORE,
    UPLOAD_INTERACTION_CAPACITY,
    UPLOAD_INTERACTION_EXISTING_REUSED,
    UPLOAD_INTERACTION_FILECHOOSER,
    UPLOAD_OBSERVATION_FILENAME,
    append_upload_diagnostic,
    build_upload_observation_snapshot,
    diagnostic_has_stage,
    is_resume_upload_accessible_name,
    normalise_upload_accessible_name,
)

PROTECTED_DEFAULT = "David Cropper - AI Engineer CV.pdf"
HATCH_CV = "David Cropper - Hatch - AI Trainer - CV.pdf"
HATCH_CL = "David Cropper - Hatch - AI Trainer - Cover Letter.pdf"
NOVIGI_CV = "David Cropper - Novigi Pty Ltd - Senior AI Engineer - CV.pdf"
OPP_ID = "opp_01M0CTP2ZJ754YG5G7YA7X3ZMA"


class FakeFileInput:
    def __init__(
        self,
        *,
        visible: bool = True,
        enabled: bool = True,
        attached: bool = True,
        input_id: str = "resume-input",
        name: str = "resume",
        aria_label: str = "Upload resume",
        data_automation: str = "resumeUpload",
        throws: Exception | None = None,
    ) -> None:
        self._visible = visible
        self._enabled = enabled
        self.attached = attached
        self.input_id = input_id
        self.name = name
        self.aria_label = aria_label
        self.data_automation = data_automation
        self._throws = throws
        self.set_calls: list[str] = []

    def is_visible(self) -> bool:
        return self._visible

    def is_enabled(self) -> bool:
        return self._enabled

    def bounding_box(self):
        return {"x": 1, "y": 2, "width": 10, "height": 10}

    def evaluate(self, script: str):  # noqa: ARG002
        return {
            "tag_name": "input",
            "input_type": "file",
            "attached": self.attached,
            "id": self.input_id,
            "name": self.name,
            "aria_label": self.aria_label,
            "data_automation": self.data_automation,
        }

    def set_input_files(self, path: str) -> None:
        if self._throws is not None:
            raise self._throws
        self.set_calls.append(path)


class FakeLocator:
    def __init__(self, nodes: list) -> None:
        self._nodes = list(nodes)
        self.first = self._nodes[0] if self._nodes else self

    def count(self) -> int:
        return len(self._nodes)

    def nth(self, index: int):
        return self._nodes[index]

    def set_input_files(self, path: str) -> None:
        if not self._nodes:
            raise RuntimeError("no input")
        self._nodes[0].set_input_files(path)

    def is_visible(self) -> bool:
        return bool(self._nodes and hasattr(self._nodes[0], "is_visible") and self._nodes[0].is_visible())

    def inner_text(self, timeout: int | None = None) -> str:  # noqa: ARG002
        if self._nodes and hasattr(self._nodes[0], "inner_text"):
            return self._nodes[0].inner_text()
        return getattr(self, "_text", "")

    def locator(self, _selector: str):
        return FakeLocator([])


class FakeRadio:
    def __init__(self, text: str, *, selected: bool) -> None:
        self._text = text
        self._selected = selected
        self.check_calls = 0
        self.click_calls = 0
        self.page: FakeUploadPage | None = None

    def is_visible(self) -> bool:
        return True

    def is_checked(self) -> bool:
        return self._selected

    def evaluate(self, script: str):  # noqa: ARG002
        return [self._text]

    def check(self, timeout: int | None = None) -> None:  # noqa: ARG002
        self.check_calls += 1
        self._selected = True
        if self.page is not None:
            for radio in self.page.radios:
                if radio is not self:
                    radio._selected = False

    def click(self, timeout: int | None = None) -> None:  # noqa: ARG002
        self.click_calls += 1
        self.check()


class FakeUploadButton:
    def __init__(
        self,
        *,
        aria_busy: str | None = None,
        inner: str = "Upload",
        kind: str = "resume",
    ) -> None:
        self._aria_busy = aria_busy
        self._inner = inner
        self.kind = kind
        self.clicks: list[str] = []
        self.page: FakeUploadPage | None = None

    def is_visible(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def inner_text(self) -> str:
        return self._inner

    def get_attribute(self, name: str):
        if name == "aria-busy":
            return self._aria_busy
        if name == "aria-label":
            return self._inner
        return None

    def click(self, timeout: int | None = None) -> None:  # noqa: ARG002
        self.clicks.append("click")
        if self.page is not None:
            self.page.last_upload_clicked = self.kind
            if self.kind == "resume" and self.page.capacity_on_upload_click:
                self.page.filechooser_fires = False
                self.page.capacity_modal_visible = True
                self.page.body_text = (
                    "Résumé limit reached. Please select a résumé to delete "
                    "from your list and try again."
                )

    def locator(self, _selector: str):
        return FakeLocator([])

    def evaluate(self, script: str):  # noqa: ARG002
        if "ancestor_depth" in script or "nearest_ancestor" in script:
            return {
                "method": "nearest_ancestor_excluding_cover_input",
                "input_id": "resume-fileFile",
                "label_for": "",
                "ancestor_depth": 4,
                "found": True,
            }
        return {
            "tag_name": "button",
            "role": "button",
            "aria_busy": self._aria_busy,
            "aria_label": "",
            "class_name": "upload-btn",
            "inner_text": self._inner,
            "svg_classes": ["icon-refresh"],
            "progressbar_count": 0,
            "aria_busy_child_count": 0,
            "spin_or_loading_count": 0,
        }


class FakeFileChooser:
    def __init__(self, page: FakeUploadPage) -> None:
        self.page = page

    def set_files(self, path: str) -> None:
        if self.page.chooser_throws is not None:
            raise self.page.chooser_throws
        self.page.filechooser_set_calls.append(path)
        if not self.page.appear_expected_cv:
            return
        name = Path(path).name
        for radio in self.page.radios:
            radio._selected = False
        existing = next(
            (radio for radio in self.page.radios if name in radio._text),
            None,
        )
        if existing is None:
            added = FakeRadio(name, selected=True)
            added.page = self.page
            self.page.radios.insert(0, added)
        else:
            existing._selected = True
        if self.page.auto_check_default:
            self.page.default_checkbox_checked = True
            self.page.structural_default_filename = name


class FakeExpectFileChooser:
    def __init__(self, page: FakeUploadPage) -> None:
        self.page = page
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ARG002
        if exc_type:
            return False
        if not self.page.filechooser_fires:
            raise TimeoutError("Timeout waiting for file chooser")
        self.value = FakeFileChooser(self.page)
        return False


class FakeHandle:
    def __init__(self, element) -> None:
        self._element = element

    def as_element(self):
        return self._element


class FakeCoverLetterRadio:
    def __init__(self, *, checked: bool = False) -> None:
        self._checked = checked
        self.check_calls = 0

    def is_checked(self) -> bool:
        return self._checked

    def check(self, timeout: int | None = None) -> None:  # noqa: ARG002
        self.check_calls += 1
        self._checked = True

    def click(self, timeout: int | None = None) -> None:  # noqa: ARG002
        self.check()


class FakeUploadPage:
    def __init__(
        self,
        *,
        resume_inputs: list[FakeFileInput] | None = None,
        cover_inputs: list[FakeFileInput] | None = None,
        radios: list[FakeRadio] | None = None,
        cover_letter_radio: bool = False,
        upload_busy: str | None = None,
        resume_upload_button: FakeUploadButton | None = None,
        cover_letter_upload_button: FakeUploadButton | None = None,
        filechooser_fires: bool = True,
        chooser_throws: Exception | None = None,
        appear_expected_cv: bool = True,
        auto_check_default: bool = False,
        cl_upload_first: bool = False,
        associate_resume_upload: bool = True,
        body_text: str = "Cover letter uploaded",
        capacity_on_upload_click: bool = False,
    ) -> None:
        self.resume_inputs = list(resume_inputs or [])
        self.cover_inputs = list(cover_inputs or [])
        self.radios = list(radios or [])
        for radio in self.radios:
            radio.page = self
        self.cover_letter_radio_control = (
            FakeCoverLetterRadio(checked=False) if cover_letter_radio else None
        )
        self.cover_letter_radio = cover_letter_radio
        self.upload_busy = upload_busy
        self.wait_ms: list[int] = []
        self.filechooser_fires = filechooser_fires
        self.chooser_throws = chooser_throws
        self.appear_expected_cv = appear_expected_cv
        self.auto_check_default = auto_check_default
        self.capacity_on_upload_click = capacity_on_upload_click
        self.capacity_modal_visible = False
        self.filechooser_set_calls: list[str] = []
        self.last_upload_clicked: str | None = None
        self.default_checkbox_checked = False
        self.structural_default_filename = PROTECTED_DEFAULT
        self.body_text = body_text
        if resume_upload_button is not None:
            self.resume_upload_button = resume_upload_button
        elif associate_resume_upload and self.resume_inputs:
            self.resume_upload_button = FakeUploadButton(
                aria_busy=upload_busy, kind="resume"
            )
        else:
            self.resume_upload_button = None
        self.cover_letter_upload_button = cover_letter_upload_button
        self.cl_upload_first = cl_upload_first
        if self.resume_upload_button is not None:
            self.resume_upload_button.page = self
        if self.cover_letter_upload_button is not None:
            self.cover_letter_upload_button.page = self

    def locator(self, selector: str):
        if selector == "body":
            body = FakeLocator([])
            body._text = self.body_text
            return body
        if "cover" in selector.lower():
            return FakeLocator(self.cover_inputs)
        if "resume" in selector.lower():
            return FakeLocator(self.resume_inputs)
        return FakeLocator([])

    def get_by_role(self, role: str, name=None):
        if role == "button":
            buttons: list[FakeUploadButton] = []
            if self.cl_upload_first and self.cover_letter_upload_button:
                buttons.append(self.cover_letter_upload_button)
            if self.resume_upload_button:
                buttons.append(self.resume_upload_button)
            if self.cover_letter_upload_button and not self.cl_upload_first:
                buttons.append(self.cover_letter_upload_button)
            if self.capacity_modal_visible:
                close = FakeUploadButton(inner="Close", kind="close")
                close.page = self
                buttons.append(close)
            if not buttons:
                buttons = [FakeUploadButton(aria_busy=self.upload_busy)]
            if name is not None:
                import re as _re

                pattern = name if hasattr(name, "search") else _re.compile(str(name), _re.I)
                buttons = [
                    button
                    for button in buttons
                    if pattern.search(
                        (button.inner_text() or "").replace("\u2060", " ").strip()
                    )
                ]
            return FakeLocator(buttons)
        if role == "radio":
            if isinstance(name, str) and "cover letter" in name.lower():
                return FakeLocator(
                    [self.cover_letter_radio_control]
                    if self.cover_letter_radio_control
                    else []
                )
            return FakeLocator(self.radios)
        return FakeLocator([])

    def get_by_text(self, pattern):
        import re as _re

        compiled = pattern if hasattr(pattern, "search") else _re.compile(str(pattern), _re.I)
        if compiled.search(self.body_text or ""):
            node = FakeUploadButton(inner=self.body_text, kind="text")
            return FakeLocator([node])
        return FakeLocator([])

    def wait_for_timeout(self, ms: int) -> None:
        self.wait_ms.append(ms)

    def evaluate_handle(self, _script: str):
        return FakeHandle(self.resume_upload_button)

    def expect_file_chooser(self, timeout: int | None = None):  # noqa: ARG002
        return FakeExpectFileChooser(self)


def _metrics() -> SpikeMetrics:
    return SpikeMetrics(opportunity_id=OPP_ID)


def _export_pdfs(tmp_path: Path) -> tuple[Path, Path]:
    export = tmp_path / "export"
    export.mkdir()
    cv = export / HATCH_CV
    cl = export / HATCH_CL
    cv.write_bytes(b"%PDF")
    cl.write_bytes(b"%PDF")
    return cv, cl


def _novigi_selected() -> list[FakeRadio]:
    return [
        FakeRadio(NOVIGI_CV, selected=True),
        FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False),
    ]


def _hatch_present_other_selected() -> list[FakeRadio]:
    return [
        FakeRadio(NOVIGI_CV, selected=True),
        FakeRadio(HATCH_CV, selected=False),
        FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False),
    ]


def _capacity_library_with_hatch() -> list[FakeRadio]:
    radios = _hatch_present_other_selected()
    radios.extend(
        FakeRadio(f"Filler {index} CV.pdf", selected=False) for index in range(7)
    )
    return radios


def test_resume_input_count_zero_skips_filechooser(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(resume_inputs=[], radios=_novigi_selected())
    uploaded = prepare_and_upload_documents(
        page,
        cv_pdf=cv,
        cl_pdf=cl,
        metrics=_metrics(),
        upload_diagnostic_path=path,
    )
    assert uploaded is False
    payload = json.loads(path.read_text(encoding="utf-8"))
    after = next(
        item for item in payload["snapshots"] if item["stage"] == STAGE_FIRST_UPLOAD_AFTER
    )
    assert after["resume_input_count_zero_skip"] is True
    assert after["filechooser_event_observed"] is None
    assert after["set_input_files_started"] is False
    assert after["match_count"] == 0
    assert page.filechooser_set_calls == []
    assert page.wait_ms == []


def test_visible_resume_upload_filechooser_returns(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    node = FakeFileInput()
    page = FakeUploadPage(resume_inputs=[node], radios=_novigi_selected())
    without = prepare_and_upload_documents(page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics())
    node2 = FakeFileInput()
    page2 = FakeUploadPage(resume_inputs=[node2], radios=_novigi_selected())
    with_dump = prepare_and_upload_documents(
        page2,
        cv_pdf=cv,
        cl_pdf=cl,
        metrics=_metrics(),
        upload_diagnostic_path=path,
    )
    assert without is True
    assert with_dump is True
    assert node.set_calls == []
    assert node2.set_calls == []
    assert page.filechooser_set_calls == [str(cv)]
    assert page2.filechooser_set_calls == [str(cv)]
    assert page.resume_upload_button.clicks == ["click"]
    assert 200 in page.wait_ms
    after = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
        if item["stage"] == STAGE_FIRST_UPLOAD_AFTER
    )
    assert after["upload_interaction"] == UPLOAD_INTERACTION_FILECHOOSER
    assert after["filechooser_event_observed"] is True
    assert after["chooser_set_files_returned"] is True
    assert after["chooser_set_files_threw"] is False
    assert after["set_input_files_started"] is False
    assert after["chosen_via"] == CHOSEN_VIA_RESUME_FILE_ASSOCIATED_UPLOAD
    assert after["expected_cv_path"] == str(cv)
    assert after["resume_upload_association"]["method"] == (
        "nearest_ancestor_excluding_cover_input"
    )


def test_chooser_set_files_throw_stops(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    node = FakeFileInput()
    page = FakeUploadPage(
        resume_inputs=[node],
        radios=_novigi_selected(),
        chooser_throws=TimeoutError("chooser failed"),
    )
    metrics = _metrics()
    try:
        prepare_and_upload_documents(
            page,
            cv_pdf=cv,
            cl_pdf=cl,
            metrics=metrics,
            upload_diagnostic_path=path,
        )
    except ResumeUploadInteractionError as error:
        assert error.reason == "chooser_set_files_threw"
    else:
        raise AssertionError("expected ResumeUploadInteractionError")
    assert node.set_calls == []
    after = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
        if item["stage"] == STAGE_FIRST_UPLOAD_AFTER
    )
    assert after["filechooser_event_observed"] is True
    assert after["chooser_set_files_started"] is True
    assert after["chooser_set_files_returned"] is False
    assert after["chooser_set_files_threw"] is True
    assert after["chooser_set_files_exception_type"] == "TimeoutError"
    assert after["set_input_files_started"] is False
    assert page.wait_ms == [400] or 200 not in page.wait_ms


def test_no_filechooser_event_stops(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=_novigi_selected(),
        filechooser_fires=False,
    )
    try:
        prepare_and_upload_documents(
            page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics(), upload_diagnostic_path=path
        )
    except ResumeUploadInteractionError as error:
        assert error.reason == "no_filechooser_event"
    else:
        raise AssertionError("expected ResumeUploadInteractionError")
    after = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
        if item["stage"] == STAGE_FIRST_UPLOAD_AFTER
    )
    assert after["filechooser_event_observed"] is False
    assert after["chooser_set_files_started"] is False
    assert after["capacity_modal_observed"] is False
    assert after["upload_interaction"] != UPLOAD_INTERACTION_CAPACITY
    assert page.filechooser_set_calls == []


def test_multiple_resume_inputs_including_hidden(tmp_path: Path) -> None:
    hidden = FakeFileInput(visible=False, input_id="hidden-resume")
    visible = FakeFileInput(visible=True, input_id="visible-resume")
    matches = inspect_file_input_matches(FakeLocator([hidden, visible]))
    assert len(matches) == 2
    assert matches[0]["visible"] is False
    assert matches[0]["id"] == "hidden-resume"
    assert matches[1]["visible"] is True
    snapshot = build_upload_observation_snapshot(
        stage=STAGE_FIRST_UPLOAD_BEFORE,
        resume_input_matches=matches,
        chosen_index=0,
        chosen_via=CHOSEN_VIA_LOCATOR_FIRST,
        cover_letter_input_count=1,
    )
    assert snapshot["match_count"] == 2
    assert snapshot["chosen_index"] == 0
    assert snapshot["resume_inputs"][0]["visible"] is False


def test_cover_letter_input_count_recorded_separately(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        cover_inputs=[FakeFileInput(input_id="cover"), FakeFileInput(input_id="cover2")],
        radios=_novigi_selected(),
    )
    capture_upload_observation(
        page,
        path=path,
        stage=STAGE_FIRST_UPLOAD_BEFORE,
        expected_cv_filename=HATCH_CV,
    )
    snap = json.loads(path.read_text(encoding="utf-8"))["snapshots"][0]
    assert snap["match_count"] == 1
    assert snap["cover_letter_input_count"] == 2


def test_first_vs_retry_stages_are_distinct(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=_novigi_selected(),
    )
    metrics = _metrics()
    prepare_and_upload_documents(
        page, cv_pdf=cv, cl_pdf=cl, metrics=metrics, upload_diagnostic_path=path
    )
    prepare_and_upload_documents(
        page,
        cv_pdf=cv,
        cl_pdf=cl,
        metrics=metrics,
        retry_cv=True,
        upload_diagnostic_path=path,
    )
    stages = [
        item["stage"]
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
    ]
    assert STAGE_FIRST_UPLOAD_BEFORE in stages
    assert STAGE_FIRST_UPLOAD_AFTER in stages
    assert STAGE_RETRY_UPLOAD_BEFORE in stages
    assert STAGE_RETRY_UPLOAD_AFTER in stages


def test_spinner_detector_raw_evidence_persisted(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=_novigi_selected(),
        upload_busy="true",
    )
    capture_upload_observation(
        page,
        path=path,
        stage=STAGE_FIRST_CV_WAIT_FINAL,
        expected_cv_filename=HATCH_CV,
    )
    snap = json.loads(path.read_text(encoding="utf-8"))["snapshots"][0]
    assert snap["spinner_detector"] is True
    assert snap["upload_button_aria_busy"] is True
    assert snap["upload_controls"][0]["aria_busy"] == "true"
    assert snap["upload_controls"][0]["svg_classes"] == ["icon-refresh"]


def test_expected_cv_absent_and_present_persisted(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    absent = FakeUploadPage(radios=_novigi_selected())
    capture_upload_observation(
        absent, path=path, stage=STAGE_FIRST_CV_WAIT_INITIAL, expected_cv_filename=HATCH_CV
    )
    present = FakeUploadPage(
        radios=[
            FakeRadio(f"{HATCH_CV}\nAdded less than a minute ago", selected=True),
            FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False),
        ]
    )
    capture_upload_observation(
        present, path=path, stage=STAGE_RETRY_CV_WAIT_FINAL, expected_cv_filename=HATCH_CV
    )
    first, second = json.loads(path.read_text(encoding="utf-8"))["snapshots"]
    assert first["expected_cv_present"] is False
    assert first["expected_cv_selected"] is False
    assert first["selected_filename"] == NOVIGI_CV
    assert first["structural_default_filename"] == PROTECTED_DEFAULT
    assert HATCH_CV not in first["resume_filenames"]
    assert second["expected_cv_present"] is True
    assert second["expected_cv_selected"] is True
    assert second["selected_filename"] == HATCH_CV


def test_diagnostic_written_before_stop(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(resume_inputs=[], radios=_novigi_selected())
    prepare_and_upload_documents(
        page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics(), upload_diagnostic_path=path
    )
    decision = confirm_expected_cv_for_application(
        page,
        expected_cv_filename=HATCH_CV,
        metrics=_metrics(),
        timeout_ms=0,
        upload_diagnostic_path=path,
        upload_wait_phase="first",
    )
    assert decision.action == "stop"
    assert decision.reason == "expected_cv_not_present"
    assert path.exists()
    assert diagnostic_has_stage(path, STAGE_FIRST_UPLOAD_AFTER)
    assert diagnostic_has_stage(path, STAGE_FIRST_CV_WAIT_INITIAL)
    assert diagnostic_has_stage(path, STAGE_FIRST_CV_WAIT_FINAL)


def test_confirm_wait_dumps_retry_phase(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    page = FakeUploadPage(radios=_novigi_selected())
    confirm_expected_cv_for_application(
        page,
        expected_cv_filename=HATCH_CV,
        metrics=_metrics(),
        timeout_ms=0,
        upload_diagnostic_path=path,
        upload_wait_phase="retry",
    )
    stages = [
        item["stage"]
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
    ]
    assert stages == [STAGE_RETRY_CV_WAIT_INITIAL, STAGE_RETRY_CV_WAIT_FINAL]


def test_append_keeps_first_then_retry_order(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    for stage in (
        STAGE_FIRST_UPLOAD_BEFORE,
        STAGE_FIRST_CV_WAIT_FINAL,
        STAGE_RETRY_UPLOAD_BEFORE,
        STAGE_RETRY_CV_WAIT_FINAL,
    ):
        append_upload_diagnostic(
            path,
            build_upload_observation_snapshot(stage=stage, retry_cv="retry" in stage),
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert [item["stage"] for item in payload["snapshots"]] == [
        STAGE_FIRST_UPLOAD_BEFORE,
        STAGE_FIRST_CV_WAIT_FINAL,
        STAGE_RETRY_UPLOAD_BEFORE,
        STAGE_RETRY_CV_WAIT_FINAL,
    ]


def test_unicode_upload_name_normalises() -> None:
    assert normalise_upload_accessible_name("\u2060Upload") == "Upload"
    assert is_resume_upload_accessible_name("\u2060Upload")
    assert is_resume_upload_accessible_name("Upload")
    assert not is_resume_upload_accessible_name("Upload a cover letter")


def test_two_upload_buttons_resume_associated_not_first(tmp_path: Path) -> None:
    cv, cl = _export_pdfs(tmp_path)
    resume_btn = FakeUploadButton(inner="\u2060Upload", kind="resume")
    cover_btn = FakeUploadButton(inner="\u2060Upload", kind="cover")
    cover_input = FakeFileInput(input_id="cover-letter-fileFile")
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput(input_id="resume-fileFile")],
        cover_inputs=[cover_input],
        radios=_novigi_selected(),
        resume_upload_button=resume_btn,
        cover_letter_upload_button=cover_btn,
        cl_upload_first=True,
        cover_letter_radio=True,
    )
    uploaded = prepare_and_upload_documents(
        page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics()
    )
    assert uploaded is True
    assert resume_btn.clicks == ["click"]
    assert cover_btn.clicks == []
    assert page.last_upload_clicked == "resume"
    assert cover_input.set_calls == [str(cl)]
    assert page.resume_inputs[0].set_calls == []


def test_expected_cv_never_appears_after_filechooser(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=_novigi_selected(),
        appear_expected_cv=False,
    )
    prepare_and_upload_documents(
        page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics(), upload_diagnostic_path=path
    )
    decision = confirm_expected_cv_for_application(
        page,
        expected_cv_filename=cv.name,
        metrics=_metrics(),
        timeout_ms=0,
        upload_diagnostic_path=path,
        upload_wait_phase="first",
    )
    assert decision.action == "stop"
    assert decision.reason == "expected_cv_not_present"
    after = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
        if item["stage"] == STAGE_FIRST_UPLOAD_AFTER
    )
    assert after["chooser_set_files_returned"] is True
    assert after["expected_cv_present"] is False


def test_no_saved_resume_selected_initialises_non_default(tmp_path: Path) -> None:
    cv, cl = _export_pdfs(tmp_path)
    hatch = FakeRadio(HATCH_CV, selected=False)
    default = FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=[hatch, default],
        appear_expected_cv=False,
    )
    prepare_and_upload_documents(page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics())
    assert hatch.check_calls == 1
    assert default.check_calls == 0
    assert hatch.is_checked()


def test_dont_include_resume_never_used_as_initialisation(tmp_path: Path) -> None:
    cv, cl = _export_pdfs(tmp_path)
    skip = FakeRadio("Don't include a résumé", selected=True)
    hatch = FakeRadio(HATCH_CV, selected=False)
    default = FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=[skip, hatch, default],
        appear_expected_cv=False,
    )
    prepare_and_upload_documents(page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics())
    assert skip.check_calls == 0
    assert skip.click_calls == 0
    assert hatch.check_calls == 1
    assert default.check_calls == 0


def test_already_selected_saved_resume_is_left_selected(tmp_path: Path) -> None:
    cv, cl = _export_pdfs(tmp_path)
    hatch = FakeRadio(HATCH_CV, selected=True)
    default = FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=[hatch, default],
        appear_expected_cv=False,
    )
    prepare_and_upload_documents(page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics())
    assert hatch.check_calls == 0
    assert default.check_calls == 0
    assert hatch.is_checked()


def test_retry_uses_filechooser_not_hidden_input(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    node = FakeFileInput()
    page = FakeUploadPage(
        resume_inputs=[node],
        radios=_novigi_selected(),
        appear_expected_cv=False,
    )
    metrics = _metrics()
    prepare_and_upload_documents(
        page, cv_pdf=cv, cl_pdf=cl, metrics=metrics, upload_diagnostic_path=path
    )
    prepare_and_upload_documents(
        page,
        cv_pdf=cv,
        cl_pdf=cl,
        metrics=metrics,
        retry_cv=True,
        upload_diagnostic_path=path,
    )
    assert node.set_calls == []
    assert page.filechooser_set_calls == [str(cv), str(cv)]
    stages = [
        item["stage"]
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
    ]
    assert stages.count(STAGE_RETRY_UPLOAD_AFTER) == 1
    retry_after = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
        if item["stage"] == STAGE_RETRY_UPLOAD_AFTER
    )
    assert retry_after["upload_interaction"] == UPLOAD_INTERACTION_FILECHOOSER
    assert retry_after["set_input_files_started"] is False
    assert retry_after["chooser_set_files_returned"] is True


def test_cover_letter_still_uses_hidden_input(tmp_path: Path) -> None:
    cv, cl = _export_pdfs(tmp_path)
    resume_input = FakeFileInput(input_id="resume-fileFile")
    cover_input = FakeFileInput(input_id="cover-letter-fileFile")
    page = FakeUploadPage(
        resume_inputs=[resume_input],
        cover_inputs=[cover_input],
        radios=_novigi_selected(),
        cover_letter_radio=True,
        appear_expected_cv=False,
    )
    metrics = _metrics()
    uploaded = prepare_and_upload_documents(
        page, cv_pdf=cv, cl_pdf=cl, metrics=metrics
    )
    assert uploaded is True
    assert resume_input.set_calls == []
    assert cover_input.set_calls == [str(cl)]
    assert page.cover_letter_radio_control.check_calls == 1
    assert any(item.startswith("cover_letter:") for item in metrics.documents_uploaded)


def test_resume_upload_button_not_associated_stops(tmp_path: Path) -> None:
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=_novigi_selected(),
        associate_resume_upload=False,
    )
    try:
        prepare_and_upload_documents(page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics())
    except ResumeUploadInteractionError as error:
        assert error.reason == "resume_upload_button_not_associated"
    else:
        raise AssertionError("expected ResumeUploadInteractionError")
    assert page.filechooser_set_calls == []


def test_filechooser_then_expected_cv_selected(tmp_path: Path) -> None:
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=_novigi_selected(),
    )
    prepare_and_upload_documents(page, cv_pdf=cv, cl_pdf=cl, metrics=_metrics())
    decision = confirm_expected_cv_for_application(
        page,
        expected_cv_filename=cv.name,
        metrics=_metrics(),
        timeout_ms=1_000,
        poll_ms=1,
    )
    assert decision.action != "stop"
    assert decision.present is True
    assert decision.selected is True
    assert decision.reason == "expected_cv_selected"


def test_expected_cv_already_present_selects_without_upload(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=_hatch_present_other_selected(),
        capacity_on_upload_click=True,
    )
    metrics = _metrics()
    uploaded = prepare_and_upload_documents(
        page,
        cv_pdf=cv,
        cl_pdf=cl,
        metrics=metrics,
        upload_diagnostic_path=path,
    )
    assert uploaded is True
    assert f"cv:{HATCH_CV}" in metrics.documents_uploaded
    assert page.filechooser_set_calls == []
    assert page.resume_upload_button.clicks == []
    hatch = next(radio for radio in page.radios if HATCH_CV in radio._text)
    assert hatch.is_checked() is True
    after = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
        if item["stage"] == STAGE_FIRST_UPLOAD_AFTER
    )
    assert after["upload_interaction"] == UPLOAD_INTERACTION_EXISTING_REUSED
    assert after["chosen_via"] == CHOSEN_VIA_EXISTING_SAVED_RESUME
    assert after["existing_expected_cv_reused"] is True
    assert after["upload_attempted"] is False
    assert after["filechooser_event_observed"] is False
    assert after["capacity_modal_observed"] is False
    assert after["expected_cv_present_before_upload"] is True
    assert after["expected_cv_selected"] is True
    trigger = evaluate_rotation_trigger(
        upload_failure_reason="resume_capacity_blocked",
        rotation_already_attempted=False,
        expected_cv_present=True,
    )
    assert trigger.should_attempt is False
    assert trigger.reason == "expected_cv_already_present_no_rotation"


def test_expected_cv_present_at_capacity_does_not_rotate(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    radios = _capacity_library_with_hatch()
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=radios,
        capacity_on_upload_click=True,
    )
    metrics = _metrics()
    uploaded = prepare_and_upload_documents(
        page,
        cv_pdf=cv,
        cl_pdf=cl,
        metrics=metrics,
        upload_diagnostic_path=path,
    )
    assert uploaded is True
    assert page.resume_upload_button.clicks == []
    assert page.filechooser_set_calls == []
    after = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
        if item["stage"] == STAGE_FIRST_UPLOAD_AFTER
    )
    assert after["saved_resume_count"] == 10
    assert after["existing_expected_cv_reused"] is True
    decision = evaluate_rotation_decision(
        entries=build_seek_resume_snapshot(
            [(radio._text, radio.is_checked()) for radio in radios]
        ).entries,
        upload_failure_reason="resume_capacity_blocked",
        rotation_already_attempted=False,
        menu_observed=True,
        expected_cv_present=True,
    )
    assert decision.action == "stop"
    assert decision.reason == "expected_cv_already_present_no_rotation"


def test_capacity_modal_is_resume_capacity_blocked_not_filechooser(tmp_path: Path) -> None:
    path = tmp_path / UPLOAD_OBSERVATION_FILENAME
    cv, cl = _export_pdfs(tmp_path)
    page = FakeUploadPage(
        resume_inputs=[FakeFileInput()],
        radios=_novigi_selected(),
        capacity_on_upload_click=True,
    )
    metrics = _metrics()
    try:
        prepare_and_upload_documents(
            page,
            cv_pdf=cv,
            cl_pdf=cl,
            metrics=metrics,
            upload_diagnostic_path=path,
        )
    except ResumeUploadInteractionError as error:
        assert error.reason == "resume_capacity_blocked"
    else:
        raise AssertionError("expected ResumeUploadInteractionError")
    assert "resume_capacity_blocked" not in RESUME_UPLOAD_INTERACTION_FAILURES
    assert page.filechooser_set_calls == []
    assert page.resume_upload_button.clicks == ["click"]
    after = next(
        item
        for item in json.loads(path.read_text(encoding="utf-8"))["snapshots"]
        if item["stage"] == STAGE_FIRST_UPLOAD_AFTER
    )
    assert after["upload_interaction"] == UPLOAD_INTERACTION_CAPACITY
    assert after["capacity_modal_observed"] is True
    assert after["filechooser_event_observed"] is False
    assert after["upload_attempted"] is True
    assert after["existing_expected_cv_reused"] is False
    trigger = evaluate_rotation_trigger(
        upload_failure_reason="resume_capacity_blocked",
        rotation_already_attempted=False,
        expected_cv_present=False,
    )
    assert trigger.should_attempt is True
    decision = evaluate_rotation_decision(
        entries=build_seek_resume_snapshot(
            [(radio._text, radio.is_checked()) for radio in page.radios]
        ).entries,
        upload_failure_reason="resume_capacity_blocked",
        rotation_already_attempted=False,
        menu_observed=True,
        deletion_verified=True,
        expected_cv_present=False,
    )
    assert decision.action == "retry_upload_once"


def test_expected_cv_as_structural_default_refuses_continue() -> None:
    snapshot = build_seek_resume_snapshot(
        [
            (f"Default\n{HATCH_CV}", True),
            (PROTECTED_DEFAULT, False),
        ]
    )
    page = FakeUploadPage(
        radios=[
            FakeRadio(f"Default\n{HATCH_CV}", selected=True),
            FakeRadio(PROTECTED_DEFAULT, selected=False),
        ]
    )
    assert application_cv_is_structural_default(
        default_filename=snapshot.default_filename,
        expected_filename=HATCH_CV,
    )
    try:
        documents_step_ready_to_continue(
            page,
            expected_cv_filename=HATCH_CV,
            snapshot=snapshot,
            spinner_active=False,
        )
    except DocumentsStepGateError as error:
        assert error.reason == "expected_cv_is_structural_default"
    else:
        raise AssertionError("expected DocumentsStepGateError")


def test_protected_default_with_expected_cv_selected_may_continue() -> None:
    snapshot = build_seek_resume_snapshot(
        [
            (HATCH_CV, True),
            (f"Default\n{PROTECTED_DEFAULT}", False),
        ]
    )
    page = FakeUploadPage(
        radios=[
            FakeRadio(HATCH_CV, selected=True),
            FakeRadio(f"Default\n{PROTECTED_DEFAULT}", selected=False),
        ]
    )
    documents_step_ready_to_continue(
        page,
        expected_cv_filename=HATCH_CV,
        snapshot=snapshot,
        spinner_active=False,
    )
    assert application_cv_is_structural_default(
        default_filename=PROTECTED_DEFAULT,
        expected_filename=HATCH_CV,
    ) is False
