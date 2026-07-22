"""Deterministic opportunity-assessment fixtures for offline architecture tests.

Builders return untrusted assessment payloads (no ``job_analysis`` or ``profile``).
``OpportunityAssessmentService`` binds caller-supplied trusted inputs after assessment.

Scenarios key off shared FR-002 posting markers in ``job_analysis.posting.raw_text``
so journeys can chain JobAnalysisService → OpportunityAssessmentService without
duplicating JobAnalysis structures in this package.
"""

from __future__ import annotations

from collections.abc import Callable

from career_intelligence.job_analysis.fixtures import (
    MARKER_AI_ENGINEER,
    MARKER_AMBIGUOUS_SENIORITY,
    MARKER_APPLIED_AI,
    MARKER_CONTRACT,
    MARKER_DATA_ENGINEER,
    MARKER_MISSING_SALARY,
    MARKER_NO_TECHNOLOGIES,
    MARKER_WORKING_RIGHTS,
)

from .assessor import OpportunityAssessmentPayload

PayloadBuilder = Callable[[], OpportunityAssessmentPayload]

# Shared FR-002 markers link extraction and assessment stages. Prefer the shared
# names; aliases retained for older assessment-only references in tests/docs.
MARKER_ASSESS_NO_TECHNOLOGIES = MARKER_NO_TECHNOLOGIES
MARKER_ASSESS_WORKING_RIGHTS = MARKER_WORKING_RIGHTS


def _job(
    source: str,
    *,
    item_index: int | None = None,
    name: str | None = None,
    excerpt: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"source": source}
    if item_index is not None:
        payload["item_index"] = item_index
    if name is not None:
        payload["name"] = name
    if excerpt is not None:
        payload["excerpt"] = excerpt
    return payload


def _profile(
    source: str,
    ref: str,
    *,
    excerpt: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"source": source, "ref": ref}
    if excerpt is not None:
        payload["excerpt"] = excerpt
    return payload


def _finding(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": "alignment",
        "summary": "Placeholder finding.",
        "importance": "material",
        "job_evidence": [],
        "profile_evidence": [],
    }
    payload.update(overrides)
    return payload


def _dimension(dimension: str, judgment: str, summary: str, findings: list[dict[str, object]]) -> dict[str, object]:
    return {
        "dimension": dimension,
        "judgment": judgment,
        "summary": summary,
        "findings": findings,
    }


def _summary(summary: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {"summary": summary}
    payload.update(overrides)
    return payload


def assessment_strong_ai_alignment() -> OpportunityAssessmentPayload:
    """Scenario 1: strong AI Engineering alignment without inventing commercial AI employment."""
    return {
        "technical_fit": _dimension(
            "technical",
            "strong",
            "Required Python and FastAPI align with demonstrated profile skills and portfolio work.",
            [
                _finding(
                    kind="alignment",
                    summary="Required Python is demonstrated across employment, skills, and projects.",
                    job_evidence=[_job("technology", item_index=0, name="Python", excerpt="Python and FastAPI required")],
                    profile_evidence=[
                        _profile("skill", "skill:Python"),
                        _profile("experience", "experience:nbn-data-engineer-2020"),
                    ],
                ),
                _finding(
                    kind="alignment",
                    summary="Required FastAPI is demonstrated in independent engineering and portfolio projects.",
                    job_evidence=[_job("technology", item_index=1, name="FastAPI", excerpt="Python and FastAPI required")],
                    profile_evidence=[
                        _profile("skill", "skill:FastAPI"),
                        _profile("project", "project:operational-intelligence-copilot"),
                    ],
                ),
            ],
        ),
        "commercial_fit": _dimension(
            "commercial",
            "moderate",
            "Role aligns with AI Engineering direction; Sydney hybrid location is workable but not ideal.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Applied AI Engineering role family aligns with the candidate target role.",
                    job_evidence=[_job("role_family", excerpt="Applied AI Engineer")],
                    profile_evidence=[_profile("identity", "identity:target_role")],
                ),
                _finding(
                    kind="partial_alignment",
                    summary="Hybrid Sydney arrangement is compatible with flexible remote preference but not Melbourne-based.",
                    job_evidence=[_job("work_arrangement", excerpt="Hybrid Sydney (Barangaroo), 2 days in office")],
                    profile_evidence=[
                        _profile("preference", "preference:remote"),
                        _profile("preference", "preference:locations"),
                    ],
                ),
            ],
        ),
        "portfolio_fit": _dimension(
            "portfolio",
            "strong",
            "Portfolio projects credibly demonstrate applied AI engineering and RAG capability.",
            [
                _finding(
                    kind="alignment",
                    summary="Portfolio projects demonstrate applied AI prototypes and production-minded LLM systems.",
                    job_evidence=[
                        _job(
                            "responsibility",
                            item_index=0,
                            excerpt="Deliver applied AI prototypes into production services",
                        )
                    ],
                    profile_evidence=[
                        _profile("project", "project:operational-intelligence-copilot"),
                        _profile("project", "project:governance-document-rag"),
                    ],
                ),
            ],
        ),
        "summary": _summary(
            "Strong technical and portfolio alignment for an applied AI Engineering role.",
            key_alignments=[
                "Python and FastAPI requirements are well supported.",
                "Portfolio demonstrates applied AI delivery patterns.",
            ],
            key_gaps=["Role is Sydney hybrid rather than Melbourne-based."],
        ),
    }


