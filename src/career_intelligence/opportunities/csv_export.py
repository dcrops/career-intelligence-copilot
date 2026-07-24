"""Deterministic CSV export of structured Opportunity records (M3)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from .models import Opportunity

# Stable column order for spreadsheet review (Excel-friendly on Windows).
EXPORT_COLUMNS: tuple[str, ...] = (
    "opportunity_id",
    "created_at",
    "updated_at",
    "job_title",
    "company",
    "location_text",
    "source_kind",
    "source_url",
    "canonical_url",
    "platform_job_id",
    "pursuit_posture",
    "application_tier",
    "practical_value",
    "technical_fit",
    "commercial_fit",
    "portfolio_fit",
    "owner_decision",
    "decided_at",
    "decision_notes",
    "status",
    "outcome",
    "interview_stage",
    "follow_up_date",
    "outcome_notes",
    "has_artifacts",
    "legacy_import_fingerprint",
    "legacy_source_file",
)

DEFAULT_EXPORT_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "exports" / "opportunities.csv"
)


class OpportunityCsvExporter:
    """Flatten Opportunity records into a deterministic UTF-8-SIG CSV."""

    def export(
        self,
        opportunities: list[Opportunity],
        output_path: Path,
    ) -> Path:
        """Write opportunities to ``output_path``. Does not mutate records."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Newest first matches OpportunityService.list_opportunities ordering.
        ordered = sorted(opportunities, key=lambda item: item.opportunity_id, reverse=True)
        rows = [self.row_from_opportunity(item) for item in ordered]

        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        try:
            with temporary.open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(EXPORT_COLUMNS),
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(rows)
            temporary.replace(output_path)
        except OSError:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
            raise
        return output_path

    def row_from_opportunity(self, opportunity: Opportunity) -> dict[str, str]:
        identity = opportunity.identity
        summary = opportunity.strategy_summary
        decision = opportunity.decision
        outcome = opportunity.outcome
        legacy = opportunity.legacy_import
        return {
            "opportunity_id": opportunity.opportunity_id,
            "created_at": _fmt_datetime(identity.created_at),
            "updated_at": _fmt_datetime(opportunity.updated_at),
            "job_title": _cell(identity.title),
            "company": _cell(identity.company),
            "location_text": _cell(identity.location_text),
            "source_kind": identity.source_kind,
            "source_url": _cell(str(identity.source_url) if identity.source_url else None),
            "canonical_url": _cell(
                str(identity.canonical_url) if identity.canonical_url else None
            ),
            "platform_job_id": _cell(identity.platform_job_id),
            "pursuit_posture": _cell(summary.pursuit_posture if summary else None),
            "application_tier": _cell(summary.application_tier if summary else None),
            "practical_value": _cell(summary.practical_value if summary else None),
            "technical_fit": _cell(summary.technical_fit if summary else None),
            "commercial_fit": _cell(summary.commercial_fit if summary else None),
            "portfolio_fit": _cell(summary.portfolio_fit if summary else None),
            "owner_decision": _cell(decision.decision if decision else None),
            "decided_at": _fmt_datetime(decision.decided_at) if decision else "",
            "decision_notes": _cell(decision.notes if decision else None),
            "status": opportunity.status,
            "outcome": _cell(outcome.outcome if outcome else None),
            "interview_stage": _cell(outcome.interview_stage if outcome else None),
            "follow_up_date": _fmt_date(outcome.follow_up_date) if outcome else "",
            "outcome_notes": _cell(outcome.notes if outcome else None),
            "has_artifacts": "yes" if opportunity.artifact_paths else "no",
            "legacy_import_fingerprint": _cell(
                legacy.import_fingerprint if legacy else None
            ),
            "legacy_source_file": _cell(legacy.source_file if legacy else None),
        }


def _cell(value: str | None) -> str:
    return "" if value is None else value


def _fmt_datetime(value: datetime) -> str:
    text = value.isoformat()
    return text.replace("+00:00", "Z")


def _fmt_date(value: date | None) -> str:
    if value is None:
        return ""
    return value.isoformat()
