# ADR-004: Opportunity as Pre-Decision System of Record; Review Queue as Derived Projection

**Status:** Accepted (FR-009 M0) — **implemented in FR-009 M1** (2026-07-30;
[acceptance](../eval/fr009_m1_persistence_boundary.md))  
**Date:** 2026-07-29  
**Amends:** [ADR-002](002_opportunity_persistence.md) (persistence boundary and record meaning)  
**Reaffirms:** [ADR-003](003_application_workflow_orchestration.md) (checkpoints are recovery data)

## Context

FR-008 delivered a deterministic workflow that persists an Opportunity **only after
the owner chooses `apply`** (`routing.APPLY_SIDE_EFFECT_SEQUENCE`;
`PersistOpportunityNode` fails closed unless `approval.owner_decision == "apply"`).
Skip and defer complete with no durable record.

FR-009 must let the owner compare and prioritise many analysed jobs. That is
impossible if the only durable records are jobs already chosen for application:

- A skipped or deferred job leaves no auditable trace, so the same advert can be
  re-analysed and re-decided indefinitely.
- Duplicate detection has nothing to match against for jobs that were never applied to.
- The review queue would have to read workflow checkpoints, which ADR-003 defines as
  runtime recovery state, not a business catalogue.

The Opportunity **contract** never required an owner decision. ADR-002 describes the
aggregate as "produced by `OpportunityService` after Application Strategy";
`create_from_strategy` creates records with `decision=None` and `status="assessed"`;
M4 ranking already explains records where "Owner has not yet recorded
apply/skip/defer". The live store confirms it: **13 of 16 records have no owner
decision**. Apply-only was an FR-008 *routing* restriction, never a persistence
constraint.

## Decision

1. **Meaning.** An Opportunity is the durable record of a *successfully analysed job
   candidate that may require an owner decision* — not a job the owner has decided to
   apply for.
2. **Boundary.** The intended persistence point is after successful FR-005 Application
   Strategy and **before** owner review. Apply, skip, and defer then update that same
   record. FR-009 M1 moves the workflow node; M0 fixes the contract only.
3. **Single source of truth.** `data/opportunities/` (ADR-002) remains the business
   system of record. The FR-009 review queue is a **derived projection / query service**
   over persisted Opportunities. No second persisted queue aggregate.
4. **Derived rank.** Queue position, priority band, age, staleness, and duplicate
   grouping are computed from persisted fields. Rank position is not persisted.
5. **Checkpoints stay recovery data.** No list/query/catalogue features are added to
   `CheckpointStore` to serve FR-009.
6. **Orthogonal review metadata.** Owner review metadata is persisted as independent
   fields (`OpportunityReview`: `reviewed_at`, `pinned`, `defer_until`, `archived_at`),
   not as one lifecycle enum, and stays separate from `OwnerDecisionRecord`,
   `PipelineStatus`, workflow status, and duplicate state.
7. **Duplicates are non-destructive.** A confirmed duplicate is recorded as
   `DuplicateRelation(duplicate_of, confirmed_at, evidence)` on the duplicate record.
   Nothing is merged or deleted; both records stay auditable. A shared
   `content_fingerprint` alone is not proof — the live store already contains three
   fingerprint collision groups.
8. **M4 ranking is the frozen fit baseline.** FR-009 may add eligibility filtering and
   explicit owner overrides *around* the `pursuit_posture → fit strength →
   application_tier → opportunity_id` sort key. No composite score, no LLM ranking.
9. **Archive is review visibility only.** Archiving hides a record from active review.
   Employer rejection, withdrawal, and process completion remain FR-012 pipeline
   concepts.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Keep apply-only persistence; build the queue from workflow checkpoints | Turns recovery state into a business database (contradicts ADR-003); checkpoints are per-run, deletable, and not keyed by job identity |
| Add a separate "seen jobs" store for skip/defer | A second source of truth for the same entity; duplicate identity, provenance, and ranking logic; divergence risk |
| Persist a separate `ReviewQueueItem` aggregate | Queue content is fully derivable; a persisted queue must then be invalidated and reconciled on every Opportunity change |
| Single `review_state` lifecycle enum (`awaiting_review`, `reviewed`, `deferred`, `closed`, `archived`) | Independent concerns collapse into mutually exclusive states (a reviewed *and* pinned *and* deferred record needs a new state each time); overlaps `PipelineStatus`; transition table grows combinatorially |
| Hybrid: small enum plus metadata | Retains two representations of the same facts and the risk that they disagree; derived labels give the same reporting benefit for free |
| Treat `content_fingerprint` as a unique key | Live collisions prove near-identical bodies recur legitimately; a unique key would block valid records and hide reposts |

