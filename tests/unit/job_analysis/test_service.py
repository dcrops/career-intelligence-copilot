"""Unit tests for JobAnalysisService trust-boundary behaviour."""

from __future__ import annotations

import pytest
from career_intelligence.job_analysis import (
    JobAnalysis,
    JobAnalysisError,
    JobAnalysisService,
    JobAnalysisValidationError,
    JobPosting,
)
from career_intelligence.job_analysis.extractor import JobAnalysisPayload
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    analysis_for_ai_engineer,
    posting_ai_engineer,
)


def _fixture_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


class _StaticPayloadExtractor:
    def __init__(self, payload: JobAnalysisPayload) -> None:
        self._payload = payload

    def extract(self, posting: JobPosting) -> JobAnalysisPayload:
        return self._payload


class _FailingExtractor:
    def extract(self, posting: JobPosting) -> JobAnalysisPayload:
        raise JobAnalysisError("extractor failed")


def _minimal_valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "role_family": {"family": "unknown"},
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [],
        "responsibilities": [],
        "compensation": {"clarity": "unstated"},
        "location": {"clarity": "unstated"},
        "work_arrangement": {"arrangement": "unspecified"},
        "employment": {},
        "experience_requirements": [],
    }
    payload.update(overrides)
    return payload


def test_service_requires_an_extractor() -> None:
    with pytest.raises(TypeError):
        JobAnalysisService()  # type: ignore[call-arg]


def test_fixture_extractor_can_be_passed_explicitly() -> None:
    analysis = _fixture_service().analyse(posting_ai_engineer())
    assert analysis.role_family.family == "ai_engineering"


def test_valid_payload_becomes_trusted_job_analysis() -> None:
    posting = posting_ai_engineer()
    service = JobAnalysisService(_StaticPayloadExtractor(analysis_for_ai_engineer()))

    analysis = service.analyse(posting)

    assert isinstance(analysis, JobAnalysis)
    assert analysis.role_family.family == "ai_engineering"
    assert analysis.seniority.level == "senior"


def test_returned_analysis_contains_exact_original_posting() -> None:
    posting = posting_ai_engineer()
    analysis = _fixture_service().analyse(posting)

    assert analysis.posting is posting
    assert analysis.posting == posting


def test_missing_identity_enriched_from_grounded_extraction() -> None:
    raw = (
        "Maincode\n\nAI Infrastructure Engineer\n\n"
        "About Maincode\nMaincode is an AI research company."
    )
    posting = JobPosting(raw_text=raw)
    payload = _minimal_valid_payload(
        posting_identity={
            "title": "AI Infrastructure Engineer",
            "company": "Maincode",
            "title_evidence": [
                {"excerpt": "AI Infrastructure Engineer", "section": "Job title"}
            ],
            "company_evidence": [{"excerpt": "Maincode", "section": "Company"}],
        }
    )
    analysis = JobAnalysisService(_StaticPayloadExtractor(payload)).analyse(posting)

    assert analysis.posting is not posting
    assert analysis.posting.title == "AI Infrastructure Engineer"
    assert analysis.posting.company == "Maincode"
    assert analysis.posting.raw_text == raw


def test_caller_supplied_identity_not_overwritten() -> None:
    posting = JobPosting(
        raw_text="Maincode\n\nAI Infrastructure Engineer\n",
        title="Caller Title",
        company="Caller Co",
    )
    payload = _minimal_valid_payload(
        posting_identity={
            "title": "AI Infrastructure Engineer",
            "company": "Maincode",
            "title_evidence": [
                {"excerpt": "AI Infrastructure Engineer", "section": "Job title"}
            ],
            "company_evidence": [{"excerpt": "Maincode", "section": "Company"}],
        }
    )
    analysis = JobAnalysisService(_StaticPayloadExtractor(payload)).analyse(posting)

    assert analysis.posting is posting
    assert analysis.posting.title == "Caller Title"
    assert analysis.posting.company == "Caller Co"


def test_ungrounded_extracted_identity_is_dropped() -> None:
    posting = JobPosting(raw_text="A posting with no explicit employer heading.")
    payload = _minimal_valid_payload(
        posting_identity={
            "title": "Invented Role",
            "company": "Invented Co",
            "title_evidence": [{"excerpt": "Invented Role", "section": "Job title"}],
            "company_evidence": [{"excerpt": "Invented Co", "section": "Company"}],
        }
    )
    analysis = JobAnalysisService(_StaticPayloadExtractor(payload)).analyse(posting)

    assert analysis.posting.title is None
    assert analysis.posting.company is None


def test_extractor_payload_cannot_replace_input_posting() -> None:
    caller_posting = posting_ai_engineer()
    other_posting = JobPosting(
        title="Other Role",
        company="Other Co",
        raw_text="Unrelated posting text that must not appear in the result.",
    )
    payload = dict(analysis_for_ai_engineer())
    payload["posting"] = other_posting.model_dump(mode="python")
    service = JobAnalysisService(_StaticPayloadExtractor(payload))

    with pytest.raises(JobAnalysisValidationError) as raised:
        service.analyse(caller_posting)

    assert any(error.loc == ("posting",) for error in raised.value.errors)
    assert "must not include 'posting'" in raised.value.errors[0].msg


def test_extractor_payload_containing_posting_is_rejected() -> None:
    payload = _minimal_valid_payload(
        posting={
            "raw_text": "Extractor-supplied posting that should be rejected.",
            "title": "Injected",
        }
    )
    service = JobAnalysisService(_StaticPayloadExtractor(payload))

    with pytest.raises(JobAnalysisValidationError, match="validation failed") as raised:
        service.analyse(posting_ai_engineer())

    assert any("must not include 'posting'" in error.msg for error in raised.value.errors)


def test_schema_invalid_mapping_becomes_validation_error() -> None:
    payload = _minimal_valid_payload(role_family={"family": "not_a_real_family"})
    service = JobAnalysisService(_StaticPayloadExtractor(payload))

    with pytest.raises(JobAnalysisValidationError) as raised:
        service.analyse(posting_ai_engineer())

    assert raised.value.errors
    assert isinstance(raised.value, JobAnalysisError)


def test_missing_required_payload_fields_become_validation_error() -> None:
    payload = {
        "role_family": {"family": "unknown"},
        # seniority and compensation omitted — required by JobAnalysis
    }
    service = JobAnalysisService(_StaticPayloadExtractor(payload))

    with pytest.raises(JobAnalysisValidationError) as raised:
        service.analyse(posting_ai_engineer())

    locs = {error.loc[0] for error in raised.value.errors if error.loc}
    assert "seniority" in locs or "compensation" in locs or "work_arrangement" in locs


def test_nested_evidence_validation_failures_become_validation_error() -> None:
    payload = _minimal_valid_payload(
        role_family={"family": "ai_engineering"},  # known family without evidence
    )
    service = JobAnalysisService(_StaticPayloadExtractor(payload))

    with pytest.raises(JobAnalysisValidationError) as raised:
        service.analyse(posting_ai_engineer())

    assert any("evidence" in error.msg.lower() for error in raised.value.errors)


def test_service_propagates_extractor_job_analysis_error() -> None:
    service = JobAnalysisService(_FailingExtractor())

    with pytest.raises(JobAnalysisError, match="extractor failed") as raised:
        service.analyse(posting_ai_engineer())

    assert not isinstance(raised.value, JobAnalysisValidationError)
