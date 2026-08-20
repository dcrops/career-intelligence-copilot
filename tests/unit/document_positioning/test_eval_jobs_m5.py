"""M5 frozen E1–E4 identities — not a preference evaluation."""

from __future__ import annotations

from career_intelligence.document_positioning.benchmark.jobs import (
    FROZEN_EVAL_JOBS,
    load_advertisement,
    load_job_analysis,
)


def test_four_frozen_jobs_are_distinct() -> None:
    analyses = [load_job_analysis(job) for job in FROZEN_EVAL_JOBS]
    companies = [item.posting.company for item in analyses]
    titles = [item.posting.title for item in analyses]
    assert len(set(companies)) == 4
    assert len(set(titles)) >= 3
    ads = [load_advertisement(job) for job in FROZEN_EVAL_JOBS]
    assert len(set(ads)) == 4


def test_e1_is_allura_not_live_repurpose_ai_engineer() -> None:
    job = FROZEN_EVAL_JOBS[0]
    analysis = load_job_analysis(job)
    assert analysis.posting.company
    assert "allura" in analysis.posting.company.casefold()
    assert "001_strong_ai_engineer" in str(job.analysis_path)


def test_e2_uses_tracked_csk_freeze() -> None:
    job = FROZEN_EVAL_JOBS[1]
    text = load_advertisement(job)
    assert "AWS Bedrock" in text
    assert "chatbots" in text.casefold()
    assert job.opportunity_id == "opp_01M0E6GQ9XQH9DK9N5T0MS67N0"
    assert "eval_jobs" in str(job.analysis_path)


def test_e3_is_maincode_infrastructure() -> None:
    job = FROZEN_EVAL_JOBS[2]
    analysis = load_job_analysis(job)
    assert analysis.posting.company
    assert "maincode" in analysis.posting.company.casefold()


def test_e4_is_repurpose_adoption_specialist() -> None:
    job = FROZEN_EVAL_JOBS[3]
    analysis = load_job_analysis(job)
    title = (analysis.posting.title or "").casefold()
    assert "adoption" in title or "repurpose" in (analysis.posting.company or "").casefold()
    assert "008_repurpose" in str(job.analysis_path)


def test_e1_cv_pack_excludes_public_holiday() -> None:
    """Live E1 fail-closed named this Master project; it is not packed."""
    from career_intelligence.cv_generation import (
        DeterministicTailoringPlanner,
        TailoringOptions,
        TailoringPlanService,
    )
    from career_intelligence.cv_generation.master_adapt import (
        DEFAULT_MASTER_CV_PATH,
        load_master_cv_markdown,
    )
    from career_intelligence.document_positioning import (
        build_cv_positioning_pack,
        build_positioning_plan,
    )
    from career_intelligence.document_positioning.benchmark.jobs import eval_strategy
    from tests.unit.document_positioning.helpers import live_profile

    job = FROZEN_EVAL_JOBS[0]
    profile = live_profile()
    analysis = load_job_analysis(job)
    master = load_master_cv_markdown(DEFAULT_MASTER_CV_PATH)
    tailoring = TailoringPlanService(DeterministicTailoringPlanner()).plan(
        eval_strategy(analysis, profile, job.analysis_path),
        profile,
        options=TailoringOptions(owner_approved_to_tailor=True),
    )
    pack = build_cv_positioning_pack(
        analysis,
        profile,
        build_positioning_plan(analysis, profile),
        tailoring,
        master,
    )
    names = {item.name.casefold() for item in pack.selected_projects}
    assert "public holiday entitlements application" not in names
    assert names
