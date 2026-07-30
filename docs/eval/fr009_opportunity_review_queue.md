# FR-009 — Opportunity Review Queue & Ranking

**Status:** **Complete** — documentation frozen  
**Date:** 2026-07-30  
**ADR:** [ADR-004](../adr/004_opportunity_review_boundary.md) (Accepted; Decision 8
amended by M4 calibration)  
**Recommendation:** **GO** (engineering close-out)

Milestone acceptance records: [M0](fr009_m0_domain_contracts.md),
[M1](fr009_m1_persistence_boundary.md), [M2](fr009_m2_owner_review_actions.md),
[M3](fr009_m3_duplicate_detection.md), [M4](fr009_m4_recommendations.md).

## Objectives

Let the owner answer "which opportunity deserves attention next?" over many acquired
jobs — with a durable record for every analysed job, reversible owner review controls,
non-destructive duplicate handling, and a deterministic explainable ordering. Without
persisted queue state, opaque scoring, LLM ranking, application-pipeline semantics, or
a user interface.

## Implementation summary

| Milestone | Delivered |
|-----------|-----------|
| M0 | Domain and policy contracts; `OpportunityReview`, `DuplicateRelation`; persisted-vs-derived classification; ADR-004 |
| M1 | Persistence moved before the owner-review interrupt; apply/skip/defer update the same record; read-only `ReviewQueueService` projection |
| M2 | Reversible owner actions (mark reviewed, pin/unpin, defer until/clear defer, archive/reopen) with append-only `review_actions` audit evidence |
| M3 | Deterministic multi-evidence duplicate detection, owner confirmation/rejection, derived star-shaped groups, advisory canonical selection |
| M4 | Quality-first ranking calibration and derived explainable recommendations (bands, urgency, next action) |
| Close-out | Documentation freeze; FR-009 marked complete; FR-010 becomes the active FR |

Packages: `career_intelligence.review_queue`, `career_intelligence.duplicates`,
`career_intelligence.recommendations`, plus additive contracts and services in
`career_intelligence.opportunities` and calibration in
`career_intelligence.opportunity_comparison`.

## Delivered capability

| Capability | Behaviour |
|------------|-----------|
| Pre-review persistence | Every successfully strategised job becomes a durable Opportunity **before** owner review, so skip and defer stay auditable |
| Derived review queue | `list_awaiting_review` / `list_active_opportunities` computed on every call; eligibility, rank position, and exclusion reasons are never stored |
| Owner review actions | Mark reviewed, pin/unpin, defer until/clear defer, archive/reopen — each reversible, idempotent on harmless repeats, and audited |
| Duplicate detection | Read-only, deterministic, multi-evidence candidates with `definite` / `probable` / `possible` confidence and matching/differing/unknown facets |
| Duplicate resolution | Owner confirms, rejects (symmetrically, so a declined pair never returns), or leaves unresolved; records are **linked, never merged or deleted** |
| Canonical selection | Deterministic recommendation, applied only on explicit owner confirmation |
| Duplicate exclusion | A confirmed member leaves the queue with reason `confirmed_duplicate`; the canonical stays and carries `duplicate_group_size` |
| Deterministic recommendations | `OpportunityRecommendationService` returns a stable prioritised report for the same inputs |
| Calibrated quality-first ranking | Sort key optimises opportunity quality and owner value, not application effort |
| Recommendation explanations | `ranking_reasons` plus structured `positives` / `negatives` / `missing` / `trade_offs` |
| Priority bands | Coarse `immediate` / `high` / `standard` / `low` labels derived from posture, practical value, and fit — not a second sort key |
| Urgency generation | `due` / `upcoming` from `outcome.follow_up_date`; `process` for interviewing/offer; otherwise `none` |
| Next-action generation | Deterministic next step from owner decision, review metadata, and pipeline status |
| Pin override | Pinned records appear first with the explicit reason `"Pinned by owner"`; underlying fit signals and reasons are unchanged |
| Read-only recommendation flow | Recommendation and detection queries write nothing — no decisions, review metadata, artefacts, or index rows |
| Derived, not persisted | Rank position, priority band, urgency, duplicate confidence, and duplicate groups are all computed |

