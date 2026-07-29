# FR-009 M0 Acceptance Report — Opportunity Persistence Boundary & Domain Contracts

**Milestone:** FR-009 M0 (of M0–M4 + close-out)  
**Status:** Complete — **FR-009 is not complete**  
**Date:** 2026-07-29  
**Architecture:** [ADR-004](../adr/004_opportunity_review_boundary.md) (Accepted)  
**Scope:** domain contracts, policy specification, backward compatibility, M1 integration
contract. No review queue, ranking extension, owner actions, or duplicate detection.

---

## 1. Problem resolved

FR-008 persists an Opportunity **only after the owner chooses `apply`**
(`orchestration/routing.py` → `APPLY_SIDE_EFFECT_SEQUENCE`;
`PersistOpportunityNode.execute` refuses to run unless
`state.approval.owner_decision == "apply"`). Skip and defer complete with no durable
record.

FR-009 needs the opposite: a durable record for every successfully analysed job so the
owner can compare candidates, remember what was skipped or deferred, and detect
duplicates. Building that on FR-008's boundary would have required either reading
workflow checkpoints (recovery state — forbidden by ADR-003) or inventing a second
"seen jobs" store (a second source of truth for the same entity).

**Resolution:** the Opportunity record becomes durable *before* the owner decision, and
the review queue becomes a derived projection over it. Nothing else gains a source of
truth.

## 2. Decision

An **Opportunity** is the durable record of a *successfully analysed job candidate that
may require an owner decision*. Persistence belongs after FR-005 Application Strategy
and before owner review. Apply, skip, and defer update that same record. The review
queue is derived, never persisted. Full decision text and alternatives:
[ADR-004](../adr/004_opportunity_review_boundary.md).

## 3. Repository evidence

| Evidence | Source | What it shows |
|----------|--------|---------------|
| "produced by `OpportunityService` after Application Strategy" | [ADR-002](../adr/002_opportunity_persistence.md), [06_domain_model.md](../06_domain_model.md) | The broadened meaning restores ADR-002's original intent; apply-only was never the contract |
| `create_from_strategy` creates `decision=None`, `status="assessed"` | `opportunities/service.py` | Pre-decision creation already valid; no contract change needed to allow it |
| **13 of 16 live records have `decision: null`** | `data/opportunities/index.yaml` | Pre-decision Opportunities already exist and load today |
| "Owner has not yet recorded apply/skip/defer" ranking reason | `opportunity_comparison/ranking.py` | M4 ranking already anticipated decision-free records |
| `is_open_opportunity` excludes `decision == "skip"` | `opportunity_comparison/ranking.py` | Owner decision 5 semantics (skip preserved, excluded from active review) already partly encoded |
| Persist node gated on `apply`; skip/defer complete with no record | `orchestration/side_effect_nodes.py`, `tests/functional/test_fr008_checkpoint_resume.py` | Confirms the restriction is workflow routing, not persistence |
| Pre-allocated id + reclaim on resume | `side_effect_nodes.py`, ADR-003 evidence §4 | The idempotency mechanism M1 must move earlier already exists |
| 0/16 records carry `platform_job_id` / `canonical_url` / `source_url`; 16/16 carry `content_fingerprint`; **3 fingerprint collision groups** (2+2+3) | `data/opportunities/index.yaml` | Exact URL/ID evidence is unavailable on today's paste/export path; fingerprint alone cannot prove duplication |
| `CheckpointStore` has no list/query surface | `orchestration/store.py`, ADR-003 guardrails | Checkpoints cannot serve as the catalogue, confirming owner decision 4 |
| `PipelineStatus` already contains `deferred` | `opportunities/models.py`, `transitions.py` | Defer could be expressed three ways; M0 had to choose one (see §6) |

**No material contradiction with the owner decisions was found.** The single tension
requiring an explicit ruling is the three-way overlap on "defer" (§6).

## 4. Contracts delivered

Additive, in `career_intelligence.opportunities`:

