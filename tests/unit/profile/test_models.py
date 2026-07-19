from datetime import date

import pytest
from pydantic import ValidationError

from career_intelligence.profile import CareerProfile


def test_valid_profile_has_typed_sections(valid_profile: CareerProfile) -> None:
    assert valid_profile.experience[0].start_date == date(2022, 1, 1)
    assert valid_profile.experience[0].kind == "employment"
    assert valid_profile.experience[0].organisation == "Example Company"
    assert valid_profile.skills.technical[0].name == "Python"
    assert valid_profile.projects[0].demonstrates == ["Evidence-backed decision support"]


def test_experience_kind_is_required(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    del payload["experience"][0]["kind"]

    with pytest.raises(ValidationError, match="kind"):
        CareerProfile.model_validate(payload)


@pytest.mark.parametrize(
    "kind", ["employment", "independent_engineering", "professional_development"]
)
def test_experience_accepts_each_permitted_kind(valid_profile: CareerProfile, kind: str) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["experience"][0]["kind"] = kind

    profile = CareerProfile.model_validate(payload)

    assert profile.experience[0].kind == kind


def test_experience_rejects_unknown_kind(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["experience"][0]["kind"] = "freelance"

    with pytest.raises(ValidationError, match="kind"):
        CareerProfile.model_validate(payload)


def test_experience_rejects_legacy_company_field(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["experience"][0]["company"] = payload["experience"][0].pop("organisation")

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CareerProfile.model_validate(payload)


def test_experience_organisation_is_required(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    del payload["experience"][0]["organisation"]

    with pytest.raises(ValidationError, match="organisation"):
        CareerProfile.model_validate(payload)


def _certification_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "example-cert",
        "name": "Example Certification",
        "issuer": "Example Issuer",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_certification_status_is_required(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    certification = _certification_payload()
    del certification["status"]
    payload["certifications"] = [certification]

    with pytest.raises(ValidationError, match="status"):
        CareerProfile.model_validate(payload)


@pytest.mark.parametrize("status", ["active", "expired"])
def test_certification_accepts_each_permitted_status(
    valid_profile: CareerProfile, status: str
) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["certifications"] = [_certification_payload(status=status)]

    profile = CareerProfile.model_validate(payload)

    assert profile.certifications[0].status == status


def test_certification_rejects_unknown_status(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["certifications"] = [_certification_payload(status="lapsed")]

    with pytest.raises(ValidationError, match="status"):
        CareerProfile.model_validate(payload)


def test_certification_expiry_date_accepts_year_month(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["certifications"] = [_certification_payload(status="expired", expiry_date="2026-07")]

    profile = CareerProfile.model_validate(payload)

    assert profile.certifications[0].expiry_date == date(2026, 7, 1)


def test_skill_rejects_self_assessed_level(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["skills"]["technical"][0]["level"] = "expert"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CareerProfile.model_validate(payload)


def test_technical_skills_cannot_be_empty(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["skills"]["technical"] = []

    with pytest.raises(ValidationError, match="at least 1 item"):
        CareerProfile.model_validate(payload)


def test_projects_cannot_be_empty(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["projects"] = []

    with pytest.raises(ValidationError, match="at least 1 item"):
        CareerProfile.model_validate(payload)


def test_entity_ids_must_be_unique(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["projects"].append(payload["projects"][0].copy())

    with pytest.raises(ValidationError, match="projects ids must be unique"):
        CareerProfile.model_validate(payload)


def test_experience_end_date_cannot_precede_start(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["experience"][0]["end_date"] = "2021-12-01"

    with pytest.raises(ValidationError, match="end_date must be on or after start_date"):
        CareerProfile.model_validate(payload)


def test_required_strings_reject_whitespace(valid_profile: CareerProfile) -> None:
    payload = valid_profile.model_dump(mode="json")
    payload["goals"]["primary"] = "   "

    with pytest.raises(ValidationError, match="at least 1 character"):
        CareerProfile.model_validate(payload)
