"""Agent-run store protocol (FR-015 M2)."""

from __future__ import annotations

from typing import Protocol

from .models import AgentRun


class AgentRunStore(Protocol):
    def save(self, run: AgentRun) -> AgentRun: ...

    def load(self, agent_run_id: str) -> AgentRun: ...

    def exists(self, agent_run_id: str) -> bool: ...
