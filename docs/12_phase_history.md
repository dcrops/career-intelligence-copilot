# Phase History

Brief narrative of completed delivery phases. For day-to-day status and sequencing,
see [10_roadmap.md](10_roadmap.md). For chronological product decisions, see
[11_changelog.md](11_changelog.md). For Phase 2 release evidence, see
[eval/phase2_release_report.md](eval/phase2_release_report.md).

This document does **not** list every changelog entry. It freezes high-level outcomes
and lessons so later work (starting with FR-006b) does not reopen settled Phase 2
questions without explicit owner intent.

---

## Phase 1 — Product Definition

**Objective:** Align vision, Phase 2 MVP scope, and repository structure before writing
product code.

**Major milestones:**

- Product vision, problem statement, and functional specification for Phase 2
- Engineering principles and domain model (decision loop)
- Repository layout (docs, operational folders, placeholders)
- ADR-001 — Python / YAML / public profile service foundation

**Outcome:** Phase 2 Job Intelligence MVP scope approved; implementation unblocked.

**Lessons learned:**

- Keep authoritative docs few and cross-linked; avoid duplicating requirements into
  chat or informal notes.
- Horizon 1 urgency must be explicit in prioritisation, or portfolio/learning goals
  will expand Phase 2 prematurely.
- Defer stack choices until a validated need exists (ADR-001 earned the foundation).

---

## Phase 2 — Job Intelligence (MVP)

**Objective:** Ship a usable vertical slice: analyse a job, assess fit, match
portfolio, recommend effort, optionally tailor a CV, persist the opportunity, record
owner decisions, and rank open opportunities — on real SEEK/LinkedIn ads.

**Major milestones:**

| Track | Delivered |
|-------|-----------|
| Intelligence | FR-001 → FR-005 (profile, analysis, assessment, portfolio, strategy) |
| Documents | FR-006 CV generation (owner-sequenced; not originally a Phase 2 exit blocker) |
| Close-out loop | M1 persistence, M2 decisions/outcomes, M3 CSV bridge, M4 ranking, M4a identity, M5 GO |

**Outcome:** Phase 2 **Complete** with formal **GO**
([eval/phase2_release_report.md](eval/phase2_release_report.md)). The decision loop is
the operational foundation for Horizon 1.

**Lessons learned:**

- Persist trusted artefacts early; ranking and list UX fail without identity and a
  durable Opportunity record (M4a was a corrective milestone, not a nice-to-have).
- Keep CSV as a derived view; structured store as system of record avoids parallel
  trackers (M3).
- Separate ranking from `OpportunityService`; keep comparison deterministic and
  explainable (M4).
- Human review and material-benefit gates (e.g. CV) are product behaviour — document
  override paths rather than weakening gates for convenience.
- Live OpenAI eval on real ads surfaces evidence-contract failures fixtures miss;
  prompt versions (FR-002 v8, FR-003 v11) are part of the baseline.

**Do not reopen without explicit owner request:** Phase 2 exit criteria, Opportunity
SoT shape, ranking sort key, or Horizon 2 domains (recruiters, networking, meetups).

---

## Next

