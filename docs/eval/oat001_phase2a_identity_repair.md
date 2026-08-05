# OAT-001 Phase 2A — Identity Repair Capability + Proposed Plans

**Status:** Phase 2A complete — **stop for owner approval**  
**Date:** 2026-08-05  
**Does not execute:** bulk identity repairs (2B), missing acquisitions (2C), duplicate confirmations (2D)

---

## 1. Executive summary

Phase 2A delivers a narrow owner-controlled identity-repair capability:

```text
cic opportunity repair-identity <opp_id> --title "…" --company "…" [--override] [--source-note "…"]
```

It updates only `Opportunity.identity.title` / `.company` (mutable projection) and appends a
`repair_identity` review-action audit entry. Immutable posting/JobAnalysis artefacts,
decisions, outcomes, pipeline status, and duplicate links are unchanged.

**No live Opportunity writes** were performed in 2A beyond capability implementation
and tests. Bulk repairs and the 8 FR-008 acquisitions await explicit owner approval of
the tables below.

---

## 2. Identity-repair architecture

| Rule | Behaviour |
|------|-----------|
| Authority | Explicit owner-supplied `--title` / `--company` only (no LLM, no raw-text parse) |
| Default | Fill **missing** fields only |
| Overwrite | Refused unless `--override` |
| Idempotent | Same values → no write, no extra audit entry |
| Audit | `review_actions` entry `action=repair_identity` with prior/new/source_note |
| Artefacts | Never modified (`posting.json` hash unchanged) |
| Fail closed | Unknown id; empty strings; neither field supplied; conflicting overwrite |

Service: `OpportunityService.repair_identity`  
CLI: `cic opportunity repair-identity`  
Action kind: `ReviewActionKind.repair_identity` (additive)

Distinct from `cic opportunity backfill-identity` (copies from posting.json fields only —
still correct for the 2 records that already have posting title/company, useless for the 14).

---

## 3. Files changed (2A)

| Path | Change |
|------|--------|
| `src/career_intelligence/opportunities/models.py` | `repair_identity` review action kind |
| `src/career_intelligence/opportunities/service.py` | `repair_identity` method |
| `src/career_intelligence/cli/main.py` | `cic opportunity repair-identity` |
| `tests/unit/opportunities/test_identity_repair.py` | New focused tests |

---

## 4. Tests

`tests/unit/opportunities/test_identity_repair.py` — fill missing; one field; refuse overwrite;
override; idempotent; unknown id; validation; CLI success/block.

Regression: `tests/unit/opportunities/` + `tests/functional/test_fr009_duplicate_review.py` →
**131 passed**.

---

## 5. Proposed 14-record repair table

Evidence: exact `content_fingerprint` match to numbered job file + posting `raw_text` title/company lines
(owner still supplies values explicitly — not auto-parsed by the service).

| Opportunity ID | Job file | Proposed title | Proposed company | Evidence | Duplicate cluster | Safe? | Proposed command |
|----------------|----------|----------------|------------------|----------|-------------------|-------|------------------|
| `opp_01KY8RFAH81M9V30ZVH9TM09T5` | `002_bluefin_…` | AI Systems Developer | Bluefin Resources Pty Limited | job+raw; decision=apply | Bluefin | Yes | `cic opportunity repair-identity opp_01KY8RFAH81M9V30ZVH9TM09T5 --title "AI Systems Developer" --company "Bluefin Resources Pty Limited" --source-note "manual_validation/jobs/002_bluefin_ai_systems_developer.txt"` |
| `opp_01KY8WWW3AK8KKXAKM5KRZ03VE` | `001_strong_…` | AI Engineer | Allura Partners | job+raw; sibling `opp_01KYP7Y6…` already complete | Allura | Yes | `… opp_01KY8WWW3AK8KKXAKM5KRZ03VE --title "AI Engineer" --company "Allura Partners" --source-note "manual_validation/jobs/001_strong_ai_engineer.txt"` |
| `opp_01KY8WXQ8HQ4J5G2XTM3XFHGEX` | `002_bluefin_…` | AI Systems Developer | Bluefin Resources Pty Limited | job+raw | Bluefin | Yes | same title/company as Bluefin row |
| `opp_01KY8WYE6RM54EYV8QT0YXHCQP` | `003_mid_role.txt` | Junior Software / DevOps Engineer | Jirotech Pty Ltd | job+raw | — | Yes | repair with those values + source-note job 003 |
| `opp_01KY8X103H78C9WXJ2B71KHXHG` | `004_associate_…` | Associate AI Product Manager | SEEK Limited | job+raw | — | Yes | … |
| `opp_01KY8X1S0BC20YEX2QDAGAKEEH` | `005_network_…` | Network Engineer- Automation & AI | Capgemini Australia Pty Ltd | job+raw (hyphen as in posting) | — | Yes | … |
| `opp_01KY8X38A0QEFV3PQCV7V68WSD` | `007_technology_…` | Technology and Automation Lead | Buildlab | job+raw | — | Yes | … |
| `opp_01KY8X3XQ5NP8JKTXEKQ1J8GR0` | `008_repurpose_…` | AI Adoption Specialist | REPURPOSE IT P/L | job+raw | — | Yes | … |
| `opp_01KY8X4NPVYNZ4W27ZN9MEDV3Q` | `009_forever_new_…` | Senior AI Automation Engineer – Digital | Forever New Clothing | job+raw (en-dash as in posting) | — | Yes | … |
| `opp_01KY8X5A6VFW3RK70WXNX0A36P` | `010_pisell_…` | AI Quality & Systems Reliability Engineer | Pisell | job+raw | — | Yes | … |
| `opp_01KY8X66C3NSYXJ4E2RNTMMKM5` | `011_officeworks_…` | AI Engineer | Officeworks | job+raw | — | Yes | … |
| `opp_01KY8X6V6N32558CDNXW0RXW7V` | `012_maincode_…` | AI Infrastructure Engineer | Maincode | job+raw; sibling `opp_01KY8ZDE…` complete | Maincode | Yes | … |
| `opp_01KY8X7SSERDT9BGAHQ71RF6F3` | `013_pay_com_au_…` | AI Automation Engineer | pay.com.au | job+raw; decision=**skip** | — | Yes (identity only) | … |
| `opp_01KY8YA5KWQWDFBEQ68N71PDEM` | `012_maincode_…` | AI Infrastructure Engineer | Maincode | job+raw | Maincode | Yes | … |

