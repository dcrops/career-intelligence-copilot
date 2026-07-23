import subprocess
import sys
from datetime import date
from pathlib import Path

from career_intelligence.profile import (
    CareerProfileService,
    ProfileSection,
    Skill,
)


def test_real_profile_user_journey(tmp_path: Path, golden_profile_path: Path) -> None:
    working_path = tmp_path / "career_profile.yaml"
    service = CareerProfileService.from_path(working_path)

    scaffold = service.init_profile()
    assert scaffold.identity.target_role == "AI Engineer"

    real_profile = CareerProfileService.from_path(golden_profile_path).load()
    service.save(real_profile)
    assert service.validate().identity.full_name == "David Cropper"

    summary = service.summary()
    assert summary.target_role == "AI Engineer"
    assert summary.technical_skill_count > 0
    assert summary.project_count == 4

    projects = service.get_section(ProfileSection.PROJECTS)
    operational_copilot = next(
        project for project in projects if project.id == "operational-intelligence-copilot"
    )
    assert operational_copilot.technologies
    assert operational_copilot.demonstrates

    experience = {entry.id: entry for entry in service.get_section(ProfileSection.EXPERIENCE)}
    nbn = experience["nbn-data-engineer-2020"]
    data_development = experience["data-engineering-development-2023"]
    ai_development = experience["ai-engineering-development-2025"]
    chase = experience["chase-risk-compliance-ai-engineer"]

    assert nbn.kind == "employment"
    assert data_development.kind == "professional_development"
    assert ai_development.kind == "professional_development"
    assert chase.kind == "independent_engineering"

    assert nbn.end_date == date(2023, 10, 1)
    assert data_development.start_date == date(2023, 10, 1)
    assert data_development.end_date == date(2025, 6, 1)
    assert ai_development.start_date == date(2025, 7, 1)
    assert ai_development.end_date == date(2025, 11, 1)
    assert chase.start_date == date(2025, 12, 1)
    assert chase.end_date is None

    # Pre-nbn QA and study history (owner-supplied 2026-07-19).
    pre_nbn_timeline = [
        ("bakers-delight-test-analyst-2009", date(2009, 3, 1), date(2012, 6, 1)),
        ("console-test-analyst-2012", date(2012, 6, 1), date(2014, 12, 1)),
        ("bakers-delight-test-analyst-2015", date(2015, 1, 1), date(2018, 10, 1)),
        ("accesshq-test-analyst-2018", date(2018, 10, 1), date(2019, 6, 1)),
        ("bakers-delight-test-analyst-2019", date(2019, 8, 1), date(2019, 9, 1)),
        ("general-assembly-data-science-2019", date(2019, 9, 1), date(2019, 12, 1)),
    ]
    for entry_id, start, end in pre_nbn_timeline:
        assert experience[entry_id].start_date == start
        assert experience[entry_id].end_date == end

    general_assembly = experience["general-assembly-data-science-2019"]
    assert general_assembly.kind == "professional_development"
    assert general_assembly.technologies == ["Python", "NLP", "Web Scraping"]
    skill_names = {skill.name for skill in service.load().skills.technical}
    assert "NLP" not in skill_names
    assert "Web Scraping" not in skill_names
    assert "Java" not in skill_names
    assert "Ruby on Rails" not in skill_names
    assert "Gherkin" not in skill_names
    assert experience["accesshq-test-analyst-2018"].kind == "employment"
    assert experience["console-test-analyst-2012"].organisation == "Console"

    certifications = {
        certification.id: certification
        for certification in service.get_section(ProfileSection.CERTIFICATIONS)
    }
    assert certifications["databricks-certified-data-engineer-associate"].status == "expired"
    assert certifications["databricks-certified-data-engineer-associate"].expiry_date == date(
        2026, 7, 1
    )
    assert certifications["aws-certified-developer-associate"].status == "active"
    assert certifications["databricks-certified-data-engineer-professional"].status == "active"

    profile = service.load()
    profile.skills.technical.append(
        Skill(name="Pydantic", evidence="project:career-intelligence-copilot-fr001")
    )
    service.save(profile)
    assert service.load().skills.technical[-1].name == "Pydantic"

    repository_root = Path(__file__).parents[2]
    for command in (
        ["validate"],
        ["summary"],
        ["show", "projects"],
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "career_intelligence.cli.main",
                "profile",
                *command,
                "--path",
                str(working_path),
            ],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    assert (
        "Career profile is valid."
        in subprocess.run(
            [
                sys.executable,
                "-m",
                "career_intelligence.cli.main",
                "profile",
                "validate",
                "--path",
                str(working_path),
            ],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )

    cli_initialized_path = tmp_path / "cli_initialized.yaml"
    init_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "career_intelligence.cli.main",
            "profile",
            "init",
            "--path",
            str(cli_initialized_path),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert init_result.returncode == 0, init_result.stderr
    assert CareerProfileService.from_path(cli_initialized_path).validate()
