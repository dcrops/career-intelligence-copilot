# FR-019 M1 — Automatic Yahoo Mailbox Intake

**Status:** **GO** (proposed — pending owner acceptance of M1.1) — mailbox intake
live-validated; pre-M2 reliability closed in
[fr019_m1_1_reliability_hardening.md](fr019_m1_1_reliability_hardening.md)  
**Date:** 2026-08-11  
**Live close-out:** 2026-08-11 (Yahoo SEEK + LinkedIn dogfood)  
**M1.1:** [fr019_m1_1_reliability_hardening.md](fr019_m1_1_reliability_hardening.md)  
**Phase:** Horizon 1B — FR-019 Core Loop Operationalisation  
**Parent:** [fr019_core_loop_operationalisation.md](fr019_core_loop_operationalisation.md)  
**M0:** [fr019_m0_engineering_spike.md](fr019_m0_engineering_spike.md) (**Accepted / GO**)  
**Does not begin:** M2 `cic daily`, scheduling, recommend CLI, APPLY UX, submission
automation, Recruiter Intelligence.  
**M1 accepted:** **Proposed GO** after M1.1 live recovery (owner review).

---

## 1. Executive summary

M1 delivers automatic obtainment of job-alert messages from Yahoo Mail
(**`CIC Job Alerts`**) via IMAP, with email-level idempotency, and hands MIME to
**frozen FR-018** (`opportunity_sources_from_email_file` → `ThinDiscoveryIngress`).

**Live evidence (2026-08-11):**

| Layer | Result |
|-------|--------|
| Yahoo IMAP + app password | Proven after Norton inbound IMAP scan disabled |
| SEEK alert (manual move into folder) | 5/5 jobs → workflow `awaiting_owner` |
| LinkedIn alert (natural Yahoo filter) | 6 jobs → 3 `awaiting_owner`, 3 `failed` at **assess** |
| Email ledger idempotency | SEEK + LinkedIn both skipped on re-run |
| Authoritative JD content | **All 11** jobs show `enriched_from_job_url` — **no card-only analysis** |
| Downstream failures | Assessment **validation** fail-closed (not acquisition/content) |

**Verdict:** **GO** for M1 mailbox intake once owner accepts M1.1 reliability
hardening ([M1.1](fr019_m1_1_reliability_hardening.md)). Do **not** start M2
`cic daily` until separately authorised. Mailbox intake itself is not the
failure mode; assess retry + `retry-run` close the prior CONDITIONAL GO debt.

---

## 2. Architecture implemented

```text
Yahoo IMAP (CIC Job Alerts)  OR  --drop-folder *.eml
        ↓
MailboxIntakeService (+ EmailIntakeLedger)
        ↓
temp .eml materialisation
        ↓
opportunity_sources_from_email_file   (FR-018)
        ↓
ThinDiscoveryIngress(fail_closed_on_card_only=True)
        ↓
EmailAcquisitionAdapter (+ URL enrich)
        ↓
ApplicationWorkflowRunner (FR-008) when content sufficient
```

CLI: `cic opportunity mailbox-intake`

---

## 3. Components

### New (`career_intelligence.mailbox`)

| Module | Role |
|--------|------|
| `config.py` | `load_mailbox_config` — file + env (env wins); redaction |
| `ledger.py` | Email-level processed JSON ledger |
| `imap_client.py` | Yahoo IMAP TLS + `BODY.PEEK[]` |
| `drop_folder.py` | `.eml` fallback loader |
| `intake.py` | Orchestration → FR-018 |
| `models.py` / `errors.py` | Typed messages and errors |

### Additive FR-018 (not a reopen)

| Change | Why |
|--------|-----|
| `EmailAcquisitionAdapter.fail_closed_on_card_only` (default **False**) | Opt-in fail-closed for M1 without changing frozen discover-email default |
| `ThinDiscoveryIngress.fail_closed_on_card_only` | Pass-through for mailbox path |

---

## 4. Yahoo IMAP behaviour

| Setting | Value |
|---------|--------|
| Host | `imap.mail.yahoo.com` |
| Port | `993` TLS (OS trust store / truststore; **never** disable verify) |
| Auth | App password (`CIC_MAILBOX_APP_PASSWORD`) |
| Folder | Default `CIC Job Alerts` |
| Fetch | `UID SEARCH ALL` + `UID FETCH … BODY.PEEK[]` |
| Mark seen | Default **false** (opt-in `CIC_MAILBOX_MARK_SEEN`) |
| Delete/move | **Never** |

