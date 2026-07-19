"""Command-line interface for the career profile."""

from pathlib import Path
from typing import Annotated, Never

import typer
import yaml
from pydantic import BaseModel

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
app.add_typer(profile_app, name="profile")

PathOption = Annotated[
    Path | None,
    typer.Option("--path", help="Override the configured career profile path."),
]


def _service(path: Path | None) -> CareerProfileService:
    return CareerProfileService.from_path(path) if path else CareerProfileService()


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


def _exit_for(error: ProfileError) -> Never:
    if isinstance(error, ProfileValidationError):
        typer.echo("Career profile validation failed:", err=True)
        for detail in error.errors:
            typer.echo(f"- {_format_location(detail.loc)}: {detail.msg}", err=True)
        raise typer.Exit(code=1)

    typer.echo(str(error), err=True)
    code = 1 if isinstance(error, UnknownSectionError) else 2
    raise typer.Exit(code=code)


@profile_app.command("validate")
def validate_profile(path: PathOption = None) -> None:
    """Validate the configured career profile."""
    try:
        _service(path).validate()
    except (ProfileValidationError, ProfileNotFoundError, ProfileStorageError) as error:
        _exit_for(error)
    typer.echo("Career profile is valid.")


@profile_app.command("summary")
def profile_summary(path: PathOption = None) -> None:
    """Display a compact career-profile summary."""
    try:
        summary = _service(path).summary()
    except ProfileError as error:
        _exit_for(error)
    typer.echo(_render(summary))


@profile_app.command("show")
def show_profile_section(
    section: Annotated[ProfileSection, typer.Argument(help="Profile section to display.")],
    path: PathOption = None,
) -> None:
    """Display one named profile section."""
    try:
        value = _service(path).get_section(section)
    except ProfileError as error:
        _exit_for(error)
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
        _service(path).init_profile(force=force)
    except ProfileError as error:
        _exit_for(error)
    target = path or "the configured path"
    typer.echo(f"Career profile initialized at {target}.")


if __name__ == "__main__":
    app()
