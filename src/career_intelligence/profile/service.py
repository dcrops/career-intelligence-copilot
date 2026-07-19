"""Public service layer for career-profile consumers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from career_intelligence.storage.yaml_store import YamlProfileStore

from .errors import (
    ErrorDetail,
    ProfileNotFoundError,
    ProfileStorageError,
    ProfileValidationError,
    UnknownSectionError,
)
from .models import (
    CareerProfile,
    Goals,
    Identity,
    Preferences,
    ProfileSummary,
    Project,
    Skill,
    Skills,
)
from .sections import ProfileSection
from .store import ProfileStore

DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[3] / "data" / "career_profile.yaml"


class CareerProfileService:
    """Stable interface used by the CLI and future decision stages."""

    def __init__(self, store: ProfileStore | None = None) -> None:
        self._store = store or YamlProfileStore(_configured_profile_path())

    @classmethod
    def from_path(cls, path: Path) -> CareerProfileService:
        """Compose the service for an explicit profile path."""
        return cls(store=YamlProfileStore(path))

    def load(self) -> CareerProfile:
        return self._store.load()

    def validate(self, profile: CareerProfile | None = None) -> CareerProfile:
        if profile is None:
            return self.load()

        try:
            return CareerProfile.model_validate(profile.model_dump(mode="python"))
        except ValidationError as error:
            raise ProfileValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

    def save(self, profile: CareerProfile) -> CareerProfile:
        validated = self.validate(profile)
        self._store.save(validated)
        return validated

    def get_section(self, section: ProfileSection) -> Any:
        try:
            profile_section = ProfileSection(section)
        except ValueError as error:
            allowed = ", ".join(item.value for item in ProfileSection)
            raise UnknownSectionError(
                f"Unknown profile section '{section}'. Choose from: {allowed}."
            ) from error
        return getattr(self.load(), profile_section.value)

    def summary(self) -> ProfileSummary:
        profile = self.load()
        return ProfileSummary(
            full_name=profile.identity.full_name,
            target_role=profile.identity.target_role,
            technical_skill_count=len(profile.skills.technical),
            domain_skill_count=len(profile.skills.domain),
            soft_skill_count=len(profile.skills.soft),
            project_count=len(profile.projects),
            certification_count=len(profile.certifications),
            primary_goal=profile.goals.primary,
        )

    def init_profile(self, force: bool = False) -> CareerProfile:
        if not force:
            try:
                self.load()
            except ProfileNotFoundError:
                pass
            else:
                raise ProfileStorageError(
                    "Career profile already exists. Use --force to replace it."
                )

        return self.save(_initial_profile())


def _configured_profile_path() -> Path:
    configured = os.getenv("CIC_PROFILE_PATH")
    return Path(configured) if configured else DEFAULT_PROFILE_PATH


def _initial_profile() -> CareerProfile:
    """Return a valid scaffold that can be explicitly initialized."""
    return CareerProfile(
        schema_version="1",
        identity=Identity(
            full_name="Your Name",
            target_role="AI Engineer",
            summary="Replace this summary with evidence from your career history.",
        ),
        experience=[],
        skills=Skills(
            technical=[
                Skill(
                    name="Add a technical skill",
                    evidence="Replace with an experience, project, or certification reference",
                )
            ],
            domain=[],
            soft=[],
        ),
        projects=[
            Project(
                id="replace-with-project",
                name="Replace with a portfolio project",
                summary="Describe what was built and why.",
                technologies=[],
                outcomes=[],
                demonstrates=[],
            )
        ],
        certifications=[],
        goals=Goals(primary="Define the primary career goal"),
        preferences=Preferences(
            locations=[],
            employment_types=[],
            remote="flexible",
            company_stages=[],
            must_haves=[],
            deal_breakers=[],
        ),
    )
