"""Orchestration persistence protocols (FR-016 M2)."""

from __future__ import annotations

from typing import Protocol

from .models import Handoff, OperationalBrief, OrchestrationRun


class OrchestrationRunStore(Protocol):
    def save(self, run: OrchestrationRun) -> OrchestrationRun: ...

    def load(self, orchestration_run_id: str) -> OrchestrationRun: ...

    def exists(self, orchestration_run_id: str) -> bool: ...


class HandoffStore(Protocol):
    def save(self, handoff: Handoff) -> Handoff: ...

    def load(self, handoff_id: str) -> Handoff: ...


class BriefStore(Protocol):
    def save(self, brief: OperationalBrief) -> OperationalBrief: ...

    def load(self, brief_id: str) -> OperationalBrief: ...
