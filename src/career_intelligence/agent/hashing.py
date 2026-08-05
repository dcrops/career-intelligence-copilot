"""Snapshot hashing for loop detection (FR-015 M2)."""

from __future__ import annotations

import hashlib
import json

from .models import ReadinessSnapshot


def compute_snapshot_hash(snapshot: ReadinessSnapshot) -> str:
    """Return a stable SHA-256 hex digest of readiness fields that affect policy."""
    payload = {
        "opportunity_id": snapshot.opportunity_id,
        "decision": snapshot.decision,
        "artefacts": snapshot.artefacts.model_dump(mode="json"),
        "package": snapshot.package.model_dump(mode="json"),
        "truth": {
            "status": snapshot.truth.status,
            "report_ref": snapshot.truth.report_ref,
            "owner_edited_markdown_since_validation": (
                snapshot.truth.owner_edited_markdown_since_validation
            ),
            "blocking_finding_codes": list(snapshot.truth.blocking_finding_codes),
        },
        "owner_approvals_present": snapshot.owner_approvals_present,
        "clarification_required": snapshot.clarification_required,
        "clarification_message": snapshot.clarification_message,
        "provider_available": snapshot.provider_available,
        "contradictory_flags": list(snapshot.contradictory_flags),
        # Exclude prior_agent_run_* and observed_at from hash so resume inspect
        # can change loop context without false "progress".
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
