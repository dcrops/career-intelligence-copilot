"""In-memory stores for FR-016 orchestration (tests / offline corpus)."""

from __future__ import annotations

from .errors import OrchestrationRunNotFoundError, OrchestrationStorageError
from .models import Handoff, OperationalBrief, OrchestrationRun


class InMemoryOrchestrationStore:
    """Combined in-memory store for runs, handoffs, and briefs."""

    def __init__(self) -> None:
        self._runs: dict[str, OrchestrationRun] = {}
        self._handoffs: dict[str, Handoff] = {}
        self._briefs: dict[str, OperationalBrief] = {}

    def save(self, run: OrchestrationRun) -> OrchestrationRun:
        self._runs[run.orchestration_run_id] = run
        return run

    def load(self, orchestration_run_id: str) -> OrchestrationRun:
        if orchestration_run_id not in self._runs:
            raise OrchestrationRunNotFoundError(
                f"Orchestration run not found: {orchestration_run_id}"
            )
        return self._runs[orchestration_run_id]

    def exists(self, orchestration_run_id: str) -> bool:
        return orchestration_run_id in self._runs

    def save_handoff(self, handoff: Handoff) -> Handoff:
        self._handoffs[handoff.handoff_id] = handoff
        return handoff

    def load_handoff(self, handoff_id: str) -> Handoff:
        if handoff_id not in self._handoffs:
            raise OrchestrationStorageError(f"Handoff not found: {handoff_id}")
        return self._handoffs[handoff_id]

    def save_brief(self, brief: OperationalBrief) -> OperationalBrief:
        self._briefs[brief.brief_id] = brief
        return brief

    def load_brief(self, brief_id: str) -> OperationalBrief:
        if brief_id not in self._briefs:
            raise OrchestrationStorageError(f"Brief not found: {brief_id}")
        return self._briefs[brief_id]

    def list_runs(self) -> list[OrchestrationRun]:
        return sorted(
            self._runs.values(),
            key=lambda r: r.updated_at,
            reverse=True,
        )