## Calibrated ranking policy

```
pursuit_posture → fit_strength → practical_value → opportunity_id
```

- `application_tier` provides **effort context only** — it is shown on ranked items and in
  explanations, and cannot displace a higher-value role.
- **Missing evidence cannot improve ranking:** a fit judgment of `unknown` contributes 0.
- **Unavailable data is never invented:** closing dates do not exist in the product, and
  salary / location / work model live on FR-002 artefacts rather than the Opportunity
  index, so none of them are ranking inputs or urgency sources.
- Presentation order is `eligible → pinned first → calibrated key`.
- No composite score and no LLM ranking.

## Architecture

- **System of record:** `data/opportunities/` (ADR-004). The review queue, duplicate
  groups, and recommendations are derived projections over it.
- **Checkpoints:** `data/workflow_runs/` remains recovery infrastructure; no listing or
  catalogue features were added.
- **Read/write separation:** `ReviewQueueService`, `DuplicateDetectionService`, and
  `OpportunityRecommendationService` are read-only; `OpportunityReviewService` and
  `DuplicateReviewService` own writes.
- **Composition:** `OpportunityRecommendationService` composes `ReviewQueueService`, so
  eligibility, exclusion reasons, and pin override stay single-sourced.
- **Concern separation:** owner decision, review metadata, `PipelineStatus`, workflow
  status, and duplicate state remain distinct fields. FR-009 never writes
  `PipelineStatus` and never mutates FR-002–FR-005 artefact snapshots.
- **ADR:** no new ADR — ADR-004 Decision 8 was amended to record the M4 calibration under
  explicit owner authorisation.

### Delivered workflow

```
Acquire → Validate → Analyse → Assess → Match → Strategy
   → allocate opportunity_id → checkpoint → Persist (decision = None)
   → Owner Review (interrupt)
   → Apply | Skip | Defer → Record Decision on the same Opportunity → Complete
```

## Validation evidence

| Layer | Evidence |
|-------|----------|
| Unit testing | `tests/unit/opportunities/` (contracts, review actions, duplicate actions), `tests/unit/review_queue/`, `tests/unit/duplicates/`, `tests/unit/recommendations/`, `tests/unit/opportunity_comparison/`, `tests/unit/orchestration/test_m1_pre_review_persistence.py` |
| Functional testing | `tests/functional/test_fr009_review_queue.py`, `test_fr009_owner_review_actions.py`, `test_fr009_duplicate_review.py`, `test_fr009_recommendations.py` |
| Manual validation | `scripts/run_fr009_review_queue_manual.py`, `run_fr009_owner_review_manual.py`, `run_fr009_duplicate_review_manual.py`, `run_fr009_recommendations_manual.py` |
| Full suite at freeze | `python -m pytest -q` → **1019 passed** |

Verified behaviours at close-out:

| Check | Result |
|-------|--------|
| Deterministic ordering and stable tie-breaking | ✓ |
| Reload / replay idempotency (fresh service, same report) | ✓ |
| Duplicate handling — link never merge; rejected pairs never return; confirmed member excluded, canonical retained | ✓ |
| Pin ordering raises a record without altering fit strength or fit reasons | ✓ |
| Recommendation explanations match the ordering, and report `missing` rather than inventing values | ✓ |
| Exactly one Opportunity across resume, replay, and lost-checkpoint runs | ✓ |
| Live `data/opportunities/` queries are read-only | ✓ |
| Owner review actions preserve decision, status, outcome, artefacts, provenance, and duplicate state | ✓ |

Manual validation outcome: **PASS** (details per milestone report; M4:
[fr009_m4_recommendations.md](fr009_m4_recommendations.md)). One data limitation was
recorded rather than treated as a defect: most live rows predate grounded identity, so
recommendations show `missing` company/title until `cic opportunity backfill-identity`
is run.

