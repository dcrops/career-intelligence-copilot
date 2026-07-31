"""JSON directory adapter for preparation orchestration runs.

Package-private. Downstream callers must use ``ApplicationPreparationOrchestrator``.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .errors import (
    ApplicationPreparationStorageError,
    ApplicationPreparationValidationError,
    ErrorDetail,
    PreparationRunNotFoundError,
)
from .models import PreparationRunState


class JsonDirectoryPreparationRunStore:
    """Persist one JSON file per run under ``root/{run_id}.json``."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, state: PreparationRunState) -> PreparationRunState:
        path = self._path(state.run_id)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            payload = (
                json.dumps(state.model_dump(mode="json"), indent=2, ensure_ascii=False)
                + "\n"
            )
            temporary.write_text(payload, encoding="utf-8", newline="\n")
            temporary.replace(path)
        except OSError as error:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
            raise ApplicationPreparationStorageError(
                f"Could not write preparation run {state.run_id}: {error}"
            ) from error
        return state

    def load(self, run_id: str) -> PreparationRunState:
        path = self._path(run_id)
        if not path.is_file():
            raise PreparationRunNotFoundError(f"Preparation run not found: {run_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return PreparationRunState.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            if isinstance(error, ValidationError):
                raise ApplicationPreparationValidationError(
                    [ErrorDetail.from_pydantic(item) for item in error.errors()]
                ) from error
            raise ApplicationPreparationStorageError(
                f"Could not load preparation run {run_id}: {error}"
            ) from error

    def exists(self, run_id: str) -> bool:
        return self._path(run_id).is_file()

    def _path(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"
