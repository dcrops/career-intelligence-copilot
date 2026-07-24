"""FR-002 extraction prompt and chrome-hardening regression tests."""

from __future__ import annotations

from career_intelligence.job_analysis import JobAnalysisService, JobPosting
from career_intelligence.job_analysis.extraction import JobAnalysisExtraction
from career_intelligence.job_analysis.extraction_prompt import (
    EXTRACTION_INSTRUCTIONS_V1,
    EXTRACTION_PROMPT_VERSION,
)
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    analysis_for_ai_engineer,
    analysis_for_junior_software_devops,
    posting_ai_engineer,
    posting_junior_software_devops,
)
from career_intelligence.job_analysis.openai_extractor import (
    OpenAIJobExtractor,
    _format_posting_input,
)

from .test_openai_extractor import _FakeOpenAI, _FakeParseResult


def test_prompt_version_is_v8() -> None:
    assert EXTRACTION_PROMPT_VERSION == "v8"


def test_prompt_deprioritises_seek_chrome() -> None:
    text = EXTRACTION_INSTRUCTIONS_V1.casefold()
    assert "how you match" in text
    assert "show all" in text
    assert "application-volume" in text or "application volume" in text
    assert "view all jobs" in text
    assert "employer questions" in text
    assert "profile-match" in text or "profile match" in text


def test_prompt_requires_multiple_responsibilities_and_split_technologies() -> None:
    text = EXTRACTION_INSTRUCTIONS_V1.casefold()
    assert "responsibilities" in text
    assert "deduplicate" in text
    assert "self-motivated" in text
    assert "infrastructure as code" in text
    assert "required" in text and "preferred" in text
    assert "do not invent technologies" in text


def test_junior_fixture_does_not_treat_how_you_match_as_full_tech_list() -> None:
    analysis = JobAnalysisService(FixtureExtractor()).analyse(
        posting_junior_software_devops()
    )
    tech_names = [tech.name for tech in analysis.technologies]

    assert "Python Programming" not in tech_names
    assert any(name.casefold() == "python" for name in tech_names)
    assert len(tech_names) >= 5
    assert len(analysis.responsibilities) >= 5


def test_openai_mock_preserves_employer_authored_technologies_and_levels() -> None:
    extraction = JobAnalysisExtraction.model_validate(
        analysis_for_junior_software_devops()
    )
    client = _FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    extractor = OpenAIJobExtractor(client=client)

    payload = extractor.extract(posting_junior_software_devops())
    by_name = {tech["name"]: tech["level"] for tech in payload["technologies"]}

    assert by_name["Python"] == "preferred"
    assert by_name["Terraform"] == "preferred"
    assert "Python Programming" not in by_name
    assert len(payload["responsibilities"]) >= 5
    assert client.responses.calls[0]["instructions"] == EXTRACTION_INSTRUCTIONS_V1


def test_openai_mock_does_not_introduce_unsupported_technologies() -> None:
    extraction = JobAnalysisExtraction.model_validate(
        analysis_for_junior_software_devops()
    )
    client = _FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    payload = OpenAIJobExtractor(client=client).extract(posting_junior_software_devops())

    unsupported = {"Kubernetes", "Kafka", "Rust", "Golang"}
    names = {tech["name"] for tech in payload["technologies"]}
    assert names.isdisjoint(unsupported)


def test_existing_ai_engineer_extraction_behaviour_unchanged() -> None:
    extraction = JobAnalysisExtraction.model_validate(analysis_for_ai_engineer())
    client = _FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    payload = OpenAIJobExtractor(client=client).extract(posting_ai_engineer())

    assert payload["role_family"]["family"] == "ai_engineering"
    assert {tech["name"]: tech["level"] for tech in payload["technologies"]} == {
        "Python": "required",
        "LangChain": "preferred",
    }


def test_seek_chrome_only_posting_still_formats_for_extractor() -> None:
    """Chrome text is passed through; prompt instructs de-prioritisation."""
    posting = JobPosting(
        title="AI Engineer",
        company="Example",
        raw_text=(
            "View all jobs\nHow you match\nPython Programming\nGoogle Cloud\n"
            "Show all\nMedium application volume\n"
            "About the role\nBuild LLM tools with Python and evaluation harnesses.\n"
            "Skills\nPython required; Azure preferred.\n"
        ),
    )
    rendered = _format_posting_input(posting)
    assert "How you match" in rendered
    assert "About the role" in rendered
    assert EXTRACTION_PROMPT_VERSION == "v8"
