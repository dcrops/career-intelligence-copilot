from pathlib import Path

import pytest

from career_intelligence.profile import (
    CareerProfileService,
    ProfileSection,
    ProfileStorageError,
    Skill,
    UnknownSectionError,
)


def test_service_returns_named_section(tmp_profile_path: Path) -> None:
    service = CareerProfileService.from_path(tmp_profile_path)

    projects = service.get_section(ProfileSection.PROJECTS)

    assert projects[0].id == "example-project"


def test_service_rejects_unknown_section(tmp_profile_path: Path) -> None:
    service = CareerProfileService.from_path(tmp_profile_path)

    with pytest.raises(UnknownSectionError, match="Choose from"):
        service.get_section("unknown")  # type: ignore[arg-type]


def test_service_builds_typed_summary(tmp_profile_path: Path) -> None:
    summary = CareerProfileService.from_path(tmp_profile_path).summary()

    assert summary.full_name == "Test Candidate"
    assert summary.target_role == "AI Engineer"
    assert summary.technical_skill_count == 1
    assert summary.project_count == 1
    assert summary.primary_goal == "Secure an AI Engineering role."


def test_service_saves_full_model_update(tmp_profile_path: Path) -> None:
    service = CareerProfileService.from_path(tmp_profile_path)
    profile = service.load()
    profile.skills.technical.append(Skill(name="FastAPI", evidence="project:example-project"))

    saved = service.save(profile)

    assert saved.skills.technical[-1].name == "FastAPI"
    assert service.load().skills.technical[-1].evidence == "project:example-project"


def test_init_creates_valid_scaffold(tmp_path: Path) -> None:
    path = tmp_path / "new" / "profile.yaml"
    service = CareerProfileService.from_path(path)

    initialized = service.init_profile()

    assert path.is_file()
    assert service.validate() == initialized


def test_init_refuses_to_overwrite_without_force(tmp_profile_path: Path) -> None:
    service = CareerProfileService.from_path(tmp_profile_path)

    with pytest.raises(ProfileStorageError, match="--force"):
        service.init_profile()


def test_init_force_replaces_existing_profile(tmp_profile_path: Path) -> None:
    service = CareerProfileService.from_path(tmp_profile_path)

    initialized = service.init_profile(force=True)

    assert initialized.identity.full_name == "Your Name"
    assert service.load() == initialized
