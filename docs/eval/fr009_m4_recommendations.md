# FR-009 M4 — Opportunity Prioritisation and Recommendation

**Date:** 2026-07-30  
**Status:** Complete. FR-009 was closed on 2026-07-30 —
[FR-009 acceptance](fr009_opportunity_review_queue.md).  
**Architecture:** [ADR-004](../adr/004_opportunity_review_boundary.md)  
**Preceding milestones:** [M0](fr009_m0_domain_contracts.md),
[M1](fr009_m1_persistence_boundary.md), [M2](fr009_m2_owner_review_actions.md),
[M3](fr009_m3_duplicate_detection.md)

---

## 1. Architectural decisions made

| # | Decision | Reasoning |
|---|----------|-----------|
| 1 | **Recommendations are derived, never persisted.** | Same rule as queue position and duplicate groups (ADR-004). A stored rank would stale on every review or strategy change. |
| 2 | **Calibrate the comparison sort key for quality, not effort.** | Owner authorised M4 with "do not optimise for application effort" — generation/submission are expected to automate. `application_tier` leaves the sort key; `practical_value` enters it. |
| 3 | **`unknown` fit contributes 0.** | Missing evidence must not increase confidence. |
| 4 | **Recommendation service composes the review queue.** | Eligibility, pin override, and duplicate exclusion stay single-sourced in `ReviewQueueService`. Recommendations add structured explanation on top. |
| 5 | **Do not invent unavailable signals.** | Closing dates do not exist in the product. Salary/location/work model live on JobAnalysis artefacts, not the Opportunity index — they are not ranking factors until denormalised or joined deliberately. |
| 6 | **Fix decision-aware ranking wording.** | FR-009 keeps `status=assessed` after apply; the old "Recently assessed; awaiting owner action" was false for applied records. |
| 7 | **No new ADR.** | M4 amends ADR-004's frozen sort-key guardrail under explicit owner authorisation for calibration. |

---

## 2. Ranking model selected

**Calibrated sort key** (ascending = higher priority):

1. `pursuit_posture` — FR-005 attention signal  
2. Fit strength (technical + commercial + portfolio; `unknown` = 0)  
3. `practical_value` — career value (`career_priority` → `acceptable_opportunity` → `volume_obligation` → `deferred_pending_information`)  
4. `opportunity_id` — stable tie-break  

**Removed from the sort key:** `application_tier` (effort band). It remains on the ranked item and in explanations as **effort context** so the owner can still see expected application cost without letting it displace a higher-value role.

**Presentation override (unchanged):** eligible → pinned first → calibrated order.

**Eligibility (unchanged):** archived, confirmed-duplicate, skipped, currently deferred, and terminal statuses stay out of the default projections.

---

## 3. Recommendation representation

New package `career_intelligence.recommendations`:

| Type | Role |
|------|------|
| `OpportunityRecommendation` | One prioritised item with band, urgency, next action, +/-/missing/trade-offs, ranking reasons, optional `duplicate_group_size` |
| `RecommendationReport` | Derived report for `awaiting_review` or `active` scope |
| `OpportunityRecommendationService` | Read-only composer over `ReviewQueueService` |

Queries:

- `recommend_awaiting_review(reference_date=…)`
- `recommend_active(reference_date=…)`

Priority bands (`immediate` / `high` / `standard` / `low`) are coarse labels derived from posture, practical value, and fit — not a second sort key.

---

## 4. Explanation strategy

Every recommendation carries:

| Field | Content |
|-------|---------|
| `ranking_reasons` | Calibrated comparison reasons (posture, fit, practical value, effort context, decision/status, relative position) |
| `positives` | Strong posture, career priority, strong fits, pin |
| `negatives` | Weak posture, volume obligation, weak/misaligned fits |
| `missing` | Absent company/title/location identity; unknown fit dimensions; incomplete strategy summary |
| `trade_offs` | e.g. high effort band with low practical value; strong posture with modest fit |
| `urgency` | `due` / `upcoming` from `outcome.follow_up_date`; `process` for interviewing/offer; otherwise `none` — **never invents closing dates** |
| `recommended_next_action` | Deterministic from decision + review + pipeline status (e.g. `record_owner_decision`, `prepare_application_package`) |

