"""Isolated SEEK résumé Upload + filechooser experiment.

Does **not** change production AAS upload behaviour beyond the isolated
experiment itself. Production AAS now uses the same visible Upload +
filechooser path; this script remains a standalone diagnostic.

One live trial: select an existing résumé → click the résumé Upload control
associated with ``#resume-fileFile`` → Playwright filechooser → tailored CV.

Never uploads cover letter, never Continues, never rotates, never Submits.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SPIKE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SPIKE_DIR.parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_SPIKE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR.parent))

from aas0.document_gates import filenames_equal, snapshot_has_filename  # noqa: E402
from aas0.load_inputs import (  # noqa: E402
    DEFAULT_PROFILE_DIR,
    DEFAULT_RUNS_DIR,
    format_preflight_report,
    load_spike_inputs,
)
from aas0.metrics import SpikeMetrics, TimedPhase  # noqa: E402
from aas0.owner_gate import wait_for_continue, wait_for_end_session  # noqa: E402
from aas0.run_assist import _click_apply_entry  # noqa: E402
from aas0.seek_documents import (  # noqa: E402
    choose_documents_visible,
    click_resume_radio_by_filename,
    inspect_resume_upload_controls,
    observe_resume_snapshot,
    page_body_text,
    resume_file_input,
    resume_upload_spinner_active,
)
from aas0.submit_guard import FinalSubmitGuardError  # noqa: E402
from aas0.upload_artefacts import assert_safe_external_upload_pdf  # noqa: E402

CSK_OPPORTUNITY_ID = "opp_01M0E6GQ9XQH9DK9N5T0MS67N0"
OBSERVATION_FILENAME = "controlled_resume_upload_observation.json"
POLL_MS = 400
SETTLE_TIMEOUT_MS = 45_000
FILECHOOSER_TIMEOUT_MS = 8_000

_FIND_RESUME_UPLOAD_BUTTON_JS = """() => {
  const resume = document.querySelector('#resume-fileFile');
  if (!resume) return null;
  const isUpload = (el) => {
    const raw = ((el.getAttribute('aria-label') || '') + ' '
      + (el.innerText || '')).replace(/\\u2060/g, ' ').replace(/\\s+/g, ' ').trim();
    return /^upload$/i.test(raw);
  };
  const coverInputs = [...document.querySelectorAll(
    'input[type=file][id*="cover" i], input[type=file][name*="cover" i], '
    + 'input[type=file][data-automation*="cover" i], input[type=file][id*="Cover"]'
  )].filter((el) => el !== resume);
  const label = resume.id
    ? document.querySelector('label[for="' + resume.id + '"]')
    : null;
  if (label) {
    const fromLabel = [label, ...label.querySelectorAll('button, [role="button"]')]
      .filter(isUpload);
    if (fromLabel.length === 1) return fromLabel[0];
  }
  let node = resume.parentElement;
  for (let depth = 1; depth <= 14 && node; depth += 1) {
    const uploads = [...node.querySelectorAll('button, [role="button"]')].filter(isUpload);
    const hasCover = coverInputs.some((el) => node.contains(el));
    if (uploads.length === 1 && !hasCover) return uploads[0];
    node = node.parentElement;
  }
  return null;
}"""

_DESCRIBE_ASSOCIATION_JS = """(button) => {
  const resume = document.querySelector('#resume-fileFile');
  const ancestors = [];
  let node = resume;
  for (let i = 0; i < 10 && node; i += 1) {
    ancestors.push({
      tag: String(node.tagName || '').toLowerCase(),
      id: String(node.id || ''),
      class_name: String(node.className || '').slice(0, 160),
    });
    node = node.parentElement;
  }
  let depth = 0;
  let shared = resume;
  while (shared && button && !shared.contains(button)) {
    shared = shared.parentElement;
    depth += 1;
  }
  const label = resume && resume.id
    ? document.querySelector('label[for="' + resume.id + '"]')
    : null;
  return {
    method: label && label.contains(button)
      ? 'label_for_resume-fileFile'
      : 'nearest_ancestor_excluding_cover_input',
    input_id: resume ? String(resume.id || '') : '',
    input_visible: resume ? !!(resume.offsetParent || resume.getClientRects().length) : false,
    label_for: label ? String(label.getAttribute('for') || '') : '',
    ancestor_depth: depth,
    shared_ancestor: shared ? {
      tag: String(shared.tagName || '').toLowerCase(),
      id: String(shared.id || ''),
      class_name: String(shared.className || '').slice(0, 160),
    } : null,
    button: button ? {
      tag: String(button.tagName || '').toLowerCase(),
      id: String(button.id || ''),
      role: String(button.getAttribute('role') || 'button'),
      aria_label: String(button.getAttribute('aria-label') || ''),
      inner_text: String(button.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 80),
      class_name: String(button.className || '').slice(0, 200),
      disabled: !!button.disabled,
      aria_busy: button.getAttribute('aria-busy'),
    } : null,
    ancestor_chain: ancestors,
  };
}"""


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    # #region agent log
    try:
        payload = {
            "sessionId": "152216",
            "runId": "controlled-resume-upload",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        path = _REPO_ROOT / "debug-152216.log"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except Exception:  # noqa: BLE001
        pass
    # #endregion


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _blocker_reason(page) -> str | None:
    body = (page_body_text(page) or "").lower()
    if "captcha" in body or "recaptcha" in body or "verify you are human" in body:
        return "captcha_or_blocker"
    return None


def _snapshot_payload(snapshot) -> dict[str, Any]:
    return {
        "filenames": [entry.filename for entry in snapshot.entries],
        "selected_filename": snapshot.selected_filename,
        "default_filename": snapshot.default_filename,
        "default_observable": snapshot.default_observable,
        "count": len(snapshot.entries),
    }


def _button_state(page) -> dict[str, Any]:
    controls, aria_busy, has_progress, uploading_text = inspect_resume_upload_controls(page)
    return {
        "spinner_detector": resume_upload_spinner_active(page),
        "upload_button_aria_busy": aria_busy,
        "upload_control_has_progress": has_progress,
        "uploading_text_visible": uploading_text,
        "upload_controls": controls,
    }


def _screenshot(page, shot_dir: Path, name: str, observation: dict[str, Any]) -> None:
    shot_dir.mkdir(parents=True, exist_ok=True)
    path = shot_dir / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    observation.setdefault("screenshots", []).append(str(path))


def _write_observation(path: Path, observation: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(observation, indent=2) + "\n", encoding="utf-8")


def _stop(
    observation: dict[str, Any],
    path: Path,
    *,
    outcome: str,
    reason: str,
) -> dict[str, Any]:
    observation["final_outcome"] = outcome
    observation["final_reason"] = reason
    observation["stopped_at"] = _utc_stamp()
    _write_observation(path, observation)
    _agent_log("B", "controlled_resume_upload_experiment.py:_stop", "experiment stopped", {
        "outcome": outcome,
        "reason": reason,
    })
    return observation


def run_experiment(page, *, cv_pdf: Path, run_dir: Path, observation: dict[str, Any]) -> dict[str, Any]:
    obs_path = run_dir / OBSERVATION_FILENAME
    shot_dir = run_dir / "screenshots"
    observation["expected_cv_filename"] = cv_pdf.name
    observation["expected_cv_path"] = str(cv_pdf)
    observation["filechooser_event_observed"] = False
    observation["set_files_returned"] = False
    observation["set_files_threw"] = False
    observation["polls"] = []

    blocker = _blocker_reason(page)
    if blocker:
        _screenshot(page, shot_dir, "fail_blocker", observation)
        return _stop(observation, obs_path, outcome="fail", reason=blocker)

    if not choose_documents_visible(page):
        _screenshot(page, shot_dir, "fail_not_choose_documents", observation)
        return _stop(observation, obs_path, outcome="fail", reason="choose_documents_not_active")

    snapshot = observe_resume_snapshot(page)
    observation["baseline"] = _snapshot_payload(snapshot)
    _agent_log("C", "controlled_resume_upload_experiment.py:baseline", "baseline snapshot", observation["baseline"])
    if not snapshot.default_observable or not snapshot.default_filename:
        _screenshot(page, shot_dir, "fail_default_unobservable", observation)
        return _stop(observation, obs_path, outcome="fail", reason="structural_default_not_observable")
    non_default = [
        entry.filename
        for entry in snapshot.entries
        if entry.filename and not filenames_equal(entry.filename, snapshot.default_filename)
    ]
    if not non_default:
        _screenshot(page, shot_dir, "fail_no_saved_resume", observation)
        return _stop(observation, obs_path, outcome="fail", reason="no_saved_non_default_resume")

    if not snapshot.selected_filename:
        clicked = click_resume_radio_by_filename(page, non_default[0])
        observation["selected_existing_resume_explicitly"] = clicked
        observation["explicit_selection_target"] = non_default[0]
        page.wait_for_timeout(400)
        snapshot = observe_resume_snapshot(page)
        observation["after_explicit_selection"] = _snapshot_payload(snapshot)
        if not snapshot.selected_filename:
            _screenshot(page, shot_dir, "fail_selection_required", observation)
            return _stop(observation, obs_path, outcome="fail", reason="could_not_select_existing_resume")
    else:
        observation["selected_existing_resume_explicitly"] = False
        observation["explicit_selection_target"] = None

    observation["baseline_selected_after_precondition"] = snapshot.selected_filename
    observation["baseline_default"] = snapshot.default_filename
    baseline_default = snapshot.default_filename
    _screenshot(page, shot_dir, "01_before_upload", observation)

    resume_matches = resume_file_input(page)
    if resume_matches.count() < 1:
        return _stop(observation, obs_path, outcome="fail", reason="resume-fileFile_not_found")

    handle = page.evaluate_handle(_FIND_RESUME_UPLOAD_BUTTON_JS)
    element = handle.as_element()
    if element is None:
        observation["resume_upload_association"] = {
            "found": False,
            "note": "No Upload button in a container with #resume-fileFile excluding cover inputs",
        }
        _screenshot(page, shot_dir, "fail_no_resume_upload_button", observation)
        return _stop(observation, obs_path, outcome="fail", reason="resume_upload_button_not_associated")

    association = element.evaluate(_DESCRIBE_ASSOCIATION_JS)
    observation["resume_upload_association"] = association
    _agent_log("E", "controlled_resume_upload_experiment.py:association", "resume Upload association", association)

    busy_before = resume_upload_spinner_active(page)
    observation["busy_before_click"] = busy_before
    if busy_before:
        _screenshot(page, shot_dir, "fail_already_busy", observation)
        return _stop(observation, obs_path, outcome="fail", reason="upload_already_busy_at_baseline")

    filechooser_fired = False
    set_files_error = None
    try:
        with page.expect_file_chooser(timeout=FILECHOOSER_TIMEOUT_MS) as pending:
            element.click(timeout=5_000)
        chooser = pending.value
        filechooser_fired = True
        observation["filechooser_event_observed"] = True
        _agent_log("A", "controlled_resume_upload_experiment.py:filechooser", "filechooser fired", {
            "path": str(cv_pdf),
        })
        try:
            chooser.set_files(str(cv_pdf))
            observation["set_files_returned"] = True
            observation["set_files_threw"] = False
        except Exception as error:  # noqa: BLE001
            observation["set_files_returned"] = False
            observation["set_files_threw"] = True
            observation["set_files_exception"] = f"{type(error).__name__}: {error}"
            set_files_error = error
    except Exception as error:  # noqa: BLE001
        observation["filechooser_event_observed"] = False
        observation["filechooser_exception"] = f"{type(error).__name__}: {error}"
        _screenshot(page, shot_dir, "02_no_filechooser", observation)
        _agent_log("A", "controlled_resume_upload_experiment.py:filechooser", "filechooser missing", {
            "error": str(error),
        })
        return _stop(observation, obs_path, outcome="fail", reason="no_filechooser_event")

    _screenshot(page, shot_dir, "02_after_filechooser", observation)
    if set_files_error is not None:
        return _stop(observation, obs_path, outcome="fail", reason="chooser_set_files_threw")

    started = time.monotonic()
    final_snapshot = snapshot
    while True:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        tick_snapshot = observe_resume_snapshot(page)
        tick = {
            "elapsed_ms": elapsed_ms,
            **_snapshot_payload(tick_snapshot),
            **_button_state(page),
            "expected_present": snapshot_has_filename(tick_snapshot, cv_pdf.name),
            "expected_selected": filenames_equal(cv_pdf.name, tick_snapshot.selected_filename),
            "default_unchanged": filenames_equal(baseline_default, tick_snapshot.default_filename),
        }
        observation["polls"].append(tick)
        _write_observation(obs_path, observation)
        busy = bool(tick["spinner_detector"])
        present = bool(tick["expected_present"])
        selected = bool(tick["expected_selected"])
        default_ok = bool(tick["default_unchanged"]) and tick_snapshot.default_observable
        if present and selected and default_ok and not busy:
            final_snapshot = tick_snapshot
            observation["final_snapshot"] = _snapshot_payload(final_snapshot)
            _screenshot(page, shot_dir, "03_final_settled", observation)
            return _stop(observation, obs_path, outcome="pass", reason="expected_cv_selected_and_settled")
        if not tick_snapshot.default_observable:
            _screenshot(page, shot_dir, "03_fail_default", observation)
            return _stop(observation, obs_path, outcome="fail", reason="default_became_unobservable")
        if not default_ok:
            _screenshot(page, shot_dir, "03_fail_default_changed", observation)
            return _stop(observation, obs_path, outcome="fail", reason="default_changed")
        if elapsed_ms >= SETTLE_TIMEOUT_MS:
            observation["final_snapshot"] = _snapshot_payload(tick_snapshot)
            _screenshot(page, shot_dir, "03_fail_timeout", observation)
            if busy:
                return _stop(observation, obs_path, outcome="fail", reason="upload_stuck")
            if not present:
                return _stop(observation, obs_path, outcome="fail", reason="expected_cv_never_appeared")
            if not selected:
                return _stop(observation, obs_path, outcome="fail", reason="expected_cv_appeared_not_selected")
            return _stop(observation, obs_path, outcome="fail", reason="did_not_settle")
        page.wait_for_timeout(POLL_MS)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Isolated SEEK résumé Upload + filechooser experiment (no AAS behaviour change)."
    )
    parser.add_argument("--opportunity-id", default=CSK_OPPORTUNITY_ID)
    parser.add_argument("--authorize-live", action="store_true")
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    inputs = load_spike_inputs(args.opportunity_id)
    print(format_preflight_report(inputs))
    if not args.authorize_live:
        print("Refusing to open SEEK: pass --authorize-live.")
        return 0
    if not inputs.truth.external_use_allowed or inputs.blocking_warnings:
        print("Refusing live experiment: preflight blocked.")
        return 2
    assert_safe_external_upload_pdf(inputs.cv_pdf, kind="cv", must_exist=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed.")
        return 1

    run_id = _utc_stamp()
    run_dir = args.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (args.runs_dir / "CURRENT_RUN.txt").write_text(str(run_dir) + "\n", encoding="utf-8")
    args.profile_dir.mkdir(parents=True, exist_ok=True)
    metrics = SpikeMetrics(opportunity_id=inputs.opportunity_id)
    observation: dict[str, Any] = {
        "experiment": "controlled_resume_upload_filechooser",
        "opportunity_id": inputs.opportunity_id,
        "apply_url": inputs.apply_url,
        "company": inputs.company,
        "title": inputs.title,
        "started_at": run_id,
        "production_aas_upload_unchanged": True,
    }
    obs_path = run_dir / OBSERVATION_FILENAME
    _write_observation(obs_path, observation)
    _agent_log("A", "controlled_resume_upload_experiment.py:main", "live experiment starting", {
        "opportunity_id": inputs.opportunity_id,
        "run_dir": str(run_dir),
        "cv": inputs.cv_pdf.name,
    })

    print(
        "\nCONTROLLED RÉSUMÉ UPLOAD EXPERIMENT\n"
        f"Run: {run_dir}\n"
        "Will click visible résumé Upload + filechooser only.\n"
        "Will NOT upload cover letter, Continue, rotate, retry, or Submit.\n"
    )

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(args.profile_dir),
            headless=False,
            accept_downloads=False,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            with TimedPhase(metrics, "automation"):
                page.goto(inputs.apply_url, wait_until="domcontentloaded", timeout=60_000)
            wait_for_continue(
                run_dir,
                metrics,
                "CONTROLLED EXPERIMENT: confirm this is a FRESH SEEK apply session "
                "(not the previously stuck CSK tab).\n"
                "Sign in if needed. When the job page is ready, create OWNER_CONTINUE.\n"
                "Experiment will click Quick apply, then résumé Upload + filechooser only.\n"
                "No cover letter, Continue, rotation, or Submit.",
            )
            if not choose_documents_visible(page):
                try:
                    _click_apply_entry(page, metrics)
                    try:
                        page.wait_for_load_state("networkidle", timeout=15_000)
                    except Exception:  # noqa: BLE001
                        page.wait_for_timeout(3000)
                except FinalSubmitGuardError as error:
                    observation["apply_error"] = str(error)
                    _stop(observation, obs_path, outcome="fail", reason="apply_entry_blocked")
                    print(f"STOP: {error}")
                    wait_for_end_session(
                        run_dir,
                        metrics,
                        "Experiment could not enter apply. Create OWNER_END_SESSION to close.",
                    )
                    return 1
            page.wait_for_timeout(1500)
            if not choose_documents_visible(page):
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and not choose_documents_visible(page):
                    page.wait_for_timeout(500)
            result = run_experiment(page, cv_pdf=inputs.cv_pdf, run_dir=run_dir, observation=observation)
            print(json.dumps({
                "final_outcome": result.get("final_outcome"),
                "final_reason": result.get("final_reason"),
                "filechooser_event_observed": result.get("filechooser_event_observed"),
                "set_files_returned": result.get("set_files_returned"),
                "observation": str(obs_path),
            }, indent=2))
            wait_for_end_session(
                run_dir,
                metrics,
                "Experiment finished (no Continue / no Submit). Inspect the page, "
                "then create OWNER_END_SESSION to close the browser.",
            )
        finally:
            context.close()
    return 0 if observation.get("final_outcome") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
