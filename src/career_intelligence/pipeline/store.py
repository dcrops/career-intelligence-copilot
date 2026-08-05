"""Persistence boundary for pipeline events (FR-013 M1).

Append-only identity: events are never updated or deleted. Opportunity status
writes are out of scope for this store (ADR-005 / M2 service).
"""

from __future__ import annotations

from typing import Protocol

from .models import PipelineEvent


class PipelineEventStore(Protocol):
    """Replaceable store — audit only; not Opportunity SoT."""

    def append(self, event: PipelineEvent) -> PipelineEvent:
        """Persist a new event after contract validation. Fails on id collision."""

    def load(self, event_id: str) -> PipelineEvent:
        """Load a pipeline event by id."""

    def list(
        self,
        *,
        opportunity_id: str | None = None,
    ) -> list[PipelineEvent]:
        """List events, optionally filtered by opportunity.

        Order: ``occurred_at`` ascending, then ``event_id`` ascending.
        """

    def exists(self, event_id: str) -> bool:
        """Return whether an event is present."""