def assessment_production_ai_required() -> OpportunityAssessmentPayload:
    """Scenario 2: production AI required — portfolio/independent evidence only, not commercial employment."""
    return {
        "technical_fit": _dimension(
            "technical",
            "mixed",
            "Core technologies align, but required production LLM experience is not established in commercial employment.",
            [
                _finding(
                    kind="alignment",
                    summary="Required Python is demonstrated across data engineering employment and AI portfolio work.",
                    job_evidence=[_job("technology", item_index=0, name="Python", excerpt="Strong Python required")],
                    profile_evidence=[
                        _profile("skill", "skill:Python"),
                        _profile("experience", "experience:nbn-data-engineer-2020"),
                    ],
                ),
                _finding(
                    kind="partial_alignment",
                    summary=(
                        "Required production LLM or RAG experience is supported by independent "
                        "engineering and portfolio projects, not commercial AI employment."
                    ),
                    job_evidence=[
                        _job(
                            "experience_requirement",
                            item_index=1,
                            excerpt="Production LLM or RAG experience required",
                        )
                    ],
                    profile_evidence=[
                        _profile("experience", "experience:chase-risk-compliance-ai-engineer"),
                        _profile("project", "project:governance-document-rag"),
                    ],
                ),
                _finding(
                    kind="gap",
                    summary=(
                        "No commercial employment entry establishes paid production AI Engineering "
                        "delivery; independent engineering is real capability evidence but not "
                        "equivalent to commercial production AI employment."
                    ),
                    job_evidence=[
                        _job(
                            "experience_requirement",
                            item_index=1,
                            excerpt="Production LLM or RAG experience required",
                        )
                    ],
                    profile_evidence=[],
                ),
            ],
        ),
        "commercial_fit": _dimension(
            "commercial",
            "moderate",
            "Stated compensation and hybrid Melbourne arrangement are broadly compatible with preferences.",
            [
                _finding(
                    kind="alignment",
                    summary="Hybrid Melbourne location aligns with stated location preferences.",
                    job_evidence=[_job("location", excerpt="Hybrid Melbourne")],
                    profile_evidence=[_profile("preference", "preference:locations")],
                ),
                _finding(
                    kind="assumption",
                    summary="Salary range is stated, but the profile records no salary minimum for comparison.",
                    importance="minor",
                    assumption="Compensation cannot be scored against a minimum threshold because salary_min is unset.",
                    job_evidence=[_job("compensation", excerpt="Salary $150,000–$180,000 AUD + super")],
                    profile_evidence=[_profile("preference", "preference:salary_min")],
                ),
            ],
        ),
        "portfolio_fit": _dimension(
            "portfolio",
            "moderate",
            "Portfolio projects support an AI engineering narrative but do not substitute for commercial tenure claims.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Portfolio RAG and copilot projects demonstrate relevant LLM application engineering patterns.",
                    job_evidence=[_job("role_family", excerpt="Senior AI Engineer")],
                    profile_evidence=[
                        _profile("project", "project:governance-document-rag"),
                        _profile("project", "project:operational-intelligence-copilot"),
                    ],
                ),
            ],
        ),
        "summary": _summary(
            "Mixed fit: strong Python and portfolio evidence, but commercial production AI employment is not established.",
            key_alignments=["Python and RAG-oriented portfolio projects are relevant."],
            key_gaps=["Commercial production AI employment is not evidenced."],
        ),
    }


