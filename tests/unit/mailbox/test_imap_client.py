"""Fake IMAP + Yahoo client tests (FR-019 M1)."""

from __future__ import annotations

from career_intelligence.mailbox.config import MailboxConfig
from career_intelligence.mailbox.imap_client import YahooImapMailboxClient


class _FakeImap:
    def __init__(self, rfc822: bytes) -> None:
        self._rfc822 = rfc822
        self.logged_in = False
        self.selected: str | None = None
        self.readonly: bool | None = None
        self.fetch_commands: list[tuple[str, ...]] = []
        self.logged_out = False

    def login(self, user: str, password: str) -> None:
        assert user
        assert password
        self.logged_in = True

    def select(self, mailbox: str, readonly: bool = False) -> tuple[str, list[bytes]]:
        self.selected = mailbox
        self.readonly = readonly
        return "OK", [b"1 (UIDVALIDITY 4242)"]

    def uid(self, command: str, *args: str) -> tuple[str, list[bytes | None]]:
        self.fetch_commands.append((command, *args))
        if command == "SEARCH":
            return "OK", [b"17"]
        if command == "FETCH":
            assert any("BODY.PEEK[]" in a for a in args)
            return "OK", [(b"17 (BODY[] {10}", self._rfc822)]
        if command == "STORE":
            return "OK", [None]
        return "NO", [None]

    def logout(self) -> None:
        self.logged_out = True

    def noop(self) -> tuple[str, list[bytes]]:
        return "OK", [b""]


def _sample_eml() -> bytes:
    return (
        b"From: jobmail@seek.com.au\r\n"
        b"To: owner@yahoo.com\r\n"
        b"Subject: New jobs\r\n"
        b"Message-ID: <seek-alert-1@seek.com.au>\r\n"
        b"Date: Mon, 11 Aug 2026 01:00:00 +0000\r\n"
        b"\r\n"
        b"https://www.seek.com.au/job/93312273\r\n"
    )


def test_imap_fetch_uses_body_peek_and_preserves_message_id() -> None:
    fake = _FakeImap(_sample_eml())
    config = MailboxConfig(
        host="imap.mail.yahoo.com",
        port=993,
        user="owner@yahoo.com",
        app_password="app-pass",
        folder="CIC Job Alerts",
        mark_seen=False,
    )
    client = YahooImapMailboxClient(config, connection_factory=lambda _c: fake)
    messages = client.fetch_messages()
    assert fake.logged_in is True
    assert fake.readonly is True
    assert fake.logged_out is True
    assert any(
        "BODY.PEEK[]" in " ".join(str(part) for part in cmd)
        for cmd in fake.fetch_commands
    )
    assert len(messages) == 1
    assert messages[0].message_id == "<seek-alert-1@seek.com.au>"
    assert messages[0].uid == 17
    assert messages[0].uidvalidity == 4242
    assert messages[0].folder == "CIC Job Alerts"
    assert b"93312273" in messages[0].raw_rfc822
