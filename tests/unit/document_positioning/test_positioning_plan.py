"""M1 PositioningPlan builder — semantic behaviour, not CSK-specific strings."""

from __future__ import annotations

from career_intelligence.document_positioning import (
    CV_REWRITE_SURFACE,
    LOCKED_MASTER_SECTIONS,
    SupportStatus,
    build_positioning_plan,
)

from tests.unit.document_positioning.helpers import (
    adoption_job,
    analysis_with,
    poisoned_assessment,
    specialist_job,
    specialist_profile,
    tech,
)


def _plan(**overrides: object):
    job = overrides.pop("job", None) or specialist_job()
    profile = overrides.pop("profile", None) or specialist_profile()
    assessment = overrides.pop("assessment", None)
    assert not overrides
    return build_positioning_plan(job, profile, assessment=assessment)


def _need(plan, label: str):
    matches = [
        item
        for item in plan.employer_needs
        if item.need.label.casefold() == label.casefold()
    ]
    assert matches, f"missing employer need {label!r}"
    return matches[0]


def test_a_rag_alias_evidence_is_direct_for_rag_requirement() -> None:
    item = _need(_plan(), "RAG")
    assert item.classification.status is SupportStatus.SUPPORTED_DIRECT
    assert item.classification.requested_identity == "rag"
    assert item.classification.may_claim_requested is True


def test_b_aws_evidence_is_related_for_bedrock_requirement() -> None:
    item = _need(_plan(), "AWS Bedrock")
    assert item.classification.status is SupportStatus.SUPPORTED_RELATED
    assert item.classification.requested_identity == "aws_bedrock"
    assert item.classification.promotable_identity == "aws"
    assert item.classification.promotable_profile_label == "AWS"
    assert item.classification.may_claim_requested is False


def test_c_bedrock_related_selects_aws_and_forbids_bedrock_experience() -> None:
    plan = _plan()
    item = _need(plan, "AWS Bedrock")
    refs = {ref.ref for ref in item.evidence_refs}
    assert "skill:AWS" in refs
    assert "certification:aws-dev" in refs
    assert all("bedrock" not in ref.ref.casefold() for ref in item.evidence_refs)
    forbidden = {claim.may_not_claim.casefold() for claim in plan.forbidden_claims}
    assert "aws bedrock" in forbidden
    assert "bedrock" in forbidden
    assert not any(
        claim.kind == "direct" and "bedrock" in claim.statement.casefold()
        for claim in plan.argument_spine
    )
    related = next(claim for claim in plan.argument_spine if claim.kind == "related")
    assert "AWS" in related.statement
    assert "Do not claim" in related.statement


def test_d_unsupported_chatbot_requirement() -> None:
    item = _need(_plan(), "chatbots")
    assert item.classification.status is SupportStatus.UNSUPPORTED
    assert item.classification.requested_identity == "chatbot"
    assert item.evidence_refs == ()


def test_e_javascript_does_not_support_java() -> None:
    from career_intelligence.profile.models import CareerProfile

    payload = specialist_profile().model_dump(mode="python")
    payload["skills"]["technical"].append(
        {"name": "JavaScript", "evidence": "project:rag-project"}
    )
    profile = CareerProfile.model_validate(payload)
    plan = _plan(job=analysis_with(technologies=[tech("Java")]), profile=profile)
    item = _need(plan, "Java")
    assert item.classification.status is SupportStatus.UNSUPPORTED
    assert item.evidence_refs == ()


def test_f_unknown_exact_normalised_capability_can_be_direct() -> None:
    plan = _plan()
    item = _need(plan, "Python")
    assert item.classification.status is SupportStatus.SUPPORTED_DIRECT
    assert item.classification.requested_identity is None
    assert item.classification.may_claim_requested is True
    assert any(ref.source == "skill" for ref in item.evidence_refs)


def test_g_unknown_non_match_cannot_become_related() -> None:
    plan = _plan(
        job=analysis_with(technologies=[tech("TypeScript")]),
        profile=specialist_profile(),
    )
    item = _need(plan, "TypeScript")
    assert item.classification.status is SupportStatus.UNSUPPORTED
    assert item.classification.requested_identity is None
    assert item.evidence_refs == ()
    assert not any(
        "related" in claim.kind for claim in plan.argument_spine if "TypeScript" in claim.statement
    )


