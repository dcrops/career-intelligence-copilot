"""Builders for orchestration unit tests (FR-008 M0)."""

from __future__ import annotations

from datetime import UTC, datetime

from career_intelligence.orchestration import (
    AcquisitionEnvelope,
    ApprovalState,
    WorkflowControl,
    WorkflowEvent,
    WorkflowState,
    new_workflow_run_id,
)


def fixed_run_id() -> str:
    return "wfr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def now() -> datetime:
    return datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)


def make_control(**overrides: object) -> WorkflowControl:
    timestamp = now()
    payload: dict[str, object] = {
        "run_id": fixed_run_id(),
        "status": "running",
        "current_node": "analyse",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    payload.update(overrides)
    return WorkflowControl.model_validate(payload)


def make_acquisition(**overrides: object) -> AcquisitionEnvelope:
    payload: dict[str, object] = {
        "source_kind": "paste",
        "acquired_at": now(),
        "raw_content": "Senior AI Engineer\nBuild LLM systems.",
        "normalised_content": "Senior AI Engineer\nBuild LLM systems.",
        "title": "Senior AI Engineer",
        "company": "Example Co",
    }
    payload.update(overrides)
    return AcquisitionEnvelope.model_validate(payload)


def make_state(**overrides: object) -> WorkflowState:
    payload: dict[str, object] = {
        "control": make_control(),
        "acquisition": make_acquisition(),
    }
    payload.update(overrides)
    if "control" in overrides and isinstance(overrides["control"], dict):
        payload["control"] = make_control(**overrides["control"])
    if "acquisition" in overrides and isinstance(overrides["acquisition"], dict):
        payload["acquisition"] = make_acquisition(**overrides["acquisition"])
    if "approval" in overrides and isinstance(overrides["approval"], dict):
        payload["approval"] = ApprovalState.model_validate(overrides["approval"])
    return WorkflowState.model_validate(payload)


def make_event(event_type: str, **overrides: object) -> WorkflowEvent:
    payload: dict[str, object] = {
        "event_type": event_type,
        "timestamp": now(),
        "run_id": fixed_run_id(),
    }
    if event_type in {
        "node_started",
        "node_succeeded",
        "node_failed",
        "retry_scheduled",
        "retry_exhausted",
    }:
        payload.setdefault("node_id", "analyse")
        payload.setdefault("node_kind", "llm_backed")
    if event_type in {"node_succeeded", "node_failed"}:
        payload.setdefault("duration_ms", 12)
    if event_type == "node_failed":
        payload.setdefault("recoverable", True)
        payload.setdefault("message", "transient failure")
    if event_type in {"retry_scheduled", "retry_exhausted"}:
        payload.setdefault("attempt", 2)
        payload.setdefault("message", "retry metadata")
    if event_type == "retry_scheduled":
        payload.setdefault("recoverable", True)
    if event_type == "checkpoint_written":
        payload.setdefault("checkpoint_reason", "approval")
    if event_type == "approval_requested":
        payload.setdefault("approval_kind", "owner_review")
    if event_type == "approval_received":
        payload.setdefault("decision", "apply")
    payload.update(overrides)
    return WorkflowEvent.model_validate(payload)


def unique_run_id() -> str:
    return new_workflow_run_id()
