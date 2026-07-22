"""Functional acceptance tests for FR-003 Opportunity Assessment (public service boundary)."""

from __future__ import annotations

from pathlib import Path

import career_intelligence.opportunity_assessment as opportunity_assessment_api
import pytest
from career_intelligence.job_analysis import JobAnalysis, JobAnalysisService
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_ambiguous_seniority,
    posting_applied_ai_engineer,
    posting_contract,
    posting_data_engineer,
    posting_missing_salary,
    posting_no_technologies,
    posting_working_rights,
)
from career_intelligence.opportunity_assessment import (
    OpportunityAssessment,
    OpportunityAssessmentError,
    OpportunityAssessmentService,
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.assessor import OpportunityAssessmentPayload
from career_intelligence.opportunity_assessment.fixture_assessor import FixtureAssessor
from career_intelligence.opportunity_assessment.fixtures import (
    assessment_production_ai_required,
    assessment_strong_ai_alignment,
)
from career_intelligence.profile import CareerProfile, CareerProfileService

_FORBIDDEN_OUTPUT_FIELD_NAMES = frozenset(
    {
        "tier",
        "platinum",
        "gold",
        "silver",
        "skip",
        "apply",
        "defer",
        "effort",
        "quota",
        "application_target",
        "interview_probability",
        "percentage",
        "score",
    }
)


def _collect_field_names(value: object) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            names.add(str(key).lower())
            names |= _collect_field_names(nested)
    elif isinstance(value, list):
        for item in value:
            names |= _collect_field_names(item)
    return names


def _job_analysis_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def _fixture_assessment_service() -> OpportunityAssessmentService:
    return OpportunityAssessmentService(FixtureAssessor())


def _golden_profile(golden_profile_path: Path) -> CareerProfile:
    return CareerProfileService.from_path(golden_profile_path).load()


def _analyse(posting_builder: object) -> JobAnalysis:
    return _job_analysis_service().analyse(posting_builder())  # type: ignore[operator]


class _StaticPayloadAssessor:
    def __init__(self, payload: OpportunityAssessmentPayload) -> None:
        self._payload = payload

    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessmentPayload:
        _ = job_analysis, profile
        return self._payload


class _FailingAssessor:
    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessmentPayload:
        _ = job_analysis, profile
        raise OpportunityAssessmentError("assessor failed")


def _assert_complete_assessment(assessment: OpportunityAssessment) -> None:
    assert isinstance(assessment, OpportunityAssessment)
    for dimension in (
        assessment.technical_fit,
        assessment.commercial_fit,
        assessment.portfolio_fit,
    ):
        assert dimension.judgment
        assert dimension.findings
        assert dimension.summary
    assert assessment.summary.summary


def _assert_no_forbidden_output_fields(assessment: OpportunityAssessment) -> None:
    field_names = _collect_field_names(assessment.model_dump(mode="json"))
    forbidden_present = field_names & _FORBIDDEN_OUTPUT_FIELD_NAMES
    assert not forbidden_present, f"forbidden fields present: {sorted(forbidden_present)}"


def test_valid_assessment_returns_complete_opportunity_assessment(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    _assert_complete_assessment(assessment)
    _assert_no_forbidden_output_fields(assessment)


def test_caller_owned_job_analysis_is_bound(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    assert assessment.job_analysis is job_analysis


@pytest.mark.parametrize("embedded_key", ["job_analysis", "profile", "career_profile"])
def test_embedded_caller_inputs_in_assessor_payload_are_rejected(
    golden_profile_path: Path,
    embedded_key: str,
) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    payload = dict(assessment_strong_ai_alignment())
    payload[embedded_key] = {"injected": True}
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(job_analysis, profile)

    assert any(error.loc == (embedded_key,) for error in raised.value.errors)
    assert "must not include" in raised.value.errors[0].msg


def test_alignment_findings_require_job_and_profile_evidence(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    alignment_findings = [
        finding
        for dimension in (
            assessment.technical_fit,
            assessment.commercial_fit,
            assessment.portfolio_fit,
        )
        for finding in dimension.findings
        if finding.kind == "alignment"
    ]
    assert alignment_findings
    assert all(finding.job_evidence and finding.profile_evidence for finding in alignment_findings)


def test_alignment_without_profile_evidence_is_rejected(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    payload = dict(assessment_strong_ai_alignment())
    technical = dict(payload["technical_fit"])  # type: ignore[arg-type]
    findings = [dict(technical["findings"][0])]  # type: ignore[index]
    findings[0]["profile_evidence"] = []
    technical["findings"] = findings
    payload["technical_fit"] = technical
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(job_analysis, profile)

    assert any("profile evidence" in error.msg.lower() for error in raised.value.errors)


def test_invalid_profile_reference_is_rejected(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    payload = dict(assessment_production_ai_required())
    technical = dict(payload["technical_fit"])  # type: ignore[arg-type]
    findings = [dict(technical["findings"][0])]  # type: ignore[index]
    findings[0]["profile_evidence"] = [{"source": "project", "ref": "project:nonexistent-id"}]
    technical["findings"] = findings
    payload["technical_fit"] = technical
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(job_analysis, profile)

    assert any(
        error.loc[-1] == "ref" and "nonexistent-id" in error.msg for error in raised.value.errors
    )


@pytest.mark.parametrize("item_index", [99, 5])
def test_out_of_range_technology_index_is_rejected(
    golden_profile_path: Path,
    item_index: int,
) -> None:
    job_analysis = _analyse(posting_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    payload = dict(assessment_production_ai_required())
    technical = dict(payload["technical_fit"])  # type: ignore[arg-type]
    findings = [dict(technical["findings"][0])]  # type: ignore[index]
    findings[0]["job_evidence"] = [
        {"source": "technology", "item_index": item_index, "name": "Python"}
    ]
    technical["findings"] = findings
    payload["technical_fit"] = technical
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(job_analysis, profile)

    assert any("out of range" in error.msg for error in raised.value.errors)


def test_scalar_job_evidence_without_item_index_is_accepted(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    scalar_sources = {
        ref.source
        for dimension in (
            assessment.technical_fit,
            assessment.commercial_fit,
            assessment.portfolio_fit,
        )
        for finding in dimension.findings
        for ref in finding.job_evidence
        if ref.item_index is None
    }
    assert "role_family" in scalar_sources or "compensation" in scalar_sources


def test_independent_engineering_honesty_for_production_ai_scenario(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_ai_engineer)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    partial_findings = [
        finding
        for finding in assessment.technical_fit.findings
        if finding.kind == "partial_alignment"
    ]
    gap_findings = [
        finding for finding in assessment.technical_fit.findings if finding.kind == "gap"
    ]
    assert partial_findings
    assert gap_findings
    assert any(
        ref.ref == "experience:chase-risk-compliance-ai-engineer"
        for finding in partial_findings
        for ref in finding.profile_evidence
    )
    assert not any(
        finding.kind == "alignment"
        and any(
            ref.ref == "experience:chase-risk-compliance-ai-engineer"
            for ref in finding.profile_evidence
        )
        for finding in assessment.technical_fit.findings
    )
    limitation_text = " ".join(finding.summary.lower() for finding in gap_findings)
    assert "commercial" in limitation_text
    assert "independent" in limitation_text or "not equivalent" in limitation_text


def test_no_named_technologies_scenario_avoids_fabricated_tech_findings(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_no_technologies)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    _assert_complete_assessment(assessment)
    assert job_analysis.technologies == []
    assert assessment.technical_fit.judgment == "unknown"
    assert any(
        finding.kind == "uncertainty" for finding in assessment.technical_fit.findings
    )
    assert not any(
        finding.kind in {"alignment", "gap"}
        and any(ref.source == "technology" for ref in finding.job_evidence)
        for finding in assessment.technical_fit.findings
    )


def test_ambiguous_seniority_scenario_preserves_uncertainty(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_ambiguous_seniority)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    _assert_complete_assessment(assessment)
    assert job_analysis.seniority.ambiguous is True
    assert any(
        finding.kind == "uncertainty"
        and any(ref.source == "seniority" for ref in finding.job_evidence)
        for finding in assessment.technical_fit.findings
    )
    assert not any(
        finding.kind == "alignment"
        and any(ref.source == "seniority" for ref in finding.job_evidence)
        for finding in assessment.technical_fit.findings
    )


def test_salary_unstated_scenario_avoids_fabricated_compensation_conflict(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_missing_salary)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    assert job_analysis.compensation.clarity == "unstated"
    assert profile.preferences.salary_min is None
    commercial_findings = assessment.commercial_fit.findings
    assert any(finding.kind in {"uncertainty", "assumption"} for finding in commercial_findings)
    assert not any(finding.kind == "conflict" for finding in commercial_findings)
    assert not any(
        finding.kind == "alignment"
        and any(ref.source == "compensation" for ref in finding.job_evidence)
        for finding in commercial_findings
    )


def test_working_rights_requirement_does_not_infer_candidate_eligibility(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_working_rights)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    rights_findings = [
        finding
        for finding in assessment.commercial_fit.findings
        if any(ref.source == "experience_requirement" for ref in finding.job_evidence)
    ]
    assert rights_findings
    assert all(not finding.profile_evidence for finding in rights_findings)
    assert all(finding.kind == "uncertainty" for finding in rights_findings)


def test_commercial_preference_handling_uses_actual_profile_preferences(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_contract)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    assert profile.preferences.deal_breakers == []
    assert profile.preferences.remote == "flexible"
    conflict_findings = [
        finding
        for finding in assessment.commercial_fit.findings
        if finding.kind == "conflict"
    ]
    assert conflict_findings
    assert all(
        any(ref.source == "preference" for ref in finding.profile_evidence)
        for finding in conflict_findings
    )
    assert not any("deal-breaker" in finding.summary.lower() for finding in conflict_findings)
    assert not any("deal_breaker" in finding.summary.lower() for finding in conflict_findings)


def test_broad_data_engineering_scenario_reports_mixed_fit_without_recommendation(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_data_engineer)
    profile = _golden_profile(golden_profile_path)

    assessment = _fixture_assessment_service().assess(job_analysis, profile)

    assert assessment.technical_fit.judgment in {"mixed", "weak"}
    assert any(
        finding.kind == "transferable_alignment"
        for finding in assessment.technical_fit.findings
    )
    assert any(finding.kind == "gap" for finding in assessment.technical_fit.findings)
    _assert_no_forbidden_output_fields(assessment)


def test_inputs_are_not_mutated(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    before_job = job_analysis.model_dump(mode="json")
    before_profile = profile.model_dump(mode="json")

    _fixture_assessment_service().assess(job_analysis, profile)

    assert job_analysis.model_dump(mode="json") == before_job
    assert profile.model_dump(mode="json") == before_profile


def test_repeated_assessment_is_deterministic(golden_profile_path: Path) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    service = _fixture_assessment_service()

    first = service.assess(job_analysis, profile).model_dump(mode="json")
    second = service.assess(job_analysis, profile).model_dump(mode="json")

    assert first == second


def test_schema_validation_failures_raise_validation_error(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    payload = dict(assessment_strong_ai_alignment())
    technical = dict(payload["technical_fit"])  # type: ignore[arg-type]
    technical["judgment"] = "not-a-real-judgment"
    payload["technical_fit"] = technical
    service = OpportunityAssessmentService(_StaticPayloadAssessor(payload))

    with pytest.raises(OpportunityAssessmentValidationError) as raised:
        service.assess(job_analysis, profile)

    assert raised.value.errors
    assert isinstance(raised.value, OpportunityAssessmentError)


def test_assessor_failures_raise_base_opportunity_assessment_error(
    golden_profile_path: Path,
) -> None:
    job_analysis = _analyse(posting_applied_ai_engineer)
    profile = _golden_profile(golden_profile_path)
    service = OpportunityAssessmentService(_FailingAssessor())

    with pytest.raises(OpportunityAssessmentError, match="assessor failed") as raised:
        service.assess(job_analysis, profile)

    assert not isinstance(raised.value, OpportunityAssessmentValidationError)


def test_public_api_exports_service_and_errors_not_assessors() -> None:
    assert "OpportunityAssessmentService" in opportunity_assessment_api.__all__
    assert "OpportunityAssessmentError" in opportunity_assessment_api.__all__
    assert "OpportunityAssessmentValidationError" in opportunity_assessment_api.__all__
    assert "FixtureAssessor" not in opportunity_assessment_api.__all__
    assert "Assessor" not in opportunity_assessment_api.__all__
    assert not hasattr(opportunity_assessment_api, "FixtureAssessor")
    assert not hasattr(opportunity_assessment_api, "Assessor")


def test_public_api_does_not_expose_fixture_module() -> None:
    assert "fixtures" not in opportunity_assessment_api.__all__
    assert not hasattr(opportunity_assessment_api, "ASSESSMENT_FIXTURE_BUILDERS")


def test_downstream_modules_do_not_import_internal_assessors() -> None:
    source_root = Path(__file__).parents[2] / "src" / "career_intelligence"
    allowed_by_name = {
        "assessor.py",
        "assessment_prompt.py",
        "extraction.py",
        "fixture_assessor.py",
        "fixtures.py",
        "openai_assessor.py",
    }

    for source_file in source_root.rglob("*.py"):
        if source_file.name in allowed_by_name:
            continue
        text = source_file.read_text(encoding="utf-8")
        assert "opportunity_assessment.fixture_assessor" not in text
        assert "opportunity_assessment.fixtures" not in text
        if source_file.name != "service.py":
            assert "opportunity_assessment.assessor" not in text
