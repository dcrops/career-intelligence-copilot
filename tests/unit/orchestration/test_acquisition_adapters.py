"""Unit tests for FR-008 acquisition adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.orchestration import (
    AcquisitionError,
    LocalFileAcquisitionAdapter,
    PasteAcquisitionAdapter,
    PasteJobInput,
    coerce_acquisition_adapter,
)
from career_intelligence.job_analysis.fixtures import posting_ai_engineer
from tests.unit.orchestration.m1_helpers import fixture_job_input, offline_runner


def test_paste_adapter_builds_result() -> None:
    adapter = PasteAcquisitionAdapter(
        PasteJobInput(
            raw_text="Senior AI Engineer\nBuild systems.",
            title="Senior AI Engineer",
            company="Example",
            source_url="https://example.com/jobs/1",
        )
    )
    assert adapter.source_kind == "paste"
    result = adapter.acquire()
    assert result.source_kind == "paste"
    assert result.posting.title == "Senior AI Engineer"
    assert result.company == "Example"
    assert any("does not fetch" in w for w in result.warnings)


def test_paste_adapter_empty_fails() -> None:
    with pytest.raises(AcquisitionError, match="non-empty"):
        PasteAcquisitionAdapter(PasteJobInput(raw_text="   ")).acquire()


def test_local_file_adapter(tmp_path: Path) -> None:
    posting = posting_ai_engineer()
    path = tmp_path / "exported_job.txt"
    path.write_text(posting.raw_text, encoding="utf-8")
    adapter = LocalFileAcquisitionAdapter(
        path,
        title="Senior AI Engineer",
        company="Northside Analytics",
        source_url="https://example.com/jobs/ai",
    )
    assert adapter.source_kind == "export"
    result = adapter.acquire()
    assert result.source_kind == "export"
    assert result.source_identifier is not None
    assert path.name in (result.source_identifier or "")
    assert "CIC-FIXTURE" in result.raw_content or "AI" in result.raw_content
    assert result.title == "Senior AI Engineer"
    assert any("local export file" in w for w in result.warnings)
    assert any("does not fetch" in w for w in result.warnings)


def test_local_file_missing(tmp_path: Path) -> None:
    with pytest.raises(AcquisitionError, match="not found"):
        LocalFileAcquisitionAdapter(tmp_path / "missing.txt").acquire()


def test_local_file_empty(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("  \n  ", encoding="utf-8")
    with pytest.raises(AcquisitionError, match="empty"):
        LocalFileAcquisitionAdapter(path).acquire()


def test_coerce_paste_input() -> None:
    job = fixture_job_input()
    adapter = coerce_acquisition_adapter(job)
    assert adapter.source_kind == "paste"
    assert isinstance(adapter, PasteAcquisitionAdapter)


def test_workflow_identical_node_order_for_file_and_paste(tmp_path: Path) -> None:
    posting = posting_ai_engineer()
    path = tmp_path / "job.txt"
    path.write_text(posting.raw_text, encoding="utf-8")

    paste_state = offline_runner(opportunities_dir=tmp_path / "opps_p").start(
        fixture_job_input()
    )
    file_state = offline_runner(opportunities_dir=tmp_path / "opps_f").start(
        LocalFileAcquisitionAdapter(path)
    )

    paste_nodes = [n.node_id for n in paste_state.execution.completed_nodes]
    file_nodes = [n.node_id for n in file_state.execution.completed_nodes]
    assert paste_nodes == file_nodes
    assert paste_state.status == file_state.status == "awaiting_owner"
    assert paste_state.acquisition is not None
    assert file_state.acquisition is not None
    assert paste_state.acquisition.source_kind == "paste"
    assert file_state.acquisition.source_kind == "export"
    assert paste_state.artefacts.strategy is not None
    assert file_state.artefacts.strategy is not None
