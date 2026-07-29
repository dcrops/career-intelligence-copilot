"""Unit tests for JsonDirectoryCheckpointStore (FR-008 M1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.orchestration import (
    JsonDirectoryCheckpointStore,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from tests.unit.orchestration.helpers import make_control, make_state, unique_run_id


def test_json_store_round_trip(tmp_path: Path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    state = make_state(control=make_control(run_id=unique_run_id(), current_node="strategy"))
    store.save(state)
    loaded = store.load(state.run_id)
    assert loaded == state
    assert store.path_for(state.run_id).is_file()


def test_json_store_process_reload(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    run_id = unique_run_id()
    JsonDirectoryCheckpointStore(root).save(
        make_state(control=make_control(run_id=run_id, current_node="owner_review"))
    )
    # New store instance simulates a new process.
    loaded = JsonDirectoryCheckpointStore(root).load(run_id)
    assert loaded.control.current_node == "owner_review"


def test_json_store_corrupt_file_fails_closed(tmp_path: Path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    run_id = unique_run_id()
    path = store.path_for(run_id)
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(Exception):
        store.load(run_id)


def test_json_store_missing(tmp_path: Path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    with pytest.raises(WorkflowNotFoundError):
        store.load(unique_run_id())