def assessment_no_named_technologies() -> OpportunityAssessmentPayload:
    """Scenario 3: no named technologies — uncertainty only, no invented tech gaps."""
    return {
        "technical_fit": _dimension(
            "technical",
            "unknown",
            "The analysed job does not name specific technologies, so technology-level fit cannot be determined.",
            [
                _finding(
                    kind="uncertainty",
                    summary="The job analysis contains no named technology requirements to compare against profile skills.",
                    job_evidence=[_job("role_family", excerpt="AI Engineer")],
                    profile_evidence=[],
                ),
            ],
        ),
        "commercial_fit": _dimension(
            "commercial",
            "moderate",
            "Remote Australia arrangement aligns with location preferences.",
            [
                _finding(
                    kind="alignment",
                    summary="Fully remote Australia arrangement aligns with Remote Australia location preference.",
                    job_evidence=[_job("work_arrangement", excerpt="Fully remote within Australia")],
                    profile_evidence=[_profile("preference", "preference:locations")],
                ),
            ],
        ),
        "portfolio_fit": _dimension(
            "portfolio",
            "moderate",
            "Outcome-focused advert still aligns with AI Engineering portfolio direction at role-family level.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="AI Engineering role family aligns with portfolio projects despite sparse technical detail in the advert.",
                    job_evidence=[_job("role_family", excerpt="AI Engineer")],
                    profile_evidence=[
                        _profile("project", "project:operational-intelligence-copilot"),
                        _profile("goal", "goal:primary"),
                    ],
                ),
            ],
        ),
        "summary": _summary(
            "Limited technical assessability because the advert names no specific technologies.",
            key_alignments=["Remote Australia arrangement fits stated preferences."],
            key_gaps=["No technology requirements were extracted to compare against skills."],
        ),
    }


def assessment_ambiguous_seniority() -> OpportunityAssessmentPayload:
    """Scenario 4: ambiguous seniority — uncertainty, no forced seniority match."""
    return {
        "technical_fit": _dimension(
            "technical",
            "mixed",
            "Python capability aligns, but seniority expectations remain ambiguous in the job analysis.",
            [
                _finding(
                    kind="alignment",
                    summary="Required Python is demonstrated in profile skills and projects.",
                    job_evidence=[
                        _job(
                            "technology",
                            item_index=0,
                            name="Python",
                            excerpt="Python and production LLM experience required",
                        )
                    ],
                    profile_evidence=[_profile("skill", "skill:Python")],
                ),
                _finding(
                    kind="uncertainty",
                    summary="Seniority is ambiguous between senior and lead levels, so seniority fit cannot be determined confidently.",
                    job_evidence=[_job("seniority", excerpt="open to Senior or Lead level depending on experience")],
                    profile_evidence=[],
                ),
            ],
        ),
        "commercial_fit": _dimension(
            "commercial",
            "moderate",
            "Hybrid Melbourne and stated salary are broadly compatible with preferences.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Hybrid Melbourne location is compatible with Melbourne location preference.",
                    job_evidence=[_job("location", excerpt="Hybrid Melbourne, 3 days in office")],
                    profile_evidence=[_profile("preference", "preference:locations")],
                ),
            ],
        ),
        "portfolio_fit": _dimension(
            "portfolio",
            "moderate",
            "Portfolio supports LLM delivery experience without establishing a specific seniority band.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Portfolio projects demonstrate LLM application delivery relevant to the responsibilities.",
                    job_evidence=[
                        _job(
                            "responsibility",
                            item_index=0,
                            excerpt="Own LLM application delivery end-to-end",
                        )
                    ],
                    profile_evidence=[_profile("project", "project:governance-document-rag")],
                ),
            ],
        ),
        "summary": _summary(
            "Moderate overall fit with explicit seniority uncertainty.",
            key_alignments=["Python and LLM-oriented portfolio work are relevant."],
            key_gaps=["Seniority expectations remain ambiguous."],
        ),
    }


