"""Workflow node contract (FR-008 M0) — identification and failure reporting only.

No service wrappers or business logic in this module. M1+ supplies implementations.
"""

from __future__ import annotations

from typing import Annotated, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from .models import WorkflowState
from .types import NodeKind

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Reserved identifiers for the application workflow graph (slice + future).
KNOWN_NODE_IDS: frozenset[str] = frozenset(
    {
        "acquire",
        "validate_normalise",
        "analyse",
        "assess",
        "match",
        "strategy",
        "owner_review",
        "persist",
        "record_decision",
        "deduplicate",
        "rank",
        "prepare_package",
        "submit",
        "track",
    }
)


class NodeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NodeSpec(NodeModel):
    """Deterministic identity and classification for one workflow node."""

    node_id: NonEmptyString
    display_name: NonEmptyString
    kind: NodeKind
    description: NonEmptyString | None = None

    @model_validator(mode="after")
    def node_id_is_known_or_namespaced(self) -> NodeSpec:
        """Allow known graph ids or extension ids prefixed with ``x_``."""
        value = self.node_id
        if value in KNOWN_NODE_IDS or value.startswith("x_"):
            return self
        raise ValueError(
            f"Unknown node_id '{value}'. Use a known graph id or an 'x_' extension id."
        )


class NodeFailure(NodeModel):
    """Explicit failure payload a node may report (without raising)."""

    message: NonEmptyString
    recoverable: bool = False
    detail: NonEmptyString | None = None


class NodeSuccess(NodeModel):
    """Marker that a node completed and produced an updated workflow state."""

    state: WorkflowState


class NodeOutcome(NodeModel):
    """Typed node result: exactly one of success or failure must be set."""

    success: NodeSuccess | None = None
    failure: NodeFailure | None = None

    @model_validator(mode="after")
    def exactly_one_branch(self) -> NodeOutcome:
        has_success = self.success is not None
        has_failure = self.failure is not None
        if has_success == has_failure:
            raise ValueError("NodeOutcome requires exactly one of success or failure")
        return self


@runtime_checkable
class WorkflowNode(Protocol):
    """Public node contract — implementations arrive in M1+.

    ``execute`` receives the current workflow state and returns a typed outcome.
    Nodes must not import storage adapters or provider SDKs.
    """

    @property
    def spec(self) -> NodeSpec:
        """Stable node identity and classification."""

    def execute(self, state: WorkflowState) -> NodeOutcome:
        """Run the node against ``state`` without mutating the caller's object.

        Success outcomes carry a new ``WorkflowState``. Failures use
        ``NodeFailure`` (or implementations may raise ``WorkflowNodeError``).
        """
