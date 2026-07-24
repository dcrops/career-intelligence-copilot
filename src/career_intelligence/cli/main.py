"""Command-line interface for Career Intelligence Copilot."""

from pathlib import Path
from typing import Annotated, Never

import typer
import yaml
from pydantic import BaseModel

from career_intelligence.opportunities import (
    DEFAULT_EXPORT_PATH,
    INTERVIEW_STAGES,
    OUTCOME_KINDS,
    OWNER_DECISION_KINDS,
    PIPELINE_STATUSES,
    OpportunityCsvBridge,
    OpportunityError,
    OpportunityNotFoundError,
    OpportunityService,
    OpportunityTransitionError,
    OpportunityValidationError,
)
from career_intelligence.opportunity_comparison import (
    OpportunityComparisonError,
    OpportunityComparisonService,
    OpportunityComparisonValidationError,
)
from career_intelligence.profile import (
    CareerProfileService,
    ProfileError,
    ProfileNotFoundError,
    ProfileSection,
    ProfileStorageError,
    ProfileValidationError,
    UnknownSectionError,
)

app = typer.Typer(help="Career Intelligence Copilot.")
profile_app = typer.Typer(help="Manage and inspect the career profile.")
opportunity_app = typer.Typer(
    help="Inspect and update persisted opportunities (M1–M4)."
)
app.add_typer(profile_app, name="profile")
app.add_typer(opportunity_app, name="opportunity")

PathOption = Annotated[
    Path | None,
    typer.Option("--path", help="Override the configured career profile path."),
]

OpportunitiesDirOption = Annotated[
    Path | None,
    typer.Option(
        "--dir",
        help="Override the opportunities store directory (default: data/opportunities).",
    ),
]


def _profile_service(path: Path | None) -> CareerProfileService:
    return CareerProfileService.from_path(path) if path else CareerProfileService()


def _opportunity_service(root: Path | None) -> OpportunityService:
    return OpportunityService.from_path(root) if root else OpportunityService()


def _csv_bridge(root: Path | None) -> OpportunityCsvBridge:
    return (
        OpportunityCsvBridge.from_path(root)
        if root
        else OpportunityCsvBridge()
    )


def _render(value: object) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif isinstance(value, list):
        value = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in value
        ]
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True).rstrip()


def _format_location(location: tuple[str | int, ...]) -> str:
    return ".".join(str(part) for part in location)


def _exit_for_profile(error: ProfileError) -> Never:
    if isinstance(error, ProfileValidationError):
        typer.echo("Career profile validation failed:", err=True)
        for detail in error.errors:
            typer.echo(f"- {_format_location(detail.loc)}: {detail.msg}", err=True)
        raise typer.Exit(code=1)

    typer.echo(str(error), err=True)
    code = 1 if isinstance(error, UnknownSectionError) else 2
    raise typer.Exit(code=code)


def _exit_for_opportunity(error: OpportunityError) -> Never:
    if isinstance(error, OpportunityValidationError):
        typer.echo("Opportunity validation failed:", err=True)
        for detail in error.errors:
            typer.echo(f"- {_format_location(detail.loc)}: {detail.msg}", err=True)
        raise typer.Exit(code=1)

    typer.echo(str(error), err=True)
    if isinstance(error, (OpportunityNotFoundError, OpportunityTransitionError)):
        raise typer.Exit(code=1)
    raise typer.Exit(code=2)


def _exit_for_comparison(error: OpportunityComparisonError) -> Never:
    if isinstance(error, OpportunityComparisonValidationError):
        typer.echo("Opportunity comparison validation failed:", err=True)
        for detail in error.errors:
            typer.echo(f"- {_format_location(detail.loc)}: {detail.msg}", err=True)
        raise typer.Exit(code=1)
    typer.echo(str(error), err=True)
    raise typer.Exit(code=2)


@profile_app.command("validate")
def validate_profile(path: PathOption = None) -> None:
    """Validate the configured career profile."""
    try:
        _profile_service(path).validate()
    except (ProfileValidationError, ProfileNotFoundError, ProfileStorageError) as error:
        _exit_for_profile(error)
    typer.echo("Career profile is valid.")


@profile_app.command("summary")
def profile_summary(path: PathOption = None) -> None:
    """Display a compact career-profile summary."""
    try:
        summary = _profile_service(path).summary()
    except ProfileError as error:
        _exit_for_profile(error)
    typer.echo(_render(summary))


@profile_app.command("show")
def show_profile_section(
    section: Annotated[ProfileSection, typer.Argument(help="Profile section to display.")],
    path: PathOption = None,
) -> None:
    """Display one named profile section."""
    try:
        value = _profile_service(path).get_section(section)
    except ProfileError as error:
        _exit_for_profile(error)
    typer.echo(_render(value))