**Already complete (no repair):**

- `opp_01KYP7Y6R0X0V9F4V00SKZVKW6` — AI Engineer / Allura Partners  
- `opp_01KY8ZDEEHFN6CDPPTY2PNC9PS` — AI Infrastructure Engineer / Maincode  

**Ambiguous repairs:** none on fingerprint match. **Do not execute 2B until owner approves this table.**

---

## 6. Missing-job acquisition plan (Phase 2C — not executed)

Authoritative path:

```text
python scripts/run_fr008_workflow_manual.py start --source export \
  --job-file manual_validation/jobs/<file>.txt \
  --title "…" --company "…"
# then resume --decision apply|skip|defer when awaiting_owner
```

| Job | Title | Company | Title/company verified against |
|-----|-------|---------|--------------------------------|
| 006 | Senior AI Engineer | Kogan.com | live strategy `posting` + job file |
| 014 | AI Automation Engineer | Anton Murray Consulting | live strategy + job file |
| 015 | Graduate / Junior Full Stack Developer | Expedient Software | live strategy (short form of full posting title) |
| 016 | AI Engineer \| Contact Centre | Robert Half | live strategy |
| 017 | AI Engineer | Mars Recruitment | live strategy |
| 018 | AI Enablement Lead | Carlton Football Club | live strategy |
| 019 | AI Engineer | Redwolf + Rosch | live strategy |
| 020 | AI Engineer | Accenture | job file only (no live strategy JSON) |

Do **not** attach existing loose CV/CL by filename. After new `opp_*` IDs exist, regenerate
package / truth / CV / CL under those IDs if owner wants Opportunity-bound artefacts.

Before 2C writes: timestamped backup of `data/opportunities/` and relevant `data/workflow_runs/`.

---

## 7. Manual validation (2A capability — unit/CLI covered; live spot-check deferred to 2B)

Automated coverage for: fill; idempotent; overwrite block; override; posting unchanged;
decision/pipeline unchanged; show renders title/company.

Live single-record repair (owner-approved) is the first step of **Phase 2B**, not 2A.

---

## 8. Duplicate review outcome (2A)

No confirmations executed. Known clusters remain as Phase 1:

- Allura: `…WWW` ~ `…P7Y6` (prefer `…P7Y6` canonical after identity repair)
- Bluefin: `…RFA` (apply) ~ `…WXQ`
- Maincode: `…X6V` ~ `…YA5` ~ `…ZDE` (prefer `…ZDE` canonical)

Phase 2D: `python scripts/run_fr009_duplicate_review_manual.py candidates --opportunities data/opportunities`
then owner `DuplicateReviewService` confirmations.

---

## 9. Final counts (current live SoT — unchanged by 2A)

| Metric | Count |
|--------|------:|
| Numbered job files | 20 |
| Opportunity records | 16 |
| Unique roles in SoT (by fingerprint) | 12 |
| Identity-complete Opportunities | 2 |
| Identity-incomplete | 14 |
| Duplicate clusters (unconfirmed) | 3 |
| Missing numbered jobs | 8 |

**Expected after 2B+2C+2D (if approved):** 24 Opportunities; 20 unique roles; 24 identity-complete
(if all repairs applied); 3 confirmed duplicate groups.

---

## 10. Downstream artefacts requiring regeneration

After 2C acquisitions, for each new Opportunity: Opportunity-bound strategy is created by
FR-008; CV/CL/package/truth under that `opp_*` must be **newly generated** if needed.
Existing `career-documents/...` and `manual_validation/outputs/live/...` remain unbound
reference material only.

---

## 11. Rollback evidence

2A made **no SoT writes**. Capability is additive. Rollback of code = revert the listed
files. Future 2B/2C: restore timestamped `data/opportunities/` backup; drop new
`data/workflow_runs/wfr_*` for aborted acquisitions.

---

## 12. OAT-001 findings (to date)

1. Re-acquisition with `--title/--company` created duplicates instead of repairing identity.  
2. `backfill-identity` cannot help when posting fields are null; artefacts must stay immutable.  
3. Owner-supplied `repair-identity` is the safe repair path for the 14.  
4. Eight numbered jobs still lack Opportunities.  
5. Loose CV/CL must not be filename-attached.

---

## 13. Repository status after 2A

| Item | Status |
|------|--------|
| Identity repair capability | **Implemented + tested** |
| Bulk repairs | **Not started** — awaiting approval of §5 |
| Missing acquisitions | **Not started** — awaiting approval of §6 |
| Duplicate confirmations | **Not started** |
| FR-015 / FR-016 | Untouched / not started |

**STOP.** Approve §5 (and optionally §6) to proceed to Phase 2B / 2C.
