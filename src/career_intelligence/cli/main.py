"""Command-line interface for Career Intelligence Copilot."""

from pathlib import Path
from typing import Annotated, Never

import typer
import yaml
from pydantic import BaseModel

from career_intelligence.application_package import (
    DEFAULT_PACKAGES_ROOT,
    ApplicationPackageEligibilityError,
    ApplicationPackageError,
    ApplicationPackageIntegrityError,
    ApplicationPackageNotFoundError,
    ApplicationPackageService,
    ApplicationPackageStorageError,
    ApplicationPackageValidationError,
)
from career_intelligence.application_preparation import (
    DEFAULT_PREPARATION_RUNS_ROOT,
    ApplicationPreparationError,
    ApplicationPreparationOrchestrator,
    ApplicationPreparationStorageError,
    ApplicationPreparationValidationError,
    PreparationRunNotFoundError,
    PreparationRunState,
)
from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterPlanGateError,
    CoverLetterPlanOptions,
)
from career_intelligence.cv_generation import (
    CvGenerationGateError,
    CvGenerationOptions,
    TailoringOptions,
    TailoringPlanGateError,
)
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
from career_intelligence.submission import (
    DEFAULT_SUBMISSION_ATTEMPTS_ROOT,
    FakeSubmissionAdapter,
    ManualAssistedAdapter,
    SubmissionAttempt,
    SubmissionAttemptNotFoundError,
    SubmissionChannelError,
    SubmissionDuplicateError,
    SubmissionError,
    SubmissionGateError,
    SubmissionOrchestrator,
    SubmissionReadinessReport,
    SubmissionStorageError,
    SubmissionValidationError,
)
from career_intelligence.truth_validation import (
    DEFAULT_TRUTH_REPORTS_ROOT,
    JsonDirectoryTruthReportStore,
    TruthGateError,
    TruthReport,
    TruthReportNotFoundError,
    TruthValidationError,
    TruthValidationService,
    evaluate_package_truth,
)
from career_intelligence.pipeline import (
    DEFAULT_PIPELINE_EVENTS_ROOT,
    DEFAULT_PIPELINE_EXPORT_PATH,
    JsonDirectoryPipelineEventStore,
    PackageEvidenceRef,
    PipelineApplyResult,
    PipelineConsistencyError,
    PipelineDivergenceError,
    PipelineError,
    PipelineEvent,
    PipelineEvidence,
    PipelinePartialWriteError,
    PipelineStorageError,
    PipelineSummaryReport,
    PipelineTrackingService,
    PipelineTransitionError,
    PipelineValidationError,
)
from career_intelligence.agent import (
    DEFAULT_AGENT_RUNS_ROOT,
    DEFAULT_MAX_STEPS,
    AgentGoal,
    AgentRunNotFoundError,
    AgentRuntimeError,
    AgentStorageError,
    JsonDirectoryAgentRunStore,
    build_agent_runtime,
    format_agent_history,
    format_agent_list_line,
    format_agent_run_report,
)

app = typer.Typer(help="Career Intelligence Copilot.")
profile_app = typer.Typer(help="Manage and inspect the career profile.")
opportunity_app = typer.Typer(
    help="Inspect and update persisted opportunities (M1–M4)."
)
package_app = typer.Typer(
    help="Prepare and inspect application packages (FR-010)."
)
preparation_app = typer.Typer(
    help="Run application preparation orchestration (FR-011)."
)
submission_app = typer.Typer(
    help="Run assisted submission workflow (FR-012)."
)
pipeline_app = typer.Typer(
    help=(
        "Track and report the application pipeline after submit (FR-013). "
        "Commands: list, show, history, preparing, submit, acknowledge, interview, "
        "reject, offer, accept, withdraw, follow-up, note, evidence, correct, "
        "check, repair, report, due, export."
    ),
)
truth_app = typer.Typer(
    help=(
        "Validate recruiter-facing Markdown claims (FR-014). "
        "Commands: validate, show, validate-package."
    ),
)
agent_app = typer.Typer(
    help=(
        "Bounded Opportunity Preparation Agent (FR-015). "
        "Commands: run, resume, show, history, list. "
        "Does not submit, advance pipeline, or invoke FR-008."
    ),
)
app.add_typer(profile_app, name="profile")
app.add_typer(opportunity_app, name="opportunity")
app.add_typer(package_app, name="package")
app.add_typer(preparation_app, name="preparation")
app.add_typer(submission_app, name="submission")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(truth_app, name="truth")
app.add_typer(agent_app, name="agent")

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

PackagesDirOption = Annotated[
    Path | None,
    typer.Option(
        "--packages-dir",
        help=(
            "Override the application-packages store directory "
            f"(default: {DEFAULT_PACKAGES_ROOT})."
        ),
    ),
]

PreparationRunsDirOption = Annotated[
    Path | None,
    typer.Option(
        "--runs-dir",
        help=(
            "Override the preparation-runs store directory "
            f"(default: {DEFAULT_PREPARATION_RUNS_ROOT})."
        ),
    ),
]

SubmissionAttemptsDirOption = Annotated[
    Path | None,
    typer.Option(
        "--attempts-dir",
        help=(
            "Override the submission-attempts store directory "
            f"(default: {DEFAULT_SUBMISSION_ATTEMPTS_ROOT})."
        ),
    ),
]

PipelineEventsDirOption = Annotated[
    Path | None,
    typer.Option(
        "--events-dir",
        help=(
            "Override the pipeline-events store directory "
            f"(default: {DEFAULT_PIPELINE_EVENTS_ROOT})."
        ),
    ),
]

TruthReportsDirOption = Annotated[
    Path | None,
    typer.Option(
        "--truth-reports-dir",
        help=(
            "Override the truth-reports store directory "
            f"(default: {DEFAULT_TRUTH_REPORTS_ROOT})."
        ),
    ),
]

AgentRunsDirOption = Annotated[
    Path | None,
    typer.Option(
        "--agent-runs-dir",
        help=(
            "Override the agent-runs store directory "
            f"(default: {DEFAULT_AGENT_RUNS_ROOT})."
        ),
    ),
]

ProfilePathOption = Annotated[
    Path | None,
    typer.Option(
        "--profile",
        help="Override the career profile path used for package preparation.",
    ),
]


def _profile_service(path: Path | None) -> CareerProfileService:
    return CareerProfileService.from_path(path) if path else CareerProfileService()


def _opportunity_service(root: Path | None) -> OpportunityService:
    return OpportunityService.from_path(root) if root else OpportunityService()


def _package_service(
    *,
    opportunities_dir: Path | None,
    packages_dir: Path | None,
    profile_path: Path | None,
    cv_output_dir: Path | None = None,
    cover_letter_output_dir: Path | None = None,
) -> ApplicationPackageService:
    opportunities = _opportunity_service(opportunities_dir)
    profile = (
        CareerProfileService.from_path(profile_path)
        if profile_path is not None
        else CareerProfileService()
    )
    return ApplicationPackageService(
        opportunities,
        profile=profile,
        packages_root=packages_dir,
        cv_output_dir=cv_output_dir,
        cover_letter_output_dir=cover_letter_output_dir,
    )


def _preparation_orchestrator(
    *,
    opportunities_dir: Path | None,
    packages_dir: Path | None,
    profile_path: Path | None,
    runs_dir: Path | None,
    cv_output_dir: Path | None = None,
    cover_letter_output_dir: Path | None = None,
) -> ApplicationPreparationOrchestrator:
    opportunities = _opportunity_service(opportunities_dir)
    packages = _package_service(
        opportunities_dir=opportunities_dir,
        packages_dir=packages_dir,
        profile_path=profile_path,
        cv_output_dir=cv_output_dir,
        cover_letter_output_dir=cover_letter_output_dir,
    )
    return ApplicationPreparationOrchestrator(
        opportunities,
        packages,
        runs_root=runs_dir,
    )


