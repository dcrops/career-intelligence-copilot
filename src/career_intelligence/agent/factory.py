"""Build a live AgentRuntime from store paths (FR-015 M3)."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.application_preparation import ApplicationPreparationOrchestrator
from career_intelligence.candidate_contact import load_candidate_contact
from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterPlanOptions,
)
from career_intelligence.cv_generation import CvGenerationOptions, TailoringOptions
from career_intelligence.opportunities import OpportunityService
from career_intelligence.profile import CareerProfileService
from career_intelligence.truth_validation import JsonDirectoryTruthReportStore

from .adapters import ServiceActionExecutor
from .json_store import DEFAULT_AGENT_RUNS_ROOT, JsonDirectoryAgentRunStore
from .proposer import DeterministicActionProposer, OpenAIActionProposer
from .readiness import LiveReadinessBuilder
from .runtime import AgentRuntime
from .types import DEFAULT_MAX_STEPS


def build_agent_runtime(
    *,
    opportunities_dir: Path | None = None,
    packages_dir: Path | None = None,
    preparation_runs_dir: Path | None = None,
    agent_runs_dir: Path | None = None,
    truth_reports_dir: Path | None = None,
    profile_path: Path | None = None,
    cv_output_dir: Path | None = None,
    cover_letter_output_dir: Path | None = None,
    use_llm_proposer: bool = False,
    max_steps: int = DEFAULT_MAX_STEPS,
    override_material_benefit: bool = False,
) -> AgentRuntime:
    """Assemble LiveReadinessBuilder + ServiceActionExecutor + store + proposer."""
    opportunities = (
        OpportunityService.from_path(opportunities_dir)
        if opportunities_dir is not None
        else OpportunityService()
    )
    profile_service = (
        CareerProfileService.from_path(profile_path)
        if profile_path is not None
        else CareerProfileService()
    )
    profile = profile_service.load()
    packages = ApplicationPackageService(
        opportunities,
        profile=profile,
        packages_root=packages_dir,
        cv_output_dir=cv_output_dir,
        cover_letter_output_dir=cover_letter_output_dir,
    )
    preparation = ApplicationPreparationOrchestrator(
        opportunities,
        packages,
        runs_root=preparation_runs_dir,
    )
    truth_store = JsonDirectoryTruthReportStore(truth_reports_dir)
    readiness = LiveReadinessBuilder(
        opportunities,
        packages,
        profile=profile,
        truth_store=truth_store,
    )
    contact = load_candidate_contact()
    executor = ServiceActionExecutor(
        preparation=preparation,
        packages=packages,
        profile=profile,
        truth_store=truth_store,
        tailoring_options=TailoringOptions(
            owner_approved_to_tailor=True,
            override_material_benefit=override_material_benefit,
        ),
        cv_options=CvGenerationOptions(
            tailoring_plan_approved=True,
            contact=contact,
        ),
        cover_letter_plan_options=CoverLetterPlanOptions(
            owner_approved_to_plan=True,
            override_material_benefit=override_material_benefit,
        ),
        cover_letter_options=CoverLetterGenerationOptions(
            cover_letter_plan_approved=True,
            contact=contact,
        ),
    )
    store = JsonDirectoryAgentRunStore(
        agent_runs_dir if agent_runs_dir is not None else DEFAULT_AGENT_RUNS_ROOT
    )
    proposer = (
        OpenAIActionProposer() if use_llm_proposer else DeterministicActionProposer()
    )
    return AgentRuntime(
        readiness=readiness,
        executor=executor,
        proposer=proposer,
        store=store,
        max_steps=max_steps,
    )