```
OpportunityReview        reviewed_at: datetime | None = None
                         pinned: bool = False
                         defer_until: date | None = None
                         archived_at: datetime | None = None
                         invariant: archived records are not pinned

DuplicateRelation        duplicate_of: OpportunityId        (canonical record)
                         confirmed_at: datetime
                         evidence: tuple[DuplicateEvidenceKind, ...] = ()

DuplicateEvidenceKind    platform_job_id | canonical_url | identity_facets
                         | content_fingerprint | owner_judgment

Opportunity              + review: OpportunityReview = OpportunityReview()
                         + duplicate: DuplicateRelation | None = None
                         invariant: duplicate_of must not be the record's own id
```

`defer_until` is a `date` (matching `OutcomeRecord.follow_up_date`) so "currently
deferred" is decidable without timezone arithmetic.

### Invariants established

| # | Invariant | Where enforced / recorded |
|---|-----------|---------------------------|
| 1 | One `opportunity_id` identifies one durable Opportunity | `OpportunityId` pattern; store id checks (existing) |
| 2 | An Opportunity may exist before the owner chooses apply | `create_from_strategy` contract + `test_opportunity_is_durable_before_any_owner_decision` |
| 3 | FR-002–FR-005 artefact snapshots are never mutated by FR-009 | `store.save` never touches artifacts; `test_review_update_does_not_touch_decision_or_ranking_inputs` |
| 4 | Owner decision is distinct from review metadata | Separate `decision` / `review` fields; no cross-validation between them |
| 5 | Queue position is derived and deterministic | ADR-004 §4; no rank field exists to persist |
| 6 | Workflow checkpoints are not the business system of record | ADR-003 + ADR-004 guardrails; no store change made |
| 7 | Resume/replay must not create a second Opportunity | Existing pre-allocated-id reclaim; M1 must re-prove it at the new boundary |
| 8 | Apply-only records remain readable | `test_apply_only_record_without_review_keys_still_loads` |
| 9 | Missing optional provenance must not break persistence | All identity facets remain optional; 16 live records with 0 URLs load today |
| 10 | A shared fingerprint does not prove duplication | `test_identical_content_fingerprints_stay_independent_records` |
| 11 | Skipped / archived records remain auditable | Non-destructive fields only; no delete path added |
| 12 | FR-009 introduces no application pipeline state | `PipelineStatus` untouched; ADR-004 guardrail |
| 13 | An archived record is not simultaneously pinned | `OpportunityReview.archived_records_are_not_pinned` |
| 14 | A duplicate never references itself | `Opportunity.duplicate_does_not_point_at_itself` |
| 15 | Review metadata does not alter M4 ordering | `test_review_metadata_does_not_change_m4_ranking` |

## 5. Persisted versus derived data

| Field / concept | Classification | Notes |
|-----------------|----------------|-------|
| `identity.*` (id, created_at, source facets, fingerprint) | Intrinsic persisted | Immutable after create (M4a backfill of title/company is the only exception) |
| `strategy_summary` | Intrinsic persisted (denormalised FR-003–FR-005) | Ranking input; never edited by review actions |
| `artifact_paths` + artifact snapshots | Intrinsic persisted, immutable | FR-009 reads only |
| `decision` (`OwnerDecisionRecord`) | Owner-authored persisted | apply / skip / defer + `decided_at` + notes |
| `review.reviewed_at` | Owner-authored persisted | Timestamp, not a boolean, so "when" survives |
| `review.pinned` | Owner-authored persisted | Explicit override; must never rewrite fit signals |
| `review.defer_until` | Owner-authored persisted | Date the record returns to active review |
| `review.archived_at` | Owner-authored persisted | Review visibility only — not employer rejection |
| `duplicate` (`DuplicateRelation`) | Owner-authored persisted | Confirmation + evidence; non-destructive |
| `status` (`PipelineStatus`) | Persisted, owned by M2/FR-012 | FR-009 must not write it |
| `outcome` (`OutcomeRecord`) | Historical audit persisted | FR-012 territory |
| Queue eligibility | **Derived** | not archived ∧ not confirmed duplicate ∧ decision ≠ skip ∧ not currently deferred |
| Rank position / priority band | **Derived** | Computed per query from the M4 sort key plus pinning |
| Age in days / staleness | **Derived** | From `identity.created_at` and a reference date |
| Ranking explanation | **Derived** | Regenerated per query (M4 `reasons`) |
| Duplicate confidence | **Derived** (later) | Detection output; only the owner's confirmation is persisted |
| Review-state label (`awaiting_review`, `reviewed`, `deferred`, `archived`) | **Derived** | Presentation label over orthogonal fields |