def _submission_orchestrator(
    *,
    opportunities_dir: Path | None,
    packages_dir: Path | None,
    profile_path: Path | None,
    attempts_dir: Path | None,
    cv_output_dir: Path | None = None,
    cover_letter_output_dir: Path | None = None,
    fake_outcome: str | None = None,
    truth_reports_dir: Path | None = None,
) -> SubmissionOrchestrator:
    opportunities = _opportunity_service(opportunities_dir)
    packages = _package_service(
        opportunities_dir=opportunities_dir,
        packages_dir=packages_dir,
        profile_path=profile_path,
        cv_output_dir=cv_output_dir,
        cover_letter_output_dir=cover_letter_output_dir,
    )
    fake = FakeSubmissionAdapter()
    if fake_outcome is not None:
        fake.set_outcome(fake_outcome)  # type: ignore[arg-type]
    return SubmissionOrchestrator(
        opportunities,
        packages,
        attempts_root=attempts_dir,
        adapters={
            "fake": fake,
            "manual_assisted": ManualAssistedAdapter(),
        },
        truth_reports_root=truth_reports_dir,
        enable_truth_gate=True,
    )


def _pipeline_tracking_service(
    *,
    opportunities_dir: Path | None,
    events_dir: Path | None,
) -> PipelineTrackingService:
    opportunities = _opportunity_service(opportunities_dir)
    if events_dir is not None:
        events_root = events_dir
    elif opportunities_dir is not None:
        events_root = opportunities_dir.parent / "pipeline_events"
    else:
        events_root = DEFAULT_PIPELINE_EVENTS_ROOT
    return PipelineTrackingService(
        opportunities=opportunities,
        events=JsonDirectoryPipelineEventStore(events_root),
    )


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


def _exit_for_package(error: ApplicationPackageError) -> Never:
    if isinstance(error, ApplicationPackageValidationError):
        typer.echo("Application package validation failed:", err=True)
        for detail in error.errors:
            typer.echo(f"- {_format_location(detail.loc)}: {detail.msg}", err=True)
        raise typer.Exit(code=1)

    typer.echo(str(error), err=True)
    if isinstance(
        error,
        (
            ApplicationPackageNotFoundError,
            ApplicationPackageEligibilityError,
            ApplicationPackageIntegrityError,
        ),
    ):
        raise typer.Exit(code=1)
    if isinstance(error, ApplicationPackageStorageError):
        raise typer.Exit(code=2)
    raise typer.Exit(code=2)


def _exit_for_preparation(error: ApplicationPreparationError) -> Never:
    if isinstance(error, ApplicationPreparationValidationError):
        typer.echo("Application preparation validation failed:", err=True)
        for detail in error.errors:
            typer.echo(f"- {_format_location(detail.loc)}: {detail.msg}", err=True)
        raise typer.Exit(code=1)

    typer.echo(str(error), err=True)
    if isinstance(error, PreparationRunNotFoundError):
        raise typer.Exit(code=1)
    if isinstance(error, ApplicationPreparationStorageError):
        raise typer.Exit(code=2)
    raise typer.Exit(code=2)


def _print_preparation_summary(state: PreparationRunState) -> None:
    typer.echo(f"run_id: {state.run_id}")
    typer.echo(f"opportunity_id: {state.opportunity_id}")
    typer.echo(f"status: {state.status}")
    steps = ", ".join(step.step_id for step in state.completed_steps) or "(none)"
    typer.echo(f"completed_steps: {steps}")
    if state.package is not None:
        typer.echo(
            f"package: {state.package.opportunity_id} "
            f"(prepared_at={state.package.prepared_at.isoformat()})"
        )
    if state.error is not None:
        typer.echo(
            f"error: step={state.error.step_id} "
            f"type={state.error.error_type} "
            f"message={state.error.message}"
        )


def _print_package_summary(manifest) -> None:
    acq = manifest.evidence.acquisition
    typer.echo(f"opportunity_id: {manifest.opportunity_id}")
    typer.echo(f"prepared_at: {manifest.prepared_at.isoformat()}")
    typer.echo(f"owner_review_required: {manifest.owner_review_required}")
    typer.echo(
        f"company/title: {acq.company or '—'} / {acq.title or '—'}"
    )
    typer.echo(f"source_kind: {acq.source_kind}")
    typer.echo("evidence artefacts:")
    for name, relative in sorted(manifest.evidence.artifact_paths.items()):
        typer.echo(f"  - {name}: {relative}")
    typer.echo("cv:")
    typer.echo(f"  markdown: {manifest.cv.markdown_path}")
    typer.echo(f"  html: {manifest.cv.html_path}")
    typer.echo(f"  plan: {manifest.cv.plan_json_path}")
    typer.echo("cover_letter:")
    typer.echo(f"  markdown: {manifest.cover_letter.markdown_path}")
    typer.echo(f"  html: {manifest.cover_letter.html_path}")
    typer.echo(f"  plan: {manifest.cover_letter.plan_json_path}")


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


@package_app.command("prepare")
def prepare_package(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help=(
                "Explicitly set FR-006/FR-007 owner-approval gates "
                "(required to prepare)."
            ),
        ),
    ] = False,
    override_material_benefit: Annotated[
        bool,
        typer.Option(
            "--override-material-benefit",
            help=(
                "Record an explicit FR-006/FR-007 material-benefit override "
                "when the strategy tier does not already justify documents."
            ),
        ),
    ] = False,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full package manifest as YAML."),
    ] = False,
) -> None:
    """Prepare or regenerate the current Application Package for an apply Opportunity.

    Thin adapter over ApplicationPackageService. Existing FR-006 / FR-007 approval
    gates remain enforced — pass ``--approve`` to set them explicitly.
    """
    if not approve:
        typer.echo(
            "Refusing prepare: pass --approve to set FR-006/FR-007 owner-approval "
            "gates explicitly. Owner review remains mandatory before external use.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        service = _package_service(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
        )
        manifest = service.prepare(
            opportunity_id,
            tailoring_options=TailoringOptions(
                owner_approved_to_tailor=True,
                override_material_benefit=override_material_benefit,
            ),
            cv_options=CvGenerationOptions(tailoring_plan_approved=True),
            cover_letter_plan_options=CoverLetterPlanOptions(
                owner_approved_to_plan=True,
                override_material_benefit=override_material_benefit,
            ),
            cover_letter_options=CoverLetterGenerationOptions(
                cover_letter_plan_approved=True
            ),
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except ApplicationPackageError as error:
        _exit_for_package(error)
    except (
        TailoringPlanGateError,
        CvGenerationGateError,
        CoverLetterPlanGateError,
    ) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(manifest))
        return

    typer.echo(
        f"Prepared application package for {manifest.opportunity_id} "
        f"(owner_review_required={manifest.owner_review_required})."
    )
    _print_package_summary(manifest)


@package_app.command("show")
def show_package(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full package manifest as YAML."),
    ] = False,
    no_verify: Annotated[
        bool,
        typer.Option(
            "--no-verify",
            help="Load the manifest without checking that draft files exist.",
        ),
    ] = False,
) -> None:
    """Show the current Application Package for an Opportunity."""
    try:
        service = _package_service(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
        )
        manifest = service.get(opportunity_id, verify=not no_verify)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except ApplicationPackageError as error:
        _exit_for_package(error)
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(manifest))
        return
    _print_package_summary(manifest)


