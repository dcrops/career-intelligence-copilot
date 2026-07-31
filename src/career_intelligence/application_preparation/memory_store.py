"""In-memory PreparationRunStore for unit tests and ephemeral local runs."""

from __future__ import annotations

from .errors import PreparationRunNotFoundError
from .models import PreparationRunState


class InMemoryPreparationRunStore:
    """Process-local dict-backed preparation-run store."""

    def __init__(self) -> None:
        self._runs: dict[str, PreparationRunState] = {}

    def save(self, state: PreparationRunState) -> PreparationRunState:
        stored = PreparationRunState.model_validate(state.model_dump(mode="python"))
        self._runs[stored.run_id] = stored
        return stored

    def load(self, run_id: str) -> PreparationRunState:
        try:
            state = self._runs[run_id]
        except KeyError as error:
            raise PreparationRunNotFoundError(
                f"Preparation run not found: {run_id}"
            ) from error
        return PreparationRunState.model_validate(state.model_dump(mode="python"))

    def exists(self, run_id: str) -> bool:
        return run_id in self._runs
