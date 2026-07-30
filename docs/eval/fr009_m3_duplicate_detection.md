# FR-009 M3 — Duplicate Detection, Owner Confirmation and Canonical Selection

**Date:** 2026-07-30
**Status:** Complete. FR-009 remains **in progress** (M4 ranking calibration deferred).
**Architecture:** [ADR-004](../adr/004_opportunity_review_boundary.md)
**Preceding milestones:** [M0](fr009_m0_domain_contracts.md),
[M1](fr009_m1_persistence_boundary.md), [M2](fr009_m2_owner_review_actions.md)

---

## 1. Architectural decisions made

| # | Decision | Reasoning |
|---|----------|-----------|
| 1 | **Link, never merge.** No Opportunity is deleted, collapsed, or overwritten. | A false merge hides a real vacancy permanently and silently; a visible duplicate costs one glance. The asymmetry sets the whole design. |
| 2 | **Detection is derived, not persisted.** Candidates and groups are computed on every call. | Same rule that keeps queue position derived (ADR-004 decision 4). A persisted candidate table would be a second source of truth that goes stale the moment a record changes. |
| 3 | **Read/write split mirrors M1–M2.** `duplicates.DuplicateDetectionService` reads; `opportunities.DuplicateReviewService` writes. | M2 established that projections stay query-only. Detection can therefore be run at any time with no risk of mutation. |
| 4 | **Duplicate groups are star-shaped and one hop deep.** Canonical holds no relation; members carry `duplicate_of`. Chains rejected. | Reuses the existing M0 `DuplicateRelation` contract with no new aggregate. A group is reconstructed by a single scan, and "who is canonical" always has one answer. |
| 5 | **Rejections are persisted symmetrically** in the additive `Opportunity.duplicate_rejections`. | A rejected suggestion must not reappear. Writing both sides means either record can answer "already settled" without a global scan, and detection is direction-independent. |
| 6 | **Canonical selection is recommended, never applied.** | Consistent with "AI recommends; owner decides". The recommendation is deterministic so it can be explained and tested. |
| 7 | **Duplicate state stays orthogonal** to owner decision, review metadata, and `PipelineStatus`. | Prevents the "Potential Duplicate" pseudo-workflow-state the milestone brief warned against. Confirming a duplicate changes no decision and no pipeline status. |
| 8 | **Duplicate actions reuse the M2 audit mechanism** (`review_actions`). | One audit surface, not two. Kinds added: `confirm_duplicate`, `reject_duplicate`, `confirm_canonical`. |

**No new ADR.** M3 implements ADR-004 decision 7 ("duplicates are non-destructive")
rather than deciding anything that contradicts or extends it. ADR-004's implementation
status, compatibility, deferred-work, and guardrail sections were updated instead.

---

## 2. Duplicate detection strategy

Deterministic, multi-evidence, and explainable. No fuzzy or probabilistic matching, no
LLM.

**Facet comparison** (`duplicates/evidence.py`) classifies each comparable identity facet
as `matching`, `differing`, or `unknown`:

| Facet | Comparison |
|-------|------------|
| `platform` | `source_kind` equality, but only for identifying platforms (`seek`, `linkedin`, `indeed`, `recruiter`) — `manual` / `import` / `other` say nothing about origin |
| `platform_job_id` | exact |
| `canonical_url`, `source_url` | scheme/host/path, casefolded, query and fragment removed |
| `company` | casefolded, punctuation dropped, legal-entity suffixes removed (`Acme Pty Ltd` = `ACME`) |
| `title` | casefolded, bracketed asides and work-arrangement tokens removed (`Senior AI Engineer (Remote)` = `senior ai engineer`) |
| `location` | token containment, so `Sydney, NSW` matches `Sydney NSW Australia` |
| `content_fingerprint` | exact |

**A facet missing on either side is `unknown`, never a match.** This matters concretely:
0 of 16 live records carry a `platform_job_id` or `canonical_url`, so treating absence as
agreement would make every live pair look identical.

