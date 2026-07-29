"""Unit tests for CheckpointStore protocol + in-memory adapter (FR-008 M0)."""

from __future__ import annotations

import pytest

from career_intelligence.orchestration import (
    InMemoryCheckpointStore,
    WorkflowNotFoundError,
    WorkflowState,
)
from tests.unit.orchestration.helpers import make_control, make_state, unique_run_id


def test_save_load_round_trip() -> None:
    store = InMemoryCheckpointStore()
    state = make_state(control=make_control(run_id=unique_run_id(), current_node="strategy"))
    saved = store.save(state)
    loaded = store.load(saved.run_id)
    assert loaded == saved
    assert loaded.control.current_node == "strategy"


def test_exists_and_delete() -> None:
    store = InMemoryCheckpointStore()
    state = make_state(control=make_control(run_id=unique_run_id()))
    assert store.exists(state.run_id) is False
    store.save(state)
    assert store.exists(state.run_id) is True
    store.delete(state.run_id)
    assert store.exists(state.run_id) is False
    store.delete(state.run_id)  # idempotent


def test_load_missing_raises() -> None:
    store = InMemoryCheckpointStore()
    with pytest.raises(WorkflowNotFoundError) as exc_info:
        store.load("wfr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert exc_info.value.run_id.startswith("wfr_")


def test_save_isolates_caller_mutation() -> None:
    store = InMemoryCheckpointStore()
    state = make_state(control=make_control(run_id=unique_run_id(), current_node="analyse"))
    store.save(state)
    # Mutating the original control object must not affect the store.
    state.control.current_node = "tampered"
    loaded = store.load(state.run_id)
    assert loaded.control.current_node == "analyse"


def test_upsert_overwrites() -> None:
    store = InMemoryCheckpointStore()
    run_id = unique_run_id()
    store.save(make_state(control=make_control(run_id=run_id, current_node="analyse")))
    store.save(make_state(control=make_control(run_id=run_id, current_node="assess")))
    loaded = store.load(run_id)
    assert loaded.control.current_node == "assess"


def test_store_satisfies_protocol_surface() -> None:
    store = InMemoryCheckpointStore()
    assert callable(store.save)
    assert callable(store.load)
    assert callable(store.exists)
    assert callable(store.delete)
    sample = make_state(control=make_control(run_id=unique_run_id()))
    assert isinstance(store.save(sample), WorkflowState)
