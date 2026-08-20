"""M4 bounded cover-letter positioning — selection, pack, writer, fail-closed."""

from __future__ import annotations

import pytest

from career_intelligence.document_positioning import (
    BoundedCoverLetterPositioningService,
    BoundedCvPositioningService,
    CoverLetterPositioningExtraction,
    CoverLetterPositioningProviderError,
    CoverLetterPositioningValidationError,
    DEFAULT_SOURCE_COUNT,
    FixtureCoverLetterPositioningComposer,
    FixtureCvPositioningComposer,
    MAX_SOURCE_COUNT,
    SupportStatus,
    build_cover_letter_positioning_pack,
    build_cv_positioning_pack,
    build_positioning_plan,
)
from career_intelligence.profile.models import CareerProfile
from tests.unit.application_strategy.helpers import portfolio_project_evidence
from tests.unit.cv_generation.helpers import strategy_from_payload
from tests.unit.document_positioning.helpers import (
    adoption_job,
    analysis_with,
    eval_strategy,
    golden_job_analysis,
    live_profile,
    poisoned_assessment,
    specialist_job,
    specialist_profile,
    tech,
)
from tests.unit.document_positioning.test_m3_cv_positioning import (
    _MINI_MASTER,
    _tailoring,
)


class _FixedComposer:
    def __init__(self, extraction: CoverLetterPositioningExtraction) -> None:
        self.extraction = extraction

    def compose(self, pack: object) -> CoverLetterPositioningExtraction:
        return self.extraction


class _BoomComposer:
    def compose(self, pack: object) -> CoverLetterPositioningExtraction:
        raise RuntimeError("provider down")


def _strategy(job, profile, emphasis=None):
    if emphasis is None:
        emphasis = [
            {
                "project_id": project.id,
                "source_rank": index,
                "summary": f"Emphasise {project.name}.",
                "evidence": [portfolio_project_evidence(project.id)],
            }
            for index, project in enumerate(profile.projects[:5], start=1)
        ]
    return strategy_from_payload(job_analysis=job, portfolio_emphasis=emphasis)


def _pack(job=None, profile=None, assessment=None, strategy=None):
    bound_job = job or specialist_job()
    bound_profile = profile or specialist_profile()
    return build_cover_letter_positioning_pack(
        bound_job,
        bound_profile,
        assessment=assessment,
        strategy=strategy or _strategy(bound_job, bound_profile),
    )


def _compose(composer, job=None, profile=None, assessment=None, strategy=None):
    bound_job = job or specialist_job()
    bound_profile = profile or specialist_profile()
    return BoundedCoverLetterPositioningService(composer).compose(
        bound_job,
        bound_profile,
        assessment=assessment,
        strategy=strategy or _strategy(bound_job, bound_profile),
    )


def _two_project_profile():
    payload = specialist_profile().model_dump(mode="python")
    payload["projects"].append(
        {
            "id": "payroll-lite",
            "name": "Payroll Lite",
            "summary": "Deterministic payroll rules with Python APIs.",
            "technologies": ["Python", "REST APIs"],
            "outcomes": ["Explainable payroll checks."],
            "demonstrates": ["Deterministic rules"],
        }
    )
    return CareerProfile.model_validate(payload)


def test_a_evidence_selection_is_driven_by_employer_needs() -> None:
    pack = _pack()
    covered = {
        label.casefold()
        for source in pack.selected_sources
        for label in source.employer_needs_covered
    }
    assert "rag" in covered or any("retrieval" in item for item in covered)
    assert all(source.source_type != "job" for source in pack.selected_sources)


def test_b_direct_evidence_outranks_generic_project_overlap() -> None:
    profile = _two_project_profile()
    job = analysis_with(technologies=[tech("RAG"), tech("Python")])
    strategy = _strategy(
        job,
        profile,
        emphasis=[
            {
                "project_id": "payroll-lite",
                "source_rank": 1,
                "summary": "Rank 1 by tag overlap.",
                "evidence": [portfolio_project_evidence("payroll-lite")],
            },
            {
                "project_id": "rag-project",
                "source_rank": 2,
                "summary": "Rank 2 RAG project.",
                "evidence": [portfolio_project_evidence("rag-project")],
            },
        ],
    )
    pack = _pack(job=job, profile=profile, strategy=strategy)
    ids = [item.source_id for item in pack.selected_sources]
    assert "project:rag-project" in ids
    assert pack.portfolio_overrides


