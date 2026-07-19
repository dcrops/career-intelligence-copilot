from pathlib import Path

from typer.testing import CliRunner

from career_intelligence.cli.main import app

runner = CliRunner()


def test_validate_command_formats_structured_errors() -> None:
    invalid_path = Path(__file__).parents[2] / "fixtures" / "invalid_profile_missing_fields.yaml"

    result = runner.invoke(
        app,
        ["profile", "validate", "--path", str(invalid_path)],
    )

    assert result.exit_code == 1
    assert "Career profile validation failed:" in result.output
    assert "skills.technical:" in result.output
    assert "goals: Field required" in result.output
