"""Unit tests for OpenAIJobExtractor using an injected fake client (offline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from openai import OpenAIError
from pydantic import ValidationError

from career_intelligence.job_analysis import (
    JobAnalysisError,
    JobAnalysisValidationError,
    JobPosting,
)
from career_intelligence.job_analysis.extraction import JobAnalysisExtraction
from career_intelligence.job_analysis.extraction_prompt import (
    EXTRACTION_INSTRUCTIONS_V1,
    EXTRACTION_PROMPT_VERSION,
)
from career_intelligence.job_analysis.fixtures import (
    analysis_for_ai_engineer,
    analysis_for_ambiguous_seniority,
    analysis_for_missing_salary,
    posting_ai_engineer,
)
from career_intelligence.job_analysis.openai_extractor import (
    DEFAULT_MODEL,
    OpenAIJobExtractor,
    _format_posting_input,
)


def _valid_extraction_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = dict(analysis_for_ai_engineer())
    payload.update(overrides)
    return payload


@dataclass
class _FakeRefusalContent:
    refusal: str
    type: str = "refusal"


@dataclass
class _FakeMessage:
    content: list[object]
    type: str = "message"


@dataclass
class _FakeParseResult:
    output_parsed: object | None = None
    output: list[object] = field(default_factory=list)


class _FakeResponses:
    def __init__(
        self,
        *,
        result: object | None = None,
        side_effect: BaseException | None = None,
    ) -> None:
        self._result = result
        self._side_effect = side_effect
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        if self._side_effect is not None:
            raise self._side_effect
        assert self._result is not None
        return self._result


class _FakeOpenAI:
    def __init__(
        self,
        *,
        result: object | None = None,
        side_effect: BaseException | None = None,
    ) -> None:
        self.responses = _FakeResponses(result=result, side_effect=side_effect)


def _extractor_with(
    *,
    result: object | None = None,
    side_effect: BaseException | None = None,
) -> tuple[OpenAIJobExtractor, _FakeOpenAI]:
    client = _FakeOpenAI(result=result, side_effect=side_effect)
    return OpenAIJobExtractor(client=client), client


def test_prompt_version_and_instructions_are_defined() -> None:
    assert EXTRACTION_PROMPT_VERSION == "v7"
    assert "Evidence (global" in EXTRACTION_INSTRUCTIONS_V1
    assert "Never emit a known role family" in EXTRACTION_INSTRUCTIONS_V1
    assert "never invent compensation" in EXTRACTION_INSTRUCTIONS_V1.lower()
    assert "ambiguous=false" in EXTRACTION_INSTRUCTIONS_V1.lower()
    assert 'clarity="unstated"' in EXTRACTION_INSTRUCTIONS_V1.lower()
    assert "<jobtitle>" in EXTRACTION_INSTRUCTIONS_V1.lower()
    assert "job title" in EXTRACTION_INSTRUCTIONS_V1.lower()
    assert "employment" in EXTRACTION_INSTRUCTIONS_V1.lower()
    assert "never infer" in EXTRACTION_INSTRUCTIONS_V1.lower()
    assert "How you match" in EXTRACTION_INSTRUCTIONS_V1
    assert "network_engineering" in EXTRACTION_INSTRUCTIONS_V1
    assert "Negative examples (must remain unspecified / empty evidence)" not in (
        EXTRACTION_INSTRUCTIONS_V1
    )
    assert "posting" in EXTRACTION_INSTRUCTIONS_V1.lower()


def test_format_posting_input_tags_trusted_metadata_sections() -> None:
    posting = JobPosting(
        title="Principal AI Engineer",
        company="ABC Pty Ltd",
        source_url="https://example.com/jobs/principal-ai",
        raw_text="Build LLM applications with Python. Hybrid Melbourne.",
    )

    rendered = _format_posting_input(posting)

    assert "<JobTitle>\nPrincipal AI Engineer\n</JobTitle>" in rendered
    assert "<Company>\nABC Pty Ltd\n</Company>" in rendered
    assert "<SourceURL>\nhttps://example.com/jobs/principal-ai\n</SourceURL>" in rendered
    assert "<JobDescription>\nBuild LLM applications with Python. Hybrid Melbourne.\n</JobDescription>" in rendered
    assert "Title:" not in rendered
    assert "Job description:" not in rendered


def test_format_posting_input_omits_absent_optional_metadata() -> None:
    posting = JobPosting(raw_text="AI Engineer. Python required.")

    rendered = _format_posting_input(posting)

    assert rendered.startswith("<JobDescription>")
    assert "<JobTitle>" not in rendered
    assert "<Company>" not in rendered
    assert "<SourceURL>" not in rendered


def test_valid_extraction_returns_payload_without_posting() -> None:
    extraction = JobAnalysisExtraction.model_validate(_valid_extraction_payload())
    extractor, client = _extractor_with(result=_FakeParseResult(output_parsed=extraction))

    payload = extractor.extract(posting_ai_engineer())

    assert "posting" not in payload
    assert payload["role_family"]["family"] == "ai_engineering"
    assert payload["seniority"]["level"] == "senior"
    assert client.responses.calls[0]["model"] == DEFAULT_MODEL
    assert client.responses.calls[0]["instructions"] == EXTRACTION_INSTRUCTIONS_V1
    assert client.responses.calls[0]["text_format"] is JobAnalysisExtraction
    rendered = client.responses.calls[0]["input"]
    assert "<JobTitle>\nSenior AI Engineer\n</JobTitle>" in rendered
    assert "<JobDescription>" in rendered


def test_required_versus_preferred_preserved() -> None:
    extraction = JobAnalysisExtraction.model_validate(_valid_extraction_payload())
    extractor, _ = _extractor_with(result=_FakeParseResult(output_parsed=extraction))

    payload = extractor.extract(posting_ai_engineer())
    by_name = {tech["name"]: tech["level"] for tech in payload["technologies"]}

    assert by_name["Python"] == "required"
    assert by_name["LangChain"] == "preferred"


def test_evidence_excerpts_preserved() -> None:
    extraction = JobAnalysisExtraction.model_validate(_valid_extraction_payload())
    extractor, _ = _extractor_with(result=_FakeParseResult(output_parsed=extraction))

    payload = extractor.extract(posting_ai_engineer())
    python = next(tech for tech in payload["technologies"] if tech["name"] == "Python")

    assert python["evidence"][0]["excerpt"] == "Strong Python required"


def test_ambiguous_seniority_preserved() -> None:
    extraction = JobAnalysisExtraction.model_validate(analysis_for_ambiguous_seniority())
    extractor, _ = _extractor_with(result=_FakeParseResult(output_parsed=extraction))

    payload = extractor.extract(
        JobPosting(raw_text="Senior / Lead AI Engineer with conflicting signals.")
    )

    assert payload["seniority"]["ambiguous"] is True
    assert payload["seniority"]["level"] == "unknown"
    assert set(payload["seniority"]["candidate_levels"]) == {"senior", "lead"}
    assert payload["seniority"]["evidence"]


def test_unknown_and_unstated_values_preserved() -> None:
    extraction = JobAnalysisExtraction.model_validate(analysis_for_missing_salary())
    extractor, _ = _extractor_with(result=_FakeParseResult(output_parsed=extraction))

    payload = extractor.extract(JobPosting(raw_text="AI Engineer. Competitive salary."))

    assert payload["compensation"]["clarity"] == "unstated"
    assert payload["compensation"].get("minimum") is None
    assert payload["seniority"]["level"] == "unknown"
    assert payload["seniority"]["ambiguous"] is False


def test_refusal_becomes_job_analysis_error() -> None:
    result = _FakeParseResult(
        output_parsed=None,
        output=[_FakeMessage(content=[_FakeRefusalContent(refusal="Not allowed")])],
    )
    extractor, _ = _extractor_with(result=result)

    with pytest.raises(JobAnalysisError, match="refused") as raised:
        extractor.extract(posting_ai_engineer())

    assert not isinstance(raised.value, JobAnalysisValidationError)


def test_empty_response_becomes_job_analysis_error() -> None:
    extractor, _ = _extractor_with(result=_FakeParseResult(output_parsed=None))

    with pytest.raises(JobAnalysisError, match="empty structured extraction"):
        extractor.extract(posting_ai_engineer())


def test_malformed_structured_response_becomes_validation_error() -> None:
    extractor, _ = _extractor_with(
        result=_FakeParseResult(
            output_parsed={"role_family": {"family": "not_a_real_family"}}
        )
    )

    with pytest.raises(JobAnalysisValidationError) as raised:
        extractor.extract(posting_ai_engineer())

    assert raised.value.errors


def test_sdk_exception_becomes_job_analysis_error() -> None:
    extractor, _ = _extractor_with(side_effect=OpenAIError("upstream failure"))

    with pytest.raises(JobAnalysisError, match="OpenAI extraction failed") as raised:
        extractor.extract(posting_ai_engineer())

    assert not isinstance(raised.value, JobAnalysisValidationError)


def test_unexpected_programmer_errors_propagate() -> None:
    extractor, _ = _extractor_with(side_effect=RuntimeError("bug in fake client"))

    with pytest.raises(RuntimeError, match="bug in fake client"):
        extractor.extract(posting_ai_engineer())


def test_sdk_validation_error_becomes_job_analysis_validation_error() -> None:
    side_effect = ValidationError.from_exception_data(
        "JobAnalysisExtraction",
        [
            {
                "type": "missing",
                "loc": ("compensation",),
                "input": {},
            }
        ],
    )
    extractor, _ = _extractor_with(side_effect=side_effect)

    with pytest.raises(JobAnalysisValidationError) as raised:
        extractor.extract(posting_ai_engineer())

    assert raised.value.errors


def test_payload_excludes_posting_and_candidate_fit_fields() -> None:
    extraction = JobAnalysisExtraction.model_validate(_valid_extraction_payload())
    extractor, _ = _extractor_with(result=_FakeParseResult(output_parsed=extraction))

    payload = extractor.extract(posting_ai_engineer())
    forbidden = {
        "posting",
        "technical_fit",
        "commercial_fit",
        "portfolio_fit",
        "tier",
        "recommendation",
        "apply",
        "skip",
        "candidate_fit",
        "match_score",
    }

    assert set(payload).isdisjoint(forbidden)


def test_extraction_is_deterministic_for_identical_fake_responses() -> None:
    extraction = JobAnalysisExtraction.model_validate(_valid_extraction_payload())
    result = _FakeParseResult(output_parsed=extraction)
    extractor, _ = _extractor_with(result=result)
    posting = posting_ai_engineer()

    first = extractor.extract(posting)
    second = extractor.extract(posting)

    assert first == second


def test_configurable_model_is_passed_to_parse() -> None:
    extraction = JobAnalysisExtraction.model_validate(_valid_extraction_payload())
    client = _FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    extractor = OpenAIJobExtractor(client=client, model="gpt-4o")

    extractor.extract(posting_ai_engineer())

    assert client.responses.calls[0]["model"] == "gpt-4o"
