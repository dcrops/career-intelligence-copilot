"""M3 bounded CV positioning — evidence pack, writer, fail-closed validation."""

from __future__ import annotations

import pytest

from career_intelligence.cv_generation import (
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanService,
)
from career_intelligence.cv_generation.master_adapt import (
    DEFAULT_MASTER_CV_PATH,
    extract_h2_section,
    extract_master_summary,
    load_master_cv_markdown,
)
from career_intelligence.document_positioning import (
    BoundedCvPositioningService,
    CvPositioningExtraction,
    CvPositioningProviderError,
    CvPositioningValidationError,
    FixtureCvPositioningComposer,
    SupportStatus,
    build_cv_positioning_pack,
    build_positioning_plan,
    classify_requirement,
)
from career_intelligence.document_positioning.cv_composer import ProjectRelevanceLine
from tests.unit.application_strategy.helpers import portfolio_project_evidence
from tests.unit.cv_generation.helpers import strategy_from_payload
from tests.unit.document_positioning.helpers import (
    analysis_with,
    adoption_job,
    live_profile,
    poisoned_assessment,
    specialist_job,
    specialist_profile,
    tech,
)

_MINI_MASTER = """# Test Candidate

**AI Engineer**

---

## Professional Summary

Generic master summary for any role.

## Selected Engineering Highlights

- Designed and delivered a **portfolio of AI applications** combining deterministic logic with AI reasoning across RAG, operational intelligence, diagnostics, entitlements, and career decision support.
- Built modular service architectures with **FastAPI**, containerised services with **Docker**, and unit/regression suites in **PyTest**.

## Core Skills

**Python** · **AWS**

## Professional Experience

### Data Engineer — Example Telco
*2020 – 2023*

- Built reporting solutions using AWS services.

## Featured AI Projects

### Document Intelligence RAG

**Overview:** Grounded answers over organisational documents.

**Technology Stack:** Python · Retrieval-Augmented Generation

### Public Holiday Entitlements Application

**Overview:** Holiday rules engine.

**Technology Stack:** Python

## Courses & Upskilling

- Example course

## Certifications

- AWS Certified Developer - Associate
"""


class _FixedComposer:
    def __init__(self, extraction: CvPositioningExtraction) -> None:
        self.extraction = extraction

    def compose(self, pack: object) -> CvPositioningExtraction:
        return self.extraction


class _BoomComposer:
    def compose(self, pack: object) -> CvPositioningExtraction:
        raise RuntimeError("provider down")


def _tailoring(job, profile):
    emphasis = [
        {
            "project_id": project.id,
            "source_rank": index,
            "summary": f"Emphasise {project.name}.",
            "evidence": [portfolio_project_evidence(project.id)],
        }
        for index, project in enumerate(profile.projects[:3], start=1)
    ]
    return TailoringPlanService(DeterministicTailoringPlanner()).plan(
        strategy_from_payload(job_analysis=job, portfolio_emphasis=emphasis),
        profile,
        options=TailoringOptions(owner_approved_to_tailor=True),
    )


def _pack(job=None, profile=None, master=None, assessment=None):
    bound_job = job or specialist_job()
    bound_profile = profile or specialist_profile()
    markdown = master or _MINI_MASTER
    positioning = build_positioning_plan(bound_job, bound_profile, assessment=assessment)
    tailoring = _tailoring(bound_job, bound_profile)
    return build_cv_positioning_pack(
        bound_job,
        bound_profile,
        positioning,
        tailoring,
        markdown,
        assessment=assessment,
    )


def _compose(composer, job=None, profile=None, master=None, assessment=None):
    bound_job = job or specialist_job()
    bound_profile = profile or specialist_profile()
    markdown = master or _MINI_MASTER
    return BoundedCvPositioningService(composer).compose(
        bound_job,
        bound_profile,
        _tailoring(bound_job, bound_profile),
        markdown,
        assessment=assessment,
    )


def test_a_pack_contains_only_authorised_candidate_evidence() -> None:
    pack = _pack()
    for item in pack.candidate_evidence:
        assert item.source in {
            "skill",
            "experience",
            "project",
            "certification",
            "master_summary",
        }
        assert not item.ref.startswith("job:")
        assert "AWS Bedrock" not in item.text


