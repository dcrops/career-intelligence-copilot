"""OAT-001 Phase 2B/2C/2D operational runner — batch identity repair helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from career_intelligence.opportunities import OpportunityService  # noqa: E402

DIR = ROOT / "data" / "opportunities"


def snapshot() -> dict:
    svc = OpportunityService.from_path(DIR)
    ops = svc.list_opportunities()
    complete = [o for o in ops if o.identity.title and o.identity.company]
    return {
        "count": len(ops),
        "identity_complete": len(complete),
        "ids": sorted(o.opportunity_id for o in ops),
        "decisions": {
            o.opportunity_id: (
                o.decision.decision if o.decision is not None else None
            )
            for o in ops
        },
        "statuses": {o.opportunity_id: o.status for o in ops},
        "review_action_counts": {
            o.opportunity_id: len(o.review_actions) for o in ops
        },
    }


def posting_hash(oid: str) -> str:
    path = DIR / "artifacts" / oid / "posting.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repair(oid: str, title: str, company: str, note: str) -> None:
    cmd = [
        sys.executable,
        "-m",
        "career_intelligence.cli.main",
        "opportunity",
        "repair-identity",
        oid,
        "--dir",
        str(DIR),
        "--title",
        title,
        "--company",
        company,
        "--source-note",
        note,
    ]
    # Prefer cic if installed; fall back to module path via typer app
    try:
        from typer.testing import CliRunner
        from career_intelligence.cli.main import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "opportunity",
                "repair-identity",
                oid,
                "--dir",
                str(DIR),
                "--title",
                title,
                "--company",
                company,
                "--source-note",
                note,
            ],
        )
        if result.exit_code != 0:
            raise RuntimeError(result.output or str(result.exception))
        print(result.output.strip())
    except Exception:
        # fallback subprocess with python -c
        raise


REPAIRS = [
    # batch 1 — Bluefin + Allura incomplete
    (
        "opp_01KY8RFAH81M9V30ZVH9TM09T5",
        "AI Systems Developer",
        "Bluefin Resources Pty Limited",
        "manual_validation/jobs/002_bluefin_ai_systems_developer.txt",
    ),
    (
        "opp_01KY8WXQ8HQ4J5G2XTM3XFHGEX",
        "AI Systems Developer",
        "Bluefin Resources Pty Limited",
        "manual_validation/jobs/002_bluefin_ai_systems_developer.txt",
    ),
    (
        "opp_01KY8WWW3AK8KKXAKM5KRZ03VE",
        "AI Engineer",
        "Allura Partners",
        "manual_validation/jobs/001_strong_ai_engineer.txt",
    ),
    # batch 2 — mid roles
    (
        "opp_01KY8WYE6RM54EYV8QT0YXHCQP",
        "Junior Software / DevOps Engineer",
        "Jirotech Pty Ltd",
        "manual_validation/jobs/003_mid_role.txt",
    ),
    (
        "opp_01KY8X103H78C9WXJ2B71KHXHG",
        "Associate AI Product Manager",
        "SEEK Limited",
        "manual_validation/jobs/004_associate_ai_product_manager.txt",
    ),
    (
        "opp_01KY8X1S0BC20YEX2QDAGAKEEH",
        "Network Engineer- Automation & AI",
        "Capgemini Australia Pty Ltd",
        "manual_validation/jobs/005_network_engineer_automation_ai.txt",
    ),
    (
        "opp_01KY8X38A0QEFV3PQCV7V68WSD",
        "Technology and Automation Lead",
        "Buildlab",
        "manual_validation/jobs/007_technology_and_automation_lead.txt",
    ),
    # batch 3
    (
        "opp_01KY8X3XQ5NP8JKTXEKQ1J8GR0",
        "AI Adoption Specialist",
        "REPURPOSE IT P/L",
        "manual_validation/jobs/008_repurpose_it_ai_adoption_specialist.txt",
    ),
    (
        "opp_01KY8X4NPVYNZ4W27ZN9MEDV3Q",
        "Senior AI Automation Engineer – Digital",
        "Forever New Clothing",
        "manual_validation/jobs/009_forever_new_senior_ai_automation_engineer_digital.txt",
    ),
    (
        "opp_01KY8X5A6VFW3RK70WXNX0A36P",
        "AI Quality & Systems Reliability Engineer",
        "Pisell",
        "manual_validation/jobs/010_pisell_ai_quality_systems_reliability_engineer.txt",
    ),
    (
        "opp_01KY8X66C3NSYXJ4E2RNTMMKM5",
        "AI Engineer",
        "Officeworks",
        "manual_validation/jobs/011_officeworks_ai_engineer.txt",
    ),
    # batch 4 — Maincode incomplete + pay.com.au
    (
        "opp_01KY8X6V6N32558CDNXW0RXW7V",
        "AI Infrastructure Engineer",
        "Maincode",
        "manual_validation/jobs/012_maincode_ai_infrastructure_engineer.txt",
    ),
    (
        "opp_01KY8YA5KWQWDFBEQ68N71PDEM",
        "AI Infrastructure Engineer",
        "Maincode",
        "manual_validation/jobs/012_maincode_ai_infrastructure_engineer.txt",
    ),
    (
        "opp_01KY8X7SSERDT9BGAHQ71RF6F3",
        "AI Automation Engineer",
        "pay.com.au",
        "manual_validation/jobs/013_pay_com_au_ai_automation_engineer.txt",
    ),
]

BATCHES = [
    REPAIRS[0:3],
    REPAIRS[3:7],
    REPAIRS[7:11],
    REPAIRS[11:14],
]


def validate_batch(before: dict, repaired_ids: list[str]) -> None:
    after = snapshot()
    assert after["count"] == before["count"], (before["count"], after["count"])
    assert after["ids"] == before["ids"]
    for oid in before["ids"]:
        assert after["decisions"][oid] == before["decisions"][oid], oid
        assert after["statuses"][oid] == before["statuses"][oid], oid
        # review history only grows for repaired ids
        if oid in repaired_ids:
            assert after["review_action_counts"][oid] == before["review_action_counts"][oid] + 1, oid
        else:
            assert after["review_action_counts"][oid] == before["review_action_counts"][oid], oid
    svc = OpportunityService.from_path(DIR)
    for oid in repaired_ids:
        o = svc.get(oid)
        assert o.identity.title and o.identity.company, oid
        print(f"  OK show-fields {oid}: {o.identity.company} / {o.identity.title}")
    print(
        f"  STORE count={after['count']} identity_complete={after['identity_complete']}"
    )


def run_repairs() -> None:
    from typer.testing import CliRunner
    from career_intelligence.cli.main import app

    runner = CliRunner()
    baseline = snapshot()
    print("BASELINE", json.dumps({k: baseline[k] for k in ("count", "identity_complete")}))
    posting_hashes = {oid: posting_hash(oid) for oid in baseline["ids"]}

    for i, batch in enumerate(BATCHES, start=1):
        before = snapshot()
        print(f"\n=== REPAIR BATCH {i}/{len(BATCHES)} ({len(batch)} records) ===")
        repaired: list[str] = []
        for oid, title, company, note in batch:
            result = runner.invoke(
                app,
                [
                    "opportunity",
                    "repair-identity",
                    oid,
                    "--dir",
                    str(DIR),
                    "--title",
                    title,
                    "--company",
                    company,
                    "--source-note",
                    note,
                ],
            )
            print(result.output.strip())
            if result.exit_code != 0:
                raise SystemExit(f"FAILED {oid}: {result.output}")
            repaired.append(oid)
        validate_batch(before, repaired)
        # posting hashes unchanged
        for oid in baseline["ids"]:
            assert posting_hash(oid) == posting_hashes[oid], f"posting mutated {oid}"
        print(f"BATCH {i} VALIDATED")

    final = snapshot()
    print("\n=== 2B COMPLETE ===")
    print(json.dumps({k: final[k] for k in ("count", "identity_complete")}, indent=2))


if __name__ == "__main__":
    run_repairs()
