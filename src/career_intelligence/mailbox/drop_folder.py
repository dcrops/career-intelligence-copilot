"""Drop-folder .eml fallback for mailbox intake (FR-019 M1).

Development / test / manual recovery only — not the production headline.
Feeds the same FR-018 path as IMAP-retrieved MIME.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .models import IngestedMailMessage
from .imap_client import _message_id_from_rfc822, _received_at_from_rfc822


def list_eml_files(directory: Path) -> list[Path]:
    """Sorted ``.eml`` files in a drop folder (non-recursive)."""
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if path.suffix.lower() == ".eml")


def ingested_from_eml_file(
    path: Path,
    *,
    folder: str = "drop_folder",
) -> IngestedMailMessage:
    """Materialise an on-disk ``.eml`` as an ``IngestedMailMessage``."""
    raw = path.read_bytes()
    return IngestedMailMessage(
        message_id=_message_id_from_rfc822(raw),
        folder=folder,
        uid=None,
        uidvalidity=None,
        raw_rfc822=raw,
        content_sha256=hashlib.sha256(raw).hexdigest(),
        received_at=_received_at_from_rfc822(raw),
        source="drop_folder",
        path_hint=str(path.resolve()),
    )


def load_drop_folder_messages(directory: Path) -> list[IngestedMailMessage]:
    return [ingested_from_eml_file(path) for path in list_eml_files(directory)]