@profile_app.command("init")
def init_profile(
    path: PathOption = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing profile with the scaffold."),
    ] = False,
) -> None:
    """Create a valid editable career-profile scaffold."""
    try:
        _profile_service(path).init_profile(force=force)
    except ProfileError as error:
        _exit_for_profile(error)
    target = path or "the configured path"
    typer.echo(f"Career profile initialized at {target}.")


@opportunity_app.command("list")
def list_opportunities(
    dir: OpportunitiesDirOption = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit full YAML instead of the compact table."),
    ] = False,
) -> None:
    """List persisted opportunities (newest first)."""
    try:
        items = _opportunity_service(dir).list_opportunities()
    except OpportunityError as error:
        _exit_for_opportunity(error)

    if yaml_output:
        typer.echo(_render(items))
        return

    if not items:
        typer.echo("No opportunities persisted.")
        return

    header = (
        f"{'opportunity_id':<34} {'status':<12} {'posture':<22} "
        f"{'tier':<10} {'company':<22} title"
    )
    typer.echo(header)
    typer.echo("-" * len(header))
    for item in items:
        company = (item.identity.company or "—")[:20]
        title = (item.identity.title or "—")[:40]
        created = item.identity.created_at.date().isoformat()
        summary = item.strategy_summary
        posture = summary.pursuit_posture if summary else "—"
        tier = summary.application_tier if summary else "—"
        typer.echo(
            f"{item.opportunity_id:<34} {item.status:<12} "
            f"{posture:<22} "
            f"{tier:<10} "
            f"{company:<22} {title}  ({created})"
        )


@opportunity_app.command("show")
def show_opportunity(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
) -> None:
    """Show one persisted opportunity (identity, decision, outcome, artifacts)."""
    try:
        opportunity = _opportunity_service(dir).get(opportunity_id)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    typer.echo(_render(opportunity))


@opportunity_app.command("decide")
def decide_opportunity(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    decision: Annotated[
        str,
        typer.Argument(help=f"Owner decision: {', '.join(OWNER_DECISION_KINDS)}."),
    ],
    dir: OpportunitiesDirOption = None,
    notes: Annotated[
        str | None,
        typer.Option("--notes", help="Optional decision notes."),
    ] = None,
) -> None:
    """Record the owner's apply / skip / defer decision (does not change status)."""
    try:
        opportunity = _opportunity_service(dir).record_decision(
            opportunity_id,
            decision,  # type: ignore[arg-type]
            notes=notes,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    typer.echo(
        f"Recorded decision '{opportunity.decision.decision}' "
        f"for {opportunity.opportunity_id} "
        f"(status unchanged: {opportunity.status})."
    )


@opportunity_app.command("outcome")
def update_opportunity_outcome(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    status: Annotated[
        str | None,
        typer.Option("--status", help=f"Pipeline status: {', '.join(PIPELINE_STATUSES)}."),
    ] = None,
    outcome: Annotated[
        str | None,
        typer.Option("--outcome", help=f"Outcome kind: {', '.join(OUTCOME_KINDS)}."),
    ] = None,
    interview_stage: Annotated[
        str | None,
        typer.Option(
            "--interview-stage",
            help=f"Interview stage: {', '.join(INTERVIEW_STAGES)}.",
        ),
    ] = None,
    follow_up_date: Annotated[
        str | None,
        typer.Option("--follow-up-date", help="Follow-up date (YYYY-MM-DD)."),
    ] = None,
    clear_follow_up: Annotated[
        bool,
        typer.Option("--clear-follow-up", help="Clear any stored follow-up date."),
    ] = False,
    notes: Annotated[
        str | None,
        typer.Option("--notes", help="Optional outcome notes."),
    ] = None,
) -> None:
    """Update pipeline status and/or outcome details."""
    parsed_follow_up = None
    if follow_up_date is not None:
        from datetime import date

        try:
            parsed_follow_up = date.fromisoformat(follow_up_date)
        except ValueError:
            typer.echo(
                f"Invalid --follow-up-date '{follow_up_date}'. Use YYYY-MM-DD.",
                err=True,
            )
            raise typer.Exit(code=1) from None

    try:
        opportunity = _opportunity_service(dir).update_outcome(
            opportunity_id,
            status=status,  # type: ignore[arg-type]
            outcome=outcome,  # type: ignore[arg-type]
            interview_stage=interview_stage,  # type: ignore[arg-type]
            follow_up_date=parsed_follow_up,
            notes=notes,
            clear_follow_up_date=clear_follow_up,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)

    outcome_kind = opportunity.outcome.outcome if opportunity.outcome else "—"
    typer.echo(
        f"Updated {opportunity.opportunity_id}: "
        f"status={opportunity.status}, outcome={outcome_kind}."
    )


@opportunity_app.command("export-csv")
def export_opportunities_csv(
    dir: OpportunitiesDirOption = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=f"Output CSV path (default: {DEFAULT_EXPORT_PATH}).",
        ),
    ] = None,
) -> None:
    """Export structured opportunities to a spreadsheet CSV (derived view)."""
    try:
        path = _csv_bridge(dir).export_opportunities_csv(output)
        count = len(_opportunity_service(dir).list_opportunities())
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except OSError as error:
        typer.echo(f"Could not write export: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(f"Exported {count} opportunity record(s) to {path}")


@opportunity_app.command("import-legacy-csv")
def import_legacy_csv(
    source: Annotated[
        Path,
        typer.Argument(help="Path to legacy application_tracker.csv (or fixture copy)."),
    ],
    dir: OpportunitiesDirOption = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Validate only; create no opportunities."),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Write JSON import report to this path.",
        ),
    ] = None,
) -> None:
    """One-time migration import from the legacy tracker CSV (not continuous sync)."""
    try:
        result = _csv_bridge(dir).import_legacy_opportunities_csv(
            source,
            dry_run=dry_run,
            report_path=report,
        )
    except FileNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    except (OpportunityError, ValueError, OSError) as error:
        if isinstance(error, OpportunityError):
            _exit_for_opportunity(error)
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    mode = "DRY RUN" if result.dry_run else "IMPORT"
    typer.echo(f"Legacy CSV {mode}: {result.source_file}")
    typer.echo(f"  rows_read: {result.rows_read}")
    typer.echo(f"  rows_imported: {result.rows_imported}")
    typer.echo(f"  rows_skipped (duplicates): {result.rows_skipped}")
    typer.echo(f"  rows_failed: {result.rows_failed}")
    if report is not None:
        typer.echo(f"  report: {report}")
    for item in result.row_results:
        oid = item.opportunity_id or "—"
        typer.echo(
            f"  row {item.row_number}: {item.result} — {item.reason} [{oid}]"
        )
    if result.rows_failed and not result.dry_run:
        raise typer.Exit(code=1)


