"""Mailbox intake → FR-018 integration (FR-019 M1)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from career_intelligence.discovery import (
    EmailAcquisitionAdapter,
    FakeHttpClient,
    HttpFetchResponse,
)
from career_intelligence.discovery.email_parse import email_locator
from career_intelligence.job_analysis.fixtures import MARKER_AI_ENGINEER
from career_intelligence.mailbox.drop_folder import load_drop_folder_messages
from career_intelligence.mailbox.intake import MailboxIntakeService
from career_intelligence.mailbox.ledger import EmailIntakeLedger
from career_intelligence.orchestration import JsonDirectoryCheckpointStore
from career_intelligence.orchestration.acquisition import AcquisitionError
from career_intelligence.opportunities import OpportunityService
from tests.unit.orchestration.m1_helpers import offline_runner

FIXTURES = Path(__file__).parents[2] / "fixtures" / "discovery"


def test_drop_folder_intake_reuses_fr018_and_ledgers(tmp_path: Path) -> None:
    drop = tmp_path / "drop"
    drop.mkdir()
    shutil.copy(FIXTURES / "seek_job_alert.eml", drop / "seek.eml")
    opportunities = OpportunityService.from_path(tmp_path / "opps")
    ledger = EmailIntakeLedger(tmp_path / "ledger.json")

    service = MailboxIntakeService(
        opportunities=opportunities,
        runner_factory=lambda: offline_runner(
            opportunities_dir=tmp_path / "opps",
            store=JsonDirectoryCheckpointStore(tmp_path / "runs"),
        ),
        ledger=ledger,
        offline_fixture_marker=MARKER_AI_ENGINEER,
    )
    first = service.run(drop_folder=drop)
    assert first.processed_count == 1
    assert first.messages[0].discovery is not None
    assert first.messages[0].discovery.acquired_count >= 1

    second = service.run(drop_folder=drop)
    assert second.skipped_count == 1
    assert second.processed_count == 0


def test_fail_closed_on_card_only_after_enrich_failure() -> None:
    locator = email_locator(FIXTURES / "linkedin_job_alert_comm.eml", 0)
    job_url = "https://www.linkedin.com/jobs/view/4381552675"
    client = FakeHttpClient(
        responses={
            job_url: HttpFetchResponse(
                url=job_url,
                status_code=403,
                body=b"blocked",
                content_type="text/html",
            )
        },
        calls=[],
    )
    with pytest.raises(AcquisitionError, match="Insufficient"):
        EmailAcquisitionAdapter(
            locator=locator,
            http_client=client,
            fail_closed_on_card_only=True,
        ).acquire()


def test_fail_soft_default_preserved_for_fr018() -> None:
    locator = email_locator(FIXTURES / "linkedin_job_alert_comm.eml", 0)
    job_url = "https://www.linkedin.com/jobs/view/4381552675"
    client = FakeHttpClient(
        responses={
            job_url: HttpFetchResponse(
                url=job_url,
                status_code=403,
                body=b"blocked",
                content_type="text/html",
            )
        },
        calls=[],
    )
    result = EmailAcquisitionAdapter(
        locator=locator,
        http_client=client,
        fail_closed_on_card_only=False,
    ).acquire()
    assert any("job_url_enrichment_failed" in w for w in result.warnings)
    assert result.raw_content


def test_load_drop_folder_messages(tmp_path: Path) -> None:
    drop = tmp_path / "d"
    drop.mkdir()
    shutil.copy(FIXTURES / "indeed_job_alert.eml", drop / "indeed.eml")
    messages = load_drop_folder_messages(drop)
    assert len(messages) == 1
    assert messages[0].source == "drop_folder"
    assert messages[0].raw_rfc822