@package_app.command("verify")
def verify_package(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    truth_reports_dir: TruthReportsDirOption = None,
) -> None:
    """Verify package integrity and fail-closed truth external-use readiness."""
    try:
        service = _package_service(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
        )
        manifest = service.get(opportunity_id, verify=True)
        truth_status = evaluate_package_truth(
            manifest=manifest,
            profile=service.load_profile(),
            store=JsonDirectoryTruthReportStore(truth_reports_dir or DEFAULT_TRUTH_REPORTS_ROOT),
            revalidate=False,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except ApplicationPackageError as error:
        _exit_for_package(error)
    except ProfileError as error:
        _exit_for_profile(error)
    except TruthValidationError as error:
        typer.echo(f"Truth validation error: {error}", err=True)
        raise typer.Exit(code=2) from error

    typer.echo(
        f"Application package for {manifest.opportunity_id} is intact "
        f"(owner_review_required={manifest.owner_review_required})."
    )
    if truth_status.external_use_allowed:
        typer.echo("Truth external-use: ALLOWED")
    else:
        typer.echo("Truth external-use: BLOCKED", err=True)
        for message in truth_status.messages:
            typer.echo(f"- {message}", err=True)
        raise typer.Exit(code=1)


@preparation_app.command("run")
def run_preparation(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    runs_dir: PreparationRunsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help=(
                "Explicitly set FR-006/FR-007 owner-approval gates "
                "(required to run preparation)."
            ),
        ),
    ] = False,
    override_material_benefit: Annotated[
        bool,
        typer.Option(
            "--override-material-benefit",
            help=(
                "Record an explicit FR-006/FR-007 material-benefit override "
                "when the strategy tier does not already justify documents."
            ),
        ),
    ] = False,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full PreparationRunState as YAML."),
    ] = False,
) -> None:
    """Run preparation orchestration for an apply Opportunity (FR-011).

    Thin adapter over ApplicationPreparationOrchestrator. Does not call
    ApplicationPackageService directly. Pass ``--approve`` to set FR-006/FR-007
    gates explicitly.
    """
    if not approve:
        typer.echo(
            "Refusing preparation run: pass --approve to set FR-006/FR-007 "
            "owner-approval gates explicitly. Owner review remains mandatory "
            "before external use.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        orchestrator = _preparation_orchestrator(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            runs_dir=runs_dir,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
        )
        state = orchestrator.run(
            opportunity_id,
            tailoring_options=TailoringOptions(
                owner_approved_to_tailor=True,
                override_material_benefit=override_material_benefit,
            ),
            cv_options=CvGenerationOptions(tailoring_plan_approved=True),
            cover_letter_plan_options=CoverLetterPlanOptions(
                owner_approved_to_plan=True,
                override_material_benefit=override_material_benefit,
            ),
            cover_letter_options=CoverLetterGenerationOptions(
                cover_letter_plan_approved=True
            ),
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except ApplicationPreparationError as error:
        _exit_for_preparation(error)
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(state))
    else:
        if state.status == "completed":
            typer.echo("Preparation orchestration completed.")
        else:
            typer.echo("Preparation orchestration failed.", err=True)
        _print_preparation_summary(state)

    if state.status != "completed":
        raise typer.Exit(code=1)


@preparation_app.command("show")
def show_preparation(
    run_id: Annotated[str, typer.Argument(help="Preparation run id (apr_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    runs_dir: PreparationRunsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full PreparationRunState as YAML."),
    ] = False,
) -> None:
    """Show a preparation orchestration run by id."""
    try:
        orchestrator = _preparation_orchestrator(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            runs_dir=runs_dir,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
        )
        state = orchestrator.get(run_id)
    except ApplicationPreparationError as error:
        _exit_for_preparation(error)
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(state))
        return
    _print_preparation_summary(state)


def _exit_for_submission(error: SubmissionError) -> Never:
    if isinstance(error, SubmissionValidationError):
        typer.echo("Submission validation failed:", err=True)
        for detail in error.errors:
            typer.echo(f"- {_format_location(detail.loc)}: {detail.msg}", err=True)
        raise typer.Exit(code=1)

    message = str(error)
    if isinstance(error, SubmissionGateError):
        if "owner_approved_submit" in message:
            typer.echo("Owner Approval Required", err=True)
        elif "package" in message.lower() or "draft" in message.lower():
            typer.echo("Package Verification Failed", err=True)
        else:
            typer.echo("Submission gate failed.", err=True)
        typer.echo(message, err=True)
        raise typer.Exit(code=1)

    if isinstance(error, SubmissionDuplicateError):
        if "outcome_unknown" in message:
            typer.echo("Outcome Unknown", err=True)
        else:
            typer.echo("Duplicate Submission Blocked", err=True)
        typer.echo(message, err=True)
        raise typer.Exit(code=1)

    if isinstance(error, SubmissionChannelError):
        typer.echo("Unknown channel.", err=True)
        typer.echo(message, err=True)
        raise typer.Exit(code=1)

    if isinstance(error, SubmissionAttemptNotFoundError):
        typer.echo(message, err=True)
        raise typer.Exit(code=1)

    if isinstance(error, SubmissionStorageError):
        typer.echo(message, err=True)
        raise typer.Exit(code=2)

    typer.echo(message, err=True)
    raise typer.Exit(code=2)


def _headline_for_attempt(attempt: SubmissionAttempt) -> str:
    mapping = {
        "submitted": "Submission Completed",
        "manual_completed": "Attempt Recorded",
        "manual_action_required": "Manual Action Required",
        "failed": "Submission Failed",
        "outcome_unknown": "Outcome Unknown",
        "cancelled": "Submission Cancelled",
        "in_progress": "Submission In Progress",
        "ready": "Submission Ready",
    }
    return mapping.get(attempt.status, f"Status: {attempt.status}")


def _print_attempt_summary(attempt: SubmissionAttempt) -> None:
    typer.echo(f"attempt_id: {attempt.attempt_id}")
    typer.echo(f"opportunity_id: {attempt.opportunity_id}")
    typer.echo(f"status: {attempt.status}")
    typer.echo(f"channel: {attempt.channel}")
    typer.echo(f"mode: {attempt.mode}")
    if attempt.destination:
        typer.echo(f"destination: {attempt.destination}")
    typer.echo(f"created_at: {attempt.created_at.isoformat()}")
    typer.echo(f"updated_at: {attempt.updated_at.isoformat()}")
    if attempt.completed_at is not None:
        typer.echo(f"completed_at: {attempt.completed_at.isoformat()}")
    typer.echo(
        f"owner_approved_submit: {attempt.evidence.owner_approved_submit}"
    )
    if attempt.evidence.result_code:
        typer.echo(f"result_code: {attempt.evidence.result_code}")
    if attempt.evidence.message:
        typer.echo(f"message: {attempt.evidence.message}")
    if attempt.evidence.failure_reason:
        typer.echo(f"failure_reason: {attempt.evidence.failure_reason}")


def _print_readiness(report: SubmissionReadinessReport) -> None:
    if report.ready:
        typer.echo("Submission Ready")
    else:
        typer.echo("Submission Not Ready", err=True)
    typer.echo(f"opportunity_id: {report.opportunity_id}")
    typer.echo(f"decision: {report.decision}")
    typer.echo(f"package_verified: {report.package_verified}")
    if report.package_prepared_at is not None:
        typer.echo(f"package_prepared_at: {report.package_prepared_at.isoformat()}")
    typer.echo(
        "available_channels: " + (", ".join(report.available_channels) or "(none)")
    )
    for message in report.messages:
        typer.echo(f"- {message}")


def _exit_for_attempt_status(attempt: SubmissionAttempt) -> None:
    if attempt.status in {"submitted", "manual_completed"}:
        return
    raise typer.Exit(code=1)


@submission_app.command("check")
def check_submission(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    attempts_dir: SubmissionAttemptsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    channel: Annotated[
        str | None,
        typer.Option(
            "--channel",
            help="Optional channel to validate (fake|manual_assisted).",
        ),
    ] = None,
    destination: Annotated[
        str | None,
        typer.Option("--destination", help="Optional destination URL or label."),
    ] = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the readiness report as YAML."),
    ] = False,
    truth_reports_dir: TruthReportsDirOption = None,
) -> None:
    """Validate submission readiness without creating an attempt."""
    try:
        orchestrator = _submission_orchestrator(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            attempts_dir=attempts_dir,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
            truth_reports_dir=truth_reports_dir,
        )
        report = orchestrator.check_readiness(
            opportunity_id,
            channel=channel,  # type: ignore[arg-type]
            destination=destination,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except SubmissionError as error:
        _exit_for_submission(error)
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(report))
    else:
        _print_readiness(report)

    if not report.ready:
        raise typer.Exit(code=1)


