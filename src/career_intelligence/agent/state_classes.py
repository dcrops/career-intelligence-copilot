"""Classify readiness snapshots into BOPA state classes (FR-015 M1).

Pure functions only — no I/O, no service calls, no LLM.
"""

from __future__ import annotations

from .models import ReadinessSnapshot
from .types import (
    STATE_CLASS_PRIORITY,
    AgentAction,
    AgentStopReason,
    ReadinessStateClass,
)

# Actions never granted by M1 ToolPolicy for upstream FR-002–005 repair.
_DIAGNOSE_AND_STOP: frozenset[AgentAction] = frozenset(
    {"inspect_readiness", "request_owner_review", "stop"}
)

_PREP_WHEN_APPROVED: frozenset[AgentAction] = frozenset(
    {
        "inspect_readiness",
        "run_preparation",
        "request_owner_review",
        "stop",
    }
)

_VERIFY_AND_PREP: frozenset[AgentAction] = frozenset(
    {
        "inspect_readiness",
        "verify_package",
        "run_preparation",
        "request_owner_review",
        "stop",
    }
)

_REVALIDATE_TRUTH: frozenset[AgentAction] = frozenset(
    {
        "inspect_readiness",
        "validate_truth_package",
        "request_owner_review",
        "stop",
    }
)

_TRUTH_BLOCKED: frozenset[AgentAction] = frozenset(
    {
        "inspect_readiness",
        "validate_truth_package",
        "request_owner_review",
        "stop",
    }
)

_READY: frozenset[AgentAction] = frozenset(
    {
        "inspect_readiness",
        "verify_package",
        "request_owner_review",
        "stop",
    }
)

_PROVIDER_DOWN: frozenset[AgentAction] = frozenset({"inspect_readiness", "stop"})


def applicable_state_classes(snapshot: ReadinessSnapshot) -> tuple[ReadinessStateClass, ...]:
    """Return all state classes that currently apply, priority order preserved."""
    found: list[ReadinessStateClass] = []

    if not snapshot.provider_available:
        found.append("provider_unavailable")

    if snapshot.contradictory_flags:
        found.append("unsupported_or_contradictory")
    elif _is_contradictory_combination(snapshot):
        found.append("unsupported_or_contradictory")

    if snapshot.clarification_required:
        found.append("clarification_required")

    if snapshot.decision == "apply" and not snapshot.owner_approvals_present:
        # Approvals only required when preparation would otherwise be legal.
        if snapshot.artefacts.all_present and snapshot.package.status in {
            "absent",
            "incomplete",
            "stale",
            "integrity_failed",
        }:
            found.append("owner_approval_required")

    if not snapshot.artefacts.job_analysis:
        found.append("missing_analysis")
    if not snapshot.artefacts.assessment:
        found.append("missing_assessment")
    if not snapshot.artefacts.portfolio_match:
        found.append("missing_portfolio_match")
    if not snapshot.artefacts.strategy:
        found.append("missing_strategy")

    if snapshot.decision != "apply":
        # BOPA prepare_for_owner_review only coordinates the apply path.
        if "unsupported_or_contradictory" not in found:
            if snapshot.decision in {"skip", "defer", None}:
                found.append("unsupported_or_contradictory")
    else:
        if snapshot.package.status == "integrity_failed":
            found.append("package_integrity_failure")
        if snapshot.package.status == "incomplete" and not snapshot.package.cv_present:
            found.append("missing_cv")
        if (
            snapshot.package.status == "incomplete"
            and not snapshot.package.cover_letter_present
        ):
            found.append("missing_cover_letter")
        if snapshot.package.status == "absent":
            found.append("missing_package")
        if snapshot.package.status == "stale":
            found.append("stale_package")

        if snapshot.truth.owner_edited_markdown_since_validation:
            found.append("owner_markdown_revalidation_required")
        if snapshot.truth.status == "stale":
            found.append("stale_truth_report")
        if snapshot.truth.status == "absent" and snapshot.package.status == "present":
            found.append("missing_truth_report")
        if snapshot.truth.status in {"fail", "review_required"}:
            found.append("truth_blocked")

    if snapshot.prior_agent_run_incomplete:
        found.append("partial_agent_run")

    if _is_ready_for_owner_review(snapshot):
        found.append("ready_for_owner_review")

    # Stable priority ordering.
    order = {name: idx for idx, name in enumerate(STATE_CLASS_PRIORITY)}
    found_sorted = sorted(set(found), key=lambda c: order[c])
    return tuple(found_sorted)


