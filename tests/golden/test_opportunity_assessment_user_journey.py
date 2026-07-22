"""Golden journeys: CareerProfile → JobAnalysis → OpportunityAssessment (offline).

Proves FR-001 / FR-002 / FR-003 service composition through real public boundaries
with deterministic fixture extractors and assessors. Not a duplicate of the FR-003
functional acceptance suite.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from career_intelligence.job_analysis import JobAnalysis, JobAnalysisService, JobPosting
from career_intelligence.job_analysis.fixture_extractor import FixtureExtractor
from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER,
    MARKER_APPLIED_AI,
    MARKER_DATA_ENGINEER,
    MARKER_NO_TECHNOLOGIES,
    MARKER_WORKING_RIGHTS,
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_data_engineer,
    posting_no_technologies,
    posting_working_rights,
)
from career_intelligence.opportunity_assessment import (
    OpportunityAssessment,
    OpportunityAssessmentService,
)
from career_intelligence.opportunity_assessment.fixture_assessor import FixtureAssessor
from career_intelligence.profile import CareerProfile, CareerProfileService

_FORBIDDEN_FIELD_NAMES = frozenset(
    {
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
        "jobseeker",
    }
)


def _golden_profile(golden_profile_path: Path) -> CareerProfile:
    return CareerProfileService.from_path(golden_profile_path).load()


def _job_analysis_service() -> JobAnalysisService:
    return JobAnalysisService(FixtureExtractor())


def _assessment_service() -> OpportunityAssessmentService:
    return OpportunityAssessmentService(FixtureAssessor())


def _run_journey(
    posting: JobPosting,
    profile: CareerProfile,
) -> tuple[JobAnalysis, OpportunityAssessment]:
    job_analysis = _job_analysis_service().analyse(posting)
    assessment = _assessment_service().assess(job_analysis, profile)
    return job_analysis, assessment


def _assert_complete_assessment(
    assessment: OpportunityAssessment,
    *,
    job_analysis: JobAnalysis,
) -> None:
    assert isinstance(assessment, OpportunityAssessment)
    assert assessment.job_analysis is job_analysis
    assert assessment.technical_fit.dimension == "technical"
    assert assessment.commercial_fit.dimension == "commercial"
    assert assessment.portfolio_fit.dimension == "portfolio"
    assert assessment.technical_fit.findings
    assert assessment.commercial_fit.findings
    assert assessment.portfolio_fit.findings
    assert assessment.summary.summary

    dumped = assessment.model_dump(mode="json")
    serialised = str(dumped).lower()
    for token in _FORBIDDEN_FIELD_NAMES:
        assert token not in serialised
    assert "job_analysis" in dumped
    assert "profile" not in dumped
    assert "career_profile" not in dumped


def test_profile_loads_through_career_profile_service(golden_profile_path: Path) -> None:
    profile = _golden_profile(golden_profile_path)

    assert isinstance(profile, CareerProfile)
    assert profile.identity.target_role
    assert profile.skills.technical
    assert any(entry.kind == "independent_engineering" for entry in profile.experience)
    assert profile.projects


def test_strong_ai_engineering_alignment_journey(golden_profile_path: Path) -> None:
    """Applied AI Engineer: Profile → JobAnalysis → OpportunityAssessment."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_applied_ai_engineer()
    assert MARKER_APPLIED_AI in posting.raw_text

    job_analysis, assessment = _run_journey(posting, profile)

    assert isinstance(job_analysis, JobAnalysis)
    assert job_analysis.posting is posting
    assert job_analysis.role_family.family == "ai_engineering"
    assert {tech.name for tech in job_analysis.technologies} >= {"Python", "FastAPI"}

    _assert_complete_assessment(assessment, job_analysis=job_analysis)
    assert assessment.technical_fit.judgment == "strong"
    assert assessment.portfolio_fit.judgment == "strong"
    assert any(
        finding.kind == "alignment" and finding.job_evidence and finding.profile_evidence
        for finding in assessment.technical_fit.findings
    )

    second = _assessment_service().assess(job_analysis, profile)
    assert second.model_dump(mode="json") == assessment.model_dump(mode="json")