def assessment_onsite_location() -> OpportunityAssessmentPayload:
    """Scenario 5: on-site/hybrid constraint — honest comparison, no invented deal-breaker."""
    return {
        "technical_fit": _dimension(
            "technical",
            "moderate",
            "Python and LangChain requirements align with demonstrated skills and portfolio evidence.",
            [
                _finding(
                    kind="alignment",
                    summary="Required Python is demonstrated in profile skills and projects.",
                    job_evidence=[_job("technology", item_index=0, name="Python", excerpt="Python and LangChain required")],
                    profile_evidence=[_profile("skill", "skill:Python")],
                ),
            ],
        ),
        "commercial_fit": _dimension(
            "commercial",
            "mixed",
            "Sydney hybrid on-site expectations and contract engagement create commercial friction without a profile deal-breaker.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Hybrid Sydney with 3 days on-site is workable but not aligned with Melbourne-first location preferences.",
                    job_evidence=[_job("work_arrangement", excerpt="Hybrid Sydney, 3 days on-site")],
                    profile_evidence=[
                        _profile("preference", "preference:locations"),
                        _profile("preference", "preference:remote"),
                    ],
                ),
                _finding(
                    kind="conflict",
                    summary="Contract engagement conflicts with full-time permanent employment preference.",
                    job_evidence=[_job("employment", excerpt="Full-time contract (initial 6 months)")],
                    profile_evidence=[_profile("preference", "preference:employment_types")],
                ),
            ],
        ),
        "portfolio_fit": _dimension(
            "portfolio",
            "moderate",
            "RAG portfolio projects remain relevant to the contract delivery scope.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Portfolio RAG work aligns with retrieval pipeline responsibilities.",
                    job_evidence=[
                        _job(
                            "responsibility",
                            item_index=0,
                            excerpt="Implement retrieval pipelines and evaluation tooling",
                        )
                    ],
                    profile_evidence=[_profile("project", "project:governance-document-rag")],
                ),
            ],
        ),
        "summary": _summary(
            "Mixed commercial fit due to Sydney on-site hybrid expectations and contract engagement.",
            key_alignments=["Technical stack overlaps with profile skills."],
            key_gaps=["Sydney on-site hybrid and contract terms diverge from stated preferences."],
        ),
    }


def assessment_salary_unstated() -> OpportunityAssessmentPayload:
    """Scenario 6: salary unstated — limited commercial assessability."""
    return {
        "technical_fit": _dimension(
            "technical",
            "moderate",
            "Python requirement aligns; LangChain is preferred rather than required.",
            [
                _finding(
                    kind="alignment",
                    summary="Required Python is demonstrated in profile skills and projects.",
                    job_evidence=[_job("technology", item_index=0, name="Python", excerpt="Python required")],
                    profile_evidence=[_profile("skill", "skill:Python")],
                ),
            ],
        ),
        "commercial_fit": _dimension(
            "commercial",
            "unknown",
            "Compensation is unstated, so salary alignment cannot be assessed.",
            [
                _finding(
                    kind="uncertainty",
                    summary="Compensation is unstated in the job analysis, so salary fit cannot be determined.",
                    job_evidence=[_job("compensation")],
                    profile_evidence=[],
                ),
                _finding(
                    kind="assumption",
                    summary="No salary minimum is recorded in the profile for comparison even if compensation were stated.",
                    importance="minor",
                    assumption="salary_min is null, so commercial comparison would remain limited without owner input.",
                    job_evidence=[],
                    profile_evidence=[_profile("preference", "preference:salary_min")],
                ),
            ],
        ),
        "portfolio_fit": _dimension(
            "portfolio",
            "moderate",
            "RAG-focused responsibilities align with governance RAG portfolio work.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="RAG assistant responsibilities align with the governance-aware RAG portfolio project.",
                    job_evidence=[
                        _job(
                            "responsibility",
                            item_index=0,
                            excerpt="Develop RAG assistants over internal knowledge bases",
                        )
                    ],
                    profile_evidence=[_profile("project", "project:governance-document-rag")],
                ),
            ],
        ),
        "summary": _summary(
            "Moderate technical and portfolio fit with unstated compensation limiting commercial assessability.",
            key_alignments=["Python and RAG portfolio evidence are relevant."],
            key_gaps=["Compensation is unstated."],
        ),
    }


