"""Command-line interface for Career Intelligence Copilot."""

from pathlib import Path
from typing import Annotated, Never

import typer
import yaml
from pydantic import BaseModel

from career_intelligence.opportunities import (
    OpportunityError,
    OpportunityNotFoundError,
    OpportunityService,
    OpportunityValidationError,
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
opportunity_app = typer.Typer(help="Inspect persisted opportunities (M1).")
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
    code = 1 if isinstance(error, OpportunityNotFoundError) else 2
    raise typer.Exit(code=code)


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
        typer.echo(
            f"{item.opportunity_id:<34} {item.status:<12} "
            f"{item.strategy_summary.pursuit_posture:<22} "
            f"{item.strategy_summary.application_tier:<10} "
            f"{company:<22} {title}  ({created})"
        )


@opportunity_app.command("show")
def show_opportunity(
    opportunity_id: Annotated[str, typer.Argument(help="Opportunity id (opp_<ULID>).")],
    dir: OpportunitiesDirOption = None,
) -> None:
    """Show one persisted opportunity (identity, summary, artifact paths)."""
    try:
        opportunity = _opportunity_service(dir).get(opportunity_id)
    except OpportunityError as error:
        _exit_for_opportunity(error)
    typer.echo(_render(opportunity))


if __name__ == "__main__":
    app()