**Confidence tiers** (`duplicates/detection.py`):

| Confidence | Rule |
|------------|------|
| `definite` | same canonical URL, **or** same source URL, **or** same platform *and* platform job id |
| `probable` | company + title + (location **or** identical description text); **or** company + identical description text |
| `possible` | company + title alone; **or** identical description text alone |
| *(no candidate)* | anything weaker |

Normalisation deliberately collapses only formatting noise: `Acme` ≠ `Acme Digital`, and
`AI Engineer` ≠ `Senior AI Engineer`.

**Why a fingerprint alone is capped at `possible`.** The live store's five candidate pairs
are all fingerprint-only collisions from re-running the same posting through the workflow.
If a fingerprint were proof, the system would merge on the weakest evidence it has. The
tier keeps them visible and owner-resolvable instead.

**Nothing is auto-confirmed at any tier** — `definite` describes evidence strength, not
authority to act.

**Determinism.** Pairs are ordered by `opportunity_id` (ULIDs are time-sortable, so the
earlier discovery comes first) and candidates sort by confidence then ids. Detection over
the same records returns byte-identical results regardless of scan order, which the tests
assert directly.

**Resolved pairs are skipped:** confirmed links, records already sharing a canonical, and
rejected pairs. So the candidate list shrinks as review progresses instead of re-asking
settled questions.

---

## 3. Duplicate group model

```
canonical  opp_A   duplicate = None
             ▲
             ├──── opp_B   duplicate = DuplicateRelation(duplicate_of=opp_A, confirmed_at, evidence)
             └──── opp_C   duplicate = DuplicateRelation(duplicate_of=opp_A, confirmed_at, evidence)
```

- **Derived, not stored.** `build_groups` scans `duplicate_of` links; there is no group
  aggregate, no group id, and no group file.
- **One hop deep.** Chains raise `OpportunityTransitionError`, so `duplicate_of` always
  points at a true canonical and the projection is unambiguous.
- **Everything survives.** Each member keeps its own identity, provenance, review
  metadata, owner decision, and FR-002–FR-005 artefact snapshots.
- **Not a workflow state.** `reviewed_at`, `pinned`, `defer_until`, `archived_at`, and the
  owner decision are untouched by grouping.
- **Queue effect.** Members are excluded with the existing deterministic reason
  `confirmed_duplicate`; the canonical stays in the queue. Unresolved candidates exclude
  nothing.

**Owner action contracts**

| Action | Inputs | State change | Idempotency | Invalid cases |
|--------|--------|--------------|-------------|---------------|
| `confirm_duplicate` | duplicate id, canonical id, evidence kinds, timestamps | `DuplicateRelation` on the duplicate record only | same link → no-op, original `confirmed_at` kept, no new audit entry | self-reference (validation error); already linked elsewhere, canonical is itself a duplicate, subject is an existing canonical, or pair previously rejected (transition errors) |
| `reject_duplicate` | two ids, optional note, timestamps | `DuplicateRejection` appended on **both** records | already rejected → no-op, original `rejected_at` kept | self-reference; pair already confirmed |
| `confirm_canonical` | chosen canonical id, timestamps | every member re-pointed at the choice; chosen record's relation cleared | already canonical → no-op returning the group | record not part of a confirmed group |

Each real change appends exactly one `ReviewActionRecord`; each no-op appends none.

---

## 4. Canonical recommendation strategy

Deterministic ordering, applied in sequence (`duplicates/canonical.py`):

1. **Has FR-002–FR-005 artefact snapshots** — a canonical record without evidence cannot
   drive tailoring later.
2. **Not a recruiter repost** — prefer the record advertised by a non-intermediary.
3. **Platform rank** — `seek` → `linkedin` → `indeed` → `other` → `manual` → `import` →
   `recruiter`; structured platforms carry a stable listing id and canonical URL.