Owner remains in control: recommendations never write decisions, review metadata, or duplicate links.

---

## 5. Alternative designs considered and rejected

| Alternative | Why rejected |
|-------------|--------------|
| Persist priority / rank on Opportunity | Second source of truth; contradicts ADR-004 derived-views principle |
| Opaque composite score | Unexplainable; forbidden by FR-009 contracts |
| LLM ranking | Non-deterministic; contradicts "deterministic first" |
| Rank by application_tier (effort) | Explicitly rejected by M4 owner brief |
| Load JobAnalysis for salary/location/remote vs Career Profile | Valuable later, but requires artefact I/O and preference-matching policy; not available as index fields; deferred rather than inventing |
| Urgency from closing dates | Closing dates do not exist anywhere in the product |
| Replace ReviewQueueService with recommendations | Would duplicate eligibility/pin logic; composition is safer |
| New ADR for calibration | ADR-004 already owns the boundary; amend it |

---

## 6. Testing summary

**Comparison calibration** (`tests/unit/opportunity_comparison/`): posture > fit > practical value; effort tier cannot outrank value; unknown fit = 0; decision-aware assessed wording; stable id tie-break.

**Recommendations** (`tests/unit/recommendations/`): quality order, replay stability, missing-location reporting without inventing salary urgency, follow-up urgency, next actions, pin override, duplicate exclusion + group annotation, read-only store, legacy incomplete records.

**Functional** (`tests/functional/test_fr009_recommendations.py`): deterministic explained order on real artefacts; pin + duplicate interaction; apply updates next action without mutating ranking inputs; reload idempotency.

---

## 7. Full test results

```
python -m pytest -q
1019 passed in 18.07s
```

Baseline at M3 was 1002; M4 adds 17 tests. Focused lint on M4 paths passes.

---

## 8. Manual validation results

`python scripts/run_fr009_recommendations_manual.py demo --workspace data/_fr009_m4_manual --offline-fixtures`

| Scenario | Result |
|----------|--------|
| Three fixtures ordered by quality (pursue/career_priority ahead of consider, ahead of do_not_prioritise) with +/- explanations | **Pass** |
| Stable replay of the same report | **Pass** |
| Pin raises weak record; fit strength unchanged | **Pass** |
| Apply → `prepare_application_package`; no "awaiting owner action" wording; awaiting queue excludes applied | **Pass** |
| Opportunity count unchanged (read-only) | **Pass** |
| Fixture set had no duplicate candidates (distinct roles) — duplicate branch skipped | **Data limitation** |

`recommend --opportunities data/opportunities` (read-only): 13 awaiting / 3 excluded. Top item `pursue` / `career_priority` / fit 13. Most live rows still miss identity company/title — recommendations surface that as `missing` without inventing values. Live store unmodified.

---

## 9. Follow-up recommendations

| Item | Note |
|------|------|
| **FR-009 close-out** | **Done** (2026-07-30) — [FR-009 acceptance](fr009_opportunity_review_queue.md) |
| **Identity backfill** | `cic opportunity backfill-identity` so live recommendations show real titles/companies |
| **Profile preference matching** | Optional later: join JobAnalysis location/comp/remote to Career Profile preferences — requires explicit policy |
| **Closing-date extraction** | Only if acquisition/analysis gain a closing-date field; do not fake urgency |
| **Group-aware queue wording** | Canonical already carries `duplicate_group_size` on recommendations; optional richer UI later |
| **CLI `cic opportunity recommend`** | Manual script covers validation; a Typer command would be convenience only |

---

## 10. Final assessment

| Dimension | Result |
|-----------|--------|
| Implementation | **PASS** |
| Ranking calibration | **PASS** — quality over effort |
| Explainability | **PASS** |
| Determinism | **PASS** |
| Derived (not persisted) | **PASS** |
| Owner control preserved | **PASS** |
| Duplicate / queue interaction | **PASS** |
| Testing | **PASS** — 1019 passed |
| Manual validation | **PASS** |
| Documentation | **PASS** |
| Backward compatibility | **PASS** — no migration |
| Architecture | **PASS** |

**Recommendation for FR-009 close-out: GO** after owner review of this report. Run identity backfill before relying on live recommendation titles.
