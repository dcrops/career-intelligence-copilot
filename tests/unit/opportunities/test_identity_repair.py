"""Tests for owner-controlled Opportunity identity repair (OAT-001)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from career_intelligence.cli.main import app
from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.opportunities import (
    OpportunityService,
    OpportunityTransitionError,
    OpportunityValidationError,
)
from career_intelligence.opportunities.errors import OpportunityNotFoundError
from tests.unit.opportunities.helpers import create_opportunity, trusted_pipeline

runner = CliRunner()


def _blank_identity_opportunity(tmp_path: Path):
    posting, analysis, assessment, match, strategy = trusted_pipeline(
        company="Temp",
        title="Temp",
        raw_text="AI Systems Developer\n\nBluefin Resources Pty Limited\nMelbourne",
    )
    blank_posting = JobPosting(raw_text=posting.raw_text)
    service = OpportunityService.from_path(tmp_path)
    opportunity = service.create_from_strategy(
        posting=blank_posting,
        job_analysis=analysis.model_copy(update={"posting": blank_posting}),
        assessment=assessment,
        portfolio_match=match,
        strategy=strategy,
    )
    assert opportunity.identity.title is None
    assert opportunity.identity.company is None
    return service, opportunity


def _posting_sha(service: OpportunityService, opportunity_id: str) -> str:
    artifacts = service.load_artifacts(opportunity_id)
    raw = artifacts.posting.model_dump_json().encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def test_repair_fills_missing_title_and_company(tmp_path: Path) -> None:
    service, opportunity = _blank_identity_opportunity(tmp_path)
    before_hash = _posting_sha(service, opportunity.opportunity_id)
    updated = service.repair_identity(
        opportunity.opportunity_id,
        title="AI Systems Developer",
        company="Bluefin Resources Pty Limited",
        source_note="manual_validation/jobs/002_bluefin_ai_systems_developer.txt",
    )
    assert updated.opportunity_id == opportunity.opportunity_id
    assert updated.identity.title == "AI Systems Developer"
    assert updated.identity.company == "Bluefin Resources Pty Limited"
    assert updated.status == opportunity.status
    assert updated.decision == opportunity.decision
    assert updated.outcome == opportunity.outcome
    assert len(updated.review_actions) == 1
    assert updated.review_actions[0].action == "repair_identity"
    assert "owner_supplied_repair" in (updated.review_actions[0].detail or "")
    assert _posting_sha(service, opportunity.opportunity_id) == before_hash


def test_repair_updates_only_one_missing_field(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(
        tmp_path, company="Maincode", title="Temp Title"
    )
    # Clear company only.
    blanked = opportunity.model_copy(
        update={
            "identity": opportunity.identity.model_copy(update={"company": None}),
        },
        deep=True,
    )
    service._store.save(blanked)  # noqa: SLF001
    updated = service.repair_identity(
        opportunity.opportunity_id,
        company="Maincode",
        title="Temp Title",  # already set — must not conflict when equal
    )
    assert updated.identity.title == "Temp Title"
    assert updated.identity.company == "Maincode"


def test_repair_refuses_silent_overwrite(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(
        tmp_path, company="Maincode", title="AI Infrastructure Engineer"
    )
    with pytest.raises(OpportunityTransitionError, match="title already set"):
        service.repair_identity(
            opportunity.opportunity_id,
            title="Different Title",
            company="Maincode",
        )
    reloaded = service.get(opportunity.opportunity_id)
    assert reloaded.identity.title == "AI Infrastructure Engineer"
    assert reloaded.review_actions == ()


def test_repair_override_replaces_when_requested(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(
        tmp_path, company="Maincode", title="AI Infrastructure Engineer"
    )
    updated = service.repair_identity(
        opportunity.opportunity_id,
        title="AI Infra Engineer",
        override=True,
        source_note="owner correction",
    )
    assert updated.identity.title == "AI Infra Engineer"
    assert updated.identity.company == "Maincode"
    assert updated.review_actions[-1].action == "repair_identity"


def test_repair_idempotent_same_values(tmp_path: Path) -> None:
    service, opportunity = _blank_identity_opportunity(tmp_path)
    first = service.repair_identity(
        opportunity.opportunity_id,
        title="AI Systems Developer",
        company="Bluefin Resources Pty Limited",
    )
    second = service.repair_identity(
        opportunity.opportunity_id,
        title="AI Systems Developer",
        company="Bluefin Resources Pty Limited",
    )
    assert second.identity.title == first.identity.title
    assert second.identity.company == first.identity.company
    assert len(second.review_actions) == 1  # no duplicate audit on no-op


def test_repair_unknown_opportunity_fails(tmp_path: Path) -> None:
    service = OpportunityService.from_path(tmp_path)
    with pytest.raises(OpportunityNotFoundError):
        service.repair_identity(
            "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA",
            title="X",
            company="Y",
        )


def test_repair_requires_title_or_company(tmp_path: Path) -> None:
    service, opportunity = _blank_identity_opportunity(tmp_path)
    with pytest.raises(OpportunityValidationError):
        service.repair_identity(opportunity.opportunity_id)


def test_cli_repair_identity(tmp_path: Path) -> None:
    service, opportunity = _blank_identity_opportunity(tmp_path)
    result = runner.invoke(
        app,
        [
            "opportunity",
            "repair-identity",
            opportunity.opportunity_id,
            "--dir",
            str(tmp_path),
            "--title",
            "AI Systems Developer",
            "--company",
            "Bluefin Resources Pty Limited",
            "--source-note",
            "oat001",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Repaired identity" in result.output
    reloaded = service.get(opportunity.opportunity_id)
    assert reloaded.identity.title == "AI Systems Developer"
    shown = runner.invoke(
        app, ["opportunity", "show", opportunity.opportunity_id, "--dir", str(tmp_path)]
    )
    assert shown.exit_code == 0
    assert "AI Systems Developer" in shown.output
    assert "Bluefin Resources Pty Limited" in shown.output


def test_cli_repair_blocks_overwrite_without_flag(tmp_path: Path) -> None:
    _, opportunity, _ = create_opportunity(
        tmp_path, company="Maincode", title="AI Infrastructure Engineer"
    )
    result = runner.invoke(
        app,
        [
            "opportunity",
            "repair-identity",
            opportunity.opportunity_id,
            "--dir",
            str(tmp_path),
            "--title",
            "Other",
        ],
    )
    assert result.exit_code != 0
    assert "already set" in result.output.lower() or "title" in result.output.lower()