def test_production_ai_independent_engineering_not_commercial_employment(
    golden_profile_path: Path,
) -> None:
    """Production AI required: portfolio/independent evidence recognised, not employment."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_ai_engineer()
    assert MARKER_AI_ENGINEER in posting.raw_text

    job_analysis, assessment = _run_journey(posting, profile)

    assert job_analysis.role_family.family == "ai_engineering"
    assert job_analysis.seniority.level == "senior"
    assert any(
        "production" in req.description.lower() or "rag" in req.description.lower()
        for req in job_analysis.experience_requirements
    )

    _assert_complete_assessment(assessment, job_analysis=job_analysis)
    assert assessment.technical_fit.judgment == "mixed"

    partial = [
        finding
        for finding in assessment.technical_fit.findings
        if finding.kind == "partial_alignment"
    ]
    gaps = [finding for finding in assessment.technical_fit.findings if finding.kind == "gap"]
    assert partial
    assert gaps

    chase_refs = [
        finding
        for finding in assessment.technical_fit.findings
        if any(
            ref.ref == "experience:chase-risk-compliance-ai-engineer"
            for ref in finding.profile_evidence
        )
    ]
    assert chase_refs
    for finding in chase_refs:
        text = finding.summary.lower()
        assert "independent" in text
        assert "commercial" in text or "not equivalent" in text
        assert finding.kind != "alignment" or "not" in text

    gap_text = " ".join(finding.summary.lower() for finding in gaps)
    assert "commercial" in gap_text
    assert "independent" in gap_text or "not equivalent" in gap_text


def test_no_named_technologies_remain_uncertainty(golden_profile_path: Path) -> None:
    """Empty technology list → uncertainty; no invented technology gaps."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_no_technologies()
    assert MARKER_NO_TECHNOLOGIES in posting.raw_text

    job_analysis, assessment = _run_journey(posting, profile)

    assert job_analysis.technologies == []
    assert job_analysis.role_family.family == "ai_engineering"

    _assert_complete_assessment(assessment, job_analysis=job_analysis)
    assert assessment.technical_fit.judgment == "unknown"
    assert any(finding.kind == "uncertainty" for finding in assessment.technical_fit.findings)
    assert not any(
        finding.kind in {"alignment", "gap", "conflict"}
        and any(ref.source == "technology" for ref in finding.job_evidence)
        for finding in assessment.technical_fit.findings
    )


def test_working_rights_not_inferred_from_profile(golden_profile_path: Path) -> None:
    """Working-rights requirement is job-side only; no candidate eligibility inference."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_working_rights()
    assert MARKER_WORKING_RIGHTS in posting.raw_text

    job_analysis, assessment = _run_journey(posting, profile)

    assert any(
        "working rights" in req.description.lower()
        for req in job_analysis.experience_requirements
    )

    _assert_complete_assessment(assessment, job_analysis=job_analysis)
    assert assessment.commercial_fit.judgment == "unknown"

    working_rights_findings = [
        finding
        for finding in assessment.commercial_fit.findings
        if "working-rights" in finding.summary.lower()
        or "working rights" in finding.summary.lower()
    ]
    assert working_rights_findings
    assert all(finding.job_evidence for finding in working_rights_findings)
    assert all(not finding.profile_evidence for finding in working_rights_findings)

    serialised = assessment.model_dump(mode="json")
    commercial_text = str(serialised["commercial_fit"]).lower()
    assert "eligible" not in commercial_text
    assert "citizenship" not in commercial_text


def test_broad_mixed_fit_data_engineer_journey(golden_profile_path: Path) -> None:
    """Data Engineer: transferable strengths with role-family divergence."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_data_engineer()
    assert MARKER_DATA_ENGINEER in posting.raw_text

    job_analysis, assessment = _run_journey(posting, profile)

    assert job_analysis.role_family.family == "data_engineering"
    assert {tech.name for tech in job_analysis.technologies} >= {"Python", "SQL"}

    _assert_complete_assessment(assessment, job_analysis=job_analysis)
    assert assessment.technical_fit.judgment == "mixed"
    assert any(
        finding.kind == "transferable_alignment"
        for finding in assessment.technical_fit.findings
    )
    assert any(finding.kind == "gap" for finding in assessment.technical_fit.findings)


def test_evidence_refs_resolve_across_stages(golden_profile_path: Path) -> None:
    """Service-bound assessment keeps valid profile and job evidence indexes."""
    profile = _golden_profile(golden_profile_path)
    posting = posting_applied_ai_engineer()

    job_analysis, assessment = _run_journey(posting, profile)
    _assert_complete_assessment(assessment, job_analysis=job_analysis)

    for dimension in (
        assessment.technical_fit,
        assessment.commercial_fit,
        assessment.portfolio_fit,
    ):
        for finding in dimension.findings:
            for job_ref in finding.job_evidence:
                if job_ref.source == "technology":
                    assert job_ref.item_index is not None
                    assert job_ref.item_index < len(job_analysis.technologies)
                elif job_ref.source == "responsibility":
                    assert job_ref.item_index is not None
                    assert job_ref.item_index < len(job_analysis.responsibilities)
                elif job_ref.source == "experience_requirement":
                    assert job_ref.item_index is not None
                    assert job_ref.item_index < len(job_analysis.experience_requirements)
            for profile_ref in finding.profile_evidence:
                assert ":" in profile_ref.ref
                namespace, identifier = profile_ref.ref.split(":", 1)
                assert namespace == profile_ref.source
                assert identifier


def test_all_golden_journeys_are_deterministic(golden_profile_path: Path) -> None:
    """Repeated offline journeys yield identical serialised assessments."""
    profile = _golden_profile(golden_profile_path)
    builders: tuple[Callable[[], JobPosting], ...] = (
        posting_applied_ai_engineer,
        posting_ai_engineer,
        posting_no_technologies,
        posting_working_rights,
        posting_data_engineer,
    )

    for builder in builders:
        posting = builder()
        first_analysis, first_assessment = _run_journey(posting, profile)
        second_analysis, second_assessment = _run_journey(builder(), profile)

        assert first_analysis.model_dump(mode="json") == second_analysis.model_dump(
            mode="json"
        )
        # Caller-owned posting identity differs; compare assessment excluding job_analysis.
        first_payload = first_assessment.model_dump(mode="json")
        second_payload = second_assessment.model_dump(mode="json")
        first_payload.pop("job_analysis")
        second_payload.pop("job_analysis")
        assert first_payload == second_payload
