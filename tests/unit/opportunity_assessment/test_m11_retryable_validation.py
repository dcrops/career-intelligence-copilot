"""FR-019 M1.1 — selective Opportunity Assessment validation retryability."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.opportunity_assessment.errors import (
    ErrorDetail,
    OpportunityAssessmentValidationError,
    assessment_validation_is_retryable,
)
from career_intelligence.opportunity_assessment.models import FitDimensionAssessment


def test_judgment_material_inconsistency_is_retryable() -> None:
    err = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit",),
                msg="technical judgment 'strong' is inconsistent with material gap",
                type="judgment_material_inconsistency",
            )
        ]
    )
    assert assessment_validation_is_retryable(err) is True


def test_evidence_ref_name_mismatch_is_retryable() -> None:
    err = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit", "findings", 1, "job_evidence", 0, "name"),
                msg="technology name 'Node.js' does not match technologies[1].name 'HTML'",
                type="evidence_ref_name_mismatch",
            )
        ]
    )
    assert assessment_validation_is_retryable(err) is True


def test_evidence_ref_index_out_of_range_is_retryable() -> None:
    err = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit", "findings", 0, "job_evidence", 0, "item_index"),
                msg="technology item_index 9 is out of range for 3 technologies item(s)",
                type="evidence_ref_index_out_of_range",
            )
        ]
    )
    assert assessment_validation_is_retryable(err) is True


def test_forbidden_embedded_input_is_unrecoverable() -> None:
    err = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("job_analysis",),
                msg="assessor payload must not include 'job_analysis'",
                type="forbidden_embedded_input",
            )
        ]
    )
    assert assessment_validation_is_retryable(err) is False


def test_unknown_value_error_is_unrecoverable() -> None:
    err = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit", "judgment"),
                msg="Input should be ...",
                type="value_error",
            )
        ]
    )
    assert assessment_validation_is_retryable(err) is False


def test_mixed_retryable_and_forbidden_is_unrecoverable() -> None:
    err = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit",),
                msg="inconsistent",
                type="judgment_material_inconsistency",
            ),
            ErrorDetail(
                loc=("profile",),
                msg="forbidden",
                type="forbidden_embedded_input",
            ),
        ]
    )
    assert assessment_validation_is_retryable(err) is False


def test_empty_errors_unrecoverable() -> None:
    err = OpportunityAssessmentValidationError([])
    assert assessment_validation_is_retryable(err) is False


def test_model_validator_emits_judgment_code() -> None:
    with pytest.raises(ValidationError) as raised:
        FitDimensionAssessment.model_validate(
            {
                "dimension": "technical",
                "judgment": "strong",
                "summary": "Overstated.",
                "findings": [
                    {
                        "kind": "gap",
                        "importance": "material",
                        "summary": "Missing production LLM delivery evidence.",
                        "job_evidence": [
                            {
                                "source": "experience_requirement",
                                "item_index": 0,
                            }
                        ],
                        "profile_evidence": [],
                    }
                ],
            }
        )
    types = {e["type"] for e in raised.value.errors()}
    assert "judgment_material_inconsistency" in types
