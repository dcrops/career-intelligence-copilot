"""Errors for FR-016 multi-agent contracts (M1)."""

from __future__ import annotations

from typing import Any


class MultiAgentContractError(ValueError):
    """Raised when an orchestration contract invariant is violated."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class DelegationPolicyError(MultiAgentContractError):
    """Raised when DelegationPolicy rejects a proposed specialist handoff."""


class ObsPolicyError(MultiAgentContractError):
    """Raised when OBS ToolPolicy rejects a proposed action."""


class OrchestrationRuntimeError(Exception):
    """Base error for DOS runtime failures."""


class OrchestrationRunNotFoundError(OrchestrationRuntimeError):
    """Raised when an orchestration run cannot be loaded."""


class OrchestrationStorageError(OrchestrationRuntimeError):
    """Raised when orchestration persistence fails."""


class DomainWorkForbiddenError(OrchestrationRuntimeError):
    """Raised when DOS is asked to perform domain work directly."""
