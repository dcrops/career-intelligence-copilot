# Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [001](001_python_yaml_profile_foundation.md) | Python + YAML profile foundation | Accepted |
| [002](002_opportunity_persistence.md) | Opportunity persistence | Accepted |
| [003](003_application_workflow_orchestration.md) | Application workflow orchestration architecture | Accepted — thin in-repo runner; LangGraph not required for current FR-008 scope |
| [004](004_opportunity_review_boundary.md) | Opportunity as pre-decision system of record; review queue as derived projection | Accepted (FR-009 M0), implemented and closed (FR-009 M1–M4; Decision 8 amended by the M4 ranking calibration) — amends ADR-002 persistence boundary |

Related: [04_functional_specification.md](../04_functional_specification.md) § FR-008,
§ FR-009, § FR-010, § FR-011, § FR-012; [10_roadmap.md](../10_roadmap.md) § Horizon 1A.

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
[M2](../eval/fr012_m2_owner_workflow.md)).
Post-FR-010 architecture validation:
[eval/architecture_health_check_post_fr010.md](../eval/architecture_health_check_post_fr010.md).

**FR-011 ADR note:** No new ADR. Preparation orchestration is a dedicated coordinator
outside the FR-008 runner and does not amend ADR-002 / ADR-003 / ADR-004.

**FR-012 ADR note:** No new ADR. Submission assistance is a dedicated coordinator
with append-only attempt audit and a thin CLI. It does not amend ADR-002 / ADR-003 /
ADR-004, does not write PipelineStatus (FR-013), and does not wire FR-008 submit.