def test_b_jd_text_is_not_candidate_evidence() -> None:
    pack = _pack()
    evidence_blob = " ".join(item.text for item in pack.candidate_evidence)
    assert "CSK nexus" not in evidence_blob
    assert all(need.kind != "candidate" for need in pack.employer_needs)


def test_c_key_alignments_cannot_authorise_claims() -> None:
    job = specialist_job()
    pack = _pack(job=job, assessment=poisoned_assessment(job))
    assert pack.assessment_ignored is True
    bedrock = next(item for item in pack.employer_needs if "bedrock" in item.label.casefold())
    assert bedrock.status is SupportStatus.SUPPORTED_RELATED
    assert bedrock.may_claim_requested is False
    assert "AWS Bedrock" not in pack.claimable_direct_labels


def test_d_direct_capability_may_be_expressed() -> None:
    pack = _pack()
    assert "Retrieval-Augmented Generation" in pack.claimable_direct_labels or "Python" in pack.claimable_direct_labels
    result = _compose(FixtureCvPositioningComposer())
    folded = result.extraction.summary.casefold()
    assert "python" in folded or "retrieval" in folded or "rag" in folded


def test_e_related_promotes_profile_capability_only() -> None:
    pack = _pack()
    bedrock = next(item for item in pack.employer_needs if "bedrock" in item.label.casefold())
    assert bedrock.status is SupportStatus.SUPPORTED_RELATED
    assert bedrock.promotable_profile_label == "AWS"
    assert "AWS" in pack.related_profile_labels
    assert "AWS Bedrock" not in pack.claimable_direct_labels