def assessment_working_rights() -> OpportunityAssessmentPayload:
    """Scenario 7: working-rights requirement — job-side only, candidate status unknown."""
    return {
        "technical_fit": _dimension(
            "technical",
            "unknown",
            "Sparse technical detail prevents technology-level assessment.",
            [
                _finding(
                    kind="uncertainty",
                    summary="No named technology requirements were extracted from the job analysis.",
                    job_evidence=[_job("role_family", excerpt="AI Engineer")],
                    profile_evidence=[],
                ),
            ],
        ),
        "commercial_fit": _dimension(
            "commercial",
            "unknown",
            "Working-rights requirement is stated, but the profile provides no eligibility evidence.",
            [
                _finding(
                    kind="uncertainty",
                    summary=(
                        "The job states an Australian working-rights requirement, but the profile "
                        "records no working-rights or visa information to confirm eligibility."
                    ),
                    job_evidence=[
                        _job(
                            "experience_requirement",
                            item_index=0,
                            excerpt="Must have unrestricted Australian working rights",
                        )
                    ],
                    profile_evidence=[],
                ),
            ],
        ),
        "portfolio_fit": _dimension(
            "portfolio",
            "moderate",
            "AI Engineering portfolio direction remains relevant despite sparse advert detail.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="AI Engineering role family aligns with portfolio direction.",
                    job_evidence=[_job("role_family", excerpt="AI Engineer")],
                    profile_evidence=[_profile("goal", "goal:primary")],
                ),
            ],
        ),
        "summary": _summary(
            "Commercial assessability is limited by an explicit working-rights requirement and absent profile evidence.",
            key_alignments=["Role family aligns with AI Engineering goals."],
            key_gaps=["Working-rights eligibility cannot be assessed from the profile."],
        ),
    }


def assessment_broad_developer_mixed() -> OpportunityAssessmentPayload:
    """Scenario 8: broad data-engineering role with transferable fit and honest AI gaps."""
    return {
        "technical_fit": _dimension(
            "technical",
            "mixed",
            "Data engineering skills transfer strongly; AI-specific emphasis is limited for a data-engineering role family.",
            [
                _finding(
                    kind="transferable_alignment",
                    summary="Required Python and SQL align with commercial data engineering employment.",
                    job_evidence=[_job("technology", item_index=0, name="Python", excerpt="Python and SQL required")],
                    profile_evidence=[_profile("experience", "experience:nbn-data-engineer-2020")],
                ),
                _finding(
                    kind="transferable_alignment",
                    summary="Preferred Spark and dbt align with professional development and data engineering skills.",
                    job_evidence=[_job("technology", item_index=2, name="Spark", excerpt="Spark and dbt preferred")],
                    profile_evidence=[
                        _profile("skill", "skill:dbt"),
                        _profile("experience", "experience:data-engineering-development-2023"),
                    ],
                ),
                _finding(
                    kind="gap",
                    summary="Role family is data engineering rather than applied AI Engineering, which is the candidate's primary target direction.",
                    job_evidence=[_job("role_family", excerpt="Data Engineer")],
                    profile_evidence=[
                        _profile("identity", "identity:target_role"),
                        _profile("goal", "goal:primary"),
                    ],
                ),
            ],
        ),
        "commercial_fit": _dimension(
            "commercial",
            "moderate",
            "Melbourne hybrid permanent role aligns with location and employment preferences.",
            [
                _finding(
                    kind="alignment",
                    summary="Hybrid Melbourne permanent arrangement aligns with stated preferences.",
                    job_evidence=[_job("work_arrangement", excerpt="Hybrid Melbourne")],
                    profile_evidence=[
                        _profile("preference", "preference:locations"),
                        _profile("preference", "preference:employment_types"),
                    ],
                ),
            ],
        ),
        "portfolio_fit": _dimension(
            "portfolio",
            "weak",
            "Portfolio emphasises AI engineering projects more than lakehouse data-platform delivery.",
            [
                _finding(
                    kind="partial_alignment",
                    summary="Data engineering employment history supports pipeline responsibilities more than AI portfolio projects do.",
                    job_evidence=[
                        _job(
                            "responsibility",
                            item_index=0,
                            excerpt="Design and operate batch and streaming pipelines",
                        )
                    ],
                    profile_evidence=[_profile("experience", "experience:nbn-data-engineer-2020")],
                ),
            ],
        ),
        "summary": _summary(
            "Mixed fit: strong transferable data engineering alignment, but the role is not the primary AI Engineering target.",
            key_alignments=["Commercial data engineering experience is highly relevant."],
            key_gaps=["Role family diverges from the AI Engineering target direction."],
        ),
    }


ASSESSMENT_FIXTURE_BUILDERS: dict[str, PayloadBuilder] = {
    MARKER_APPLIED_AI: assessment_strong_ai_alignment,
    MARKER_AI_ENGINEER: assessment_production_ai_required,
    MARKER_NO_TECHNOLOGIES: assessment_no_named_technologies,
    MARKER_AMBIGUOUS_SENIORITY: assessment_ambiguous_seniority,
    MARKER_CONTRACT: assessment_onsite_location,
    MARKER_MISSING_SALARY: assessment_salary_unstated,
    MARKER_WORKING_RIGHTS: assessment_working_rights,
    MARKER_DATA_ENGINEER: assessment_broad_developer_mixed,
}
