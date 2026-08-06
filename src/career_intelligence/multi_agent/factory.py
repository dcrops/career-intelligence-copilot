"""Build a live DeterministicOrchestrationSupervisor (FR-016 M3)."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.agent.factory import build_agent_runtime

from .bopa_adapter import BopaSpecialistAdapter
from .json_store import DEFAULT_ORCHESTRATION_RUNS_ROOT, JsonDirectoryOrchestrationStore
from .observation import ReadinessObservationBuilder
from .obs_runtime import ObsRuntime
from .supervisor import DeterministicOrchestrationSupervisor
from .types import DEFAULT_MAX_ORCHESTRATION_STEPS


def build_orchestration_supervisor(
    *,
    opportunities_dir: Path | None = None,
    packages_dir: Path | None = None,
    preparation_runs_dir: Path | None = None,
    agent_runs_dir: Path | None = None,
    orchestration_runs_dir: Path | None = None,
    truth_reports_dir: Path | None = None,
    profile_path: Path | None = None,
    cv_output_dir: Path | None = None,
    cover_letter_output_dir: Path | None = None,
    use_llm_proposer: bool = False,
    max_steps: int = DEFAULT_MAX_ORCHESTRATION_STEPS,
    override_material_benefit: bool = False,
) -> tuple[DeterministicOrchestrationSupervisor, JsonDirectoryOrchestrationStore]:
    """Assemble DOS over live readiness + BOPA adapter + JSON orchestration store.

    BOPA ToolPolicy / allow-list are unchanged (via ``build_agent_runtime``).
    """
    agent_runtime = build_agent_runtime(
        opportunities_dir=opportunities_dir,
        packages_dir=packages_dir,
        preparation_runs_dir=preparation_runs_dir,
        agent_runs_dir=agent_runs_dir,
        truth_reports_dir=truth_reports_dir,
        profile_path=profile_path,
        cv_output_dir=cv_output_dir,
        cover_letter_output_dir=cover_letter_output_dir,
        use_llm_proposer=use_llm_proposer,
        override_material_benefit=override_material_benefit,
    )
    # Reuse the same readiness builder instance from the agent runtime.
    observation = ReadinessObservationBuilder(agent_runtime._readiness)  # noqa: SLF001
    store = JsonDirectoryOrchestrationStore(
        orchestration_runs_dir
        if orchestration_runs_dir is not None
        else DEFAULT_ORCHESTRATION_RUNS_ROOT
    )
    supervisor = DeterministicOrchestrationSupervisor(
        observation_builder=observation,
        bopa_adapter=BopaSpecialistAdapter(agent_runtime),
        obs_runtime=ObsRuntime(),
        store=store,
        max_steps=max_steps,
    )
    return supervisor, store
