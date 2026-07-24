"""Operational CSV bridge: export + one-time legacy import (M3).

Structured store remains the system of record. No bidirectional sync.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .csv_export import DEFAULT_EXPORT_PATH, OpportunityCsvExporter
from .legacy_import import (
    LegacyImportReport,
    LegacyOpportunityCsvImporter,
    LegacyRowResult,
    write_import_report,
)
from .service import OpportunityService


class OpportunityCsvBridge:
    """Thin orchestration over OpportunityService for CSV export/import."""

    def __init__(self, opportunity_service: OpportunityService | None = None) -> None:
        self._opportunities = opportunity_service or OpportunityService()
        self._exporter = OpportunityCsvExporter()
        self._importer = LegacyOpportunityCsvImporter()

    @classmethod
    def from_path(cls, root: Path) -> OpportunityCsvBridge:
        return cls(opportunity_service=OpportunityService.from_path(root))

    def export_opportunities_csv(self, output_path: Path | None = None) -> Path:
        """Export current opportunities to CSV. Does not mutate the store."""
        target = Path(output_path) if output_path is not None else DEFAULT_EXPORT_PATH
        records = self._opportunities.list_opportunities()
        return self._exporter.export(records, target)

    def import_legacy_opportunities_csv(
        self,
        source_path: Path,
        *,
        dry_run: bool = False,
        report_path: Path | None = None,
    ) -> LegacyImportReport:
        """One-time migration import. Row-atomic; dry_run creates nothing."""
        started = datetime.now(UTC)
        source_path = Path(source_path)
        existing = self._opportunities.legacy_import_fingerprints()
        valid, early_results = self._importer.parse_and_validate(
            source_path,
            existing_fingerprints=existing,
        )

        row_results: list[LegacyRowResult] = list(early_results)
        imported = 0
        skipped = sum(1 for item in early_results if item.result == "skipped_duplicate")
        failed = sum(1 for item in early_results if item.result == "rejected")

        seen_in_batch: set[str] = set(existing)

        for parsed in valid:
            if parsed.fingerprint in seen_in_batch:
                row_results.append(
                    LegacyRowResult(
                        row_number=parsed.row_number,
                        result="skipped_duplicate",
                        reason="Duplicate fingerprint within the same import batch",
                        company=parsed.company,
                        role=parsed.role,
                        import_fingerprint=parsed.fingerprint,
                    )
                )
                skipped += 1
                continue

            if dry_run:
                row_results.append(
                    LegacyRowResult(
                        row_number=parsed.row_number,
                        result="would_import",
                        reason=(
                            f"Would create opportunity "
                            f"(decision={parsed.decision}, status={parsed.status}, "
                            f"outcome={parsed.outcome})"
                        ),
                        company=parsed.company,
                        role=parsed.role,
                        import_fingerprint=parsed.fingerprint,
                    )
                )
                seen_in_batch.add(parsed.fingerprint)
                continue

            opportunity = self._importer.build_opportunity(
                parsed,
                source_file=str(source_path),
                imported_at=datetime.now(UTC),
            )
            saved = self._opportunities.create_from_legacy(opportunity)
            seen_in_batch.add(parsed.fingerprint)
            imported += 1
            row_results.append(
                LegacyRowResult(
                    row_number=parsed.row_number,
                    result="imported",
                    reason="Created structured opportunity from legacy tracker row",
                    opportunity_id=saved.opportunity_id,
                    company=parsed.company,
                    role=parsed.role,
                    import_fingerprint=parsed.fingerprint,
                )
            )

        row_results.sort(key=lambda item: item.row_number)
        completed = datetime.now(UTC)
        report = LegacyImportReport(
            source_file=str(source_path),
            started_at=started,
            completed_at=completed,
            dry_run=dry_run,
            rows_read=len(valid) + len(early_results),
            rows_imported=0 if dry_run else imported,
            rows_skipped=skipped,
            rows_failed=failed,
            row_results=row_results,
        )
        if report_path is not None:
            write_import_report(report, Path(report_path))
        return report