---

## 5. Email ledger

Path: `data/mailbox_intake/processed.json` (gitignored).

Keys: Message-ID (primary), folder+uidvalidity+uid (secondary), content hash for
drop-folder edge cases.

**Processed when:** parse+ingress hand-off completes (including all jobs failed),
or parse fails closed (unsupported/empty — recorded so we do not loop forever).  
**Not recorded** on unexpected crash-class errors before hand-off (retryable).

Job-level identity remains FR-018/FR-009.

### Live ledger evidence

| Message | Outcome summary | Re-run |
|---------|-----------------|--------|
| SEEK `<9f6267b8-…@noti-x.seek.com.au>` | `acquired=5 skipped=0 failed=0` | skipped (ledger) |
| LinkedIn `<947877476.…@…linkedin.com>` | `acquired=3 skipped=0 failed=3` | skipped (ledger) |

Second full mailbox run: `processed=0 skipped=2 ledger=2 failed=0`.

**Semantics (intentional M1):** email-level “processed” means MIME was obtained,
parsed, decomposed, and handed to FR-018 — **not** that every child job reached
Opportunity SoT. Child failures remain as workflow checkpoints (see §14).

---

## 6. Secrets

| Path | Git |
|------|-----|
| `config/local_secrets.env.example` | Yes |
| `config/local_secrets.env` | **No** |

Env `CIC_MAILBOX_*` overrides file. Password never in `repr` / redacted in IMAP errors.

---

## 7. Content-sufficiency / fail-closed

Mailbox intake sets `fail_closed_on_card_only=True`.

When enrich is attempted and does not yield preferred JD body, and email lacks JD
signals → `AcquisitionError` (“Insufficient authoritative…”) → discovery item
`failed` / `malformed_content` — **runner not invoked**.

Default `discover-email` unchanged (fail-soft).

### Live fail-closed pressure test

| Question | Evidence |
|----------|----------|
| Did any SEEK job reach Job Analysis on card-only content? | **No** — all five have `enriched_from_job_url` |
| Did any LinkedIn job reach Job Analysis on card-only content? | **No** — all six have `enriched_from_job_url` |
| Did failed LinkedIn jobs have adequate source content? | **Yes** — analyse succeeded; assess validation failed |
| Did any job get discovery `ACQUIRED` with insufficient JD? | **No** among live 11 |
| Is `ACQUIRED` ambiguous for owners? | **Finding** — see §13 |

---

## 8. Testing evidence

| Suite | Result |
|-------|--------|
| `tests/unit/mailbox/` | Pass (pre-live) |
| `tests/unit/discovery/test_m4_email_ingress.py` | Pass (FR-018 fail-soft preserved) |
| Full regression | Green at M1 implementation close-out (**1585**) |
| Live Yahoo | Owner machine 2026-08-11 (this report) |

No live Yahoo credentials in CI.

---

## 9. Owner live smoke checklist

1. Yahoo: enable IMAP; create app password for CIC.  
2. Create folder **`CIC Job Alerts`**; filter SEEK / LinkedIn / Indeed alerts into it.  
3. **Norton (Windows):** if IMAP TLS fails with untrusted root, disable **only**
   Norton → Email Protection → **Scan inbound emails (POP3, IMAP4)**. Keep AV and
   other Email Protection on. Do **not** disable CIC certificate verification.  
4. Copy `config/local_secrets.env.example` → `config/local_secrets.env`; fill
   `CIC_MAILBOX_USER` and `CIC_MAILBOX_APP_PASSWORD` **locally** (never paste into chat).  
5. Dry-run without IMAP:  
   `cic opportunity mailbox-intake --drop-folder tests/fixtures/discovery --offline-fixtures`  
6. Live:  
   `cic opportunity mailbox-intake`  
   (set `OPENAI_API_KEY` for live analysis; or `--offline-fixtures` only if markers present).  
7. Re-run: ledger skips; job definite skip where applicable.  
8. Indeed: expect fail-closed when enrich blocked and card-only (delivery still pending).  
9. Confirm password absent from logs and `git status`.

---

## 10. Live environment — Norton / TLS

**Finding (operational prerequisite):** Norton Email Protection inbound POP3/IMAP
scanning presents `Norton Web/Mail Shield Untrusted Root`. CIC correctly rejects
the intercepted TLS chain (verification remains enabled).

