"""In-memory PipelineEventStore for unit tests and ephemeral local runs."""

from __future__ import annotations

from .errors import PipelineAppendOnlyError, PipelineEventNotFoundError
from .models import PipelineEvent
from .transitions import validate_event_contract


class InMemoryPipelineEventStore:
    """Append-only in-memory event store."""

    def __init__(self) -> None:
        self._events: dict[str, PipelineEvent] = {}

    def append(self, event: PipelineEvent) -> PipelineEvent:
        validate_event_contract(event)
        if event.event_id in self._events:
            raise PipelineAppendOnlyError(
                f"Pipeline event already exists: {event.event_id}"
            )
        stored = PipelineEvent.model_validate(event.model_dump(mode="python"))
        self._events[event.event_id] = stored
        return stored

    def load(self, event_id: str) -> PipelineEvent:
        return PipelineEvent.model_validate(
            self._require(event_id).model_dump(mode="python")
        )

    def list(
        self,
        *,
        opportunity_id: str | None = None,
    ) -> list[PipelineEvent]:
        items = [
            PipelineEvent.model_validate(item.model_dump(mode="python"))
            for item in self._events.values()
            if opportunity_id is None or item.opportunity_id == opportunity_id
        ]
        return sorted(items, key=lambda item: (item.occurred_at, item.event_id))

    def exists(self, event_id: str) -> bool:
        return event_id in self._events

    def _require(self, event_id: str) -> PipelineEvent:
        try:
            return self._events[event_id]
        except KeyError as error:
            raise PipelineEventNotFoundError(
                f"Pipeline event not found: {event_id}"
            ) from error