def test_c_related_evidence_covers_without_claiming_requested() -> None:
    pack = _pack()
    bedrock = next(item for item in pack.employer_needs if "bedrock" in item.label.casefold())
    assert bedrock.status is SupportStatus.SUPPORTED_RELATED
    related_sources = [
        item
        for item in pack.selected_sources
        if "related" in item.coverage_kinds
        or any("bedrock" in n.casefold() for n in item.employer_needs_covered)
    ]
    assert related_sources
    assert "AWS Bedrock" not in pack.claimable_direct_labels
    assert "AWS" in pack.related_profile_labels


def test_d_aws_bedrock_never_creates_bedrock_candidate_experience() -> None:
    result = _compose(FixtureCoverLetterPositioningComposer())
    folded = " ".join(result.paragraphs).casefold()
    assert "bedrock experience" not in folded
    assert "aws bedrock experience" not in folded


def test_e_unsupported_chatbot_cannot_be_claimed() -> None:
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "Example Co's Specialist AI Engineer role needs Python.",
            "I have production chatbot experience and conversational AI expertise.",
            "This packed evidence supports the role.",
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_f_maincode_gpu_linux_hpc_cannot_be_claimed() -> None:
    job = golden_job_analysis("012_maincode_ai_infrastructure_engineer")
    profile = live_profile()
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "Maincode's AI Infrastructure Engineer role needs applied AI.",
            "I have GPU, Linux, and HPC experience from production clusters.",
            "This packed evidence supports the role.",
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError):
        _compose(
            _FixedComposer(extraction),
            job=job,
            profile=profile,
            strategy=eval_strategy(job, profile),
        )


def test_g_repurpose_copilot_claude_cannot_be_claimed() -> None:
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "Example Co's AI Adoption Specialist role needs enablement.",
            "I have GitHub Copilot and Claude expertise from commercial delivery.",
            "This packed evidence supports the role.",
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError):
        _compose(_FixedComposer(extraction), job=adoption_job())


def test_h_portfolio_match_rank_can_influence_selection() -> None:
    profile = _two_project_profile()
    job = analysis_with(technologies=[tech("Python")])
    first = _pack(
        job=job,
        profile=profile,
        strategy=_strategy(
            job,
            profile,
            emphasis=[
                {
                    "project_id": "rag-project",
                    "source_rank": 1,
                    "summary": "Rank 1.",
                    "evidence": [portfolio_project_evidence("rag-project")],
                },
                {
                    "project_id": "payroll-lite",
                    "source_rank": 2,
                    "summary": "Rank 2.",
                    "evidence": [portfolio_project_evidence("payroll-lite")],
                },
            ],
        ),
    )
    second = _pack(
        job=job,
        profile=profile,
        strategy=_strategy(
            job,
            profile,
            emphasis=[
                {
                    "project_id": "payroll-lite",
                    "source_rank": 1,
                    "summary": "Rank 1.",
                    "evidence": [portfolio_project_evidence("payroll-lite")],
                },
                {
                    "project_id": "rag-project",
                    "source_rank": 2,
                    "summary": "Rank 2.",
                    "evidence": [portfolio_project_evidence("rag-project")],
                },
            ],
        ),
    )
    first_lead = first.selected_sources[0].source_id
    second_lead = second.selected_sources[0].source_id
    assert first.selected_sources[0].portfolio_match_rank == 1 or "project:" in first_lead
    assert second.selected_sources[0].portfolio_match_rank == 1 or "project:" in second_lead
    project_leads = {first_lead, second_lead}
    assert "project:rag-project" in project_leads or "project:payroll-lite" in project_leads


