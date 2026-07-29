"""Durable JSON-directory checkpoint store (FR-008 M1).

Private persistence detail behind ``CheckpointStore``. Not Opportunity SoT.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .errors import (
    ErrorDetail,
    WorkflowCheckpointError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from .models import WorkflowState


class JsonDirectoryCheckpointStore:
    """One ``{run_id}.json`` file per workflow run under a root directory."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def path_for(self, run_id: str) -> Path:
        return self._root / f"{run_id}.json"

    def save(self, state: WorkflowState) -> WorkflowState:
        stored = WorkflowState.model_validate(state.model_dump(mode="python"))
        path = self.path_for(stored.run_id)
        temporary = path.with_suffix(".json.tmp")
        try:
            temporary.write_text(
                stored.model_dump_json(indent=2),
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as error:
            raise WorkflowCheckpointError(
                f"Failed to save checkpoint for {stored.run_id}: {error}"
            ) from error
        return stored

    def load(self, run_id: str) -> WorkflowState:
        path = self.path_for(run_id)
        if not path.is_file():
            raise WorkflowNotFoundError(run_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return WorkflowState.model_validate(payload)
        except (OSError, json.JSONDecodeError) as error:
            raise WorkflowCheckpointError(
                f"Failed to load checkpoint for {run_id}: {error}"
            ) from error
        except ValidationError as error:
            raise WorkflowValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

    def exists(self, run_id: str) -> bool:
        return self.path_for(run_id).is_file()

    def delete(self, run_id: str) -> None:
        path = self.path_for(run_id)
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            raise WorkflowCheckpointError(
                f"Failed to delete checkpoint for {run_id}: {error}"
            ) from error
