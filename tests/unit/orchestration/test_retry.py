"""Unit tests for FR-008 M3 failure classification and retry policy."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.orchestration import (
    FailureInjection,
    RetryPolicy,
    RetryState,
    classify_exception,
    classification_from_flag,
    looks_transient,
)


def test_looks_transient_markers() -> None:
    assert looks_transient(TimeoutError("provider timeout"))
    assert looks_transient(RuntimeError("rate limit 429"))
    assert looks_transient(ConnectionError("connection reset"))
    assert not looks_transient(ValueError("schema invalid"))
    assert not looks_transient(RuntimeError("unexpected boom"))


def test_classify_exception_unknown_fail_closed() -> None:
    assert classify_exception(RuntimeError("mystery")) == "unrecoverable"
    assert classify_exception(TimeoutError("timed out")) == "recoverable"


def test_classification_from_flag() -> None:
    assert classification_from_flag(True) == "recoverable"
    assert classification_from_flag(False) == "unrecoverable"


def test_retry_policy_validation() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="eligible_node_ids"):
        RetryPolicy(eligible_node_ids=frozenset())
    policy = RetryPolicy(max_attempts=3, eligible_node_ids=frozenset({"analyse"}))
    assert policy.is_eligible("analyse")
    assert not policy.is_eligible("validate_normalise")
    assert not policy.is_eligible("owner_review")


def test_failure_injection_validation() -> None:
    with pytest.raises(ValueError, match="fail_count"):
        FailureInjection(node_id="analyse", fail_count=-1)


def test_retry_state_invariants() -> None:
    active = RetryState(
        node_id="analyse",
        attempts_used=1,
        max_attempts=3,
        last_classification="recoverable",
        last_message="timeout",
    )
    assert active.next_action == "retry_node"
    assert not active.exhausted

    exhausted = RetryState(
        node_id="analyse",
        attempts_used=3,
        max_attempts=3,
        last_classification="recoverable",
        last_message="timeout",
        exhausted=True,
        next_action="fail_closed",
    )
    assert exhausted.exhausted

    with pytest.raises(ValidationError):
        RetryState(
            node_id="analyse",
            attempts_used=4,
            max_attempts=3,
            last_classification="recoverable",
            last_message="timeout",
        )

    with pytest.raises(ValidationError):
        RetryState(
            node_id="analyse",
            attempts_used=1,
            max_attempts=3,
            last_classification="recoverable",
            last_message="timeout",
            exhausted=True,
            next_action="retry_node",
        )
