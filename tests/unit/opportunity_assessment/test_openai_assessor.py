"""Unit tests for OpenAIAssessor using an injected fake client (offline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import career_intelligence.opportunity_assessment as opportunity_assessment_api
import pytest
from openai import OpenAIError
from pydantic import ValidationError

from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import posting_applied_ai_engineer
from career_intelligence.opportunity_assessment import (
    OpportunityAssessment,
    OpportunityAssessmentError,
    OpportunityAssessmentService,
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.assessment_prompt import (
    ASSESSMENT_INSTRUCTIONS_V1,
    ASSESSMENT_PROMPT_VERSION,
)
from career_intelligence.opportunity_assessment.extraction import OpportunityAssessmentExtraction
from career_intelligence.opportunity_assessment.fixtures import assessment_strong_ai_alignment
from career_intelligence.opportunity_assessment.openai_assessor import (
    DEFAULT_MODEL,
    OpenAIAssessor,
    format_assessment_input,
)
from career_intelligence.profile import CareerProfileService


def _valid_extraction_payload() -> dict[str, object]:
    return dict(assessment_strong_ai_alignment())


def _golden_profile_path() -> Path:
    return Path(__file__).parents[2] / "fixtures" / "golden" / "career_profile.yaml"


def _job_analysis():
    return JobAnalysisService(FixtureExtractor()).analyse(posting_applied_ai_engineer())


def _profile():
    return CareerProfileService.from_path(_golden_profile_path()).load()


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


def _assessor_with(
    *,
    result: object | None = None,
    side_effect: BaseException | None = None,
) -> tuple[OpenAIAssessor, _FakeOpenAI]:
    client = _FakeOpenAI(result=result, side_effect=side_effect)
    return OpenAIAssessor(client=client), client


def test_prompt_version_and_instructions_are_defined() -> None:
    assert ASSESSMENT_PROMPT_VERSION == "v11"
    assert "Technical Fit" in ASSESSMENT_INSTRUCTIONS_V1 or "technical" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "commercial" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "portfolio" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "independent_engineering" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "tier" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "quota" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "working rights" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "job_analysis" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "Never emit a required evidence-reference array as empty" in ASSESSMENT_INSTRUCTIONS_V1
    assert "partial_alignment" in ASSESSMENT_INSTRUCTIONS_V1
    assert "transferable_alignment" in ASSESSMENT_INSTRUCTIONS_V1
    assert 'kind is exactly "assumption"' in ASSESSMENT_INSTRUCTIONS_V1 or "kind=\"assumption\"" in ASSESSMENT_INSTRUCTIONS_V1
    assert "assumption MUST be null" in ASSESSMENT_INSTRUCTIONS_V1 or "assumption: forbidden" in ASSESSMENT_INSTRUCTIONS_V1
    assert "cite-as" in ASSESSMENT_INSTRUCTIONS_V1.lower() or "cite-as JSON" in ASSESSMENT_INSTRUCTIONS_V1
    assert "verbatim" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "bare ids" in ASSESSMENT_INSTRUCTIONS_V1.lower()
    assert "ProfileEvidenceCiteGuide" in ASSESSMENT_INSTRUCTIONS_V1
    assert "FindingFieldGuide" in ASSESSMENT_INSTRUCTIONS_V1


def test_format_assessment_input_includes_trusted_sections_and_catalogues() -> None:
    job_analysis = _job_analysis()
    profile = _profile()

    rendered = format_assessment_input(job_analysis, profile)

    assert "<JobAnalysis>" in rendered
    assert "<CareerProfile>" in rendered
    assert "<ValidProfileReferences>" in rendered
    assert "<JobEvidenceIndexes>" in rendered
    assert "<ProfileEvidenceCiteGuide>" in rendered
    assert "<FindingFieldGuide>" in rendered
    assert "assumption: forbidden" in rendered
    assert "experience:nbn-data-engineer-2020" in rendered
    assert "project:operational-intelligence-copilot" in rendered
    assert "skill:Python" in rendered
    assert "preference:remote" in rendered
    assert '"role_family"' in rendered
    assert '"posting"' in rendered
    assert "technology[0]:" in rendered
    assert "cite:" in rendered
    assert '"source": "skill"' in rendered[
        rendered.index("<ProfileEvidenceCiteGuide>") : rendered.index(
            "</ProfileEvidenceCiteGuide>"
        )
    ]
    # Catalogue appears before CareerProfile so selectable refs are primary.
    assert rendered.index("<ValidProfileReferences>") < rendered.index("<CareerProfile>")


def test_format_assessment_input_avoids_bare_profile_ids_for_copying() -> None:
    """Live v5/v6 regression: bare CareerProfile ids were copied into profile refs."""
    rendered = format_assessment_input(_job_analysis(), _profile())

    catalogue = rendered[
        rendered.index("<ValidProfileReferences>") : rendered.index("</ValidProfileReferences>")
    ]
    career_profile = rendered[
        rendered.index("<CareerProfile>") : rendered.index("</CareerProfile>")
    ]

    assert "experience:chase-risk-compliance-ai-engineer" in catalogue
    assert "project:operational-intelligence-copilot" in catalogue
    assert "skill:Python" in catalogue
    assert "preference:salary_min" in catalogue
    # Catalogue lists complete tokens only — no annotation tails.
    assert "# kind=" not in catalogue
    assert "# technical" not in catalogue

    assert '"id": "operational-intelligence-copilot"' not in career_profile
    assert '"id": "chase-risk-compliance-ai-engineer"' not in career_profile
    assert '"id": "nbn-data-engineer-2020"' not in career_profile
    assert '"ref": "project:operational-intelligence-copilot"' in career_profile
    assert '"ref": "experience:chase-risk-compliance-ai-engineer"' in career_profile
    assert '"ref": "skill:Python"' in career_profile
    assert '"ref": "preference:salary_min"' in career_profile
    # Preference field names must not appear as bare JSON object keys.
    assert '"salary_min":' not in career_profile
    assert '"salary_currency":' not in career_profile


def test_format_assessment_input_is_deterministic() -> None:
    job_analysis = _job_analysis()
    profile = _profile()

    first = format_assessment_input(job_analysis, profile)
    second = format_assessment_input(job_analysis, profile)

    assert first == second


def test_valid_assessment_returns_payload_without_caller_owned_fields() -> None:
    extraction = OpportunityAssessmentExtraction.model_validate(_valid_extraction_payload())
    assessor, client = _assessor_with(result=_FakeParseResult(output_parsed=extraction))
    job_analysis = _job_analysis()
    profile = _profile()

    payload = assessor.assess(job_analysis, profile)

    assert "job_analysis" not in payload
    assert "profile" not in payload
    assert "career_profile" not in payload
    assert payload["technical_fit"]["judgment"] == "strong"
    assert client.responses.calls[0]["model"] == DEFAULT_MODEL
    assert client.responses.calls[0]["instructions"] == ASSESSMENT_INSTRUCTIONS_V1
    assert client.responses.calls[0]["text_format"] is OpportunityAssessmentExtraction
    assert "<JobAnalysis>" in client.responses.calls[0]["input"]


def test_openai_assessor_calls_responses_parse_with_extraction_schema() -> None:
    extraction = OpportunityAssessmentExtraction.model_validate(_valid_extraction_payload())
    assessor, client = _assessor_with(result=_FakeParseResult(output_parsed=extraction))

    assessor.assess(_job_analysis(), _profile())

    assert len(client.responses.calls) == 1
    assert client.responses.calls[0]["text_format"] is OpportunityAssessmentExtraction


def test_refusal_becomes_opportunity_assessment_error() -> None:
    result = _FakeParseResult(
        output_parsed=None,
        output=[_FakeMessage(content=[_FakeRefusalContent(refusal="Not allowed")])],
    )
    assessor, _ = _assessor_with(result=result)

    with pytest.raises(OpportunityAssessmentError, match="refused") as raised:
        assessor.assess(_job_analysis(), _profile())

    assert not isinstance(raised.value, OpportunityAssessmentValidationError)


def test_empty_response_becomes_opportunity_assessment_error() -> None:
    assessor, _ = _assessor_with(result=_FakeParseResult(output_parsed=None))

    with pytest.raises(OpportunityAssessmentError, match="empty structured assessment"):
        assessor.assess(_job_analysis(), _profile())


def test_malformed_structured_response_becomes_validation_error() -> None:
    assessor, _ = _assessor_with(
        result=_FakeParseResult(
            output_parsed={
                "technical_fit": {
                    "dimension": "technical",
                    "judgment": "not-a-real-judgment",
                    "summary": "Bad judgment.",
                    "findings": [
                        {
                            "kind": "uncertainty",
                            "summary": "Placeholder.",
                            "importance": "minor",
                        }
                    ],
                },
                "commercial_fit": {
                    "dimension": "commercial",
                    "judgment": "unknown",
                    "summary": "Placeholder.",
                    "findings": [
                        {
                            "kind": "uncertainty",
                            "summary": "Placeholder.",
                            "importance": "minor",
                        }
                    ],
                },
                "portfolio_fit": {
                    "dimension": "portfolio",
                    "judgment": "unknown",
                    "summary": "Placeholder.",
                    "findings": [
                        {
                            "kind": "uncertainty",
                            "summary": "Placeholder.",
                            "importance": "minor",
                        }
                    ],
                },
                "summary": {"summary": "Placeholder."},
            }
        )
    )

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        assessor.assess(_job_analysis(), _profile())

    assert raised.value.errors


def test_sdk_exception_becomes_opportunity_assessment_error() -> None:
    assessor, _ = _assessor_with(side_effect=OpenAIError("upstream failure"))

    with pytest.raises(OpportunityAssessmentError, match="OpenAI assessment failed") as raised:
        assessor.assess(_job_analysis(), _profile())

    assert not isinstance(raised.value, OpportunityAssessmentValidationError)


def test_unexpected_programmer_errors_propagate() -> None:
    assessor, _ = _assessor_with(side_effect=RuntimeError("bug in fake client"))

    with pytest.raises(RuntimeError, match="bug in fake client"):
        assessor.assess(_job_analysis(), _profile())


def test_sdk_validation_error_becomes_opportunity_assessment_validation_error() -> None:
    side_effect = ValidationError.from_exception_data(
        "OpportunityAssessmentExtraction",
        [
            {
                "type": "missing",
                "loc": ("summary",),
                "input": {},
            }
        ],
    )
    assessor, _ = _assessor_with(side_effect=side_effect)

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        assessor.assess(_job_analysis(), _profile())

    assert raised.value.errors


def test_configurable_model_is_passed_to_parse() -> None:
    extraction = OpportunityAssessmentExtraction.model_validate(_valid_extraction_payload())
    client = _FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    assessor = OpenAIAssessor(client=client, model="gpt-4o")

    assessor.assess(_job_analysis(), _profile())

    assert client.responses.calls[0]["model"] == "gpt-4o"


def test_alignment_with_empty_job_evidence_fails_through_service() -> None:
    """Live v2 regression: alignment findings omitted job_evidence."""
    payload = dict(assessment_strong_ai_alignment())
    technical = dict(payload["technical_fit"])
    findings = [dict(technical["findings"][0])]
    findings[0]["job_evidence"] = []
    technical["findings"] = findings
    payload["technical_fit"] = technical
    assessor = OpenAIAssessor(
        client=_FakeOpenAI(result=_FakeParseResult(payload))
    )

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        OpportunityAssessmentService(assessor).assess(_job_analysis(), _profile())

    assert any("job evidence" in error.msg.lower() for error in raised.value.errors)


def test_non_assumption_with_assumption_text_fails_through_service() -> None:
    """Live v2 regression: model populated assumption on non-assumption findings."""
    payload = dict(assessment_strong_ai_alignment())
    commercial = dict(payload["commercial_fit"])
    findings = [dict(commercial["findings"][0])]
    findings[0]["assumption"] = "Salary minimum not recorded."
    commercial["findings"] = findings
    payload["commercial_fit"] = commercial
    assessor = OpenAIAssessor(
        client=_FakeOpenAI(result=_FakeParseResult(payload))
    )

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        OpportunityAssessmentService(assessor).assess(_job_analysis(), _profile())

    assert any("assumption" in error.msg.lower() for error in raised.value.errors)


def test_bare_profile_ref_without_namespace_fails_through_service() -> None:
    """Live regression: model emitted bare ids without namespace:id prefix (v1; recurred v5)."""
    payload = dict(assessment_strong_ai_alignment())
    technical = dict(payload["technical_fit"])
    findings = [dict(technical["findings"][0])]
    findings[0]["profile_evidence"] = [
        {"source": "project", "ref": "operational-intelligence-copilot"}
    ]
    technical["findings"] = findings
    payload["technical_fit"] = technical

    with pytest.raises(ValidationError, match="namespace:id") as raised:
        OpportunityAssessmentExtraction.model_validate(payload)

    assert "namespace:id" in str(raised.value)


def test_portfolio_alignment_without_job_evidence_fails_through_service() -> None:
    """Live v4 regression: portfolio_fit findings cited projects without job evidence."""
    payload = dict(assessment_strong_ai_alignment())
    portfolio = dict(payload["portfolio_fit"])
    findings = [dict(portfolio["findings"][0])]
    findings[0]["job_evidence"] = []
    portfolio["findings"] = findings
    payload["portfolio_fit"] = portfolio
    assessor = OpenAIAssessor(
        client=_FakeOpenAI(result=_FakeParseResult(payload))
    )

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        OpportunityAssessmentService(assessor).assess(_job_analysis(), _profile())

    assert any("job evidence" in error.msg.lower() for error in raised.value.errors)


def test_openai_assessor_remains_package_private() -> None:
    assert "OpenAIAssessor" not in opportunity_assessment_api.__all__
    assert not hasattr(opportunity_assessment_api, "OpenAIAssessor")


def test_fake_client_path_works_through_opportunity_assessment_service() -> None:
    extraction = OpportunityAssessmentExtraction.model_validate(_valid_extraction_payload())
    assessor = OpenAIAssessor(
        client=_FakeOpenAI(result=_FakeParseResult(output_parsed=extraction))
    )
    job_analysis = _job_analysis()
    profile = _profile()

    assessment = OpportunityAssessmentService(assessor).assess(job_analysis, profile)

    assert isinstance(assessment, OpportunityAssessment)
    assert assessment.job_analysis is job_analysis
    assert assessment.technical_fit.judgment == "strong"
