"""FR-019 M1.1 functional: selective assess retry + failed-run recovery."""

from __future__ import annotations

from typing import Any

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment import OpportunityAssessmentService
from career_intelligence.opportunity_assessment.assessor import OpportunityAssessmentPayload
from career_intelligence.opportunity_assessment.errors import (
    ErrorDetail,
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.fixture_assessor import FixtureAssessor
from career_intelligence.orchestration import (
    ApplicationWorkflowRunner,
    JsonDirectoryCheckpointStore,
    RetryPolicy,
    WorkflowDependencies,
)
from career_intelligence.profile.models import CareerProfile
from tests.unit.orchestration.m1_helpers import (
    fixture_job_input,
    offline_dependencies,
    offline_runner,
)


class _SequenceAssessor:
    """First N calls raise typed validation errors; then FixtureAssessor."""

    def __init__(
        self,
        *,
        fail_count: int,
        error: OpportunityAssessmentValidationError,
    ) -> None:
        self._remaining = fail_count
        self._error = error
        self._ok = FixtureAssessor()
        self.calls = 0

    def assess(
        self,
        job_analysis: JobAnalysis,
        profile: CareerProfile,
    ) -> OpportunityAssessmentPayload:
        self.calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            raise self._error
        return self._ok.assess(job_analysis, profile)


def _judgment_error() -> OpportunityAssessmentValidationError:
    return OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit",),
                msg=(
                    "technical judgment 'strong' is inconsistent with material "
                    "gap/conflict findings"
                ),
                type="judgment_material_inconsistency",
            )
        ]
    )


def _evidence_mismatch_error() -> OpportunityAssessmentValidationError:
    return OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("technical_fit", "findings", 1, "job_evidence", 0, "name"),
                msg="technology name 'Node.js' does not match technologies[1].name 'HTML'",
                type="evidence_ref_name_mismatch",
            )
        ]
    )


def _runner_with_assessor(
    tmp_path,
    assessor: Any,
    *,
    store=None,
    retry_policy: RetryPolicy | None = None,
) -> ApplicationWorkflowRunner:
    deps = offline_dependencies(
        store=store or JsonDirectoryCheckpointStore(tmp_path / "runs"),
        opportunities_dir=tmp_path / "opps",
    )
    deps = WorkflowDependencies(
        profile=deps.profile,
        job_analysis=deps.job_analysis,
        assessment=OpportunityAssessmentService(assessor),
        portfolio_matching=deps.portfolio_matching,
        application_strategy=deps.application_strategy,
        store=deps.store,
        opportunities=deps.opportunities,
    )
    return ApplicationWorkflowRunner(
        deps,
        retry_policy=retry_policy or RetryPolicy(max_attempts=3),
    )


def test_judgment_validation_retries_then_succeeds(tmp_path) -> None:
    assessor = _SequenceAssessor(fail_count=1, error=_judgment_error())
    runner = _runner_with_assessor(tmp_path, assessor)
    state = runner.start(fixture_job_input())
    assert state.status == "awaiting_owner"
    assert assessor.calls == 2
    types = [e.event_type for e in state.execution.events]
    assert "retry_scheduled" in types
    assert state.artefacts.assessment is not None
    assert state.artefacts.opportunity_id is not None
    analyse_starts = [
        e
        for e in state.execution.events
        if e.event_type == "node_started" and e.node_id == "analyse"
    ]
    assert len(analyse_starts) == 1


def test_evidence_mismatch_retries_then_succeeds(tmp_path) -> None:
    assessor = _SequenceAssessor(fail_count=1, error=_evidence_mismatch_error())
    runner = _runner_with_assessor(tmp_path, assessor)
    state = runner.start(fixture_job_input())
    assert state.status == "awaiting_owner"
    assert assessor.calls == 2
    assert "retry_scheduled" in [e.event_type for e in state.execution.events]


