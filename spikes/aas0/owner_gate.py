"""File-based owner gates for AAS-0 (works when stdin is not interactive)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .metrics import SpikeMetrics, TimedPhase


def wait_for_continue(
    run_dir: Path,
    metrics: SpikeMetrics,
    message: str,
    *,
    poll_seconds: float = 0.5,
) -> None:
    """Block until OWNER_CONTINUE appears; counts as owner attention."""
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt = run_dir / "OWNER_PROMPT.txt"
    gate = run_dir / "OWNER_CONTINUE"
    if gate.exists():
        gate.unlink()
    prompt.write_text(message.strip() + "\n", encoding="utf-8")
    print(f"\n--- OWNER ATTENTION ---\n{message}")
    print(f"To continue: create empty file:\n  {gate}\n")
    with TimedPhase(metrics, "owner"):
        while not gate.exists():
            time.sleep(poll_seconds)
    try:
        gate.unlink()
    except OSError:
        pass


def ask_question(
    run_dir: Path,
    metrics: SpikeMetrics,
    label: str,
    options: list[str],
    *,
    poll_seconds: float = 0.5,
) -> tuple[str, bool]:
    """Wait for OWNER_ANSWER.json written by owner/agent.

    Expected JSON::
        {"answer": "...", "reusable": false}
    or plain-text OWNER_ANSWER.txt with the answer only (reusable=false).
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = run_dir / "OWNER_PROMPT.txt"
    answer_json = run_dir / "OWNER_ANSWER.json"
    answer_txt = run_dir / "OWNER_ANSWER.txt"
    for path in (answer_json, answer_txt):
        if path.exists():
            path.unlink()

    lines = [
        "UNKNOWN / AMBIGUOUS APPLICATION QUESTION",
        "",
        label,
        "",
    ]
    if options:
        lines.append("Options:")
        for idx, option in enumerate(options, start=1):
            lines.append(f"  {idx}. {option}")
        lines.append("")
    lines.extend(
        [
            "Respond by writing OWNER_ANSWER.json:",
            '  {"answer": "<text or option number>", "reusable": false}',
            "Or write plain text to OWNER_ANSWER.txt (reusable defaults false).",
            "Use answer SKIP to skip the field.",
            "",
            f"Wait path: {run_dir}",
        ]
    )
    prompt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n--- UNKNOWN / AMBIGUOUS QUESTION ---")
    print(prompt_path.read_text(encoding="utf-8"))

    with TimedPhase(metrics, "owner"):
        while True:
            if answer_json.exists():
                raw = json.loads(answer_json.read_text(encoding="utf-8-sig"))
                answer = str(raw.get("answer", "")).strip()
                reusable = bool(raw.get("reusable", False))
                try:
                    answer_json.unlink()
                except OSError:
                    pass
                break
            if answer_txt.exists():
                answer = answer_txt.read_text(encoding="utf-8-sig").strip()
                reusable = False
                try:
                    answer_txt.unlink()
                except OSError:
                    pass
                break
            time.sleep(poll_seconds)

    if answer.upper() == "SKIP":
        metrics.record_field(label, "skipped", detail="owner_skip")
        return "", False
    if options and answer.isdigit():
        index = int(answer) - 1
        if 0 <= index < len(options):
            answer = options[index]
    return answer, reusable


def wait_for_end_session(
    run_dir: Path,
    metrics: SpikeMetrics,
    message: str,
    *,
    poll_seconds: float = 0.5,
) -> None:
    """Block until OWNER_END_SESSION appears; keep browser open meanwhile."""
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt = run_dir / "OWNER_PROMPT.txt"
    gate = run_dir / "OWNER_END_SESSION"
    if gate.exists():
        gate.unlink()
    prompt.write_text(message.strip() + "\n", encoding="utf-8")
    print(f"\n--- OWNER SESSION HANDOFF ---\n{message}")
    print(f"When finished (after manual Submit or abandon), create:\n  {gate}\n")
    with TimedPhase(metrics, "owner"):
        while not gate.exists():
            time.sleep(poll_seconds)
    try:
        gate.unlink()
    except OSError:
        pass
