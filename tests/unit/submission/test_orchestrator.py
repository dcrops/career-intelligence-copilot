"""Unit tests for FR-012 M1 SubmissionOrchestrator gates and behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.submission import (
    FakeSubmissionAdapter,
    InMemorySubmissionAttemptStore,
    ManualAssistedAdapter,
    SubmissionChannelError,
    SubmissionDuplicateError,
    SubmissionGateError,
    SubmissionOrchestrator,
)
from tests.unit.application_package.helpers import (
    package_service,
    seed_applied_opportunity,
)
from tests.unit.submission.helpers_m1 import (
    DESTINATION,
    make_orchestrator,
    prepared_workspace,
)


def test_submit_fake_success(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    attempt = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert attempt.status == "submitted"
    assert attempt.evidence.owner_approved_submit is True
    assert attempt.evidence.result_code == "fake_submitted"
    assert fake.call_count == 1
    assert orchestrator.get_attempt(attempt.attempt_id).status == "submitted"


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        ("failed", "failed"),
        ("manual_action_required", "manual_action_required"),
        ("outcome_unknown", "outcome_unknown"),
    ],
)
def test_fake_configured_outcomes(tmp_path: Path, outcome: str, status: str) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    fake = FakeSubmissionAdapter(outcome=outcome)  # type: ignore[arg-type]
    orchestrator, _, _ = make_orchestrator(
        tmp_path, opportunities, packages, fake=fake
    )
    attempt = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert attempt.status == status
    if status in {"failed", "outcome_unknown"}:
        assert attempt.evidence.failure_reason is not None
    if status == "manual_action_required":
        assert attempt.completed_at is None


def test_missing_owner_approval_refuses_before_adapter(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    with pytest.raises(SubmissionGateError, match="owner_approved_submit"):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=False,
            destination=DESTINATION,
        )
    assert fake.call_count == 0
    assert orchestrator.list_attempts(opportunity_id=opportunity_id) == []


def test_missing_opportunity(tmp_path: Path) -> None:
    opportunities, packages, _, _ = prepared_workspace(tmp_path)
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    with pytest.raises(SubmissionGateError):
        orchestrator.submit(
            "opp_01K00000000000000000000000",
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
    assert fake.call_count == 0


def test_decision_not_apply(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(
        tmp_path, decision="skip"
    )
    packages = package_service(tmp_path, opportunities, profile)
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    with pytest.raises(SubmissionGateError, match="apply"):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
    assert fake.call_count == 0


def test_missing_package(tmp_path: Path) -> None:
    opportunities, opportunity_id, profile = seed_applied_opportunity(tmp_path)
    packages = package_service(tmp_path, opportunities, profile)
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    with pytest.raises(SubmissionGateError, match="package"):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
    assert fake.call_count == 0


def test_package_integrity_failure(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    manifest = packages.get(opportunity_id, verify=True)
    Path(manifest.cv.markdown_path).unlink()
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    with pytest.raises(SubmissionGateError, match="missing draft"):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
    assert fake.call_count == 0


def test_unknown_channel(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    store = InMemorySubmissionAttemptStore()
    orchestrator = SubmissionOrchestrator(
        opportunities,
        packages,
        store=store,
        adapters={},
    )
    with pytest.raises(SubmissionChannelError):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )


def test_missing_destination(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    with pytest.raises(SubmissionGateError, match="Destination"):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=None,
        )
    assert fake.call_count == 0


def test_manual_assisted_never_claims_submitted(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, _, manual = make_orchestrator(tmp_path, opportunities, packages)
    attempt = orchestrator.submit(
        opportunity_id,
        channel="manual_assisted",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert attempt.status == "manual_action_required"
    assert "owner must complete externally" in attempt.evidence.message.lower()
    assert manual.call_count == 1
    assert attempt.evidence.result_code == "manual_assisted_checklist"


def test_duplicate_submitted_blocks(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    first = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert first.status == "submitted"
    with pytest.raises(SubmissionDuplicateError, match="successful"):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
    assert fake.call_count == 1


def test_force_new_attempt_requires_reason(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, fake, _ = make_orchestrator(tmp_path, opportunities, packages)
    orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    with pytest.raises(SubmissionGateError, match="force_reason"):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
            force_new_attempt=True,
            force_reason=None,
        )
    second = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
        force_new_attempt=True,
        force_reason="employer asked for updated CV",
    )
    assert second.status == "submitted"
    assert fake.call_count == 2
    assert "force_new_attempt_reason=" in (second.evidence.message or "")


def test_in_progress_reclaim_does_not_reinvoke_adapter(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    fake = FakeSubmissionAdapter(outcome="manual_action_required")
    orchestrator, _, _ = make_orchestrator(
        tmp_path, opportunities, packages, fake=fake
    )
    first = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert first.status == "manual_action_required"
    second = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert second.attempt_id == first.attempt_id
    assert fake.call_count == 1


def test_outcome_unknown_requires_acknowledgement(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    fake = FakeSubmissionAdapter(outcome="outcome_unknown")
    orchestrator, _, _ = make_orchestrator(
        tmp_path, opportunities, packages, fake=fake
    )
    first = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert first.status == "outcome_unknown"
    with pytest.raises(SubmissionDuplicateError, match="outcome_unknown"):
        orchestrator.submit(
            opportunity_id,
            channel="fake",
            owner_approved_submit=True,
            destination=DESTINATION,
        )
    fake.set_outcome("submitted")
    second = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
        acknowledge_prior_outcome_unknown=True,
    )
    assert second.status == "submitted"
    assert second.attempt_id != first.attempt_id
    assert fake.call_count == 2


def test_prior_failed_allows_new_attempt(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    fake = FakeSubmissionAdapter(outcome="failed")
    orchestrator, _, _ = make_orchestrator(
        tmp_path, opportunities, packages, fake=fake
    )
    first = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert first.status == "failed"
    fake.set_outcome("submitted")
    second = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert second.status == "submitted"
    assert fake.call_count == 2


def test_record_manual_completion(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, fake, manual = make_orchestrator(tmp_path, opportunities, packages)
    attempt = orchestrator.record_manual_completion(
        opportunity_id,
        owner_approved_submit=True,
        attestation="Submitted via employer careers portal on 2026-07-31",
        destination=DESTINATION,
        confirmation_reference="CONF-99",
    )
    assert attempt.status == "manual_completed"
    assert attempt.evidence.result_code == "manual_owner_completed"
    assert "attestation=" in attempt.evidence.message
    assert "confirmation_reference=CONF-99" in attempt.evidence.message
    assert fake.call_count == 0
    assert manual.call_count == 0


def test_record_manual_completion_requires_approval(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, _, _ = make_orchestrator(tmp_path, opportunities, packages)
    with pytest.raises(SubmissionGateError, match="owner_approved_submit"):
        orchestrator.record_manual_completion(
            opportunity_id,
            owner_approved_submit=False,
            attestation="done",
            destination=DESTINATION,
        )


def test_record_manual_completion_closes_open_assisted(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, _, manual = make_orchestrator(tmp_path, opportunities, packages)
    open_attempt = orchestrator.submit(
        opportunity_id,
        channel="manual_assisted",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert open_attempt.status == "manual_action_required"
    completed = orchestrator.record_manual_completion(
        opportunity_id,
        owner_approved_submit=True,
        attestation="Form submitted manually",
        destination=DESTINATION,
    )
    assert completed.attempt_id == open_attempt.attempt_id
    assert completed.status == "manual_completed"
    assert manual.call_count == 1


def test_manual_completed_blocks_duplicate(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    orchestrator, _, _ = make_orchestrator(tmp_path, opportunities, packages)
    orchestrator.record_manual_completion(
        opportunity_id,
        owner_approved_submit=True,
        attestation="done once",
        destination=DESTINATION,
    )
    with pytest.raises(SubmissionDuplicateError):
        orchestrator.record_manual_completion(
            opportunity_id,
            owner_approved_submit=True,
            attestation="done again",
            destination=DESTINATION,
        )


def test_adapters_do_not_persist(tmp_path: Path) -> None:
    opportunities, packages, _, opportunity_id = prepared_workspace(tmp_path)
    store = InMemorySubmissionAttemptStore()
    fake = FakeSubmissionAdapter()
    orchestrator = SubmissionOrchestrator(
        opportunities,
        packages,
        store=store,
        adapters={"fake": fake, "manual_assisted": ManualAssistedAdapter()},
    )
    # Adapter alone has no store reference.
    assert not hasattr(fake, "store")
    attempt = orchestrator.submit(
        opportunity_id,
        channel="fake",
        owner_approved_submit=True,
        destination=DESTINATION,
    )
    assert store.load(attempt.attempt_id).status == "submitted"