4. **Identity metadata completeness** — count of populated identity facets (out of 7).
5. **Earliest discovery** (`identity.created_at`).
6. **`opportunity_id` ascending** — so ties never depend on scan order.

The result carries `reasons`, `current_canonical_opportunity_id`, `matches_current`, and
`owner_confirmation_required=True`. Nothing is re-pointed without
`confirm_canonical`.

**Honest limitation.** `SourceKind` has no employer-careers value: `derive_source_facets`
maps an employer's own careers site to `other`. "Official employer source" is therefore
approximated by "not a recruiter repost" plus platform rank. Adding an employer-careers
source kind is recorded as deferred work in ADR-004.

---

## 5. Alternative designs considered and rejected

| Alternative | Why rejected |
|-------------|--------------|
| **Automatic merge above a confidence threshold** | The harm is asymmetric: a wrong merge silently removes a real vacancy from the owner's queue, while a duplicate left visible costs a glance. No threshold justifies that trade at this scale. |
| **Persisted duplicate-candidate table** | A second source of truth that goes stale whenever identity or acquisition data changes, and it contradicts ADR-004's "derived, never persisted" rule for queue-shaped data. Detection is cheap over 16 records. |
| **A `DuplicateGroup` aggregate with its own id and file** | Introduces a second persistence mechanism, a consistency problem between group file and records, and migration cost — for information already implied by `duplicate_of`. |
| **Peer-to-peer duplicate links (many-to-many)** | "Which advertisement do I act on?" would have no single answer, and transitive closure would have to be computed and disambiguated on every read. The star shape answers it structurally. |
| **A `potential_duplicate` review/workflow state** | Explicitly warned against in the milestone brief, and it would conflate an unresolved *suggestion* (derivable) with owner-authored review state. It would also collide with `PipelineStatus` semantics. |
| **Rejection recorded on one side only** | Detection would have to know which side to consult; symmetric records make suppression direction-independent and keep the check local to each record. |
| **Fuzzy/edit-distance title and description similarity** | Non-deterministic thresholds, hard to explain in an owner-facing rationale, and impossible to test as a fixed contract. Deferred until deterministic evidence proves insufficient. |
| **LLM-judged duplicate confirmation** | Unexplainable and non-reproducible for a decision whose failure mode is losing a vacancy. Contradicts "intelligence before automation". |
| **Extending `OpportunityReviewService` with duplicate actions** | Duplicate review is a distinct concern with pair-level (not record-level) semantics and its own invariants. A focused service keeps each class's contract small; both write through `OpportunityService.replace`. |
| **Optimistic concurrency / record versioning** | Same finding as M2: the store rewrites the whole index and is single-user. Actions reload immediately before writing; the limitation is documented rather than redesigned. |

---

## 6. Testing summary

**New unit tests — `tests/unit/duplicates/` (27)**

| Area | Coverage |
|------|----------|
| Confidence tiers | Each tier's rule, including "same platform, different job id" staying reviewable rather than definite |
| Fingerprint safety | Identical description text alone never exceeds `possible` |
| Unknown vs match | Missing facets are `unknown`; `manual` source kind is not platform evidence |
| Normalisation | Suffix/bracket noise collapses; genuinely different names stay different |
| Determinism | Forward and reverse scans produce identical candidates and ordering |
| Resolved pairs | Confirmed, same-group, and rejected pairs are not re-suggested (including one-sided rejection) |
| Canonical policy | Every criterion in isolation, plus order-independence and advisory flags |
| Groups | Derived from `duplicate_of` only; a lone record forms no group |
| Read-only | `index.yaml` is byte-identical after candidate and group queries |
| Backward compatibility | Rows written before `duplicate_rejections` existed still load and project |

**New unit tests — `tests/unit/opportunities/test_m3_duplicate_actions.py` (18)**

