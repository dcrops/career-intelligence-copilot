"""OAT-001 Phase 4 — owner presentation polish tests."""

from __future__ import annotations

from career_intelligence.agent import (
    AdapterExecutionError,
    AgentGoal,
    AgentRuntime,
    DeterministicActionProposer,
    InMemoryAgentRunStore,
    ScriptedActionExecutor,
    StaticReadinessBuilder,
    format_agent_run_report,
    owner_action_required,
)
from career_intelligence.agent.error_mapping import stop_reason_for_adapter_error
from career_intelligence.agent.presentation import pipeline_owner_note
from tests.unit.agent.helpers import (
    OPP,
    make_package,
    make_snapshot,
    make_truth,
)


def test_material_benefit_maps_to_dedicated_stop_reason() -> None:
    err = AdapterExecutionError(
        "preparation run apr_x ended as failed: Material-benefit gate refused "
        "TailoringPlan: application_tier is 'silver' and next_actions does not "
        "include consider_cv_tailoring. Set override_material_benefit=True "
        "to proceed with an explicit recorded override."
    )
    assert stop_reason_for_adapter_error(err) == "material_benefit_required"


def test_unrelated_adapter_error_remains_unexpected() -> None:
    err = AdapterExecutionError("WeasyPrint is required for PDF rendering.")
    assert stop_reason_for_adapter_error(err) == "unexpected_failure"


def test_runtime_material_benefit_awaiting_owner_not_unexpected() -> None:
    class _FailingPrep:
        def execute(self, action, snapshot, *, completed_actions):  # noqa: ANN001
            raise AdapterExecutionError(
                "Material-benefit gate refused TailoringPlan: "
                "Set override_material_benefit=True to proceed"
            )

    snap = make_snapshot(package=make_package(status="absent"))
    run = AgentRuntime(
        readiness=StaticReadinessBuilder([snap]),
        executor=_FailingPrep(),  # type: ignore[arg-type]
        proposer=DeterministicActionProposer(),
        store=InMemoryAgentRunStore(),
    ).start(AgentGoal(opportunity_id=OPP), owner_approvals_present=True)
    assert run.stop_reason == "material_benefit_required"
    assert run.status == "awaiting_owner"
    report = format_agent_run_report(run)
    assert "material_benefit_required" in report
    assert "--override-material-benefit" in report
    assert "unexpected_failure" not in report
    assert "Resume is not available" not in owner_action_required(
        run.stop_reason, status=run.status
    )


def test_failed_guidance_says_start_new_run_not_resume() -> None:
    text = owner_action_required("unexpected_failure", status="failed")
    assert "start a new" in text.lower()
    assert "resume is not available" in text.lower()
    text2 = owner_action_required("unsupported_state", status="failed")
    assert "resume is not available" in text2.lower()


def test_awaiting_owner_guidance_mentions_resume() -> None:
    text = owner_action_required("truth_validation_blocked", status="awaiting_owner")
    assert "resume" in text.lower()
    text2 = owner_action_required("material_benefit_required", status="awaiting_owner")
    assert "--override-material-benefit" in text2
    assert "resume" in text2.lower()


def test_pipeline_messaging_interviewing() -> None:
    note = pipeline_owner_note("interviewing")
    assert note is not None
    assert "interviewing" in note.lower()
    assert "usually unnecessary" in note.lower()
    assert "owner-controlled" in note.lower()


def test_pipeline_messaging_in_report() -> None:
    snap = make_snapshot(
        package=make_package(status="absent"),
        pipeline_status="interviewing",
    )
    # Force unsupported via missing decision
    snap = make_snapshot(
        decision=None,
        package=make_package(status="absent"),
        pipeline_status="submitted",
    )
    run = AgentRuntime(
        readiness=StaticReadinessBuilder([snap]),
        executor=ScriptedActionExecutor(),
        store=InMemoryAgentRunStore(),
    ).start(AgentGoal(opportunity_id=OPP), owner_approvals_present=True)
    report = format_agent_run_report(run)
    assert "pipeline:" in report
    assert "submitted" in report
    assert "usually unnecessary" in report.lower()
    assert "Initial inspection" in report


def test_truth_blockers_section_in_show() -> None:
    snap = make_snapshot(
        package=make_package(
            status="present",
            cv_present=True,
            cover_letter_present=True,
            manifest_ref="package:x",
        ),
        truth=make_truth(
            status="fail",
            report_ref="trp_x",
            blocking_finding_codes=(
                "Unsupported certification: AWS Certified Developer",
            ),
        ),
    )
    run = AgentRuntime(
        readiness=StaticReadinessBuilder([snap]),
        executor=ScriptedActionExecutor(),
        store=InMemoryAgentRunStore(),
    ).start(AgentGoal(opportunity_id=OPP), owner_approvals_present=True)
    report = format_agent_run_report(run)
    assert "Truth blockers" in report
    assert "Unsupported certification: AWS Certified Developer" in report
    assert "Initial inspection" in report


def test_override_guidance_in_owner_action() -> None:
    text = owner_action_required("material_benefit_required", status="awaiting_owner")
    assert "Preparation blocked" in text or "material-benefit" in text.lower()
    assert "--override-material-benefit" in text
