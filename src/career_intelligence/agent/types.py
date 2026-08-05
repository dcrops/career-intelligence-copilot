"""Shared literal types for FR-015 Bounded Opportunity Preparation Agent (BOPA)."""

from __future__ import annotations

from typing import Literal, get_args

# M1 allow-list only. Submit / pipeline / discovery / analyse are intentionally absent.
AgentAction = Literal[
    "inspect_readiness",
    "run_preparation",
    "verify_package",
    "validate_truth_package",
    "request_owner_review",
    "stop",
]
AGENT_ACTIONS: tuple[AgentAction, ...] = get_args(AgentAction)

AgentGoalKind = Literal["prepare_for_owner_review"]
AGENT_GOAL_KINDS: tuple[AgentGoalKind, ...] = get_args(AgentGoalKind)

AgentRunStatus = Literal[
    "running",
    "awaiting_owner",
    "completed",
    "failed",
    "cancelled",
]
AGENT_RUN_STATUSES: tuple[AgentRunStatus, ...] = get_args(AgentRunStatus)

AgentStopReason = Literal[
    "completed_for_owner_review",
    "owner_approval_required",
    "clarification_required",
    "truth_validation_blocked",
    "material_benefit_required",
    "invalid_state",
    "policy_blocked",
    "retry_exhausted",
    "provider_unavailable",
    "max_steps_reached",
    "unexpected_failure",
    "unsupported_state",
]
AGENT_STOP_REASONS: tuple[AgentStopReason, ...] = get_args(AgentStopReason)

# Concrete readiness classes where BOPA adds value beyond FR-008 (ADR-007).
ReadinessStateClass = Literal[
    "missing_analysis",
    "missing_assessment",
    "missing_portfolio_match",
    "missing_strategy",
    "missing_package",
    "stale_package",
    "missing_cv",
    "missing_cover_letter",
    "package_integrity_failure",
    "missing_truth_report",
    "stale_truth_report",
    "truth_blocked",
    "owner_markdown_revalidation_required",
    "clarification_required",
    "partial_agent_run",
    "provider_unavailable",
    "unsupported_or_contradictory",
    "owner_approval_required",
    "ready_for_owner_review",
]
READINESS_STATE_CLASSES: tuple[ReadinessStateClass, ...] = get_args(ReadinessStateClass)

# Highest-priority first when classifying a snapshot.
STATE_CLASS_PRIORITY: tuple[ReadinessStateClass, ...] = (
    "provider_unavailable",
    "unsupported_or_contradictory",
    "clarification_required",
    "owner_approval_required",
    "missing_analysis",
    "missing_assessment",
    "missing_portfolio_match",
    "missing_strategy",
    "package_integrity_failure",
    "missing_cv",
    "missing_cover_letter",
    "missing_package",
    "stale_package",
    "owner_markdown_revalidation_required",
    "stale_truth_report",
    "missing_truth_report",
    "truth_blocked",
    "partial_agent_run",
    "ready_for_owner_review",
)

PackageStatus = Literal[
    "absent",
    "present",
    "incomplete",
    "stale",
    "integrity_failed",
]
PACKAGE_STATUSES: tuple[PackageStatus, ...] = get_args(PackageStatus)

TruthStatus = Literal[
    "absent",
    "pass",
    "fail",
    "stale",
    "review_required",
    "warning",
]
TRUTH_STATUSES: tuple[TruthStatus, ...] = get_args(TruthStatus)

OwnerDecisionKind = Literal["apply", "skip", "defer"]
OWNER_DECISION_KINDS: tuple[OwnerDecisionKind, ...] = get_args(OwnerDecisionKind)

PolicyDecisionKind = Literal["allow", "deny"]
POLICY_DECISION_KINDS: tuple[PolicyDecisionKind, ...] = get_args(PolicyDecisionKind)

AuditEventKind = Literal[
    "run_started",
    "snapshot_observed",
    "action_proposed",
    "policy_evaluated",
    "action_blocked",
    "action_executed",
    "service_result",
    "stop_recorded",
    "error_recorded",
    "resume_observed",
]
AUDIT_EVENT_KINDS: tuple[AuditEventKind, ...] = get_args(AuditEventKind)

# Always blocked — not in AgentAction allow-list; listed for policy/docs clarity.
FORBIDDEN_ACTION_NAMES: frozenset[str] = frozenset(
    {
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

DEFAULT_MAX_STEPS: int = 8
