"""YAML directory adapter for opportunity index + immutable JSON artifacts.

Package-private. Downstream callers must use ``OpportunityService``.
"""

from __future__ import annotations

import json
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis, JobPosting
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.portfolio_matching.models import PortfolioMatch

from .errors import (
    ErrorDetail,
    OpportunityArtifactExistsError,
    OpportunityNotFoundError,
    OpportunityStorageError,
    OpportunityValidationError,
)
from .models import ARTIFACT_FILENAMES, Opportunity

_INDEX_FILENAME = "index.yaml"
_ARTIFACTS_DIRNAME = "artifacts"

_ARTIFACT_KEYS = (
    "posting.json",
    "job_analysis.json",
    "assessment.json",
    "portfolio_match.json",
    "strategy.json",
)


class YamlDirectoryOpportunityStore:
    """Persist opportunities under ``root/index.yaml`` and ``root/artifacts/``."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.index_path = root / _INDEX_FILENAME
        self.artifacts_root = root / _ARTIFACTS_DIRNAME

    def get(self, opportunity_id: str) -> Opportunity:
        opportunities = self._load_index()
        for item in opportunities:
            if item.opportunity_id == opportunity_id:
                return item
        raise OpportunityNotFoundError(f"Opportunity not found: {opportunity_id}")

    def list_opportunities(self) -> list[Opportunity]:
        items = self._load_index()
        # ULID ids are time-sortable; descending = newest first.
        return sorted(items, key=lambda item: item.opportunity_id, reverse=True)

    def create(
        self,
        opportunity: Opportunity,
        *,
        posting: JobPosting,
        job_analysis: JobAnalysis,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        strategy: ApplicationStrategy,
    ) -> Opportunity:
        opportunity_id = opportunity.opportunity_id
        artifact_dir = self.artifacts_root / opportunity_id

        if artifact_dir.exists():
            raise OpportunityArtifactExistsError(
                f"Artifact directory already exists for {opportunity_id}"
            )

        existing = {item.opportunity_id for item in self._load_index()}
        if opportunity_id in existing:
            raise OpportunityStorageError(
                f"Opportunity id already present in index: {opportunity_id}"
            )

        relative_paths = {
            name: f"{_ARTIFACTS_DIRNAME}/{opportunity_id}/{name}" for name in _ARTIFACT_KEYS
        }
        payload = opportunity.model_copy(
            update={"artifact_paths": relative_paths},
            deep=True,
        )

        artifacts: dict[str, BaseModel] = {
            "posting.json": posting,
            "job_analysis.json": job_analysis,
            "assessment.json": assessment,
            "portfolio_match.json": portfolio_match,
            "strategy.json": strategy,
        }

        try:
            artifact_dir.mkdir(parents=True, exist_ok=False)
            for filename, model in artifacts.items():
                self._write_immutable_json(artifact_dir / filename, model)
            self._append_index(payload)
        except Exception:
            if artifact_dir.exists():
                with suppress(OSError):
                    shutil.rmtree(artifact_dir)
            raise

        return payload

    def _write_immutable_json(self, path: Path, model: BaseModel) -> None:
        if path.exists():
            raise OpportunityArtifactExistsError(f"Artifact already exists: {path}")
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            temporary.write_text(
                json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            temporary.replace(path)
        except OSError as error:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
            raise OpportunityStorageError(f"Could not write artifact {path}: {error}") from error

    def _load_index(self) -> list[Opportunity]:
        if not self.index_path.is_file():
            return []
        try:
            with self.index_path.open(encoding="utf-8") as handle:
                raw = yaml.safe_load(handle)
        except yaml.YAMLError as error:
            raise OpportunityStorageError(
                f"Invalid YAML in {self.index_path}: {error}"
            ) from error
        except OSError as error:
            raise OpportunityStorageError(f"Could not read {self.index_path}: {error}") from error

        if raw is None:
            return []
        if not isinstance(raw, dict):
            raise OpportunityStorageError(
                f"Opportunity index at {self.index_path} must be a YAML mapping."
            )
        entries = raw.get("opportunities", [])
        if not isinstance(entries, list):
            raise OpportunityStorageError(
                f"'opportunities' in {self.index_path} must be a list."
            )

        result: list[Opportunity] = []
        for index, item in enumerate(entries):
            if not isinstance(item, dict):
                raise OpportunityStorageError(
                    f"opportunities[{index}] in {self.index_path} must be a mapping."
                )
            try:
                result.append(Opportunity.model_validate(item))
            except ValidationError as error:
                raise OpportunityValidationError(
                    [ErrorDetail.from_pydantic(detail) for detail in error.errors()]
                ) from error
        return result

    def _append_index(self, opportunity: Opportunity) -> None:
        items = self._load_index()
        items.append(opportunity)
        self._write_index(items)

    def _write_index(self, opportunities: list[Opportunity]) -> None:
        serialized: dict[str, Any] = {
            "schema_version": "1",
            "opportunities": [item.model_dump(mode="json") for item in opportunities],
        }
        temporary = self.index_path.with_suffix(self.index_path.suffix + ".tmp")
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                yaml.safe_dump(
                    serialized,
                    handle,
                    sort_keys=False,
                    allow_unicode=True,
                    default_flow_style=False,
                )
            temporary.replace(self.index_path)
        except (OSError, yaml.YAMLError) as error:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
            raise OpportunityStorageError(
                f"Could not write {self.index_path}: {error}"
            ) from error


# Re-export for tests that assert filename constants match models.
assert set(_ARTIFACT_KEYS) == set(ARTIFACT_FILENAMES)
