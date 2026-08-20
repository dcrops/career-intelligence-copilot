"""AAS-0 Playwright assist runner — STOP before final submission.

Disposable spike. Not a production subsystem.

Live SEEK interaction requires explicit --authorize-live.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow `python spikes/aas0/run_assist.py` from repo root without install tricks
# beyond PYTHONPATH=src (documented in README).
_SPIKE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SPIKE_DIR.parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_SPIKE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR.parent))

from aas0.answer_policy import (  # noqa: E402
    AnswerDecision,
    KnownAnswers,
    is_default_resume_checkbox_label,
    merge_owner_extra,
    resolve_answer,
)
from aas0.default_checkbox_observation import (  # noqa: E402
    DEFAULT_CHECKBOX_OBSERVATION_FILENAME,
    STAGE_BEFORE_DOCUMENT_UPLOAD,
    STAGE_STRUCTURAL_DEFAULT_REOBSERVED,
)
from aas0.upload_observation import (  # noqa: E402
    STAGE_FIRST_CV_WAIT_FINAL,
    STAGE_RETRY_CV_WAIT_FINAL,
    UPLOAD_OBSERVATION_FILENAME,
)
from aas0.document_gates import (  # noqa: E402
    DocumentsStepGateError,
    evaluate_review_document_gate,
    filenames_equal,
    snapshot_has_filename,
)
from aas0.load_inputs import (  # noqa: E402
    DEFAULT_OPPORTUNITY_ID,
    DEFAULT_PROFILE_DIR,
    DEFAULT_RUNS_DIR,
    format_preflight_report,
    load_spike_inputs,
)
from aas0.metrics import SpikeMetrics, TimedPhase  # noqa: E402
from aas0.owner_gate import ask_question, wait_for_continue, wait_for_end_session  # noqa: E402
from aas0.resume_lifecycle import (  # noqa: E402
    SeekResumeSnapshot,
    application_cv_is_structural_default,
    detect_resume_capacity_message,
    evaluate_default_change,
)
from aas0.resume_rotation import (  # noqa: E402
    evaluate_rotation_decision,
    skips_as_metrics,
    wait_until_deletion_verified,
)
from aas0.seek_documents import (  # noqa: E402
    capture_default_checkbox_observation,
    capture_fingerprint,
    capture_upload_observation,
    choose_documents_visible,
    documents_step_ready_to_continue,
    dump_expected_cv_appeared_once,
    observe_resume_snapshot,
    observe_review_documents,
    page_body_text,
    prepare_and_upload_documents,
    record_resume_snapshot,
    resume_upload_spinner_active,
    confirm_expected_cv_for_application,
    attempt_one_resume_deletion,
    should_run_documents_stage,
    uncheck_default_checkbox_if_checked,
    ResumeUploadInteractionError,
    RESUME_UPLOAD_INTERACTION_FAILURES,
)
from aas0.session_handoff import (  # noqa: E402
    apply_owner_session_submission_observation,
    build_final_review_handoff,
)
from aas0.state_progress import (  # noqa: E402
    CoverLetterGateError,
    SameStateRetryGuard,
    is_final_review_page,
    looks_like_stepper_review_label,
)
from aas0.submit_guard import (  # noqa: E402
    ControlClass,
    FinalSubmitGuardError,
    PageSignals,
    assert_may_activate,
    classify_control,
)
from aas0.upload_artefacts import UnsafeUploadArtefactError  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AAS-0 application assistance spike (Seek-native; no final submit)."
    )
    parser.add_argument(
        "--opportunity-id",
        default=DEFAULT_OPPORTUNITY_ID,
        help="Packaged opportunity id (default: Repurpose It).",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate artefacts/truth/seeded answers and exit (no browser).",
    )
    parser.add_argument(
        "--authorize-live",
        action="store_true",
        help="Required to launch Playwright against the real application URL.",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=DEFAULT_PROFILE_DIR,
        help="Dedicated disposable/persistent Playwright Chromium profile.",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help="Directory for metrics JSON and screenshots.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=True,
        help="Run headed (default).",
    )
    parser.add_argument(
        "--manual-comparison-minutes",
        type=float,
        default=None,
        help="Optional owner estimate of fully-manual minutes for comparison.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    inputs = load_spike_inputs(args.opportunity_id)
    report = format_preflight_report(inputs)
    print(report)

    if inputs.blocking_warnings or not inputs.truth.external_use_allowed:
        blocking_truth = not inputs.truth.external_use_allowed
        print(
            "PREFLIGHT BLOCK: resolve blocking warnings with the owner before "
            "--authorize-live. Spike will not auto-regenerate documents.\n"
        )
        if args.preflight_only or not args.authorize_live:
            return 2 if (blocking_truth or inputs.blocking_warnings) else 0

    if args.preflight_only:
        print("Preflight complete. No browser launched.")
        return 0 if inputs.truth.external_use_allowed and not inputs.blocking_warnings else 2

    if not args.authorize_live:
        print(
            "Refusing to open SEEK: pass --authorize-live after owner authorization.\n"
            "Example:\n"
            "  python spikes/aas0/run_assist.py --authorize-live --opportunity-id "
            f"{args.opportunity_id}\n"
        )
        return 0

    if not inputs.truth.external_use_allowed:
        print("Refusing live run: external-use gate not allowed.")
        return 2

    if inputs.blocking_warnings:
        print("Refusing live run: blocking preflight warnings remain:")
        for warning in inputs.blocking_warnings:
            print(f"  - {warning}")
        return 2

    return run_live(args, inputs)


def run_live(args: argparse.Namespace, inputs) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is not installed. Install spike deps only:\n"
            "  pip install -r spikes/aas0/requirements-spike.txt\n"
            "  playwright install chromium\n"
        )
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.runs_dir / run_id
    shot_dir = run_dir / "screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    args.profile_dir.mkdir(parents=True, exist_ok=True)
    (args.runs_dir / "CURRENT_RUN.txt").write_text(str(run_dir) + "\n", encoding="utf-8")
    checkbox_dump = run_dir / DEFAULT_CHECKBOX_OBSERVATION_FILENAME
    upload_dump = run_dir / UPLOAD_OBSERVATION_FILENAME
    cv_appeared_dumped = [False]

    metrics = SpikeMetrics(opportunity_id=inputs.opportunity_id)
    metrics.expected_cv_filename = inputs.cv_pdf.name
    metrics.expected_cover_letter_filename = inputs.cover_letter_pdf.name
    metrics.add_note(
        "LIMITATION: SEEK-native application assistance experiment "
        "(not general ATS)."
    )
    metrics.add_note(f"apply_url={inputs.apply_url}")
    if args.manual_comparison_minutes is not None:
        metrics.add_note(
            f"owner_manual_comparison_minutes={args.manual_comparison_minutes}"
        )

    known: KnownAnswers = inputs.known
    reusable_candidates: list[dict[str, str]] = []

    print(
        "\nLIVE SPIKE STARTING\n"
        f"Profile: {args.profile_dir}\n"
        "Log into SEEK manually in the opened window if prompted.\n"
        "Spike will NEVER click final Submit.\n"
        "If CAPTCHA / hostile flow appears: STOP and report — do not switch targets.\n"
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
                metrics.pages_traversed += 1
            _screenshot(page, shot_dir, "01_initial", metrics)

            # Allow owner login / dismiss banners (file gate — no stdin required).
            wait_for_continue(
                run_dir,
                metrics,
                "If SEEK requires login or shows a blocker, complete it in the "
                "Playwright Chromium window now.\n"
                "When the SEEK job page is ready (signed in if needed), "
                "create OWNER_CONTINUE in this run directory (agent can do this "
                "when you say continue).",
            )

            with TimedPhase(metrics, "automation"):
                _click_apply_entry(page, metrics)
                metrics.pages_traversed += 1
                # SEEK Quick apply often loads the form asynchronously.
                try:
                    page.wait_for_load_state("networkidle", timeout=15_000)
                except Exception:  # noqa: BLE001
                    page.wait_for_timeout(3000)
                try:
                    page.locator(
                        "input:not([type=hidden]), textarea, select, input[type=file]"
                    ).first.wait_for(state="visible", timeout=20_000)
                except Exception as error:  # noqa: BLE001
                    metrics.add_note(f"form_fields_not_visible_after_apply: {error}")
                    page.wait_for_timeout(2000)

            _screenshot(page, shot_dir, "02_after_apply_entry", metrics)

            same_state = SameStateRetryGuard(max_failures=2)

            # Main assist loop — limited iterations; SEEK-specific hardcoding OK.
            handoff_done = False
            resume_before_snapshot: SeekResumeSnapshot | None = None
            resume_before_captured = False
            documents_stage_complete = False
            for step in range(1, 8):
                if _page_looks_like_final_review(page):
                    _handoff_final_review(
                        page=page,
                        run_dir=run_dir,
                        shot_dir=shot_dir,
                        metrics=metrics,
                        step=step,
                        expected_cv_filename=inputs.cv_pdf.name,
                        expected_cover_letter_filename=inputs.cover_letter_pdf.name,
                    )
                    handoff_done = True
                    break

                documents_page = should_run_documents_stage(
                    ui_visible=choose_documents_visible(page),
                    stage_complete=documents_stage_complete,
                )
                documents_verified_this_step = False

                if documents_page and not resume_before_captured:
                    resume_before_snapshot = observe_resume_snapshot(page)
                    record_resume_snapshot(
                        metrics, resume_before_snapshot, stage="before"
                    )
                    capture_default_checkbox_observation(
                        page,
                        path=checkbox_dump,
                        stage=STAGE_BEFORE_DOCUMENT_UPLOAD,
                        expected_cv_filename=inputs.cv_pdf.name,
                        snapshot=resume_before_snapshot,
                    )
                    resume_before_captured = True

                uploaded = False
                with TimedPhase(metrics, "automation"):
                    filled = _assist_visible_fields(page, known, metrics)
                    if documents_page:
                        try:
                            uploaded = prepare_and_upload_documents(
                                page,
                                cv_pdf=inputs.cv_pdf,
                                cl_pdf=inputs.cover_letter_pdf,
                                metrics=metrics,
                                upload_diagnostic_path=upload_dump,
                            )
                        except ResumeUploadInteractionError as error:
                            metrics.upload_failure_reason = error.reason
                            metrics.add_failure(str(error))
                            if error.reason == "resume_capacity_blocked":
                                cap_snapshot = observe_resume_snapshot(page)
                                record_resume_snapshot(
                                    metrics, cap_snapshot, stage="after_upload"
                                )
                                _screenshot(
                                    page,
                                    shot_dir,
                                    f"0{step + 2}_resume_capacity",
                                    metrics,
                                )
                                recovered = _recover_or_stop_after_resume_upload_failure(
                                    page=page,
                                    run_dir=run_dir,
                                    shot_dir=shot_dir,
                                    metrics=metrics,
                                    snapshot=cap_snapshot,
                                    expected_cv=inputs.cv_pdf.name,
                                    observed_selected=cap_snapshot.selected_filename,
                                    upload_failure_reason="resume_capacity_blocked",
                                    stage="stopped_resume_capacity",
                                    cv_pdf=inputs.cv_pdf,
                                    cl_pdf=inputs.cover_letter_pdf,
                                    step=step,
                                    diagnostic_path=checkbox_dump,
                                    diagnostic_cv_appeared=cv_appeared_dumped,
                                    upload_diagnostic_path=upload_dump,
                                )
                                if recovered:
                                    continue
                                handoff_done = True
                                break
                            _screenshot(
                                page, shot_dir, "99_resume_upload_interaction", metrics
                            )
                            _stop_for_owner_inspection(
                                page=page,
                                run_dir=run_dir,
                                shot_dir=shot_dir,
                                metrics=metrics,
                                reason=(
                                    "AAS-0.1 STOP: résumé Upload filechooser "
                                    f"failed ({error.reason}). No hidden-input "
                                    "fallback. Browser left open for inspection."
                                ),
                                stage="stopped_resume_upload_interaction",
                            )
                            handoff_done = True
                            break
                        except UnsafeUploadArtefactError as error:
                            metrics.final_stage_reached = "stopped_unsafe_upload"
                            metrics.add_failure(str(error))
                            _screenshot(page, shot_dir, "99_unsafe_upload", metrics)
                            _stop_for_owner_inspection(
                                page=page,
                                run_dir=run_dir,
                                shot_dir=shot_dir,
                                metrics=metrics,
                                reason=(
                                    "AAS-0.1 STOP: refused to upload an internal or "
                                    "non-export PDF. Browser left open for inspection."
                                ),
                                stage="stopped_unsafe_upload",
                            )
                            handoff_done = True
                            break

                if documents_page:
                    cv_wait = confirm_expected_cv_for_application(
                        page,
                        expected_cv_filename=inputs.cv_pdf.name,
                        metrics=metrics,
                        diagnostic_path=checkbox_dump,
                        diagnostic_cv_appeared=cv_appeared_dumped,
                        upload_diagnostic_path=upload_dump,
                        upload_wait_phase="first",
                    )
                    after_snapshot = observe_resume_snapshot(page)
                    record_resume_snapshot(
                        metrics, after_snapshot, stage="after_upload"
                    )
                    capture_default_checkbox_observation(
                        page,
                        path=checkbox_dump,
                        stage=STAGE_STRUCTURAL_DEFAULT_REOBSERVED,
                        expected_cv_filename=inputs.cv_pdf.name,
                        snapshot=after_snapshot,
                    )
                    if cv_wait.action == "stop":
                        _screenshot(
                            page, shot_dir, f"0{step + 2}_cv_selection", metrics
                        )
                        recovered = _recover_or_stop_after_resume_upload_failure(
                            page=page,
                            run_dir=run_dir,
                            shot_dir=shot_dir,
                            metrics=metrics,
                            snapshot=after_snapshot,
                            expected_cv=inputs.cv_pdf.name,
                            observed_selected=cv_wait.observed_selected,
                            upload_failure_reason=cv_wait.reason,
                            stage="stopped_cv_selection",
                            cv_pdf=inputs.cv_pdf,
                            cl_pdf=inputs.cover_letter_pdf,
                            step=step,
                            diagnostic_path=checkbox_dump,
                            diagnostic_cv_appeared=cv_appeared_dumped,
                            upload_diagnostic_path=upload_dump,
                        )
                        if recovered:
                            continue
                        handoff_done = True
                        break
                    dump_expected_cv_appeared_once(
                        page,
                        path=checkbox_dump,
                        expected_cv_filename=inputs.cv_pdf.name,
                        dumped_flag=cv_appeared_dumped,
                    )
                    if not _protect_default_after_expected_cv(
                        page=page,
                        run_dir=run_dir,
                        shot_dir=shot_dir,
                        metrics=metrics,
                        expected_cv_filename=inputs.cv_pdf.name,
                        resume_before_snapshot=resume_before_snapshot,
                        checkbox_dump=checkbox_dump,
                        upload_dump=upload_dump,
                        step=step,
                        upload_wait_phase="first",
                    ):
                        handoff_done = True
                        break

                capacity = None
                if documents_page:
                    capacity = detect_resume_capacity_message(page_body_text(page))
                expected_cv_ok = metrics.cv_selection_reason == "expected_cv_selected"
                if (
                    (capacity or metrics.resume_capacity_blocked)
                    and not expected_cv_ok
                    and not metrics.resume_rotation_attempted
                ):
                    metrics.resume_capacity_blocked = True
                    metrics.resume_capacity_evidence = (
                        metrics.resume_capacity_evidence or capacity or ""
                    )
                    cap_snapshot = observe_resume_snapshot(page)
                    record_resume_snapshot(
                        metrics, cap_snapshot, stage="after_upload"
                    )
                    _screenshot(page, shot_dir, f"0{step + 2}_resume_capacity", metrics)
                    recovered = _recover_or_stop_after_resume_upload_failure(
                        page=page,
                        run_dir=run_dir,
                        shot_dir=shot_dir,
                        metrics=metrics,
                        snapshot=cap_snapshot,
                        expected_cv=inputs.cv_pdf.name,
                        observed_selected=cap_snapshot.selected_filename,
                        upload_failure_reason="resume_capacity_blocked",
                        stage="stopped_resume_capacity",
                        cv_pdf=inputs.cv_pdf,
                        cl_pdf=inputs.cover_letter_pdf,
                        step=step,
                        diagnostic_path=checkbox_dump,
                        diagnostic_cv_appeared=cv_appeared_dumped,
                        upload_diagnostic_path=upload_dump,
                    )
                    if recovered:
                        continue
                    handoff_done = True
                    break

                if filled or uploaded:
                    _screenshot(page, shot_dir, f"0{step + 2}_autofilled", metrics)

                # Pause for any remaining empty required-looking questions.
                with TimedPhase(metrics, "automation"):
                    pending = _collect_unanswered_labels(page, known)

                if pending:
                    _screenshot(page, shot_dir, f"0{step + 2}_unknown_pause", metrics)
                    for label, options in pending:
                        answer, persist = ask_question(
                            run_dir, metrics, label, options
                        )
                        known = merge_owner_extra(known, label, answer)
                        if persist:
                            reusable_candidates.append(
                                {"question": label, "answer": answer}
                            )
                        with TimedPhase(metrics, "automation"):
                            _fill_by_label(page, label, answer, metrics, outcome="owner")

                # Gate Choose Documents Continue on selected CV + cover letter.
                if documents_page:
                    try:
                        documents_snapshot = observe_resume_snapshot(page)
                        documents_step_ready_to_continue(
                            page,
                            expected_cv_filename=inputs.cv_pdf.name,
                            snapshot=documents_snapshot,
                            spinner_active=resume_upload_spinner_active(page),
                        )
                        documents_verified_this_step = (
                            metrics.cv_selection_reason == "expected_cv_selected"
                        )
                    except DocumentsStepGateError as error:
                        metrics.cv_selection_reason = error.reason
                        metrics.add_failure(str(error))
                        _screenshot(
                            page, shot_dir, f"0{step + 2}_cv_continue_gate", metrics
                        )
                        if error.reason == "expected_cv_is_structural_default":
                            owner_reason = (
                                "AAS-0.1 STOP: expected application CV is also "
                                "the structural Default. Restore "
                                "'David Cropper - AI Engineer CV.pdf' as Default "
                                "in the Playwright window without changing the "
                                "selected application CV. Automation will not "
                                "restore Default by selecting another résumé "
                                "and will not Submit."
                            )
                        else:
                            owner_reason = (
                                "AAS-0.1 STOP: Choose Documents Continue refused.\n"
                                f"{error}\n"
                                "Automation will not Continue or Submit."
                            )
                        _stop_for_owner_inspection(
                            page=page,
                            run_dir=run_dir,
                            shot_dir=shot_dir,
                            metrics=metrics,
                            reason=owner_reason,
                            stage="stopped_default_checkbox"
                            if error.reason == "expected_cv_is_structural_default"
                            else "stopped_cv_selection",
                        )
                        handoff_done = True
                        break
                    except CoverLetterGateError as error:
                        metrics.add_failure(str(error))
                        same_state.failures += 1
                        metrics.add_note(
                            f"documents_gate_blocked (failure "
                            f"{same_state.failures}/{same_state.max_failures}): {error}"
                        )
                        _screenshot(
                            page, shot_dir, f"0{step + 2}_documents_gate", metrics
                        )
                        if same_state.failures >= same_state.max_failures:
                            metrics.final_stage_reached = "owner_pause_same_state"
                            wait_for_continue(
                                run_dir,
                                metrics,
                                "AAS-0 STOP / OWNER PAUSE: Choose Documents did not become "
                                "ready after 2 attempts (cover-letter radio/validation).\n"
                                "Fix the cover-letter selection in the browser if possible, "
                                "then create OWNER_CONTINUE to retry once — or Ctrl+C / close "
                                "to abort. Spike will not loop Continue blindly.",
                            )
                            same_state.failures = 0
                        continue

                before = capture_fingerprint(page)
                clicked = False
                with TimedPhase(metrics, "automation"):
                    clicked = _try_advance_navigation(page, metrics, run_dir)
                if not clicked:
                    if _page_looks_like_final_review(page):
                        _handoff_final_review(
                            page=page,
                            run_dir=run_dir,
                            shot_dir=shot_dir,
                            metrics=metrics,
                            step=step,
                            expected_cv_filename=inputs.cv_pdf.name,
                            expected_cover_letter_filename=inputs.cover_letter_pdf.name,
                        )
                        handoff_done = True
                        break
                    metrics.add_note(
                        f"Loop step {step}: no further safe navigation; stopping."
                    )
                    metrics.final_stage_reached = (
                        metrics.final_stage_reached or "stopped_mid_flow"
                    )
                    _screenshot(page, shot_dir, "99_stopped", metrics)
                    break

                page.wait_for_timeout(1200)
                after = capture_fingerprint(page)
                outcome = same_state.record(before, after)
                metrics.add_note(
                    f"continue_outcome={outcome} "
                    f"before_step={before.step_label!r} after_step={after.step_label!r} "
                    f"validation={after.validation_messages!r}"
                )
                if outcome == "advanced":
                    metrics.pages_traversed += 1
                    _screenshot(page, shot_dir, f"0{step + 2}_advanced", metrics)
                    if documents_verified_this_step:
                        documents_stage_complete = True
                        metrics.add_note(
                            "documents_stage_complete: Continue advanced; "
                            "will not re-enter résumé upload/confirm/rotation"
                        )
                    # If advance landed on final review, hand off immediately.
                    if _page_looks_like_final_review(page):
                        _handoff_final_review(
                            page=page,
                            run_dir=run_dir,
                            shot_dir=shot_dir,
                            metrics=metrics,
                            step=step,
                            expected_cv_filename=inputs.cv_pdf.name,
                            expected_cover_letter_filename=inputs.cover_letter_pdf.name,
                        )
                        handoff_done = True
                        break
                    continue
                if outcome == "retry":
                    metrics.add_failure(
                        "Continue click did not advance application state "
                        f"(attempt {same_state.failures}/{same_state.max_failures})"
                    )
                    _screenshot(page, shot_dir, f"0{step + 2}_no_advance", metrics)
                    continue
                # stop
                metrics.final_stage_reached = "owner_pause_same_state"
                _screenshot(page, shot_dir, "99_same_state_stop", metrics)
                wait_for_continue(
                    run_dir,
                    metrics,
                    "AAS-0 STOP / OWNER PAUSE: Continue did not change application "
                    "state after 2 attempts (likely cover-letter / validation).\n"
                    "Inspect the Playwright window, then create OWNER_CONTINUE to "
                    "acknowledge and end this assist loop, or abort the process.",
                )
                metrics.add_note("Owner acknowledged same-state stop")
                break
            else:
                if not handoff_done:
                    metrics.final_stage_reached = metrics.final_stage_reached or "max_steps"
                    _screenshot(page, shot_dir, "99_max_steps", metrics)

        except FinalSubmitGuardError as error:
            metrics.add_failure(str(error))
            metrics.final_stage_reached = "guard_blocked"
            try:
                _screenshot(page, shot_dir, "99_guard_block", metrics)
            except Exception:  # noqa: BLE001
                pass
            print(f"\nGUARD STOP: {error}\n")
        except UnsafeUploadArtefactError as error:
            metrics.add_failure(str(error))
            metrics.final_stage_reached = metrics.final_stage_reached or "stopped_unsafe_upload"
            try:
                _screenshot(page, shot_dir, "99_unsafe_upload", metrics)
            except Exception:  # noqa: BLE001
                pass
            print(f"\nUNSAFE UPLOAD STOP: {error}\n")
        except KeyboardInterrupt:
            metrics.add_failure("owner_interrupted")
            metrics.final_stage_reached = "interrupted"
            print("\nInterrupted by owner.\n")
        except Exception as error:  # noqa: BLE001 — record spike runtime failures
            metrics.add_failure(f"runtime_error: {error}")
            metrics.final_stage_reached = metrics.final_stage_reached or "runtime_error"
            try:
                _screenshot(page, shot_dir, "99_runtime_error", metrics)
            except Exception:  # noqa: BLE001
                pass
            print(f"\nRUNTIME STOP: {error}\n")
        finally:
            metrics.submit_clicked = False
            metrics_path = run_dir / "metrics.json"
            metrics.write_json(metrics_path)
            if reusable_candidates:
                (run_dir / "reusable_answer_candidates.json").write_text(
                    json.dumps(reusable_candidates, indent=2) + "\n",
                    encoding="utf-8",
                )
            print(json.dumps(metrics.to_dict()["timing"], indent=2))
            print(f"\nMetrics written: {metrics_path}")
            print(
                "CONFIRMATION: submit_clicked=false "
                f"(application_submission={metrics.application_submission})."
            )
            # Close only after owner end-session handoff (or error paths without handoff).
            context.close()

    return 0


def _protect_default_after_expected_cv(
    *,
    page,
    run_dir: Path,
    shot_dir: Path,
    metrics: SpikeMetrics,
    expected_cv_filename: str,
    resume_before_snapshot: SeekResumeSnapshot | None,
    checkbox_dump: Path | None,
    upload_dump: Path | None,
    step: int,
    upload_wait_phase: str,
) -> bool:
    """Uncheck auto-Default after expected CV is selected. False means STOP."""
    baseline_filename = (
        None
        if resume_before_snapshot is None
        else resume_before_snapshot.default_filename
    )
    baseline_observable = (
        False
        if resume_before_snapshot is None
        else resume_before_snapshot.default_observable
    )
    if baseline_filename is None:
        baseline_filename = metrics.default_resume_before
        baseline_observable = metrics.default_observable_before
    checkbox = uncheck_default_checkbox_if_checked(
        page,
        metrics,
        diagnostic_path=checkbox_dump,
        expected_cv_filename=expected_cv_filename,
        baseline_default_filename=baseline_filename,
        baseline_default_observable=baseline_observable,
    )
    metrics.default_checkbox_reason = checkbox.reason
    metrics.default_checkbox_still_checked = checkbox.still_checked
    capture_default_checkbox_observation(
        page,
        path=checkbox_dump,
        stage=STAGE_STRUCTURAL_DEFAULT_REOBSERVED,
        expected_cv_filename=expected_cv_filename,
        was_checked=checkbox.was_checked,
        uncheck_attempted=checkbox.uncheck_attempted,
        uncheck_returned=checkbox.uncheck_returned,
        uncheck_threw=checkbox.uncheck_threw,
        uncheck_exception_type=checkbox.uncheck_exception_type,
        uncheck_exception_message=checkbox.uncheck_exception_message,
        checkbox_enabled=checkbox.checkbox_enabled,
        baseline_default_filename=checkbox.baseline_default_filename,
        settle_poll_count=checkbox.settle_poll_count,
        settle_wait_ms=checkbox.settle_wait_ms,
        guard=checkbox,
    )
    settled = observe_resume_snapshot(page)
    wait_stage = (
        STAGE_RETRY_CV_WAIT_FINAL
        if upload_wait_phase == "retry"
        else STAGE_FIRST_CV_WAIT_FINAL
    )
    capture_upload_observation(
        page,
        path=upload_dump,
        stage=wait_stage,
        expected_cv_filename=expected_cv_filename,
        retry_cv=upload_wait_phase == "retry",
        snapshot=settled,
        default_before_upload=baseline_filename,
        default_after_upload=settled.default_filename,
        default_after_uncheck_settle=settled.default_filename,
    )
    if checkbox.should_stop:
        locked = checkbox.reason == "structural_default_checkbox_locked"
        if locked:
            metrics.add_failure(
                "SEEK Default checkbox is checked and disabled on the "
                "committed structural Default. Not unchecking and not "
                f"transferring Default. reason={checkbox.reason}"
            )
            owner_reason = (
                "AAS-0.1 STOP: Make this my default résumé is checked "
                "and disabled because the selected application CV is the "
                "committed structural Default. Automation will not uncheck "
                "a disabled control, will not transfer Default onto another "
                "résumé, and will not Submit. Restore "
                "'David Cropper - AI Engineer CV.pdf' as Default in the "
                "Playwright window, leaving the application CV selected."
            )
        else:
            metrics.add_failure(
                "SEEK Default checkbox remained checked after uncheck. "
                "Not restoring Default automatically. "
                f"reason={checkbox.reason}"
            )
            owner_reason = (
                "AAS-0.1 STOP: Make this my default résumé stayed "
                "checked after uncheck. Automation will not restore "
                "Default and will not Submit. Uncheck or restore the "
                "recruiter-discovery résumé in the Playwright window "
                "if needed."
            )
        _screenshot(page, shot_dir, f"0{step + 2}_default_checkbox", metrics)
        _stop_for_owner_inspection(
            page=page,
            run_dir=run_dir,
            shot_dir=shot_dir,
            metrics=metrics,
            reason=owner_reason,
            stage="stopped_default_checkbox",
        )
        return False
    if resume_before_snapshot is not None:
        change = evaluate_default_change(resume_before_snapshot, settled)
        metrics.default_change_reason = change.reason
        metrics.add_note(
            f"default_change reason={change.reason} "
            f"before={change.before!r} after={change.after!r} "
            f"should_stop={change.should_stop}"
        )
        if change.should_stop:
            metrics.default_changed_unexpected = True
            metrics.add_failure(
                "Unexpected SEEK Default résumé change: "
                f"{change.before!r} → {change.after!r} "
                f"({change.reason}). Not restoring automatically."
            )
            _screenshot(page, shot_dir, f"0{step + 2}_default_changed", metrics)
            _stop_for_owner_inspection(
                page=page,
                run_dir=run_dir,
                shot_dir=shot_dir,
                metrics=metrics,
                reason=(
                    "AAS-0.1 STOP: SEEK Default résumé changed "
                    "unexpectedly. Automation will not restore it "
                    "and will not Submit. Inspect the Playwright "
                    "window; restore Default manually if needed."
                ),
                stage="stopped_default_changed",
            )
            return False
    elif baseline_filename and not filenames_equal(
        baseline_filename, settled.default_filename
    ):
        metrics.default_changed_unexpected = True
        metrics.add_failure(
            "Unexpected SEEK Default résumé change: "
            f"{baseline_filename!r} → {settled.default_filename!r}. "
            "Not restoring automatically."
        )
        _screenshot(page, shot_dir, f"0{step + 2}_default_changed", metrics)
        _stop_for_owner_inspection(
            page=page,
            run_dir=run_dir,
            shot_dir=shot_dir,
            metrics=metrics,
            reason=(
                "AAS-0.1 STOP: SEEK Default résumé changed unexpectedly. "
                "Automation will not restore it and will not Submit."
            ),
            stage="stopped_default_changed",
        )
        return False
    return True


def _recover_or_stop_after_resume_upload_failure(
    *,
    page,
    run_dir: Path,
    shot_dir: Path,
    metrics: SpikeMetrics,
    snapshot: SeekResumeSnapshot,
    expected_cv: str,
    observed_selected: str | None,
    upload_failure_reason: str,
    stage: str,
    cv_pdf: Path,
    cl_pdf: Path,
    step: int,
    diagnostic_path: Path | None = None,
    diagnostic_cv_appeared: list[bool] | None = None,
    upload_diagnostic_path: Path | None = None,
) -> bool:
    """One legal Delete, verify, retry expected CV once. True if the loop may continue."""
    failure_reason = upload_failure_reason
    if failure_reason in RESUME_UPLOAD_INTERACTION_FAILURES:
        metrics.upload_failure_reason = failure_reason
        metrics.add_failure(
            "Résumé Upload filechooser failed; not rotating. "
            f"upload_failure_reason={failure_reason}"
        )
        _stop_for_owner_inspection(
            page=page,
            run_dir=run_dir,
            shot_dir=shot_dir,
            metrics=metrics,
            reason=(
                "AAS-0.1 STOP: résumé Upload filechooser failed "
                f"({failure_reason}). No hidden-input fallback."
            ),
            stage="stopped_resume_upload_interaction",
        )
        return False
    capacity = detect_resume_capacity_message(page_body_text(page))
    if capacity:
        metrics.resume_capacity_blocked = True
        metrics.resume_capacity_evidence = (
            metrics.resume_capacity_evidence or capacity
        )
        failure_reason = "resume_capacity_blocked"
    metrics.upload_failure_reason = failure_reason
    metrics.resume_default_before_deletion = snapshot.default_filename
    decision = evaluate_rotation_decision(
        entries=snapshot.entries,
        upload_failure_reason=failure_reason,
        rotation_already_attempted=metrics.resume_rotation_attempted,
        default_observable_before=snapshot.default_observable,
        expected_cv_present=snapshot_has_filename(snapshot, expected_cv),
    )
    metrics.resume_rotation_reason = decision.reason
    metrics.cleanup_candidate = decision.candidate.filename
    metrics.cleanup_candidate_reason = decision.candidate.reason
    metrics.cleanup_skips = skips_as_metrics(decision.skips)
    skip_lines = "; ".join(
        f"{skip.filename} ({skip.reason})" for skip in decision.skips[:8]
    )

    def _stop(reason: str, *, deletion_status: str = "") -> bool:
        metrics.add_failure(
            "Expected CV upload failed; bounded rotation stopped. "
            f"upload_failure_reason={failure_reason} "
            f"rotation_reason={reason} "
            f"candidate={decision.candidate.filename!r} "
            f"deletion_status={deletion_status or reason} "
            f"observed_selected={observed_selected!r}"
        )
        _stop_for_owner_inspection(
            page=page,
            run_dir=run_dir,
            shot_dir=shot_dir,
            metrics=metrics,
            reason=(
                "AAS-0.1 STOP: expected CV is not the selected application "
                "résumé; bounded rotation did not complete.\n"
                f"expected={expected_cv!r}\n"
                f"observed_selected={observed_selected!r}\n"
                f"upload_failure_reason={failure_reason}\n"
                f"rotation_reason={reason}\n"
                f"safe_candidate={decision.candidate.filename!r} "
                f"({decision.candidate.reason})\n"
                f"default_before={snapshot.default_filename!r}\n"
                f"default_after_deletion="
                f"{metrics.resume_default_after_deletion!r}\n"
                f"deleted_filename={metrics.resume_deleted_filename!r}\n"
                f"deletion_status={deletion_status or reason}\n"
                f"retry_attempted={metrics.resume_rotation_retry_attempted}\n"
                f"retry_outcome={metrics.resume_rotation_retry_outcome}\n"
                f"skipped={skip_lines or 'none'}\n"
                "Automation will not Continue or Submit with the wrong CV. "
                "Browser left open."
            ),
            stage=stage,
        )
        return False

    if decision.action != "attempt_delete":
        metrics.resume_rotation_attempted = True
        return _stop(decision.reason)

    metrics.resume_rotation_attempted = True
    deletion_status = attempt_one_resume_deletion(
        page,
        candidate_filename=decision.candidate.filename,
        candidate_index=decision.candidate.index,
        metrics=metrics,
        diagnostic_path=run_dir / "delete_confirmation_observation.json",
    )
    _screenshot(page, shot_dir, f"0{step + 2}_resume_delete", metrics)
    if deletion_status == "resume_delete_confirmation_unobserved":
        return _stop(
            "resume_delete_confirmation_unobserved",
            deletion_status=deletion_status,
        )
    if deletion_status != "clicked_delete":
        return _stop(deletion_status, deletion_status=deletion_status)

    metrics.resume_list_count_before = len(snapshot.entries)
    metrics.resume_deleted_filename = decision.candidate.filename

    def _wait_for_inventory(ms: int) -> None:
        metrics.add_waiting(ms / 1000.0)
        page.wait_for_timeout(ms)

    waited = wait_until_deletion_verified(
        lambda: observe_resume_snapshot(page),
        before=snapshot,
        deleted_filename=decision.candidate.filename or "",
        deleted_index=decision.candidate.index,
        wait=_wait_for_inventory,
    )
    after_delete = waited.snapshot
    record_resume_snapshot(metrics, after_delete, stage="after_upload")
    metrics.resume_default_after_deletion = after_delete.default_filename
    metrics.resume_delete_verification_poll_count = waited.poll_count
    metrics.resume_delete_verification_wait_ms = waited.elapsed_ms
    metrics.resume_delete_verification_reason = waited.reason
    metrics.resume_list_count_after_deletion = len(after_delete.entries)
    metrics.add_note(
        "resume_delete_verification "
        f"action={waited.action} reason={waited.reason} "
        f"polls={waited.poll_count} wait_ms={waited.elapsed_ms} "
        f"count_before={len(snapshot.entries)} "
        f"count_after={len(after_delete.entries)} "
        f"candidate={decision.candidate.filename!r} "
        f"index={decision.candidate.index} "
        f"default_before={snapshot.default_filename!r} "
        f"default_after={after_delete.default_filename!r}"
    )
    if waited.action != "verified":
        metrics.resume_rotation_reason = waited.reason
        if waited.reason == "default_changed_after_deletion":
            metrics.default_changed_unexpected = True
            metrics.default_change_reason = waited.reason
        return _stop(waited.reason, deletion_status="clicked_delete")

    metrics.resume_rotation_retry_attempted = True
    try:
        prepare_and_upload_documents(
            page,
            cv_pdf=cv_pdf,
            cl_pdf=cl_pdf,
            metrics=metrics,
            retry_cv=True,
            upload_diagnostic_path=upload_diagnostic_path,
        )
        dump_expected_cv_appeared_once(
            page,
            path=diagnostic_path,
            expected_cv_filename=expected_cv,
            dumped_flag=diagnostic_cv_appeared,
        )
    except Exception as error:  # noqa: BLE001
        metrics.resume_rotation_retry_outcome = f"retry_upload_failed:{error}"
        return _stop(
            "retry_failed_no_second_deletion",
            deletion_status="clicked_delete",
        )
    cv_wait = confirm_expected_cv_for_application(
        page,
        expected_cv_filename=expected_cv,
        metrics=metrics,
        diagnostic_path=diagnostic_path,
        diagnostic_cv_appeared=diagnostic_cv_appeared,
        upload_diagnostic_path=upload_diagnostic_path,
        upload_wait_phase="retry",
    )
    _screenshot(page, shot_dir, f"0{step + 2}_retry_cv_wait_final", metrics)
    retry_selected = cv_wait.action != "stop" and cv_wait.selected
    metrics.resume_rotation_retry_outcome = cv_wait.reason
    if not retry_selected:
        metrics.resume_rotation_reason = "retry_failed_no_second_deletion"
        return _stop(
            "retry_failed_no_second_deletion",
            deletion_status="clicked_delete",
        )
    if not _protect_default_after_expected_cv(
        page=page,
        run_dir=run_dir,
        shot_dir=shot_dir,
        metrics=metrics,
        expected_cv_filename=expected_cv,
        resume_before_snapshot=None,
        checkbox_dump=diagnostic_path,
        upload_dump=upload_diagnostic_path,
        step=step,
        upload_wait_phase="retry",
    ):
        metrics.resume_rotation_retry_outcome = "retry_default_protection_failed"
        return False
    metrics.resume_rotation_reason = "retry_expected_cv_selected"
    metrics.add_note(
        "Bounded résumé rotation recovered: deleted "
        f"{decision.candidate.filename!r} and expected CV is selected."
    )
    return True


def _record_owner_submission_observation(page, metrics: SpikeMetrics) -> None:
    """Passive observation after OWNER_END_SESSION. Never clicks Submit."""
    try:
        body = page.locator("body").inner_text(timeout=5000)
    except Exception:  # noqa: BLE001
        body = ""
    observation = apply_owner_session_submission_observation(
        metrics,
        body_text=body,
        url=getattr(page, "url", "") or "",
    )
    metrics.add_note(
        f"post_owner_submission_observation status={observation.status} "
        f"evidence={observation.evidence!r}"
    )


def _stop_for_owner_inspection(
    *,
    page,
    run_dir: Path,
    shot_dir: Path,
    metrics: SpikeMetrics,
    reason: str,
    stage: str,
) -> None:
    """Stop automation, keep browser open, never Submit. No speculative recovery."""
    metrics.final_stage_reached = stage
    metrics.browser_kept_open_for_owner = True
    metrics.submit_clicked = False
    metrics.application_submission = "not_completed"
    metrics.add_note(reason)
    print(f"\n=== AAS-0.1 OWNER INSPECTION ===\n{reason}\n")
    wait_for_end_session(
        run_dir,
        metrics,
        f"{reason}\n"
        "Automation will NOT click Submit application and will NOT restore "
        "the SEEK Default résumé.\n"
        f"Create OWNER_END_SESSION under:\n  {run_dir}\n"
        "when finished inspecting (or after you have corrected Default).",
    )
    _record_owner_submission_observation(page, metrics)
    try:
        _screenshot(page, shot_dir, "99_owner_inspection_end", metrics)
    except Exception:  # noqa: BLE001
        pass


def _handoff_final_review(
    *,
    page,
    run_dir: Path,
    shot_dir: Path,
    metrics: SpikeMetrics,
    step: int,
    expected_cv_filename: str,
    expected_cover_letter_filename: str,
) -> None:
    """Stop at Review only when both expected export filenames are visible."""
    observation = observe_review_documents(page)
    gate = evaluate_review_document_gate(
        expected_cv=expected_cv_filename,
        expected_cover_letter=expected_cover_letter_filename,
        observation=observation,
    )
    metrics.record_review_document_gate(
        observed_cv=gate.observed_cv,
        observed_cover_letter=gate.observed_cover_letter,
        reason=gate.reason,
    )
    metrics.add_note(
        f"review_documents reason={gate.reason} "
        f"expected_cv={gate.expected_cv!r} observed_cv={gate.observed_cv!r} "
        f"expected_cl={gate.expected_cover_letter!r} "
        f"observed_cl={gate.observed_cover_letter!r}"
    )
    if gate.should_stop:
        metrics.add_failure(
            "Review documents do not match expected export artefacts: "
            f"reason={gate.reason} "
            f"expected_cv={gate.expected_cv!r} observed_cv={gate.observed_cv!r} "
            f"expected_cl={gate.expected_cover_letter!r} "
            f"observed_cl={gate.observed_cover_letter!r}"
        )
        _screenshot(page, shot_dir, f"0{step + 2}_review_mismatch", metrics)
        _stop_for_owner_inspection(
            page=page,
            run_dir=run_dir,
            shot_dir=shot_dir,
            metrics=metrics,
            reason=(
                "AAS-0.1 STOP: SEEK Review does not show the expected documents.\n"
                f"expected CV: {gate.expected_cv!r}\n"
                f"observed CV: {gate.observed_cv!r}\n"
                f"expected cover letter: {gate.expected_cover_letter!r}\n"
                f"observed cover letter: {gate.observed_cover_letter!r}\n"
                f"reason: {gate.reason}\n"
                "APPLICATION READY FOR OWNER was not declared. "
                "Automation will not Submit."
            ),
            stage="stopped_review_documents",
        )
        return

    submit_visible = _detect_final_submit_visible(page, metrics)
    handoff = build_final_review_handoff(final_submit_control_visible=submit_visible)
    metrics.final_stage_reached = "review_or_confirmation"
    metrics.browser_kept_open_for_owner = handoff.browser_kept_open_for_owner
    metrics.submit_clicked = False
    metrics.application_submission = "not_completed"
    handoff_snapshot = observe_resume_snapshot(page)
    record_resume_snapshot(metrics, handoff_snapshot, stage="handoff")
    if (
        metrics.default_observable_before
        and metrics.default_observable_at_handoff
        and metrics.default_resume_before
        and metrics.default_resume_at_handoff
        and metrics.default_resume_before.casefold()
        != metrics.default_resume_at_handoff.casefold()
    ):
        metrics.default_changed_unexpected = True
        metrics.default_change_reason = "default_filename_changed_at_handoff"
        metrics.add_failure(
            "Unexpected SEEK Default résumé change at Review handoff: "
            f"{metrics.default_resume_before!r} → "
            f"{metrics.default_resume_at_handoff!r}. Not restoring automatically."
        )
    _screenshot(page, shot_dir, f"0{step + 2}_final_review", metrics)
    metrics.add_note(
        "AUTOMATION STOPPED at Review and submit. "
        "Browser kept open for owner manual review/Submit. "
        f"final_submit_control_visible={submit_visible}"
    )
    print(
        "\n=== APPLICATION READY FOR OWNER ===\n"
        "Reached SEEK Review and submit.\n"
        "Automation will NOT click Submit application.\n"
        "Browser stays open — review, then Submit manually if desired.\n"
        "When finished (submitted or abandoned), create OWNER_END_SESSION "
        f"under:\n  {run_dir}\n"
    )
    wait_for_end_session(
        run_dir,
        metrics,
        "AAS-0 handoff: browser is open on Review and submit.\n"
        "1) Manually review the application in Playwright Chromium.\n"
        "2) Manually click Submit application if you want to apply "
        "(automation will never click it).\n"
        "3) Create OWNER_END_SESSION in this run directory when done "
        "so the spike can observe the resulting page and then close.",
    )
    _record_owner_submission_observation(page, metrics)
    try:
        _screenshot(page, shot_dir, "99_after_owner_session", metrics)
    except Exception:  # noqa: BLE001
        pass
    print(
        f"\nOwner session ended. submission_observation="
        f"{metrics.application_submission} "
        f"({metrics.submission_observation_evidence}). Closing browser.\n"
    )


def _screenshot(page, shot_dir: Path, name: str, metrics: SpikeMetrics) -> None:
    path = shot_dir / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    metrics.screenshots.append(str(path))


def _job_detail_signals(page) -> PageSignals:
    url = page.url
    heading = ""
    try:
        heading = page.locator("h1").first.inner_text(timeout=2000)
    except Exception:  # noqa: BLE001
        heading = ""
    return PageSignals(
        url=url,
        heading_text=heading,
        looks_like_job_detail="/job/" in url and "apply" not in url.lower(),
        looks_like_application_form="apply" in url.lower() or "application" in url.lower(),
        looks_like_review_or_confirmation=_page_looks_like_final_review(page),
    )


def _click_apply_entry(page, metrics: SpikeMetrics) -> None:
    """Activate category-A Apply entry on the job detail page only."""
    signals = _job_detail_signals(page)
    # Prefer visible Apply controls; classify before activation.
    for locator in page.locator("a, button").all():
        try:
            if not locator.is_visible():
                continue
            label = (locator.inner_text() or "").strip()
        except Exception:  # noqa: BLE001
            continue
        if not label:
            continue
        if "apply" not in label.lower():
            continue
        kind = classify_control(label, page=signals)
        if kind is ControlClass.NAVIGATION:
            assert_may_activate(label, page=signals)
            locator.click()
            metrics.add_note(f"Clicked navigation Apply entry: {label!r}")
            return
        if kind is ControlClass.FINAL_SUBMIT:
            metrics.add_failure(f"Saw final-submit-like Apply at entry: {label!r}")
            raise FinalSubmitGuardError(
                f"Refused Apply control classified as final submit: {label!r}"
            )
    # Fallback: SEEK job detail commonly uses "Quick apply".
    for name in ("Quick apply", "Apply"):
        link = page.get_by_role("link", name=name)
        button = page.get_by_role("button", name=name)
        target = None
        if link.count() > 0 and link.first.is_visible():
            target = link.first
            label = name
        elif button.count() > 0 and button.first.is_visible():
            target = button.first
            label = name
        if target is None:
            continue
        assert_may_activate(label, page=signals)
        target.click()
        metrics.add_note(f"Clicked fallback Apply entry control: {label!r}")
        return
    raise FinalSubmitGuardError(
        "Could not find a safe Apply / Quick apply entry control on the job page."
    )


def _page_looks_like_final_review(page) -> bool:
    body = ""
    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception:  # noqa: BLE001
        return False
    return is_final_review_page(body)


def _detect_final_submit_visible(page, metrics: SpikeMetrics) -> bool:
    signals = PageSignals(
        url=page.url,
        looks_like_review_or_confirmation=True,
        looks_like_application_form=True,
    )
    for locator in page.locator("button, input[type=submit], a").all():
        try:
            if not locator.is_visible():
                continue
            label = (locator.inner_text() or locator.get_attribute("value") or "").strip()
        except Exception:  # noqa: BLE001
            continue
        if not label:
            continue
        if looks_like_stepper_review_label(label):
            continue
        if classify_control(label, page=signals) is ControlClass.FINAL_SUBMIT:
            metrics.add_note(f"Final submit control observed (not clicked): {label!r}")
            return True
    return False


def _try_advance_navigation(page, metrics: SpikeMetrics, run_dir: Path) -> bool:
    _dismiss_blocking_modals(page, metrics)
    signals = PageSignals(
        url=page.url,
        looks_like_application_form=True,
        looks_like_review_or_confirmation=_page_looks_like_final_review(page),
        has_visible_resume_upload=_has_file_input(page),
    )
    # Prefer SEEK's known continue control before scanning every button.
    continue_btn = page.locator('[data-testid="continue-button"]')
    if continue_btn.count() > 0:
        try:
            if continue_btn.first.is_visible():
                label = (continue_btn.first.inner_text() or "Continue").strip() or "Continue"
                kind = classify_control(label, page=signals)
                if kind is ControlClass.NAVIGATION:
                    assert_may_activate(label, page=signals)
                    continue_btn.first.click(timeout=10_000)
                    metrics.add_note(
                        f"Clicked SEEK continue-button: {label!r} "
                        "(progress not assumed until state verifies)"
                    )
                    return True
        except Exception as error:  # noqa: BLE001
            metrics.add_note(f"continue-button click failed: {error}")

    preferred = ("continue", "next", "save and continue")
    for locator in page.locator("button, a").all():
        try:
            if not locator.is_visible():
                continue
            label = (locator.inner_text() or "").strip()
        except Exception:  # noqa: BLE001
            continue
        if not label:
            continue
        lowered = label.lower()
        if "review and submit" in lowered:
            metrics.add_note(f"Skipped final submit during advance scan: {label!r}")
            continue
        if not any(p in lowered for p in preferred):
            continue
        kind = classify_control(label, page=signals)
        if kind is ControlClass.NAVIGATION:
            assert_may_activate(label, page=signals)
            try:
                locator.click(timeout=10_000)
            except Exception as error:  # noqa: BLE001
                metrics.add_note(f"nav click failed for {label!r}: {error}")
                _dismiss_blocking_modals(page, metrics)
                try:
                    locator.click(timeout=5_000, force=True)
                except Exception as error2:  # noqa: BLE001
                    metrics.add_failure(f"nav_click_failed:{label}:{error2}")
                    return False
            metrics.add_note(
                f"Clicked navigation control: {label!r} "
                "(progress not assumed until state verifies)"
            )
            return True
        if kind is ControlClass.FINAL_SUBMIT:
            metrics.add_note(f"Skipped final submit during advance scan: {label!r}")
            continue
        answer, _ = ask_question(
            run_dir,
            metrics,
            f"Activate ambiguous control {label!r}? Answer YES or NO.",
            ["YES", "NO"],
        )
        if answer.upper() in {"YES", "Y"}:
            locator.click()
            metrics.add_note(f"Owner authorized ambiguous control: {label!r}")
            return True
        metrics.add_note(f"Owner refused ambiguous control: {label!r}")
        return False
    return False


def _dismiss_blocking_modals(page, metrics: SpikeMetrics) -> None:
    """Close SEEK Braid modals that intercept clicks (e.g. profile photo error)."""
    modal = page.locator("#braid-modal-container")
    if modal.count() == 0:
        return
    try:
        if not modal.first.is_visible():
            return
    except Exception:  # noqa: BLE001
        return
    metrics.add_note("Dismissing blocking modal overlay")
    for selector in (
        '#braid-modal-container button[aria-label="Close"]',
        '#braid-modal-container button[aria-label="close"]',
        '#braid-modal-container button:has-text("Close")',
        '#braid-modal-container button:has-text("OK")',
        '#braid-modal-container button:has-text("Got it")',
    ):
        btn = page.locator(selector)
        try:
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click(timeout=3000)
                page.wait_for_timeout(500)
                return
        except Exception:  # noqa: BLE001
            continue
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        metrics.add_note("Sent Escape to dismiss modal")
    except Exception as error:  # noqa: BLE001
        metrics.add_note(f"modal_dismiss_failed: {error}")


def _has_file_input(page) -> bool:
    try:
        return page.locator("input[type=file]").count() > 0
    except Exception:  # noqa: BLE001
        return False


def _assist_visible_fields(page, known: KnownAnswers, metrics: SpikeMetrics) -> bool:
    filled_any = False
    locators = page.locator("input:not([type=file]):not([type=hidden]), textarea, select")
    count = locators.count()
    for index in range(count):
        locator = locators.nth(index)
        try:
            if not locator.is_visible():
                continue
            current = locator.input_value()
            if current and current.strip():
                continue
            label = _label_for_control(page, locator)
            if is_default_resume_checkbox_label(label):
                metrics.add_note(
                    "Skipped Make this my default résumé checkbox in field assist"
                )
                continue
            result = resolve_answer(label, known)
            if result.decision is AnswerDecision.KNOWN and result.value:
                _fill_locator(locator, result.value)
                metrics.record_field(
                    label or f"field_{index}",
                    "auto",
                    detail=result.reason,
                    value_preview=result.value,
                )
                filled_any = True
            else:
                metrics.record_field(
                    label or f"field_{index}",
                    "unknown",
                    detail=result.reason,
                )
        except Exception as error:  # noqa: BLE001
            metrics.add_failure(f"field_assist_failed[{index}]: {error}")
            metrics.record_field(f"field_{index}", "failed", detail=str(error))
    return filled_any


def _collect_unanswered_labels(page, known: KnownAnswers) -> list[tuple[str, list[str]]]:
    pending: list[tuple[str, list[str]]] = []
    locators = page.locator("input:not([type=file]):not([type=hidden]), textarea, select")
    for index in range(locators.count()):
        locator = locators.nth(index)
        try:
            if not locator.is_visible():
                continue
            current = locator.input_value()
            if current and current.strip():
                continue
            label = _label_for_control(page, locator) or f"unlabeled_field_{index}"
            if is_default_resume_checkbox_label(label):
                continue
            result = resolve_answer(label, known)
            if result.decision is AnswerDecision.PAUSE:
                options: list[str] = []
                tag = locator.evaluate("el => el.tagName").lower()
                if tag == "select":
                    options = locator.locator("option").all_inner_texts()
                pending.append((label, options))
        except Exception:  # noqa: BLE001
            continue
    # Dedupe labels preserving order
    seen: set[str] = set()
    unique: list[tuple[str, list[str]]] = []
    for label, options in pending:
        if label in seen:
            continue
        seen.add(label)
        unique.append((label, options))
    return unique


def _fill_by_label(page, label: str, value: str, metrics: SpikeMetrics, *, outcome: str) -> None:
    if not value:
        return
    if is_default_resume_checkbox_label(label):
        metrics.add_note("Refused to operate Make this my default résumé via field fill")
        return
    locator = page.get_by_label(label, exact=False)
    try:
        if locator.count() == 0:
            metrics.record_field(label, "failed", detail="label_not_found_for_owner_answer")
            return
        _fill_locator(locator.first, value)
        metrics.record_field(label, outcome, detail="owner_provided", value_preview=value)  # type: ignore[arg-type]
    except Exception as error:  # noqa: BLE001
        metrics.record_field(label, "failed", detail=str(error))


def _fill_locator(locator, value: str) -> None:
    tag = locator.evaluate("el => el.tagName").lower()
    input_type = (locator.get_attribute("type") or "").lower()
    if tag == "select":
        try:
            locator.select_option(label=value)
        except Exception:  # noqa: BLE001
            locator.select_option(value=value)
        return
    if input_type in {"checkbox", "radio"}:
        if value.lower() in {"y", "yes", "true", "1"}:
            locator.check()
        return
    locator.fill(value)


def _label_for_control(page, locator) -> str:
    try:
        labelled = locator.evaluate(
            """el => {
              const id = el.getAttribute('id');
              if (id) {
                const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
                if (lab && lab.innerText) return lab.innerText.trim();
              }
              const aria = el.getAttribute('aria-label');
              if (aria) return aria.trim();
              const ph = el.getAttribute('placeholder');
              if (ph) return ph.trim();
              const name = el.getAttribute('name');
              if (name) return name.trim();
              return '';
            }"""
        )
        if labelled:
            return str(labelled)
    except Exception:  # noqa: BLE001
        pass
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