def test_f_aws_bedrock_cannot_be_claimed() -> None:
    extraction = CvPositioningExtraction(
        summary="I have AWS Bedrock experience building Bedrock applications.",
        project_relevance=[],
    )
    with pytest.raises(CvPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_g_unsupported_cannot_appear_as_candidate_experience() -> None:
    extraction = CvPositioningExtraction(
        summary="I have production chatbot experience and conversational AI expertise.",
        project_relevance=[],
    )
    with pytest.raises(CvPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_h_rag_direct_remains_claimable() -> None:
    pack = _pack()
    rag = next(item for item in pack.employer_needs if item.label.casefold() == "rag")
    assert rag.status is SupportStatus.SUPPORTED_DIRECT
    result = _compose(FixtureCvPositioningComposer())
    assert "rag" in result.extraction.summary.casefold() or "retrieval" in result.extraction.summary.casefold()


def test_i_llm_direct_is_not_a_rag_shortcut() -> None:
    rag_only = classify_requirement("LLM", ["Retrieval-Augmented Generation"])
    assert rag_only.status is SupportStatus.UNSUPPORTED
    live = build_positioning_plan(
        analysis_with(technologies=[tech("LLM"), tech("Python")]),
        live_profile(),
    )
    llm = next(item for item in live.employer_needs if item.need.label.casefold() == "llm")
    assert llm.classification.status is SupportStatus.SUPPORTED_DIRECT
    assert llm.classification.promotable_profile_label == "LLM application development"


def test_j_java_does_not_become_javascript() -> None:
    job = analysis_with(technologies=[tech("Java")])
    profile = specialist_profile()
    pack = _pack(job=job, profile=profile)
    java = next(item for item in pack.employer_needs if item.label.casefold() == "java")
    assert java.status is SupportStatus.UNSUPPORTED
    extraction = CvPositioningExtraction(
        summary="I have Java experience from JavaScript work.",
        project_relevance=[],
    )
    with pytest.raises(CvPositioningValidationError):
        _compose(_FixedComposer(extraction), job=job, profile=profile)


def test_k_ai_lead_summary_positioning() -> None:
    result = _compose(FixtureCvPositioningComposer())
    assert result.pack.trajectory_mode == "ai_lead"
    assert "ai engineer" in result.extraction.summary.casefold()
    assert "qa →" not in result.extraction.summary.casefold()


def test_l_bridge_summary_positioning() -> None:
    job = analysis_with(family="software_engineering", technologies=[tech("Python")])
    result = _compose(FixtureCvPositioningComposer(), job=job)
    assert result.pack.trajectory_mode == "bridge"
    folded = result.extraction.summary.casefold()
    assert "reliability" in folded or "testing" in folded


def test_m_full_chapters_summary_positioning() -> None:
    result = _compose(FixtureCvPositioningComposer(), job=adoption_job())
    assert result.pack.trajectory_mode == "full_chapters"
    folded = result.extraction.summary.casefold()
    assert "qa" in folded or "tester" in folded
    assert "data engineer" in folded


def test_n_methodology_included_when_plan_says_true() -> None:
    live_master = load_master_cv_markdown(DEFAULT_MASTER_CV_PATH)
    result = _compose(
        FixtureCvPositioningComposer(),
        job=specialist_job(),
        profile=live_profile(),
        master=live_master,
    )
    assert result.include_methodology is True
    assert "AI Engineering Methodology" in result.markdown


def test_o_methodology_omitted_when_plan_says_false() -> None:
    from tests.unit.document_positioning.helpers import golden_job_analysis

    live_master = load_master_cv_markdown(DEFAULT_MASTER_CV_PATH)
    job = golden_job_analysis("012_maincode_ai_infrastructure_engineer")
    result = _compose(
        FixtureCvPositioningComposer(),
        job=job,
        profile=live_profile(),
        master=live_master,
    )
    assert result.include_methodology is False
    assert "AI Engineering Methodology" not in result.markdown


def test_p_locked_employment_history_unchanged() -> None:
    result = _compose(FixtureCvPositioningComposer())
    original = extract_h2_section(_MINI_MASTER, "professional experience")
    rendered = extract_h2_section(result.markdown, "professional experience")
    assert original == rendered


def test_q_locked_project_bodies_unchanged() -> None:
    result = _compose(FixtureCvPositioningComposer())
    original = extract_h2_section(_MINI_MASTER, "featured ai projects")
    assert original is not None
    assert "**Overview:** Grounded answers over organisational documents." in result.markdown
    assert "Grounded answers over organisational documents." in (original or "")


def test_r_certifications_courses_contact_preserved() -> None:
    result = _compose(FixtureCvPositioningComposer())
    assert extract_h2_section(_MINI_MASTER, "certifications") == extract_h2_section(
        result.markdown, "certifications"
    )
    assert extract_h2_section(_MINI_MASTER, "courses & upskilling") == extract_h2_section(
        result.markdown, "courses & upskilling"
    )
    assert "Test Candidate" in result.markdown


def test_s_forbidden_claim_from_fake_llm_fails() -> None:
    extraction = CvPositioningExtraction(
        summary="Hands-on Bedrock expertise from commercial AWS Bedrock delivery.",
        project_relevance=[],
    )
    with pytest.raises(CvPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_t_unsupported_claim_from_fake_llm_fails() -> None:
    extraction = CvPositioningExtraction(
        summary="I built production chatbots and virtual agents for support teams.",
        project_relevance=[],
    )
    with pytest.raises(CvPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_u_malformed_llm_output_fails_closed() -> None:
    class Malformed:
        def compose(self, pack: object) -> object:
            return {"summary": "", "project_relevance": []}

    with pytest.raises(CvPositioningValidationError):
        _compose(Malformed())  # type: ignore[arg-type]


def test_v_provider_failure_fails_closed() -> None:
    with pytest.raises(CvPositioningProviderError):
        _compose(_BoomComposer())


def test_w_no_silent_master_summary_fallback() -> None:
    with pytest.raises(CvPositioningProviderError):
        result = _compose(_BoomComposer())
        raise AssertionError(result.extraction.summary)
    master = extract_master_summary(_MINI_MASTER)
    assert master == "Generic master summary for any role."


def test_x_same_inputs_same_pack() -> None:
    first = _pack()
    second = _pack()
    assert first.model_dump() == second.model_dump()


def test_related_project_relevance_cannot_claim_bedrock() -> None:
    extraction = CvPositioningExtraction(
        summary="AI Engineer using packed Python and AWS evidence.",
        project_relevance=[
            ProjectRelevanceLine(
                project_name="Document Intelligence RAG",
                line="built with AWS Bedrock experience on this project.",
            )
        ],
    )
    result = _compose(_FixedComposer(extraction))
    assert result.extraction.project_relevance == []
    assert "bedrock" not in result.extraction.summary.casefold()


def test_exact_packed_project_relevance_is_retained() -> None:
    extraction = CvPositioningExtraction(
        summary="AI Engineer using packed Python and retrieval evidence.",
        project_relevance=[
            ProjectRelevanceLine(
                project_name="Document Intelligence RAG",
                line="demonstrates Python delivery from packed independent portfolio evidence.",
            )
        ],
    )
    result = _compose(_FixedComposer(extraction))
    assert len(result.extraction.project_relevance) == 1
    assert result.extraction.project_relevance[0].project_name == (
        "Document Intelligence RAG"
    )


def test_unpacked_project_relevance_is_dropped() -> None:
    extraction = CvPositioningExtraction(
        summary="AI Engineer using packed Python and retrieval evidence.",
        project_relevance=[
            ProjectRelevanceLine(
                project_name="Public Holiday Entitlements Application",
                line="demonstrates Python delivery from packed independent portfolio evidence.",
            )
        ],
    )
    result = _compose(_FixedComposer(extraction))
    assert result.extraction.project_relevance == []
    assert "Relevant to this role" not in result.markdown


def test_valid_summary_survives_after_dropping_bad_relevance() -> None:
    extraction = CvPositioningExtraction(
        summary="AI Engineer using packed Python and retrieval evidence.",
        project_relevance=[
            ProjectRelevanceLine(
                project_name="Public Holiday Entitlements Application",
                line="demonstrates Python delivery from packed independent portfolio evidence.",
            )
        ],
    )
    result = _compose(_FixedComposer(extraction))
    assert "packed Python" in result.extraction.summary
    assert result.extraction.project_relevance == []


def test_mixed_relevance_drops_only_invalid_line() -> None:
    extraction = CvPositioningExtraction(
        summary="AI Engineer using packed Python and retrieval evidence.",
        project_relevance=[
            ProjectRelevanceLine(
                project_name="Document Intelligence RAG",
                line="demonstrates Python delivery from packed independent portfolio evidence.",
            ),
            ProjectRelevanceLine(
                project_name="Public Holiday Entitlements Application",
                line="demonstrates Python delivery from packed independent portfolio evidence.",
            ),
        ],
    )
    result = _compose(_FixedComposer(extraction))
    names = [item.project_name for item in result.extraction.project_relevance]
    assert names == ["Document Intelligence RAG"]


def test_empty_relevance_remains_valid() -> None:
    extraction = CvPositioningExtraction(
        summary="AI Engineer using packed Python and retrieval evidence.",
        project_relevance=[],
    )
    result = _compose(_FixedComposer(extraction))
    assert result.extraction.project_relevance == []


def test_invented_metric_in_summary_still_fails() -> None:
    extraction = CvPositioningExtraction(
        summary="I improved retrieval quality by 47% using packed Python evidence.",
        project_relevance=[],
    )
    with pytest.raises(CvPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_unpacked_project_claim_in_summary_still_fails() -> None:
    extraction = CvPositioningExtraction(
        summary=(
            "I developed Public Holiday Entitlements Application as packed "
            "Python evidence for this role."
        ),
        project_relevance=[],
    )
    with pytest.raises(CvPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_forbidden_summary_is_not_saved_by_dropping_relevance() -> None:
    extraction = CvPositioningExtraction(
        summary="I have AWS Bedrock experience building Bedrock applications.",
        project_relevance=[
            ProjectRelevanceLine(
                project_name="Public Holiday Entitlements Application",
                line="demonstrates Python delivery from packed independent portfolio evidence.",
            )
        ],
    )
    with pytest.raises(CvPositioningValidationError):
        _compose(_FixedComposer(extraction))