With **only** inbound email scanning OFF:

```text
DEFAULT_OK TLSv1.3
TRUSTSTORE_OK TLSv1.3
IMAP_TRUSTSTORE_OK
IMAP_DEFAULT_OK
PRODUCTION_IMAP_SSL_OK
```

**Do not:** install arbitrary roots, `CERT_NONE`, or `verify=False`.

---

## 11. Live mailbox / provider evidence

### Yahoo filter

LinkedIn Job Alert arrived naturally and was routed by Yahoo filter into
`CIC Job Alerts` without manual `.eml` export or folder move. That is production
routing proof. SEEK was manually moved for first IMAP smoke; SEEK Yahoo filter
remains configured — do not hold M1 open solely for a second natural SEEK delivery.

### SEEK live (5 jobs)

| # | Company | Role | URL | Enrich | Useful size | Workflow | Analysis | Assess |
|---|---------|------|-----|--------|-------------|----------|----------|--------|
| 0 | Cognizant | Data Scientist(Agent Evaluations) | seek `/93874085` | `enriched_from_job_url` | ~5777 | `awaiting_owner` | Yes | mixed |
| 1 | Cognizant | AI Security Architect | seek `/93874091` | yes | ~6043 | `awaiting_owner` | Yes | mixed |
| 2 | Intelligen Pty Ltd | AI Engineer | seek `/93838543` | yes | ~4963 | `awaiting_owner` | Yes | weak |
| 3 | Lookahead | Senior AI Engineer (contract) | seek `/93660152` | yes | ~1661 | `awaiting_owner` | Yes | mixed |
| 4 | Fyndr Group | Principal AI Engineer | seek `/93795958` | yes | ~3532 | `awaiting_owner` | Yes | mixed |

All five: email discovery → canonical SEEK URL → URL enrich → substantive JD →
analyse → assess → persist → owner review. Content class: **A (full/authoritative)**.

### LinkedIn live (6 jobs)

| # | Company / title (as acquired) | URL | Enrich | Useful size | Workflow | Failure |
|---|-------------------------------|-----|--------|-------------|----------|---------|
| 0 | Leidos Australia / Software Engineer \| 12-month FTC | `/4433838731` | yes | ~9625 | `awaiting_owner` | — |
| 1 | Quantexa / Data Engineer | `/4442519428` | yes | ~5956 | `awaiting_owner` | — |
| 2 | MYOB / AI Engineering Manager | `/4406101747` | yes | ~6629 | **failed @ assess** | strong vs material gap |
| 3 | title/company metadata swapped: HUB24 Limited / Melbourne, VIC | `/4414727674` | yes | ~4673 | **failed @ assess** | Node.js ≠ technologies[1] HTML |
| 4 | Maincode / Distribution Engineer (Matilda) | `/4402887888` | yes | ~1515 | `awaiting_owner` | — |
| 5 | Maincode / Product Engineer (UI / Frontend) | `/4392878371` | yes | ~4971 | **failed @ assess** | Python ≠ technologies[0] TypeScript |

All six: `enriched_from_job_url`; analyse completed before any failure. **No silent
card-only regression** vs FR-018 LinkedIn lesson.

### Indeed

Alerts configured (active/daily); owner not receiving delivery at close-out.
New `ai engineer` / Melbourne test alert created; **email delivery unproven**.
External-source limitation — **not** an M1 blocker if multi-provider delivery is
not required by M1 criteria. No Indeed sender filter invented without evidence.

---

## 12. Content-sufficiency & application-generation readiness

Semantic classes used: **A** full/authoritative advertisement; **B** partial but
substantive; **C** thin/card-only; **D** unavailable. Length alone was not used.

