"""FR-017 M4 final owner validation — persisted run + fixtures + corpus.

Writes only under data/_fr017_m4_manual_tmp/ (disposable demo store).
Does not mutate DOS/BOPA/OBS runtime or production SoTs.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.multi_agent import (
    JsonDirectoryOrchestrationStore,
    get_demo_fixture,
    run_observability_corpus,
)

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "data" / "_fr017_m4_manual_tmp"
runner = CliRunner()

RECON_MARKERS = (
    "Owner goal:",
    "Observed state",
    "selected=",
    "delegation=",
    "lifecycle=",
    "Stop reason:",
    "Owner next action:",
    "Steps / visits:",
    "idempotency",
    "R1-R12 reconstructability",
)


def _safe(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def main() -> int:
    print("FR-017 M4 final validation")
    print("=" * 72)
    failed = 0

    # Corpus first
    corpus = run_observability_corpus()
    print(
        f"\nCORPUS: {corpus.passed}/{corpus.total} "
        f"go={corpus.go_no_go} repeat={corpus.deterministic_repeat_ok}"
    )
    if not corpus.all_passed or corpus.go_no_go != "GO":
        failed += 1
        print("CORPUS FAILED")

    # A — persisted run (C05 written once, then CLI metrics load-only)
    if TMP.exists():
        shutil.rmtree(TMP)
    store = JsonDirectoryOrchestrationStore(TMP)
    fx = get_demo_fixture("C05_prepare_then_brief")
    store.save(fx.run)
    for h in fx.handoffs:
        store.save_handoff(h)
    run_path = TMP / f"{fx.run.orchestration_run_id}.json"
    before = run_path.read_text(encoding="utf-8")
    mtimes = {p: p.stat().st_mtime_ns for p in TMP.rglob("*.json")}

    print("\n### A. complete persisted run")
    result = runner.invoke(
        app,
        [
            "agent",
            "orchestrate",
            "metrics",
            fx.run.orchestration_run_id,
            "--orchestration-runs-dir",
            str(TMP),
        ],
    )
    out = _safe(result.output or "")
    print(out[:2500])
    if result.exit_code != 0 or not all(m in (result.output or "") for m in RECON_MARKERS):
        print("A FAILED")
        failed += 1
    after = run_path.read_text(encoding="utf-8")
    if before != after:
        print("A WRITE DETECTED on run file")
        failed += 1
    for p, mt in mtimes.items():
        if p.exists() and p.stat().st_mtime_ns != mt:
            print(f"A WRITE DETECTED on {p.name}")
            failed += 1

    demos = (
        ("B", "fixture run", ("metrics", "--fixture", "C01_complete_successful")),
        ("C", "prepare_then_brief", ("metrics", "--fixture", "C05_prepare_then_brief")),
        ("D", "missing metadata", ("metrics", "--fixture", "C06_missing_optional_metadata")),
        ("E", "measured zero", ("metrics", "--fixture", "C07_measured_zero")),
        ("F", "orphaned child", ("metrics", "--fixture", "C08_orphaned_child_ref")),
        ("G", "contradictory audit", ("metrics", "--fixture", "C14_malformed_contradictory")),
        ("H", "corpus summary", ("metrics-corpus",)),
    )
    for label, title, args in demos:
        print(f"\n### {label}. {title}")
        r = runner.invoke(app, ["agent", "orchestrate", *args])
        print(_safe((r.output or "")[:1200]))
        if r.exit_code != 0:
            print(f"{label} FAILED")
            failed += 1

    print("\n### I. read-only proof")
    print(
        "A: run JSON unchanged after metrics CLI. "
        "B-H: --fixture / metrics-corpus use in-memory fixtures (no production store). "
        "No DOS/BOPA/OBS start/resume invoked."
    )

    # Cleanup disposable store (optional leave for inspection — remove for cleanliness)
    shutil.rmtree(TMP, ignore_errors=True)

    if failed:
        print(f"\nM4 VALIDATION FAILED ({failed})")
        return 1
    print("\nM4 VALIDATION PASSED")
    print(json.dumps({"corpus_passed": corpus.passed, "corpus_total": corpus.total, "go": corpus.go_no_go}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
