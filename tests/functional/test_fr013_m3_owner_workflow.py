"""Functional owner journey for FR-013 M3 pipeline CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.pipeline import (
    JsonDirectoryPipelineEventStore,
    PipelineTrackingService,
)
from career_intelligence.opportunities import OpportunityService
from tests.unit.opportunities.helpers import create_opportunity

runner = CliRunner()


def test_fr013_m3_owner_journey(tmp_path: Path) -> None:
    opportunities, opportunity, _ = create_opportunity(tmp_path / "opportunities")
    oid = opportunity.opportunity_id
    common = [
        "--dir",
        str(tmp_path / "opportunities"),
        "--events-dir",
        str(tmp_path / "pipeline_events"),
    ]

    # Apply decision exists outside pipeline; mark preparing then submit.
    opportunities.record_decision(oid, "apply", notes="pursue")
    steps = [
        ["pipeline", "preparing", oid, *common, "--note", "package in progress"],
        ["pipeline", "submit", oid, *common, "--channel", "linkedin", "--note", "sent"],
        ["pipeline", "acknowledge", oid, *common, "--note", "auto-reply"],
        ["pipeline", "interview", oid, *common, "--stage", "recruiter", "--note", "phone"],
        [
            "pipeline",
            "interview",
            oid,
            *common,
            "--stage",
            "technical",
            "--note",
            "coding",
        ],
        [
            "pipeline",
            "interview",
            oid,
            *common,
            "--stage",
            "other",
            "--note",
            "final interview",
        ],
        ["pipeline", "reject", oid, *common, "--reason", "team fit"],
        [
            "pipeline",
            "correct",
            oid,
            *common,
            "--to",
            "interviewing",
            "--note",
            "rejection was premature",
            "--outcome",
            "pending",
        ],
        ["pipeline", "offer", oid, *common, "--detail", "verbal"],
        ["pipeline", "follow-up", oid, *common, "--date", "2026-08-25"],
        ["pipeline", "note", oid, "excited but cautious", *common],
    ]
    for argv in steps:
        result = runner.invoke(app, argv)
        assert result.exit_code == 0, f"{argv}: {result.output}"

    show = runner.invoke(app, ["pipeline", "show", oid, *common])
    assert show.exit_code == 0
    assert "status: offer" in show.output
    assert "consistency: ok" in show.output

    history = runner.invoke(app, ["pipeline", "history", oid, *common])
    assert history.exit_code == 0
    assert "Status -> submitted" in history.output
    assert "Evidence" in history.output or "Acknowledgement" in history.output or "auto-reply" in history.output
    assert "Correction:" in history.output
    assert "Status -> offer" in history.output
    assert "Note" in history.output

    check = runner.invoke(app, ["pipeline", "check", oid, *common])
    assert check.exit_code == 0
    assert "Pipeline Consistent" in check.output

    # Append-only: history length matches step count (each command appends one entry).
    tracking = PipelineTrackingService(
        opportunities=OpportunityService.from_path(tmp_path / "opportunities"),
        events=JsonDirectoryPipelineEventStore(tmp_path / "pipeline_events"),
    )
    assert len(tracking.list_events(oid)) == len(steps)
