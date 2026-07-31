"""JSON directory adapter for submission attempts (FR-012 M0).

Package-private persistence. Callers should use the public ``submission`` API.
Append-only identity: no delete; create fails on collision; terminal attempts
cannot be rewritten.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .errors import (
    ErrorDetail,
    SubmissionAppendOnlyError,
    SubmissionAttemptNotFoundError,
    SubmissionStorageError,
    SubmissionTransitionError,
    SubmissionValidationError,
)
from .models import TERMINAL_SUBMISSION_STATUSES, SubmissionAttempt
from .transitions import validate_status_transition


class JsonDirectorySubmissionAttemptStore:
    """Persist one JSON file per attempt under ``root/{attempt_id}.json``."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def create(self, attempt: SubmissionAttempt) -> SubmissionAttempt:
        path = self._path(attempt.attempt_id)
        if path.is_file():
            raise SubmissionAppendOnlyError(
                f"Submission attempt already exists: {attempt.attempt_id}"
            )
        if attempt.status != "ready":
            raise SubmissionAppendOnlyError(
                "New submission attempts must be created with status 'ready'"
            )
        return self._write(attempt)

    def save(self, attempt: SubmissionAttempt) -> SubmissionAttempt:
        previous = self.load(attempt.attempt_id)
        if previous.status in TERMINAL_SUBMISSION_STATUSES:
            raise SubmissionAppendOnlyError(
                f"Cannot modify terminal submission attempt {attempt.attempt_id} "
                f"(status={previous.status})"
            )
        if attempt.created_at != previous.created_at:
            raise SubmissionAppendOnlyError("created_at is immutable")
        if attempt.opportunity_id != previous.opportunity_id:
            raise SubmissionAppendOnlyError("opportunity_id is immutable")
        if attempt.package != previous.package:
            raise SubmissionAppendOnlyError("package ref is immutable")
        if attempt.channel != previous.channel:
            raise SubmissionAppendOnlyError("channel is immutable")
        if attempt.mode != previous.mode:
            raise SubmissionAppendOnlyError("mode is immutable")
        try:
            validate_status_transition(previous.status, attempt.status)
        except SubmissionTransitionError as error:
            raise SubmissionAppendOnlyError(str(error)) from error
        return self._write(attempt)

    def load(self, attempt_id: str) -> SubmissionAttempt:
        path = self._path(attempt_id)
        if not path.is_file():
            raise SubmissionAttemptNotFoundError(
                f"Submission attempt not found: {attempt_id}"
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return SubmissionAttempt.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            if isinstance(error, ValidationError):
                raise SubmissionValidationError(
                    [ErrorDetail.from_pydantic(item) for item in error.errors()]
                ) from error
            raise SubmissionStorageError(
                f"Could not load submission attempt {attempt_id}: {error}"
            ) from error

    def list(
        self,
        *,
        opportunity_id: str | None = None,
    ) -> list[SubmissionAttempt]:
        if not self.root.is_dir():
            return []
        items: list[SubmissionAttempt] = []
        try:
            paths = sorted(self.root.glob("sub_*.json"))
        except OSError as error:
            raise SubmissionStorageError(
                f"Could not list submission attempts: {error}"
            ) from error
        for path in paths:
            attempt = self.load(path.stem)
            if opportunity_id is None or attempt.opportunity_id == opportunity_id:
                items.append(attempt)
        return sorted(items, key=lambda item: item.attempt_id)

    def exists(self, attempt_id: str) -> bool:
        return self._path(attempt_id).is_file()

    def _write(self, attempt: SubmissionAttempt) -> SubmissionAttempt:
        path = self._path(attempt.attempt_id)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            payload = (
                json.dumps(attempt.model_dump(mode="json"), indent=2, ensure_ascii=False)
                + "\n"
            )
            temporary.write_text(payload, encoding="utf-8", newline="\n")
            temporary.replace(path)
        except OSError as error:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
            raise SubmissionStorageError(
                f"Could not write submission attempt {attempt.attempt_id}: {error}"
            ) from error
        return attempt

    def _path(self, attempt_id: str) -> Path:
        return self.root / f"{attempt_id}.json"
