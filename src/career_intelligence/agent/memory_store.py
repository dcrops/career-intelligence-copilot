"""In-memory agent-run store for tests."""

from __future__ import annotations

from .errors import AgentRunNotFoundError
from .models import AgentRun


class InMemoryAgentRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, AgentRun] = {}

    def save(self, run: AgentRun) -> AgentRun:
        self._runs[run.agent_run_id] = run
        return run

    def load(self, agent_run_id: str) -> AgentRun:
        try:
            return self._runs[agent_run_id]
        except KeyError as error:
            raise AgentRunNotFoundError(f"Agent run not found: {agent_run_id}") from error

    def exists(self, agent_run_id: str) -> bool:
        return agent_run_id in self._runs

    def list_runs(self) -> list[AgentRun]:
        runs = list(self._runs.values())
        runs.sort(key=lambda r: r.updated_at, reverse=True)
        return runs
