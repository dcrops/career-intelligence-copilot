"""Mailbox intake errors (FR-019 M1)."""

from __future__ import annotations


class MailboxError(Exception):
    """Base error for mailbox intake."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


class MailboxConfigError(MailboxError):
    """Missing or invalid mailbox configuration / secrets."""


class MailboxImapError(MailboxError):
    """IMAP connection, auth, or fetch failure."""


class MailboxIntakeError(MailboxError):
    """Intake orchestration failure."""
