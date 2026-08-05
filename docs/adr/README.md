# Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [001](001_python_yaml_profile_foundation.md) | Python + YAML profile foundation | Accepted |
| [002](002_opportunity_persistence.md) | Opportunity persistence | Accepted |
| [003](003_application_workflow_orchestration.md) | Application workflow orchestration architecture | Accepted — thin in-repo runner; LangGraph not required for current FR-008 scope |
| [004](004_opportunity_review_boundary.md) | Opportunity as pre-decision system of record; review queue as derived projection | Accepted (FR-009 M0), implemented and closed (FR-009 M1–M4; Decision 8 amended by the M4 ranking calibration) — amends ADR-002 persistence boundary |
| [005](005_application_pipeline_lifecycle.md) | Application pipeline lifecycle (stored status + append-only events) | Accepted (FR-013 M1) — amends ADR-002 lifecycle audit; reaffirms ADR-004; SubmissionAttempt never auto-advances status |
| [006](006_recruiter_document_truth_validation.md) | Recruiter document truth validation (deterministic fail-closed boundary) | Accepted (FR-014 M1) — detection certainty ≠ evidence validation; JD never authorizes candidate capability |
| [007](007_bounded_agentic_workflow.md) | Bounded Agentic Workflow (BOPA; policy B; ToolPolicy) | Accepted (FR-015 frozen) — one agent, one Opportunity, post-acquisition; does not wrap FR-008; no submit/pipeline/discovery |

Related: [04_functional_specification.md](../04_functional_specification.md) § FR-008,
§ FR-009, § FR-010, § FR-011, § FR-012, § FR-013, § FR-014, § FR-015; [10_roadmap.md](../10_roadmap.md) § Horizon 1A.

Close-out records:
[eval/fr008_workflow_orchestration.md](../eval/fr008_workflow_orchestration.md),
[eval/fr009_opportunity_review_queue.md](../eval/fr009_opportunity_review_queue.md),
[eval/fr010_application_package.md](../eval/fr010_application_package.md),
[eval/fr011_application_preparation.md](../eval/fr011_application_preparation.md)
(milestones [M0](../eval/fr011_m0_application_preparation.md),
[M1](../eval/fr011_m1_executable_preparation.md)),
[eval/fr012_submission_assistance.md](../eval/fr012_submission_assistance.md)
(milestones [M0](../eval/fr012_m0_submission_contracts.md),
[M1](../eval/fr012_m1_submission_orchestration.md),
[M2](../eval/fr012_m2_owner_workflow.md)),
[eval/fr013_m0_engineering_spike.md](../eval/fr013_m0_engineering_spike.md) (Accepted),
[eval/fr013_m1_pipeline_contracts.md](../eval/fr013_m1_pipeline_contracts.md),
[eval/fr013_m2_pipeline_tracking.md](../eval/fr013_m2_pipeline_tracking.md),
[eval/fr013_m3_owner_workflow.md](../eval/fr013_m3_owner_workflow.md),
[eval/fr013_m4_reporting_acceptance.md](../eval/fr013_m4_reporting_acceptance.md),
[eval/fr013_application_pipeline_tracking.md](../eval/fr013_application_pipeline_tracking.md)
(FR-013 frozen),
[eval/fr014_m0_engineering_spike.md](../eval/fr014_m0_engineering_spike.md) (Accepted),
[eval/fr014_m1_truth_validation_contracts.md](../eval/fr014_m1_truth_validation_contracts.md),
[eval/fr014_m2_technology_validation.md](../eval/fr014_m2_technology_validation.md),
[eval/fr014_m3_owner_workflow.md](../eval/fr014_m3_owner_workflow.md),
[eval/fr014_m4_claim_validation.md](../eval/fr014_m4_claim_validation.md),
[eval/fr014_recruiter_document_truth_validation.md](../eval/fr014_recruiter_document_truth_validation.md) (FR-014 frozen),
[eval/fr015_m0_engineering_spike.md](../eval/fr015_m0_engineering_spike.md) (Accepted),
[eval/fr015_m1_agent_contracts.md](../eval/fr015_m1_agent_contracts.md),
[eval/fr015_m2_agent_runtime.md](../eval/fr015_m2_agent_runtime.md),
[eval/fr015_m3_owner_cli.md](../eval/fr015_m3_owner_cli.md).
Post-FR-010 architecture validation:
[eval/architecture_health_check_post_fr010.md](../eval/architecture_health_check_post_fr010.md).

**FR-011 ADR note:** No new ADR. Preparation orchestration is a dedicated coordinator
outside the FR-008 runner and does not amend ADR-002 / ADR-003 / ADR-004.

**FR-012 ADR note:** No new ADR. Submission assistance is a dedicated coordinator
with append-only attempt audit and a thin CLI. It does not amend ADR-002 / ADR-003 /
ADR-004, does not write PipelineStatus (FR-013), and does not wire FR-008 submit.

**FR-013 ADR note:** [ADR-005](005_application_pipeline_lifecycle.md) accepted at M1;
FR-013 **complete and frozen**
([eval/fr013_application_pipeline_tracking.md](../eval/fr013_application_pipeline_tracking.md)).
Opportunity remains current-state SoT; append-only PipelineEvents provide audit;
SubmissionAttempt success never auto-advances `Opportunity.status`.

**FR-014 ADR note:** [ADR-006](006_recruiter_document_truth_validation.md) accepted at M1.
FR-014 **complete and frozen**
([eval/fr014_recruiter_document_truth_validation.md](../eval/fr014_recruiter_document_truth_validation.md)).
Detection certainty is distinct from evidence validation; PASS requires complete
coverage and performed detection + validation; JD/assessment/strategy/plans never
authorize candidate capability. M2–M4 delivered technology + extended claim kinds,
owner CLI, and fail-closed package/submission gates.

**FR-015 ADR note:** [ADR-007](007_bounded_agentic_workflow.md) accepted; FR-015 frozen (M1–M4).
BOPA coordinates post-acquisition package/truth readiness under deterministic
ToolPolicy; does not wrap FR-008. M1 contracts; M2 runtime; M3 owner CLI
([eval/fr015_m3_owner_cli.md](../eval/fr015_m3_owner_cli.md)).
