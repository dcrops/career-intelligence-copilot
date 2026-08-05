"""OAT-001 Phase 3 — live BOPA evaluation harness (operational only).

Runs cic agent run/show/history/resume and pipeline show before/after each scenario.
Does not modify FR-015 behaviour. Evidence under data/_oat001_phase3_bopa/.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "_oat001_phase3_bopa"
CIC = [sys.executable, "-m", "career_intelligence.cli.main"]


@dataclass
class Scenario:
    name: str
    opportunity_id: str
    label: str
    notes: str = ""


SCENARIOS: list[Scenario] = [
    Scenario(
        "S1_fresh_assessed",
        "opp_01KZ8CEJANPX26DWEKQNF7BWH9",
        "Redwolf + Rosch / AI Engineer (fresh assessed, apply)",
    ),
    Scenario(
        "S2_submitted",
        "opp_01KY8X66C3NSYXJ4E2RNTMMKM5",
        "Officeworks / AI Engineer (submitted)",
    ),
    Scenario(
        "S3_interviewing",
        "opp_01KY8RFAH81M9V30ZVH9TM09T5",
        "Bluefin / AI Systems Developer (interviewing)",
    ),
    Scenario(
        "S4_gold",
        "opp_01KY8WYE6RM54EYV8QT0YXHCQP",
        "Jirotech / Junior Software DevOps (Gold, pursue; decision=None)",
    ),
    Scenario(
        "S5_bronze_apply",
        "opp_01KZ8CCQZTVNN2JKF91P1FANT2",
        "Carlton Football Club / AI Enablement Lead (Bronze, apply, fresh assessed)",
    ),
]


@dataclass
class CmdResult:
    argv: list[str]
    exit_code: int
    duration_s: float
    stdout: str
    stderr: str


@dataclass
class ScenarioResult:
    scenario: str
    opportunity_id: str
    label: str
    pipeline_before: str = ""
    pipeline_after: str = ""
    pipeline_after_resume: str = ""
    run: CmdResult | None = None
    show: CmdResult | None = None
    history: CmdResult | None = None
    resume: CmdResult | None = None
    show_after_resume: CmdResult | None = None
    history_after_resume: CmdResult | None = None
    agent_run_id: str | None = None
    notes: list[str] = field(default_factory=list)


def _run(argv: list[str], *, timeout: int = 900) -> CmdResult:
    env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(REPO / "src")}
    t0 = time.perf_counter()
    proc = subprocess.run(
        argv,
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout,
    )
    return CmdResult(
        argv=argv[3:],  # drop python -m module prefix noise for report
        exit_code=proc.returncode,
        duration_s=round(time.perf_counter() - t0, 3),
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _cic(*args: str, timeout: int = 900) -> CmdResult:
    return _run(CIC + list(args), timeout=timeout)


def _extract_run_id(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("run_id:"):
            return line.split(":", 1)[1].strip()
    return None


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_scenario(sc: Scenario) -> ScenarioResult:
    dest = OUT / sc.name
    dest.mkdir(parents=True, exist_ok=True)
    result = ScenarioResult(
        scenario=sc.name,
        opportunity_id=sc.opportunity_id,
        label=sc.label,
    )

    pipe_b = _cic("pipeline", "show", sc.opportunity_id)
    result.pipeline_before = pipe_b.stdout + pipe_b.stderr
    _write(dest / "01_pipeline_before.txt", result.pipeline_before)

    run = _cic("agent", "run", sc.opportunity_id, "--approve", "--verbose")
    result.run = run
    _write(dest / "02_agent_run.txt", f"exit={run.exit_code} duration_s={run.duration_s}\n\nSTDOUT:\n{run.stdout}\n\nSTDERR:\n{run.stderr}")
    rid = _extract_run_id(run.stdout) or _extract_run_id(run.stderr)
    result.agent_run_id = rid

    if rid:
        show = _cic("agent", "show", rid, "--verbose")
        result.show = show
        _write(dest / "03_agent_show.txt", show.stdout + show.stderr)

        hist = _cic("agent", "history", rid, "--verbose")
        result.history = hist
        _write(dest / "04_agent_history.txt", hist.stdout + hist.stderr)
    else:
        result.notes.append("Could not extract agent_run_id from run output")

    pipe_a = _cic("pipeline", "show", sc.opportunity_id)
    result.pipeline_after = pipe_a.stdout + pipe_a.stderr
    _write(dest / "05_pipeline_after.txt", result.pipeline_after)

    if rid:
        resume = _cic("agent", "resume", rid, "--approve", "--verbose")
        result.resume = resume
        _write(
            dest / "06_agent_resume.txt",
            f"exit={resume.exit_code} duration_s={resume.duration_s}\n\nSTDOUT:\n{resume.stdout}\n\nSTDERR:\n{resume.stderr}",
        )

        show2 = _cic("agent", "show", rid, "--verbose")
        result.show_after_resume = show2
        _write(dest / "07_agent_show_after_resume.txt", show2.stdout + show2.stderr)

        hist2 = _cic("agent", "history", rid, "--verbose")
        result.history_after_resume = hist2
        _write(dest / "08_agent_history_after_resume.txt", hist2.stdout + hist2.stderr)

        pipe_r = _cic("pipeline", "show", sc.opportunity_id)
        result.pipeline_after_resume = pipe_r.stdout + pipe_r.stderr
        _write(dest / "09_pipeline_after_resume.txt", result.pipeline_after_resume)

    return result


def _cmd_to_dict(c: CmdResult | None) -> dict | None:
    if c is None:
        return None
    return {
        "argv": c.argv,
        "exit_code": c.exit_code,
        "duration_s": c.duration_s,
        "stdout_len": len(c.stdout),
        "stderr_len": len(c.stderr),
        "stdout_preview": c.stdout[:2000],
        "stderr_preview": c.stderr[:1000],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    selected = SCENARIOS
    if only:
        selected = [s for s in SCENARIOS if s.name in only or s.opportunity_id in only]
        if not selected:
            print("No matching scenarios", file=sys.stderr)
            return 2

    results: list[ScenarioResult] = []
    for sc in selected:
        print(f"\n=== {sc.name}: {sc.label} ===", flush=True)
        r = run_scenario(sc)
        results.append(r)
        print(
            f"  run_id={r.agent_run_id} duration={r.run.duration_s if r.run else '?'}s "
            f"exit={r.run.exit_code if r.run else '?'}",
            flush=True,
        )

    summary = []
    for r in results:
        summary.append(
            {
                "scenario": r.scenario,
                "opportunity_id": r.opportunity_id,
                "label": r.label,
                "agent_run_id": r.agent_run_id,
                "notes": r.notes,
                "run": _cmd_to_dict(r.run),
                "resume": _cmd_to_dict(r.resume),
                "pipeline_unchanged_after_run": r.pipeline_before == r.pipeline_after,
                "pipeline_unchanged_after_resume": (
                    r.pipeline_before == r.pipeline_after_resume
                    if r.pipeline_after_resume
                    else None
                ),
            }
        )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT / 'summary.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
