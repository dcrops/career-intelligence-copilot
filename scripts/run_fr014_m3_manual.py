#!/usr/bin/env python3
"""Manual validation for FR-014 M3 owner CLI and external-use gates.

Usage:
  python scripts/run_fr014_m3_manual.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.cv_generation.pdf_renderer import render_pdf_from_html as _real_pdf
from tests.unit.application_package.helpers import (
    approved_gate_options,
    package_service,
    seed_applied_opportunity,
)
from tests.unit.application_strategy.helpers import fixtures_dir

PROFILE = fixtures_dir() / "minimal_valid_profile.yaml"
REDWOLF = (
    "Roles centred on Python, TypeScript, and Vue are where I do my best "
    "engineering work."
)
runner = CliRunner()


def _ensure_pdf_stub() -> None:
    """Allow prepare without system WeasyPrint (same policy as tests/conftest)."""
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        stub = lambda _html: b"%PDF-1.4\nstub\n%%EOF\n"
        import career_intelligence.cover_letter.draft_writer as cl_dw
        import career_intelligence.cv_generation.draft_writer as cv_dw
        import career_intelligence.cv_generation.pdf_renderer as pdf

        pdf.render_pdf_from_html = stub  # type: ignore[assignment]
        cv_dw.render_pdf_from_html = stub  # type: ignore[assignment]
        cl_dw.render_pdf_from_html = stub  # type: ignore[assignment]
        _ = _real_pdf  # silence unused when weasyprint present


def _pkg_common(workspace: Path, truth: Path) -> list[str]:
    return [
        "--dir",
        str(workspace),
        "--packages-dir",
        str(workspace / "application_packages"),
        "--cv-dir",
        str(workspace / "cv_generated"),
        "--cover-letter-dir",
        str(workspace / "cover_letter_generated"),
        "--profile",
        str(PROFILE),
        "--truth-reports-dir",
        str(truth),
    ]


def _sub_common(workspace: Path, truth: Path) -> list[str]:
    return [
        *_pkg_common(workspace, truth),
        "--attempts-dir",
        str(workspace / "attempts"),
    ]


def _run_m3(workspace: Path) -> int:
    _ensure_pdf_stub()
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    opportunities, oid, profile = seed_applied_opportunity(workspace)
    packages = package_service(workspace, opportunities, profile)
    packages.prepare(oid, **approved_gate_options())  # type: ignore[arg-type]
    truth = workspace / "truth_reports"
    pkg = _pkg_common(workspace, truth)
    sub = _sub_common(workspace, truth)

    # 1 Redwolf FAIL
    redwolf = workspace / "redwolf.md"
    redwolf.write_text(REDWOLF, encoding="utf-8")
    r1 = runner.invoke(
        app,
        [
            "truth",
            "validate",
            str(redwolf),
            "--profile",
            str(PROFILE),
            "--kind",
            "cover_letter_markdown",
            "--no-persist",
        ],
    )
    print("[1] redwolf validate", r1.exit_code, "(expect FAIL=1)")
    assert r1.exit_code == 1 and "outcome: fail" in r1.output

    # 2 Corrected PASS (capability + employer context)
    redwolf.write_text(
        "I have experience with Python.\nThe role uses TypeScript and Vue.\n",
        encoding="utf-8",
    )
    r2 = runner.invoke(
        app,
        [
            "truth",
            "validate",
            str(redwolf),
            "--profile",
            str(PROFILE),
            "--kind",
            "cover_letter_markdown",
            "--no-persist",
        ],
    )
    print("[2] corrected validate", r2.exit_code, "(expect PASS=0)")
    assert r2.exit_code == 0 and "outcome: pass" in r2.output

    # 3 Supported candidate statement alone
    supported = workspace / "supported.md"
    supported.write_text(
        "I have experience with Python and FastAPI.\n", encoding="utf-8"
    )
    # FastAPI may be unsupported on minimal profile — use Python-only for PASS
    supported.write_text("I have experience with Python.\n", encoding="utf-8")
    r2b = runner.invoke(
        app,
        [
            "truth",
            "validate",
            str(supported),
            "--profile",
            str(PROFILE),
            "--kind",
            "cover_letter_markdown",
            "--no-persist",
        ],
    )
    print("[2b] supported Python", r2b.exit_code, "(expect PASS=0)")
    assert r2b.exit_code == 0

    # 4 Package validate
    r3 = runner.invoke(app, ["truth", "validate-package", oid, *pkg])
    print("[3] validate-package", r3.exit_code, "(expect ALLOWED)")
    assert r3.exit_code == 0 and "ALLOWED" in r3.output

    # 5 Stale after Markdown edit
    manifest = packages.get(oid, verify=True)
    cl = Path(manifest.cover_letter.markdown_path)
    cl.write_text(cl.read_text(encoding="utf-8") + "\nowner edit\n", encoding="utf-8")
    r4 = runner.invoke(app, ["truth", "validate-package", oid, *pkg, "--check-only"])
    print("[4] stale check-only", r4.exit_code, "(expect BLOCKED)")
    assert r4.exit_code == 1 and "BLOCKED" in r4.output

    r5 = runner.invoke(app, ["submission", "check", oid, *sub])
    print("[5] submission while stale", r5.exit_code, "(expect Not Ready)")
    assert r5.exit_code == 1

    # 6 One failing document blocks package
    cl.write_text(REDWOLF, encoding="utf-8")
    r6 = runner.invoke(app, ["truth", "validate-package", oid, *pkg])
    print("[6] redwolf in package", r6.exit_code, "(expect BLOCKED)")
    assert r6.exit_code == 1

    # 7 Restore safe Markdown + revalidate + submission ready
    cl.write_text("I have experience with Python.\n", encoding="utf-8")
    r7 = runner.invoke(app, ["truth", "validate-package", oid, *pkg])
    print("[7] revalidate safe package", r7.exit_code)
    assert r7.exit_code == 0

    r8 = runner.invoke(app, ["submission", "check", oid, *sub])
    print("[8] submission after PASS", r8.exit_code, "(expect Ready)")
    assert r8.exit_code == 0 and "Submission Ready" in r8.output

    print("M3 MANUAL PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["m3"], nargs="?", default="m3")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=_REPO_ROOT / "data" / "_fr014_m3_manual",
    )
    args = parser.parse_args()
    return _run_m3(args.workspace)


if __name__ == "__main__":
    raise SystemExit(main())
