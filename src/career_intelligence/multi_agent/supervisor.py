"""Deterministic Orchestration Supervisor runtime (FR-016 M2).

DOS delegates only. It does not call mutating domain services, bypass specialist
ToolPolicy, waive truth, submit, or advance pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime

from career_intelligence.agent.errors import AgentProviderError

from .bopa_adapter import BopaSpecialistAdapter
from .briefing import select_next_specialist
from .delegation_policy import (
    evaluate_delegation_policy,
    handoff_idempotency_key,
)
from .errors import DomainWorkForbiddenError, OrchestrationRuntimeError
from .ids import (
    new_handoff_id,
    new_orchestration_audit_event_id,
    new_orchestration_run_id,
)
from .json_store import JsonDirectoryOrchestrationStore
from .memory_store import InMemoryOrchestrationStore
from .models import (
    Handoff,
    OrchestrationAuditEvent,
    OrchestrationGoal,
    OrchestrationObservation,
    OrchestrationRun,
    SpecialistDelegationProposal,
    SpecialistVisitRecord,
)
from .observation import ObservationBuilder
from .obs_runtime import ObsRuntime
from .types import (
    DEFAULT_MAX_ORCHESTRATION_STEPS,
    DEFAULT_MAX_VISITS_PER_SPECIALIST,
    OrchestrationStopReason,
    SpecialistId,
)

_BOPA_AWAITING: frozenset[str] = frozenset(
    {
        "completed_for_owner_review",
        "owner_approval_required",
        "clarification_required",
        "truth_validation_blocked",
        "material_benefit_required",
    }
)

OrchestrationStore = InMemoryOrchestrationStore | JsonDirectoryOrchestrationStore


class DeterministicOrchestrationSupervisor:
    """DOS: observe → select → handoff → specialist → audit → stop/continue."""

    def __init__(
        self,
        *,
        observation_builder: ObservationBuilder,
        bopa_adapter: BopaSpecialistAdapter | None = None,
        obs_runtime: ObsRuntime | None = None,
        store: OrchestrationStore | None = None,
        max_steps: int = DEFAULT_MAX_ORCHESTRATION_STEPS,
        max_visits_per_specialist: int = DEFAULT_MAX_VISITS_PER_SPECIALIST,
    ) -> None:
        self._observation = observation_builder
        self._bopa = bopa_adapter
        self._obs = obs_runtime or ObsRuntime()
        self._store: OrchestrationStore = store or InMemoryOrchestrationStore()
        self._max_steps = max_steps
        self._max_visits = max_visits_per_specialist

    def get(self, orchestration_run_id: str) -> OrchestrationRun:
        return self._store.load(orchestration_run_id)

    def get_handoff(self, handoff_id: str) -> Handoff:
        return self._store.load_handoff(handoff_id)

    def get_brief(self, brief_id: str):
        return self._store.load_brief(brief_id)

    def attempt_domain_work(self, *_args: object, **_kwargs: object) -> None:
        """Hard forbid — DOS must never perform domain work."""
        raise DomainWorkForbiddenError(
            "DOS delegates only; domain work is forbidden on the supervisor"
        )

    def start(
        self,
        goal: OrchestrationGoal,
        *,
        owner_approvals_present: bool = False,
        provider_available: bool = True,
    ) -> OrchestrationRun:
        now = _now()
        run = OrchestrationRun(
            orchestration_run_id=new_orchestration_run_id(),
            goal=goal,
            status="running",
            step_count=0,
            max_steps=self._max_steps,
            max_visits_per_specialist=self._max_visits,
            owner_approvals_present=owner_approvals_present,
            provider_available=provider_available,
            created_at=now,
            updated_at=now,
        )
        run = self._append_event(
            run,
            kind="orchestration_started",
            message=f"goal={goal.goal_kind} opportunity={goal.opportunity_id}",
        )
        run = self._store.save(run)
        return self._loop(run)

    def resume(
        self,
        orchestration_run_id: str,
        *,
        owner_approvals_present: bool | None = None,
        provider_available: bool | None = None,
    ) -> OrchestrationRun:
        run = self._store.load(orchestration_run_id)
        if run.status not in {"awaiting_owner", "running"}:
            raise OrchestrationRuntimeError(
                f"cannot resume orchestration in status {run.status!r}"
            )
        updates: dict[str, object] = {
            "status": "running",
            "stop_reason": None,
            "owner_action_required": None,
            "active_specialist": None,
            "active_handoff_id": None,
            "updated_at": _now(),
        }
        if owner_approvals_present is not None:
            updates["owner_approvals_present"] = owner_approvals_present
        if provider_available is not None:
            updates["provider_available"] = provider_available
        run = run.model_copy(update=updates)
        run = self._append_event(
            run,
            kind="state_observed",
            message=f"resume {orchestration_run_id}",
            refs=(orchestration_run_id,),
        )
        run = self._store.save(run)
        return self._loop(run, resuming=True)

    def _loop(self, run: OrchestrationRun, *, resuming: bool = False) -> OrchestrationRun:
        last_hash: str | None = None
        unchanged_rounds = 0
        while run.status == "running":
            if run.step_count >= run.max_steps:
                return self._stop(run, "orchestration_max_steps", status="failed")

            observation = self._observe(run)
            run = run.model_copy(
                update={"last_observation": observation, "updated_at": _now()}
            )
            run = self._append_event(
                run,
                kind="state_observed",
                message=f"hash={observation.observation_hash}",
                refs=(
                    f"package:{observation.package_status}",
                    f"truth:{observation.truth_status}",
                    f"pipeline:{observation.pipeline_status}",
                ),
            )

            if observation.observation_hash == last_hash:
                unchanged_rounds += 1
            else:
                unchanged_rounds = 0
                last_hash = observation.observation_hash
            if unchanged_rounds >= 2 and not resuming:
                return self._stop(run, "no_progress", status="failed")
            resuming = False

            visits = {v.specialist_id: v.visit_count for v in run.specialist_visits}
            obs_done = self._obs_completed_for_hash(run, observation.observation_hash)
            bopa_done = self._bopa_completed(run)
            target = select_next_specialist(
                observation,
                run.goal,
                specialist_visit_counts=visits,
                obs_completed_for_hash=obs_done,
                bopa_completed=bopa_done,
            )
            run = self._append_event(
                run,
                kind="specialist_considered",
                specialist_id=target,
                message=f"selected={target!r} approved visits={visits}",
            )

            if target is None:
                return self._stop_without_specialist(run, observation)

            run = self._append_event(
                run,
                kind="specialist_selected",
                specialist_id=target,
                message=f"delegate to {target}",
            )
            run = self._delegate(run, observation, target)
            if run.status != "running":
                return run

        return run

    def _observe(self, run: OrchestrationRun) -> OrchestrationObservation:
        return self._observation.build(
            run.goal,
            owner_approvals_present=run.owner_approvals_present,
            provider_available=run.provider_available,
            prior_agent_run_ids=run.child_agent_run_ids,
            prior_orchestration_run_id=run.orchestration_run_id,
        )

    def _delegate(
        self,
        run: OrchestrationRun,
        observation: OrchestrationObservation,
        target: SpecialistId,
    ) -> OrchestrationRun:
        requested_goal = (
            "brief_opportunity_readiness"
            if target == "obs"
            else "prepare_for_owner_review"
        )
        proposal = SpecialistDelegationProposal(
            target_specialist=target,
            rationale=f"deterministic selection of {target}",
            requested_goal_kind=requested_goal,
            evidence_refs=(f"hash:{observation.observation_hash}",),
        )
        # Owner notes / untrusted text never affect policy inputs.
        visits = {v.specialist_id: v.visit_count for v in run.specialist_visits}
        path = self._delegation_path(run)
        recent_keys = self._recent_delegation_keys(run)

        decision = evaluate_delegation_policy(
            run.goal,
            observation,
            proposal,
            step_count=run.step_count,
            max_steps=run.max_steps,
            specialist_visit_counts=visits,
            max_visits_per_specialist=run.max_visits_per_specialist,
            recent_delegation_keys=recent_keys,
            delegation_path=path,
            owner_approvals_present=run.owner_approvals_present,
        )

        handoff = Handoff(
            handoff_id=new_handoff_id(),
            orchestration_run_id=run.orchestration_run_id,
            source="supervisor",
            target_specialist=target,
            opportunity_id=run.goal.opportunity_id,
            requested_goal_kind=requested_goal,
            observed_state_hash=observation.observation_hash,
            expected_output_kind=(
                "operational_brief" if target == "obs" else "agent_run_result"
            ),
            owner_approval_status=(
                "present" if run.owner_approvals_present else "missing"
            ),
            policy_decision=decision.decision,
            policy_deny_reason=decision.deny_reason,
            reason=proposal.rationale,
            acceptance="pending",
            idempotency_key=handoff_idempotency_key(
                run.orchestration_run_id,
                target,
                requested_goal,
                observation.observation_hash,
            ),
            created_at=_now(),
        )

        if decision.decision == "deny":
            handoff = handoff.model_copy(
                update={
                    "acceptance": "policy_blocked",
                    "acceptance_reason": decision.deny_reason,
                    "resolved_at": _now(),
                }
            )
            self._store.save_handoff(handoff)
            run = run.model_copy(
                update={
                    "handoff_ids": run.handoff_ids + (handoff.handoff_id,),
                    "step_count": run.step_count + 1,
                    "updated_at": _now(),
                }
            )
            run = self._append_event(
                run,
                kind="delegation_blocked",
                specialist_id=target,
                handoff_id=handoff.handoff_id,
                policy_decision="deny",
                stop_reason=decision.stop_reason,
                message=decision.deny_reason,
            )
            stop = decision.stop_reason or "delegation_blocked"
            status = "awaiting_owner" if stop == "owner_approval_required" else "failed"
            return self._stop(run, stop, status=status)

        handoff = handoff.model_copy(update={"acceptance": "accepted"})
        self._store.save_handoff(handoff)
        run = run.model_copy(
            update={
                "handoff_ids": run.handoff_ids + (handoff.handoff_id,),
                "active_specialist": target,
                "active_handoff_id": handoff.handoff_id,
                "step_count": run.step_count + 1,
                "updated_at": _now(),
            }
        )
        run = self._append_event(
            run,
            kind="delegation_allowed",
            specialist_id=target,
            handoff_id=handoff.handoff_id,
            policy_decision="allow",
        )
        run = self._append_event(
            run,
            kind="handoff_created",
            specialist_id=target,
            handoff_id=handoff.handoff_id,
            message=handoff.idempotency_key,
        )
        run = self._append_event(
            run,
            kind="handoff_accepted",
            specialist_id=target,
            handoff_id=handoff.handoff_id,
        )
        run = self._store.save(run)

        if target == "obs":
            return self._run_obs(run, handoff, observation)
        return self._run_bopa(run, handoff)

    def _run_obs(
        self,
        run: OrchestrationRun,
        handoff: Handoff,
        observation: OrchestrationObservation,
    ) -> OrchestrationRun:
        # Skip regenerate if brief already exists for same hash.
        if run.last_brief_id is not None:
            try:
                prior = self._store.load_brief(run.last_brief_id)
                if (
                    prior.observation_hash
                    and prior.observation_hash == observation.observation_hash
                ):
                    handoff = handoff.model_copy(
                        update={
                            "acceptance": "completed",
                            "child_brief_id": prior.brief_id,
                            "resolved_at": _now(),
                        }
                    )
                    self._store.save_handoff(handoff)
                    run = self._record_visit(run, "obs", handoff.handoff_id, observation)
                    run = self._append_event(
                        run,
                        kind="specialist_completed",
                        specialist_id="obs",
                        handoff_id=handoff.handoff_id,
                        message="brief unchanged; skipped regenerate",
                        refs=(prior.brief_id,),
                    )
                    return self._stop(
                        run,
                        "briefing_complete",
                        status="awaiting_owner",
                        owner_action=prior.owner_action_summary,
                    )
            except Exception:  # noqa: BLE001
                pass

        handoff = handoff.model_copy(update={"acceptance": "executing"})
        self._store.save_handoff(handoff)
        run = self._append_event(
            run,
            kind="specialist_started",
            specialist_id="obs",
            handoff_id=handoff.handoff_id,
        )
        brief = self._obs.execute(handoff, run.goal, observation)
        brief = brief.model_copy(
            update={"orchestration_run_id": run.orchestration_run_id}
        )
        self._store.save_brief(brief)
        handoff = handoff.model_copy(
            update={
                "acceptance": "completed",
                "child_brief_id": brief.brief_id,
                "resolved_at": _now(),
            }
        )
        self._store.save_handoff(handoff)
        run = run.model_copy(
            update={
                "last_brief_id": brief.brief_id,
                "active_specialist": None,
                "active_handoff_id": None,
                "updated_at": _now(),
            }
        )
        run = self._record_visit(run, "obs", handoff.handoff_id, observation)
        run = self._append_event(
            run,
            kind="specialist_completed",
            specialist_id="obs",
            handoff_id=handoff.handoff_id,
            refs=(brief.brief_id,),
            message=brief.owner_action_summary[:500],
        )
        run = self._store.save(run)

        # Brief-only / pipeline-advises / ambiguity → stop after OBS.
        # Post-BOPA synthesis → stop with mapped owner action.
        # Brief-before-mutate with BOPA still needed → continue loop.
        needs = observation.briefing_need_classes or ()
        if run.goal.goal_kind == "brief_opportunity_readiness" or run.goal.brief_only:
            return self._stop(
                run,
                "briefing_complete",
                status="awaiting_owner",
                owner_action=brief.owner_action_summary,
            )
        if any(
            n in needs
            for n in (
                "pipeline_advises_against_preparation",
                "cross_surface_ambiguity",
            )
        ):
            return self._stop(
                run,
                "briefing_complete",
                status="awaiting_owner",
                owner_action=brief.owner_action_summary,
            )
        if "truth_blockers_need_synthesis" in needs and self._bopa_completed(run):
            return self._stop(
                run,
                "truth_validation_blocked",
                status="awaiting_owner",
                owner_action=brief.owner_action_summary,
            )
        if "post_specialist_synthesis" in needs and self._bopa_completed(run):
            # Map from last BOPA stop if available.
            stop = self._map_bopa_stop(run) or "completed_for_owner_review"
            return self._stop(
                run,
                stop,
                status="awaiting_owner",
                owner_action=brief.owner_action_summary,
            )
        # Otherwise continue (e.g. OBS then BOPA) — mark obs done for hash via visit.
        return run

    def _run_bopa(self, run: OrchestrationRun, handoff: Handoff) -> OrchestrationRun:
        if self._bopa is None:
            handoff = handoff.model_copy(
                update={
                    "acceptance": "stopped",
                    "acceptance_reason": "bopa adapter unavailable",
                    "resolved_at": _now(),
                }
            )
            self._store.save_handoff(handoff)
            return self._stop(run, "specialist_unavailable", status="failed")

        handoff = handoff.model_copy(update={"acceptance": "executing"})
        self._store.save_handoff(handoff)
        run = self._append_event(
            run,
            kind="specialist_started",
            specialist_id="bopa",
            handoff_id=handoff.handoff_id,
        )

        resume_id = None
        if run.child_agent_run_ids:
            # Resume incomplete child if last status was awaiting/running.
            last_id = run.child_agent_run_ids[-1]
            try:
                prior = self._bopa._runtime.get(last_id)  # noqa: SLF001 — thin reuse
                if prior.status in {"awaiting_owner", "running"}:
                    resume_id = last_id
            except Exception:  # noqa: BLE001
                resume_id = None

        try:
            result = self._bopa.execute(
                handoff,
                owner_approvals_present=run.owner_approvals_present,
                provider_available=run.provider_available,
                resume_agent_run_id=resume_id,
            )
        except AgentProviderError as error:
            handoff = handoff.model_copy(
                update={
                    "acceptance": "stopped",
                    "acceptance_reason": str(error),
                    "resolved_at": _now(),
                }
            )
            self._store.save_handoff(handoff)
            run = self._append_event(
                run,
                kind="error_recorded",
                specialist_id="bopa",
                handoff_id=handoff.handoff_id,
                message=str(error),
            )
            return self._stop(run, "provider_unavailable", status="failed")

        child = result.agent_run
        child_ids = run.child_agent_run_ids
        if child.agent_run_id not in child_ids:
            child_ids = child_ids + (child.agent_run_id,)  # type: ignore[operator]

        handoff = handoff.model_copy(
            update={
                "acceptance": "completed" if result.status != "failed" else "stopped",
                "acceptance_reason": result.stop_reason
                if result.status == "failed"
                else None,
                "child_agent_run_id": child.agent_run_id,
                "resolved_at": _now(),
            }
        )
        # stopped requires acceptance_reason
        if handoff.acceptance == "stopped" and handoff.acceptance_reason is None:
            handoff = handoff.model_copy(
                update={"acceptance_reason": result.stop_reason or "bopa_failed"}
            )
        self._store.save_handoff(handoff)

        observation = run.last_observation
        run = run.model_copy(
            update={
                "child_agent_run_ids": child_ids,
                "active_specialist": None,
                "active_handoff_id": None,
                "updated_at": _now(),
            }
        )
        if observation is not None:
            run = self._record_visit(run, "bopa", handoff.handoff_id, observation)
        run = self._append_event(
            run,
            kind="specialist_completed"
            if result.status != "failed"
            else "specialist_stopped",
            specialist_id="bopa",
            handoff_id=handoff.handoff_id,
            stop_reason=_map_agent_stop(result.stop_reason),
            refs=(child.agent_run_id,),
            message=f"bopa status={result.status} stop={result.stop_reason}",
        )
        run = self._store.save(run)

        if result.status == "failed":
            stop = _map_agent_stop(result.stop_reason) or "unexpected_failure"
            return self._stop(run, stop, status="failed")

        # Continue to OBS for synthesis only when owner requested it.
        if (
            run.goal.goal_kind == "coordinate_opportunity_readiness"
            and not run.goal.brief_only
            and run.goal.synthesize_after_prepare
            and result.stop_reason in _BOPA_AWAITING
        ):
            return run  # loop continues → OBS post synthesis

        stop = _map_agent_stop(result.stop_reason) or "completed_for_owner_review"
        status = "awaiting_owner" if result.stop_reason in _BOPA_AWAITING else "failed"
        return self._stop(run, stop, status=status)

    def _stop_without_specialist(
        self,
        run: OrchestrationRun,
        observation: OrchestrationObservation,
    ) -> OrchestrationRun:
        if run.last_brief_id is not None:
            return self._stop(
                run,
                "briefing_complete",
                status="awaiting_owner",
                owner_action="Review the latest operational brief.",
            )
        if self._bopa_completed(run):
            stop = self._map_bopa_stop(run) or "completed_for_owner_review"
            return self._stop(run, stop, status="awaiting_owner")
        if observation.readiness_primary_state_class in {
            "missing_analysis",
            "missing_assessment",
            "missing_portfolio_match",
            "missing_strategy",
        }:
            return self._stop(run, "invalid_state", status="failed")
        return self._stop(run, "unsupported_state", status="failed")

    def _stop(
        self,
        run: OrchestrationRun,
        reason: OrchestrationStopReason,
        *,
        status: str,
        owner_action: str | None = None,
    ) -> OrchestrationRun:
        awaiting = {
            "briefing_complete",
            "completed_for_owner_review",
            "owner_approval_required",
            "clarification_required",
            "truth_validation_blocked",
            "material_benefit_required",
        }
        if status == "awaiting_owner" and reason not in awaiting and owner_action is None:
            owner_action = f"Orchestration stopped: {reason}"
        run = run.model_copy(
            update={
                "status": status,
                "stop_reason": reason,
                "owner_action_required": owner_action,
                "active_specialist": None,
                "active_handoff_id": None,
                "checkpoint_ref": f"checkpoint:{run.orchestration_run_id}:{run.step_count}",
                "updated_at": _now(),
            }
        )
        run = self._append_event(
            run,
            kind="owner_gate_reached" if status == "awaiting_owner" else "orchestration_stop_recorded",
            stop_reason=reason,
            message=owner_action,
        )
        if status != "awaiting_owner":
            run = self._append_event(
                run,
                kind="orchestration_stop_recorded",
                stop_reason=reason,
            )
        return self._store.save(run)

    def _append_event(
        self,
        run: OrchestrationRun,
        *,
        kind: str,
        specialist_id: SpecialistId | None = None,
        handoff_id: str | None = None,
        policy_decision: str | None = None,
        stop_reason: OrchestrationStopReason | None = None,
        message: str | None = None,
        refs: tuple[str, ...] = (),
    ) -> OrchestrationRun:
        event = OrchestrationAuditEvent(
            event_id=new_orchestration_audit_event_id(),
            kind=kind,  # type: ignore[arg-type]
            at=_now(),
            specialist_id=specialist_id,
            handoff_id=handoff_id,  # type: ignore[arg-type]
            policy_decision=policy_decision,  # type: ignore[arg-type]
            stop_reason=stop_reason,
            message=message,
            refs=refs,
        )
        return run.model_copy(
            update={
                "events": run.events + (event,),
                "updated_at": _now(),
            }
        )

    def _record_visit(
        self,
        run: OrchestrationRun,
        specialist_id: SpecialistId,
        handoff_id: str,
        observation: OrchestrationObservation,
    ) -> OrchestrationRun:
        visits = list(run.specialist_visits)
        found = False
        for i, visit in enumerate(visits):
            if visit.specialist_id == specialist_id:
                visits[i] = visit.model_copy(
                    update={
                        "visit_count": visit.visit_count + 1,
                        "last_handoff_id": handoff_id,
                        "last_observation_hash": observation.observation_hash,
                        "completed_output_refs": visit.completed_output_refs
                        + ((observation.observation_hash or handoff_id),),
                    }
                )
                found = True
                break
        if not found:
            visits.append(
                SpecialistVisitRecord(
                    specialist_id=specialist_id,
                    visit_count=1,
                    last_handoff_id=handoff_id,  # type: ignore[arg-type]
                    last_observation_hash=observation.observation_hash,
                    completed_output_refs=(observation.observation_hash or handoff_id,),
                )
            )
        return run.model_copy(update={"specialist_visits": tuple(visits)})

    def _obs_completed_for_hash(self, run: OrchestrationRun, hash_: str | None) -> bool:
        if hash_ is None or run.last_brief_id is None:
            return False
        try:
            brief = self._store.load_brief(run.last_brief_id)
            return brief.observation_hash == hash_
        except Exception:  # noqa: BLE001
            return False

    def _bopa_completed(self, run: OrchestrationRun) -> bool:
        if not run.child_agent_run_ids:
            return False
        for hid in reversed(run.handoff_ids):
            try:
                h = self._store.load_handoff(hid)
            except Exception:  # noqa: BLE001
                continue
            if h.target_specialist == "bopa" and h.acceptance in {
                "completed",
                "stopped",
            }:
                return True
        return bool(run.child_agent_run_ids)

    def _map_bopa_stop(self, run: OrchestrationRun) -> OrchestrationStopReason | None:
        if self._bopa is None or not run.child_agent_run_ids:
            return None
        try:
            child = self._bopa._runtime.get(run.child_agent_run_ids[-1])  # noqa: SLF001
            return _map_agent_stop(child.stop_reason)
        except Exception:  # noqa: BLE001
            return None

    def _delegation_path(self, run: OrchestrationRun) -> tuple[SpecialistId, ...]:
        path: list[SpecialistId] = []
        for hid in run.handoff_ids:
            try:
                h = self._store.load_handoff(hid)
            except Exception:  # noqa: BLE001
                continue
            if h.policy_decision == "allow" and h.acceptance in {
                "accepted",
                "executing",
                "completed",
                "stopped",
            }:
                path.append(h.target_specialist)
        return tuple(path)

    def _recent_delegation_keys(self, run: OrchestrationRun) -> tuple[str, ...]:
        keys: list[str] = []
        for hid in run.handoff_ids:
            try:
                h = self._store.load_handoff(hid)
            except Exception:  # noqa: BLE001
                continue
            if h.policy_decision == "allow" and h.observed_state_hash:
                # Match delegation_policy._idempotency_key shape: target|goal|hash
                keys.append(
                    f"{h.target_specialist}|{h.requested_goal_kind}|{h.observed_state_hash}"
                )
        return tuple(keys)


def _map_agent_stop(reason: str | None) -> OrchestrationStopReason | None:
    if reason is None:
        return None
    mapping: dict[str, OrchestrationStopReason] = {
        "completed_for_owner_review": "completed_for_owner_review",
        "owner_approval_required": "owner_approval_required",
        "clarification_required": "clarification_required",
        "truth_validation_blocked": "truth_validation_blocked",
        "material_benefit_required": "material_benefit_required",
        "invalid_state": "invalid_state",
        "unsupported_state": "unsupported_state",
        "policy_blocked": "policy_blocked",
        "provider_unavailable": "provider_unavailable",
        "max_steps_reached": "orchestration_max_steps",
        "unexpected_failure": "unexpected_failure",
    }
    return mapping.get(reason)


def _now() -> datetime:
    return datetime.now(tz=UTC)
