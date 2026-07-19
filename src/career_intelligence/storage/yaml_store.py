"""YAML persistence adapter for the career profile."""

from contextlib import suppress
from pathlib import Path

import yaml
from pydantic import ValidationError

from career_intelligence.profile.errors import (
    ErrorDetail,
    ProfileNotFoundError,
    ProfileStorageError,
    ProfileValidationError,
)
from career_intelligence.profile.models import CareerProfile


class YamlProfileStore:
    """Load and save one typed career profile as YAML."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> CareerProfile:
        if not self.path.is_file():
            raise ProfileNotFoundError(
                f"Career profile not found at {self.path}. Run 'cic profile init'."
            )

        try:
            with self.path.open(encoding="utf-8") as profile_file:
                raw_profile = yaml.safe_load(profile_file)
        except yaml.YAMLError as error:
            raise ProfileStorageError(f"Invalid YAML in {self.path}: {error}") from error
        except OSError as error:
            raise ProfileStorageError(f"Could not read {self.path}: {error}") from error

        if not isinstance(raw_profile, dict):
            raise ProfileStorageError(f"Career profile root at {self.path} must be a YAML mapping.")

        try:
            return CareerProfile.model_validate(raw_profile)
        except ValidationError as error:
            raise ProfileValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

    def save(self, profile: CareerProfile) -> None:
        serialized = profile.model_dump(mode="json")
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with temporary_path.open("w", encoding="utf-8", newline="\n") as profile_file:
                yaml.safe_dump(
                    serialized,
                    profile_file,
                    sort_keys=False,
                    allow_unicode=True,
                    default_flow_style=False,
                )
            temporary_path.replace(self.path)
        except (OSError, yaml.YAMLError) as error:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
            raise ProfileStorageError(f"Could not write {self.path}: {error}") from error