| Provider | Job | Class | JA readiness | Assessment readiness | CV tailoring | Cover letter | Notes |
|----------|-----|-------|--------------|----------------------|--------------|--------------|-------|
| SEEK | Cognizant Data Scientist | A | READY | READY | READY | READY | Enriched SEEK page |
| SEEK | Cognizant AI Security Architect | A | READY | READY | READY | READY | |
| SEEK | Intelligen AI Engineer | A | READY | READY | READY | READY | |
| SEEK | Lookahead Senior AI Engineer | A | READY | READY | **PARTIAL** | **PARTIAL** | Shorter (~1.6k) but real role/about-you; owner review for depth |
| SEEK | Fyndr Principal AI Engineer | A | READY | READY | READY | READY | |
| LI | Leidos Software Engineer | A | READY | READY | READY | READY | |
| LI | Quantexa Data Engineer | A | READY | READY | READY | READY | Full JD; curly-apostrophe headings |
| LI | MYOB AI Eng Manager | A | READY | READY (content) | READY* | READY* | *Blocked by assess validation, not thin content |
| LI | HUB24 (role in body) | A | READY | READY (content) | READY* | READY* | Metadata title/company swap; body OK |
| LI | Maincode Distribution (Matilda) | A/B | READY | READY | **PARTIAL** | **PARTIAL** | Shorter growth/systems JD; enough for posture, thin for fine claims |
| LI | Maincode Product Engineer UI | A | READY | READY (content) | READY* | READY* | *Assess validation blocked persist |

\*Ready on **source evidence**; not safe to claim a completed assessment package
until assess succeeds.

**Thin/card-only reaching analysis:** **None** in this live set.

---

## 13. Meaning of discovery `ACQUIRED`

Implementation (`ThinDiscoveryIngress`): status **`acquired`** is returned only when
the FR-008 runner allocates an **`opportunity_id`** (persist path) and the run is not
a failed terminal without id. Live successful jobs show workflow
`control.status=awaiting_owner`.

Therefore CLI **`ACQUIRED` ≠ “raw content obtained”**. It means approximately:

> content acquired **and** Horizon 1A workflow progressed far enough to persist an
> Opportunity (typically through owner-review interrupt).

Jobs that fail at **assess** after successful analyse are reported as discovery
**`failed` / `runner_failure`**, even though authoritative JD + JobAnalysis exist
on the checkpoint. **Finding:** owner-facing vocabulary is easy to misread; do
**not** rename in this task — record for a later UX/clarity decision.

---

## 14. Downstream failure triage (3 LinkedIn)

All three: **source content adequate**; **Job Analysis succeeded**; failure at
**Opportunity Assessment validation**; `last_error.recoverable=False`;
**`retry` field null**; **no** `retry_scheduled` / `retry_exhausted` events;
**one** assess attempt each; **`opportunity_id` unset** (pre-persist).

| Job | Error | Classifications |
|-----|-------|-----------------|
| MYOB AI Engineering Manager | `technical judgment 'strong'` inconsistent with material gap/conflict | **EXPECTED FAIL-CLOSED BEHAVIOUR**; **LLM STRUCTURED-OUTPUT / RELIABILITY ISSUE**; **RETRY-POLICY GAP** (validation treated unrecoverable → no re-sample) |
| HUB24 | evidence tech name `Node.js` ≠ `technologies[1].name` `HTML` | **EXPECTED FAIL-CLOSED**; **LLM STRUCTURED-OUTPUT** (evidence index/name mismatch); **RETRY-POLICY GAP** |
| Maincode Product Engineer UI | evidence `Python` ≠ `technologies[0].name` `TypeScript` | Same as HUB24 |

**Not** poor-fit rejection: a coherent weak/mixed/reject assessment would have
persisted. These are **inconsistent or mis-indexed LLM assessment outputs**
correctly refused by validators.

**Do not weaken validators** to make them pass.

### Retry audit

FR-008 retries apply to `analyse` / `assess` only when `NodeFailure.recoverable=True`
(transient heuristics). `OpportunityAssessmentValidationError` is classified
**unrecoverable** via `classify_exception` (no transient markers).  
Mailbox composition does **not** bypass retry — retry correctly did not run under
the **current accepted contract**. Whether validation failures **should** be
retryable is a separate policy question (gap for owner approval — no fix here).

### Failed-job recovery audit

| Mechanism | Status |
|-----------|--------|
| Email re-intake (default) | **Blocked** by ledger (by design) |
| `mailbox-intake --force` | Re-processes email; blunt (re-runs all jobs) |
| `cic opportunity discover <url>` | **Viable** per-job re-acquire (manual) |
| `cic agent resume` on failed workflow | **Not available** for `status=failed` |
| Checkpoint on disk | **Yes** — acquisition + job_analysis retained under `data/workflow_runs/` |
| Discovery outcome `workflow_run_id` on pre-persist fail | **Often omitted** (`_failed()` helper) — operability friction |