**Current focus:** Horizon 1B — **FR-019 Core Loop Operationalisation** (M0 GO;
M1 ready —
[eval/fr019_core_loop_operationalisation.md](eval/fr019_core_loop_operationalisation.md)).
**FR-018 Complete / Frozen / Accepted**
([eval/fr018_opportunity_discovery_acquisition.md](eval/fr018_opportunity_discovery_acquisition.md);
[ADR-010](adr/010_opportunity_discovery_ingress.md);
[package](masterclass/FR018/)).
**Horizon 1A complete:** FR-008–FR-017 frozen. **FR-017** is **complete and frozen**
([acceptance](eval/fr017_agent_evaluation_observability.md);
[ADR-009](adr/009_orchestration_evaluation_substrate.md);
[package](masterclass/FR017/)). **FR-016** is
**complete and frozen** (learning proof — **GO AS LEARNING PROOF ONLY**;
[acceptance](eval/fr016_multi_agent_orchestration.md);
[ADR-008](adr/008_multi_agent_orchestration.md)). **FR-015** Bounded Agentic Workflow is
**complete and frozen**
([acceptance](eval/fr015_bounded_agentic_workflow.md);
[ADR-007](adr/007_bounded_agentic_workflow.md);
milestones [M0](eval/fr015_m0_engineering_spike.md)–[M4](eval/fr015_m4_evaluation.md)).
**FR-014** Recruiter Document Truth Validation is
**complete and frozen**
([acceptance](eval/fr014_recruiter_document_truth_validation.md);
[ADR-006](adr/006_recruiter_document_truth_validation.md)).
**Completed:** FR-008 Job Acquisition & Workflow Orchestration (2026-07-29);
**FR-009** Opportunity Review Queue & Ranking (2026-07-30 —
[acceptance](eval/fr009_opportunity_review_queue.md)); **FR-010** Application Package
Preparation (2026-07-31 — [acceptance](eval/fr010_application_package.md));
**FR-011** Application Preparation Orchestration (2026-07-31 —
[acceptance](eval/fr011_application_preparation.md);
milestones [M0](eval/fr011_m0_application_preparation.md),
[M1](eval/fr011_m1_executable_preparation.md));
**FR-012** Submission Assistance (2026-07-31 —
[acceptance](eval/fr012_submission_assistance.md);
milestones [M0](eval/fr012_m0_submission_contracts.md),
[M1](eval/fr012_m1_submission_orchestration.md),
[M2](eval/fr012_m2_owner_workflow.md));
**FR-013** Application Pipeline Tracking (2026-08-05 —
[acceptance](eval/fr013_application_pipeline_tracking.md);
[ADR-005](adr/005_application_pipeline_lifecycle.md);
milestones [M0](eval/fr013_m0_engineering_spike.md)–[M4](eval/fr013_m4_reporting_acceptance.md));
**FR-014** Recruiter Document Truth Validation (2026-08-05 —
[acceptance](eval/fr014_recruiter_document_truth_validation.md);
[ADR-006](adr/006_recruiter_document_truth_validation.md);
milestones [M0](eval/fr014_m0_engineering_spike.md)–[M4](eval/fr014_m4_claim_validation.md));
**FR-015** Bounded Agentic Workflow (2026-08-05 —
[acceptance](eval/fr015_bounded_agentic_workflow.md);
[ADR-007](adr/007_bounded_agentic_workflow.md);
milestones [M0](eval/fr015_m0_engineering_spike.md)–[M4](eval/fr015_m4_evaluation.md));
**FR-016** Multi-Agent Orchestration (2026-08-06 —
[acceptance](eval/fr016_multi_agent_orchestration.md);
[ADR-008](adr/008_multi_agent_orchestration.md);
milestones [M0](eval/fr016_m0_engineering_spike.md)–[M4](eval/fr016_m4_evaluation.md));
**FR-017** Agent Evaluation & Observability (2026-08-07 —
[acceptance](eval/fr017_agent_evaluation_observability.md);
[ADR-009](adr/009_orchestration_evaluation_substrate.md);
milestones [M0](eval/fr017_m0_engineering_spike.md)–[M4](eval/fr017_m4_evaluation.md)).
**After usable 1A application loop:** Horizon 1B scaled acquisition and market
engagement (FR-018–FR-026) — **FR-018** first; **FR-019 Core Loop
Operationalisation** current; recruiter work **FR-020+** deferred — **not gated on
FR-017** (remap [11_changelog.md](11_changelog.md) § 1.115, § 1.128)  
**Principle:** Job acquisition first. Recruiter outreach second.  
**Later:** Horizon 2 capability phases (FR-027+; see roadmap)
