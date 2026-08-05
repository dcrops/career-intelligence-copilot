"""Errors for FR-015 agent contracts and runtime."""

from __future__ import annotations

from typing import Any


class AgentContractError(ValueError):
    """Raised when an agent contract invariant is violated."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class AgentPolicyError(AgentContractError):
    """Raised when ToolPolicy rejects a proposed action."""


class AgentRuntimeError(Exception):
    """Base error for AgentRuntime failures."""


class AgentRunNotFoundError(AgentRuntimeError):
    """Raised when an agent run cannot be loaded."""


class AgentStorageError(AgentRuntimeError):
    """Raised when agent-run persistence fails."""


class AgentProviderError(AgentRuntimeError):
    """Raised when the action proposer provider is unavailable or fails."""


class AdapterExecutionError(AgentRuntimeError):
    """Raised when a thin service adapter fails unexpectedly."""
