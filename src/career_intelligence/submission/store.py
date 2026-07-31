"""Persistence boundary for submission attempts (FR-012 M0).

Append-only identity: attempts are never deleted. New attempts are created once;
in-flight status advances replace the current snapshot only after transition
validation. Terminal attempts are immutable.
"""

from __future__ import annotations

from typing import Protocol

from .models import SubmissionAttempt


class SubmissionAttemptStore(Protocol):
    """Replaceable store — audit only; not Opportunity SoT."""

    def create(self, attempt: SubmissionAttempt) -> SubmissionAttempt:
        """Persist a new attempt. Fails if ``attempt_id`` already exists."""

    def save(self, attempt: SubmissionAttempt) -> SubmissionAttempt:
        """Replace an existing attempt after a validated status transition."""

    def load(self, attempt_id: str) -> SubmissionAttempt:
        """Load a submission attempt by id."""

    def list(
        self,
        *,
        opportunity_id: str | None = None,
    ) -> list[SubmissionAttempt]:
        """List attempts, optionally filtered by opportunity, sorted by id."""

    def exists(self, attempt_id: str) -> bool:
        """Return whether an attempt is present."""
