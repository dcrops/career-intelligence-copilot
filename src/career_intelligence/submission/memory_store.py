"""In-memory SubmissionAttemptStore for unit tests and ephemeral local runs."""

from __future__ import annotations

from .errors import (
    SubmissionAppendOnlyError,
    SubmissionAttemptNotFoundError,
    SubmissionTransitionError,
)
from .models import TERMINAL_SUBMISSION_STATUSES, SubmissionAttempt
from .transitions import validate_status_transition


class InMemorySubmissionAttemptStore:
    """Process-local dict-backed append-only submission-attempt store."""

    def __init__(self) -> None:
        self._attempts: dict[str, SubmissionAttempt] = {}

    def create(self, attempt: SubmissionAttempt) -> SubmissionAttempt:
        if attempt.attempt_id in self._attempts:
            raise SubmissionAppendOnlyError(
                f"Submission attempt already exists: {attempt.attempt_id}"
            )
        if attempt.status != "ready":
            raise SubmissionAppendOnlyError(
                "New submission attempts must be created with status 'ready'"
            )
        stored = SubmissionAttempt.model_validate(attempt.model_dump(mode="python"))
        self._attempts[stored.attempt_id] = stored
        return stored

    def save(self, attempt: SubmissionAttempt) -> SubmissionAttempt:
        previous = self._require(attempt.attempt_id)
        if previous.status in TERMINAL_SUBMISSION_STATUSES:
            raise SubmissionAppendOnlyError(
                f"Cannot modify terminal submission attempt {attempt.attempt_id} "
                f"(status={previous.status})"
            )
        if attempt.attempt_id != previous.attempt_id:
            raise SubmissionAppendOnlyError("attempt_id cannot change")
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
        stored = SubmissionAttempt.model_validate(attempt.model_dump(mode="python"))
        self._attempts[stored.attempt_id] = stored
        return stored

    def load(self, attempt_id: str) -> SubmissionAttempt:
        return SubmissionAttempt.model_validate(
            self._require(attempt_id).model_dump(mode="python")
        )

    def list(
        self,
        *,
        opportunity_id: str | None = None,
    ) -> list[SubmissionAttempt]:
        items = [
            SubmissionAttempt.model_validate(item.model_dump(mode="python"))
            for item in self._attempts.values()
            if opportunity_id is None or item.opportunity_id == opportunity_id
        ]
        return sorted(items, key=lambda item: item.attempt_id)

    def exists(self, attempt_id: str) -> bool:
        return attempt_id in self._attempts

    def _require(self, attempt_id: str) -> SubmissionAttempt:
        try:
            return self._attempts[attempt_id]
        except KeyError as error:
            raise SubmissionAttemptNotFoundError(
                f"Submission attempt not found: {attempt_id}"
            ) from error
