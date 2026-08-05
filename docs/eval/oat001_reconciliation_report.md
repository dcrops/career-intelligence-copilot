# OAT-001 — Opportunity Reconciliation Final Report

**Status:** Phase 2B + 2C + 2D **complete**  
**Date:** 2026-08-05  
**Backup:** `data/_oat001_backup_20260805T170854Z/`  
**Does not include:** BOPA / FR-015 operational testing

---

## 1. Executive summary

OAT-001 Phase 2 reconciled the live Opportunity corpus with the 20 numbered job files.

| Phase | Result |
|-------|--------|
| 2A | Identity-repair capability (accepted earlier) |
| 2B | **14** owner-supplied identity repairs in 4 validated batches → **16/16** identity-complete |
| 2C | **8** FR-008 acquisitions in 4 batches → **24** Opportunities, all identity-complete |
| 2D | **3** duplicate groups confirmed (Allura, Bluefin, Maincode); **0** unresolved candidates |

All pre-existing Opportunity IDs were preserved. Decisions, pipeline status, and prior review history on existing records were not rewritten by repairs (only additive `repair_identity` audit entries). Immutable `posting.json` artefacts were not modified.

---

## 2. Before vs after

| Metric | Before OAT-001 Phase 2 | After Phase 2D |
|--------|------------------------:|---------------:|
| Numbered job files (`001`–`020`) | 20 | 20 |
| Opportunity records | 16 | **24** |
| Unique posting fingerprints | 12 | **20** |
| Identity-complete Opportunities | 2 | **24** |
| Identity-incomplete | 14 | **0** |
| Missing numbered jobs (no Opportunity) | 8 | **0** |
| Unresolved duplicate candidates | 5 | **0** |
| Confirmed duplicate groups | 0 | **3** |
| Confirmed duplicate members | 0 | **4** |

---

## 3. Phase 2B — identity repairs

Executed in 4 batches via `cic opportunity repair-identity` (owner-supplied title/company; `source_note` = job path).

After each batch: count unchanged at 16 until complete; IDs unchanged; posting hashes unchanged; decisions/status unchanged; `cic`-equivalent show fields verified; identity_complete progressed 2→5→9→13→16.

All 14 incomplete records repaired (see Phase 2A table). Example audit: `review_actions` entry `repair_identity` with prior/new/source_note.

---

## 4. Phase 2C — missing Opportunity acquisition

FR-008 path: `run_fr008_workflow_manual.py start --source export --title --company` then `resume --decision apply`.

| Job | New Opportunity ID | Workflow run | Identity |
|-----|--------------------|--------------|----------|
| 006 Kogan | `opp_01KZ8C6365GD9GMFSGGD087R7X` | `wfr_01KZ8C53466T9YR1CQET4CHPTV` | Senior AI Engineer / Kogan.com |
| 014 Anton | `opp_01KZ8C7E1Z5Z4NHAHBK8QAT170` | `wfr_01KZ8C678HH81NHHPKE1CBE276` | AI Automation Engineer / Anton Murray Consulting |
| 015 Expedient | `opp_01KZ8C95JX2R20YWFDYWZZ5XYP` | `wfr_01KZ8C7K5CKB186XPPSFMSG696` | Graduate / Junior Full Stack Developer / Expedient Software |
| 016 Robert Half | `opp_01KZ8CARK0521JJ56PBS6V94GP` | `wfr_01KZ8C99VBR7NVX6CQC29JQ7YX` | AI Engineer \| Contact Centre / Robert Half |
| 017 Mars | `opp_01KZ8CBWNCXWQF97WKD6MCEFG7` | `wfr_01KZ8CAWRGFG5TWW1WBW315BWV` | AI Engineer / Mars Recruitment |
| 018 Carlton | `opp_01KZ8CCQZTVNN2JKF91P1FANT2` | `wfr_01KZ8CC0QCRX835RCP2840YW9T` | AI Enablement Lead / Carlton Football Club |
| 019 Redwolf | `opp_01KZ8CEJANPX26DWEKQNF7BWH9` | `wfr_01KZ8CCW8E32DKCQFX9HYTH02B` | AI Engineer / Redwolf + Rosch |
| 020 Accenture | `opp_01KZ8CFRVDMSA5HWVTNXY6KW82` | `wfr_01KZ8CEPH1DENJ87ZRD27BQM7R` | AI Engineer / Accenture |

Evidence: `data/_oat001_phase2c_runs/summary.json`.  
Prior 16 IDs remained a subset after every batch.

---

## 5. Phase 2D — duplicate review

Owner confirmations via `DuplicateReviewService.confirm_duplicate` (link, never merge):

| Cluster | Canonical | Duplicate member(s) |
|---------|-----------|---------------------|
| Bluefin | `opp_01KY8RFAH81M9V30ZVH9TM09T5` (apply) | `opp_01KY8WXQ8HQ4J5G2XTM3XFHGEX` |
| Allura | `opp_01KYP7Y6R0X0V9F4V00SKZVKW6` (apply) | `opp_01KY8WWW3AK8KKXAKM5KRZ03VE` |
| Maincode | `opp_01KY8ZDEEHFN6CDPPTY2PNC9PS` | `opp_01KY8X6V6N32558CDNXW0RXW7V`, `opp_01KY8YA5KWQWDFBEQ68N71PDEM` |

Post-check: `candidates --opportunities data/opportunities` → **0 unresolved**, **3 confirmed groups**.

---

## 6. Downstream artefacts requiring regeneration

Loose `manual_validation/outputs/live/*.json` and `career-documents/cv|cover-letters/generated/*` for jobs 006 / 014–020 remain **unbound** to the new Opportunity IDs.

For Opportunity-bound packages (when the owner needs them):

| New opp | Suggested next work |
|---------|---------------------|
| Eight new apply Opportunities above | `cic preparation` / package / truth under each new `opp_*` — **do not** filename-attach legacy CV/CL |
| Existing 16 | Artefacts already under `data/opportunities/artifacts/<opp_*>/`; identity now displayable for queue/compare |

`data/application_packages/` still has no live packages beyond README — package generation was out of OAT-001 scope.

**BOPA testing:** not started (per owner instruction).

---

## 7. Rollback

Restore from `data/_oat001_backup_20260805T170854Z/`:

1. Stop writers.  
2. Replace `data/opportunities/index.yaml` and `data/opportunities/artifacts/` from the backup.  
3. Optionally remove new workflow runs `wfr_01KZ8C*` under `data/workflow_runs/` listed in §4.  
4. Do **not** delete the eight new Opportunities casually if only undoing repairs — prefer restore of the full backup snapshot.

---

## 8. OAT-001 findings

1. Owner-supplied `repair-identity` successfully closed the posting-null identity gap without mutating artefacts.  
2. FR-008 acquisition with explicit `--title` / `--company` produces identity-complete records.  
3. Earlier re-acquisitions correctly remain as linked duplicates (not merges).  
4. All 20 numbered jobs now have ≥1 Opportunity; unique fingerprint count = 20.  
5. Corpus is ready for later operational trials (including BOPA) once the owner requests them.

---

## 9. Final repository status

| Item | Status |
|------|--------|
| Numbered job files | 20 |
| Opportunity records | **24** |
| Identity-complete | **24** |
| Missing numbered jobs | **0** |
| Confirmed duplicate groups | **3** |
| Unresolved duplicate candidates | **0** |
| BOPA testing | **Not started** |
| FR-016 | Not started |
