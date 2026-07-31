"""Submission Orchestrator (FR-012 M1).

Deterministic coordinator: gates → adapter → append-only attempt store.
Does not own package rules, channel mechanics, PipelineStatus, or CLI behaviour.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.application_package import (
    ApplicationPackageError,
    ApplicationPackageIntegrityError,
    ApplicationPackageNotFoundError,
    ApplicationPackageService,
)
from career_intelligence.opportunities import (
    OpportunityNotFoundError,
    OpportunityService,
    OpportunityStorageError,
)

from .adapters import SubmissionAdapter, SubmissionAdapterRequest, SubmissionAdapterResult
from .errors import (
    SubmissionChannelError,
    SubmissionDuplicateError,
    SubmissionGateError,
)
from .fake_adapter import FakeSubmissionAdapter
from .ids import new_submission_attempt_id
from .json_store import JsonDirectorySubmissionAttemptStore
from .manual_adapter import ManualAssistedAdapter
from .models import (
    SUCCESS_SUBMISSION_STATUSES,
    PackageRef,
    SubmissionAttempt,
    SubmissionChannel,
    SubmissionEvidence,
    SubmissionMode,
    SubmissionReadinessReport,
)
from .store import SubmissionAttemptStore
from .transitions import apply_status_transition

DEFAULT_SUBMISSION_ATTEMPTS_ROOT = (
    Path(__file__).resolve().parents[3] / "data" / "submission_attempts"
)

_OPEN_STATUSES = frozenset({"in_progress", "manual_action_required"})


class SubmissionOrchestrator:
    """Sequences submission assistance without inventing success or silent submit."""

    def __init__(
        self,
        opportunities: OpportunityService,
        packages: ApplicationPackageService,
        *,
        store: SubmissionAttemptStore | None = None,
        attempts_root: Path | None = None,
        adapters: dict[SubmissionChannel, SubmissionAdapter] | None = None,
    ) -> None:
        self._opportunities = opportunities
        self._packages = packages
        if store is not None:
            self._store = store
        else:
            root = (
                attempts_root
                if attempts_root is not None
                else DEFAULT_SUBMISSION_ATTEMPTS_ROOT
            )
            self._store = JsonDirectorySubmissionAttemptStore(root)
        self._adapters: dict[SubmissionChannel, SubmissionAdapter] = (
            adapters
            if adapters is not None
            else {
                "fake": FakeSubmissionAdapter(),
                "manual_assisted": ManualAssistedAdapter(),
            }
        )

    def get_attempt(self, attempt_id: str) -> SubmissionAttempt:
        """Reload a submission attempt by id."""
        return self._store.load(attempt_id)

    def list_attempts(
        self,
        *,
        opportunity_id: str | None = None,
    ) -> list[SubmissionAttempt]:
        """List attempts, optionally filtered by opportunity."""
        return self._store.list(opportunity_id=opportunity_id)

    def check_readiness(
        self,
        opportunity_id: str,
        *,
        channel: SubmissionChannel | None = None,
        destination: str | None = None,
    ) -> SubmissionReadinessReport:
        """Validate submission preconditions without creating an attempt.

        Reuses the same gates as ``submit`` / ``record_manual_completion``.
        Does not invoke adapters and does not write to the attempt store.
        """
        messages: list[str] = []
        channels = sorted(self._adapters.keys())
        decision: str | None = None
        package_verified = False
        package_prepared_at = None

        try:
            opportunity = self._opportunities.get(opportunity_id)
        except (OpportunityNotFoundError, OpportunityStorageError) as error:
            return SubmissionReadinessReport(
                opportunity_id=opportunity_id,  # type: ignore[arg-type]
                ready=False,
                decision=None,
                package_verified=False,
                package_prepared_at=None,
                available_channels=channels,  # type: ignore[arg-type]
                messages=[str(error)],
            )

        decision = (
            opportunity.decision.decision if opportunity.decision else None
        )
        if decision != "apply":
            messages.append(
                f"Opportunity decision is {decision!r}; require 'apply'"
            )

        try:
            manifest = self._packages.get(opportunity_id, verify=True)
            package_verified = True
            package_prepared_at = manifest.prepared_at
            if manifest.opportunity_id != opportunity_id:
                package_verified = False
                messages.append(
                    "Package opportunity_id does not match requested opportunity_id"
                )
        except ApplicationPackageNotFoundError:
            messages.append(
                f"Application package not found for opportunity {opportunity_id}"
            )
        except ApplicationPackageIntegrityError as error:
            messages.append(str(error))
        except ApplicationPackageError as error:
            messages.append(str(error))

        if channel is not None:
            try:
                adapter = self._require_adapter(channel)
            except SubmissionChannelError as error:
                messages.append(str(error))
            else:
                if adapter.requires_destination and (
                    destination is None or not str(destination).strip()
                ):
                    messages.append(
                        f"Destination is required for channel '{channel}'"
                    )

        ready = decision == "apply" and package_verified and not messages
        if ready:
            messages.append("Submission preconditions satisfied")

        return SubmissionReadinessReport(
            opportunity_id=opportunity_id,  # type: ignore[arg-type]
            ready=ready,
            decision=decision,
            package_verified=package_verified,
            package_prepared_at=package_prepared_at,
            available_channels=channels,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

    def submit(
        self,
        opportunity_id: str,
        *,
        channel: SubmissionChannel,
        owner_approved_submit: bool,
        destination: str | None = None,
        mode: SubmissionMode | None = None,
        force_new_attempt: bool = False,
        force_reason: str | None = None,
        acknowledge_prior_outcome_unknown: bool = False,
    ) -> SubmissionAttempt:
        """Run gated submission assistance for one Opportunity via a channel adapter.

        No adapter call occurs until every gate and policy check passes.
        """
        if not owner_approved_submit:
            raise SubmissionGateError(
                "Explicit owner_approved_submit=True is required; "
                "submission approval is distinct from apply / package / document gates"
            )

        adapter = self._require_adapter(channel)
        resolved_mode = mode if mode is not None else adapter.mode
        package_ref = self._validate_preconditions(
            opportunity_id,
            channel=channel,
            destination=destination,
            adapter=adapter,
        )

        existing = self._attempts_for(opportunity_id, channel)
        open_attempt = self._latest_open(existing)
        if open_attempt is not None:
            return open_attempt

        self._enforce_duplicate_policy(
            existing,
            force_new_attempt=force_new_attempt,
            force_reason=force_reason,
            acknowledge_prior_outcome_unknown=acknowledge_prior_outcome_unknown,
        )

        now = datetime.now(UTC)
        attempt_id = new_submission_attempt_id()
        audit_bits: list[str] = []
        if force_new_attempt and force_reason:
            audit_bits.append(f"force_new_attempt_reason={force_reason}")
        if acknowledge_prior_outcome_unknown:
            audit_bits.append("acknowledged_prior_outcome_unknown=true")
        audit_suffix = "; ".join(audit_bits) if audit_bits else None

        ready = SubmissionAttempt(
            attempt_id=attempt_id,  # type: ignore[arg-type]
            opportunity_id=opportunity_id,  # type: ignore[arg-type]
            package=package_ref,
            channel=channel,
            mode=resolved_mode,
            destination=destination,
            status="ready",
            created_at=now,
            updated_at=now,
            evidence=SubmissionEvidence(
                owner_approved_submit=True,
                result_code=None,
                message=audit_suffix,
                failure_reason=None,
            ),
        )
        self._store.create(ready)

        stamp = datetime.now(UTC)
        in_progress = apply_status_transition(
            self._store.load(attempt_id),
            "in_progress",
            evidence=SubmissionEvidence(
                owner_approved_submit=True,
                result_code="adapter_invoked",
                message=f"Invoking {channel} adapter",
                failure_reason=None,
            ),
            updated_at=stamp,
        )
        self._store.save(in_progress)

        request = SubmissionAdapterRequest(
            attempt_id=attempt_id,
            opportunity_id=opportunity_id,  # type: ignore[arg-type]
            package=package_ref,
            channel=channel,
            mode=resolved_mode,
            destination=destination,
        )
        try:
            result = adapter.execute(request)
        except Exception as error:
            return self._persist_adapter_outcome(
                attempt_id,
                SubmissionAdapterResult(
                    status="failed",
                    result_code="adapter_exception",
                    message=f"Adapter raised {type(error).__name__}",
                    failure_reason=str(error) or type(error).__name__,
                ),
                audit_suffix=audit_suffix,
            )

        return self._persist_adapter_outcome(
            attempt_id, result, audit_suffix=audit_suffix
        )

    def record_manual_completion(
        self,
        opportunity_id: str,
        *,
        owner_approved_submit: bool,
        attestation: str,
        channel: SubmissionChannel = "manual_assisted",
        destination: str | None = None,
        confirmation_reference: str | None = None,
        force_new_attempt: bool = False,
        force_reason: str | None = None,
        acknowledge_prior_outcome_unknown: bool = False,
        completed_at: datetime | None = None,
    ) -> SubmissionAttempt:
        """Record that the owner completed submission outside the system.

        Does not invoke a channel adapter. Never claims adapter-submitted success.
        When an open ``in_progress`` / ``manual_action_required`` attempt exists for
        the channel, that attempt is completed; otherwise a new attempt is created.
        """
        if not owner_approved_submit:
            raise SubmissionGateError(
                "Explicit owner_approved_submit=True is required to record "
                "manual completion"
            )
        if not attestation or not attestation.strip():
            raise SubmissionGateError(
                "Non-empty owner attestation is required for manual completion"
            )

        # Manual completion does not need a live adapter, but channel must be known
        # so audit trails stay consistent with registered channels.
        adapter = self._require_adapter(channel)
        package_ref = self._validate_preconditions(
            opportunity_id,
            channel=channel,
            destination=destination,
            adapter=adapter,
            require_destination=destination is not None or adapter.requires_destination,
        )

        existing = self._attempts_for(opportunity_id, channel)
        open_attempt = self._latest_open(existing)
        completion_stamp = completed_at or datetime.now(UTC)
        evidence = self._manual_completion_evidence(
            attestation=attestation,
            confirmation_reference=confirmation_reference,
            force_new_attempt=force_new_attempt,
            force_reason=force_reason,
            acknowledge_prior_outcome_unknown=acknowledge_prior_outcome_unknown,
        )

        if open_attempt is not None:
            # in_progress and manual_action_required may both move to manual_completed.
            completed = apply_status_transition(
                open_attempt,
                "manual_completed",
                evidence=evidence,
                updated_at=completion_stamp,
                completed_at=completion_stamp,
            )
            return self._store.save(completed)

        self._enforce_duplicate_policy(
            existing,
            force_new_attempt=force_new_attempt,
            force_reason=force_reason,
            acknowledge_prior_outcome_unknown=acknowledge_prior_outcome_unknown,
        )

        now = datetime.now(UTC)
        attempt_id = new_submission_attempt_id()
        ready = SubmissionAttempt(
            attempt_id=attempt_id,  # type: ignore[arg-type]
            opportunity_id=opportunity_id,  # type: ignore[arg-type]
            package=package_ref,
            channel=channel,
            mode="assist_only",
            destination=destination,
            status="ready",
            created_at=now,
            updated_at=now,
            evidence=SubmissionEvidence(owner_approved_submit=True),
        )
        self._store.create(ready)

        in_progress = apply_status_transition(
            self._store.load(attempt_id),
            "in_progress",
            evidence=SubmissionEvidence(
                owner_approved_submit=True,
                result_code="manual_recording",
                message="Recording owner-attested manual completion (no adapter)",
            ),
            updated_at=datetime.now(UTC),
        )
        self._store.save(in_progress)

        completed = apply_status_transition(
            self._store.load(attempt_id),
            "manual_completed",
            evidence=evidence,
            updated_at=completion_stamp,
            completed_at=completion_stamp,
        )
        return self._store.save(completed)

    def _manual_completion_evidence(
        self,
        *,
        attestation: str,
        confirmation_reference: str | None,
        force_new_attempt: bool,
        force_reason: str | None,
        acknowledge_prior_outcome_unknown: bool,
    ) -> SubmissionEvidence:
        parts = [
            "manual_owner_attestation",
            f"attestation={attestation.strip()}",
        ]
        if confirmation_reference and confirmation_reference.strip():
            parts.append(f"confirmation_reference={confirmation_reference.strip()}")
        if force_new_attempt and force_reason:
            parts.append(f"force_new_attempt_reason={force_reason}")
        if acknowledge_prior_outcome_unknown:
            parts.append("acknowledged_prior_outcome_unknown=true")
        return SubmissionEvidence(
            owner_approved_submit=True,
            result_code="manual_owner_completed",
            message="; ".join(parts),
            failure_reason=None,
        )

    def _persist_adapter_outcome(
        self,
        attempt_id: str,
        result: SubmissionAdapterResult,
        *,
        audit_suffix: str | None = None,
    ) -> SubmissionAttempt:
        stamp = datetime.now(UTC)
        current = self._store.load(attempt_id)
        message = result.message
        if audit_suffix:
            message = f"{result.message}; {audit_suffix}"
        evidence = SubmissionEvidence(
            owner_approved_submit=True,
            result_code=result.result_code,
            message=message,
            failure_reason=result.failure_reason,
        )
        updated = apply_status_transition(
            current,
            result.as_attempt_status(),
            evidence=evidence,
            updated_at=stamp,
        )
        return self._store.save(updated)

    def _validate_preconditions(
        self,
        opportunity_id: str,
        *,
        channel: SubmissionChannel,
        destination: str | None,
        adapter: SubmissionAdapter,
        require_destination: bool | None = None,
    ) -> PackageRef:
        try:
            opportunity = self._opportunities.get(opportunity_id)
        except OpportunityNotFoundError as error:
            raise SubmissionGateError(str(error)) from error
        except OpportunityStorageError as error:
            raise SubmissionGateError(str(error)) from error

        decision = opportunity.decision.decision if opportunity.decision else None
        if decision != "apply":
            raise SubmissionGateError(
                f"Opportunity {opportunity_id} is not eligible for submission "
                f"(decision={decision!r}; require 'apply')"
            )

        try:
            manifest = self._packages.get(opportunity_id, verify=True)
        except ApplicationPackageNotFoundError as error:
            raise SubmissionGateError(
                f"Application package not found for opportunity {opportunity_id}"
            ) from error
        except ApplicationPackageIntegrityError as error:
            raise SubmissionGateError(str(error)) from error
        except ApplicationPackageError as error:
            raise SubmissionGateError(str(error)) from error

        if manifest.opportunity_id != opportunity_id:
            raise SubmissionGateError(
                "Package opportunity_id does not match requested opportunity_id"
            )

        needs_destination = (
            adapter.requires_destination
            if require_destination is None
            else require_destination
        )
        if needs_destination and (destination is None or not str(destination).strip()):
            raise SubmissionGateError(
                f"Destination is required for channel '{channel}'"
            )

        return PackageRef(
            opportunity_id=manifest.opportunity_id,
            prepared_at=manifest.prepared_at,
            manifest_hash=None,
        )

    def _require_adapter(self, channel: SubmissionChannel) -> SubmissionAdapter:
        try:
            return self._adapters[channel]
        except KeyError as error:
            raise SubmissionChannelError(
                f"Unknown or unregistered submission channel: {channel!r}"
            ) from error

    def _attempts_for(
        self,
        opportunity_id: str,
        channel: SubmissionChannel,
    ) -> list[SubmissionAttempt]:
        return [
            item
            for item in self._store.list(opportunity_id=opportunity_id)
            if item.channel == channel
        ]

    @staticmethod
    def _latest_open(attempts: list[SubmissionAttempt]) -> SubmissionAttempt | None:
        open_ones = [item for item in attempts if item.status in _OPEN_STATUSES]
        if not open_ones:
            return None
        return sorted(open_ones, key=lambda item: item.attempt_id)[-1]

    def _enforce_duplicate_policy(
        self,
        existing: list[SubmissionAttempt],
        *,
        force_new_attempt: bool,
        force_reason: str | None,
        acknowledge_prior_outcome_unknown: bool,
    ) -> None:
        successes = [
            item for item in existing if item.status in SUCCESS_SUBMISSION_STATUSES
        ]
        if successes:
            if not force_new_attempt:
                latest = sorted(successes, key=lambda item: item.attempt_id)[-1]
                raise SubmissionDuplicateError(
                    f"A successful submission attempt already exists for this "
                    f"opportunity and channel "
                    f"(attempt_id={latest.attempt_id}, status={latest.status}). "
                    f"Pass force_new_attempt=True with force_reason to create another."
                )
            if force_reason is None or not force_reason.strip():
                raise SubmissionGateError(
                    "force_new_attempt requires a non-empty auditable force_reason"
                )

        unknowns = [item for item in existing if item.status == "outcome_unknown"]
        if unknowns and not acknowledge_prior_outcome_unknown:
            latest = sorted(unknowns, key=lambda item: item.attempt_id)[-1]
            raise SubmissionDuplicateError(
                f"A prior attempt has outcome_unknown "
                f"(attempt_id={latest.attempt_id}). Pass "
                f"acknowledge_prior_outcome_unknown=True to create a new attempt; "
                f"uncertain outcomes are never auto-retried."
            )