## Definition of Done

| Criterion | Status |
|-----------|--------|
| Functional implementation complete (M0–M4) | ✓ |
| Unit tests passing | ✓ |
| Functional tests passing | ✓ |
| Manual validation completed | ✓ (PASS) |
| Acceptance report completed | ✓ (per-milestone + this FR record) |
| Engineering notes updated | ✓ [08_implementation_notes.md](../08_implementation_notes.md) |
| Changelog updated | ✓ [11_changelog.md](../11_changelog.md) |
| Roadmap updated | ✓ [10_roadmap.md](../10_roadmap.md) |
| Documentation consistent | ✓ spec, domain model, testing strategy, guide, ADR index |
| Owner review complete | ✓ M4 owner reviewed and approved |

## Limitations (by design)

- No user interface or CLI review-queue command; manual scripts cover validation.
- No application-pipeline semantics — submitted / interviewing / rejected / withdrawn
  remain FR-012.
- No document package generation (FR-010) or submission (FR-011).
- Salary, location, work model, and closing-date signals are not ranking inputs.
- Whole-index YAML rewrite means concurrent writers are last-writer-wins; services
  reload immediately before applying an action.
- Duplicate groups are one hop deep by design; chains are rejected.

## Deferred work

| Deferred | Rationale |
|----------|-----------|
| Identity backfill on the live store | Operational task; `cic opportunity backfill-identity` exists |
| Employer-careers `SourceKind` | Canonical selection currently approximates it as "not a recruiter repost" |
| Career Profile preference matching (location / compensation / work model) | Requires artefact joins and an explicit preference policy |
| Closing-date urgency | Only if acquisition or analysis gains a real closing-date field; never faked |
| `cic opportunity recommend` CLI | Convenience only |
| Multi-user concurrency control | Out of scope in the single-user phase |

## Lessons learned

1. Persist before the human interrupt — a review product needs a record for the jobs the
   owner rejects, not only the ones they pursue.
2. Pre-allocated identity plus idempotent create closes crash windows without a second
   source of truth.
3. Derived projections avoid stale duplicated state: rank, band, urgency, and duplicate
   groups all recompute correctly after any review action.
4. Orthogonal review fields beat a lifecycle enum when concerns are genuinely
   independent — no transition table and no migration.
5. Link, never merge: a false merge hides a real vacancy permanently, a visible duplicate
   costs one glance.
6. Explicit reference dates make date-sensitive policy testable; domain code should not
   read the clock.
7. Keep presentation override (pin) visibly separate from fit so calibration stays
   honest.
8. Calibration is an owner decision recorded in an ADR amendment — not a quiet weight
   change.

## GO / NO-GO assessment

| Area | Result | Notes |
|------|--------|-------|
| Implementation | **PASS** | M0–M4 delivered; boundaries intact |
| Determinism | **PASS** | Stable ordering and stable explanations for the same inputs |
| Explainability | **PASS** | Ranking reasons plus structured recommendation explanation |
| Derived state | **PASS** | No persisted rank, band, urgency, or group aggregate |
| Owner control | **PASS** | Detection and recommendation advise; the owner decides |
| Testing | **PASS** | 1019 passed at freeze |
| Manual validation | **PASS** | Milestone scripts; one data limitation recorded |
| Documentation | **PASS** | Spec, roadmap, changelog, notes, testing strategy, ADR-004 |
| Backward compatibility | **PASS** | Additive fields; no migration; no live data mutation |
| Architecture | **PASS** | ADR-004 implemented; Decision 8 amended for calibration |

### Recommendation

**GO** — FR-009 is complete and frozen.

Next active functional requirement: **FR-010 Application Package Preparation**. Do not
reopen FR-009 scope (persistence boundary, queue projection, duplicate policy, or the
calibrated sort key) without explicit owner request.
