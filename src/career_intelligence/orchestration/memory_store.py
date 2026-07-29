"""In-memory CheckpointStore for unit tests and ephemeral local runs.

Not a durable production adapter — use ``JsonDirectoryCheckpointStore`` for
process-level resume under ``data/workflow_runs/``.
"""

from __future__ import annotations

from .errors import WorkflowNotFoundError
from .models import WorkflowState


class InMemoryCheckpointStore:
    """Process-local dict-backed checkpoint store."""

    def __init__(self) -> None:
        self._runs: dict[str, WorkflowState] = {}

    def save(self, state: WorkflowState) -> WorkflowState:
        # Store a validated copy so callers cannot mutate the store by reference.
        stored = WorkflowState.model_validate(state.model_dump(mode="python"))
        self._runs[stored.run_id] = stored
        return stored

    def load(self, run_id: str) -> WorkflowState:
        try:
            state = self._runs[run_id]
        except KeyError as error:
            raise WorkflowNotFoundError(run_id) from error
        return WorkflowState.model_validate(state.model_dump(mode="python"))

    def exists(self, run_id: str) -> bool:
        return run_id in self._runs

    def delete(self, run_id: str) -> None:
        self._runs.pop(run_id, None)
