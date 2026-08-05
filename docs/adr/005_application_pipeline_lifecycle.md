# ADR-005: Application Pipeline Lifecycle (Stored Status + Append-Only Events)

**Status:** Accepted (FR-013 M1)  
**Date:** 2026-08-05  
**Amends:** [ADR-002](002_opportunity_persistence.md) (lifecycle audit discipline on
Opportunity)  
**Reaffirms:** [ADR-004](004_opportunity_review_boundary.md) (Opportunity remains the
single business system of record; review metadata stays orthogonal to pipeline)  
**Does not amend:** [ADR-003](003_application_workflow_orchestration.md) (checkpoints
remain recovery data; FR-008 runner does not absorb pipeline tracking)

**Spike:** [eval/fr013_m0_engineering_spike.md](../eval/fr013_m0_engineering_spike.md)
(Accepted)

---

## Context

FR-008–FR-012 deliver analysis through owner-assisted submission. Phase 2 M2 already
stores `PipelineStatus` and `OutcomeRecord` on Opportunity, but overwrites those
fields without an append-only transition history. FR-012 records
`SubmissionAttempt` audit under `data/submission_attempts/` and **must not** write
`PipelineStatus`.

Real applications have been submitted with CIC. The owner needs deterministic
lifecycle tracking — not learning, not automation, not a second business aggregate.

---

## Decision

1. **Opportunity remains the aggregate and current-state source of truth.**
   `Opportunity.status` (`PipelineStatus`) and `Opportunity.outcome`
   (`OutcomeRecord`) stay stored queryable fields for ranking, review eligibility,
   and recommendations.

2. **Append-only `PipelineEvent` records provide the audit trail.** Every
   owner-visible status advance, interview-stage change, outcome change, evidence
   addition, follow-up change, note, and correction appends an immutable event
   keyed by `opportunity_id`. Events are never mutated or deleted.

3. **Coarse status + separate interview stage.** Retain the existing
   `PipelineStatus` vocabulary. Do **not** create a mega-enum for recruiter
   contact, phone screen, technical, final, acknowledged, or archive. Interview
   granularity stays on `InterviewStage` (and events). Review archive remains
   FR-009 `archived_at`.

4. **SubmissionAttempt success does not automatically advance `Opportunity.status`.**
   FR-012 terminal success (`submitted` / `manual_completed`) is submission audit
   only. Pipeline advancement to `submitted` (or any later stage) is an **explicit
   owner action** in FR-013 that may *cite* a `submission_attempt_id` as evidence.
   No SubmissionAttempt store write, adapter callback, or orchestrator completion
   path may write `PipelineStatus`.

5. **Corrections are new events.** Mistaken transitions (including leaving a
   terminal status) are represented by appending a `correction` event with a
   required note (and optional `supersedes_event_id`). Prior events are retained.
   There is no in-place mutation of historical events and no delete API.

6. **Persistence.** Events live beside Opportunity under
   `data/pipeline_events/{opportunity_id}/` (audit store). They are not Opportunity
   SoT replacements and not workflow checkpoints.

7. **Service boundary (M2).** `PipelineTrackingService` is the sole coordinated
   writer that appends events and updates stored Opportunity status / outcome.
   M1 delivered contracts and the append-only event store only.

8. **Out of scope.** Adaptive scoring, FR-003/FR-004 redesign, dashboards, email,
   recruiter messaging, silent automation, and a separate Application aggregate.

---

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Opportunity field updates only (no event log) | No durable audit; corrections destroy history |
| New Application aggregate as lifecycle SoT | Second business SoT; package/submission already key by `opportunity_id`; premature 1:N |
| Package-owned lifecycle | Regeneration must not reset progress; package is a versioned artefact |
| Pure event sourcing (derive status only) | Ranking/review/recommendations already consume stored `Opportunity.status`; projection tax without payoff |
| Auto-advance status from FR-012 success | Violates FR-012 freeze and human-review / manual-first philosophy |

---

## Consequences

- FR-013 M1 freezes `PipelineEvent`, evidence rules, transition/correction policy,
  and append-only persistence in `career_intelligence.pipeline`.
- FR-012 remains unchanged: attempts never write `PipelineStatus`.
- **M2 write ordering (accepted):** validate → append `PipelineEvent` → project
  onto Opportunity via `OpportunityService.apply_pipeline_projection`. Event-only
  kinds (`note`, `evidence_added`) skip the Opportunity write.
- **Partial failure:** if the event is durable and Opportunity projection fails,
  raise `PipelinePartialWriteError` and recover with `apply_stored_event` /
  `reconcile` (idempotent). Never delete the event.
- **Divergence:** `detect_divergence` / `require_consistent` compare Opportunity
  fields to folded event history; `reconcile` re-projects.
- Feeding outcomes into FR-003 assessments remains a separate future FR.

---

## Guardrails

- Do not treat `SubmissionAttempt` or `ApplicationPackageManifest` as pipeline SoT.
- Do not delete or rewrite `PipelineEvent` records.
- Do not advance `Opportunity.status` from submission success without an explicit
  owner pipeline action.
- Do not collapse review archive, owner decision, and pipeline status into one enum.
