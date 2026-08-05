"""Unit tests for FR-013 M1 append-only pipeline event stores."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from career_intelligence.pipeline import (
    InMemoryPipelineEventStore,
    JsonDirectoryPipelineEventStore,
    PipelineAppendOnlyError,
    PipelineEventNotFoundError,
    PipelineValidationError,
)
from tests.unit.pipeline.helpers import (
    ATTEMPT_A,
    EVENT_A,
    EVENT_B,
    FIXED_OCCURRED,
    OPP_A,
    OPP_B,
    make_event,
    make_evidence,
)

LATER = FIXED_OCCURRED + timedelta(hours=1)


@pytest.fixture(params=["memory", "json"])
def store(request: pytest.FixtureRequest, tmp_path: Path):
    if request.param == "memory":
        return InMemoryPipelineEventStore()
    return JsonDirectoryPipelineEventStore(tmp_path / "pipeline_events")


def test_append_load_list_round_trip(store) -> None:
    created = store.append(
        make_event(
            kind="note",
            evidence=make_evidence(note="hello"),
        )
    )
    loaded = store.load(EVENT_A)
    assert loaded == created
    assert store.exists(EVENT_A)
    assert [item.event_id for item in store.list()] == [EVENT_A]


def test_list_filters_and_orders(store) -> None:
    store.append(
        make_event(
            event_id=EVENT_B,
            opportunity_id=OPP_A,
            occurred_at=LATER,
            evidence=make_evidence(note="second"),
        )
    )
    store.append(
        make_event(
            event_id=EVENT_A,
            opportunity_id=OPP_A,
            occurred_at=FIXED_OCCURRED,
            evidence=make_evidence(note="first"),
        )
    )
    store.append(
        make_event(
            event_id="ple_01ARZ3NDEKTSV4RRFFQ69G5FAC",
            opportunity_id=OPP_B,
            evidence=make_evidence(note="other"),
        )
    )
    listed = store.list(opportunity_id=OPP_A)
    assert [item.event_id for item in listed] == [EVENT_A, EVENT_B]


def test_append_rejects_duplicate_id(store) -> None:
    store.append(make_event(evidence=make_evidence(note="a")))
    with pytest.raises(PipelineAppendOnlyError):
        store.append(make_event(evidence=make_evidence(note="b")))


def test_append_rejects_invalid_contract(store) -> None:
    with pytest.raises(PipelineValidationError):
        store.append(
            make_event(
                kind="status_transition",
                from_status="preparing",
                to_status="submitted",
                evidence=make_evidence(),
            )
        )


def test_append_submit_with_attempt_citation(store) -> None:
    event = store.append(
        make_event(
            kind="status_transition",
            from_status="preparing",
            to_status="submitted",
            evidence=make_evidence(
                submission_attempt_id=ATTEMPT_A,
                submitted_at=datetime(2026, 8, 5, 4, 0, 0, tzinfo=UTC),
                note="owner attested submit",
            ),
        )
    )
    assert event.evidence.submission_attempt_id == ATTEMPT_A
    # Citing an attempt never implies a store-side Opportunity write (M1 has none).


def test_load_missing(store) -> None:
    with pytest.raises(PipelineEventNotFoundError):
        store.load(EVENT_A)


def test_no_update_or_delete_api(store) -> None:
    assert not hasattr(store, "save")
    assert not hasattr(store, "delete")
    assert not hasattr(store, "update")