## 6. Review-state modelling decision

Recommendation: **Option B — orthogonal persisted fields.**

| Criterion | A: single enum | B: orthogonal fields | C: hybrid |
|-----------|----------------|----------------------|-----------|
| Clarity | One value to read, but one value must express several facts | Each field answers one question | Two representations of overlapping facts |
| Invalid combinations | Cannot express "reviewed and pinned and deferred" without new states | Only two need blocking (pinned+archived; self-duplicate) | Enum and fields can disagree |
| Transition complexity | Full transition table; grows combinatorially | Independent field updates; no table | Table plus field rules |
| Extensibility | Every new concern adds states | New concern = one field | Ambiguous where new concerns belong |
| Persistence compatibility | Old records need a default state and possibly migration | Missing keys read as defaults; no migration | Needs the enum backfilled |
| Query simplicity | Simple equality, but "which states count as active?" is hidden policy | Explicit boolean policy, testable field by field | Two sources to check |
| Overlap with pipeline status | High — `deferred` and `closed` collide with `PipelineStatus` | None; review fields carry no pipeline meaning | Partial overlap remains |
| Migration cost | Non-zero (16 live records) | Zero | Non-zero |

**Defer ruling.** `deferred` already exists in three plausible places. FR-009 expresses
defer as `decision="defer"` (the owner's business decision, audit) plus
`review.defer_until` (when it returns to active review). FR-009 does **not** write
`status="deferred"`; pipeline status stays with M2/FR-012. M4's existing treatment of
status `deferred` as open is unchanged.

## 7. Backward compatibility

- **No migration.** New fields are optional/defaulted; missing keys mean "never
  reviewed, not a duplicate". Verified by loading a hand-written apply-only index row.
- **No schema version bump.** The index loader ignores `schema_version`; bumping it
  would imply a migration that does not exist.
- **No live-record mutation in M0.** `data/opportunities/index.yaml` was read for
  evidence only.
- **Known serialisation side effect:** `save()` rewrites the whole index, so default
  review keys will appear on existing rows the next time any decision or outcome is
  recorded. Serialisation changes; meaning does not.
- **Existing owner decisions are untouched** — `record_decision` behaviour is unchanged.
- **CSV bridge unaffected** — `EXPORT_COLUMNS` is explicit; new fields do not leak.
- **Mixed old/new records are covered by tests** (legacy row + freshly created record
  in the same suite).

## 8. Acquisition provenance implications

| Question | M0 answer |
|----------|-----------|
| Which provenance fields belong on future Opportunities? | The existing facets are sufficient: `source_kind`, `platform_job_id`, `canonical_url`, `source_url`, `company`, `title`, `location_text`, `content_fingerprint`. No new fields in M0 |
| Raw vs canonical URL | Keep both. `source_url` preserves what the owner supplied (tracking parameters included); `canonical_url` is the normalised match key |
| Is `platform_job_id` optional? | Yes, permanently — 0/16 live records have one, and paste/export sources may never supply one |
| Should the fingerprint become a public domain field? | It already is, via `OpportunityIdentity` on the public `Opportunity`. No separate accessor is needed; it must never be treated as a unique key |
| Unify `source_kind` vocabularies? | **Keep separate.** Orchestration (`paste`, `export`, …) describes *how* a job arrived; opportunities (`seek`, `linkedin`, `manual`, …) describes *where* it came from. Mapping happens at the boundary, as with `decision_boundary.to_opportunity_decision` |
| Is a provenance value object warranted? | Not yet — `OpportunityIdentity` already groups these facets; extracting a new object would churn the public API without new behaviour |
| M0 or later? | Contract-level only in M0; detection thresholds and match precedence belong to FR-009 M3 |

## 9. M1 integration contract

Target sequence (FR-009 M1, not implemented in M0):

```
strategy succeeds
  → allocate opportunity_id (if absent) → checkpoint
  → persist Opportunity idempotently (decision=None)
  → checkpoint
  → owner_review interrupt
  → resume with apply | skip | defer
  → record_decision on the same opportunity_id
  → complete
```

M1 must prove:

1. `persist` runs for every decision path, so skip and defer produce durable records.
2. `create_from_strategy(opportunity_id=…)` still reclaims rather than duplicates when
   resumed at the earlier boundary (crash windows A–E in ADR-004).
3. `record_decision` is idempotent for a repeated identical decision and fails closed on
   a conflicting one (current `RecordDecisionNode` behaviour, now reachable for skip and
   defer).
4. Routing changes stay inspectable — `persist` moves out of
   `APPLY_SIDE_EFFECT_SEQUENCE`; `record_decision` applies to all three decisions.
5. Existing FR-008 functional tests are updated deliberately, not incidentally: the
   assertion "skip/defer create no Opportunity" becomes "skip/defer create a record
   carrying that decision".

## 10. Testing

Added `tests/unit/opportunities/test_m0_review_contracts.py` (9 tests):

| Test | Contract proven |
|------|-----------------|
| `test_opportunity_is_durable_before_any_owner_decision` | Pre-decision persistence is legitimate and reloadable |
| `test_new_records_receive_deterministic_review_defaults` | Defaults are deterministic |
| `test_apply_only_record_without_review_keys_still_loads` | Old records deserialise with no migration |
| `test_review_and_duplicate_survive_a_store_round_trip` | YAML round-trip preserves new fields |
| `test_duplicate_relation_cannot_reference_itself` | Self-duplication rejected |
| `test_archived_record_cannot_stay_pinned` | Contradictory review metadata rejected |
| `test_review_update_does_not_touch_decision_or_ranking_inputs` | Review is orthogonal to decision and ranking inputs |
| `test_review_metadata_does_not_change_m4_ranking` | M4 baseline frozen; no accidental reordering |
| `test_identical_content_fingerprints_stay_independent_records` | Fingerprint alone does not prove duplication |

Results:

- `tests/unit/opportunities/test_m0_review_contracts.py` — 9 passed
- `tests/unit/opportunities` + `tests/unit/opportunity_comparison` +
  `tests/unit/orchestration` + `tests/functional` — 314 passed
- Full repository suite — **895 passed** (886 at FR-008 freeze plus the 9 M0 contract
  tests; no regressions)

No FR-008 test required modification, which is itself evidence that the contracts are
additive.

## 11. Deferred work

- Moving workflow persistence before owner review (FR-009 M1)
- Review queue projection, eligibility policy, filtering, ordering extensions (M1)
- Owner queue actions: mark reviewed, pin, defer until, archive, reopen (M2)
- Duplicate candidate detection and owner confirmation (M3)
- Manual validation and ranking calibration (M4)
- UI / CLI queue surfaces (not scheduled)
- Application pipeline status semantics (FR-012)

## 12. GO / NO-GO assessment

| Area | Result | Notes |
|------|--------|-------|
| Implementation | **PASS** | Additive contracts only; no behaviour moved; FR-008 untouched |
| Domain model | **PASS** | Orthogonal review metadata, non-destructive duplicate relation, bounded concepts kept separate |
| Testing | **PASS** | 9 focused contract tests; 314 targeted tests green |
| Documentation | **PASS** | Spec, domain model, notes, testing strategy, roadmap, changelog, ADR-004, this report |
| Backward compatibility | **PASS** | No migration, no live mutation, old records verified loadable |
| Architecture | **PASS** | One system of record; queue derived; checkpoints remain recovery data (ADR-004) |

### Recommendation

**GO for FR-009 M1** — deterministic review projection plus the workflow
persistence-boundary move, with resume/replay idempotency as M1's single primary
architectural risk.

M1 must not begin without explicit owner approval.

## 13. Verification commands

```
python -m pytest tests/unit/opportunities/test_m0_review_contracts.py -q
python -m pytest tests/unit/opportunities tests/unit/opportunity_comparison tests/unit/orchestration tests/functional -q
python -m pytest -q
```