def test_retryable_validation_exhausts_at_three(tmp_path) -> None:
    assessor = _SequenceAssessor(fail_count=10, error=_judgment_error())
    runner = _runner_with_assessor(tmp_path, assessor)
    state = runner.start(fixture_job_input())
    assert state.status == "failed"
    assert assessor.calls == 3
    assert state.artefacts.assessment is None
    assert state.artefacts.opportunity_id is None
    assert state.artefacts.job_analysis is not None
    assert list(runner.opportunities.list_opportunities()) == []
    types = [e.event_type for e in state.execution.events]
    assert types.count("retry_scheduled") == 2
    assert "retry_exhausted" in types


def test_forbidden_embedded_does_not_retry(tmp_path) -> None:
    err = OpportunityAssessmentValidationError(
        [
            ErrorDetail(
                loc=("job_analysis",),
                msg="assessor payload must not include 'job_analysis'",
                type="forbidden_embedded_input",
            )
        ]
    )
    assessor = _SequenceAssessor(fail_count=5, error=err)
    runner = _runner_with_assessor(tmp_path, assessor)
    state = runner.start(fixture_job_input())
    assert state.status == "failed"
    assert assessor.calls == 1
    assert all(e.event_type != "retry_scheduled" for e in state.execution.events)


def test_retry_failed_reuses_job_analysis_and_succeeds(tmp_path) -> None:
    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    bad = _SequenceAssessor(fail_count=10, error=_judgment_error())
    first = _runner_with_assessor(tmp_path, bad, store=store)
    failed = first.start(fixture_job_input())
    assert failed.status == "failed"
    run_id = failed.run_id
    ja_id = id(failed.artefacts.job_analysis)
    assert failed.artefacts.job_analysis is not None

    good = FixtureAssessor()
    second = _runner_with_assessor(tmp_path, good, store=store)
    resumed = second.retry_failed(run_id)
    assert resumed.run_id == run_id
    assert resumed.status == "awaiting_owner"
    assert resumed.artefacts.opportunity_id is not None
    assert len(list(second.opportunities.list_opportunities())) == 1
    analyse_starts = [
        e
        for e in resumed.execution.events
        if e.event_type == "node_started" and e.node_id == "analyse"
    ]
    assert len(analyse_starts) == 1
    # Same checkpointed analysis object content / single analyse pass
    assert resumed.artefacts.job_analysis is not None
    assert resumed.artefacts.job_analysis.posting.title == failed.artefacts.job_analysis.posting.title
    _ = ja_id  # identity may change across load; content reuse is the contract


def test_retry_failed_refuses_non_failed(tmp_path) -> None:
    from career_intelligence.orchestration import WorkflowResumeError

    runner = offline_runner(
        store=JsonDirectoryCheckpointStore(tmp_path / "runs"),
        opportunities_dir=tmp_path / "opps",
    )
    ok = runner.start(fixture_job_input())
    assert ok.status == "awaiting_owner"
    try:
        runner.retry_failed(ok.run_id)
        raise AssertionError("expected WorkflowResumeError")
    except WorkflowResumeError as error:
        assert "failed" in str(error)


def test_mailbox_ledger_untouched_by_retry_failed(tmp_path) -> None:
    """Recovery must not mutate mailbox ledger files."""
    from career_intelligence.mailbox.ledger import EmailIntakeLedger
    from career_intelligence.mailbox.models import IngestedMailMessage

    ledger_path = tmp_path / "mailbox" / "processed.json"
    ledger = EmailIntakeLedger(ledger_path)
    ledger.record(
        IngestedMailMessage(
            message_id="<test@example.com>",
            folder="CIC Job Alerts",
            uid=1,
            uidvalidity=1,
            raw_rfc822=b"From: x\r\n\r\nbody",
            content_sha256="abc",
            source="imap",
        ),
        outcome_summary="acquired=0 skipped=0 failed=1",
    )
    before = ledger_path.read_text(encoding="utf-8")

    store = JsonDirectoryCheckpointStore(tmp_path / "runs")
    bad = _SequenceAssessor(fail_count=10, error=_judgment_error())
    first = _runner_with_assessor(tmp_path, bad, store=store)
    failed = first.start(fixture_job_input())
    second = _runner_with_assessor(tmp_path, FixtureAssessor(), store=store)
    second.retry_failed(failed.run_id)

    assert ledger_path.read_text(encoding="utf-8") == before
