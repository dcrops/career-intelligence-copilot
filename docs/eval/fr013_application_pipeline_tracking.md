# FR-013 — Application Pipeline Tracking

**Status:** **Complete** — documentation frozen  
**Date:** 2026-08-05  
**Recommendation:** **FR-013 ACCEPTED**  
**Next:** Begin **FR-014** Recruiter Document Truth Validation  
([planning](fr014_recruiter_document_truth_validation.md))

**ADR:** [ADR-005](../adr/005_application_pipeline_lifecycle.md) (Accepted)

Milestone records:
[M0](fr013_m0_engineering_spike.md),
[M1](fr013_m1_pipeline_contracts.md),
[M2](fr013_m2_pipeline_tracking.md),
[M3](fr013_m3_owner_workflow.md),
[M4](fr013_m4_reporting_acceptance.md).

---

## 1. Executive Summary

FR-013 delivers **deterministic application lifecycle tracking** after package
generation and owner submission. Opportunity remains the aggregate and
current-state source of truth; append-only `PipelineEvent` records provide the
audit trail; `PipelineTrackingService` coordinates event-first dual-write; thin
`cic pipeline` is the owner interface; derived reporting and owner-controlled CSV
export close the operational loop — without silent submit, automation, adaptive
scoring, or a second business aggregate.

| Milestone | Delivered |
|-----------|-----------|
| M0 | Engineering spike (hybrid architecture accepted) |
| M1 | Contracts, transitions, evidence, append-only store, ADR-005 |
| M2 | `PipelineTrackingService` dual-write, divergence, repair |
| M3 | Owner CLI (`cic pipeline`) |
| M4 | Reporting, CSV continuity, acceptance freeze |
| Close-out | Owner manual validation confirmed; documentation freeze |

**Final decision:** **FR-013 ACCEPTED and FROZEN.** Proceed to FR-014. Do not
reopen FR-013 exit criteria without explicit owner request.

---

## 2. Business Problem

After real applications are submitted, the owner still needs:

1. A single authoritative **current stage** per applied opportunity.
2. An **auditable history** of how that stage changed (when / why / evidence).
3. Continuity with existing ranking, review eligibility, and recommendations that
   already interpret `PipelineStatus`.
4. Continuity with `applications/` tracker semantics without a competing pipeline
   database.
5. Visibility into follow-ups, ageing, and cohort rates for daily job-search effort.

Phase 2 M2 outcome logging could overwrite status but left no append-only
transition history. FR-010–FR-012 deliberately do not advance pipeline status.
Without FR-013, dogfooding produced live statuses with no durable audit and no
owner-facing lifecycle workflow after submit.

---

## 3. Engineering Problem

| Constraint | Requirement |
|------------|-------------|
| SoT | Opportunity remains the business aggregate (`opp_<ULID>`) |
| Audit | Immutable transition / correction / evidence history |
| Compatibility | Ranking, review, recommendations keep reading stored `Opportunity.status` |
| Separation | FR-012 `SubmissionAttempt` success must never auto-advance status |
| Corrections | Honest repairs without mutating or deleting history |
| Continuity | CSV export for operational use; no mandatory legacy migration |
| Scope | No adaptive scoring, dashboards, email, recruiter messaging, or silent automation |

---

## 4. Final Architecture

```
Owner
  → cic pipeline (thin CLI)
  → PipelineTrackingService
       → validate transition / evidence
       → append PipelineEvent (data/pipeline_events/{opportunity_id}/)
       → project Opportunity.status / outcome  (event-first dual-write)
  → derived PipelineSummaryReport / due / pipeline.csv export
```

| Concern | Owner |
|---------|--------|
| Business identity | Opportunity |
| Current pipeline stage (queryable) | Stored `Opportunity.status` (`PipelineStatus`) |
| Terminal / summary result | Stored `Opportunity.outcome` (`OutcomeRecord`) |
| Interview granularity | Separate `InterviewStage` (not a mega-enum) |
| Audit of advances / corrections / evidence | Append-only `PipelineEvent` (`ple_<ULID>`) |
| Submission mechanics audit | `SubmissionAttempt` (FR-012) — cite only |
| Package artefacts | Application package manifest (FR-010) — never owns lifecycle |

**Write ordering:** validate → append event → project Opportunity.  
**Partial failure:** event durable + Opportunity fail → `PipelinePartialWriteError`;
recover via `apply_stored_event` / `reconcile` (never delete the event).  
**Consistency:** `detect_divergence` / `check` / `repair` compare folded history to
stored Opportunity fields. No projection watermark.

---

## 5. Lifecycle Model

**Coarse status** (`PipelineStatus`) remains the operational stage vocabulary
(assessed → preparing → submitted → … → terminal outcomes).  
**Interview stage** is orthogonal granularity under `interviewing`.

