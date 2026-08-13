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
    merge_owner_extra,
    resolve_answer,
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
from aas0.seek_documents import (  # noqa: E402
    capture_fingerprint,
    documents_step_ready_to_continue,
    prepare_and_upload_documents,
)
from aas0.session_handoff import (  # noqa: E402
    build_final_review_handoff,
    observe_submission_from_page_text,
)
from aas0.state_progress import (  # noqa: E402
    CoverLetterGateError,
    SameStateRetryGuard,
)
from aas0.submit_guard import (  # noqa: E402
    ControlClass,
    FinalSubmitGuardError,
    PageSignals,
    assert_may_activate,
    classify_control,
)


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

    metrics = SpikeMetrics(opportunity_id=inputs.opportunity_id)
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
                "When the Repurpose It job page is ready (signed in if needed), "
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
            for step in range(1, 8):
                if _page_looks_like_final_review(page):
                    _handoff_final_review(
                        page=page,
                        run_dir=run_dir,
                        shot_dir=shot_dir,
                        metrics=metrics,
                        step=step,
                    )
                    handoff_done = True
                    break

                with TimedPhase(metrics, "automation"):
                    filled = _assist_visible_fields(page, known, metrics)
                    uploaded = prepare_and_upload_documents(
                        page,
                        cv_pdf=inputs.cv_pdf,
                        cl_pdf=inputs.cover_letter_pdf,
                        metrics=metrics,
                    )

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

                # Gate Choose Documents Continue on radio + absence of validation.
                try:
                    documents_step_ready_to_continue(page)
                except CoverLetterGateError as error:
                    metrics.add_failure(str(error))
                    same_state.failures += 1
                    metrics.add_note(
                        f"documents_gate_blocked (failure "
                        f"{same_state.failures}/{same_state.max_failures}): {error}"
                    )
                    _screenshot(page, shot_dir, f"0{step + 2}_documents_gate", metrics)
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
                    if _detect_final_submit_visible(page, metrics):
                        _handoff_final_review(
                            page=page,
                            run_dir=run_dir,
                            shot_dir=shot_dir,
                            metrics=metrics,
                            step=step,
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
                    # If advance landed on final review, hand off immediately.
                    if _page_looks_like_final_review(page) or _detect_final_submit_visible(
                        page, metrics
                    ):
                        _handoff_final_review(
                            page=page,
                            run_dir=run_dir,
                            shot_dir=shot_dir,
                            metrics=metrics,
                            step=step,
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


def _handoff_final_review(
    *,
    page,
    run_dir: Path,
    shot_dir: Path,
    metrics: SpikeMetrics,
    step: int,
) -> None:
    """Stop automation at Review, keep browser open for owner Submit."""
    submit_visible = _detect_final_submit_visible(page, metrics)
    handoff = build_final_review_handoff(final_submit_control_visible=submit_visible)
    metrics.final_stage_reached = "review_or_confirmation"
    metrics.browser_kept_open_for_owner = handoff.browser_kept_open_for_owner
    metrics.submit_clicked = False
    metrics.application_submission = "not_completed"
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
    # Passive observation only — never activate Submit.
    try:
        body = page.locator("body").inner_text(timeout=5000)
    except Exception:  # noqa: BLE001
        body = ""
    observation = observe_submission_from_page_text(body)
    metrics.application_submission = observation.status
    metrics.submission_observation_evidence = observation.evidence
    metrics.add_note(
        f"post_owner_submission_observation status={observation.status} "
        f"evidence={observation.evidence!r}"
    )
    try:
        _screenshot(page, shot_dir, "99_after_owner_session", metrics)
    except Exception:  # noqa: BLE001
        pass
    print(
        f"\nOwner session ended. submission_observation={observation.status} "
        f"({observation.evidence}). Closing browser.\n"
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
    lowered = body.lower()
    review_hints = (
        "review your application",
        "check your application",
        "confirm your application",
        "ready to submit",
        "submit application",
        "send application",
    )
    return any(hint in lowered for hint in review_hints)


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
