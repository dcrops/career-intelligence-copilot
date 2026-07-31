"""Persistence boundary for preparation orchestration runs (FR-011)."""

from __future__ import annotations

from typing import Protocol

from .models import PreparationRunState


class PreparationRunStore(Protocol):
    """Replaceable store — recovery/audit only; not Opportunity SoT."""

    def save(self, state: PreparationRunState) -> PreparationRunState:
        """Persist the current run state (replace by run_id)."""

    def load(self, run_id: str) -> PreparationRunState:
        """Load a preparation run by id."""

    def exists(self, run_id: str) -> bool:
        """Return whether a run is present."""
