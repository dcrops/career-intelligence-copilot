"""M4 offline cover-letter positioning of frozen E1–E4 jobs. Fixture composer only."""

from __future__ import annotations

from career_intelligence.document_positioning import (
    BoundedCoverLetterPositioningService,
    FixtureCoverLetterPositioningComposer,
    MAX_SOURCE_COUNT,
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
    return BoundedCoverLetterPositioningService(
        FixtureCoverLetterPositioningComposer()
    ).compose(
        job,
        profile,
        strategy=eval_strategy(job, profile, source_path),
    )


def test_e1_allura_ai_lead_without_invented_cloud() -> None:
    result = _position(
        golden_job_analysis("001_strong_ai_engineer"),
        golden_output_path("001_strong_ai_engineer"),
    )
    pack = result.pack
    assert pack.trajectory_mode == "ai_lead"
    folded = " ".join(result.paragraphs).casefold()
    assert "google cloud" not in folded
    assert "mlops" not in folded
    assert "i am excited" not in folded
    assert "python" in folded or "rest" in folded or "llm" in folded
    assert len(pack.selected_sources) <= MAX_SOURCE_COUNT
    labels = {item.label.casefold(): item for item in pack.employer_needs}
    assert labels["python"].status is SupportStatus.SUPPORTED_DIRECT
    assert labels["llm"].status is SupportStatus.SUPPORTED_DIRECT
    types = {item.source_type for item in pack.selected_sources}
    assert "trajectory" not in types or pack.trajectory_mode != "ai_lead"


def test_e2_csk_related_bedrock_not_claimed() -> None:
    result = _position(csk_job_analysis(), csk_job_analysis_path())
    folded = " ".join(result.paragraphs).casefold()
    pack = result.pack
    bedrock = next(item for item in pack.employer_needs if "bedrock" in item.label.casefold())
    assert bedrock.status is SupportStatus.SUPPORTED_RELATED
    assert "bedrock experience" not in folded
    assert "aws bedrock experience" not in folded
    assert "chatbot" not in folded
    rag = next(item for item in pack.employer_needs if item.label.casefold() == "rag")
    assert rag.status is SupportStatus.SUPPORTED_DIRECT
    assert "AWS" in pack.related_profile_labels
    covered = {
        label.casefold()
        for source in pack.selected_sources
        for label in source.employer_needs_covered
    }
    assert "rag" in covered or any("retrieval" in item for item in covered)
    assert any(
        "bedrock" in " ".join(source.employer_needs_covered).casefold()
        or "aws" in " ".join(source.technologies).casefold()
        or source.source_type == "employment"
        for source in pack.selected_sources
    )


def test_e3_maincode_does_not_over_position_infrastructure() -> None:
    result = _position(
        golden_job_analysis("012_maincode_ai_infrastructure_engineer"),
        golden_output_path("012_maincode_ai_infrastructure_engineer"),
    )
    folded = " ".join(result.paragraphs).casefold()
    pack = result.pack
    for label in ("gpu", "linux", "hpc"):
        need = next(item for item in pack.employer_needs if item.label.casefold() == label)
        assert need.status is SupportStatus.UNSUPPORTED
        if label in folded:
            assert "do not claim" in folded or "not claim" in folded
    assert "infrastructure engineer employment" not in folded
    assert pack.selected_sources
    assert len(pack.selected_sources) <= MAX_SOURCE_COUNT


def test_e4_repurpose_full_chapters_without_copilot_claim() -> None:
    result = _position(
        golden_job_analysis("008_repurpose_it_ai_adoption_specialist"),
        golden_output_path("008_repurpose_it_ai_adoption_specialist"),
    )
    folded = " ".join(result.paragraphs).casefold()
    assert result.pack.trajectory_mode == "full_chapters"
    assert "github copilot" not in folded
    assert "claude" not in folded
    assert "tester" in folded or "qa" in folded or "testing" in folded
    assert "data engineer" in folded
    types = [item.source_type for item in result.pack.selected_sources]
    assert "trajectory" in types
