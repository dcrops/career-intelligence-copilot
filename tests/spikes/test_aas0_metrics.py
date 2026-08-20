"""SpikeMetrics construction/serialisation and Review-document recording."""

from __future__ import annotations

import json
import sys
from dataclasses import fields
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.document_gates import (  # noqa: E402
    ReviewDocumentObservation,
    evaluate_review_document_gate,
)
from aas0.metrics import SpikeMetrics  # noqa: E402

G360_CV = "David Cropper - Global 360 - AI Engineer - Applied - CV.pdf"
G360_CL = "David Cropper - Global 360 - AI Engineer - Applied - Cover Letter.pdf"

# Fields stored outside resume_lifecycle / not serialised as lifecycle keys.
_NON_LIFECYCLE_FIELDS = {
    "opportunity_id",
    "started_at_monotonic",
    "automation_seconds",
    "waiting_seconds",
    "owner_attention_seconds",
    "fields",
    "pages_traversed",
    "documents_uploaded",
    "failures",
    "screenshots",
    "final_stage_reached",
    "submit_clicked",
    "browser_kept_open_for_owner",
    "application_submission",
    "submission_observation_evidence",
    "notes",
}


def test_spike_metrics_supports_review_document_reason_and_serialises() -> None:
    metrics = SpikeMetrics(opportunity_id="opp_01KZQK08P757DCAE1RM5GPPKC6")
    assert metrics.review_document_reason == ""
    payload = metrics.to_dict()
    lifecycle = payload["resume_lifecycle"]
    assert "review_document_reason" in lifecycle
    assert lifecycle["review_document_reason"] == ""
    json.dumps(payload)


def test_review_document_gate_records_reason_on_spike_metrics(tmp_path: Path) -> None:
    metrics = SpikeMetrics(opportunity_id="opp_01KZQK08P757DCAE1RM5GPPKC6")
    observation = ReviewDocumentObservation(
        resume_filename=G360_CV,
        cover_letter_filename=G360_CL,
        observable=True,
    )
    gate = evaluate_review_document_gate(
        expected_cv=G360_CV,
        expected_cover_letter=G360_CL,
        observation=observation,
    )
    assert gate.reason == "review_documents_match"
    metrics.record_review_document_gate(
        observed_cv=gate.observed_cv,
        observed_cover_letter=gate.observed_cover_letter,
        reason=gate.reason,
    )
    assert metrics.review_document_reason == "review_documents_match"
    assert metrics.review_observed_cv == G360_CV
    assert metrics.review_observed_cover_letter == G360_CL
    payload = metrics.to_dict()
    lifecycle = payload["resume_lifecycle"]
    assert lifecycle["review_document_reason"] == "review_documents_match"
    assert lifecycle["review_observed_cv"] == G360_CV
    assert lifecycle["review_observed_cover_letter"] == G360_CL
    path = tmp_path / "metrics.json"
    metrics.write_json(path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["resume_lifecycle"]["review_document_reason"] == "review_documents_match"


def test_resume_lifecycle_serialisation_matches_dataclass_fields() -> None:
    """Catch missing dataclass fields or unserialised lifecycle metrics offline."""
    metrics = SpikeMetrics(opportunity_id="opp_test")
    payload = metrics.to_dict()
    declared = {item.name for item in fields(SpikeMetrics)} - _NON_LIFECYCLE_FIELDS
    serialised = set(payload["resume_lifecycle"])
    assert serialised == declared
    for name in declared:
        getattr(metrics, name)
    for name in (
        "review_document_reason",
        "review_observed_cv",
        "review_observed_cover_letter",
        "cv_selection_reason",
        "expected_cv_selected",
        "cleanup_candidate",
        "cleanup_candidate_reason",
        "resume_rotation_attempted",
        "resume_rotation_reason",
        "resume_deleted_filename",
        "resume_rotation_retry_attempted",
        "resume_rotation_retry_outcome",
        "default_resume_before",
        "default_observable_before",
        "default_changed_unexpected",
        "default_checkbox_reason",
        "default_checkbox_still_checked",
        "default_checkbox_uncheck_threw",
        "default_checkbox_baseline",
        "default_checkbox_settled_default",
        "default_checkbox_settle_poll_count",
        "default_checkbox_settle_wait_ms",
        "resume_default_before_deletion",
        "resume_default_after_deletion",
        "upload_failure_reason",
        "expected_cv_filename",
        "expected_cover_letter_filename",
    ):
        assert name in serialised
