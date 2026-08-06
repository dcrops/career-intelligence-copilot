"""Shared literal types for FR-016 multi-agent orchestration contracts (M1).

No runtime, CLI, or framework integration. BOPA allow-list remains owned by
``career_intelligence.agent`` and is not redefined here.
"""

from __future__ import annotations

from typing import Literal, get_args

# Live specialists in FR-016. Acquisition is a future placeholder only.
SpecialistId = Literal["obs", "bopa"]
SPECIALIST_IDS: tuple[SpecialistId, ...] = get_args(SpecialistId)

# Placeholder only — must never appear in DelegationPolicy allow matrix for M1–M2.
FUTURE_SPECIALIST_IDS: frozenset[str] = frozenset({"acquisition"})

OrchestrationGoalKind = Literal[
    "brief_opportunity_readiness",
    "coordinate_opportunity_readiness",
]
ORCHESTRATION_GOAL_KINDS: tuple[OrchestrationGoalKind, ...] = get_args(OrchestrationGoalKind)

OrchestrationRunStatus = Literal[
    "running",
    "awaiting_owner",
    "completed",
    "failed",
    "cancelled",
]
ORCHESTRATION_RUN_STATUSES: tuple[OrchestrationRunStatus, ...] = get_args(OrchestrationRunStatus)

OrchestrationStopReason = Literal[
    "briefing_complete",
    "completed_for_owner_review",
    "owner_approval_required",
    "clarification_required",
    "truth_validation_blocked",
    "material_benefit_required",
    "invalid_state",
    "unsupported_state",
    "delegation_blocked",
    "handoff_stale",
    "handoff_rejected",
    "circular_delegation",
    "repeated_delegation",
    "specialist_unavailable",
    "provider_unavailable",
    "orchestration_max_steps",
    "specialist_visit_limit",
    "no_progress",
    "policy_blocked",
    "unexpected_failure",
]
ORCHESTRATION_STOP_REASONS: tuple[OrchestrationStopReason, ...] = get_args(
    OrchestrationStopReason
)

# OBS closed allow-list — strictly read-only / briefing / stop. No BOPA mutating tools.
ObsAction = Literal[
    "inspect_readiness",
    "inspect_pipeline_context",
    "inspect_truth_blockers",
    "inspect_agent_history",
    "compose_brief",
    "recommend_delegation",
    "request_owner_review",
    "stop",
]
OBS_ACTIONS: tuple[ObsAction, ...] = get_args(ObsAction)

# Explicitly forbidden for OBS (and never granted by handoff).
OBS_FORBIDDEN_ACTION_NAMES: frozenset[str] = frozenset(
    {
        "run_preparation",
        "verify_package",
        "validate_truth_package",
        "submit",
        "record_manual_completion",
        "advance_pipeline",
        "pipeline_submit",
        "discover_jobs",
        "scrape_job_board",
        "contact_recruiter",
        "waive_truth",
        "rewrite_markdown",
        "mutate_opportunity_decision",
        "run_analyse",
        "run_assess",
        "run_match",
        "run_strategy",
        "filesystem_read",
        "filesystem_write",
        "shell_exec",
        "arbitrary_python",
    }
)

# Lifecycle: created(pending) → policy_blocked | accepted → executing → completed | stopped
# Also: rejected, stale, cancelled.
HandoffAcceptance = Literal[
    "pending",
    "policy_blocked",
    "accepted",
    "rejected",
    "executing",
    "completed",
    "stopped",
    "stale",
    "cancelled",
]
HANDOFF_ACCEPTANCES: tuple[HandoffAcceptance, ...] = get_args(HandoffAcceptance)

DelegationDecisionKind = Literal["allow", "deny"]
DELEGATION_DECISION_KINDS: tuple[DelegationDecisionKind, ...] = get_args(
    DelegationDecisionKind
)

OrchestrationAuditEventKind = Literal[
    "orchestration_started",
    "state_observed",
    "specialist_considered",
    "specialist_selected",
    "delegation_allowed",
    "delegation_blocked",
    "handoff_created",
    "handoff_accepted",
    "handoff_rejected",
    "specialist_started",
    "specialist_completed",
    "specialist_stopped",
    "owner_gate_reached",
    "retry_recorded",
    "timeout_recorded",
    "budget_snapshot",
    "orchestration_stop_recorded",
    "error_recorded",
]
ORCHESTRATION_AUDIT_EVENT_KINDS: tuple[OrchestrationAuditEventKind, ...] = get_args(
    OrchestrationAuditEventKind
)

# When OBS adds value that BOPA's prepare_for_owner_review goal should not absorb.
BriefingNeedClass = Literal[
    "pipeline_advises_against_preparation",
    "cross_surface_ambiguity",
    "truth_blockers_need_synthesis",
    "prior_agent_history_material",
    "owner_requested_brief_only",
    "batch_triage",
    "post_specialist_synthesis",
    "brief_before_mutate",
    "no_briefing_delta",
]
BRIEFING_NEED_CLASSES: tuple[BriefingNeedClass, ...] = get_args(BriefingNeedClass)

RecommendedNextStep = Literal[
    "invoke_obs",
    "invoke_bopa",
    "owner_review",
    "owner_remediate_truth",
    "owner_remediate_package",
    "owner_run_fr008",
    "stop",
]
RECOMMENDED_NEXT_STEPS: tuple[RecommendedNextStep, ...] = get_args(RecommendedNextStep)

DEFAULT_MAX_ORCHESTRATION_STEPS: int = 12
DEFAULT_MAX_VISITS_PER_SPECIALIST: int = 3
DEFAULT_MAX_OBS_STEPS: int = 6