## Consequences

- FR-009 can rank, filter, and deduplicate over one durable store without new
  infrastructure, a database, or a framework.
- Skip and defer become auditable, which changes the workflow's meaning: completing a
  run without applying still produces a record. FR-009 M1 must prove this does not
  create duplicate Opportunities on resume or replay.
- Idempotency moves earlier. Today `opportunity_id` is pre-allocated and checkpointed
  after approval; M1 must pre-allocate before `owner_review`, so the interrupt window
  sits *between* create and decision update. Required behaviour per crash window:

  | Window | Situation | Required behaviour |
  |--------|-----------|--------------------|
  | A | Persist fails before owner review | Terminal/recoverable failure with no Opportunity and no approval request; retry reuses the checkpointed planned id |
  | B | Opportunity created, crash before checkpoint | Resume reclaims the same id via `create_from_strategy(opportunity_id=…)`; no second record |
  | C | Checkpoint written, owner review interrupted | Record remains `decision=None` and is visible in the review queue as awaiting decision |
  | D | Decision received, update fails | Run stays resumable; `record_decision` re-applies the same decision idempotently (conflicting decision fails closed) |
  | E | Decision stored, crash before completion | Resume observes the decision already present and completes without rewriting it |

- Records written under apply-only semantics remain valid without migration: the new
  fields are additive with deterministic defaults, and a missing key reads as
  "never reviewed, not a duplicate".
- Writing any record rewrites the whole index file, so default review keys will appear
  on existing rows the next time a decision or outcome is saved. This changes
  serialisation only, never meaning.

## Implementation status (FR-009 M1 + M2 + M3)

Decisions 1–9 are implemented for the workflow, the default projection, and owner review
actions. `persist` moved into `PRE_APPROVAL_SEQUENCE`; all three decisions run
`POST_DECISION_SEQUENCE`; `career_intelligence.review_queue.ReviewQueueService` provides
the derived projection with pinned-first presentation override.
`OpportunityReviewService` writes orthogonal review metadata and append-only
`review_actions` audit evidence. Crash windows A–E behave as required, with one
refinement to window A: a persistence failure leaves the run **resumable** (status
`running`, error recorded, planned id kept) rather than terminally failed, matching the
FR-008 M2 treatment of side-effect nodes so a transient store outage cannot discard
completed FR-002–FR-005 analysis. The invariant the window protects is unchanged — no
Opportunity, no approval request.

**M3 implements decision 7 (duplicates are non-destructive).** Detection is derived and
advisory in `career_intelligence.duplicates`; owner-confirmed outcomes are written by
`opportunities.DuplicateReviewService`. Confirmed groups are star-shaped — the canonical
record holds no relation and members carry `DuplicateRelation(duplicate_of, …)` — so a
group is derived by one scan with no persisted group aggregate, and chains are rejected.
Rejections are persisted symmetrically in the additive `duplicate_rejections` field, which
is what stops a declined suggestion returning. Canonical selection is recommended
deterministically and applied only on explicit owner confirmation; `confirm_canonical` is
convergent, so an interrupted re-point is repaired by replaying the same action.

Ranking calibration (M4) remains deferred.

## Compatibility implications

- No schema version bump: `Opportunity` gains optional fields only, and the index
  loader ignores `schema_version`. A version bump would imply a migration that does
  not exist.
- No live data mutation in M0. M3 added no migration either: `duplicate_rejections`
  defaults to empty, so pre-M3 rows read unchanged.
- Public API is additive (`OpportunityReview`, `DuplicateRelation`,
  `DuplicateEvidenceKind`, `DUPLICATE_EVIDENCE_KINDS`, and in M3 `DuplicateRejection`,
  `DuplicateReviewService`, plus the `career_intelligence.duplicates` package). No
  renames, no removals.
- CSV export (M3) is unaffected: `EXPORT_COLUMNS` is explicit, so new fields do not
  leak into the operational bridge until deliberately added.

## Deferred work

- FR-009 M4 — manual validation and ranking calibration.
- Employer-careers `SourceKind` value, so canonical selection can prefer an official
  employer advertisement directly instead of approximating it as "not a recruiter repost".
- FR-012 — application pipeline status and outcome semantics; `PipelineStatus`
  remains outside FR-009's write surface.

## Guardrails

- FR-009 must not write `PipelineStatus`, mutate FR-002–FR-005 artefact snapshots, or
  change the M4 sort key.
- Do not add query or listing features to the workflow checkpoint store.
- Do not merge or delete records during duplicate handling.
- Do not persist derived queue values (rank, band, age, staleness).