Confirm/reject/canonical behaviour, idempotency, typed errors for self-reference, chains,
canonical re-pointing, contradictions between confirm and reject, aggregate integrity
(decision, status, outcome, artefacts, identity, review metadata preserved), audit-entry
content, queue effect, and reload durability.

**New functional journeys — `tests/functional/test_fr009_duplicate_review.py` (7)**

Real YAML store and real artefact files in `tmp_path`:

| Journey | Result |
|---------|--------|
| Cross-platform duplicate suggested → confirmed → group formed, 3/3 records and all artefact files intact | ✓ |
| Rejection suppresses the suggestion across repeated scans; later confirm attempt raises | ✓ |
| Unresolved candidate stable across scans and hides nothing from the queue | ✓ |
| Owner confirms a different canonical; nothing deleted; recommendation then matches | ✓ |
| **Crash recovery:** interrupted re-point leaves a partial star; replaying `confirm_canonical` converges to one consistent group | ✓ |
| Repeating every action leaves state, timestamps, and audit trail unchanged | ✓ |
| Duplicate state and artefacts survive a fresh service instance | ✓ |

**Shared-helper change.** `tests/unit/opportunities/helpers.py` gained an optional
`raw_text` parameter so a test posting can have a genuinely distinct content fingerprint.
Default unchanged.

---

## 7. Full test results

```
python -m pytest -q
1002 passed in 18.83s
```

Baseline at M2 was 950; M3 adds 52 tests. No existing test required modification —
detection is additive and the queue's `confirmed_duplicate` exclusion already existed
from M1.

```
python -m ruff check src/career_intelligence/duplicates \
    src/career_intelligence/opportunities/duplicate_service.py \
    src/career_intelligence/opportunities/models.py \
    src/career_intelligence/opportunities/__init__.py \
    tests/unit/duplicates tests/unit/opportunities/test_m3_duplicate_actions.py \
    tests/unit/opportunities/helpers.py tests/functional/test_fr009_duplicate_review.py
All checks passed!
```

(The repository as a whole still reports pre-existing lint findings unrelated to M3.)

---

## 8. Manual validation results

`python scripts/run_fr009_duplicate_review_manual.py demo --workspace data/_fr009_m3_manual --offline-fixtures`

Three fixture acquisitions: the same vacancy twice, plus one unrelated vacancy.

| Scenario | Observed | Result |
|----------|----------|--------|
| Detection surfaces the duplicated pair | `probable` — "Same company and title with identical description text"; matching `company, title, location, content_fingerprint`; unknown `platform, platform_job_id, canonical_url, source_url` | **Pass** |
| Unrelated vacancy not suggested | no candidate involving it | **Pass** |
| Unresolved candidates stable and non-hiding | identical across scans; both records still awaiting decision | **Pass** |
| Canonical recommendation advisory | reasons listed; `owner_confirmation_required=True` | **Pass** |
| Confirmation links without deleting | 3 of 3 records preserved; member keeps 5 artefact files; `decision` untouched; group `canonical + 1 member` | **Pass** |
| Duplicate leaves queue, canonical stays | both asserted true | **Pass** |
| Owner confirms a different canonical | roles swap; 3 of 3 records preserved; new canonical has no relation | **Pass** |
| Rejection does not return | rejected pair absent from later scans; record still present | **Pass** |
| Idempotency and audit | repeat actions changed nothing; audit `['confirm_duplicate', 'confirm_canonical', 'reject_duplicate']`; one rejection recorded | **Pass** |

`python scripts/run_fr009_duplicate_review_manual.py candidates --opportunities data/opportunities`

| Observation | Classification |
|-------------|----------------|
| 16 live records produce 5 candidates, all `possible` "Identical description text only", 0 confirmed groups | **Pass** — matches the known three fingerprint collision groups from the M0 audit; nothing auto-confirmed |
| Live identity `company` / `title` are `unknown` on those records, so evidence is fingerprint-only | **Data limitation**, not an implementation bug. `OpportunityService.backfill_identity_from_posting_artifacts` can populate them from trusted posting snapshots; recommended before any live duplicate review. |
| Live store byte-identical afterwards (`git status` clean) | **Pass** — detection is read-only |

