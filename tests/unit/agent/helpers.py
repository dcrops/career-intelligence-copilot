"""Test helpers for FR-015 M1 agent contracts."""

from __future__ import annotations

from datetime import datetime, timezone

from career_intelligence.agent import (
    AgentActionProposal,
    AgentGoal,
    AgentRun,
    ArtefactPresence,
    PackageReadiness,
    ReadinessSnapshot,
    TruthReadiness,
    new_agent_run_id,
)

OPP = "opp_01ARZ3NDEKTSV4RRFFQ69G5FAA"


def _now() -> datetime:
    return datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def make_artefacts(
    *,
    job_analysis: bool = True,
    assessment: bool = True,
    portfolio_match: bool = True,
    strategy: bool = True,
) -> ArtefactPresence:
    return ArtefactPresence(
        job_analysis=job_analysis,
        assessment=assessment,
        portfolio_match=portfolio_match,
        strategy=strategy,
    )


def make_package(
    *,
    status: str = "absent",
    cv_present: bool = False,
    cover_letter_present: bool = False,
    manifest_ref: str | None = None,
) -> PackageReadiness:
    return PackageReadiness(
        status=status,  # type: ignore[arg-type]
        cv_present=cv_present,
        cover_letter_present=cover_letter_present,
        manifest_ref=manifest_ref,
    )


def make_truth(
    *,
    status: str = "absent",
    report_ref: str | None = None,
    owner_edited_markdown_since_validation: bool = False,
    blocking_finding_codes: tuple[str, ...] = (),
) -> TruthReadiness:
    return TruthReadiness(
        status=status,  # type: ignore[arg-type]
        report_ref=report_ref,
        owner_edited_markdown_since_validation=owner_edited_markdown_since_validation,
        blocking_finding_codes=blocking_finding_codes,
    )


def make_snapshot(**overrides: object) -> ReadinessSnapshot:
    base: dict[str, object] = {
        "opportunity_id": OPP,
        "decision": "apply",
        "artefacts": make_artefacts(),
        "package": make_package(),
        "truth": make_truth(),
        "owner_approvals_present": True,
        "clarification_required": False,
        "provider_available": True,
        "contradictory_flags": (),
        "prior_agent_run_incomplete": False,
        "snapshot_hash": "hash_a",
        "observed_at": _now(),
    }
    base.update(overrides)
    return ReadinessSnapshot.model_validate(base)


def make_proposal(action: str = "inspect_readiness", **overrides: object) -> AgentActionProposal:
    base: dict[str, object] = {
        "action": action,
        "rationale": "Because readiness requires this next step.",
        "evidence_refs": ("snapshot:decision",),
    }
    base.update(overrides)
    return AgentActionProposal.model_validate(base)


def make_run(**overrides: object) -> AgentRun:
    base: dict[str, object] = {
        "agent_run_id": new_agent_run_id(),
        "goal": AgentGoal(opportunity_id=OPP),
        "status": "running",
        "step_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }
    base.update(overrides)
    return AgentRun.model_validate(base)
