# FR-014 M3 — Owner CLI and External-Use Gates

**Date:** 2026-08-05  
**Status:** Complete (M3)  
**Architecture:** [ADR-006](../adr/006_recruiter_document_truth_validation.md) (unchanged)  
**Preceding:** [M2 technology validation](fr014_m2_technology_validation.md)  
**Next:** M4 corpus-bounded broader claim kinds (not started)

---

## 1. Executive summary

M3 makes truth validation operational for the owner:

- Thin `cic truth` CLI (`validate`, `show`, `validate-package`)
- Sidecar TruthReport persistence with Markdown content hashing
- Package-level external-use readiness (CV + cover letter)
- Fail-closed submission protection (FR-012 paths)
- Owner correction workflow: edit Markdown → revalidate → submit  
  (no rewrite, no auto-correction)

Claim kinds remain M2 technology/framework scope only.

---

## 2. CLI design

| Command | Purpose |
|---------|---------|
| `cic truth validate <markdown_path>` | Validate authoritative Markdown; optional persist |
| `cic truth show <report_path>` | Display a persisted TruthReport |
| `cic truth validate-package <opportunity_id>` | Validate CV + cover letter; write current reports |

Owner-visible fields: document path, outcome, coverage, blocking / review-required /
supported findings, exact claim text, technology, evidence status, class, strength,
detection certainty. Detector internals are not exposed.

`--check-only` on `validate-package` evaluates freshness of stored reports without
re-detecting (stale-hash gate).

---

## 3. Package integration

FR-010 `ApplicationPackageManifest` is unchanged (`extra=forbid`). Truth metadata
lives in sidecars under `data/truth_reports/{opportunity_id}/`:

| Artefact | Role |
|----------|------|
| `{report_id}.json` | Immutable history |
| `current_cv_markdown.json` | Latest CV report pointer |
| `current_cover_letter_markdown.json` | Latest cover-letter report pointer |

Package questions answered:

| Question | Mechanism |
|----------|-----------|
| Which Markdown files were validated? | Report `artefact.path` + kind |
| Which report belongs to each document? | `current_{kind}.json` |
| When did validation occur? | Report timestamp (audit only) |
| Do current Markdown bytes still match? | SHA-256 content fingerprint |
| Is external use allowed? | `evaluate_package_truth` / `require_package_external_use` |

`cic package verify` also evaluates the truth gate (BLOCKED without fresh passing reports).

---

## 4. Freshness / hash design

- Fingerprint = SHA-256 of full UTF-8 Markdown bytes (`markdown_content_hash`)
- Freshness = stored fingerprint == current file hash
- Timestamps alone never authorize external use
- A report for stale Markdown never authorizes submission

---

## 5. External-use gate behaviour

External use is allowed only when **every** in-scope recruiter-facing Markdown document
has a current report that:

| Condition | Fail-closed if violated |
|-----------|-------------------------|
| outcome ∈ {pass, warning} | fail / review_required |
| coverage complete | incomplete |
| detection performed | false |
| validation performed | false |
| no blocking findings | any blocking |
| content hash matches Markdown | stale |
| report present | missing |

Review-required findings follow ADR-006 severity policy (not silently downgraded).

---

## 6. Submission integration

`SubmissionOrchestrator` defaults `enable_truth_gate=True`:

- `check_readiness` soft-blocks on missing/stale/failing truth
- `submit` / manual completion hard-raise `SubmissionGateError` via
  `require_package_external_use`
- Owner approval remains mandatory
- `SubmissionAttempt` success remains separate from truth validation and FR-013 status
- Successful technical upload cannot bypass the truth gate

Legacy FR-012 unit helpers set `enable_truth_gate=False` only where they intentionally
isolate pre-M3 submission mechanics; production CLI keeps the gate on.

---

## 7. Owner correction workflow

```
Generate → Truth FAIL → Owner reviews exact finding
  → Owner edits Markdown → Render-only → Revalidate
  → Truth PASS → Owner verifies PDF → Submit (manual / assisted)
```

Validator never repairs or rewrites the document.

---

## 8. Redwolf before / after

**Before:**

> Roles centred on Python, TypeScript, and Vue are where I do my best engineering work.

| Tech | Status |
|------|--------|
| Python | supported |
| TypeScript | unsupported **blocking** |
| Vue | unsupported **blocking** |
| outcome | **fail** |

**After owner correction** (e.g. Python capability + employer-context TypeScript/Vue):

| Statement | Class | Result |
|-----------|-------|--------|
| “I have experience with Python…” | A | supported |
| “The role uses TypeScript and Vue.” | B | not_applicable |
| outcome | — | **pass** |

---

## 9. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/truth_validation/` (incl. M3 gates + CLI) | passed |
| `tests/unit/submission/` + CLI (truth seeded) | passed |
| `tests/unit/application_package/test_cli.py` (verify + truth) | passed |
| `tests/functional/test_fr012_submission.py` | passed |
| `tests/functional/test_fr014_m2_truth_validation.py` | passed |
| Focused package/submission/truth regression | **150 passed** |

---

## 10. Manual validation

```bash
python scripts/run_fr014_m3_manual.py
```

**RESULT: PASS** — Redwolf FAIL; corrected PASS; stale blocks; package FAIL on
one bad document; submission Not Ready then Ready after revalidate.
Workspace: `data/_fr014_m3_manual/`.

---

## 11. Technical debt

| Item | Notes |
|------|-------|
| WeasyPrint optional stub in tests | Autouse stub when WeasyPrint missing; real PDF tests still need the package |
| Manifest not extended | Sidecars avoid FR-010 redesign; cross-linking is by opportunity_id + kind |
| Claim kinds still technology-only | M4 |
| Advisory generate-time gate | Dual-gate “after generate” remains optional advisory; authoritative gate is M3 |

---

## 12. Final repository status

FR-014 **M0–M3 complete**. Next: **M4** expanded claim kinds —
[eval/fr014_m4_claim_validation.md](fr014_m4_claim_validation.md) (**complete**);
FR-014 [acceptance freeze](fr014_recruiter_document_truth_validation.md).
Do not begin M4 without an explicit owner request.
