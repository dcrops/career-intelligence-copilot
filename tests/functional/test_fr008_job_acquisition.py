"""Functional acceptance: FR-008 acquisition provenance (paste + local export)."""

from __future__ import annotations

from career_intelligence.job_analysis.fixtures import posting_ai_engineer
from career_intelligence.orchestration import (
    LocalFileAcquisitionAdapter,
    completed_spike_nodes,
)
from tests.unit.orchestration.m1_helpers import fixture_job_input, offline_runner


def test_paste_acquisition_preserves_provenance_separate_from_analysis(tmp_path) -> None:
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    state = runner.start(
        fixture_job_input(
            title="Senior AI Engineer",
            company="Northside Analytics",
            source_url="https://www.seek.com.au/job/12345",
        )
    )

    assert state.status == "awaiting_owner"
    assert state.acquisition is not None
    assert state.acquisition.source_kind == "paste"
    assert state.acquisition.raw_content
    assert state.acquisition.normalised_content is not None
    assert state.acquisition.title == "Senior AI Engineer"
    assert state.acquisition.company == "Northside Analytics"
    assert str(state.acquisition.source_url).startswith("https://")
    assert any("does not fetch" in w for w in state.acquisition.warnings)

    assert state.artefacts.posting is not None
    assert state.artefacts.job_analysis is not None
    # Acquisition envelope remains the provenance source of truth for source_kind.
    assert state.acquisition.source_kind == "paste"
    assert state.artefacts.job_analysis.posting.raw_text


def test_local_file_acquisition_preserves_export_provenance(tmp_path) -> None:
    path = tmp_path / "exported_role.txt"
    path.write_text(posting_ai_engineer().raw_text, encoding="utf-8")
    runner = offline_runner(opportunities_dir=tmp_path / "opps")
    state = runner.start(
        LocalFileAcquisitionAdapter(
            path,
            title="Senior AI Engineer",
            company="Northside Analytics",
            source_url="https://example.com/jobs/exported",
        )
    )

    assert state.status == "awaiting_owner"
    assert state.acquisition is not None
    assert state.acquisition.source_kind == "export"
    assert state.acquisition.source_identifier is not None
    assert "exported_role.txt" in state.acquisition.source_identifier
    assert state.acquisition.title == "Senior AI Engineer"
    assert state.acquisition.company == "Northside Analytics"
    assert any("local export file" in w for w in state.acquisition.warnings)
    assert state.artefacts.job_analysis is not None
    assert state.artefacts.strategy is not None
    assert completed_spike_nodes(state) == [
        "acquire",
        "validate_normalise",
        "analyse",
        "assess",
        "match",
        "strategy",
        "persist",
        "owner_review",
    ]


def test_node_order_is_deterministic(tmp_path) -> None:
    state = offline_runner(opportunities_dir=tmp_path / "opps").start(fixture_job_input())
    assert completed_spike_nodes(state) == [
        "acquire",
        "validate_normalise",
        "analyse",
        "assess",
        "match",
        "strategy",
        "persist",
        "owner_review",
    ]
