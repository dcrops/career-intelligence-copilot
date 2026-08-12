"""Email-level intake ledger (FR-019 M1).

Separate from FR-018/FR-009 job identity. Stores only what is required to avoid
re-processing the same mailbox message. No secrets. Gitignored runtime data.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import IngestedMailMessage

DEFAULT_LEDGER_PATH = Path("data") / "mailbox_intake" / "processed.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class LedgerEntry:
    message_id: str
    folder: str
    uid: int | None
    uidvalidity: int | None
    content_sha256: str
    processed_at: str
    status: str
    outcome_summary: str
    source: str = "imap"


class EmailIntakeLedger:
    """Durable JSON ledger of processed alert messages."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_LEDGER_PATH
        self._by_message_id: dict[str, LedgerEntry] = {}
        self._by_folder_uid: dict[tuple[str, int, int], LedgerEntry] = {}
        self._by_hash: dict[str, LedgerEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        entries = raw.get("entries", []) if isinstance(raw, dict) else raw
        for item in entries:
            if not isinstance(item, dict):
                continue
            entry = LedgerEntry(
                message_id=str(item.get("message_id") or ""),
                folder=str(item.get("folder") or ""),
                uid=item.get("uid"),
                uidvalidity=item.get("uidvalidity"),
                content_sha256=str(item.get("content_sha256") or ""),
                processed_at=str(item.get("processed_at") or ""),
                status=str(item.get("status") or "processed"),
                outcome_summary=str(item.get("outcome_summary") or ""),
                source=str(item.get("source") or "imap"),
            )
            self._index(entry)

    def _index(self, entry: LedgerEntry) -> None:
        if entry.message_id:
            self._by_message_id[entry.message_id.casefold()] = entry
        if (
            entry.folder
            and entry.uid is not None
            and entry.uidvalidity is not None
        ):
            self._by_folder_uid[(entry.folder, entry.uidvalidity, entry.uid)] = entry
        if entry.content_sha256:
            self._by_hash[entry.content_sha256] = entry

    def contains(self, message: IngestedMailMessage) -> bool:
        """True when this mailbox message was already processed."""
        if message.message_id and message.message_id.casefold() in self._by_message_id:
            return True
        if (
            message.folder
            and message.uid is not None
            and message.uidvalidity is not None
            and (message.folder, message.uidvalidity, message.uid) in self._by_folder_uid
        ):
            return True
        if message.content_sha256 and message.content_sha256 in self._by_hash:
            # Hash alone only matches drop-folder / missing Message-ID cases when
            # Message-ID and folder+UID did not already decide.
            if not message.message_id and message.uid is None:
                return True
        return False

    def record(
        self,
        message: IngestedMailMessage,
        *,
        status: str = "processed",
        outcome_summary: str = "",
    ) -> LedgerEntry:
        entry = LedgerEntry(
            message_id=message.message_id,
            folder=message.folder,
            uid=message.uid,
            uidvalidity=message.uidvalidity,
            content_sha256=message.content_sha256,
            processed_at=_utc_now_iso(),
            status=status,
            outcome_summary=outcome_summary,
            source=message.source,
        )
        self._index(entry)
        self._persist()
        return entry

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Rebuild unique list from message_id index + folder_uid leftovers
        seen: set[tuple[Any, ...]] = set()
        entries: list[dict[str, Any]] = []
        for entry in list(self._by_message_id.values()) + list(
            self._by_folder_uid.values()
        ):
            key = (
                entry.message_id,
                entry.folder,
                entry.uid,
                entry.uidvalidity,
                entry.content_sha256,
                entry.processed_at,
            )
            if key in seen:
                continue
            seen.add(key)
            entries.append(asdict(entry))
        payload = {"version": 1, "entries": entries}
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
