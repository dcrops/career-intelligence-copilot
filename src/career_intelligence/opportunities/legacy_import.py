"""One-time legacy application_tracker.csv import (M3 migration utility)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from .identity import new_opportunity_id
from .models import (
    LegacyImportProvenance,
    Opportunity,
    OpportunityIdentity,
    OutcomeKind,
    OutcomeRecord,
    OwnerDecisionKind,
    OwnerDecisionRecord,
    PipelineStatus,
    SourceKind,
)

# Exact headers from applications/application_tracker.csv (markdown-table style).
LEGACY_HEADERS: tuple[str, ...] = (
    "Date Applied",
    "Company",
    "Role",
    "Location",
    "Employment Type",
    "Salary",
    "Source",
    "Recruiter / Hiring Manager",
    "CV Version",
    "Cover Letter",
    "Portfolio Used",
    "Status",
    "Follow-up Date",
    "Outcome",
    "Notes",
)

RowResultKind = Literal["imported", "skipped_duplicate", "rejected", "would_import"]


@dataclass(frozen=True)
class LegacyStatusMapping:
    decision: OwnerDecisionKind
    status: PipelineStatus
    outcome: OutcomeKind | None = None


# Explicit mappings only — unknown Status values are rejected (no silent guessing).
LEGACY_STATUS_MAP: dict[str, LegacyStatusMapping] = {
    "applied": LegacyStatusMapping("apply", "submitted", "pending"),
    "interview": LegacyStatusMapping("apply", "interviewing", "pending"),
    "interviewing": LegacyStatusMapping("apply", "interviewing", "pending"),
    "offer": LegacyStatusMapping("apply", "offer", "offer"),
    "accepted": LegacyStatusMapping("apply", "accepted", "accepted"),
    "rejected": LegacyStatusMapping("apply", "rejected", "rejected"),
    "withdrawn": LegacyStatusMapping("apply", "withdrawn", "withdrawn"),
    "deferred": LegacyStatusMapping("defer", "deferred", None),
    "skip": LegacyStatusMapping("skip", "assessed", None),
}

LEGACY_OUTCOME_MAP: dict[str, OutcomeKind] = {
    "pending": "pending",
    "offer": "offer",
    "accepted": "accepted",
    "rejected": "rejected",
    "withdrawn": "withdrawn",
    "unknown": "unknown",
}


@dataclass
class LegacyRowResult:
    row_number: int
    result: RowResultKind
    reason: str
    opportunity_id: str | None = None
    company: str | None = None
    role: str | None = None
    import_fingerprint: str | None = None


@dataclass
class LegacyImportReport:
    source_file: str
    started_at: datetime
    completed_at: datetime
    dry_run: bool
    rows_read: int
    rows_imported: int
    rows_skipped: int
    rows_failed: int
    row_results: list[LegacyRowResult] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "started_at": self.started_at.isoformat().replace("+00:00", "Z"),
            "completed_at": self.completed_at.isoformat().replace("+00:00", "Z"),
            "dry_run": self.dry_run,
            "rows_read": self.rows_read,
            "rows_imported": self.rows_imported,
            "rows_skipped": self.rows_skipped,
            "rows_failed": self.rows_failed,
            "row_results": [
                {
                    "row_number": item.row_number,
                    "result": item.result,
                    "reason": item.reason,
                    "opportunity_id": item.opportunity_id,
                    "company": item.company,
                    "role": item.role,
                    "import_fingerprint": item.import_fingerprint,
                }
                for item in self.row_results
            ],
        }


@dataclass
class _ParsedLegacyRow:
    row_number: int
    company: str
    role: str
    date_applied: date
    location: str | None
    source: str | None
    status_raw: str
    outcome_raw: str | None
    follow_up: date | None
    notes: str | None
    decision: OwnerDecisionKind
    status: PipelineStatus
    outcome: OutcomeKind
    source_kind: SourceKind
    fingerprint: str


class LegacyOpportunityCsvImporter:
    """Migrate supported legacy tracker rows into structured Opportunities."""

    def parse_and_validate(
        self,
        source_path: Path,
        *,
        existing_fingerprints: set[str],
    ) -> tuple[list[_ParsedLegacyRow], list[LegacyRowResult]]:
        """Parse CSV; return valid rows and rejection/skip results (no writes)."""
        rows = _read_legacy_rows(source_path)
        valid: list[_ParsedLegacyRow] = []
        results: list[LegacyRowResult] = []
        for row_number, raw in rows:
            try:
                parsed = _map_row(row_number, raw)
            except ValueError as error:
                results.append(
                    LegacyRowResult(
                        row_number=row_number,
                        result="rejected",
                        reason=str(error),
                        company=_optional(raw.get("Company")),
                        role=_optional(raw.get("Role")),
                    )
                )
                continue
            if parsed.fingerprint in existing_fingerprints:
                results.append(
                    LegacyRowResult(
                        row_number=row_number,
                        result="skipped_duplicate",
                        reason="Legacy import fingerprint already present in store",
                        company=parsed.company,
                        role=parsed.role,
                        import_fingerprint=parsed.fingerprint,
                    )
                )
                continue
            valid.append(parsed)
        return valid, results

    def build_opportunity(
        self,
        parsed: _ParsedLegacyRow,
        *,
        source_file: str,
        imported_at: datetime | None = None,
    ) -> Opportunity:
        now = imported_at or datetime.now(UTC)
        applied_at = datetime(
            parsed.date_applied.year,
            parsed.date_applied.month,
            parsed.date_applied.day,
            tzinfo=UTC,
        )
        identity = OpportunityIdentity(
            opportunity_id=new_opportunity_id(),
            created_at=applied_at,
            source_kind=parsed.source_kind,
            platform_job_id=None,
            canonical_url=None,
            source_url=None,
            company=parsed.company,
            title=parsed.role,
            location_text=parsed.location,
            content_fingerprint=None,
        )
        decision = OwnerDecisionRecord(
            decision=parsed.decision,
            decided_at=applied_at,
            notes=None,
        )
        outcome = OutcomeRecord(
            outcome=parsed.outcome,
            interview_stage="none",
            follow_up_date=parsed.follow_up,
            notes=parsed.notes,
            updated_at=now,
        )
        provenance = LegacyImportProvenance(
            source_file=source_file,
            source_row_number=parsed.row_number,
            import_fingerprint=parsed.fingerprint,
            imported_at=now,
            legacy_status=parsed.status_raw,
            legacy_outcome=parsed.outcome_raw,
            legacy_source=parsed.source,
        )
        return Opportunity(
            identity=identity,
            status=parsed.status,
            decision=decision,
            outcome=outcome,
            strategy_summary=None,
            artifact_paths={},
            legacy_import=provenance,
            updated_at=now,
        )


def compute_legacy_fingerprint(
    *,
    date_applied: date,
    company: str,
    role: str,
    source: str | None,
) -> str:
    """Deterministic migration fingerprint (company+role+date+source).

    The live tracker has no job URL column; fingerprint uses available fields only.
    """
    payload = "|".join(
        [
            date_applied.isoformat(),
            _norm(company),
            _norm(role),
            _norm(source or ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_import_report(report: LegacyImportReport, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_jsonable(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _read_legacy_rows(source_path: Path) -> list[tuple[int, dict[str, str]]]:
    if not source_path.is_file():
        raise FileNotFoundError(f"Legacy CSV not found: {source_path}")
    text = source_path.read_text(encoding="utf-8-sig")
    # Support markdown pipe tables used in applications/application_tracker.csv.
    if "|" in text.splitlines()[0]:
        return _read_markdown_table(text)
    return _read_plain_csv(source_path)


def _read_plain_csv(source_path: Path) -> list[tuple[int, dict[str, str]]]:
    with source_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")
        headers = [_clean_header(name) for name in reader.fieldnames]
        required = ("Date Applied", "Company", "Role", "Status")
        missing = [name for name in required if name not in headers]
        if missing:
            raise ValueError(f"Legacy CSV missing required columns: {', '.join(missing)}")
        rows: list[tuple[int, dict[str, str]]] = []
        for index, raw in enumerate(reader, start=2):
            cleaned = {_clean_header(k): (v or "").strip() for k, v in raw.items() if k}
            if _is_separator_row(cleaned):
                continue
            if not any(cleaned.values()):
                continue
            rows.append((index, cleaned))
        return rows


def _read_markdown_table(text: str) -> list[tuple[int, dict[str, str]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Legacy tracker file is empty")
    header_cells = _split_pipe_row(lines[0])
    headers = [_clean_header(cell) for cell in header_cells]
    required = ("Date Applied", "Company", "Role", "Status")
    missing = [name for name in required if name not in headers]
    if missing:
        raise ValueError(f"Legacy tracker missing required columns: {', '.join(missing)}")

    rows: list[tuple[int, dict[str, str]]] = []
    for line_number, line in enumerate(lines[1:], start=2):
        cells = _split_pipe_row(line)
        if not cells:
            continue
        # Separator rows: --- under each column
        if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells if cell):
            continue
        # Pad/truncate to header width
        while len(cells) < len(headers):
            cells.append("")
        raw = {headers[i]: cells[i].strip() for i in range(len(headers))}
        if _is_separator_row(raw) or not any(raw.values()):
            continue
        rows.append((line_number, raw))
    return rows


def _split_pipe_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _clean_header(name: str) -> str:
    return " ".join(name.replace("\ufeff", "").strip().split())


def _is_separator_row(raw: dict[str, str]) -> bool:
    values = [value.strip() for value in raw.values() if value and value.strip()]
    if not values:
        return True
    return all(re.fullmatch(r"-{3,}", value.replace(" ", "")) for value in values)


def _map_row(row_number: int, raw: dict[str, str]) -> _ParsedLegacyRow:
    company = _require(raw, "Company")
    role = _require(raw, "Role")
    date_applied = _parse_date(_require(raw, "Date Applied"), field_name="Date Applied")
    status_raw = _require(raw, "Status")
    status_key = status_raw.strip().lower()
    if status_key not in LEGACY_STATUS_MAP:
        supported = ", ".join(sorted({key.title() for key in LEGACY_STATUS_MAP}))
        raise ValueError(
            f"Unsupported Status '{status_raw}'. Supported: {supported}"
        )
    mapping = LEGACY_STATUS_MAP[status_key]
    outcome_raw = _optional(raw.get("Outcome"))
    if outcome_raw:
        outcome_key = outcome_raw.strip().lower()
        if outcome_key not in LEGACY_OUTCOME_MAP:
            supported = ", ".join(sorted(LEGACY_OUTCOME_MAP))
            raise ValueError(
                f"Unsupported Outcome '{outcome_raw}'. Supported: {supported}"
            )
        outcome = LEGACY_OUTCOME_MAP[outcome_key]
    elif mapping.outcome is not None:
        outcome = mapping.outcome
    else:
        outcome = "unknown"

    follow_raw = _optional(raw.get("Follow-up Date"))
    follow_up = _parse_date(follow_raw, field_name="Follow-up Date") if follow_raw else None
    source = _optional(raw.get("Source"))
    location = _optional(raw.get("Location"))
    notes = _optional(raw.get("Notes"))
    fingerprint = compute_legacy_fingerprint(
        date_applied=date_applied,
        company=company,
        role=role,
        source=source,
    )
    return _ParsedLegacyRow(
        row_number=row_number,
        company=company,
        role=role,
        date_applied=date_applied,
        location=location,
        source=source,
        status_raw=status_raw.strip(),
        outcome_raw=outcome_raw,
        follow_up=follow_up,
        notes=notes,
        decision=mapping.decision,
        status=mapping.status,
        outcome=outcome,
        source_kind=_infer_source_kind(source),
        fingerprint=fingerprint,
    )


def _infer_source_kind(source: str | None) -> SourceKind:
    if not source:
        return "import"
    lowered = source.lower()
    if "linkedin" in lowered:
        return "linkedin"
    if "seek" in lowered:
        return "seek"
    if "indeed" in lowered:
        return "indeed"
    return "import"


def _require(raw: dict[str, str], key: str) -> str:
    value = _optional(raw.get(key))
    if not value:
        raise ValueError(f"Missing required field '{key}'")
    return value


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() == "N/A":
        return None
    return cleaned


def _parse_date(value: str, *, field_name: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(
            f"Invalid {field_name} '{value}'. Expected YYYY-MM-DD."
        ) from error


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())
