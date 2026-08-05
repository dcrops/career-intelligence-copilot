# FR-014 M1 — Truth Validation Contracts

**Date:** 2026-08-05  
**Status:** Complete (M1) — contracts frozen. Succeeded by
[M2 technology validation](fr014_m2_technology_validation.md).
**Architecture:** [ADR-006](../adr/006_recruiter_document_truth_validation.md) (Accepted)  
**Preceding:** [M0 engineering spike](fr014_m0_engineering_spike.md) (Accepted)  
**Historical next (at M1):** M2 core deterministic validation — **now complete**

---

## 1. Architectural decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Package | `career_intelligence.truth_validation` | Distinct trust boundary; does not generate |
| Architecture | Catalogue → Detection → Validator → TruthReport | Owner-accepted M0 hybrid |
| Primary surface | Markdown | Owner-edit SoT; HTML/PDF derived |
| Detection vs truth | Separate fields on every finding | ADR-006; empty detection ≠ PASS |
| Candidate evidence | Profile-derived `candidate_authoritative` only | JD/plans are `context_only` |
| Detectors / gates | **Deferred to M2 / M3** | M1 = contracts only |
| M4 breadth | Corpus-justified claim kinds only | Not a general NL fact checker |

```
Future service (M2+)
  → build catalogue (M2)
  → detect claims (M2)
  → validate evidence (M2)
  → TruthReport (schema frozen in M1)
```

---

## 2. Implementation summary

| API | Role |
|-----|------|
| `Claim` / claim class / kind / strength | Structured factual assertion |
| `EvidenceProvenance` / `CatalogueEvidenceEntry` / `CandidateEvidenceCatalogue` | Catalogue contract + authority rules |
| `TruthFinding` | Detection certainty **and** evidence status (distinct) |
| `TruthReport` | Coverage, performed flags, findings, overall outcome |
| `validate_truth_report_contract` / `validate_catalogue_contract` | Explicit ADR-006 invariant helpers |
| `new_truth_report_id` / `new_truth_finding_id` / `new_claim_id` / `new_catalogue_entry_id` | `trp_` / `tfd_` / `tcl_` / `tee_` ULID ids |

Public surface: `career_intelligence.truth_validation`.

M1 does **not** implement claim detectors, catalogue population from profile, CLI,
package verify hooks, or FR-012 readiness integration.

### Key invariants encoded in models

- `outcome=pass` requires `coverage_status=complete` **and**
  `detection_performed` **and** `validation_performed`.
- Insufficient coverage cannot be `pass` / `warning`.
- Class A `supported` requires `candidate_authoritative` citations.
- JD / assessment / strategy / plans cannot be `candidate_authoritative`.
- Ambiguous Class A detection → at least `review_required`; high strength → `blocking`.
- Unsupported / contradictory Class A → `blocking`.
- Report outcome must not be weaker than worst finding severity.

---

## 3. Validation results

### Unit

`tests/unit/truth_validation/` — **22 passed**.

| Check | Result |
|-------|--------|
| Id patterns / generators | Pass |
| Extra fields forbidden | Pass |
| Class A/B subject rules | Pass |
| Profile vs JD authority | Pass |
| Class A cannot be supported by JD alone | Pass |
| Unsupported Class A blocking | Pass |
| Ambiguous detection severity | Pass |
| Empty findings + no performed flags ≠ PASS | Pass |
| Complete assessed coverage may PASS with empty findings | Pass |
| Outcome vs finding severity | Pass |
| Detection certainty ≠ evidence status | Pass |

---

## 4. Documentation updated

| Document | Change |
|----------|--------|
| ADR-006 | Accepted — detection vs truth; PASS rules; context-only JD |
| M0 spike | Marked Accepted; M4 corpus bound restated |
| Functional specification | FR-014 M0 accepted; M1 contracts |
| Domain model | Truth Validation entities |
| Testing strategy | FR-014 M1 coverage |
| Implementation notes | FR-014 M1 notes |
| Roadmap / changelog | FR-014 M1 progress |
| AGENTS / README / ADR index | Linked |
| Planning record | M0 accepted; M1 complete |

---

## 5. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| Duplicate ULID helper vs pipeline / submission | Accepted | Avoids cross-package coupling |
| Catalogue builder / detectors | Deferred | M2 |
| Owner CLI / gates | Deferred | M3 |
| Broader claim kinds | Deferred / bounded | M4 only with corpus evidence |

---

## 6. Recommendations for M2

| Recommendation | Classification |
|----------------|----------------|
| Populate Candidate Evidence Catalogue from Career Profile | M2 |
| Deterministic technology claim detection + Redwolf leakage | M2 |
| Fixture matrix: Vue/TS FAIL; Python PASS; employer-context PASS | M2 |
| Persist TruthReport (store decision) | M2 or M3 |
| Thin CLI / package / submission gates | M3 |

Validate first. Change second.

---

## 7. Final repository status

FR-014 **M0 accepted**, **M1 contracts complete**. Next: **M2** core deterministic
validation. Do not begin detectors under M1 reopen without owner request.
