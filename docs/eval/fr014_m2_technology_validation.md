# FR-014 M2 — Technology Claim Validation

**Date:** 2026-08-05  
**Status:** Complete (M2)  
**Architecture:** [ADR-006](../adr/006_recruiter_document_truth_validation.md) (unchanged)  
**Preceding:** [M1 contracts](fr014_m1_truth_validation_contracts.md)  
**Next:** M3 owner CLI + package / submission gates —
[eval/fr014_m3_owner_workflow.md](fr014_m3_owner_workflow.md) (**complete**).


---

## 1. Executive summary

M2 delivers deterministic technology/framework truth validation:

- `CandidateEvidenceCatalogue` populated from Career Profile only
- Markdown claim detection with Class A / B / C framing rules
- Evidence validation against the catalogue
- Redwolf TypeScript/Vue leakage **FAIL**; supported Python/FastAPI **PASS**
- Employer-context mentions distinguished (not capability)
- Explainable `TruthReport` findings
- No CLI, gates, rewriting, or LLM judgement

---

## 2. Catalogue architecture

```
CareerProfile
  ├─ skills.technical / domain     → profile_skill (candidate_authoritative)
  ├─ experience[].technologies     → profile_experience
  └─ projects[].technologies       → profile_project
        ↓
CandidateEvidenceCatalogue
  (object_key + aliases; claim_kinds include technology)
```

| Rule | Held |
|------|------|
| Only profile-derived authoritative entries | Yes |
| JD / assessment / strategy / plans never in catalogue as authorizing | Yes |
| `context_technology_labels` expand scan lexicon only | Yes |
| Aliases expand matching, not evidence | Yes |

API: `build_catalogue_from_profile` / `TruthValidationService.build_catalogue`.

---

## 3. Claim-detection rules

Lexicon = catalogue labels/aliases + well-known tech labels + optional JD labels.

| Framing | Class | Cues |
|---------|-------|------|
| Candidate capability | A | First-person skill cues; Redwolf “where I do my best…” |
| Employer / role context | B | “The role uses…”, “requires…”, “your team…” |
| Aspiration | C | “interested in expanding into…”, “keen to learn…” |
| Bare keyword list | — | **Ignored** (false-positive safeguard) |

Strength inferred from wording (`proficient`, `best engineering` → high, etc.).

Ambiguous Class A (mixed cues) → `review_required` or `blocking` by strength (ADR-006).

---

## 4. Redwolf before / after

**Before (generation defect):**

> Roles centred on Python, TypeScript, and Vue are where I do my best engineering work.

| Tech | Profile evidence | Risk |
|------|------------------|------|
| Python | Yes | OK |
| TypeScript | No (JD only) | Capability leakage |
| Vue | No (JD only) | Capability leakage |

**After (M2 validation):**

| Finding | Class | Evidence | Severity |
|---------|-------|----------|----------|
| python | A | supported | info |
| typescript | A | unsupported | **blocking** |
| vue | A | unsupported | **blocking** |

**Outcome:** `fail` — blocks external-use readiness once M3 gates land; already
explainable for owner review.

---

## 5. False-positive safeguards

| Safeguard | Behaviour |
|-----------|-----------|
| Employer-context cues | Class B; `not_applicable`; does not FAIL |
| Bare keyword lists | No claim emitted |
| Longest-match lexicon | Prefer `Vue.js` over `Vue` overlaps |
| Aliases | Matching only; no invented support |
| JD context labels | Lexicon expansion only; never `supported` |
| Aspiration framing | Class C; not blocking by default |

---

## 6. TruthReport examples

### Redwolf (fail)

```
outcome=fail coverage=complete detection_performed=true validation_performed=true
- python A supported info
- typescript A unsupported blocking
- vue A unsupported blocking
```

### Supported Python/FastAPI (pass)

```
outcome=pass
- python A supported info
- fastapi A supported info
```

### Employer context (pass)

```
outcome=pass
- typescript B not_applicable info
- vue B not_applicable info
```

---

## 7. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/truth_validation/` (M1+M2) | **31 passed** |
| `tests/functional/test_fr014_m2_truth_validation.py` | **1 passed** |
| Combined focused | **32 passed** |

---

## 8. Manual validation

```bash
python scripts/run_fr014_truth_manual.py
```

**RESULT: PASS** — redwolf fail; supported pass; employer_context pass.
Report artefact: `data/_fr014_m2_manual/redwolf_report.json`.

---

## 9. Documentation updated

Functional spec, domain model, testing strategy, implementation notes, roadmap,
changelog, AGENTS/README, planning record, this eval.

---

## 10. Out of scope (held)

CLI · package/submission gates · render integration · years/employment/cert/domain
claim kinds · rewriting · LLM judgement.

---

## 11. Recommendations for M3

| Item | Notes |
|------|-------|
| Thin `cic truth` CLI | Present TruthReport |
| Package verify / FR-012 readiness consume report | Fail-closed external-use gate |
| Persist TruthReports | Optional store beside opportunity |

---

## 12. Final repository status

FR-014 **M0 accepted**, **M1 contracts complete**, **M2 technology validation complete**,
**M3 owner CLI / gates complete**.
Next: **M4** corpus-bounded broader claim kinds — **not started**.
