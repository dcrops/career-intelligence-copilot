from pathlib import Path

import pytest

from career_intelligence.profile import CareerProfile, CareerProfileService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_profile_path() -> Path:
    return FIXTURES / "minimal_valid_profile.yaml"


@pytest.fixture
def valid_profile(minimal_profile_path: Path) -> CareerProfile:
    return CareerProfileService.from_path(minimal_profile_path).load()


@pytest.fixture
def tmp_profile_path(tmp_path: Path, minimal_profile_path: Path) -> Path:
    destination = tmp_path / "career_profile.yaml"
    destination.write_bytes(minimal_profile_path.read_bytes())
    return destination


@pytest.fixture
def golden_profile_path() -> Path:
    return FIXTURES / "golden" / "career_profile.yaml"