@submission_app.command("run")
def run_submission(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    attempts_dir: SubmissionAttemptsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    channel: Annotated[
        str,
        typer.Option(
            "--channel",
            help="Submission channel (fake|manual_assisted).",
        ),
    ] = "manual_assisted",
    approve_submit: Annotated[
        bool,
        typer.Option(
            "--approve-submit",
            help="Explicit owner approval to submit (required).",
        ),
    ] = False,
    destination: Annotated[
        str | None,
        typer.Option("--destination", help="Destination URL or label."),
    ] = None,
    force_new_attempt: Annotated[
        bool,
        typer.Option(
            "--force-new-attempt",
            help="Allow a new attempt after a prior success (requires --reason).",
        ),
    ] = False,
    reason: Annotated[
        str | None,
        typer.Option(
            "--reason",
            help="Auditable reason when using --force-new-attempt.",
        ),
    ] = None,
    acknowledge_prior_unknown: Annotated[
        bool,
        typer.Option(
            "--acknowledge-prior-unknown",
            help="Acknowledge a prior outcome_unknown before a new attempt.",
        ),
    ] = False,
    fake_outcome: Annotated[
        str | None,
        typer.Option(
            "--fake-outcome",
            help=(
                "Offline test aid: configure FakeSubmissionAdapter outcome "
                "(submitted|failed|manual_action_required|outcome_unknown)."
            ),
        ),
    ] = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full SubmissionAttempt as YAML."),
    ] = False,
    truth_reports_dir: TruthReportsDirOption = None,
) -> None:
    """Run assisted submission for an apply Opportunity (FR-012).

    Thin adapter over SubmissionOrchestrator. Pass ``--approve-submit``.
    """
    if not approve_submit:
        typer.echo("Owner Approval Required", err=True)
        typer.echo(
            "Refusing submission run: pass --approve-submit. Submission approval "
            "is distinct from apply / package / document gates.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        orchestrator = _submission_orchestrator(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            attempts_dir=attempts_dir,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
            fake_outcome=fake_outcome,
            truth_reports_dir=truth_reports_dir,
        )
        attempt = orchestrator.submit(
            opportunity_id,
            channel=channel,  # type: ignore[arg-type]
            owner_approved_submit=True,
            destination=destination,
            force_new_attempt=force_new_attempt,
            force_reason=reason,
            acknowledge_prior_outcome_unknown=acknowledge_prior_unknown,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except SubmissionError as error:
        _exit_for_submission(error)
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(attempt))
    else:
        typer.echo(_headline_for_attempt(attempt))
        _print_attempt_summary(attempt)

    _exit_for_attempt_status(attempt)


@submission_app.command("record-manual")
def record_manual_submission(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    attempts_dir: SubmissionAttemptsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    approve_submit: Annotated[
        bool,
        typer.Option(
            "--approve-submit",
            help="Explicit owner confirmation to record manual completion (required).",
        ),
    ] = False,
    attestation: Annotated[
        str | None,
        typer.Option(
            "--attestation",
            help="Owner attestation that the application was submitted externally.",
        ),
    ] = None,
    confirmation_reference: Annotated[
        str | None,
        typer.Option(
            "--confirmation-reference",
            help="Optional confirmation id or receipt reference.",
        ),
    ] = None,
    channel: Annotated[
        str,
        typer.Option("--channel", help="Channel label for the audit record."),
    ] = "manual_assisted",
    destination: Annotated[
        str | None,
        typer.Option("--destination", help="Destination URL or platform label."),
    ] = None,
    force_new_attempt: Annotated[
        bool,
        typer.Option("--force-new-attempt", help="Allow after a prior success."),
    ] = False,
    reason: Annotated[
        str | None,
        typer.Option("--reason", help="Auditable reason for --force-new-attempt."),
    ] = None,
    acknowledge_prior_unknown: Annotated[
        bool,
        typer.Option(
            "--acknowledge-prior-unknown",
            help="Acknowledge a prior outcome_unknown before recording.",
        ),
    ] = False,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full SubmissionAttempt as YAML."),
    ] = False,
    truth_reports_dir: TruthReportsDirOption = None,
) -> None:
    """Record that the owner completed submission outside the system."""
    if not approve_submit:
        typer.echo("Owner Approval Required", err=True)
        typer.echo(
            "Refusing record-manual: pass --approve-submit.",
            err=True,
        )
        raise typer.Exit(code=1)
    if attestation is None or not attestation.strip():
        typer.echo("Owner Approval Required", err=True)
        typer.echo(
            "Refusing record-manual: pass --attestation with a non-empty statement.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        orchestrator = _submission_orchestrator(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            attempts_dir=attempts_dir,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
            truth_reports_dir=truth_reports_dir,
        )
        attempt = orchestrator.record_manual_completion(
            opportunity_id,
            owner_approved_submit=True,
            attestation=attestation,
            channel=channel,  # type: ignore[arg-type]
            destination=destination,
            confirmation_reference=confirmation_reference,
            force_new_attempt=force_new_attempt,
            force_reason=reason,
            acknowledge_prior_outcome_unknown=acknowledge_prior_unknown,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except SubmissionError as error:
        _exit_for_submission(error)
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(attempt))
    else:
        typer.echo(_headline_for_attempt(attempt))
        _print_attempt_summary(attempt)

    _exit_for_attempt_status(attempt)


@submission_app.command("show")
def show_submission(
    attempt_id: Annotated[str, typer.Argument(help="Attempt id (sub_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    attempts_dir: SubmissionAttemptsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full SubmissionAttempt as YAML."),
    ] = False,
    truth_reports_dir: TruthReportsDirOption = None,
) -> None:
    """Show a submission attempt by id (read-only)."""
    try:
        orchestrator = _submission_orchestrator(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            attempts_dir=attempts_dir,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
            truth_reports_dir=truth_reports_dir,
        )
        attempt = orchestrator.get_attempt(attempt_id)
    except SubmissionError as error:
        _exit_for_submission(error)
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(attempt))
        return
    typer.echo(_headline_for_attempt(attempt))
    _print_attempt_summary(attempt)


@submission_app.command("list")
def list_submissions(
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    attempts_dir: SubmissionAttemptsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    opportunity_id: Annotated[
        str | None,
        typer.Option(
            "--opportunity-id",
            help="Optional filter by opportunity id.",
        ),
    ] = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit attempts as YAML."),
    ] = False,
    truth_reports_dir: TruthReportsDirOption = None,
) -> None:
    """List submission attempts (read-only)."""
    try:
        orchestrator = _submission_orchestrator(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            attempts_dir=attempts_dir,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
            truth_reports_dir=truth_reports_dir,
        )
        attempts = orchestrator.list_attempts(opportunity_id=opportunity_id)
    except SubmissionError as error:
        _exit_for_submission(error)
    except ProfileError as error:
        _exit_for_profile(error)

    if yaml_output:
        typer.echo(_render(attempts))
        return
    if not attempts:
        typer.echo("No submission attempts found.")
        return
    for attempt in attempts:
        typer.echo(
            f"{attempt.attempt_id}  {attempt.status}  "
            f"{attempt.channel}  {attempt.opportunity_id}"
        )


# --- FR-013 pipeline owner workflow (thin CLI) -------------------------------


def _exit_for_pipeline(error: PipelineError) -> Never:
    message = str(error)
    if isinstance(error, PipelineValidationError):
        typer.echo("Pipeline validation failed:", err=True)
        for detail in error.errors:
            typer.echo(f"- {_format_location(detail.loc)}: {detail.msg}", err=True)
        raise typer.Exit(code=1)
    if isinstance(error, (PipelineTransitionError, PipelineConsistencyError)):
        typer.echo(message, err=True)
        raise typer.Exit(code=1)
    if isinstance(error, PipelinePartialWriteError):
        typer.echo("Pipeline write incomplete - history saved, status not updated.", err=True)
        typer.echo(message, err=True)
        typer.echo(
            f"Retry with: cic pipeline repair {error.opportunity_id}",
            err=True,
        )
        raise typer.Exit(code=1)
    if isinstance(error, PipelineDivergenceError):
        typer.echo("Pipeline history and current status disagree.", err=True)
        typer.echo(message, err=True)
        raise typer.Exit(code=1)
    if isinstance(error, PipelineStorageError):
        typer.echo(message, err=True)
        raise typer.Exit(code=2)
    typer.echo(message, err=True)
    raise typer.Exit(code=2)


