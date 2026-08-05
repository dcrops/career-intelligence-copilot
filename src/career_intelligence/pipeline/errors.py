"""Stable public errors for pipeline tracking contracts (FR-013 M1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorDetail:
    loc: tuple[str | int, ...]
    msg: str
    type: str

    @classmethod
    def from_pydantic(cls, error: dict[str, Any]) -> ErrorDetail:
        return cls(
            loc=tuple(error.get("loc", ())),
            msg=str(error.get("msg", "Invalid value")),
            type=str(error.get("type", "value_error")),
        )


class PipelineError(Exception):
    """Base error for the public pipeline API."""


class PipelineEventNotFoundError(PipelineError):
    """Raised when a pipeline event id is not in the store."""


class PipelineValidationError(PipelineError):
    """Raised when pipeline data does not satisfy the domain schema."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Pipeline validation failed")


class PipelineStorageError(PipelineError):
    """Raised when pipeline-event persistence fails."""


class PipelineTransitionError(PipelineError):
    """Raised when a pipeline status change is illegal."""


class PipelineAppendOnlyError(PipelineError):
    """Raised when a write would violate append-only event identity."""


class PipelineConsistencyError(PipelineError):
    """Raised when event payload disagrees with Opportunity current state."""


class PipelinePartialWriteError(PipelineError):
    """Raised when the event was appended but Opportunity projection failed.

    The event id is durable. Retry ``apply_event`` with the same event id, or call
    ``reconcile``, to finish projecting onto Opportunity (ADR-005 / FR-013 M2).
    """

    def __init__(
        self,
        message: str,
        *,
        event_id: str,
        opportunity_id: str,
        phase: str = "opportunity",
    ) -> None:
        self.event_id = event_id
        self.opportunity_id = opportunity_id
        self.phase = phase
        super().__init__(message)


class PipelineDivergenceError(PipelineError):
    """Raised when stored Opportunity lifecycle disagrees with event history."""

    def __init__(self, message: str, *, report: object) -> None:
        self.report = report
        super().__init__(message)
