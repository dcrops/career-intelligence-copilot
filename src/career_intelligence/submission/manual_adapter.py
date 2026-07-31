"""Assisted-manual submission adapter (FR-012 M1).

Provides structured instructions for the owner to submit outside the system.
Never claims success, never opens a browser, never touches the network.
"""

from __future__ import annotations

from .adapters import SubmissionAdapterRequest, SubmissionAdapterResult
from .models import SubmissionChannel, SubmissionMode


class ManualAssistedAdapter:
    """Offline checklist adapter — always returns ``manual_action_required``."""

    def __init__(self) -> None:
        self.call_count = 0
        self.last_request: SubmissionAdapterRequest | None = None

    @property
    def channel(self) -> SubmissionChannel:
        return "manual_assisted"

    @property
    def mode(self) -> SubmissionMode:
        return "assist_only"

    @property
    def requires_destination(self) -> bool:
        return True

    def execute(self, request: SubmissionAdapterRequest) -> SubmissionAdapterResult:
        self.call_count += 1
        self.last_request = request
        destination = request.destination or "(no destination provided)"
        checklist = (
            "Assisted-manual submission — owner must complete externally.\n"
            f"1. Open destination: {destination}\n"
            f"2. Use prepared package for opportunity {request.opportunity_id} "
            f"(prepared_at={request.package.prepared_at.isoformat()}).\n"
            "3. Complete the employer application form using package artefacts.\n"
            "4. Capture any confirmation reference locally.\n"
            "5. Call SubmissionOrchestrator.record_manual_completion to attest "
            "completion (this adapter never records success)."
        )
        return SubmissionAdapterResult(
            status="manual_action_required",
            result_code="manual_assisted_checklist",
            message=checklist,
            failure_reason=None,
        )
