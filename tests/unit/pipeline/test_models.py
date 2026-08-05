"""Unit tests for FR-013 M1 pipeline event models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.pipeline import PipelineEvent, new_pipeline_event_id
from tests.unit.pipeline.helpers import (
    EVENT_A,
    OPP_A,
    make_event,
    make_evidence,
    make_package_ref,
)


def test_event_id_pattern_and_generator() -> None:
    generated = new_pipeline_event_id()
    assert generated.startswith("ple_")
    event = make_event(event_id=generated)
    assert event.event_id == generated


def test_rejects_bad_event_id() -> None:
    with pytest.raises(ValidationError):
        make_event(event_id="evt_01ARZ3NDEKTSV4RRFFQ69G5FAA")


def test_package_opportunity_mismatch_rejected() -> None:
    with pytest.raises(ValidationError):
        make_event(
            opportunity_id=OPP_A,
            evidence=make_evidence(package=make_package_ref(opportunity_id=
                "opp_01ARZ3NDEKTSV4RRFFQ69G5FAB"
            )),
        )


def test_supersede_self_rejected() -> None:
    with pytest.raises(ValidationError):
        make_event(
            kind="correction",
            from_status="rejected",
            to_status="submitted",
            supersedes_event_id=EVENT_A,
            evidence=make_evidence(note="fix mistaken rejection"),
        )


def test_actor_owner_or_agent() -> None:
    assert make_event(actor="owner").actor == "owner"
    assert make_event(actor="agent:fr015_demo").actor == "agent:fr015_demo"
    with pytest.raises(ValidationError):
        make_event(actor="system")


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        PipelineEvent.model_validate(
            {
                **make_event().model_dump(mode="python"),
                "surprise": True,
            }
        )
