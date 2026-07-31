"""Unit tests for FR-012 M0 append-only submission attempt stores."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from career_intelligence.submission import (
    InMemorySubmissionAttemptStore,
    JsonDirectorySubmissionAttemptStore,
    SubmissionAppendOnlyError,
    SubmissionAttemptNotFoundError,
    apply_status_transition,
)
from tests.unit.submission.helpers import (
    ATTEMPT_A,
    ATTEMPT_B,
    OPP_A,
    OPP_B,
    make_attempt,
    make_evidence,
)

NOW = datetime(2026, 7, 31, 7, 0, 0, tzinfo=UTC)


@pytest.fixture(params=["memory", "json"])
def store(request: pytest.FixtureRequest, tmp_path: Path):
    if request.param == "memory":
        return InMemorySubmissionAttemptStore()
    return JsonDirectorySubmissionAttemptStore(tmp_path / "submission_attempts")


def test_create_load_list_round_trip(store) -> None:
    created = store.create(make_attempt())
    loaded = store.load(ATTEMPT_A)
    assert loaded == created
    assert store.exists(ATTEMPT_A)
    assert [item.attempt_id for item in store.list()] == [ATTEMPT_A]


def test_list_filters_by_opportunity(store) -> None:
    store.create(make_attempt(attempt_id=ATTEMPT_A, opportunity_id=OPP_A))
    store.create(make_attempt(attempt_id=ATTEMPT_B, opportunity_id=OPP_B))
    listed = store.list(opportunity_id=OPP_B)
    assert [item.attempt_id for item in listed] == [ATTEMPT_B]


def test_create_rejects_duplicate_id(store) -> None:
    store.create(make_attempt())
    with pytest.raises(SubmissionAppendOnlyError):
        store.create(make_attempt())


def test_create_requires_ready(store) -> None:
    with pytest.raises(SubmissionAppendOnlyError):
        store.create(make_attempt(status="in_progress", evidence=make_evidence(
            result_code="x",
            message="y",
        )))


def test_save_advances_status(store) -> None:
    store.create(make_attempt())
    advanced = apply_status_transition(
        store.load(ATTEMPT_A),
        "in_progress",
        evidence=make_evidence(result_code="started", message="running"),
        updated_at=NOW,
    )
    saved = store.save(advanced)
    assert saved.status == "in_progress"
    assert store.load(ATTEMPT_A).status == "in_progress"


def test_save_rejects_illegal_transition(store) -> None:
    store.create(make_attempt())
    illegal = make_attempt(
        status="submitted",
        evidence=make_evidence(result_code="ok", message="done"),
        completed_at=NOW,
        updated_at=NOW,
    )
    with pytest.raises(SubmissionAppendOnlyError):
        store.save(illegal)


def test_terminal_attempt_immutable(store) -> None:
    store.create(make_attempt())
    in_progress = apply_status_transition(
        store.load(ATTEMPT_A),
        "in_progress",
        evidence=make_evidence(result_code="started", message="running"),
        updated_at=NOW,
    )
    store.save(in_progress)
    terminal = apply_status_transition(
        store.load(ATTEMPT_A),
        "submitted",
        evidence=make_evidence(result_code="ok", message="done"),
        updated_at=NOW,
    )
    store.save(terminal)
    mutated = make_attempt(
        status="failed",
        evidence=make_evidence(
            result_code="err",
            message="nope",
            failure_reason="should not write",
        ),
        completed_at=NOW,
        updated_at=NOW,
    )
    with pytest.raises(SubmissionAppendOnlyError):
        store.save(mutated)


def test_save_rejects_immutable_field_change(store) -> None:
    store.create(make_attempt())
    advanced = apply_status_transition(
        store.load(ATTEMPT_A),
        "in_progress",
        evidence=make_evidence(result_code="started", message="running"),
        updated_at=NOW,
    )
    changed = advanced.model_copy(update={"channel": "fake"})
    with pytest.raises(SubmissionAppendOnlyError):
        store.save(changed)


def test_load_missing_raises(store) -> None:
    with pytest.raises(SubmissionAttemptNotFoundError):
        store.load(ATTEMPT_A)


def test_json_persists_across_instances(tmp_path: Path) -> None:
    root = tmp_path / "submission_attempts"
    first = JsonDirectorySubmissionAttemptStore(root)
    first.create(make_attempt())
    second = JsonDirectorySubmissionAttemptStore(root)
    loaded = second.load(ATTEMPT_A)
    assert loaded.attempt_id == ATTEMPT_A
    assert loaded.status == "ready"


def test_no_delete_api() -> None:
    assert not hasattr(InMemorySubmissionAttemptStore, "delete")
    assert not hasattr(JsonDirectorySubmissionAttemptStore, "delete")