| Kind | Role |
|------|------|
| `status_transition` | Owner-visible coarse status advance |
| `interview_stage_change` | Recruiter / technical / other interview progress |
| `outcome_change` | Outcome summary fields |
| `evidence_added` | Package / attempt / channel / note evidence (may skip Opportunity write) |
| `follow_up_set` | Reminder date |
| `note` | Free-form note (may skip Opportunity write) |
| `correction` | New event that supersedes a mistaken prior transition; history retained |

Corrections are **new events only**. Terminal states are repairable via correction,
not by mutating prior records.

---

## 6. ADR-005 Summary

[ADR-005](../adr/005_application_pipeline_lifecycle.md) records:

1. Opportunity = aggregate + stored current-state SoT.
2. Append-only PipelineEvents = audit trail.
3. Coarse status + separate InterviewStage — no mega-enum.
4. SubmissionAttempt success never automatically advances `Opportunity.status`.
5. Corrections = new events only.
6. Events persist under `data/pipeline_events/` (not Opportunity SoT, not checkpoints).
7. `PipelineTrackingService` is the coordinated writer.
8. Out of scope: adaptive scoring, dashboards, silent automation, separate Application aggregate.

Amends ADR-002 (lifecycle audit discipline). Reaffirms ADR-004. Does not amend ADR-003.

---

## 7. Major Design Decisions

| Decision | Rationale |
|----------|-----------|
| Hybrid SoT (stored status + events) | Ranking/review already consume stored status; events supply audit without pure event-sourcing tax |
| Event-first dual-write | Audit exists before projection; partial failure is recoverable |
| Explicit owner pipeline advance after FR-012 | Preserves human-review / never-silent-submit invariants |
| Thin CLI over service | Matches FR-010/011/012; CLI presents, service decides |
| Divergence + repair (no watermark) | Sufficient consistency without coupling projection cursor to every reader |
| Derived reporting only | No second reporting schema; export is owner-controlled |
| Legacy `update_outcome` left writable | Avoid breaking Phase 2 M2; owner path is `cic pipeline` (accepted debt) |

---

## 8. Alternatives Rejected

| Alternative | Why rejected |
|-------------|--------------|
| Opportunity field updates only (no event log) | No durable audit; corrections destroy history |
| New Application aggregate as lifecycle SoT | Second business SoT; premature 1:N; package/submission already key by opportunity |
| Package-owned lifecycle | Regeneration must not reset progress |
| Pure event sourcing (derive status only) | Projection tax; ranking/review already use stored status |
| Auto-advance status from FR-012 success | Violates FR-012 freeze and human-review philosophy |
| Projection watermark (`last_projected_event_id`) | Divergence/repair suffice; watermark adds coupling without payoff |
| Mega-enum for every interview/contact nuance | Over-models; InterviewStage + notes cover granularity |

---

## 9. Manual Validation Summary

| Harness | Result |
|---------|--------|
| `scripts/run_fr013_pipeline_manual.py demo` | **PASS** (M2) |
| `scripts/run_fr013_pipeline_manual.py journey` | **PASS** (M3) |
| `scripts/run_fr013_pipeline_manual.py accept` | **PASS** (M4 multi-opportunity) |

Owner close-out validation additionally confirmed:

| Observation | Classification |
|-------------|----------------|
| Legacy opportunities show stored `status` / `interview_stage` with empty `cic pipeline history` | **Expected** — pre-FR-013 / `update_outcome` path; not a projection defect |
| New FR-013-managed opportunities create append-only PipelineEvents | **Pass** |
| Projection updates Opportunity current state correctly | **Pass** |
| `check` / divergence validates history against projected state | **Pass** |
| Owner workflow verbs behave naturally | **Pass** |
| ADR-005 invariants hold | **Pass** |

---

## 10. Testing Summary

| Suite | Result |
|-------|--------|
| `tests/unit/pipeline/` | Pass |
| Functional `tests/functional/test_fr013_*.py` | Pass |
| Combined FR-013 focused | **82 passed** |
| Manual accept harness | **PASS** |

Coverage areas: models/store, transitions/evidence, event-first dual-write, partial
failure recovery, divergence/reconcile, owner CLI, reporting/due/export.  
Does **not** cover: FR-012 auto-advance (forbidden), dashboards, adaptive scoring.

---

## 11. Risks Considered

| Risk | Mitigation |
|------|------------|
| Dual-write partial failure | Event-first; `PipelinePartialWriteError`; idempotent repair |
| Silent status advance from submission | ADR-005 forbidden; no FR-012 bridge |
| Legacy status without events | Documented expected behaviour; `history` empty; `show` still reads Opportunity |
| Competing CSV trackers | Export only; no two-way sync; structured store remains SoT |
| Over-modelling interview nuance | Coarse status + InterviewStage + notes |
| Premature Application aggregate | Rejected at M0 |

---

## 12. Technical Debt Classification

