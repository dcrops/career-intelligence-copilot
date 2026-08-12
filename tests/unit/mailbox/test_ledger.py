"""Email-level ledger tests (FR-019 M1)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from career_intelligence.mailbox.ledger import EmailIntakeLedger
from career_intelligence.mailbox.models import IngestedMailMessage


def _msg(
    *,
    message_id: str = "<id-1@yahoo>",
    folder: str = "CIC Job Alerts",
    uid: int | None = 10,
    uidvalidity: int | None = 99,
    raw: bytes = b"raw-bytes-1",
) -> IngestedMailMessage:
    return IngestedMailMessage(
        message_id=message_id,
        folder=folder,
        uid=uid,
        uidvalidity=uidvalidity,
        raw_rfc822=raw,
        content_sha256=hashlib.sha256(raw).hexdigest(),
        source="imap",
    )


def test_ledger_records_and_skips_same_message(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    ledger = EmailIntakeLedger(path)
    message = _msg()
    assert ledger.contains(message) is False
    ledger.record(message, outcome_summary="acquired=1")
    assert ledger.contains(message) is True

    reloaded = EmailIntakeLedger(path)
    assert reloaded.contains(message) is True


def test_ledger_message_id_primary(tmp_path: Path) -> None:
    ledger = EmailIntakeLedger(tmp_path / "l.json")
    first = _msg(message_id="<same@id>", uid=1)
    second = _msg(message_id="<same@id>", uid=999, raw=b"different-bytes")
    ledger.record(first)
    assert ledger.contains(second) is True


def test_ledger_folder_uid_when_needed(tmp_path: Path) -> None:
    ledger = EmailIntakeLedger(tmp_path / "l.json")
    first = _msg(message_id="", folder="CIC Job Alerts", uid=5, uidvalidity=7)
    ledger.record(first)
    again = _msg(message_id="", folder="CIC Job Alerts", uid=5, uidvalidity=7, raw=b"x")
    assert ledger.contains(again) is True
    other = _msg(message_id="", folder="CIC Job Alerts", uid=6, uidvalidity=7, raw=b"y")
    assert ledger.contains(other) is False


def test_different_emails_not_suppressed(tmp_path: Path) -> None:
    """Same job in two alert emails must not be blocked at email ledger layer."""
    ledger = EmailIntakeLedger(tmp_path / "l.json")
    a = _msg(message_id="<alert-a@linkedin>", uid=1, raw=b"digest-a")
    b = _msg(message_id="<alert-b@linkedin>", uid=2, raw=b"digest-b")
    ledger.record(a)
    assert ledger.contains(b) is False
