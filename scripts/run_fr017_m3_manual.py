"""FR-017 M3 manual validation — read-only metrics CLI demos A-I.

Does not write orchestration/agent stores. Uses --fixture and metrics-corpus only.
"""

from __future__ import annotations

import sys

from typer.testing import CliRunner

from career_intelligence.cli.main import app

runner = CliRunner()

DEMOS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("A", "complete successful run", ("metrics", "--fixture", "C01_complete_successful")),
    ("B", "blocked delegation", ("metrics", "--fixture", "C02_delegation_blocked")),
    ("C", "prepare_then_brief reconstruction", ("metrics", "--fixture", "C05_prepare_then_brief")),
    ("D", "missing optional metadata", ("metrics", "--fixture", "C06_missing_optional_metadata")),
    ("E", "measured zero", ("metrics", "--fixture", "C07_measured_zero")),
    ("F", "orphaned child", ("metrics", "--fixture", "C08_orphaned_child_ref")),
    ("G", "contradictory audit", ("metrics", "--fixture", "C14_malformed_contradictory")),
    ("H", "corpus aggregate", ("metrics-corpus",)),
)


def main() -> int:
    print("FR-017 M3 manual validation (read-only)")
    print("=" * 72)
    failed = 0
    for label, title, args in DEMOS:
        print(f"\n### {label}. {title}")
        print(f"$ cic agent orchestrate {' '.join(args)}")
        result = runner.invoke(app, ["agent", "orchestrate", *args])
        # Windows consoles may be cp1252; keep manual output ASCII-safe.
        out = (result.output or "").encode("ascii", errors="replace").decode("ascii")
        print(out)
        if result.exit_code != 0:
            print(f"FAILED exit={result.exit_code}")
            failed += 1

    print("\n### I. proof of no writes / runtime mutation")
    print(
        "Fixtures and metrics-corpus are in-memory static audits; "
        "metrics --fixture never opens orchestration_runs or agent_runs. "
        "Store-backed metrics only calls load/load_handoff (verified in unit tests)."
    )
    print("No DOS/BOPA/OBS start/resume invoked by this script.")

    if failed:
        print(f"\nMANUAL VALIDATION FAILED ({failed})")
        return 1
    print("\nMANUAL VALIDATION PASSED (A-H); I documented.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