def test_h_employer_jd_capability_cannot_become_candidate_evidence() -> None:
    plan = _plan(
        job=analysis_with(technologies=[tech("TypeScript")]),
        profile=specialist_profile(),
    )
    refs = {ref.ref.casefold() for ref in plan.selected_evidence_refs}
    assert not any("typescript" in ref for ref in refs)
    assert not any(
        claim.kind == "direct" and "typescript" in claim.statement.casefold()
        for claim in plan.argument_spine
    )


def test_i_key_alignments_cannot_independently_establish_capability() -> None:
    job = specialist_job()
    plan = _plan(job=job, assessment=poisoned_assessment(job))
    item = _need(plan, "AWS Bedrock")
    assert item.classification.status is SupportStatus.SUPPORTED_RELATED
    assert item.classification.may_claim_requested is False


def test_j_direct_classification_has_authoritative_evidence_provenance() -> None:
    item = _need(_plan(), "RAG")
    assert item.evidence_refs
    assert all(ref.ref.startswith(("skill:", "project:", "experience:", "certification:")) for ref in item.evidence_refs)
    assert any(ref.ref == "skill:Retrieval-Augmented Generation" for ref in item.evidence_refs)


def test_k_related_classification_identifies_actual_related_capability() -> None:
    item = _need(_plan(), "AWS Bedrock")
    assert item.classification.promotable_identity == "aws"
    assert item.classification.promotable_profile_label == "AWS"
    assert item.classification.may_claim_requested is False


def test_l_unsupported_classification_has_no_fabricated_evidence() -> None:
    item = _need(_plan(), "chatbots")
    assert item.evidence_refs == ()
    assert item.classification.promotable_identity is None
    assert item.classification.promotable_profile_label is None


def test_m_argument_spine_contains_only_supported_or_framed_gaps() -> None:
    plan = _plan()
    for claim in plan.argument_spine:
        folded = claim.statement.casefold()
        if claim.kind == "direct":
            assert "claim '" in folded
            assert "bedrock" not in folded
            assert "chatbot" not in folded
        elif claim.kind == "related":
            assert folded.startswith("do not claim")
        elif claim.kind == "gap":
            assert folded.startswith("gap:")
            assert "must not be claimed" in folded
        elif claim.kind in {"trajectory", "portfolio"}:
            assert "bedrock experience" not in folded
        else:
            raise AssertionError(f"unexpected spine kind {claim.kind}")


def test_n_trajectory_policy_is_deterministic() -> None:
    first = _plan()
    second = _plan()
    assert first.trajectory_mode == second.trajectory_mode == "ai_lead"
    software = _plan(
        job=analysis_with(family="software_engineering", title="Software Engineer")
    )
    assert software.trajectory_mode == "bridge"


def test_o_adoption_job_uses_full_chapters_trajectory() -> None:
    plan = _plan(job=adoption_job())
    assert plan.trajectory_mode == "full_chapters"
    trajectory = next(claim for claim in plan.argument_spine if claim.kind == "trajectory")
    assert "full_chapters" in trajectory.statement


def test_p_include_methodology_policy_is_deterministic() -> None:
    specialist = _plan()
    assert specialist.include_methodology is True
    infra = _plan(
        job=analysis_with(
            title="AI Infrastructure Engineer",
            technologies=[tech("GPU"), tech("Linux")],
            responsibilities=[],
            experience_requirements=[],
        )
    )
    assert infra.include_methodology is False
    assert _plan().include_methodology == specialist.include_methodology


def test_q_identical_inputs_produce_identical_positioning_plan() -> None:
    first = _plan()
    second = _plan()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_r_synthetic_specialist_case() -> None:
    plan = _plan()
    assert _need(plan, "RAG").classification.status is SupportStatus.SUPPORTED_DIRECT
    bedrock = _need(plan, "AWS Bedrock")
    assert bedrock.classification.status is SupportStatus.SUPPORTED_RELATED
    assert _need(plan, "chatbots").classification.status is SupportStatus.UNSUPPORTED
    blob = " ".join(
        claim.statement
        for claim in plan.argument_spine
        if claim.kind == "direct"
    ).casefold()
    assert "bedrock" not in blob
    assert "chatbot" not in blob
    assert any(ref.ref == "skill:AWS" for ref in bedrock.evidence_refs)


def test_s_locked_master_sections_are_outside_rewrite_authority() -> None:
    plan = _plan()
    assert plan.cv_rewrite_surface == CV_REWRITE_SURFACE
    assert plan.locked_master_sections == LOCKED_MASTER_SECTIONS
    overlap = set(plan.cv_rewrite_surface) & set(plan.locked_master_sections)
    assert overlap == set()
    assert "experience_bullets" in plan.locked_master_sections
    assert "professional_summary" in plan.cv_rewrite_surface
