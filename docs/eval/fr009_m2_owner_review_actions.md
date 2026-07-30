# FR-009 M2 Acceptance Report — Owner Review Actions, Reversibility and Audit

**Milestone:** FR-009 M2 (of M0–M4 + close-out)  
**Status:** Complete — historical milestone record. FR-009 was closed on 2026-07-30
([FR-009 acceptance](fr009_opportunity_review_queue.md)).  
**Date:** 2026-07-30  
**Architecture:** [ADR-004](../adr/004_opportunity_review_boundary.md) (Accepted)  
**Predecessors:** [M0](fr009_m0_domain_contracts.md), [M1](fr009_m1_persistence_boundary.md)  
**Scope:** reversible owner review actions with lightweight audit history and
pin-aware projection. No duplicate detection, ranking calibration, UI, or pipeline
tracking.

---

## 1. Implementation summary

`OpportunityReviewService` is the write boundary for owner review metadata. It reloads
an Opportunity, validates the action, mutates only the fields that action owns, appends
one `ReviewActionRecord`, and persists through `OpportunityService.replace` (index only —
artefact files are never touched). `ReviewQueueService` remains read-only and now orders
eligible records **pinned first**, then by the unchanged M4 comparison.

## 2. Action contracts

| Action | Inputs | State change | Idempotency | Invalid | Queue effect | Audit |
|--------|--------|--------------|-------------|---------|--------------|-------|
| `mark_reviewed` | optional `reviewed_at`, `occurred_at` | set `reviewed_at` if unset | preserve original timestamp; no new history | — | stays awaiting if undecided | one entry on first set |
| `pin` | optional `occurred_at` | `pinned=True` | no-op if pinned | archived → `OpportunityTransitionError` | may rise to front | one entry on change |
| `unpin` | optional `occurred_at` | `pinned=False` | no-op if unpinned | — | M4 order restored | one entry on change |
| `defer_until` | `until`, `reference_date`, `occurred_at` | `decision=defer` + `defer_until` | same date no-op | past date → validation error; apply/skip → transition error | excluded while `until > reference_date` | entry with ISO date detail |
| `clear_defer` | optional `occurred_at` | clear date **and** defer decision → `None` | no-op if not deferred | apply/skip with stray date → transition error | returns to awaiting | entry with clear detail |
| `archive` | optional `archived_at`, `occurred_at` | set `archived_at`; **auto-clear pin** | preserve original timestamp | — | excluded from both scopes | entry; detail if pin cleared |
| `reopen` | optional `occurred_at` | `archived_at=None` only | no-op if not archived | — | visibility by remaining rules | one entry on change |

## 3. State-separation proof

| Concern | Where it lives | M2 write surface |
|---------|----------------|------------------|
| Owner decision | `Opportunity.decision` | `defer_until` / `clear_defer` only; never invents apply/skip |
| Review metadata | `Opportunity.review` | all actions |
| Pipeline status | `Opportunity.status` | **never written** |
| Ranking inputs | `strategy_summary` + artefacts | **never mutated** |
| Audit evidence | `review_actions` | append-only; not used for eligibility |

Mark reviewed does not create a decision. Archive does not mean rejected. Pin does not
change fit strength.

## 4. Audit decision

| Option | Verdict |
|--------|---------|
| A — current-state fields only | Rejected: `clear_defer` would erase defer evidence |
| **B — lightweight `review_actions` on Opportunity** | **Selected** |
| C — separate audit log | Rejected: second persistence mechanism |

`ReviewActionRecord(action, occurred_at, detail?)` is additive with empty default for
old records. History is audit evidence only. Limitation: no actor field (single-user);
no previous/new value snapshots beyond optional `detail`; not a full event log.

## 5. Defer policy

- `decision=defer` + `defer_until is None` → indefinitely deferred  
- `defer_until > reference_date` → currently deferred  
- `defer_until <= reference_date` → expired → eligible for **active**; still “decided”
  for **awaiting** until `clear_defer`  
- Past dates rejected against explicit `reference_date`  
- Same-day means expired (reappears on that date)  
- `clear_defer` → undecided (`decision=None`, `defer_until=None`)

