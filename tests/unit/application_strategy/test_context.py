"""Unit tests for SearchOperatingContext."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.application_strategy import SearchOperatingContext


def test_default_volume_applications_disabled() -> None:
    context = SearchOperatingContext()

    assert context.volume_applications_enabled is False
    assert context.notes is None


def test_notes_may_be_set() -> None:
    context = SearchOperatingContext(
        volume_applications_enabled=True,
        notes="Temporary JobSeeker volume mode",
    )

    assert context.volume_applications_enabled is True
    assert context.notes == "Temporary JobSeeker volume mode"


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SearchOperatingContext.model_validate({"quota_remaining": 5})