@opportunity_app.command("backfill-identity")
def backfill_identity(
    dir: OpportunitiesDirOption = None,
) -> None:
    """Fill missing title/company from trusted posting.json artifacts (M4a).

    Does not call OpenAI. Skips rows without artifacts or without identity in
    posting.json. Never overwrites fields that are already set.
    """
    try:
        results = _opportunity_service(dir).backfill_identity_from_posting_artifacts()
    except OpportunityError as error:
        _exit_for_opportunity(error)

    updated = sum(1 for item in results if item["result"] == "updated")
    skipped = sum(1 for item in results if item["result"] == "skipped")
    failed = sum(1 for item in results if item["result"] == "failed")
    typer.echo(
        f"Identity backfill: updated={updated} skipped={skipped} failed={failed}"
    )
    for item in results:
        typer.echo(
            f"  {item['opportunity_id']}: {item['result']} — {item['reason']}"
        )
    if failed:
        raise typer.Exit(code=1)


@opportunity_app.command("compare")
def compare_open_opportunities(
    dir: OpportunitiesDirOption = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit full YAML comparison result."),
    ] = False,
) -> None:
    """Rank open opportunities for effort prioritisation (owner review required)."""
    try:
        opportunities = _opportunity_service(dir).list_opportunities()
        comparison = OpportunityComparisonService().compare_open(opportunities)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except OpportunityComparisonError as error:
        _exit_for_comparison(error)

    if yaml_output:
        typer.echo(_render(comparison))
        return

    typer.echo(
        f"Open opportunities ranked: {comparison.open_count} "
        f"(excluded {comparison.excluded_count}). Owner review required."
    )
    if not comparison.items:
        typer.echo("No open opportunities to compare.")
        return

    for item in comparison.items:
        company = item.company or "—"
        title = item.title or "—"
        posture = item.pursuit_posture or "—"
        tier = item.application_tier or "—"
        typer.echo("")
        typer.echo(
            f"{item.rank}. {item.opportunity_id}  [{item.status}]  "
            f"{company} — {title}"
        )
        typer.echo(
            f"   posture={posture}  tier={tier}  fit_strength={item.fit_strength}/15"
        )
        for reason in item.reasons:
            typer.echo(f"   - {reason}")


if __name__ == "__main__":
    app()
