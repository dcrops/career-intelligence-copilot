from pathlib import Path

import pytest

from career_intelligence.profile import CareerProfileService, ProfileValidationError


def test_invalid_profile_returns_structured_errors() -> None:
    invalid_path = Path(__file__).parents[2] / "fixtures" / "invalid_profile_missing_fields.yaml"

    with pytest.raises(ProfileValidationError) as raised:
        CareerProfileService.from_path(invalid_path).validate()

    assert raised.value.errors
    assert all(error.loc and error.msg and error.type for error in raised.value.errors)
    locations = {error.loc for error in raised.value.errors}
    assert ("skills", "technical") in locations
    assert ("goals",) in locations


def test_raw_pydantic_error_does_not_escape_public_service() -> None:
    invalid_path = Path(__file__).parents[2] / "fixtures" / "invalid_profile_missing_fields.yaml"

    with pytest.raises(ProfileValidationError):
        CareerProfileService.from_path(invalid_path).load()
