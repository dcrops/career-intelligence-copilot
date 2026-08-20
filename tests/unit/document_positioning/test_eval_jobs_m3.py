"""M3 offline positioning of frozen E1–E4 jobs. Fixture composer only."""

from __future__ import annotations

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
    FixtureCvPositioningComposer,
    SupportStatus,
)
from tests.unit.document_positioning.helpers import (
    csk_job_analysis,
    csk_job_analysis_path,
    eval_strategy,
    golden_job_analysis,
    golden_output_path,
    live_profile,
)


def _position(job, source_path=None):
    profile = live_profile()
    master = load_master_cv_markdown(DEFAULT_MASTER_CV_PATH)
    tailoring = TailoringPlanService(DeterministicTailoringPlanner()).plan(
        eval_strategy(job, profile, source_path),
        profile,
        options=TailoringOptions(owner_approved_to_tailor=True),
    )
    return BoundedCvPositioningService(FixtureCvPositioningComposer()).compose(
        job,
        profile,
        tailoring,
        master,
    )


def test_e1_allura_ai_lead_without_invented_cloud() -> None:
    result = _position(
        golden_job_analysis("001_strong_ai_engineer"),
        golden_output_path("001_strong_ai_engineer"),
    )
    pack = result.pack
    assert pack.trajectory_mode == "ai_lead"
    assert pack.include_methodology is True
    labels = {item.label.casefold(): item for item in pack.employer_needs}
    assert labels["python"].status is SupportStatus.SUPPORTED_DIRECT
    assert labels["rest apis"].status is SupportStatus.SUPPORTED_DIRECT
    assert labels["llm"].status is SupportStatus.SUPPORTED_DIRECT
    assert labels["google cloud"].status is SupportStatus.UNSUPPORTED
    folded = result.extraction.summary.casefold()
    assert "google cloud" not in folded
    assert "mlops" not in folded
    assert extract_master_summary(load_master_cv_markdown(DEFAULT_MASTER_CV_PATH)) not in (
        result.extraction.summary
    )
    assert result.pack.selected_projects
    relevance = " ".join(item.line for item in result.extraction.project_relevance).casefold()
    assert "bedrock" not in relevance
    assert "google cloud" not in relevance


def test_e2_csk_related_bedrock_not_claimed() -> None:
    result = _position(csk_job_analysis(), csk_job_analysis_path())
    folded = result.extraction.summary.casefold()
    pack = result.pack
    bedrock = next(item for item in pack.employer_needs if "bedrock" in item.label.casefold())
    assert bedrock.status is SupportStatus.SUPPORTED_RELATED
    assert bedrock.may_claim_requested is False
    assert "bedrock experience" not in folded
    assert "aws bedrock experience" not in folded
    assert "chatbot" not in folded
    rag = next(item for item in pack.employer_needs if item.label.casefold() == "rag")
    assert rag.status is SupportStatus.SUPPORTED_DIRECT
    assert pack.include_methodology is True
    assert "AWS" in pack.related_profile_labels
    assert pack.selected_projects
    relevance = " ".join(item.line for item in result.extraction.project_relevance).casefold()
    assert "bedrock" not in relevance
    assert "chatbot" not in relevance


def test_e3_maincode_does_not_over_position_infrastructure() -> None:
    result = _position(
        golden_job_analysis("012_maincode_ai_infrastructure_engineer"),
        golden_output_path("012_maincode_ai_infrastructure_engineer"),
    )
    folded = result.extraction.summary.casefold()
    pack = result.pack
    assert pack.include_methodology is False
    assert "AI Engineering Methodology" not in result.markdown
    for label in ("gpu", "linux", "hpc"):
        need = next(item for item in pack.employer_needs if item.label.casefold() == label)
        assert need.status is SupportStatus.UNSUPPORTED
        assert label not in folded
    assert pack.selected_projects
    relevance = " ".join(item.line for item in result.extraction.project_relevance).casefold()
    assert "gpu" not in relevance
    assert "hpc" not in relevance
    experience = extract_h2_section(result.markdown, "professional experience")
    master = extract_h2_section(
        load_master_cv_markdown(DEFAULT_MASTER_CV_PATH), "professional experience"
    )
    assert experience == master


def test_e4_repurpose_full_chapters_without_copilot_claim() -> None:
    result = _position(
        golden_job_analysis("008_repurpose_it_ai_adoption_specialist"),
        golden_output_path("008_repurpose_it_ai_adoption_specialist"),
    )
    folded = result.extraction.summary.casefold()
    assert result.pack.trajectory_mode == "full_chapters"
    assert result.pack.include_methodology is True
    assert "github copilot" not in folded
    assert "claude" not in folded
    assert "tester" in folded or "qa" in folded
    assert "data engineer" in folded
    relevance = " ".join(item.line for item in result.extraction.project_relevance).casefold()
    assert "github copilot" not in relevance
    assert "claude" not in relevance
