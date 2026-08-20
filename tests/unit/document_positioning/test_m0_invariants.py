"""M0 architectural freezes: eval fixtures exist; catalogue is not production-wired."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

_PRODUCTION_SCAN_DIRS = (
    REPO / "src" / "career_intelligence" / "cv_generation",
    REPO / "src" / "career_intelligence" / "cover_letter",
    REPO / "src" / "career_intelligence" / "application_package",
    REPO / "src" / "career_intelligence" / "cli",
)

_EVAL_FIXTURES = (
    REPO / "manual_validation" / "jobs" / "001_strong_ai_engineer.txt",
    REPO / "manual_validation" / "outputs" / "001_strong_ai_engineer.json",
    REPO
    / "tests"
    / "fixtures"
    / "document_positioning"
    / "eval_jobs"
    / "02_csk_mixed_fit"
    / "job.txt",
    REPO
    / "tests"
    / "fixtures"
    / "document_positioning"
    / "eval_jobs"
    / "02_csk_mixed_fit"
    / "meta.json",
    REPO / "manual_validation" / "jobs" / "012_maincode_ai_infrastructure_engineer.txt",
    REPO
    / "manual_validation"
    / "outputs"
    / "012_maincode_ai_infrastructure_engineer.json",
    REPO / "manual_validation" / "jobs" / "008_repurpose_it_ai_adoption_specialist.txt",
    REPO
    / "manual_validation"
    / "outputs"
    / "008_repurpose_it_ai_adoption_specialist.json",
    REPO / "data" / "career_profile.yaml",
    REPO / "career-documents" / "cv" / "master_ai_engineer_cv.md",
)


def test_frozen_evaluation_fixtures_exist() -> None:
    missing = [str(path) for path in _EVAL_FIXTURES if not path.is_file()]
    assert missing == []


def test_csk_tracked_freeze_is_the_eval_job_not_live_artifacts() -> None:
    freeze = (
        REPO
        / "tests"
        / "fixtures"
        / "document_positioning"
        / "eval_jobs"
        / "02_csk_mixed_fit"
        / "job.txt"
    )
    text = freeze.read_text(encoding="utf-8")
    assert "AWS Bedrock" in text
    assert "retrieval‑augmented generation (RAG)" in text or "RAG" in text
    assert "chatbots" in text.casefold()


def test_production_document_path_does_not_import_positioning_catalogue() -> None:
    hits: list[str] = []
    for root in _PRODUCTION_SCAN_DIRS:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            if "document_positioning" in source:
                hits.append(str(path.relative_to(REPO)))
    assert hits == []
