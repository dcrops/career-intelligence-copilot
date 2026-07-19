from pathlib import Path

import pytest

from career_intelligence.profile import (
    CareerProfile,
    ProfileNotFoundError,
    ProfileStorageError,
    ProfileValidationError,
)
from career_intelligence.storage.yaml_store import YamlProfileStore


def test_yaml_store_round_trips_without_data_loss(
    tmp_path: Path, valid_profile: CareerProfile
) -> None:
    path = tmp_path / "nested" / "profile.yaml"
    store = YamlProfileStore(path)

    store.save(valid_profile)

    reloaded = store.load()
    assert reloaded == valid_profile
    assert reloaded.experience[0].kind == "employment"
    assert reloaded.experience[0].organisation == "Example Company"


def test_missing_profile_raises_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "missing.yaml"

    with pytest.raises(ProfileNotFoundError, match="profile init"):
        YamlProfileStore(path).load()


def test_invalid_yaml_raises_storage_error(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("identity: [unterminated", encoding="utf-8")

    with pytest.raises(ProfileStorageError, match="Invalid YAML"):
        YamlProfileStore(path).load()


def test_non_mapping_yaml_root_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- not\n- a\n- profile\n", encoding="utf-8")

    with pytest.raises(ProfileStorageError, match="must be a YAML mapping"):
        YamlProfileStore(path).load()


def test_unknown_yaml_fields_fail_validation(tmp_path: Path, minimal_profile_path: Path) -> None:
    path = tmp_path / "extra.yaml"
    path.write_text(
        minimal_profile_path.read_text(encoding="utf-8") + "\nunexpected: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ProfileValidationError) as raised:
        YamlProfileStore(path).load()

    assert raised.value.errors[0].loc == ("unexpected",)
