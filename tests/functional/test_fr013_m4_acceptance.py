"""Functional acceptance coverage for FR-013 M4 reporting + multi-opp journey."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.opportunities import OpportunityService
from tests.unit.opportunities.helpers import trusted_pipeline

runner = CliRunner()


def _create(tmp_path: Path, *, title: str, company: str, raw: str) -> str:
    posting, analysis, assessment, match, strategy = trusted_pipeline(
        title=title,
        company=company,
        raw_text=raw,
        source_url=f"https://example.com/jobs/{title.replace(' ', '-').lower()}",
    )
    service = OpportunityService.from_path(tmp_path / "opportunities")
    opportunity = service.create_from_strategy(
        posting=posting,
        job_analysis=analysis,
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    service.record_decision(opportunity.opportunity_id, "apply")
    return opportunity.opportunity_id


def test_fr013_m4_multi_opportunity_acceptance(tmp_path: Path) -> None:
    common = [
        "--dir",
        str(tmp_path / "opportunities"),
        "--events-dir",
        str(tmp_path / "pipeline_events"),
    ]
    offer_id = _create(
        tmp_path,
        title="Offer Role",
        company="OfferCo",
        raw="Offer Role at OfferCo. Python AI engineer Melbourne hybrid.",
    )
    reject_id = _create(
        tmp_path,
        title="Reject Role",
        company="RejectCo",
        raw="Reject Role at RejectCo. Python AI engineer Melbourne hybrid.",
    )
    withdraw_id = _create(
        tmp_path,
        title="Withdraw Role",
        company="WithdrawCo",
        raw="Withdraw Role at WithdrawCo. Python AI engineer Melbourne hybrid.",
    )

    for argv in [
        ["pipeline", "submit", offer_id, *common],
        ["pipeline", "acknowledge", offer_id, *common],
        ["pipeline", "interview", offer_id, *common, "--stage", "recruiter"],
        ["pipeline", "interview", offer_id, *common, "--stage", "technical"],
        ["pipeline", "offer", offer_id, *common],
        ["pipeline", "accept", offer_id, *common],
    ]:
        assert runner.invoke(app, argv).exit_code == 0, argv

    assert runner.invoke(app, ["pipeline", "submit", reject_id, *common]).exit_code == 0
    assert runner.invoke(app, ["pipeline", "reject", reject_id, *common]).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "pipeline",
                "correct",
                reject_id,
                *common,
                "--to",
                "submitted",
                "--note",
                "wrong company email",
                "--outcome",
                "pending",
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["pipeline", "note", reject_id, "waiting on recruiter", *common],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "pipeline",
                "evidence",
                reject_id,
                *common,
                "--channel",
                "email",
                "--note",
                "thread saved",
            ],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["pipeline", "reject", reject_id, *common]).exit_code == 0

    assert (
        runner.invoke(app, ["pipeline", "submit", withdraw_id, *common]).exit_code == 0
    )
    assert (
        runner.invoke(
            app,
            ["pipeline", "follow-up", withdraw_id, *common, "--date", "2026-08-01"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["pipeline", "withdraw", withdraw_id, *common]).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["pipeline", "check", withdraw_id, *common]).exit_code == 0
    )

    report = runner.invoke(app, ["pipeline", "report", *common])
    assert report.exit_code == 0, report.output
    assert "accepted: 1" in report.output
    assert "rejected: 1" in report.output
    assert "withdrawn: 1" in report.output

    export_path = tmp_path / "pipeline.csv"
    exported = runner.invoke(
        app,
        ["pipeline", "export", *common, "--output", str(export_path)],
    )
    assert exported.exit_code == 0
    csv_text = export_path.read_text(encoding="utf-8-sig")
    assert offer_id in csv_text
    assert reject_id in csv_text
    assert withdraw_id in csv_text