**Finding (bounded pre-M2):** failed children are not permanently deleted, but
**first-class recovery is manual/awkward**. Before automating daily intake, owner
should approve either: (a) assess validation retries for LLM reliability, and/or
(b) an explicit failed-job retry/re-ingress path that does not depend on forgetting
the email ledger.

---

## 15. Acceptance criteria matrix (post live audit)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Connect Yahoo IMAP | **PASS** | Live intake after Norton fix |
| 2 | Target `CIC Job Alerts` | **PASS** | Config + live folder |
| 3 | Full MIME | **PASS** | BODY.PEEK + live parse |
| 4 | Reuse FR-018 parse | **PASS** | SEEK/LI alerts expanded |
| 5 | Reuse FR-018 ingress | **PASS** | ThinDiscoveryIngress |
| 6 | Email idempotency | **PASS** | ledger skip both messages |
| 7 | Separate from job dedupe | **PASS** | design + live |
| 8 | No credentials in Git/logs | **PASS** | gitignored secrets; redaction |
| 9 | Tests without live Yahoo | **PASS** | unit/mailbox |
| 10 | Live Yahoo smoke | **PASS** | SEEK + LinkedIn |
| 11 | SEEK via mailbox | **PASS** | 5/5 acquired path |
| 12 | LinkedIn via mailbox | **PASS** (intake) / **PARTIAL** (3/6 assess) | Natural filter + enrich; assess reliability separate |
| 13 | Insufficient content fail-closed | **PASS** (live: enrich succeeded; unit covers fail path) | No card-only analysis observed |
| 14 | No manual `.eml` for happy path | **PASS** | LinkedIn natural; SEEK manual-move only for first smoke |
| 15 | FR-008–018 intact | **PASS** | fail-soft discover-email default preserved |
| — | Content sufficiency for JA/CV/CL | **PASS** for acquired set; failed set content-ready but assess-blocked | §12 |
| — | Failed-job recovery ergonomics | **PARTIAL** | §14 |
| — | Indeed live delivery | **NOT APPLICABLE / pending** | External |

---

## 16. GO / NO-GO recommendation

### M1: **GO** (after M1.1 acceptance)

Mailbox intake criteria are met. Content sufficiency for live SEEK/LinkedIn
acquisition is proven. Downstream assess failures are **separable** from M1
transport. M1.1 delivers selective assess retry + `cic opportunity retry-run`
with live recovery of all three LinkedIn failures —
[fr019_m1_1_reliability_hardening.md](fr019_m1_1_reliability_hardening.md).

### Should M2 `cic daily` start immediately?

**No** until owner authorises M2 as a separate task after accepting M1 + M1.1.

### LinkedIn metadata (tracked debt)

HUB24-style title/company swap remains a **NON-BLOCKING** data-quality defect —
see M1.1 Gate C. Not fixed in M1.1.

---

## 17. Learning / interview takeaways

1. **Transport success ≠ content success** — IMAP and URL fetch succeeding does
   not automatically mean analysis/assessment completed.  
2. **Content sufficiency** — CV/cover letter need substantive employer
   requirements, not alert teasers. Today’s enrich path supplied that.  
3. **Provenance** — `enriched_from_job_url` vs email-card warnings must remain
   visible so owners never tailor from teasers by mistake.  
4. **Fail closed** — refusing inconsistent “strong + material gap” assessments is
   safer than shipping a polished wrong package.  
5. **Layered idempotency** — marking an email processed can be correct while child
   jobs fail — **if** children remain recoverable. Recovery ergonomics are the
   open debt.  
6. **Validation ≠ “broken AI”** — today’s failures show safety mechanisms catching
   bad structured output.  
7. **Operationalisation** — real Yahoo/LinkedIn dogfood exposed assessment
   reliability under live load that 1,585 automated tests did not.

---

## 18. Repository status

| Item | Status |
|------|--------|
| FR-019 M0 | Complete — GO |
| FR-019 M1 | **GO** (proposed with M1.1) — live-validated |
| FR-019 M1.1 | **Proposed GO** — [fr019_m1_1_reliability_hardening.md](fr019_m1_1_reliability_hardening.md) |
| M2–M6 | Not started |
| FR-019 accepted | **No** (capability still in progress) |
| Code fixes from M1 audit | Deferred to M1.1 (completed) |

**Next engineering action (owner-approved):** choose smallest pre-M2 fix from §16,
implement in a dedicated task, revalidate LinkedIn assess path — **then** M2.
