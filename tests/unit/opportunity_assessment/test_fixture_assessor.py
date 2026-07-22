"""Unit tests for FixtureAssessor and deterministic assessment fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from career_intelligence.job_analysis import JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER,
    MARKER_NO_TECHNOLOGIES,
    MARKER_WORKING_RIGHTS,
    posting_ai_engineer,
    posting_ambiguous_seniority,
    posting_applied_ai_engineer,
    posting_contract,
    posting_data_engineer,
    posting_missing_salary,
    posting_no_technologies,
    posting_working_rights,
)
from career_intelligence.opportunity_assessment import OpportunityAssessment, OpportunityAssessmentService
from career_intelligence.opportunity_assessment.errors import OpportunityAssessmentError
from career_intelligence.opportunity_assessment.fixture_assessor import FixtureAssessor
from career_intelligence.opportunity_assessment.fixtures import (
    ASSESSMENT_FIXTURE_BUILDERS,
    assessment_production_ai_required,
    assessment_strong_ai_alignment,
)
from career_intelligence.profile import CareerProfile, CareerProfileService


def _golden_profile() -> CareerProfile:
    path = Path(__file__).parents[2] / "fixtures" / "golden" / "career_profile.yaml"
    return CareerProfileService.from_path(path).load()


def _fixture_assessment_service() -> OpportunityAssessmentService:
    return OpportunityAssessmentService(FixtureAssessor())


def _job_analysis_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def test_all_assessment_fixture_builders_return_serialisable_payloads() -> None:
    for marker, builder in ASSESSMENT_FIXTURE_BUILDERS.items():
        payload = builder()
        assert isinstance(payload, dict)
        assert "job_analysis" not in payload
        assert "profile" not in payload
        assert "career_profile" not in payload
        assert "technical_fit" in payload
        assert "commercial_fit" in payload
        assert "portfolio_fit" in payload
        assert "summary" in payload
        dumped = dict(payload)
        assert marker  # marker exists for documentation parity


def test_fixture_selection_is_deterministic_for_applied_ai_marker() -> None:
    assessor = FixtureAssessor()
    first = assessor.assess(
        _job_analysis_service().analyse(posting_applied_ai_engineer()),
        _golden_profile(),
    )
    second = assessor.assess(
        _job_analysis_service().analyse(posting_applied_ai_engineer()),
        _golden_profile(),
    )

    assert first == second
    assert first == assessment_strong_ai_alignment()


def test_unknown_marker_raises_clear_error() -> None:
    from career_intelligence.job_analysis.models import JobAnalysis, JobPosting

    job_analysis = JobAnalysis.model_validate(
        {
            "posting": JobPosting(raw_text="No fixture marker present.").model_dump(mode="python"),
            "role_family": {"family": "unknown"},
            "seniority": {"level": "unknown", "ambiguous": False},
            "technologies": [],
            "responsibilities": [],
            "compensation": {"clarity": "unstated"},
            "work_arrangement": {"arrangement": "unspecified"},
        }
    )

    with pytest.raises(OpportunityAssessmentError, match="No fixture assessment"):
        FixtureAssessor().assess(job_analysis, _golden_profile())


def test_service_wires_fixture_assessor_for_production_ai_scenario() -> None:
    job_analysis = _job_analysis_service().analyse(posting_ai_engineer())
    profile = _golden_profile()

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    assert isinstance(assessment, OpportunityAssessment)
    assert assessment.job_analysis is job_analysis
    assert assessment.technical_fit.judgment == "mixed"
    assert assessment.technical_fit.findings[1].kind == "partial_alignment"
    assert assessment.technical_fit.findings[2].kind == "gap"
    assert "independent engineering" in assessment.technical_fit.findings[2].summary.lower()
    assert "commercial" in assessment.technical_fit.findings[2].summary.lower()


def test_strong_alignment_scenario_through_service() -> None:
    assessment = _fixture_assessment_service().assess(
        _job_analysis_service().analyse(posting_applied_ai_engineer()),
        _golden_profile(),
    )

    assert assessment.technical_fit.judgment == "strong"
    assert assessment.portfolio_fit.judgment == "strong"
    assert all(
        ref.ref != "experience:chase-risk-compliance-ai-engineer"
        or "independent" in finding.summary.lower()
        for dimension in (
            assessment.technical_fit,
            assessment.commercial_fit,
            assessment.portfolio_fit,
        )
        for finding in dimension.findings
        for ref in finding.profile_evidence
        if ref.source == "experience"
    )


def test_no_named_technologies_scenario_has_uncertainty_not_invented_gaps() -> None:
    job_analysis = _job_analysis_service().analyse(posting_no_technologies())
    assessment = _fixture_assessment_service().assess(job_analysis, _golden_profile())

    assert MARKER_NO_TECHNOLOGIES in job_analysis.posting.raw_text
    assert assessment.technical_fit.judgment == "unknown"
    assert any(finding.kind == "uncertainty" for finding in assessment.technical_fit.findings)
    assert not any(finding.kind == "gap" for finding in assessment.technical_fit.findings)


def test_ambiguous_seniority_scenario_preserves_uncertainty() -> None:
    assessment = _fixture_assessment_service().assess(
        _job_analysis_service().analyse(posting_ambiguous_seniority()),
        _golden_profile(),
    )

    assert any(
        finding.kind == "uncertainty" and "seniority" in finding.summary.lower()
        for finding in assessment.technical_fit.findings
    )


def test_onsite_contract_scenario_without_invented_deal_breaker() -> None:
    assessment = _fixture_assessment_service().assess(
        _job_analysis_service().analyse(posting_contract()),
        _golden_profile(),
    )

    assert assessment.commercial_fit.judgment == "mixed"
    assert any(finding.kind == "conflict" for finding in assessment.commercial_fit.findings)
    dumped = assessment.model_dump(mode="json")
    assert "deal_breaker" not in str(dumped).lower()


def test_salary_unstated_scenario_is_honest() -> None:
    assessment = _fixture_assessment_service().assess(
        _job_analysis_service().analyse(posting_missing_salary()),
        _golden_profile(),
    )

    assert assessment.commercial_fit.judgment == "unknown"
    assert any(
        finding.kind == "uncertainty" and finding.job_evidence
        for finding in assessment.commercial_fit.findings
    )
    assert not any(
        finding.kind == "conflict" and "salary" in finding.summary.lower()
        for finding in assessment.commercial_fit.findings
    )


def test_working_rights_scenario_does_not_infer_eligibility() -> None:
    assessment = _fixture_assessment_service().assess(
        _job_analysis_service().analyse(posting_working_rights()),
        _golden_profile(),
    )

    assert MARKER_WORKING_RIGHTS in assessment.job_analysis.posting.raw_text
    assert assessment.commercial_fit.judgment == "unknown"
    working_rights_findings = [
        finding
        for finding in assessment.commercial_fit.findings
        if "working-rights" in finding.summary.lower()
        or "working rights" in finding.summary.lower()
    ]
    assert working_rights_findings
    assert all(not finding.profile_evidence for finding in working_rights_findings)


def test_broad_developer_mixed_scenario() -> None:
    assessment = _fixture_assessment_service().assess(
        _job_analysis_service().analyse(posting_data_engineer()),
        _golden_profile(),
    )

    assert assessment.technical_fit.judgment == "mixed"
    assert any(finding.kind == "transferable_alignment" for finding in assessment.technical_fit.findings)
    assert any(finding.kind == "gap" for finding in assessment.technical_fit.findings)


def test_fixture_output_has_no_forbidden_tier_or_quota_fields() -> None:
    assessment = _fixture_assessment_service().assess(
        _job_analysis_service().analyse(posting_ai_engineer()),
        _golden_profile(),
    )
    dumped = assessment.model_dump(mode="json")

    forbidden = (
        "tier",
        "platinum",
        "gold",
        "silver",
        "skip",
        "apply",
        "quota",
        "obligation",
        "effort",
        "interview_probability",
    )
    serialised = str(dumped).lower()
    for token in forbidden:
        assert token not in serialised


def test_independent_engineering_not_described_as_commercial_employment() -> None:
    assessment = _fixture_assessment_service().assess(
        _job_analysis_service().analyse(posting_ai_engineer()),
        _golden_profile(),
    )

    for finding in assessment.technical_fit.findings:
        if any(
            ref.ref == "experience:chase-risk-compliance-ai-engineer"
            for ref in finding.profile_evidence
        ):
            assert "independent" in finding.summary.lower()
            assert "commercial" in finding.summary.lower() or "not equivalent" in finding.summary.lower()


def test_invalid_profile_reference_in_fixture_payload_is_rejected_by_service() -> None:
    class _BadReferenceAssessor:
        def assess(self, job_analysis, profile):
            _ = job_analysis, profile
            payload = dict(assessment_production_ai_required())
            technical = dict(payload["technical_fit"])
            findings = list(technical["findings"])
            findings[0] = dict(findings[0])
            findings[0]["profile_evidence"] = [
                {"source": "project", "ref": "project:does-not-exist"}
            ]
            technical["findings"] = findings
            payload["technical_fit"] = technical
            return payload

    with pytest.raises(OpportunityAssessmentError):
        OpportunityAssessmentService(_BadReferenceAssessor()).assess(
            _job_analysis_service().analyse(posting_ai_engineer()),
            _golden_profile(),
        )


def test_chained_fr002_extraction_to_fr003_assessment_for_ai_engineer() -> None:
    posting = posting_ai_engineer()
    assert MARKER_AI_ENGINEER in posting.raw_text

    job_analysis = _job_analysis_service().analyse(posting)
    assessment = _fixture_assessment_service().assess(job_analysis, _golden_profile())

    assert assessment.job_analysis is job_analysis
    assert assessment == _fixture_assessment_service().assess(job_analysis, _golden_profile())


def test_stable_serialisation_through_service() -> None:
    job_analysis = _job_analysis_service().analyse(posting_applied_ai_engineer())
    profile = _golden_profile()
    service = _fixture_assessment_service()

    first = service.assess(job_analysis, profile).model_dump(mode="json")
    second = service.assess(job_analysis, profile).model_dump(mode="json")

    assert first == second
