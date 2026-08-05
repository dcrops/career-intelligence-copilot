"""CLI tests for FR-013 M3 owner pipeline workflow."""

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


def _workspace(tmp_path: Path) -> tuple[str, list[str]]:
    opportunities, opportunity, _ = create_opportunity(tmp_path / "opportunities")
    _ = opportunities
    common = [
        "--dir",
        str(tmp_path / "opportunities"),
        "--events-dir",
        str(tmp_path / "pipeline_events"),
    ]
    return opportunity.opportunity_id, common


def test_pipeline_submit_show_history_list(tmp_path: Path) -> None:
    oid, common = _workspace(tmp_path)
    submit = runner.invoke(app, ["pipeline", "submit", oid, *common, "--note", "sent"])
    assert submit.exit_code == 0, submit.output
    assert "Application Submitted" in submit.output
    assert "status: submitted" in submit.output

    show = runner.invoke(app, ["pipeline", "show", oid, *common])
    assert show.exit_code == 0, show.output
    assert "Current Pipeline" in show.output
    assert "consistency: ok" in show.output

    history = runner.invoke(app, ["pipeline", "history", oid, *common])
    assert history.exit_code == 0, history.output
    assert "Status -> submitted" in history.output
    assert "event_id" not in history.output  # hidden by default

    listed = runner.invoke(app, ["pipeline", "list", *common])
    assert listed.exit_code == 0, listed.output
    assert oid in listed.output
    assert "submitted" in listed.output


def test_pipeline_interview_reject_correct_offer(tmp_path: Path) -> None:
    oid, common = _workspace(tmp_path)
    assert runner.invoke(app, ["pipeline", "submit", oid, *common]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["pipeline", "acknowledge", oid, *common, "--note", "got email"],
        ).exit_code
        == 0
    )
    interview = runner.invoke(
        app,
        ["pipeline", "interview", oid, *common, "--stage", "technical"],
    )
    assert interview.exit_code == 0, interview.output
    assert "status: interviewing" in interview.output

    reject = runner.invoke(app, ["pipeline", "reject", oid, *common, "--reason", "fit"])
    assert reject.exit_code == 0, reject.output
    assert "status: rejected" in reject.output

    correct = runner.invoke(
        app,
        [
            "pipeline",
            "correct",
            oid,
            *common,
            "--to",
            "interviewing",
            "--note",
            "mistaken rejection",
            "--outcome",
            "pending",
        ],
    )
    assert correct.exit_code == 0, correct.output
    assert "Pipeline Corrected" in correct.output

    offer = runner.invoke(app, ["pipeline", "offer", oid, *common])
    assert offer.exit_code == 0, offer.output
    assert "status: offer" in offer.output

    history = runner.invoke(app, ["pipeline", "history", oid, *common, "--verbose"])
    assert "Correction:" in history.output
    assert "id=ple_" in history.output


def test_pipeline_follow_up_and_note(tmp_path: Path) -> None:
    oid, common = _workspace(tmp_path)
    assert runner.invoke(app, ["pipeline", "submit", oid, *common]).exit_code == 0
    follow = runner.invoke(
        app,
        ["pipeline", "follow-up", oid, *common, "--date", "2026-08-20"],
    )
    assert follow.exit_code == 0, follow.output
    note = runner.invoke(app, ["pipeline", "note", oid, "owner reflection", *common])
    assert note.exit_code == 0, note.output
    history = runner.invoke(app, ["pipeline", "history", oid, *common])
    assert "Follow-up -> 2026-08-20" in history.output
    assert "Note" in history.output


def test_pipeline_interview_before_submit_fails(tmp_path: Path) -> None:
    oid, common = _workspace(tmp_path)
    result = runner.invoke(
        app,
        ["pipeline", "interview", oid, *common, "--stage", "recruiter"],
    )
    assert result.exit_code == 1
    assert "submission" in result.output.lower()


def test_pipeline_attempt_id_is_evidence_only(tmp_path: Path) -> None:
    oid, common = _workspace(tmp_path)
    attempt = "sub_01ARZ3NDEKTSV4RRFFQ69G5FAA"
    result = runner.invoke(
        app,
        [
            "pipeline",
            "submit",
            oid,
            *common,
            "--attempt-id",
            attempt,
            "--channel",
            "manual",
        ],
    )
    assert result.exit_code == 0, result.output
    assert f"submission_attempt_id: {attempt}" in result.output
    # Status advanced only because owner ran submit — not because an attempt existed.
    opportunities = OpportunityService.from_path(tmp_path / "opportunities")
    assert opportunities.get(oid).status == "submitted"
    events = JsonDirectoryPipelineEventStore(tmp_path / "pipeline_events")
    tracking = PipelineTrackingService(opportunities=opportunities, events=events)
    assert len(tracking.list_events(oid)) == 1
