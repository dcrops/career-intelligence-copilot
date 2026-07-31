"""Deterministic fake submission adapter (FR-012 M1).

No network. Outcomes are fixture-driven for orchestrator tests.
"""

from __future__ import annotations

from .adapters import (
    AdapterOutcomeStatus,
    SubmissionAdapterRequest,
    SubmissionAdapterResult,
)
from .models import SubmissionChannel, SubmissionMode


class FakeSubmissionAdapter:
    """Configurable offline adapter for automated testing."""

    def __init__(
        self,
        *,
        outcome: AdapterOutcomeStatus = "submitted",
        result_code: str | None = None,
        message: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        self._outcome = outcome
        self._result_code = result_code
        self._message = message
        self._failure_reason = failure_reason
        self.call_count = 0
        self.last_request: SubmissionAdapterRequest | None = None

    @property
    def channel(self) -> SubmissionChannel:
        return "fake"

    @property
    def mode(self) -> SubmissionMode:
        return "adapter_action"

    @property
    def requires_destination(self) -> bool:
        return True

    def set_outcome(
        self,
        outcome: AdapterOutcomeStatus,
        *,
        result_code: str | None = None,
        message: str | None = None,
        failure_reason: str | None = None,
    ) -> None:
        """Reconfigure the next ``execute`` result (tests / manual harness)."""
        self._outcome = outcome
        self._result_code = result_code
        self._message = message
        self._failure_reason = failure_reason

    def execute(self, request: SubmissionAdapterRequest) -> SubmissionAdapterResult:
        self.call_count += 1
        self.last_request = request
        code = self._result_code or f"fake_{self._outcome}"
        message = self._message or f"Fake adapter returned {self._outcome}"
        failure_reason = self._failure_reason
        if self._outcome in ("failed", "outcome_unknown") and failure_reason is None:
            failure_reason = f"fake_{self._outcome}_reason"
        return SubmissionAdapterResult(
            status=self._outcome,
            result_code=code,
            message=message,
            failure_reason=failure_reason,
        )
