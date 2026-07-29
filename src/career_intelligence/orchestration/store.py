"""Checkpoint persistence boundary for workflow runs (FR-008 M0).

Durable adapters are deferred; callers depend on this protocol only.
"""

from __future__ import annotations

from typing import Protocol

from .models import WorkflowState


class CheckpointStore(Protocol):
    """Replaceable checkpoint store — no filesystem/YAML-specific surface."""

    def save(self, state: WorkflowState) -> WorkflowState:
        """Persist the full workflow state for ``state.run_id`` (upsert)."""

    def load(self, run_id: str) -> WorkflowState:
        """Load one workflow run by id.

        Implementations raise ``WorkflowNotFoundError`` when missing.
        """

    def exists(self, run_id: str) -> bool:
        """Return whether a checkpoint exists for ``run_id``."""

    def delete(self, run_id: str) -> None:
        """Remove a checkpoint if present; no-op when missing is acceptable."""
