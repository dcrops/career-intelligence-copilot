"""Unit tests for YamlDirectoryOpportunityStore (M1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from career_intelligence.opportunities import (
    ARTIFACT_FILENAMES,
    OpportunityArtifactExistsError,
    OpportunityNotFoundError,
    OpportunityService,
)
from career_intelligence.opportunities.yaml_store import YamlDirectoryOpportunityStore

from .helpers import create_opportunity, trusted_pipeline


def test_empty_store_lists_nothing(tmp_path: Path) -> None:
    store = YamlDirectoryOpportunityStore(tmp_path)
    assert store.list_opportunities() == []
    with pytest.raises(OpportunityNotFoundError):
        store.get("opp_01ARZ3NDEKTSV4RRFFQ69G5FAV")


def test_save_load_list_round_trip(tmp_path: Path) -> None:
    service, opportunity, _ = create_opportunity(tmp_path)
    loaded = service.get(opportunity.opportunity_id)
    assert loaded.opportunity_id == opportunity.opportunity_id
    assert loaded.status == "assessed"
    listed = service.list_opportunities()
    assert len(listed) == 1
    assert listed[0].opportunity_id == opportunity.opportunity_id


def test_directory_and_index_creation(tmp_path: Path) -> None:
    create_opportunity(tmp_path)
    assert (tmp_path / "index.yaml").is_file()
    raw = yaml.safe_load((tmp_path / "index.yaml").read_text(encoding="utf-8"))
    assert raw["schema_version"] == "1"
    assert len(raw["opportunities"]) == 1
    # Index must not embed full strategy graph.
    assert "reasons" not in raw["opportunities"][0]
    assert "strategy_summary" in raw["opportunities"][0]


def test_five_immutable_artifacts_written(tmp_path: Path) -> None:
    _, opportunity, artifacts = create_opportunity(tmp_path)
    posting, analysis, assessment, match, strategy = artifacts
    artifact_dir = tmp_path / "artifacts" / opportunity.opportunity_id
    for name in ARTIFACT_FILENAMES:
        path = artifact_dir / name
        assert path.is_file()
        assert opportunity.artifact_paths[name] == (
            f"artifacts/{opportunity.opportunity_id}/{name}"
        )

    assert json.loads((artifact_dir / "posting.json").read_text(encoding="utf-8"))[
        "title"
    ] == posting.title
    assert json.loads((artifact_dir / "job_analysis.json").read_text(encoding="utf-8"))[
        "posting"
    ]["title"] == analysis.posting.title
    assert json.loads((artifact_dir / "assessment.json").read_text(encoding="utf-8"))[
        "technical_fit"
    ]["judgment"] == assessment.technical_fit.judgment
    assert json.loads((artifact_dir / "portfolio_match.json").read_text(encoding="utf-8"))[
        "summary"
    ] == match.summary
    assert json.loads((artifact_dir / "strategy.json").read_text(encoding="utf-8"))[
        "pursuit_posture"
    ] == strategy.pursuit_posture


def test_immutable_artifact_protection(tmp_path: Path) -> None:
    service, opportunity, pipeline = create_opportunity(tmp_path)
    posting, analysis, assessment, match, strategy = pipeline
    store = YamlDirectoryOpportunityStore(tmp_path)
    with pytest.raises(OpportunityArtifactExistsError):
        store.create(
            opportunity,
            posting=posting,
            job_analysis=analysis,
            assessment=assessment,
            portfolio_match=match,
            strategy=strategy,
        )


def test_artifact_failure_does_not_leave_index_entry(tmp_path: Path, monkeypatch) -> None:
    posting, analysis, assessment, match, strategy = trusted_pipeline()
    store = YamlDirectoryOpportunityStore(tmp_path)
    service = OpportunityService(store=store)

    original = store._write_immutable_json

    def fail_on_strategy(path: Path, model) -> None:
        if path.name == "strategy.json":
            raise OSError("disk full")
        return original(path, model)

    monkeypatch.setattr(store, "_write_immutable_json", fail_on_strategy)

    with pytest.raises(OSError, match="disk full"):
        service.create_from_strategy(
            posting=posting,
            job_analysis=analysis,
            assessment=assessment,
            portfolio_match=match,
            strategy=strategy,
        )

    assert not (tmp_path / "index.yaml").exists()
    assert list((tmp_path / "artifacts").glob("opp_*")) == [] or not (
        tmp_path / "artifacts"
    ).exists()
