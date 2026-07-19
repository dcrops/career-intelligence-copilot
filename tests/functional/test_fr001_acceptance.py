from pathlib import Path

import career_intelligence.profile as profile_api
from career_intelligence.profile import (
    CareerProfileService,
    ProfileSection,
    Skill,
)


def _service_with_golden_profile(tmp_path: Path, golden_profile_path: Path) -> CareerProfileService:
    path = tmp_path / "career_profile.yaml"
    path.write_bytes(golden_profile_path.read_bytes())
    return CareerProfileService.from_path(path)


def test_user_profile_can_be_updated_and_reloaded(
    tmp_path: Path, golden_profile_path: Path
) -> None:
    service = _service_with_golden_profile(tmp_path, golden_profile_path)
    profile = service.load()
    profile.skills.technical.append(
        Skill(
            name="Pydantic",
            evidence="project:career-intelligence-copilot-fr001",
        )
    )

    service.save(profile)
    reloaded = service.load()

    assert reloaded.skills.technical[-1].name == "Pydantic"
    assert reloaded.skills.technical[-1].evidence.startswith("project:")


def test_all_required_profile_facets_are_available_to_decisions(
    tmp_path: Path, golden_profile_path: Path
) -> None:
    service = _service_with_golden_profile(tmp_path, golden_profile_path)

    assert service.get_section(ProfileSection.EXPERIENCE)
    assert service.get_section(ProfileSection.SKILLS).technical
    assert service.get_section(ProfileSection.PROJECTS)
    assert service.get_section(ProfileSection.CERTIFICATIONS)
    assert service.get_section(ProfileSection.GOALS).primary
    assert service.get_section(ProfileSection.PREFERENCES).locations


def test_experience_entries_are_truthfully_classified_by_kind(
    tmp_path: Path, golden_profile_path: Path
) -> None:
    service = _service_with_golden_profile(tmp_path, golden_profile_path)

    entries = {entry.id: entry for entry in service.get_section(ProfileSection.EXPERIENCE)}

    assert entries["nbn-data-engineer-2020"].kind == "employment"
    assert entries["chase-risk-compliance-ai-engineer"].kind == "independent_engineering"

    development_kinds = {
        entry.kind
        for entry in entries.values()
        if entry.id
        in (
            "data-engineering-development-2023",
            "ai-engineering-development-2025",
            "general-assembly-data-science-2019",
        )
    }
    assert development_kinds == {"professional_development"}

    qa_role_ids = (
        "bakers-delight-test-analyst-2009",
        "console-test-analyst-2012",
        "bakers-delight-test-analyst-2015",
        "accesshq-test-analyst-2018",
        "bakers-delight-test-analyst-2019",
    )
    assert all(entries[role_id].kind == "employment" for role_id in qa_role_ids)


def test_certifications_distinguish_active_and_expired_credentials(
    tmp_path: Path, golden_profile_path: Path
) -> None:
    service = _service_with_golden_profile(tmp_path, golden_profile_path)

    certifications = {
        certification.id: certification
        for certification in service.get_section(ProfileSection.CERTIFICATIONS)
    }

    assert certifications["databricks-certified-data-engineer-associate"].status == "expired"
    assert certifications["aws-certified-developer-associate"].status == "active"
    assert certifications["databricks-certified-data-engineer-professional"].status == "active"
    assert all(certification.expiry_date is not None for certification in certifications.values())


def test_public_api_does_not_expose_storage_implementation() -> None:
    assert "YamlProfileStore" not in profile_api.__all__
    assert "ProfileStore" not in profile_api.__all__
    assert not hasattr(profile_api, "YamlProfileStore")


def test_downstream_modules_do_not_import_storage_implementation() -> None:
    source_root = Path(__file__).parents[2] / "src" / "career_intelligence"
    allowed_internal_files = {
        source_root / "profile" / "service.py",
        source_root / "storage" / "yaml_store.py",
    }

    for source_file in source_root.rglob("*.py"):
        if source_file not in allowed_internal_files:
            assert "career_intelligence.storage" not in source_file.read_text(encoding="utf-8")