def _print_pipeline_result(result: PipelineApplyResult, *, headline: str) -> None:
    opportunity = result.opportunity
    typer.echo(headline)
    typer.echo(f"opportunity_id: {opportunity.opportunity_id}")
    typer.echo(f"status: {opportunity.status}")
    if opportunity.outcome is not None:
        typer.echo(f"outcome: {opportunity.outcome.outcome}")
        if opportunity.outcome.interview_stage not in {None, "none"}:
            typer.echo(f"interview_stage: {opportunity.outcome.interview_stage}")
        if opportunity.outcome.follow_up_date is not None:
            typer.echo(f"follow_up_date: {opportunity.outcome.follow_up_date.isoformat()}")
    if result.event.evidence.note:
        typer.echo(f"note: {result.event.evidence.note}")
    if result.event.evidence.submission_attempt_id:
        typer.echo(
            f"submission_attempt_id: {result.event.evidence.submission_attempt_id}"
        )


def _print_opportunity_pipeline(opportunity: object) -> None:
    from career_intelligence.opportunities import Opportunity

    assert isinstance(opportunity, Opportunity)
    title = opportunity.identity.title or "(untitled)"
    company = opportunity.identity.company or "(unknown company)"
    typer.echo(f"{opportunity.opportunity_id}")
    typer.echo(f"  {company} - {title}")
    typer.echo(f"  status: {opportunity.status}")
    if opportunity.decision is not None:
        typer.echo(f"  decision: {opportunity.decision.decision}")
    if opportunity.outcome is not None:
        typer.echo(f"  outcome: {opportunity.outcome.outcome}")
        if opportunity.outcome.interview_stage not in {None, "none"}:
            typer.echo(f"  interview_stage: {opportunity.outcome.interview_stage}")
        if opportunity.outcome.follow_up_date is not None:
            typer.echo(
                f"  follow_up_date: {opportunity.outcome.follow_up_date.isoformat()}"
            )
        if opportunity.outcome.notes:
            typer.echo(f"  notes: {opportunity.outcome.notes}")


def _history_line(event: PipelineEvent, *, verbose: bool) -> list[str]:
    when = event.occurred_at.isoformat()
    lines: list[str] = []
    if event.kind == "status_transition":
        lines.append(f"{when}  Status -> {event.to_status}")
    elif event.kind == "correction":
        lines.append(
            f"{when}  Correction: {event.from_status} -> {event.to_status}"
        )
    elif event.kind == "interview_stage_change":
        lines.append(f"{when}  Interview stage -> {event.interview_stage}")
    elif event.kind == "outcome_change":
        lines.append(f"{when}  Outcome -> {event.outcome}")
    elif event.kind == "follow_up_set":
        if event.clear_follow_up_date:
            lines.append(f"{when}  Follow-up cleared")
        else:
            lines.append(f"{when}  Follow-up -> {event.follow_up_date}")
    elif event.kind == "note":
        lines.append(f"{when}  Note")
    elif event.kind == "evidence_added":
        lines.append(f"{when}  Evidence")
    else:
        lines.append(f"{when}  {event.kind}")

    detail_parts: list[str] = []
    if event.interview_stage and event.kind == "status_transition":
        detail_parts.append(f"interview_stage={event.interview_stage}")
    if event.outcome and event.kind in {"status_transition", "correction"}:
        detail_parts.append(f"outcome={event.outcome}")
    if event.evidence.note:
        detail_parts.append(event.evidence.note)
    if event.evidence.channel:
        detail_parts.append(f"channel={event.evidence.channel}")
    if event.evidence.submission_attempt_id:
        detail_parts.append(f"attempt={event.evidence.submission_attempt_id}")
    if event.evidence.rejection_reason:
        detail_parts.append(f"reason={event.evidence.rejection_reason}")
    if event.evidence.offer_detail:
        detail_parts.append(f"offer={event.evidence.offer_detail}")
    if detail_parts:
        lines.append("            " + " | ".join(detail_parts))
    if verbose:
        lines.append(f"            id={event.event_id} kind={event.kind}")
    return lines


def _parse_optional_date(value: str | None):
    from datetime import date

    if value is None:
        return None
    return date.fromisoformat(value)


def _parse_optional_datetime(value: str | None):
    from datetime import datetime

    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        from datetime import UTC

        return parsed.replace(tzinfo=UTC)
    return parsed


def _submit_evidence(
    *,
    opportunity_id: str,
    note: str | None,
    channel: str | None,
    attempt_id: str | None,
    package_prepared_at: str | None,
    submitted_at: str | None,
) -> PipelineEvidence:
    package = None
    prepared = _parse_optional_datetime(package_prepared_at)
    if prepared is not None:
        package = PackageEvidenceRef(
            opportunity_id=opportunity_id,
            prepared_at=prepared,
        )
    return PipelineEvidence(
        note=note or "Application submitted",
        channel=channel,
        submission_attempt_id=attempt_id,  # type: ignore[arg-type]
        package=package,
        submitted_at=_parse_optional_datetime(submitted_at),
    )


@pipeline_app.command("list")
def pipeline_list(
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    status: Annotated[
        str | None,
        typer.Option("--status", help="Filter by exact pipeline status."),
    ] = None,
    all_records: Annotated[
        bool,
        typer.Option(
            "--all",
            help="List all opportunities (not only active pipeline).",
        ),
    ] = False,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit opportunities as YAML."),
    ] = False,
) -> None:
    """List applications in the active pipeline (default) or all opportunities."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        items = tracking.list_pipeline(
            active_only=not all_records,
            status=status,  # type: ignore[arg-type]
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)

    if yaml_output:
        typer.echo(_render(items))
        return
    if not items:
        typer.echo("No applications in the pipeline.")
        return
    for item in items:
        company = item.identity.company or "?"
        title = item.identity.title or "?"
        stage = ""
        if item.outcome and item.outcome.interview_stage not in {None, "none"}:
            stage = f"  interview={item.outcome.interview_stage}"
        typer.echo(
            f"{item.opportunity_id}  {item.status}  {company} - {title}{stage}"
        )


@pipeline_app.command("show")
def pipeline_show(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the opportunity as YAML."),
    ] = False,
) -> None:
    """Show current pipeline status for one opportunity."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        opportunity = tracking.get_opportunity(opportunity_id)
        report = tracking.detect_divergence(opportunity_id)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)

    if yaml_output:
        typer.echo(_render(opportunity))
        return
    typer.echo("Current Pipeline")
    _print_opportunity_pipeline(opportunity)
    if report.divergent:
        typer.echo("  consistency: divergent (run cic pipeline repair)")
    else:
        typer.echo("  consistency: ok")


@pipeline_app.command("history")
def pipeline_history(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Include internal history ids."),
    ] = False,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit raw history records as YAML."),
    ] = False,
) -> None:
    """Show chronological application history (append-only)."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        events = tracking.list_events(opportunity_id)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)

    if yaml_output:
        typer.echo(_render(events))
        return
    if not events:
        typer.echo("No pipeline history yet.")
        return
    typer.echo(f"History for {opportunity_id}")
    for event in events:
        for line in _history_line(event, verbose=verbose):
            typer.echo(line)


@pipeline_app.command("submit")
def pipeline_submit(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
    channel: Annotated[str | None, typer.Option("--channel")] = None,
    attempt_id: Annotated[
        str | None,
        typer.Option(
            "--attempt-id",
            help="Optional FR-012 submission attempt id (evidence only).",
        ),
    ] = None,
    package_prepared_at: Annotated[
        str | None,
        typer.Option(
            "--package-prepared-at",
            help="Optional package prepared_at ISO timestamp (evidence).",
        ),
    ] = None,
    submitted_at: Annotated[
        str | None,
        typer.Option("--submitted-at", help="Optional submission time (ISO)."),
    ] = None,
) -> None:
    """Record that the owner submitted the application (explicit; never automatic)."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        evidence = _submit_evidence(
            opportunity_id=opportunity_id,
            note=note,
            channel=channel,
            attempt_id=attempt_id,
            package_prepared_at=package_prepared_at,
            submitted_at=submitted_at,
        )
        # Ensure substantive evidence even when only defaults.
        if evidence.submitted_at is None and note is None and channel is None and (
            attempt_id is None and package_prepared_at is None
        ):
            from datetime import UTC, datetime

            evidence = evidence.model_copy(
                update={"submitted_at": datetime.now(UTC)}
            )
        result = tracking.record_submitted(opportunity_id, evidence=evidence)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Application Submitted")


