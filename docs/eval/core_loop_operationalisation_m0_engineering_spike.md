# FR-019 M0 — Core Loop Operationalisation Engineering Spike

**Status:** **Complete — Accepted / GO** (owner 2026-08-11)  
**FR:** [FR-019 Core Loop Operationalisation](fr019_core_loop_operationalisation.md)  
**Canonical FR filename:** [fr019_m0_engineering_spike.md](fr019_m0_engineering_spike.md)
(this file retained as the pre-numbering path; content is the M0 evidence)  
**Date:** 2026-08-11  
**Phase:** Horizon 1B — FR-019 Core Loop Operationalisation  
**Preceding:** FR-018 Opportunity Discovery & Acquisition **Complete / Frozen /
Accepted** ([acceptance](fr018_opportunity_discovery_acquisition.md);
[ADR-010](../adr/010_opportunity_discovery_ingress.md)); Horizon 1A FR-008–FR-017
frozen; Core Loop Operationalisation Design (owner-approved direction)  
**Succeeded by:** [M1 Automatic Mailbox Intake](fr019_m1_mailbox_intake.md)  
**Scope (M0):** Architecture and source spike. **No production mailbox, `cic daily`,
scheduling, review UX, APPLY orchestration, or submission automation.**  
**Does not begin (historical M0 scope):** M1 implementation; Recruiter Intelligence;
Submission Automation spike; listing/search scraping; anti-bot bypass.

**Owner context accepted for this spike:**

1. Mailbox is **Yahoo Mail** — keep Yahoo if suitable; do not migrate without evidence.
2. Immediate priority is operationalising discovery → analysis → APPLY/SKIP → prep →
   owner review — **not** Recruiter Intelligence.
3. Assisted-manual submission (FR-012) stays production for this capability.
4. After Operationalisation acceptance, next core-loop priority is a **Submission
   Automation & Channel Adapter** investigation (not started here).

**Evidence classes used below:**

| Tag | Meaning |
|-----|---------|
| **KNOWN FROM DOCUMENTATION** | Provider docs / SEEK developer docs / repo SoT |
| **LIVE VALIDATED** | Observed in prior FR-018 owner runs or this spike without secrets |
| **INFERRED** | Reasonable engineering inference |
| **UNKNOWN / REQUIRES OWNER ACTION** | Needs owner config, credentials, or live connect |

---

## 1. Executive Summary

FR-018 proved the **ingest path** for owner-supplied job-alert `.eml` files and
owner-supplied job URLs into frozen Horizon 1A. The remaining product gap is
**automatic obtainment of those alerts** (and a thin daily batch + review/prep UX),
not a second discovery or analysis architecture.

