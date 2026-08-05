"""Append-friendly TruthReport persistence (FR-014 M3).

Layout:
  ``root/{opportunity_id}/{report_id}.json`` — immutable history copy
  ``root/{opportunity_id}/current_{artefact_kind}.json`` — latest report pointer

Unscoped (no opportunity): ``root/_unscoped/{report_id}.json`` only.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from career_intelligence.truth_validation.errors import (
    ErrorDetail,
    TruthSchemaError,
    TruthValidationError,
)
from career_intelligence.truth_validation.models import ArtefactKind, TruthReport

DEFAULT_TRUTH_REPORTS_ROOT = (
    Path(__file__).resolve().parents[3] / "data" / "truth_reports"
)

_CURRENT_PREFIX = "current_"


class TruthReportNotFoundError(TruthValidationError):
    """Raised when a current or historical truth report is missing."""


class JsonDirectoryTruthReportStore:
    """Persist TruthReports under ``data/truth_reports/``."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else DEFAULT_TRUTH_REPORTS_ROOT

    def save(self, report: TruthReport, *, as_current: bool = True) -> Path:
        """Write historical copy; optionally update the current pointer for the kind."""
        opportunity_id = report.opportunity_id or "_unscoped"
        directory = self.root / opportunity_id
        directory.mkdir(parents=True, exist_ok=True)
        history = directory / f"{report.report_id}.json"
        self._write(history, report)
        if as_current and report.opportunity_id is not None:
            current = directory / f"{_CURRENT_PREFIX}{report.artefact.kind}.json"
            self._write(current, report)
        return history

    def load(self, report_id: str) -> TruthReport:
        """Load a historical report by id."""
        path = self._find(report_id)
        if path is None:
            raise TruthReportNotFoundError(f"Truth report not found: {report_id}")
        return self._read(path)

    def load_path(self, path: Path) -> TruthReport:
        """Load a report from an explicit filesystem path."""
        return self._read(path)

    def load_current(
        self,
        opportunity_id: str,
        artefact_kind: ArtefactKind,
    ) -> TruthReport | None:
        """Return the current report for an artefact, or None if missing."""
        path = self.root / opportunity_id / f"{_CURRENT_PREFIX}{artefact_kind}.json"
        if not path.is_file():
            return None
        return self._read(path)

    def current_path(
        self,
        opportunity_id: str,
        artefact_kind: ArtefactKind,
    ) -> Path:
        return self.root / opportunity_id / f"{_CURRENT_PREFIX}{artefact_kind}.json"

    def _find(self, report_id: str) -> Path | None:
        if not self.root.is_dir():
            return None
        matches = list(self.root.glob(f"*/{report_id}.json"))
        return matches[0] if matches else None

    def _write(self, path: Path, report: TruthReport) -> None:
        path.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _read(self, path: Path) -> TruthReport:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return TruthReport.model_validate(raw)
        except (OSError, ValueError, ValidationError) as error:
            if isinstance(error, ValidationError):
                raise TruthSchemaError(
                    [ErrorDetail.from_pydantic(item) for item in error.errors()]
                ) from error
            raise TruthValidationError(f"Could not load truth report {path}: {error}") from error