def primary_state_class(snapshot: ReadinessSnapshot) -> ReadinessStateClass:
    """Return the highest-priority applicable state class."""
    classes = applicable_state_classes(snapshot)
    if not classes:
        # Defensive: treat empty classification as unsupported.
        return "unsupported_or_contradictory"
    return classes[0]


def approved_actions_for(
    snapshot: ReadinessSnapshot,
    *,
    state_class: ReadinessStateClass | None = None,
) -> frozenset[AgentAction]:
    """Return the allow-listed actions legal for the (primary) state class."""
    klass = state_class or primary_state_class(snapshot)
    return _ACTIONS_BY_CLASS[klass]


def expected_owner_stop_reason(
    snapshot: ReadinessSnapshot,
    *,
    state_class: ReadinessStateClass | None = None,
) -> AgentStopReason | None:
    """Stop reason the agent should record when it must not continue coordinating."""
    klass = state_class or primary_state_class(snapshot)
    return _STOP_BY_CLASS.get(klass)


def _is_ready_for_owner_review(snapshot: ReadinessSnapshot) -> bool:
    return (
        snapshot.decision == "apply"
        and snapshot.artefacts.all_present
        and snapshot.package.status == "present"
        and snapshot.package.cv_present
        and snapshot.package.cover_letter_present
        and snapshot.truth.status == "pass"
        and not snapshot.truth.owner_edited_markdown_since_validation
        and not snapshot.clarification_required
        and not snapshot.contradictory_flags
        and snapshot.provider_available
    )


def _is_contradictory_combination(snapshot: ReadinessSnapshot) -> bool:
    if snapshot.decision in {"skip", "defer", None}:
        if snapshot.package.status not in {"absent"}:
            return True
        if snapshot.truth.status not in {"absent"}:
            return True
    if snapshot.decision == "apply" and not snapshot.artefacts.all_present:
        if snapshot.package.status not in {"absent"}:
            return True
    if snapshot.package.status == "present" and snapshot.truth.status == "pass":
        if snapshot.truth.owner_edited_markdown_since_validation:
            return True
    return False


_ACTIONS_BY_CLASS: dict[ReadinessStateClass, frozenset[AgentAction]] = {
    "provider_unavailable": _PROVIDER_DOWN,
    "unsupported_or_contradictory": _DIAGNOSE_AND_STOP,
    "clarification_required": _DIAGNOSE_AND_STOP,
    "owner_approval_required": _DIAGNOSE_AND_STOP,
    "missing_analysis": _DIAGNOSE_AND_STOP,
    "missing_assessment": _DIAGNOSE_AND_STOP,
    "missing_portfolio_match": _DIAGNOSE_AND_STOP,
    "missing_strategy": _DIAGNOSE_AND_STOP,
    "package_integrity_failure": _VERIFY_AND_PREP,
    "missing_cv": _PREP_WHEN_APPROVED,
    "missing_cover_letter": _PREP_WHEN_APPROVED,
    "missing_package": _PREP_WHEN_APPROVED,
    "stale_package": _PREP_WHEN_APPROVED,
    "owner_markdown_revalidation_required": _REVALIDATE_TRUTH,
    "stale_truth_report": _REVALIDATE_TRUTH,
    "missing_truth_report": _REVALIDATE_TRUTH,
    "truth_blocked": _TRUTH_BLOCKED,
    "partial_agent_run": frozenset(  # resume: inspect first; further actions via refreshed snapshot
        {"inspect_readiness", "request_owner_review", "stop"}
    ),
    "ready_for_owner_review": _READY,
}

_STOP_BY_CLASS: dict[ReadinessStateClass, AgentStopReason | None] = {
    "provider_unavailable": "provider_unavailable",
    "unsupported_or_contradictory": "unsupported_state",
    "clarification_required": "clarification_required",
    "owner_approval_required": "owner_approval_required",
    "missing_analysis": "invalid_state",
    "missing_assessment": "invalid_state",
    "missing_portfolio_match": "invalid_state",
    "missing_strategy": "invalid_state",
    "package_integrity_failure": None,  # may recover via prep
    "missing_cv": None,
    "missing_cover_letter": None,
    "missing_package": None,
    "stale_package": None,
    "owner_markdown_revalidation_required": None,  # may revalidate
    "stale_truth_report": None,
    "missing_truth_report": None,
    "truth_blocked": "truth_validation_blocked",
    "partial_agent_run": None,
    "ready_for_owner_review": "completed_for_owner_review",
}