def test_i_positioning_plan_may_override_portfolio_match() -> None:
    profile = _two_project_profile()
    job = analysis_with(technologies=[tech("RAG"), tech("Python")])
    pack = _pack(
        job=job,
        profile=profile,
        strategy=_strategy(
            job,
            profile,
            emphasis=[
                {
                    "project_id": "payroll-lite",
                    "source_rank": 1,
                    "summary": "OIC-style rank 1 overlap.",
                    "evidence": [portfolio_project_evidence("payroll-lite")],
                },
                {
                    "project_id": "rag-project",
                    "source_rank": 2,
                    "summary": "RAG project.",
                    "evidence": [portfolio_project_evidence("rag-project")],
                },
            ],
        ),
    )
    ids = [item.source_id for item in pack.selected_sources]
    assert "project:rag-project" in ids
    assert pack.portfolio_overrides
    assert pack.portfolio_overrides[0].project_id == "payroll-lite"


def test_j_override_reason_is_inspectable() -> None:
    profile = _two_project_profile()
    job = analysis_with(technologies=[tech("RAG"), tech("Python")])
    pack = _pack(
        job=job,
        profile=profile,
        strategy=_strategy(
            job,
            profile,
            emphasis=[
                {
                    "project_id": "payroll-lite",
                    "source_rank": 1,
                    "summary": "Rank 1 overlap.",
                    "evidence": [portfolio_project_evidence("payroll-lite")],
                },
                {
                    "project_id": "rag-project",
                    "source_rank": 2,
                    "summary": "RAG.",
                    "evidence": [portfolio_project_evidence("rag-project")],
                },
            ],
        ),
    )
    assert pack.portfolio_overrides
    assert pack.portfolio_overrides[0].reason
    assert "need" in pack.portfolio_overrides[0].reason.casefold() or (
        "PortfolioMatch" in pack.portfolio_overrides[0].reason
    )


def test_k_two_source_default_policy() -> None:
    pack = _pack()
    assert DEFAULT_SOURCE_COUNT == 2
    assert 1 <= len(pack.selected_sources) <= MAX_SOURCE_COUNT


def test_l_third_source_only_for_distinct_uncovered_need() -> None:
    pack = _pack()
    if len(pack.selected_sources) == 3:
        third = pack.selected_sources[2]
        covered_by_first_two = {
            label.casefold()
            for source in pack.selected_sources[:2]
            for label in source.employer_needs_covered
        }
        third_needs = {label.casefold() for label in third.employer_needs_covered}
        assert third_needs - covered_by_first_two
        assert "third source" in third.purpose.casefold()
    else:
        assert len(pack.selected_sources) <= 2


def test_m_no_arbitrary_evidence_proliferation() -> None:
    pack = _pack()
    assert len(pack.selected_sources) <= MAX_SOURCE_COUNT


def test_n_ai_lead_does_not_force_full_biography() -> None:
    result = _compose(FixtureCoverLetterPositioningComposer())
    assert result.pack.trajectory_mode == "ai_lead"
    folded = " ".join(result.paragraphs).casefold()
    assert "qa →" not in folded
    assert "test analyst then" not in folded


def test_o_bridge_creates_transfer_narrative() -> None:
    job = analysis_with(family="software_engineering", technologies=[tech("Python")])
    result = _compose(FixtureCoverLetterPositioningComposer(), job=job)
    assert result.pack.trajectory_mode == "bridge"
    folded = " ".join(result.paragraphs).casefold()
    assert "transfer" in folded or "testing" in folded or "test analyst" in folded
    types = [item.source_type for item in result.pack.selected_sources]
    assert "employment" in types or "trajectory" in types


def test_p_full_chapters_preserves_qa_de_ai_trajectory() -> None:
    result = _compose(FixtureCoverLetterPositioningComposer(), job=adoption_job())
    assert result.pack.trajectory_mode == "full_chapters"
    folded = " ".join(result.paragraphs).casefold()
    assert "tester" in folded or "qa" in folded or "testing" in folded
    assert "data engineer" in folded


def test_q_generic_opening_patterns_rejected() -> None:
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "I am excited to apply for the Specialist AI Engineer role.",
            "I developed Document Intelligence RAG using packed Python evidence.",
            "This packed evidence supports Example Co's work.",
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError) as raised:
        _compose(_FixedComposer(extraction))
    assert any("generic opening" in item.msg for item in raised.value.errors)


def test_r_selected_evidence_source_represented() -> None:
    result = _compose(FixtureCoverLetterPositioningComposer())
    folded = " ".join(result.paragraphs).casefold()
    for source in result.pack.selected_sources:
        if source.source_type == "trajectory":
            assert "data engineer" in folded or "testing" in folded
            continue
        assert source.name.casefold()[:12] in folded or (
            source.organisation or ""
        ).casefold() in folded or any(
            part in folded for part in source.name.casefold().split() if len(part) >= 5
        )


