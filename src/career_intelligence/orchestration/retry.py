"""Bounded retry policy and failure classification for FR-008 M3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .nodes import NodeFailure, NodeOutcome, WorkflowNode
from .types import FailureClassification

FailureKind = Literal["recoverable", "unrecoverable"]

DEFAULT_RETRY_ELIGIBLE_NODES: frozenset[str] = frozenset({"analyse", "assess"})
DEFAULT_MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class RetryPolicy:
    """Deterministic, injectable retry configuration.

    ``max_attempts`` counts total executions of an eligible node (initial +
    retries). Exhaustion occurs when a recoverable failure happens after the
    attempt count reaches ``max_attempts``.

    ``yield_after_retry_schedule`` stops the current invocation after
    checkpointing a scheduled retry (cross-process recovery demos). Same-process
    recovery leaves this false so the runner continues immediately.
    """

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    eligible_node_ids: frozenset[str] = DEFAULT_RETRY_ELIGIBLE_NODES
    delay_ms: int = 0  # metadata only — no scheduler sleeps in the runner
    yield_after_retry_schedule: bool = False

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.delay_ms < 0:
            raise ValueError("delay_ms must be >= 0")
        if not self.eligible_node_ids:
            raise ValueError("eligible_node_ids must not be empty")

    def is_eligible(self, node_id: str) -> bool:
        return node_id in self.eligible_node_ids


@dataclass(frozen=True)
class FailureInjection:
    """Deterministic failure injection for tests and manual validation.

    The node fails ``fail_count`` times, then delegates to the wrapped node.
    Counts are process-local — cross-process demos omit injection on resume.
    """

    node_id: str
    fail_count: int
    kind: FailureKind = "recoverable"

    def __post_init__(self) -> None:
        if self.fail_count < 0:
            raise ValueError("fail_count must be >= 0")
        if not self.node_id.strip():
            raise ValueError("node_id must be non-empty")


def looks_transient(error: BaseException) -> bool:
    """Heuristic markers for provider timeouts / rate limits / connectivity."""
    name = type(error).__name__.lower()
    text = str(error).lower()
    markers = (
        "timeout",
        "rate",
        "temporarily",
        "connection",
        "unavailable",
        "429",
        "503",
        "transient",
    )
    return any(marker in name or marker in text for marker in markers)


def classify_exception(error: BaseException) -> FailureClassification:
    """Unknown exceptions fail closed unless transient markers are present."""
    return "recoverable" if looks_transient(error) else "unrecoverable"


def classification_from_flag(recoverable: bool) -> FailureClassification:
    return "recoverable" if recoverable else "unrecoverable"


def is_recoverable_failure(failure: NodeFailure) -> bool:
    return failure.recoverable is True


class InjectingNode:
    """Wrap a workflow node with bounded deterministic failure injection."""

    def __init__(self, inner: WorkflowNode, injection: FailureInjection) -> None:
        if inner.spec.node_id != injection.node_id:
            raise ValueError(
                f"Injection node_id '{injection.node_id}' does not match "
                f"wrapped node '{inner.spec.node_id}'"
            )
        self._inner = inner
        self._injection = injection
        self._failures_remaining = injection.fail_count

    @property
    def spec(self):
        return self._inner.spec

    @property
    def failures_remaining(self) -> int:
        return self._failures_remaining

    def execute(self, state):
        if self._failures_remaining > 0:
            self._failures_remaining -= 1
            recoverable = self._injection.kind == "recoverable"
            return NodeOutcome(
                failure=NodeFailure(
                    message=(
                        f"Injected {self._injection.kind} failure for "
                        f"'{self._injection.node_id}' "
                        f"({self._injection.fail_count - self._failures_remaining}/"
                        f"{self._injection.fail_count})"
                    ),
                    recoverable=recoverable,
                    detail="FailureInjection",
                )
            )
        return self._inner.execute(state)
