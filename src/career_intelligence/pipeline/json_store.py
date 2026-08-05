"""JSON directory adapter for pipeline events (FR-013 M1).

Layout: ``root/{opportunity_id}/{event_id}.json``.
Append-only: no update, no delete. Contract validated on append.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .errors import (
    ErrorDetail,
    PipelineAppendOnlyError,
    PipelineEventNotFoundError,
    PipelineStorageError,
    PipelineValidationError,
)
from .models import PipelineEvent
from .transitions import validate_event_contract


class JsonDirectoryPipelineEventStore:
    """Persist one JSON file per event under ``root/{opportunity_id}/``."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def append(self, event: PipelineEvent) -> PipelineEvent:
        validate_event_contract(event)
        path = self._path(event.opportunity_id, event.event_id)
        if path.is_file():
            raise PipelineAppendOnlyError(
                f"Pipeline event already exists: {event.event_id}"
            )
        return self._write(event)

    def load(self, event_id: str) -> PipelineEvent:
        path = self._find(event_id)
        if path is None:
            raise PipelineEventNotFoundError(
                f"Pipeline event not found: {event_id}"
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return PipelineEvent.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            if isinstance(error, ValidationError):
                raise PipelineValidationError(
                    [ErrorDetail.from_pydantic(item) for item in error.errors()]
                ) from error
            raise PipelineStorageError(
                f"Could not load pipeline event {event_id}: {error}"
            ) from error

    def list(
        self,
        *,
        opportunity_id: str | None = None,
    ) -> list[PipelineEvent]:
        if not self.root.is_dir():
            return []
        items: list[PipelineEvent] = []
        try:
            if opportunity_id is not None:
                directory = self.root / opportunity_id
                paths = (
                    sorted(directory.glob("ple_*.json"))
                    if directory.is_dir()
                    else []
                )
            else:
                paths = sorted(self.root.glob("opp_*/ple_*.json"))
        except OSError as error:
            raise PipelineStorageError(
                f"Could not list pipeline events: {error}"
            ) from error
        for path in paths:
            items.append(self.load(path.stem))
        return sorted(items, key=lambda item: (item.occurred_at, item.event_id))

    def exists(self, event_id: str) -> bool:
        return self._find(event_id) is not None

    def _write(self, event: PipelineEvent) -> PipelineEvent:
        path = self._path(event.opportunity_id, event.event_id)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = (
                json.dumps(event.model_dump(mode="json"), indent=2, ensure_ascii=False)
                + "\n"
            )
            temporary.write_text(payload, encoding="utf-8", newline="\n")
            temporary.replace(path)
        except OSError as error:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
            raise PipelineStorageError(
                f"Could not write pipeline event {event.event_id}: {error}"
            ) from error
        return event

    def _path(self, opportunity_id: str, event_id: str) -> Path:
        return self.root / opportunity_id / f"{event_id}.json"

    def _find(self, event_id: str) -> Path | None:
        if not self.root.is_dir():
            return None
        matches = list(self.root.glob(f"opp_*/{event_id}.json"))
        if not matches:
            return None
        if len(matches) > 1:
            raise PipelineStorageError(
                f"Duplicate pipeline event paths for {event_id}"
            )
        return matches[0]
