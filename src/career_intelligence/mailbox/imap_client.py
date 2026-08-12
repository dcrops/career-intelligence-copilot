"""Yahoo IMAP client for job-alert folder fetch (FR-019 M1).

Uses ``BODY.PEEK[]`` so messages are not marked \\Seen by default.
Injectable connection factory for tests — no live Yahoo in CI.
"""

from __future__ import annotations

import email
import hashlib
import imaplib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from typing import Protocol

from .config import MailboxConfig, redact_secrets
from .errors import MailboxImapError
from .models import IngestedMailMessage

ImapFactory = Callable[[MailboxConfig], "ImapConnection"]


class ImapConnection(Protocol):
    def login(self, user: str, password: str) -> None: ...

    def select(self, mailbox: str, readonly: bool = False) -> tuple[str, list[bytes]]: ...

    def uid(self, command: str, *args: str) -> tuple[str, list[bytes | None]]: ...

    def logout(self) -> None: ...

    def noop(self) -> tuple[str, list[bytes]]: ...


_UIDVALIDITY_RE = re.compile(r"UIDVALIDITY\s+(\d+)", re.IGNORECASE)


def _ssl_imap_connection(config: MailboxConfig) -> imaplib.IMAP4_SSL:
    """Open TLS IMAP using the OS trust store (do not disable verification)."""
    import ssl

    try:
        import truststore

        ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        ctx = ssl.create_default_context()
    return imaplib.IMAP4_SSL(config.host, config.port, ssl_context=ctx)


def _decode_header_value(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:  # noqa: BLE001
        return raw


def _message_id_from_rfc822(raw: bytes) -> str:
    msg = email.message_from_bytes(raw)
    mid = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
    if mid:
        return mid
    # Stable fallback when provider omits Message-ID
    digest = hashlib.sha256(raw).hexdigest()[:24]
    return f"<missing-message-id-{digest}@cic.local>"


def _received_at_from_rfc822(raw: bytes) -> datetime | None:
    msg = email.message_from_bytes(raw)
    date_hdr = msg.get("Date")
    if not date_hdr:
        return None
    try:
        dt = parsedate_to_datetime(date_hdr)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        return None


def _parse_uidvalidity(select_data: Sequence[bytes | None]) -> int | None:
    for item in select_data:
        if not item:
            continue
        text = item.decode("utf-8", errors="replace") if isinstance(item, bytes) else str(item)
        match = _UIDVALIDITY_RE.search(text)
        if match:
            return int(match.group(1))
    return None


@dataclass
class YahooImapMailboxClient:
    """Fetch full RFC822 messages from the configured Yahoo folder."""

    config: MailboxConfig
    connection_factory: ImapFactory = _ssl_imap_connection

    def fetch_messages(self) -> list[IngestedMailMessage]:
        conn: ImapConnection | None = None
        try:
            conn = self.connection_factory(self.config)
            try:
                conn.login(self.config.user, self.config.app_password)
            except Exception as exc:  # noqa: BLE001
                raise MailboxImapError(
                    "IMAP authentication failed",
                    detail=redact_secrets(str(exc), self.config),
                ) from exc

            typ, data = conn.select(f'"{self.config.folder}"', readonly=True)
            if typ != "OK":
                # Retry without quotes for simple folder names
                typ, data = conn.select(self.config.folder, readonly=True)
            if typ != "OK":
                raise MailboxImapError(
                    f"Failed to select mailbox folder {self.config.folder!r}",
                    detail=redact_secrets(repr(data), self.config),
                )

            uidvalidity = _parse_uidvalidity(data or [])
            # STATUS UIDVALIDITY as fallback
            if uidvalidity is None and hasattr(conn, "status"):
                try:
                    st_typ, st_data = conn.status(self.config.folder, "(UIDVALIDITY)")  # type: ignore[attr-defined]
                    if st_typ == "OK":
                        uidvalidity = _parse_uidvalidity(st_data or [])
                except Exception:  # noqa: BLE001
                    uidvalidity = None

            typ, data = conn.uid("SEARCH", None, "ALL")
            if typ != "OK" or not data or data[0] is None:
                return []

            uid_bytes = data[0]
            if not isinstance(uid_bytes, (bytes, bytearray)):
                return []
            uids = [u for u in uid_bytes.decode("ascii", errors="ignore").split() if u]
            messages: list[IngestedMailMessage] = []
            for uid_str in uids:
                # BODY.PEEK[] avoids setting \Seen
                fetch_typ, fetch_data = conn.uid("FETCH", uid_str, "(BODY.PEEK[])")
                if fetch_typ != "OK" or not fetch_data:
                    continue
                raw = _extract_rfc822(fetch_data)
                if raw is None:
                    continue
                uid = int(uid_str)
                messages.append(
                    IngestedMailMessage(
                        message_id=_message_id_from_rfc822(raw),
                        folder=self.config.folder,
                        uid=uid,
                        uidvalidity=uidvalidity,
                        raw_rfc822=raw,
                        content_sha256=hashlib.sha256(raw).hexdigest(),
                        received_at=_received_at_from_rfc822(raw),
                        source="imap",
                    )
                )

            if self.config.mark_seen:
                # Opt-in only — default leaves unread
                for msg in messages:
                    if msg.uid is None:
                        continue
                    try:
                        conn.uid("STORE", str(msg.uid), "+FLAGS", "(\\Seen)")
                    except Exception:  # noqa: BLE001
                        pass

            return messages
        except MailboxImapError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MailboxImapError(
                "IMAP mailbox operation failed",
                detail=redact_secrets(str(exc), self.config),
            ) from exc
        finally:
            if conn is not None:
                try:
                    conn.logout()
                except Exception:  # noqa: BLE001
                    pass


def _extract_rfc822(fetch_data: list[object]) -> bytes | None:
    """Extract RFC822 bytes from imaplib FETCH response tuples."""
    for item in fetch_data:
        if isinstance(item, tuple) and len(item) >= 2:
            payload = item[1]
            if isinstance(payload, (bytes, bytearray)):
                return bytes(payload)
        if isinstance(item, (bytes, bytearray)) and b"\n" in item:
            # Some servers return a single blob
            return bytes(item)
    return None
