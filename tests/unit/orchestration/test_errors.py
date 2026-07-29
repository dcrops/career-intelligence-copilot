"""Unit tests for orchestration errors and public exports (FR-008 M0)."""

from __future__ import annotations

import career_intelligence.orchestration as orchestration_api
from career_intelligence.orchestration import (
    ErrorDetail,
    WorkflowAwaitingOwnerError,
    WorkflowCheckpointError,
    WorkflowError,
    WorkflowNodeError,
    WorkflowNotFoundError,
    WorkflowResumeError,
    WorkflowValidationError,
)


def test_public_api_exports_contracts_and_m1_runner() -> None:
    assert hasattr(orchestration_api, "WorkflowState")
    assert hasattr(orchestration_api, "NodeSpec")
    assert hasattr(orchestration_api, "WorkflowEvent")
    assert hasattr(orchestration_api, "CheckpointStore")
    assert hasattr(orchestration_api, "InMemoryCheckpointStore")
    assert hasattr(orchestration_api, "ApplicationWorkflowRunner")
    assert hasattr(orchestration_api, "JsonDirectoryCheckpointStore")
    assert hasattr(orchestration_api, "AcquisitionAdapter")
    assert hasattr(orchestration_api, "PasteAcquisitionAdapter")
    assert hasattr(orchestration_api, "LocalFileAcquisitionAdapter")
    # No generic framework entrypoints / M2 persist API.
    assert not hasattr(orchestration_api, "WorkflowRunner")
    assert not hasattr(orchestration_api, "run_workflow")
    assert not hasattr(orchestration_api, "OpportunityService")


def test_validation_error_carries_details() -> None:
    detail = ErrorDetail(loc=("control", "status"), msg="invalid", type="value_error")
    error = WorkflowValidationError([detail])
    assert isinstance(error, WorkflowError)
    assert error.errors[0].msg == "invalid"


def test_awaiting_owner_error() -> None:
    error = WorkflowAwaitingOwnerError("wfr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert error.run_id.startswith("wfr_")
    assert "awaiting" in str(error).lower()


def test_checkpoint_hierarchy() -> None:
    missing = WorkflowNotFoundError("wfr_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert isinstance(missing, WorkflowCheckpointError)
    assert isinstance(missing, WorkflowError)


def test_resume_and_node_errors() -> None:
    resume = WorkflowResumeError("cannot resume completed run")
    assert isinstance(resume, WorkflowError)

    node = WorkflowNodeError("timeout", node_id="assess", recoverable=True)
    assert node.recoverable is True
    assert node.node_id == "assess"


def test_error_detail_from_pydantic_shape() -> None:
    detail = ErrorDetail.from_pydantic(
        {"loc": ("acquisition", "raw_content"), "msg": "Field required", "type": "missing"}
    )
    assert detail.loc == ("acquisition", "raw_content")
    assert detail.type == "missing"
