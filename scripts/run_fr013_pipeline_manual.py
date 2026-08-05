#!/usr/bin/env python3
"""Manual validation for FR-013 pipeline tracking.

Commands:
  demo     — M2 dual-write smoke (service API)
  journey  — M3 owner CLI lifecycle (cic pipeline)
  accept   — M4 multi-opportunity acceptance + report/export

Examples:
  python scripts/run_fr013_pipeline_manual.py demo --workspace data/_fr013_m2_manual
  python scripts/run_fr013_pipeline_manual.py journey --workspace data/_fr013_m3_manual
  python scripts/run_fr013_pipeline_manual.py accept --workspace data/_fr013_m4_manual
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.opportunities import OpportunityService
from career_intelligence.pipeline import (
    JsonDirectoryPipelineEventStore,
    PipelineEvidence,
    PipelinePartialWriteError,
    PipelineTrackingService,
    new_pipeline_event_id,
)
from tests.unit.opportunities.helpers import create_opportunity, trusted_pipeline
from tests.unit.pipeline.helpers_m2 import CountingFailStore


def _run_demo(workspace: Path) -> int:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    opportunities, opportunity, _ = create_opportunity(workspace / "opportunities")
    events = JsonDirectoryPipelineEventStore(workspace / "pipeline_events")
    tracking = PipelineTrackingService(opportunities=opportunities, events=events)
    opp_id = opportunity.opportunity_id
    now = datetime.now(UTC)

    print(f"opportunity_id={opp_id}")
    tracking.advance_status(
        opp_id, "preparing", evidence=PipelineEvidence(note="M2 demo prep"), occurred_at=now
    )
    tracking.record_submitted(
        opp_id,
        evidence=PipelineEvidence(
            note="M2 demo owner attested submit",
            submitted_at=now,
            channel="manual",
        ),
        occurred_at=now,
    )
    tracking.advance_status(
        opp_id,
        "interviewing",
        evidence=PipelineEvidence(note="M2 demo interview"),
        occurred_at=now,
    )

    flaky = CountingFailStore(opportunities._store, fail_on_save=1)  # noqa: SLF001
    wrapped = OpportunityService(store=flaky)
    recovering = PipelineTrackingService(opportunities=wrapped, events=events)
    event_id = new_pipeline_event_id()
    try:
        recovering.advance_status(
            opp_id,
            "offer",
            evidence=PipelineEvidence(note="inject fail"),
            event_id=event_id,
        )
        print("ERROR: expected PipelinePartialWriteError")
        return 1
    except PipelinePartialWriteError as error:
        print(f"partial_write_ok event_id={error.event_id}")

    flaky._fail_on_save = -1  # noqa: SLF001
    recovered = recovering.apply_stored_event(event_id)
    print(f"recovered_status={recovered.opportunity.status}")
    report = tracking.detect_divergence(opp_id)
    print(f"divergent={report.divergent}")
    if report.divergent or tracking.get_opportunity(opp_id).status != "offer":
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


def _run_journey(workspace: Path) -> int:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    opportunities, opportunity, _ = create_opportunity(workspace / "opportunities")
    oid = opportunity.opportunity_id
    opportunities.record_decision(oid, "apply", notes="M3 journey")
    common = [
        "--dir",
        str(workspace / "opportunities"),
        "--events-dir",
        str(workspace / "pipeline_events"),
    ]
    runner = CliRunner()

    steps: list[list[str]] = [
        ["pipeline", "preparing", oid, *common],
        ["pipeline", "submit", oid, *common, "--channel", "manual", "--note", "sent JD portal"],
        ["pipeline", "acknowledge", oid, *common, "--note", "thanks for applying"],
        ["pipeline", "interview", oid, *common, "--stage", "recruiter", "--note", "phone screen"],
        ["pipeline", "interview", oid, *common, "--stage", "technical"],
        ["pipeline", "interview", oid, *common, "--stage", "other", "--note", "final"],
        ["pipeline", "reject", oid, *common, "--reason", "leveling"],
        [
            "pipeline",
            "correct",
            oid,
            *common,
            "--to",
            "interviewing",
            "--note",
            "HR error — process continues",
            "--outcome",
            "pending",
        ],
        ["pipeline", "offer", oid, *common],
        ["pipeline", "note", oid, "negotiating start date", *common],
        ["pipeline", "history", oid, *common],
        ["pipeline", "show", oid, *common],
        ["pipeline", "list", *common],
        ["pipeline", "check", oid, *common],
    ]

    for argv in steps:
        result = runner.invoke(app, argv)
        print(f"$ cic {' '.join(argv[:3])} ... exit={result.exit_code}")
        print(result.output.rstrip().encode("ascii", errors="replace").decode("ascii"))
        print("---")
        if result.exit_code != 0:
            print("RESULT: FAIL")
            return 1

    print("RESULT: PASS")
    return 0


def _create_named(workspace: Path, *, title: str, company: str, raw: str) -> str:
    posting, analysis, assessment, match, strategy = trusted_pipeline(
        title=title,
        company=company,
        raw_text=raw,
        source_url=f"https://example.com/jobs/{company.lower()}",
    )
    service = OpportunityService.from_path(workspace / "opportunities")
    opportunity = service.create_from_strategy(
        posting=posting,
        job_analysis=analysis,
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    service.record_decision(opportunity.opportunity_id, "apply")
    return opportunity.opportunity_id


def _run_accept(workspace: Path) -> int:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    common = [
        "--dir",
        str(workspace / "opportunities"),
        "--events-dir",
        str(workspace / "pipeline_events"),
    ]
    runner = CliRunner()
    offer_id = _create_named(
        workspace,
        title="Offer Role",
        company="OfferCo",
        raw="Offer Role OfferCo Python AI Melbourne.",
    )
    reject_id = _create_named(
        workspace,
        title="Reject Role",
        company="RejectCo",
        raw="Reject Role RejectCo Python AI Melbourne.",
    )
    withdraw_id = _create_named(
        workspace,
        title="Withdraw Role",
        company="WithdrawCo",
        raw="Withdraw Role WithdrawCo Python AI Melbourne.",
    )

    steps: list[list[str]] = [
        ["pipeline", "submit", offer_id, *common],
        ["pipeline", "acknowledge", offer_id, *common],
        ["pipeline", "interview", offer_id, *common, "--stage", "recruiter"],
        ["pipeline", "interview", offer_id, *common, "--stage", "technical"],
        ["pipeline", "interview", offer_id, *common, "--stage", "other", "--note", "final"],
        ["pipeline", "offer", offer_id, *common],
        ["pipeline", "accept", offer_id, *common],
        ["pipeline", "submit", reject_id, *common],
        ["pipeline", "reject", reject_id, *common, "--reason", "level"],
        [
            "pipeline",
            "correct",
            reject_id,
            *common,
            "--to",
            "submitted",
            "--note",
            "mistaken reject",
            "--outcome",
            "pending",
        ],
        ["pipeline", "note", reject_id, "re-evaluating", *common],
        ["pipeline", "reject", reject_id, *common],
        ["pipeline", "submit", withdraw_id, *common],
        ["pipeline", "follow-up", withdraw_id, *common, "--date", "2026-08-01"],
        ["pipeline", "evidence", withdraw_id, *common, "--note", "portal screenshot"],
        ["pipeline", "withdraw", withdraw_id, *common],
        ["pipeline", "report", *common],
        ["pipeline", "due", *common, "--on", "2026-08-05"],
        [
            "pipeline",
            "export",
            *common,
            "--output",
            str(workspace / "pipeline.csv"),
        ],
        ["pipeline", "list", *common, "--all"],
        ["pipeline", "check", offer_id, *common],
    ]
    for argv in steps:
        result = runner.invoke(app, argv)
        print(f"$ cic {' '.join(argv[:3])} ... exit={result.exit_code}")
        print(result.output.rstrip().encode("ascii", errors="replace").decode("ascii"))
        print("---")
        if result.exit_code != 0:
            print("RESULT: FAIL")
            return 1
    print("RESULT: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo", "journey", "accept"])
    parser.add_argument("--workspace", type=Path, default=None)
    args = parser.parse_args()
    if args.command == "demo":
        return _run_demo(args.workspace or Path("data/_fr013_m2_manual"))
    if args.command == "journey":
        return _run_journey(args.workspace or Path("data/_fr013_m3_manual"))
    return _run_accept(args.workspace or Path("data/_fr013_m4_manual"))


if __name__ == "__main__":
    raise SystemExit(main())
