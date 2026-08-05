"""Helpers for FR-013 M2 PipelineTrackingService tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.opportunities import Opportunity, OpportunityService
from career_intelligence.opportunities.store import OpportunityStore
from career_intelligence.pipeline import (
    InMemoryPipelineEventStore,
    PipelineTrackingService,
)
from tests.unit.opportunities.helpers import create_opportunity


class CountingFailStore:
    """Wraps an OpportunityStore and fails on the Nth ``save`` call."""

    def __init__(self, inner: OpportunityStore, *, fail_on_save: int = 1) -> None:
        self._inner = inner
        self._fail_on_save = fail_on_save
        self._saves = 0

    def get(self, opportunity_id: str) -> Opportunity:
        return self._inner.get(opportunity_id)

    def list_opportunities(self) -> list[Opportunity]:
        return self._inner.list_opportunities()

    def save(self, opportunity: Opportunity) -> Opportunity:
        self._saves += 1
        if self._saves == self._fail_on_save:
            from career_intelligence.opportunities import OpportunityStorageError

            raise OpportunityStorageError("injected opportunity save failure")
        return self._inner.save(opportunity)

    def __getattr__(self, name: str):
        return getattr(self._inner, name)


def tracking_workspace(tmp_path: Path):
    """Create OpportunityService + PipelineTrackingService in tmp_path."""
    opportunities, opportunity, _ = create_opportunity(tmp_path / "opportunities")
    events = InMemoryPipelineEventStore()
    tracking = PipelineTrackingService(opportunities=opportunities, events=events)
    return tracking, opportunities, opportunity, events


def tracking_with_flaky_save(tmp_path: Path, *, fail_on_save: int = 1):
    opportunities, opportunity, _ = create_opportunity(tmp_path / "opportunities")
    # Rebuild service over wrapped store (same YAML files).
    flaky = CountingFailStore(opportunities._store, fail_on_save=fail_on_save)  # noqa: SLF001
    wrapped = OpportunityService(store=flaky)
    events = InMemoryPipelineEventStore()
    tracking = PipelineTrackingService(opportunities=wrapped, events=events)
    return tracking, wrapped, opportunity, events, flaky