| Item | Classification | Justification |
|------|----------------|---------------|
| `OpportunityService.update_outcome` still writable without events | **Accepted** | Phase 2 M2 continuity; owner path is `cic pipeline`. Empty history with non-assessed status is expected for that path |
| Duplicate ULID helpers across packages | **Accepted** | Avoids cross-package coupling; established pattern |
| No two-way sync with `applications/application_tracker.csv` | **Accepted** | Export-only continuity; no migration required for exit |
| Interview `final` not a dedicated stage enum | **Accepted** | Use `--stage other --note final`; avoids mega-enum |
| Backfill of synthetic PipelineEvents for legacy rows | **Deferred** | Out of FR-013 exit; optional future hygiene if owner requests |
| Deprecate / gate silent `update_outcome` for pipeline statuses | **Future FR** | Would harden writer discipline; not required for FR-013 acceptance |
| Adaptive scoring / outcome → FR-003 feedback | **Out of scope** | Explicitly deferred; Horizon 2 / separate FR |
| Dashboards, email, recruiter messaging | **Out of scope** | Not job-acquisition tracking |
| Projection watermark | **Out of scope** | Explicitly rejected |

None of the above block FR-013 exit.

---

## 13. Lessons Learned

1. **Spike → contracts → service → CLI → reporting → freeze** remains the right cadence.
2. **Hybrid SoT** (stored current state + append-only audit) beat pure event sourcing
   for systems that already query stored status.
3. **Submission audit ≠ pipeline lifecycle** — keeping FR-012 and FR-013 separate
   preserved human-review invariants.
4. **Event-first dual-write + repair** is enough consistency without watermarks.
5. **Legacy dual writers must be named** — empty history with live status is expected
   debt, not a silent bug, once classified.
6. **Thin CLI over a single service** continues to scale (FR-010 → FR-013).
7. **Documentation-first ADRs** (M0 spike → ADR-005 at M1) prevented mid-FR redesign.

---

## 14. Operational Readiness

| Capability | Ready |
|------------|-------|
| Record preparing / submitted / acknowledged / interview / reject / offer / accept / withdraw | Yes |
| Notes, evidence, follow-ups, corrections | Yes |
| History, check, repair | Yes |
| Report, due, export | Yes |
| Owner CLI discoverability (`cic pipeline --help`) | Yes |
| Manual harness for regression | Yes |
| Live FR-013 path for new advances | Yes |
| Legacy pre-FR-013 rows | Readable via Opportunity; history empty until new events |

**Documented owner workflow (post–FR-013):**

```
Opportunity
  → Assessment
  → Strategy
  → Application Package
  → Owner Review
  → Render
  → Manual Submission
  → Pipeline Tracking
  → Reporting
  → Operational History
```

---

## 15. Engineering Retrospective

### What worked well

- M0 architecture spike before code locked the hybrid SoT early.
- ADR-005 invariants held through M2–M4 without reopen.
- Thin CLI + service boundary matched prior FRs and stayed owner-natural.
- Focused FR-013 test pack (82) gave fast regression without suite sprawl.

### What surprised us

- Live store already had interviewing rows from Phase 2 M2 with zero events —
  validating that “empty history + non-empty status” is a real operational state,
  not a theoretical edge case.
- Projection watermark looked attractive early and proved unnecessary once
  divergence/repair existed.

### Architectural decisions that proved valuable

- Opportunity remains SoT; events are audit.
- SubmissionAttempt never auto-advances status.
- Corrections as new events.
- Derived reporting from existing fields (no parallel reporting model).

### Repeat for future FRs

- Spike → ADR → contracts → behaviour → thin owner interface → freeze.
- Name dual-writer / legacy paths explicitly in acceptance debt tables.
- Prefer repair/reconcile over watermark cursors unless readers demand them.

### What should change for FR-014

- Treat FR-014 as a **fail-closed trust boundary**, not another lifecycle writer.
- Reuse the thin-CLI / service / deterministic-first pattern.
- Do not absorb pipeline tracking, submission, or package rules into truth validation.
- Plan insertion points carefully (pre-Markdown vs package/submission gate) via spike
  before implementation — same discipline as FR-013 M0.

---

## 16. Definition of Done

| Criterion | Status |
|-----------|--------|
| Architecture accepted | ✓ |
| Contracts complete | ✓ |
| Service complete | ✓ |
| CLI complete | ✓ |
| Reporting complete | ✓ |
| Manual validation complete | ✓ |
| Tests complete | ✓ |
| Documentation complete | ✓ |
| Operationally ready | ✓ |
| Close-out / freeze | ✓ |

---

## 17. Final Acceptance Decision

**FR-013 ACCEPTED and FROZEN.**

Repository status after close-out:

- FR-013 = **Complete**
- Documentation = **Frozen**
- Next active FR = **FR-014** Recruiter Document Truth Validation

Do not reopen FR-013 exit criteria without explicit owner request.
Do not begin FR-014 implementation from this close-out alone — wait for an explicit
owner start request for FR-014 work.