**Mailbox:** Yahoo Mail **supports IMAP** (`imap.mail.yahoo.com:993` SSL) and typically
requires an **app password** when two-step verification is enabled
(**KNOWN FROM DOCUMENTATION** — [Yahoo IMAP help](https://help.yahoo.com/kb/SLN4075.html)).
CIC has **not** live-connected to the owner’s Yahoo account in this spike
(**UNKNOWN / REQUIRES OWNER ACTION** to enable IMAP / 2FA / app password and run M1
smoke). **Recommendation: KEEP YAHOO** via IMAP intake feeding the existing FR-018
email parser. Do not migrate to Gmail/Outlook without evidence Yahoo is unsuitable.

**SEEK discovery vs acquisition:** CIC can **acquire** SEEK `/job/<id>` URLs and can
**discover** SEEK job URLs **from SEEK alert emails**. CIC **cannot** today
independently discover new SEEK jobs from board search. Official SEEK API is
**partner/hirer-oriented**, not an owner-usable candidate “list suitable jobs” API
(**KNOWN FROM DOCUMENTATION** — [SEEK Developer](https://developer.seek.com/)).
Near-term automatic SEEK discovery remains: **saved search → alert email → mailbox →
FR-018**. Scraping search/list pages and third-party “v5 search” scrapers are
**NO-GO**.

**LinkedIn:** Keep proven alert → URL enrich path. No listing scrape / Playwright.

**Indeed:** Alert parse exists; URL enrich often Cloudflare-blocked. **Do not** feed
title/company/location-only cards into Horizon 1A. Prefer **fail closed** at discovery
when authoritative content is unavailable (reuse `DiscoveryItemOutcome` `failed` +
existing `failure_kind` values — no new Opportunity SoT state required).

**M0 recommendation:** **GO TO M1 under narrow scope** — Yahoo IMAP mailbox intake
adapter + email-level idempotency + secrets file + drop-folder fallback/test path.
Defer `cic daily` / recommend CLI / APPLY UX to subsequent milestones as designed.
**NO-GO:** mailbox migration without cause; SEEK scrape discovery; Indeed card-as-JD;
submission automation; Recruiter Intelligence.

**Owner decision:** **M0 GO** (2026-08-11). Capability formalised as **FR-019**;
prior Recruiter Intelligence identifier remapped to **FR-020** — changelog § 1.128.

---

## 2. Problem Statement

How does CIC **automatically obtain** newly available job-alert messages (and optional
owner URL batches) such that:

1. existing FR-018 parsers/adapters/ingress remain authoritative;
2. Horizon 1A analyse → assess → portfolio → strategy → Opportunity SoT is unchanged;
3. email-level reprocessing is prevented without duplicating FR-009 job identity;
4. insufficient advertisement content fails closed before analysis theatre;
5. credentials never enter Git or logs;
6. a future thin `cic daily` can coordinate intake → ingress → recommend summary
   without owning intelligence or scheduling?

This is **intake and operationalisation engineering**, not a new application OS.

---

## 3. Current Operational Gap

```text
TODAY (proven FR-018):
  Board alerts → owner saves .eml → cic opportunity discover-email
  → parse → URL enrich → Horizon 1A → Opportunity

DESIRED:
  Board alerts → Yahoo mailbox → CIC fetches MIME
  → existing FR-018 → Horizon 1A → recommend → owner APPLY/SKIP → prep → review
```

| Gap | Type |
|-----|------|
| Automatic mailbox fetch | ENGINEERING (new adapter) |
| Email-level processed ledger | ENGINEERING (small) |
| Secrets for IMAP app password | ENGINEERING / ops |
| `cic daily` thin batch | OPERATIONALISATION |
| FR-009 recommend on `cic` | CLI / productisation debt |
| Coherent APPLY → prep → truth stop | CLI / productisation debt |
| OS scheduling | Later (M5) — not M0/M1 logic |
| Live board submit automation | Explicitly **out of this capability** |

---

## 4. Current Source Capability Matrix

| Source | Discovery (find locators) | Acquisition (full JD) | Automatic intake | Near-term path |
|--------|---------------------------|----------------------|------------------|----------------|
| **SEEK** | Email alerts (parser); owner URL | Production URL adapter | Missing mailbox | Alert email → IMAP → FR-018 |
| **LinkedIn** | Email alerts (**LIVE VALIDATED** 6 jobs) | URL enrich (**LIVE VALIDATED**) | Missing mailbox | Same |
| **Indeed** | Email alerts (parser) | URL often Cloudflare 403 | Missing mailbox | Alert email → IMAP; enrich fail-closed if no JD |
| **Mailbox** | N/A | N/A | **Not implemented** | Yahoo IMAP (**recommended**) |
| **Drop-folder `.eml`** | File appears | Via discover-email | Manual or mail-rule | Fallback / test only |

---

## 5. Yahoo Mail Investigation

Owner mailbox: **Yahoo Mail**.

| # | Question | Answer | Evidence class |
|---|----------|--------|----------------|
| 1 | IMAP suitable? | **Yes** — Yahoo documents IMAP for third-party clients | KNOWN FROM DOCUMENTATION |
| 2 | Auth mechanism? | Username = full Yahoo address; password = **app password** when 2FA/Account Key enabled | KNOWN FROM DOCUMENTATION |
| 3 | App password required? | **Typically yes** if two-step verification is on (standard Yahoo guidance) | KNOWN FROM DOCUMENTATION |
| 4 | Full RFC/MIME? | IMAP `FETCH` can retrieve full RFC822 / MIME bodies (standard IMAP) | INFERRED (protocol); LIVE VALIDATED pending M1 connect |
| 5 | Message-ID preserved? | Present in MIME headers when Yahoo provides it; FR-018 already uses Message-ID with path fallback | KNOWN FROM DOCUMENTATION (repo `email_parse._stable_message_id`) |
| 6 | Filter by sender/subject/folder/unread? | IMAP `SEARCH` supports FROM, SUBJECT, UNSEEN, mailbox SELECT | KNOWN FROM DOCUMENTATION (IMAP); LIVE VALIDATED pending |
| 7 | Non-destructive read? | Yes — `FETCH` without `\Seen` / without `STORE` / without delete | INFERRED (IMAP capabilities) |
| 8 | Mark-read policy? | **Recommended default: leave unread** (or copy to CIC-processed label/folder if Yahoo supports). Optional opt-in mark-seen after successful email-level ledger write | INFERRED |
| 9 | Credentials CIC needs? | Yahoo email + IMAP app password; host `imap.mail.yahoo.com`; port 993 SSL | KNOWN FROM DOCUMENTATION |
| 10 | Secret storage? | See §14 — gitignored local secrets + env override | INFERRED |
| 11 | Windows Task Scheduler later? | Yes if secrets available to the scheduled process env / keyring | INFERRED; prove in M5 |
| 12 | Yahoo unsuitable? | **No evidence yet.** Historical third-party client friction is usually app-password / IMAP-enable misconfig — not IMAP absence | KNOWN FROM DOCUMENTATION |

**Official settings (Yahoo Help SLN4075):**

| Setting | Value |
|---------|--------|
| IMAP host | `imap.mail.yahoo.com` |
| Port | `993` |
| SSL | Required |
| Password | Generate App Password |

**Owner actions required before M1 live smoke (no credentials in this spike):**

1. Confirm two-step verification / Account Key posture.  
2. Generate a CIC-specific app password; store only in local secrets.  
3. Confirm IMAP access is enabled in Yahoo Mail settings if the account exposes that toggle.  
4. Confirm job alerts (SEEK / LinkedIn / Indeed) still arrive at this Yahoo inbox (or a dedicated folder).

**WHY keep Yahoo:** Owner already uses it; FR-018 validated a real LinkedIn `.eml` saved from this workflow; IMAP is a standard, maintainable protocol; migration cost is unjustified without failure evidence.

---

## 6. Mailbox Options Comparison

| Option | Engineering | Security | Reliability | Coupling | Testability | Owner friction | Verdict |
|--------|-------------|----------|-------------|----------|-------------|----------------|---------|
| **A. Yahoo IMAP** | Medium (`imaplib` or small client) | App password in local secrets | High for alerts | Protocol-stable | Fixtures + optional live smoke | Low after one-time setup | **PREFERRED** |
| **B. Dedicated Gmail** | Med–high (IMAP or Gmail API/OAuth) | OAuth better story; more setup | High | Google lock-in | Good | **Migration + new alert routing** | Alternative only if Yahoo fails |
| **C. Microsoft Graph** | High | OAuth | High | Microsoft lock-in | Harder | Migration | Not indicated |
| **D. Watched `.eml` folder** | Low | None | High if files appear | None | Excellent | **Still needs export or mail-client rule** | Fallback / dev / test |

---

## 7. Recommended Mailbox Strategy

**Production headline:** Yahoo IMAP → dedicated folder **`CIC Job Alerts`**
(Yahoo-side rules route SEEK / LinkedIn / Indeed alerts) → raw MIME → existing
FR-018 email parser → `OpportunitySource(source_kind="email", locator="…eml#job=N")`
→ `ThinDiscoveryIngress`.

Owner happy path: **no** manual message moves and **no** `.eml` export.

**Fallback / development / testing:** Watched directory of `.eml` files (and
owner-saved exports) using the same parser path.

**Do not** introduce mailbox migration in M1.

**WHY / WHAT EXISTS / MISSING / ALTERNATIVES / PRINCIPLE / INTERVIEW:**

| | |
|--|--|
| **WHY** | Removes manual `.eml` export while preserving FR-018 |
| **EXISTS** | Allow-listed MIME parser; `discover-email`; URL enrich |
| **MISSING** | IMAP fetch, filter, email-level ledger, secrets loading |
| **ALTERNATIVES** | Drop-folder-only (fails product goal); Gmail migration (unnecessary) |
| **WINS** | Matches owner mailbox; standard protocol; thin adapter |
| **PRINCIPLE** | Reuse before build; validate provider before migrating |
| **INTERVIEW** | “We kept Yahoo IMAP because the product constraint was intake, not provider fashion.” |

---

## 8. SEEK Discovery Investigation

### Discovery vs acquisition (explicit)

| Capability | Status | Evidence |
|------------|--------|----------|
| **SEEK acquisition** (given `/job/<id>` URL) | **Production** | FR-018 M2–M3; `UrlAcquisitionAdapter`; TLS via OS trust store |
| **SEEK discovery from alert email** | **Production (owner `.eml`)** | SEEK senders in `email_parse.py`; `discover-email` |
| **SEEK automatic discovery of new job URLs from board/search** | **MISSING** | No search/list/feed adapter in repo |

### Official / owner-usable mechanisms

| Mechanism | Finding | Class |
|-----------|---------|-------|
| SEEK Developer GraphQL API | Partner/hirer integrations; approval required; **not** a candidate job-search API; docs state API does **not** offer programmatic job search for reflection use-case indexing | KNOWN FROM DOCUMENTATION |
| Public self-serve “list AI jobs” API | Not available to CIC as an owner product | KNOWN FROM DOCUMENTATION / FR-018 M0 |
| RSS / public feed | No owner-usable SEEK candidate RSS adopted in repo; none confirmed in this spike | UNKNOWN for exotic feeds; **not** a current product path |
| Saved-search **email alerts** | Owner-accessible; already parsed | KNOWN + prior LIVE VALIDATED path for SEEK senders |
| Scrape `/jobs` search HTML or unofficial “v5 search” scrapers | **NO-GO** — scrape theatre / ToS / brittle; contradicts FR-018 principles | PRINCIPLE |

### Confirmed near-term architecture

```text
SEEK saved search
  → SEEK alert email (to Yahoo)
  → MailboxIntake (M1)
  → FR-018 email parser (job URLs)
  → UrlAcquisitionAdapter (full JD)
  → ThinDiscoveryIngress → Horizon 1A
```

**This spike CONFIRMS (does not merely restate) that email is the practical automatic
SEEK discovery mechanism available to CIC without scrape or partner API access.**

---

## 9. LinkedIn Discovery Decision

**No change.** Keep:

```text
LinkedIn saved job alerts → mailbox → FR-018 email discovery → URL enrich → Horizon 1A
```

**LIVE VALIDATED (FR-018):** 6 jobs parsed, enriched, full pipeline, `acquired=6`;
re-run `skipped=6`.

**Do not introduce:** listing scrape, authenticated browser discovery, Playwright,
Easy Apply infrastructure.

---

## 10. Indeed Discovery / Content-Unavailable Behaviour

### Current behaviour (repo)

`EmailAcquisitionAdapter` **fail-softs** URL enrich: if fetch/extract fails, email
card/snippet remains and acquire may still succeed (**KNOWN FROM DOCUMENTATION** —
`email_adapter.py`). FR-018 LinkedIn lesson: **card-only content is insufficient**
for honest Horizon 1A analysis (**LIVE VALIDATED** product gap).

**Required M1+ invariant**

```text
NO AUTHORITATIVE / FULL JOB CONTENT
  → DO NOT run Job Analysis / persist Opportunity as “ready”
```

### Recommended behaviour (design — implement in M1 or early operationalisation)

When email job has a URL and enrich is attempted:

| Condition | Outcome |
|-----------|---------|
| Enrich succeeds with JD signals / substantial body | Proceed (current happy path) |
| Enrich fails **and** email body lacks JD signals (card-only) | **`DiscoveryItemOutcome(status="failed")`** — do **not** call runner |
| Enrich fails but email body already has JD signals | Rare for Indeed/LinkedIn cards; may proceed with warning — spike preference: still prefer fail closed if below a content threshold |
| Offline fixtures | Unchanged test behaviour |

**Reuse existing domain model — do not invent Opportunity SoT states:**

- Use `DiscoveryItemStatus = "failed"`
- Prefer `failure_kind`: `network_failure` (Cloudflare/fetch) or `malformed_content` /
  `partial_metadata` (card-only after enrich failure)
- Surface message such as: `content_unavailable — URL enrich failed; email body is discovery card only; owner paste/URL required`

Conceptual labels like `DISCOVERED_BUT_CONTENT_UNAVAILABLE` / `NEEDS_OWNER_CONTENT`
are **presentation synonyms** for a failed discovery item — not new SoT entities.

**WHY:** Prevents repeating the FR-018 card→hollow-analysis failure mode at scale.  
**PRINCIPLE:** Fail closed; no analysis theatre.  
**INTERVIEW:** “Discovery without content is not an Opportunity — we fail the item, not the truth model.”

---

## 11. Proposed Mailbox Intake Contract

### Preferred seam (minimal reuse)

```text
MailboxIntakeAdapter
  → IngestedMailMessage[] { message_id, folder, uid, raw_rfc822, received_at }
  → materialise temporary .eml (or bytes API later)
  → existing parse_job_alert_email / discover-email expansion
  → OpportunitySource(source_kind="email", locator="…eml#job=N")
  → ThinDiscoveryIngress.discover(DiscoveryRequest)
```

**Alternative rejected as primary:** Mailbox emits `OpportunitySource` only without a
typed ingested-message DTO — loses email-level idempotency handles (UID/Message-ID).

### Responsibilities

| Mailbox intake **MAY** own | Mailbox intake **MUST NOT** own |
|----------------------------|----------------------------------|
| Connect / authenticate IMAP | Job analysis / assessment |
| Select candidate messages (FROM allow-list, UNSEEN, folder) | Ranking / recommendations |
| Retrieve full MIME | Application strategy |
| Email-level idempotency ledger | Opportunity persistence |
| Hand MIME to FR-018 parser | Submission / pipeline mutation |
| Non-destructive read policy | Horizon 1A runner logic |

Ingress, adapters, runner, Opportunity SoT remain FR-018 / FR-008 / FR-009.

---

## 12. Email-Level Idempotency Design

**Problem:** Prevent re-processing the same alert MIME when `cic daily` runs again.

**Smallest robust ledger (design):**

| Field | Role |
|-------|------|
| `message_id` (normalised) | Primary key when present |
| `folder` + `uidvalidity` + `uid` | Secondary key when Message-ID missing/unstable |
| `content_sha256` (optional) | Tie-breaker for malformed headers |
| `processed_at` | Audit |
| `outcome_summary` | Counts / last status |

Store under gitignored operational data (e.g. `data/mailbox_intake/processed.json` or
YAML) — **not** Opportunity SoT.

**Algorithm:**

1. FETCH candidate messages.  
2. If ledger hit on Message-ID (or folder+UID) → skip at **email level** (do not re-expand jobs).  
3. Else parse → expand jobs → ingress (FR-018 definite skip still applies per job).  
4. On successful parse+hand-off (even if all jobs skipped/failed at ingress) → write ledger entry.

**Default mailbox mutation:** do not mark `\Seen` unless owner opts in after trust builds.

---

## 13. Relationship to FR-009 Job Deduplication

| Layer | Owner | Example |
|-------|-------|---------|
| **Email-level idempotency** | Mailbox intake (new) | Same LinkedIn digest fetched twice |
| **Job/opportunity definite identity** | FR-018 ingress + FR-009 facets | Same job URL in two digests / two days / SEEK+LinkedIn |
| **Owner-confirmed duplicates** | FR-009 duplicate services | Soft matches requiring human confirm |

**Same email twice:** ledger skips before parse.  
**Same job in multiple alerts:** ingress `skipped` / `definite_identity_match`.  
**Same job different days:** same.  
**Same job multiple sources:** definite URL facets / owner duplicate review — **not**
reimplemented in mailbox.

---

## 14. Secrets Strategy

**Requirements:** no Git; no logs; tests without real credentials; eventual scheduled
access; owner-understandable.

| Option | Verdict |
|--------|---------|
| Environment variables | Good override; awkward alone for multi-field IMAP |
| **Gitignored local secrets file** | **Preferred primary** |
| OS keyring | Optional enhancement later |

**Recommended simplest safe approach:**

1. Gitignore e.g. `config/local_secrets.env` or `data/secrets/mailbox.env` (never commit).  
2. Document template `config/local_secrets.env.example` with keys only:
   - `CIC_MAILBOX_HOST=imap.mail.yahoo.com`
   - `CIC_MAILBOX_PORT=993`
   - `CIC_MAILBOX_USER=`
   - `CIC_MAILBOX_APP_PASSWORD=`
   - optional folder / mark-seen flag  
3. Load in mailbox intake only; never print password; redact in error messages.  
4. CI/unit tests use fixtures / fake IMAP — no live secrets.  
5. Scheduled task: set the same env vars for the task principal, or point
   `CIC_SECRETS_FILE` at the gitignored path.

Matches existing single-user pattern (`OPENAI_API_KEY` in environment) without
enterprise vaults.

---

## 15. Proposed `cic daily` Boundary

**Thin batch coordinator only** (design — not implemented in M0).

```text
cic daily
  → MailboxIntakeAdapter.fetch_new()     # + optional drop-folder
  → expand to OpportunitySource[]
  → ThinDiscoveryIngress.discover(...)
  → OpportunityRecommendationService.recommend_awaiting_review(...)  # projection
  → print + write run summary artefact
```

| | |
|--|--|
| **Inputs** | Secrets/config; opportunities dir; profile; flags (`--offline-fixtures`, `--force` rare) |
| **Outputs** | Exit summary: fetched emails, sources, acquired/skipped/failed, recommend band counts; optional JSON under `data/daily_runs/` (gitignored) |
| **Exit codes** | `0` success (including partial item failures recorded); non-zero for intake auth hard-fail / unreadable config |
| **Idempotency** | Email ledger + FR-018 definite skip |
| **MUST NOT own** | Ranking model, submit, owner decide, scheduling, runner redesign |

---

## 16. Failure / Partial-Success Semantics

| Scenario | Behaviour |
|----------|-----------|
| IMAP auth failure | Abort daily; non-zero; no silent empty success |
| One message MIME corrupt | Fail that message; continue others |
| One job enrich content-unavailable | Item `failed`; continue batch |
| All jobs definite-skipped | Success with skipped counts |
| OpenAI/runner failure on one job | Item `failed` (`runner_failure`); continue |
| Recommend projection error | Daily still reports discovery counts; recommend section soft-fails with error note |

Partial success is **normal** and must be visible in the summary.

---

## 17. Scheduling Boundary

```text
Windows Task Scheduler
  → activates venv / working directory
  → cic daily
```

Scheduler contains **no** workflow logic.

**Prove before M5:** secrets visibility to task user; `cwd`; Python/venv; logging path;
network; non-zero exits alerting owner (even if only via Task History).

---

## 18. Review / Productisation Audit

Inspected implementation (not FR names alone):

| Service | Module | On `cic` today? |
|---------|--------|-----------------|
| `OpportunityRecommendationService.recommend_awaiting_review` / `recommend_active` | `recommendations/service.py` | **No** — scripts only |
| `ReviewQueueService.list_awaiting_review` | review queue package | **No** — scripts |
| `OpportunityReviewService` pin/archive/defer | review service | **No** — scripts |
| `cic opportunity decide` | CLI → `OpportunityService` | **Yes** |
| `cic opportunity compare` | comparison service | **Yes** (open rank; not full recommend bands) |

| Future surface | Classification |
|----------------|----------------|
| `cic opportunity recommend` | **CLI / OPERATIONALISATION DEBT** (wrap existing service) |
| `cic opportunity queue` (optional) | **CLI / OPERATIONALISATION DEBT** |

**Not a new ranking capability.**

---

## 19. APPLY Preparation Audit

| Piece | Exists? | Surface |
|-------|---------|---------|
| Tailoring + CV + CL package | Yes | FR-010 / `cic package` / `cic preparation` |
| Truth validation | Yes | FR-014 / `cic truth` |
| Prep + truth to owner review | Yes | FR-015 / `cic agent run --approve` |
| Render after edit | Yes | `scripts/render_document.py` |
| Decide apply | Yes | `cic opportunity decide … apply` |

| Future surface | Classification |
|----------------|----------------|
| `cic apply prepare <id> --approve` | **CLI / OPERATIONALISATION DEBT** (alias/orchestrate existing) **or** document `cic agent run` as the path |
| Rebuilding prep/truth engines | **NOT REQUIRED** |

Must stop at **READY FOR OWNER REVIEW**; never submit.

---

## 20. Reuse Map

### Reused

ThinDiscoveryIngress · Email/URL adapters · email_parse · Url enrich · FR-008 runner ·
Opportunity SoT · FR-009 definite identity · RecommendationService · Preparation /
package / agent / truth · FR-012 assist · FR-013 pipeline (after owner submit)

### Genuinely new (M1+)

| Component | Milestone |
|-----------|-----------|
| Yahoo IMAP `MailboxIntakeAdapter` | M1 |
| Email-level processed ledger | M1 |
| Secrets loader + example template | M1 |
| Drop-folder fallback adapter | M1 |
| Indeed/card content-unavailable fail-closed policy tweak | M1 (narrow) |
| `cic daily` coordinator | M2 |
| `cic opportunity recommend` | M3 |
| APPLY prep UX alias | M4 |
| Task Scheduler wiring | M5 |

---

## 21. Explicit Non-Goals (this capability)

- Recruiter Intelligence / outreach  
- Submission channel automation (SEEK Apply, Easy Apply, ATS drivers)  
- Listing/search scraping; Cloudflare/CAPTCHA bypass  
- Second Opportunity store or analysis pipeline  
- Dashboards / notification theatre  
- Reopening frozen FR-008–FR-018 exit criteria  
- Mailbox provider migration without evidence  
- Feeding card-only alerts into Horizon 1A  

---

## 22. Core-Loop Completion Boundary

**This Operationalisation capability will NOT complete the owner’s full automation
objective.**

It operationalises:

```text
automatic intake → discovery → analysis → recommendation
→ APPLY/SKIP → application preparation → truth → owner final review
```

FR-012 assisted/manual external submission remains the production submit path
during and immediately after this capability.

---

## 23. Future Submission Automation Boundary (planning note only)

**After** Operationalisation acceptance, next core-loop priority:

**Submission Automation & Channel Adapter Spike** covering at least:

SEEK Apply · LinkedIn Easy Apply · Indeed Apply · Greenhouse · Lever · Workday ·
custom ATS · email apply

Classify each: **AUTOMATABLE | ASSISTED | MANUAL** from evidence. No universal
automation assumption. **Not started in M0.**

Recruiter Intelligence remains deferred until that boundary is investigated and
agreed.

---

## 24. Risks / External Constraints

| Risk | Mitigation |
|------|------------|
| Yahoo app password / IMAP enable friction | Owner checklist; keep drop-folder fallback |
| Yahoo IMAP policy change | Adapter boundary; migration only if proven |
| Alert volume / noise | FR-009 recommend bands; owner decide |
| Indeed enrich failures at scale | Fail closed; owner paste/URL |
| Secrets in scheduled task | Document M5 env wiring |
| Overclaiming SEEK “auto discovery” | Email-mediated discovery only |
| Weakening card fail-soft too late | Fix policy in M1 before high-volume IMAP |

---

## 25. Testing Strategy for M1+

- Unit: IMAP client fake; filter; ledger idempotency  
- Unit: MIME → existing parser golden `.eml` fixtures (no live Yahoo)  
- Unit: content-unavailable fail-closed (card + enrich fail → `failed`, no runner)  
- Contract: intake emits FR-018 `OpportunitySource` shapes  
- No CI dependency on real mailbox credentials  

---

## 26. Live Validation Strategy

After M1 GO:

1. Owner configures Yahoo app password locally (never commit).  
2. Live smoke: fetch ≥1 real SEEK and/or LinkedIn alert; parse; enrich; ingress.  
3. Re-run: email ledger skips; job definite skip.  
4. Indeed: confirm fail-closed when enrich blocked and card-only.  
5. **TECHNICAL PASS ≠ PRODUCT PASS** — dogfood morning rhythm before declaring
   operationalisation success (M6).

---

## 27. Learning / Interview Takeaways

1. **Acquisition ≠ discovery** — SEEK URL fetch ≠ automatic finding of new SEEK jobs.  
2. **Lawful volume discovery is often email**, not board search APIs (SEEK partner API
   is the wrong product surface for a candidate copilot).  
3. **Keep the owner’s mailbox** when IMAP is adequate — migration is a cost, not a virtue.  
4. **Card-only content must fail closed** after FR-018’s live lesson.  
5. **Layer idempotency:** email ledger ≠ job identity.  
6. **Operationalisation FR vs frozen capability FR** — extend with adapters and CLI debt,
   do not reopen Horizon 1A.  
7. **Assisted submit stays** until a dedicated submission spike has evidence.

---

## 28. M1 Recommendation

**Implement next (narrow):**

1. Yahoo IMAP `MailboxIntakeAdapter` (allow-listed FROM matching FR-018 senders;
   UNSEEN or since-cursor; non-destructive default).  
2. Email-level processed ledger.  
3. Secrets file + example template (gitignored).  
4. Drop-folder fallback using same hand-off to FR-018.  
5. Content-unavailable fail-closed when enrich fails and body is card-only.  
6. Spike-to-code tests with fixtures; optional owner live smoke checklist.

**Defer to M2+:** `cic daily`, recommend CLI, APPLY UX, scheduling.

---

## 29. M0 GO / NO-GO Decision

### Acceptance questions

| # | Question | Answered? |
|---|----------|-----------|
| 1 | How will CIC obtain Yahoo job-alert emails? | **Yes** — IMAP fetch of full MIME |
| 2 | Yahoo suitable or migrate? | **Keep Yahoo** pending live connect; migrate only if unsuitable |
| 3 | Duplicate email prevention? | **Yes** — Message-ID / folder+UID ledger |
| 4 | Credentials? | **Yes** — gitignored secrets + env; app password |
| 5 | MailboxIntakeAdapter owns? | **Yes** — §11 |
| 6 | `cic daily` owns? | **Yes** — §15 (design) |
| 7 | SEEK automatic discovery? | **Yes** — via SEEK alert email, not board search API/scrape |
| 8 | Indeed content unavailable? | **Yes** — fail closed at discovery; no card→analysis |
| 9 | Reused FRs? | **Yes** — §20 |
| 10 | New M1 engineering? | **Yes** — IMAP + ledger + secrets + fail-closed policy |
| 11 | Outside this capability? | **Yes** — §21–23 |
| 12 | Narrow enough? | **Yes** — no Horizon 1A reopen |

### Recommendation

**GO TO M1** under the narrow mailbox intake scope above.

**NO-GO** on: Gmail migration now; SEEK scrape/unofficial search API; card-as-JD;
submission automation; Recruiter Intelligence; implementing `cic daily` inside M1
unless owner explicitly expands M1 (not recommended).

**Owner decision:** **Accepted — GO TO M1** (2026-08-11).

---

## 30. Final Repository Status

| Item | Status |
|------|--------|
| FR-018 | Frozen / unchanged |
| Horizon 1A | Frozen / unchanged |
| This M0 report | **Complete — Accepted / GO** |
| FR-019 formalisation | See [fr019_core_loop_operationalisation.md](fr019_core_loop_operationalisation.md) |
| M1 production code | **Not started** (definition ready) |
| FR number | **FR-019** Core Loop Operationalisation |
| Submission Automation spike | **Not started** (next after FR-019 acceptance) |
| Recruiter Intelligence | **Deferred** as **FR-020** |

**Historical stop condition (M0 spike):** M0 only — met. Formalisation and M1
definition follow under FR-019.
