"""Mailbox intake orchestration → FR-018 (FR-019 M1).

Fetches messages (IMAP or drop-folder), applies email-level ledger, materialises
``.eml`` files, expands via existing ``opportunity_sources_from_email_file``, and
calls ``ThinDiscoveryIngress`` with fail-closed card-only policy enabled.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from career_intelligence.discovery import (
    DiscoveryRequest,
    ThinDiscoveryIngress,
    opportunity_sources_from_email_file,
)
from career_intelligence.discovery.errors import (
    DiscoveryUnsupportedSourceError,
    DiscoveryValidationError,
)
from career_intelligence.discovery.models import DiscoveryOutcome
from career_intelligence.orchestration.runner import ApplicationWorkflowRunner
from career_intelligence.opportunities.service import OpportunityService

from .config import MailboxConfig, load_mailbox_config
from .drop_folder import load_drop_folder_messages
from .errors import MailboxConfigError, MailboxIntakeError
from .imap_client import YahooImapMailboxClient
from .ledger import DEFAULT_LEDGER_PATH, EmailIntakeLedger
from .models import IngestedMailMessage, IntakeMessageOutcome, MailboxIntakeResult

RunnerFactory = Callable[[], ApplicationWorkflowRunner]


@dataclass
class MailboxIntakeService:
    """Compose mailbox obtainment with frozen FR-018 discovery ingress."""

    opportunities: OpportunityService
    runner_factory: RunnerFactory
    ledger: EmailIntakeLedger
    config: MailboxConfig | None = None
    imap_client: YahooImapMailboxClient | None = None
    offline_fixture_marker: str | None = None
    force: bool = False
    """When True, still expands emails even if ledger hit (testing / recovery)."""

    def run(
        self,
        *,
        drop_folder: Path | None = None,
        messages: Sequence[IngestedMailMessage] | None = None,
    ) -> MailboxIntakeResult:
        """Process IMAP and/or drop-folder messages into FR-018 discovery."""
        batch: list[IngestedMailMessage] = []
        if messages is not None:
            batch.extend(messages)
        elif drop_folder is not None:
            batch.extend(load_drop_folder_messages(drop_folder))
        else:
            if self.config is None:
                raise MailboxIntakeError(
                    "MailboxConfig required for IMAP intake "
                    "(or pass drop_folder=/messages=)"
                )
            client = self.imap_client or YahooImapMailboxClient(self.config)
            batch.extend(client.fetch_messages())

        ingress = ThinDiscoveryIngress(
            opportunities=self.opportunities,
            runner_factory=self.runner_factory,
            offline_fixture_marker=self.offline_fixture_marker,
            fail_closed_on_card_only=True,
        )

        result = MailboxIntakeResult()
        for message in batch:
            result.messages.append(self._process_one(message, ingress))
        return result

    def _process_one(
        self,
        message: IngestedMailMessage,
        ingress: ThinDiscoveryIngress,
    ) -> IntakeMessageOutcome:
        if not self.force and self.ledger.contains(message):
            return IntakeMessageOutcome(
                message=message,
                status="skipped_ledger",
            )

        with tempfile.TemporaryDirectory(prefix="cic_mailbox_") as tmp:
            eml_path = Path(tmp) / "alert.eml"
            eml_path.write_bytes(message.raw_rfc822)
            try:
                sources = opportunity_sources_from_email_file(eml_path)
            except (DiscoveryValidationError, DiscoveryUnsupportedSourceError) as exc:
                summary = f"parse_failed: {exc}"
                self.ledger.record(
                    message,
                    status="processed",
                    outcome_summary=summary,
                )
                return IntakeMessageOutcome(
                    message=message,
                    status="failed",
                    error=str(exc),
                    sources_count=0,
                )
            except Exception as exc:  # noqa: BLE001
                # Do not ledger — allow retry after unexpected crash-class errors
                return IntakeMessageOutcome(
                    message=message,
                    status="failed",
                    error=str(exc),
                )

            if not sources:
                summary = "no_jobs"
                self.ledger.record(
                    message,
                    status="processed",
                    outcome_summary=summary,
                )
                return IntakeMessageOutcome(
                    message=message,
                    status="failed",
                    error="no jobs in email",
                    sources_count=0,
                )

            outcome = ingress.discover(
                DiscoveryRequest(sources=sources, force=self.force)
            )
            summary = (
                f"acquired={outcome.acquired_count} "
                f"skipped={outcome.skipped_count} "
                f"failed={outcome.failed_count}"
            )
            self.ledger.record(
                message,
                status="processed",
                outcome_summary=summary,
            )
            return IntakeMessageOutcome(
                message=message,
                status="processed",
                discovery=outcome,
                sources_count=len(sources),
            )


def run_mailbox_intake(
    *,
    opportunities: OpportunityService,
    runner_factory: RunnerFactory,
    drop_folder: Path | None = None,
    secrets_path: Path | None = None,
    ledger_path: Path | None = None,
    offline_fixture_marker: str | None = None,
    force: bool = False,
    config: MailboxConfig | None = None,
    messages: Sequence[IngestedMailMessage] | None = None,
) -> MailboxIntakeResult:
    """Convenience entry: load config when needed and run intake."""
    resolved_config = config
    if messages is None and drop_folder is None and resolved_config is None:
        try:
            resolved_config = load_mailbox_config(secrets_path=secrets_path)
        except MailboxConfigError:
            raise

    service = MailboxIntakeService(
        opportunities=opportunities,
        runner_factory=runner_factory,
        ledger=EmailIntakeLedger(ledger_path or DEFAULT_LEDGER_PATH),
        config=resolved_config,
        offline_fixture_marker=offline_fixture_marker,
        force=force,
    )
    return service.run(drop_folder=drop_folder, messages=messages)
