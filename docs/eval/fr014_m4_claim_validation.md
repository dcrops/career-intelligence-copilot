# FR-014 M4 — Expanded Deterministic Claim Validation

**Date:** 2026-08-05  
**Status:** Complete (M4) — FR-014 close-out  
**Architecture:** [ADR-006](../adr/006_recruiter_document_truth_validation.md) (unchanged)  
**Preceding:** [M3 owner CLI / gates](fr014_m3_owner_workflow.md)  
**Acceptance:** [fr014_recruiter_document_truth_validation.md](fr014_recruiter_document_truth_validation.md) (frozen)

---

## 1. Executive summary

M4 extends deterministic validation to objectively verifiable claim kinds that the
Career Profile can authorize:

| Kind | Behaviour |
|------|-----------|
| Employment honesty | Commercial AI / commercial software / independent engineering |
| Certification | Profile certifications only |
| Duration | Years only when `supported_years` is computable from dates |
| Project delivery | Named project / delivery objects with catalogue evidence |
| Domain | Profile domain skills / project demonstrates |

Not a general NL fact checker. Soft skills, motivation, aspirations, and subjective
quality statements remain out of scope. Technology / Redwolf regression retained.

---

## 2. New claim types

| Claim | Supported when | Fail-closed when |
|-------|----------------|------------------|
| Commercial AI engineering | Employment entry marked AI + `kind=employment` | Independent-only or no AI commercial evidence |
| Commercial software engineering | Commercial engineering/software employment | No commercial software evidence |
| Independent engineering | `independent_engineering` experience | Claimed without that kind |
| Certification | Matching profile certification | Absent from catalogue |
| Years of experience | Claimed years ≤ catalogue `supported_years` (+0.5 tolerance) | Overclaim → blocking; unknown tenure → review_required |
| Delivery (“I built…”) | Named project / delivery object in catalogue | Unresolved object → review_required; certain miss → blocking |
| Domain | Domain skill / demonstrates entry | Unsupported domain → blocking |

---

## 3. Validation architecture

Unchanged pipeline:

```
CareerProfile → CandidateEvidenceCatalogue
             → Claim Detection (technology + extended)
             → Deterministic Validator
             → TruthReport
             → Package / submission gates (M3)
```

Extensions only:

- Catalogue employment markers, certs, domains, project delivery, `supported_years`
- `extended_claims.py` detectors
- Technology lexicon restricted to `claim_kinds` containing `technology`
- `VALIDATOR_VERSION = fr014-m4-deterministic-1`

---

## 4. Manual validation

```bash
python scripts/run_fr014_m4_manual.py
```

**RESULT: PASS** — commercial AI fail; commercial software pass; independent pass;
cert present/absent; years supported/overclaim/ambiguous; delivery supported/unresolved;
domain supported/unsupported; Redwolf technology fail.

---

## 5. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/truth_validation/` (M1–M4) | passed |
| `tests/functional/test_fr014_m4_claim_validation.py` | passed |
| Focused M4 + prior FR-014 functional | **45+ passed** |
| FR-010/012 CLI regression sample | passed |

---

## 6. Out of scope (held)

Soft skills · personality · motivation · aspirations · opinions · future intentions ·
subjective quality · education (no profile education field) · identity/link checking ·
LLM judgement · rewriting.

---

## 7. Final M4 status

FR-014 **M0–M4 complete**. See acceptance freeze.