## 6. Ordering policy

```
eligible → pinned first → M4 (posture → fit → tier → id) → stable ranks
```

Pinned items prepend `"Pinned by owner"`. Fit values and M4 reasons are unchanged.
Pin is a presentation override, not a fit score.

## 7. Reversibility

| Forward | Reverse |
|---------|---------|
| pin | unpin |
| defer_until | clear_defer (to undecided) or natural expiry (to active) |
| archive | reopen |

Mark reviewed has no reverse in M2 (timestamp is preserved; later “unreview” is out of
scope). Reopen does not reset decision, defer, duplicate, or reviewed_at.

## 8. Test evidence

- `tests/unit/opportunities/test_m2_review_actions.py` — actions, integrity, audit, pin
- `tests/unit/review_queue/test_service.py` — pin-first, reviewed stays awaiting
- `tests/functional/test_fr009_owner_review_actions.py` — end-to-end journeys
- Focused M2-related suites green; targeted opportunities + comparison + review_queue +
  orchestration + functional **369 passed**
- Full suite **950 passed** (928 at M1 + 22 new)
- Ruff clean on M2-touched files

## 9. Manual validation

`scripts/run_fr009_owner_review_manual.py demo --workspace data/_fr009_m2_manual
--offline-fixtures`

| # | Scenario | Outcome |
|---|----------|---------|
| 1 | Mark reviewed stays awaiting; no decision | **Pass** |
| 2 | Pin raises weak record; unpin restores M4 order | **Pass** |
| 3 | Future defer hides; expiry returns to active; clear_defer → awaiting | **Pass** |
| 4 | Archive hides; reopen restores | **Pass** |
| 5 | Idempotent repeats; one Opportunity; status assessed | **Pass** |
| 6 | Apply/skip/defer decisions intact through unrelated actions | **Pass** (unit + functional) |
| 7 | No artefact mutation | **Pass** |
| 8 | Live-store projection remains read-only when only querying | **Pass** (M1 invariant retained) |

No material issues. No policy recalibration performed.

## 10. Compatibility

No migration. Pre-M2 records load with `review_actions=()`. Missing review keys still
default. Live `data/opportunities/` was not mutated by M2 tests or the scratch demo
workspace.

## 11. Known limitations

- **Concurrency:** whole-index YAML rewrite, last-writer-wins. Mitigated by reload-before-
  write; no optimistic versioning.
- **Audit:** action + timestamp + optional detail only; no actor; no full before/after
  snapshots; history not queryable as a separate store.
- **Expired defer:** remains historically `decision=defer` until `clear_defer`, so it
  returns to *active* but not *awaiting* on expiry alone.
- **M4 wording** (“Recently assessed; awaiting owner action” on applied records) still
  deferred to M4 calibration.

## 12. Deferred work

- Duplicate candidate detection and confirmation (M3)
- Ranking calibration / M4 wording (M4)
- UI / CLI review surfaces
- Richer action history / multi-user concurrency
- Application pipeline tracking (FR-012)

## 13. Final assessment

| Area | Result |
|------|--------|
| Implementation | **PASS** |
| Reversibility | **PASS** |
| Idempotency | **PASS** |
| Auditability | **PASS** (lightweight; limitations documented) |
| Projection | **PASS** |
| Testing | **PASS** |
| Manual validation | **PASS** |
| Documentation | **PASS** |
| Backward compatibility | **PASS** |
| Architecture | **PASS** |

### Recommendation

**GO for FR-009 M3** — duplicate candidate detection and non-destructive owner
confirmation, with false-merge prevention as the primary risk.

M3 must not begin without explicit owner approval.

## 14. Verification commands

```
python -m pytest tests/unit/opportunities/test_m2_review_actions.py tests/unit/review_queue tests/functional/test_fr009_owner_review_actions.py -q
python -m pytest tests/unit/opportunities tests/unit/opportunity_comparison tests/unit/review_queue tests/unit/orchestration tests/functional -q
python -m pytest -q
python scripts/run_fr009_owner_review_manual.py demo --workspace data/_fr009_m2_manual --offline-fixtures
```
