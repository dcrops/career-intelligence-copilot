"""Shared literal types for FR-008 orchestration contracts."""

from __future__ import annotations

from typing import Literal, get_args

WorkflowStatus = Literal[
    "running",
    "awaiting_owner",
    "completed",
    "failed",
    "cancelled",
]

NodeKind = Literal["deterministic", "llm_backed", "agentic"]

OwnerDecisionKind = Literal["apply", "skip", "defer"]

AcquisitionSourceKind = Literal[
    "paste",
    "url",
    "api",
    "email",
    "saved_search",
    "export",
    "playwright",
    "other",
]

ApprovalKind = Literal["owner_review"]

FailureClassification = Literal["recoverable", "unrecoverable"]

RetryNextAction = Literal["retry_node", "fail_closed"]

WORKFLOW_STATUSES: tuple[WorkflowStatus, ...] = get_args(WorkflowStatus)
NODE_KINDS: tuple[NodeKind, ...] = get_args(NodeKind)
OWNER_DECISION_KINDS: tuple[OwnerDecisionKind, ...] = get_args(OwnerDecisionKind)
ACQUISITION_SOURCE_KINDS: tuple[AcquisitionSourceKind, ...] = get_args(AcquisitionSourceKind)
FAILURE_CLASSIFICATIONS: tuple[FailureClassification, ...] = get_args(FailureClassification)
TERMINAL_WORKFLOW_STATUSES: frozenset[WorkflowStatus] = frozenset(
    {"completed", "failed", "cancelled"}
)