@pipeline_app.command("preparing")
def pipeline_preparing(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
) -> None:
    """Mark the opportunity as preparing an application package."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.advance_status(
            opportunity_id,
            "preparing",
            evidence=PipelineEvidence(note=note or "Preparing application package"),
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Preparing Application")


@pipeline_app.command("acknowledge")
def pipeline_acknowledge(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
) -> None:
    """Record acknowledgement received (does not change pipeline status)."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.record_acknowledgement(opportunity_id, note=note)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Acknowledgement Recorded")


@pipeline_app.command("interview")
def pipeline_interview(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    stage: Annotated[
        str,
        typer.Option(
            "--stage",
            help="Interview stage: recruiter|hiring_manager|technical|other|unknown",
        ),
    ] = "recruiter",
    note: Annotated[str | None, typer.Option("--note")] = None,
) -> None:
    """Record interviewing progress (moves to interviewing or updates stage)."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.record_interview(
            opportunity_id,
            stage,  # type: ignore[arg-type]
            note=note,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Interview Updated")


@pipeline_app.command("reject")
def pipeline_reject(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
) -> None:
    """Record rejection."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.advance_status(
            opportunity_id,
            "rejected",
            evidence=PipelineEvidence(
                note=note or "Rejected",
                rejection_reason=reason,
            ),
            outcome="rejected",
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Application Rejected")


@pipeline_app.command("offer")
def pipeline_offer(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
    detail: Annotated[str | None, typer.Option("--detail")] = None,
) -> None:
    """Record that an offer was received."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.advance_status(
            opportunity_id,
            "offer",
            evidence=PipelineEvidence(
                note=note or "Offer received",
                offer_detail=detail,
            ),
            outcome="offer",
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Offer Recorded")


@pipeline_app.command("accept")
def pipeline_accept(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
) -> None:
    """Record that an offer was accepted."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.advance_status(
            opportunity_id,
            "accepted",
            evidence=PipelineEvidence(note=note or "Offer accepted"),
            outcome="accepted",
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Offer Accepted")


@pipeline_app.command("withdraw")
def pipeline_withdraw(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
) -> None:
    """Withdraw the application."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.advance_status(
            opportunity_id,
            "withdrawn",
            evidence=PipelineEvidence(note=note or "Withdrawn by owner"),
            outcome="withdrawn",
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Application Withdrawn")


@pipeline_app.command("follow-up")
def pipeline_follow_up(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    date_value: Annotated[
        str | None,
        typer.Option("--date", help="Follow-up date (YYYY-MM-DD)."),
    ] = None,
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Clear the follow-up date."),
    ] = False,
    note: Annotated[str | None, typer.Option("--note")] = None,
) -> None:
    """Record or clear a follow-up reminder (tracking only — no notifications)."""
    if not clear and date_value is None:
        typer.echo("Provide --date YYYY-MM-DD or --clear.", err=True)
        raise typer.Exit(code=1)
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.set_follow_up(
            opportunity_id,
            _parse_optional_date(date_value),
            clear=clear,
            evidence=PipelineEvidence(note=note) if note else PipelineEvidence(),
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    _print_pipeline_result(result, headline="Follow-up Updated")


@pipeline_app.command("note")
def pipeline_note(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    text: Annotated[str, typer.Argument(help="Owner note text.")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
) -> None:
    """Add an append-only owner note (does not rewrite history)."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.add_note(opportunity_id, text)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Note Added")


@pipeline_app.command("evidence")
def pipeline_evidence(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    note: Annotated[str | None, typer.Option("--note")] = None,
    channel: Annotated[str | None, typer.Option("--channel")] = None,
    attempt_id: Annotated[
        str | None,
        typer.Option("--attempt-id", help="Optional FR-012 attempt id (evidence only)."),
    ] = None,
) -> None:
    """Attach evidence (channel, attempt citation, note) without changing status."""
    evidence = PipelineEvidence(
        note=note,
        channel=channel,
        submission_attempt_id=attempt_id,  # type: ignore[arg-type]
    )
    if not evidence.has_substantive_fields():
        typer.echo("Provide at least one of --note, --channel, --attempt-id.", err=True)
        raise typer.Exit(code=1)
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.add_evidence(opportunity_id, evidence)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Evidence Attached")


@pipeline_app.command("correct")
def pipeline_correct(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    to_status: Annotated[
        str,
        typer.Option("--to", help="Corrected pipeline status."),
    ],
    note: Annotated[
        str,
        typer.Option("--note", help="Required explanation for the correction."),
    ],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    supersedes: Annotated[
        str | None,
        typer.Option("--supersedes", help="Optional prior history id being corrected."),
    ] = None,
    outcome: Annotated[str | None, typer.Option("--outcome")] = None,
) -> None:
    """Correct a previous pipeline status (append-only; never deletes history)."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        result = tracking.correct_status(
            opportunity_id,
            to_status,  # type: ignore[arg-type]
            note=note,
            supersedes_event_id=supersedes,
            outcome=outcome,  # type: ignore[arg-type]
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    _print_pipeline_result(result, headline="Pipeline Corrected")


@pipeline_app.command("check")
def pipeline_check(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
) -> None:
    """Check that current status agrees with append-only history."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        report = tracking.detect_divergence(opportunity_id)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)

    if report.divergent:
        typer.echo("Pipeline Divergent", err=True)
        for reason in report.reasons:
            typer.echo(f"- {reason}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Pipeline Consistent")
    typer.echo(f"opportunity_id: {opportunity_id}")
    typer.echo(f"status: {report.actual_status}")


@pipeline_app.command("repair")
def pipeline_repair(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
) -> None:
    """Restore current status from append-only history after a partial write."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        opportunity = tracking.reconcile(opportunity_id)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    typer.echo("Pipeline Repaired")
    _print_opportunity_pipeline(opportunity)


def _print_pipeline_report(report: PipelineSummaryReport) -> None:
    typer.echo("Pipeline Report")
    typer.echo(f"as_of: {report.as_of.isoformat()}")
    typer.echo(f"total_opportunities: {report.total_opportunities}")
    typer.echo(f"active: {report.active_count}")
    typer.echo(f"submitted_cohort: {report.submitted_count}")
    typer.echo(f"awaiting_response: {report.awaiting_response_count}")
    typer.echo(f"interviewing: {report.interviewing_count}")
    typer.echo(f"offers: {report.offer_count}")
    typer.echo(f"accepted: {report.accepted_count}")
    typer.echo(f"rejected: {report.rejected_count}")
    typer.echo(f"withdrawn: {report.withdrawn_count}")
    typer.echo(f"follow_ups_due: {report.follow_ups_due_count}")
    typer.echo(f"follow_ups_overdue: {report.follow_ups_overdue_count}")
    typer.echo(f"history_entries: {report.historical_event_count}")
    if report.interview_rate is not None:
        typer.echo(f"interview_rate: {report.interview_rate:.2%}")
    if report.offer_rate is not None:
        typer.echo(f"offer_rate: {report.offer_rate:.2%}")
    if report.acceptance_rate is not None:
        typer.echo(f"acceptance_rate: {report.acceptance_rate:.2%}")
    typer.echo("by_status:")
    for status, count in report.by_status.items():
        typer.echo(f"  {status}: {count}")
    if report.by_outcome:
        typer.echo("by_outcome:")
        for outcome, count in report.by_outcome.items():
            typer.echo(f"  {outcome}: {count}")
    if report.ageing:
        typer.echo("ageing (active):")
        for item in report.ageing[:10]:
            days = (
                f"{item.days_in_status:.1f}d"
                if item.days_in_status is not None
                else "n/a"
            )
            company = item.company or "?"
            typer.echo(
                f"  {item.opportunity_id}  {item.status}  {days}  {company}"
            )


@pipeline_app.command("report")
def pipeline_report(
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full report as YAML."),
    ] = False,
) -> None:
    """Show derived pipeline counts, rates, ageing, and follow-ups due."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        report = tracking.summary_report()
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)

    if yaml_output:
        from dataclasses import asdict

        typer.echo(
            yaml.safe_dump(asdict(report), sort_keys=False, allow_unicode=True).rstrip()
        )
        return
    _print_pipeline_report(report)


