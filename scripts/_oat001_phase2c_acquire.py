"""OAT-001 Phase 2C — acquire missing jobs via FR-008 in small batches."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_fr008_workflow_manual.py"
JOBS = ROOT / "manual_validation" / "jobs"
OPP_DIR = ROOT / "data" / "opportunities"
CHECKPOINT = ROOT / "data" / "workflow_runs"
OUT = ROOT / "data" / "_oat001_phase2c_runs"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "src"))
from career_intelligence.opportunities import OpportunityService  # noqa: E402

ACQUISITIONS = [
    (
        "006_senior_ai_engineer_kogan.txt",
        "Senior AI Engineer",
        "Kogan.com",
    ),
    (
        "014_anton_ai_automation_engineer.txt",
        "AI Automation Engineer",
        "Anton Murray Consulting",
    ),
    (
        "015_expedient_software_junior_full_stack_developer.txt",
        "Graduate / Junior Full Stack Developer",
        "Expedient Software",
    ),
    (
        "016_robert_half_ai_engineer.txt",
        "AI Engineer | Contact Centre",
        "Robert Half",
    ),
    (
        "017_mars_recruitment_ai_engineer.txt",
        "AI Engineer",
        "Mars Recruitment",
    ),
    (
        "018_carlton_ai_enablement_lead.txt",
        "AI Enablement Lead",
        "Carlton Football Club",
    ),
    (
        "019_redwolf_ai_engineer.txt",
        "AI Engineer",
        "Redwolf + Rosch",
    ),
    (
        "020_acenture_ai_engineer.txt",
        "AI Engineer",
        "Accenture",
    ),
]

BATCHES = [
    ACQUISITIONS[0:2],
    ACQUISITIONS[2:4],
    ACQUISITIONS[4:6],
    ACQUISITIONS[6:8],
]


def count() -> tuple[int, int]:
    ops = OpportunityService.from_path(OPP_DIR).list_opportunities()
    complete = sum(1 for o in ops if o.identity.title and o.identity.company)
    return len(ops), complete


def ids() -> set[str]:
    return {o.opportunity_id for o in OpportunityService.from_path(OPP_DIR).list_opportunities()}


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def parse_run_id(output: str) -> str | None:
    for line in output.splitlines():
        if line.startswith("run_id:"):
            return line.split(":", 1)[1].strip()
    return None


def parse_opp_id(output: str) -> str | None:
    for line in output.splitlines():
        if "opportunity_id" in line.lower() and "opp_" in line:
            # e.g. opportunity_id: opp_...
            if "opp_" in line:
                idx = line.index("opp_")
                token = line[idx:].split()[0].strip(",)")
                if token.startswith("opp_"):
                    return token
    # load checkpoint
    return None


def opp_from_checkpoint(run_id: str) -> str | None:
    path = CHECKPOINT / f"{run_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    arts = data.get("artefacts") or {}
    return arts.get("opportunity_id")


def acquire_one(job_file: str, title: str, company: str) -> dict:
    job_path = JOBS / job_file
    if not job_path.is_file():
        # Windows case variants
        matches = list(JOBS.glob(job_file.replace(".txt", "*.txt")))
        if not matches:
            # try case-insensitive
            matches = [p for p in JOBS.glob("*.txt") if p.name.lower() == job_file.lower()]
        if not matches:
            raise FileNotFoundError(job_file)
        job_path = matches[0]

    before_ids = ids()
    start = run_cmd(
        [
            "start",
            "--source",
            "export",
            "--job-file",
            str(job_path),
            "--title",
            title,
            "--company",
            company,
            "--opportunities-dir",
            str(OPP_DIR),
            "--checkpoint-dir",
            str(CHECKPOINT),
        ]
    )
    combined = (start.stdout or "") + "\n" + (start.stderr or "")
    (OUT / f"{job_path.stem}_start.txt").write_text(combined, encoding="utf-8")
    if start.returncode not in {0, 2, 3} and "awaiting_owner" not in combined:
        # 0 may complete; awaiting_owner often still exit 0
        if "awaiting_owner" not in combined and start.returncode != 0:
            raise RuntimeError(
                f"start failed {job_file} code={start.returncode}\n{combined[-4000:]}"
            )

    run_id = parse_run_id(combined)
    if not run_id:
        raise RuntimeError(f"no run_id for {job_file}\n{combined[-2000:]}")

    if "awaiting_owner" in combined or "Interrupted for owner review" in combined:
        resume = run_cmd(
            [
                "resume",
                "--run-id",
                run_id,
                "--decision",
                "apply",
                "--opportunities-dir",
                str(OPP_DIR),
                "--checkpoint-dir",
                str(CHECKPOINT),
            ]
        )
        combined2 = (resume.stdout or "") + "\n" + (resume.stderr or "")
        (OUT / f"{job_path.stem}_resume.txt").write_text(combined2, encoding="utf-8")
        if resume.returncode != 0 and "completed" not in combined2:
            raise RuntimeError(
                f"resume failed {job_file} code={resume.returncode}\n{combined2[-4000:]}"
            )
        combined = combined + "\n" + combined2

    opp_id = opp_from_checkpoint(run_id) or parse_opp_id(combined)
    after_ids = ids()
    new_ids = sorted(after_ids - before_ids)
    if not opp_id and new_ids:
        opp_id = new_ids[0]
    if not opp_id:
        raise RuntimeError(f"no opportunity created for {job_file}; new_ids={new_ids}")

    svc = OpportunityService.from_path(OPP_DIR)
    opp = svc.get(opp_id)
    if opp.identity.title != title or opp.identity.company != company:
        # may still be set from acquisition posting
        print(
            f"  WARN identity got title={opp.identity.title!r} company={opp.identity.company!r}"
        )
    return {
        "job_file": job_path.name,
        "run_id": run_id,
        "opportunity_id": opp_id,
        "title": opp.identity.title,
        "company": opp.identity.company,
        "decision": opp.decision.decision if opp.decision else None,
        "status": opp.status,
        "new_ids": new_ids,
    }


def main() -> int:
    n, c = count()
    print(f"BEFORE 2C: opportunities={n} identity_complete={c}")
    results = []
    for bi, batch in enumerate(BATCHES, start=1):
        print(f"\n=== ACQUIRE BATCH {bi}/{len(BATCHES)} ===")
        before_ids = ids()
        before_n, _ = count()
        for job_file, title, company in batch:
            print(f"Acquiring {job_file} …")
            row = acquire_one(job_file, title, company)
            results.append(row)
            print(
                f"  -> {row['opportunity_id']} {row['company']} / {row['title']} "
                f"decision={row['decision']} run={row['run_id']}"
            )
        after_n, after_c = count()
        after_ids = ids()
        # previous IDs preserved
        if not before_ids.issubset(after_ids):
            raise SystemExit("ID LOSS detected")
        print(
            f"BATCH {bi} VALIDATED: count {before_n}->{after_n} "
            f"identity_complete={after_c} new={sorted(after_ids-before_ids)}"
        )

    (OUT / "summary.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    n, c = count()
    print(f"\nAFTER 2C: opportunities={n} identity_complete={c}")
    print(f"Wrote {OUT / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