No material issues. No live records were modified during validation.

---

## 9. Compatibility and known limitations

**Compatibility.** `duplicate_rejections` is additive with an empty default and
`DuplicateRelation` is unchanged from M0, so no migration was needed and no live record
was touched. Rows written before M3 load and project unchanged (covered by test). As
noted in M0, any future write rewrites the whole index and will materialise default keys
on existing rows — a serialisation change only.

**Known limitations**

1. **Concurrency** — unchanged from M2: whole-index YAML rewrite, last writer wins.
   `reject_duplicate` and `confirm_canonical` perform several sequential writes, so a
   crash mid-sequence can leave a partial state. Both are convergent: replaying the same
   action completes it, which the crash-window functional test proves. Acceptable for a
   single-user store; multi-writer safety would need optimistic concurrency.
2. **Detection is O(n²)** over all records. Fine at 16 records; a blocking key (company or
   fingerprint) would be needed at a much larger scale.
3. **Rejections cannot currently be undone** through a service method. Reversal would
   need an explicit `clear_duplicate_rejection`; deferred until the owner wants it.
4. **Unlinking a confirmed duplicate** has no service method either — `confirm_canonical`
   re-points a group but does not dissolve one. Deferred for the same reason.
5. **"Official employer source" is approximated** because `SourceKind` has no
   employer-careers value (see §4).
6. **Live detection quality is capped by acquisition metadata** — no platform ids or URLs
   on existing records, and missing identity company/title on some (see §8).

---

## 10. Deferred work and follow-up recommendations for M4

| Item | Note |
|------|------|
| **Ranking calibration (M4)** | The M4 milestone proper. Includes the known wording issue "Recently assessed; awaiting owner action". |
| **Identity backfill before live duplicate review** | Run `backfill_identity_from_posting_artifacts` so live candidates rest on company/title evidence rather than fingerprint alone. Cheap, deterministic, high value for M4 validation. |
| **Employer-careers `SourceKind`** | Would let canonical selection prefer an official employer advertisement directly. |
| **Acquisition provenance capture** | Populating `platform_job_id` / `canonical_url` at acquisition would move most real duplicates from `possible` to `definite`. Belongs with acquisition adapters, not FR-009. |
| **`clear_duplicate_rejection` / `unlink_duplicate`** | Complete reversibility for duplicate decisions. |
| **Group-aware queue presentation** | Optionally annotate a canonical entry with "represents N advertisements". Presentation only — must not change fit ordering. |
| **Blocking keys for detection** | Only if the store grows enough for O(n²) to matter. |

---

## 11. Final assessment

| Dimension | Result |
|-----------|--------|
| Implementation | **PASS** |
| Non-destructiveness | **PASS** — no delete, collapse, or overwrite path exists |
| Detection determinism | **PASS** |
| Owner confirmation model | **PASS** — confirm / reject / leave unresolved, nothing automatic |
| Canonical selection | **PASS** — deterministic recommendation, explicit owner confirmation |
| Idempotency | **PASS** |
| Replay / crash recovery | **PASS** — convergent actions, verified by functional test |
| Projection | **PASS** — derived, deterministic, M4 order unchanged |
| State separation | **PASS** — duplicate state independent of decision, review metadata, pipeline status |
| Testing | **PASS** — 1002 passed |
| Manual validation | **PASS** — no material issues |
| Documentation | **PASS** |
| Backward compatibility | **PASS** — no migration |
| Architecture | **PASS** — no new source of truth, ADR-004 guardrails held |

**Recommendation for M4: GO** — with the identity backfill in §10 done first, so ranking
calibration is validated against records whose duplicate evidence is grounded in company
and title rather than description text alone.