@pipeline_app.command("due")
def pipeline_due(
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    on_date: Annotated[
        str | None,
        typer.Option("--on", help="Reference date YYYY-MM-DD (default: today UTC)."),
    ] = None,
) -> None:
    """List follow-up reminders due on or before the reference date."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        reference = _parse_optional_date(on_date)
        items = tracking.follow_ups_due(reference_date=reference)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if not items:
        typer.echo("No follow-ups due.")
        return
    for item in items:
        company = item.company or "?"
        title = item.title or "?"
        label = "overdue" if item.days_until_due < 0 else "due"
        typer.echo(
            f"{item.follow_up_date.isoformat()}  {label}  "
            f"{item.opportunity_id}  {item.status}  {company} - {title}"
        )


@pipeline_app.command("export")
def pipeline_export(
    dir: OpportunitiesDirOption = None,
    events_dir: PipelineEventsDirOption = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            help=f"CSV path (default: {DEFAULT_PIPELINE_EXPORT_PATH}).",
        ),
    ] = None,
    active_only: Annotated[
        bool,
        typer.Option(
            "--active-only",
            help="Export only active pipeline rows (preparing/submitted/interviewing/offer).",
        ),
    ] = False,
) -> None:
    """Export pipeline rows to CSV (owner-controlled; does not migrate legacy trackers)."""
    try:
        tracking = _pipeline_tracking_service(
            opportunities_dir=dir,
            events_dir=events_dir,
        )
        path = tracking.export_csv(output, active_only=active_only)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except PipelineError as error:
        _exit_for_pipeline(error)
    except OSError as error:
        typer.echo(f"Could not write export: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(f"Exported pipeline CSV to {path}")


def _print_truth_report(report: TruthReport) -> None:
    typer.echo(f"report_id: {report.report_id}")
    typer.echo(f"outcome: {report.outcome}")
    typer.echo(f"coverage: {report.coverage_status}")
    typer.echo(f"gate: {report.gate}")
    typer.echo(f"artefact: {report.artefact.kind}")
    if report.artefact.path:
        typer.echo(f"path: {report.artefact.path}")
    typer.echo(f"content_hash: {report.artefact.content_fingerprint}")
    typer.echo(f"validator_version: {report.validator_version}")
    typer.echo(f"summary: {report.summary}")
    blocking = [f for f in report.findings if f.severity == "blocking"]
    review = [f for f in report.findings if f.severity == "review_required"]
    supported = [
        f
        for f in report.findings
        if f.claim.claim_class == "A" and f.evidence_status == "supported"
    ]
    typer.echo(f"blocking: {len(blocking)}")
    for finding in blocking:
        typer.echo(
            f"  - [{finding.claim.object_key}] class={finding.claim.claim_class} "
            f"strength={finding.claim.strength} detection={finding.detection_certainty} "
            f"evidence={finding.evidence_status}"
        )
        typer.echo(f"    claim: {finding.claim.surface_text}")
        typer.echo(f"    action: {finding.recommended_action}")
    typer.echo(f"review_required: {len(review)}")
    for finding in review:
        typer.echo(
            f"  - [{finding.claim.object_key}] {finding.claim.surface_text} "
            f"({finding.recommended_action})"
        )
    if supported:
        typer.echo(f"supported: {len(supported)}")
        for finding in supported:
            typer.echo(
                f"  - [{finding.claim.object_key}] {finding.claim.surface_text}"
            )


@truth_app.command("validate")
def truth_validate(
    markdown_path: Annotated[Path, typer.Argument(help="Markdown file to validate.")],
    profile: ProfilePathOption = None,
    opportunity_id: Annotated[
        str | None,
        typer.Option("--opportunity-id", help="Opportunity id for report persistence."),
    ] = None,
    kind: Annotated[
        str | None,
        typer.Option(
            "--kind",
            help="Artefact kind: cv_markdown|cover_letter_markdown (auto-detected if omitted).",
        ),
    ] = None,
    persist: Annotated[
        bool,
        typer.Option("--persist/--no-persist", help="Persist TruthReport (default: on when opportunity-id set)."),
    ] = True,
    truth_reports_dir: TruthReportsDirOption = None,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit full TruthReport as YAML."),
    ] = False,
) -> None:
    """Validate recruiter-facing Markdown (authoritative surface)."""
    try:
        profile_service = CareerProfileService.from_path(profile) if profile else CareerProfileService()
        career_profile = profile_service.load()
        service = TruthValidationService()
        report = service.validate_markdown_path(
            markdown_path,
            profile=career_profile,
            artefact_kind=kind,  # type: ignore[arg-type]
            opportunity_id=opportunity_id,
        )
        saved: Path | None = None
        if persist and opportunity_id:
            store = JsonDirectoryTruthReportStore(
                truth_reports_dir or DEFAULT_TRUTH_REPORTS_ROOT
            )
            saved = store.save(report, as_current=True)
    except (ProfileError, TruthValidationError, OSError) as error:
        typer.echo(f"Truth validation failed: {error}", err=True)
        raise typer.Exit(code=2) from error

    if yaml_output:
        typer.echo(_render(report))
    else:
        _print_truth_report(report)
        if saved is not None:
            typer.echo(f"persisted: {saved}")
    if report.outcome in {"fail", "review_required"}:
        raise typer.Exit(code=1)


@truth_app.command("show")
def truth_show(
    report_path: Annotated[Path, typer.Argument(help="Path to a TruthReport JSON file.")],
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit full TruthReport as YAML."),
    ] = False,
) -> None:
    """Show a persisted TruthReport."""
    try:
        report = JsonDirectoryTruthReportStore().load_path(report_path)
    except (TruthReportNotFoundError, TruthValidationError, OSError) as error:
        typer.echo(f"Could not load report: {error}", err=True)
        raise typer.Exit(code=2) from error
    if yaml_output:
        typer.echo(_render(report))
    else:
        _print_truth_report(report)


@truth_app.command("validate-package")
def truth_validate_package(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    truth_reports_dir: TruthReportsDirOption = None,
    check_only: Annotated[
        bool,
        typer.Option(
            "--check-only",
            help="Evaluate stored reports for freshness without re-detecting claims.",
        ),
    ] = False,
) -> None:
    """Validate CV + cover-letter Markdown for a package and update current reports."""
    try:
        packages = _package_service(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            profile_path=profile,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
        )
        manifest = packages.get(opportunity_id, verify=True)
        status = evaluate_package_truth(
            manifest=manifest,
            profile=packages.load_profile(),
            store=JsonDirectoryTruthReportStore(
                truth_reports_dir or DEFAULT_TRUTH_REPORTS_ROOT
            ),
            revalidate=not check_only,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except ApplicationPackageError as error:
        _exit_for_package(error)
    except ProfileError as error:
        _exit_for_profile(error)
    except TruthValidationError as error:
        typer.echo(f"Truth validation failed: {error}", err=True)
        raise typer.Exit(code=2) from error

    typer.echo(f"opportunity_id: {status.opportunity_id}")
    typer.echo(
        "external_use: "
        + ("ALLOWED" if status.external_use_allowed else "BLOCKED")
    )
    for doc in status.documents:
        typer.echo(
            f"- {doc.artefact_kind}: outcome={doc.outcome} fresh={doc.fresh} "
            f"allowed={doc.external_use_allowed} report={doc.report_id}"
        )
        for message in doc.messages:
            typer.echo(f"    {message}")
    if not status.external_use_allowed:
        raise typer.Exit(code=1)


def _exit_for_agent(error: Exception) -> Never:
    if isinstance(error, AgentRunNotFoundError):
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    if isinstance(error, AgentStorageError):
        typer.echo(f"Agent storage error: {error}", err=True)
        raise typer.Exit(code=2) from error
    if isinstance(error, AgentRuntimeError):
        typer.echo(f"Agent runtime error: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Agent error: {error}", err=True)
    raise typer.Exit(code=1) from error


def _agent_store(agent_runs_dir: Path | None) -> JsonDirectoryAgentRunStore:
    return JsonDirectoryAgentRunStore(agent_runs_dir or DEFAULT_AGENT_RUNS_ROOT)


def _print_agent_run(run, *, verbose: bool = False, yaml_output: bool = False) -> None:
    if yaml_output:
        typer.echo(_render(run))
    else:
        typer.echo(format_agent_run_report(run, verbose=verbose), nl=False)


def _exit_for_agent_status(run) -> None:
    if run.status == "failed":
        raise typer.Exit(code=1)
    # awaiting_owner / completed are successful agent outcomes for the owner.
    if run.status not in {"awaiting_owner", "completed", "running", "cancelled"}:
        raise typer.Exit(code=1)


@agent_app.command("run")
def agent_run(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    runs_dir: PreparationRunsDirOption = None,
    agent_runs_dir: AgentRunsDirOption = None,
    truth_reports_dir: TruthReportsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help=(
                "Explicitly set FR-006/FR-007 owner-approval gates required for "
                "preparation (never silently defaulted)."
            ),
        ),
    ] = False,
    llm: Annotated[
        bool,
        typer.Option(
            "--llm",
            help=(
                "Use OpenAI structured proposer instead of the deterministic "
                "preference table. Proposer still receives readiness flags only."
            ),
        ),
    ] = False,
    override_material_benefit: Annotated[
        bool,
        typer.Option(
            "--override-material-benefit",
            help="Pass explicit FR-006/FR-007 material-benefit override into preparation.",
        ),
    ] = False,
    max_steps: Annotated[
        int,
        typer.Option("--max-steps", help="Maximum agent steps for this run."),
    ] = DEFAULT_MAX_STEPS,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Include proposal rationales in the report."),
    ] = False,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full AgentRun as YAML."),
    ] = False,
) -> None:
    """Run BOPA for one Opportunity (prepare_for_owner_review).

    Thin CLI over AgentRuntime. Does not invoke FR-008, submit, or advance pipeline.
    """
    if not approve:
        typer.echo(
            "Refusing agent run: pass --approve to set FR-006/FR-007 "
            "owner-approval gates explicitly when preparation may run. "
            "Owner review remains mandatory before external use.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        runtime = build_agent_runtime(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            preparation_runs_dir=runs_dir,
            agent_runs_dir=agent_runs_dir,
            truth_reports_dir=truth_reports_dir,
            profile_path=profile,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
            use_llm_proposer=llm,
            max_steps=max_steps,
            override_material_benefit=override_material_benefit,
        )
        run = runtime.start(
            AgentGoal(opportunity_id=opportunity_id),  # type: ignore[arg-type]
            owner_approvals_present=True,
            provider_available=True,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except ProfileError as error:
        _exit_for_profile(error)
    except AgentRuntimeError as error:
        _exit_for_agent(error)
    except Exception as error:  # noqa: BLE001 — surface unexpected adapter failures
        _exit_for_agent(error)

    _print_agent_run(run, verbose=verbose, yaml_output=yaml_output)
    _exit_for_agent_status(run)


@agent_app.command("resume")
def agent_resume(
    agent_run_id: Annotated[str, typer.Argument(help="Agent run id (agr_<ULID>).")],
    dir: OpportunitiesDirOption = None,
    packages_dir: PackagesDirOption = None,
    runs_dir: PreparationRunsDirOption = None,
    agent_runs_dir: AgentRunsDirOption = None,
    truth_reports_dir: TruthReportsDirOption = None,
    profile: ProfilePathOption = None,
    cv_dir: Annotated[
        Path | None,
        typer.Option("--cv-dir", help="Override CV draft output directory."),
    ] = None,
    cover_letter_dir: Annotated[
        Path | None,
        typer.Option(
            "--cover-letter-dir",
            help="Override cover-letter draft output directory.",
        ),
    ] = None,
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help="Confirm FR-006/FR-007 approval gates remain set for this resume.",
        ),
    ] = False,
    llm: Annotated[
        bool,
        typer.Option("--llm", help="Use OpenAI structured proposer for this resume."),
    ] = False,
    override_material_benefit: Annotated[
        bool,
        typer.Option(
            "--override-material-benefit",
            help="Pass explicit FR-006/FR-007 material-benefit override into preparation.",
        ),
    ] = False,
    max_steps: Annotated[
        int,
        typer.Option("--max-steps", help="Maximum agent steps for this resume."),
    ] = DEFAULT_MAX_STEPS,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Include proposal rationales in the report."),
    ] = False,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full AgentRun as YAML."),
    ] = False,
) -> None:
    """Resume a paused AgentRun from checkpoint after re-inspecting SoT."""
    if not approve:
        typer.echo(
            "Refusing agent resume: pass --approve to confirm FR-006/FR-007 "
            "owner-approval gates explicitly.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        runtime = build_agent_runtime(
            opportunities_dir=dir,
            packages_dir=packages_dir,
            preparation_runs_dir=runs_dir,
            agent_runs_dir=agent_runs_dir,
            truth_reports_dir=truth_reports_dir,
            profile_path=profile,
            cv_output_dir=cv_dir,
            cover_letter_output_dir=cover_letter_dir,
            use_llm_proposer=llm,
            max_steps=max_steps,
            override_material_benefit=override_material_benefit,
        )
        run = runtime.resume(
            agent_run_id,
            owner_approvals_present=True,
            provider_available=True,
        )
    except OpportunityError as error:
        _exit_for_opportunity(error)
    except ProfileError as error:
        _exit_for_profile(error)
    except AgentRuntimeError as error:
        _exit_for_agent(error)
    except Exception as error:  # noqa: BLE001
        _exit_for_agent(error)

    _print_agent_run(run, verbose=verbose, yaml_output=yaml_output)
    _exit_for_agent_status(run)


@agent_app.command("show")
def agent_show(
    agent_run_id: Annotated[str, typer.Argument(help="Agent run id (agr_<ULID>).")],
    agent_runs_dir: AgentRunsDirOption = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Include proposal rationales."),
    ] = False,
    yaml_output: Annotated[
        bool,
        typer.Option("--yaml", help="Emit the full AgentRun as YAML."),
    ] = False,
) -> None:
    """Show an AgentRun with readiness, steps, stop reason, and owner action."""
    try:
        run = _agent_store(agent_runs_dir).load(agent_run_id)
    except (AgentRunNotFoundError, AgentStorageError) as error:
        _exit_for_agent(error)
    _print_agent_run(run, verbose=verbose, yaml_output=yaml_output)


@agent_app.command("history")
def agent_history(
    agent_run_id: Annotated[str, typer.Argument(help="Agent run id (agr_<ULID>).")],
    agent_runs_dir: AgentRunsDirOption = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Include full event messages and refs."),
    ] = False,
) -> None:
    """Show append-only audit events for an AgentRun."""
    try:
        run = _agent_store(agent_runs_dir).load(agent_run_id)
    except (AgentRunNotFoundError, AgentStorageError) as error:
        _exit_for_agent(error)
    typer.echo(format_agent_history(run, verbose=verbose), nl=False)


@agent_app.command("list")
def agent_list(
    agent_runs_dir: AgentRunsDirOption = None,
    opportunity_id: Annotated[
        str | None,
        typer.Option("--opportunity", help="Filter by opportunity id."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum runs to list (newest first)."),
    ] = 50,
) -> None:
    """List AgentRuns (newest updated_at first)."""
    try:
        runs = _agent_store(agent_runs_dir).list_runs()
    except AgentStorageError as error:
        _exit_for_agent(error)
    if opportunity_id:
        runs = [r for r in runs if r.goal.opportunity_id == opportunity_id]
    if not runs:
        typer.echo("No agent runs found.")
        return
    for run in runs[: max(limit, 0)]:
        typer.echo(format_agent_list_line(run))


if __name__ == "__main__":
    app()
