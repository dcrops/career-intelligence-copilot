"""Stable public errors for workflow orchestration (FR-008 M0)."""

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


class WorkflowError(Exception):
    """Base error for the public orchestration API."""


class WorkflowValidationError(WorkflowError):
    """Raised when workflow state or contracts fail schema/invariant checks."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__("Workflow validation failed")


class WorkflowAwaitingOwnerError(WorkflowError):
    """Raised when a run is paused for mandatory owner approval."""

    def __init__(self, run_id: str, message: str = "Workflow is awaiting owner approval") -> None:
        self.run_id = run_id
        super().__init__(message)


class WorkflowCheckpointError(WorkflowError):
    """Raised when checkpoint persistence or load fails."""


class WorkflowNotFoundError(WorkflowCheckpointError):
    """Raised when a workflow run id is not in the checkpoint store."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Workflow run not found: {run_id}")


class WorkflowResumeError(WorkflowError):
    """Raised when resume is refused (wrong status, missing approval, stale state)."""


class WorkflowNodeError(WorkflowError):
    """Raised by a node to report an explicit execution failure (M1+)."""

    def __init__(
        self,
        message: str,
        *,
        node_id: str | None = None,
        recoverable: bool = False,
    ) -> None:
        self.node_id = node_id
        self.recoverable = recoverable
        super().__init__(message)