def test_s_duplicate_evidence_paragraph_rejected() -> None:
    paragraph = (
        "I developed Document Intelligence RAG as independent portfolio work "
        "covering RAG and Python."
    )
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "Example Co's Specialist AI Engineer role needs RAG and Python.",
            paragraph,
            paragraph,
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError) as raised:
        _compose(_FixedComposer(extraction))
    assert any("duplicate" in item.msg for item in raised.value.errors)


def test_t_forbidden_related_requested_identity_rejected() -> None:
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "Example Co's Specialist AI Engineer role needs retrieval work.",
            "I have AWS Bedrock experience building Bedrock applications.",
            "This packed evidence supports the role.",
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_u_unsupported_capability_claim_rejected() -> None:
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "Example Co's Specialist AI Engineer role needs retrieval work.",
            "I built production chatbots and virtual agents for support teams.",
            "This packed evidence supports the role.",
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_v_invented_metric_rejected() -> None:
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "Example Co's Specialist AI Engineer role needs retrieval work.",
            "I developed Document Intelligence RAG and improved accuracy by 47%.",
            "This packed evidence supports the role.",
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_w_invented_years_rejected() -> None:
    extraction = CoverLetterPositioningExtraction(
        paragraphs=[
            "Example Co's Specialist AI Engineer role needs retrieval work.",
            "I developed Document Intelligence RAG across 12 years of AWS Bedrock-free work.",
            "This packed evidence supports the role.",
        ]
    )
    with pytest.raises(CoverLetterPositioningValidationError):
        _compose(_FixedComposer(extraction))


def test_x_provider_failure_fails_closed() -> None:
    with pytest.raises(CoverLetterPositioningProviderError):
        _compose(_BoomComposer())


def test_y_malformed_output_fails_closed() -> None:
    class Malformed:
        def compose(self, pack: object) -> object:
            return {"paragraphs": []}

    with pytest.raises(CoverLetterPositioningValidationError):
        _compose(Malformed())  # type: ignore[arg-type]


def test_z_cv_and_cover_letter_capability_framing_consistent() -> None:
    job = specialist_job()
    profile = specialist_profile()
    positioning = build_positioning_plan(job, profile)
    letter = _pack(job=job, profile=profile)
    cv_pack = build_cv_positioning_pack(
        job,
        profile,
        positioning,
        _tailoring(job, profile),
        _MINI_MASTER,
    )
    assert letter.trajectory_mode == cv_pack.trajectory_mode
    assert set(letter.claimable_direct_labels) == set(cv_pack.claimable_direct_labels)
    assert set(letter.related_profile_labels) == set(cv_pack.related_profile_labels)
    assert set(letter.unsupported_labels) == set(cv_pack.unsupported_labels)
    cv = BoundedCvPositioningService(FixtureCvPositioningComposer()).compose(
        job,
        profile,
        _tailoring(job, profile),
        _MINI_MASTER,
    )
    letter_result = _compose(
        FixtureCoverLetterPositioningComposer(), job=job, profile=profile
    )
    letter_folded = " ".join(letter_result.paragraphs).casefold()
    cv_folded = cv.extraction.summary.casefold()
    assert "bedrock experience" not in letter_folded
    assert "bedrock experience" not in cv_folded


def test_no_silent_generic_letter_fallback() -> None:
    with pytest.raises(CoverLetterPositioningProviderError):
        result = _compose(_BoomComposer())
        raise AssertionError(result.paragraphs)


def test_assessment_cannot_authorise_claims() -> None:
    job = specialist_job()
    pack = _pack(job=job, assessment=poisoned_assessment(job))
    assert pack.assessment_ignored is True
    assert "AWS Bedrock" not in pack.claimable_direct_labels


def test_same_inputs_same_pack() -> None:
    assert _pack().model_dump() == _pack().model_dump()


def test_pack_records_evidence_count_policy() -> None:
    pack = _pack()
    assert pack.selected_sources
    assert "Default two evidence sources" in pack.evidence_count_policy
