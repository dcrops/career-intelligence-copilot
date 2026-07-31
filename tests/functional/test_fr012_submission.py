"""Functional acceptance for FR-012 M1 deterministic submission assistance."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.submission import (
    FakeSubmissionAdapter,
    JsonDirectorySubmissionAttemptStore,
    ManualAssistedAdapter,
    SubmissionDuplicateError,
    SubmissionGateError,
    SubmissionOrchestrator,
)
from tests.unit.submission.helpers_m1 import DESTINATION, prepared_workspace


def test_offline_submission_journey(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    store = JsonDirectorySubmissionAttemptStore(tmp_path / "submission_attempts")
    fake = FakeSubmissionAdapter()
    manual = ManualAssistedAdapter()
    orchestrator = SubmissionOrchestrator(
        opportunities,
        packages,
        store=store,
        adapters={"fake": fake, "manual_assisted": manual},
    )

    try:
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=False,
            destination=DESTINATION,
        )
        raise AssertionError("expected approval gate")
    except SubmissionGateError:
        pass
    assert fake.call_count == 0

    submitted = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert submitted.status == "submitted"

    try:
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
        raise AssertionError("expected duplicate guard")
    except SubmissionDuplicateError:
        pass

    # Separate opportunity path for manual-assisted + completion would need another
    # seed; reuse force on fake channel is already covered in unit tests.
    # Use a second prepared opportunity for assisted-manual.
    opportunities2, packages2, _, opportunity_id2 = prepared_workspace(
        tmp_path / "workspace2"
    )
    store2 = JsonDirectorySubmissionAttemptStore(tmp_path / "attempts2")
    fake2 = FakeSubmissionAdapter(outcome="outcome_unknown")
    orch2 = SubmissionOrchestrator(
        opportunities2,
        packages2,
        store=store2,
        adapters={
            "fake": fake2,
            "manual_assisted": ManualAssistedAdapter(),
        },
    )
    unknown = orch2.submit(
        opportunity_id2,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert unknown.status == "outcome_unknown"
    reloaded = JsonDirectorySubmissionAttemptStore(tmp_path / "attempts2").load(
        unknown.attempt_id
    )
    assert reloaded.status == "outcome_unknown"

    assisted = orch2.submit(
        opportunity_id2,
        channel="manual_assisted",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert assisted.status == "manual_action_required"
    completed = orch2.record_manual_completion(
        opportunity_id2,
        owner_approved_submit=True,
        attestation="Submitted on careers site",
        destination=DESTINATION,
    )
    assert completed.status == "manual_completed"
    assert completed.attempt_id == assisted.attempt_id
