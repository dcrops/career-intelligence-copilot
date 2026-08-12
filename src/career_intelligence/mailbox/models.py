"""Typed mailbox intake models (FR-019 M1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from career_intelligence.discovery.models import DiscoveryOutcome


@dataclass(frozen=True)
class IngestedMailMessage:
    """One retrieved mailbox (or drop-folder) message before FR-018 hand-off."""

    message_id: str
    folder: str
    uid: int | None
    uidvalidity: int | None
    raw_rfc822: bytes
    content_sha256: str
    received_at: datetime | None = None
    source: str = "imap"
    """``imap`` or ``drop_folder``."""
    path_hint: str | None = None
    """Original path for drop-folder messages."""


@dataclass
class IntakeMessageOutcome:
    """Per-message intake result (email-level, not job-level)."""

    message: IngestedMailMessage
    status: str
    """``processed`` | ``skipped_ledger`` | ``failed``."""
    discovery: DiscoveryOutcome | None = None
    error: str | None = None
    sources_count: int = 0


@dataclass
class MailboxIntakeResult:
    """Batch result for one mailbox / drop-folder intake run."""

    messages: list[IntakeMessageOutcome] = field(default_factory=list)

    @property
    def processed_count(self) -> int:
        return sum(1 for item in self.messages if item.status == "processed")

    @property
    def skipped_count(self) -> int:
        return sum(1 for item in self.messages if item.status == "skipped_ledger")

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.messages if item.status == "failed")
