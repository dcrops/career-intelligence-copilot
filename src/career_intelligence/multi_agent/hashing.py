"""Observation hashing for FR-016 orchestration loop detection."""

from __future__ import annotations

import hashlib
import json

from .models import OrchestrationObservation


def compute_observation_hash(observation: OrchestrationObservation) -> str:
    """Stable content hash of routing-relevant observation fields."""
    payload = {
        "opportunity_id": observation.opportunity_id,
        "decision": observation.decision,
        "readiness_primary_state_class": observation.readiness_primary_state_class,
        "package_status": observation.package_status,
        "truth_status": observation.truth_status,
        "pipeline_status": observation.pipeline_status,
        "owner_approvals_present": observation.owner_approvals_present,
        "prior_agent_run_ids": list(observation.prior_agent_run_ids),
        "truth_blocking_labels": list(observation.truth_blocking_labels),
        "contradictory_flags": list(observation.contradictory_flags),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
