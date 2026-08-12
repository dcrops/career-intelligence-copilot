# FR-019 Core Loop Operationalisation

**Status:** **In progress** — M0 **Accepted / GO**; M1 **GO** (proposed with
M1.1); M1.1 Reliability Hardening **proposed GO**
([fr019_m1_1_reliability_hardening.md](fr019_m1_1_reliability_hardening.md))  
**Date formalised:** 2026-08-11  
**Phase:** Horizon 1B  
**Capability name:** Core Loop Operationalisation  
**Preceding:** FR-018 Opportunity Discovery & Acquisition **Complete / Frozen /
Accepted** ([acceptance](fr018_opportunity_discovery_acquisition.md);
[ADR-010](../adr/010_opportunity_discovery_ingress.md))  
**Architectural evidence (M0):**
[fr019_m0_engineering_spike.md](fr019_m0_engineering_spike.md)
(canonical copy of
[core_loop_operationalisation_m0_engineering_spike.md](core_loop_operationalisation_m0_engineering_spike.md))  
**M1 definition:** [fr019_m1_mailbox_intake.md](fr019_m1_mailbox_intake.md)  
**Remap:** Prior FR-019 Recruiter Intelligence → **FR-020** (and subsequent FRs +1)
— [changelog § 1.128](../11_changelog.md).

---

## 1. Why a new FR (not reopen FR-018)

| | |
|--|--|
| **WHAT EXISTS (FR-018)** | Lawful discovery/acquisition adapters; thin ingress; owner `.eml` + URL paths into frozen Horizon 1A |
| **WHAT IS NEW (FR-019)** | Automatic mailbox intake; daily batch coordination; owner-operable recommend/APPLY-prep surfaces; scheduling; dogfood of the composed loop |
| **WHAT IS PRODUCTISATION DEBT** | FR-009 recommend via `cic`; coherent APPLY→prep→truth path (`cic agent run` or thin alias) |
| **WHAT REMAINS DEFERRED** | Submission channel automation; Recruiter Intelligence (FR-020+); listing scrape |

FR-018 closed the **acquisition framework**. FR-019 operationalises the **owner
daily job-search loop** around that framework and frozen Horizon 1A services.
Reopening FR-018 would blur adapter capability freeze with operational UX and
mailbox credentials — rejected.

**Interview takeaway:** Separate *capability FRs* (what the system can ingest)
from *operationalisation FRs* (how the owner runs the loop every day).

---

## 2. Capability objective

Transform already-built Horizon 1 components into a coherent owner-operable
daily workflow:

```text
AUTOMATIC JOB ALERT INTAKE
        ↓
DISCOVERY / ACQUISITION          (FR-018)
        ↓
ANALYSIS → ASSESSMENT → PORTFOLIO → STRATEGY   (FR-002–005 / FR-008)
        ↓
RECOMMENDATION / PRIORITISATION  (FR-009)
        ↓
OWNER: APPLY / SKIP / LATER
        ↓
APPLICATION PREPARATION + TRUTH  (FR-010/011/014/015)
        ↓
RENDERED / VERIFIED PACKAGE
        ↓
OWNER FINAL REVIEW
```

**Stops before** new external submission automation. **FR-012** assisted/manual
submission remains the production submit path during this FR.

---

## 3. Core-loop completion boundary

**Completion of FR-019 does NOT complete the owner’s full automation objective.**

It completes:

```text
automatic intake → discovery → analysis → recommendation
→ APPLY / SKIP / LATER → application preparation → truth → owner final review
```

Existing assisted/manual submission (FR-012) remains. After FR-019 acceptance and
dogfood, the next core-loop investigation is **Submission Automation & Channel
Adapters** (FR number assigned when that spike is authorised) — **before**
Recruiter Intelligence (**FR-020**).

---

## 4. Accepted architecture (from M0 GO)

### Mailbox

- Keep **Yahoo Mail**
- **Yahoo IMAP** `imap.mail.yahoo.com:993` SSL; app password (or equivalent)
- Production folder: **`CIC Job Alerts`** (Yahoo rules route SEEK / LinkedIn / Indeed alerts)
- Happy path: **no** manual `.eml` export
- `.eml` drop-folder: tests / development / fallback recovery only

### Intake seam

```text
Yahoo Mail (CIC Job Alerts)
  → MailboxIntakeAdapter
  → raw MIME / email-source representation
  → existing FR-018 email parser
  → ThinDiscoveryIngress
  → existing FR-008 workflow
  → Opportunity SoT
```

Mailbox intake **may** own: IMAP connect, folder select, MIME retrieve, intake
filters, email-level idempotency, hand-off to FR-018.  
Mailbox intake **must not** own: analysis, assessment, portfolio, strategy,
ranking, Opportunity persistence, prep, submit, pipeline.

### Idempotency

| Layer | Owner | Question |
|-------|-------|----------|
| Email-level | Mailbox intake (FR-019) | Already processed this mailbox message? |
| Job-level | FR-018 / FR-009 | Already discovered this job/opportunity? |

### SEEK / LinkedIn / Indeed

- **SEEK:** acquisition ≠ discovery; auto-discovery via **alert email** only; no scrape
- **LinkedIn:** alert → URL enrich (FR-018 live-validated); no listing scrape
- **Indeed:** fail closed when authoritative content unavailable; no card-as-JD analysis

### Secrets (formalised)

**Preferred owner path:** gitignored `config/local_secrets.env`  
**Template (committed):** `config/local_secrets.env.example`  
**Override:** same `CIC_MAILBOX_*` variables in the process environment (env wins)  
See [fr019_m1_mailbox_intake.md](fr019_m1_mailbox_intake.md) § Secrets.

---

## 5. Milestones

| Milestone | Intent | Status |
|-----------|--------|--------|
| M0 | Architecture & source spike | **Complete — GO** ([M0](fr019_m0_engineering_spike.md)) |
| **M1** | Automatic Yahoo mailbox intake | **GO** (proposed with M1.1) ([M1](fr019_m1_mailbox_intake.md)) |
| **M1.1** | Assess retry + failed-run recovery | **Proposed GO** ([M1.1](fr019_m1_1_reliability_hardening.md)) |
| **M2** | Thin `cic daily` batch coordinator | Planned |
| **M3** | Review operability (`cic opportunity recommend`) | Planned — CLI debt |
| **M4** | APPLY preparation workflow (compose FR-010/011/014/015) | Planned — productisation debt |
| **M5** | Windows Task Scheduler → `cic daily` | Planned |
| **M6** | Live dogfood & acceptance | Planned |

### M0 — Architecture & Source Spike (complete)

Yahoo suitability; mailbox strategy; SEEK discovery vs acquisition; LinkedIn;
Indeed fail-closed; intake seam; idempotency; secrets; `cic daily` / scheduling
boundaries; reuse audit. **Owner GO 2026-08-11.**

### M1 — Automatic Mailbox Intake

Smallest production Yahoo IMAP path into FR-018. Success:

> CIC can obtain and process new job-alert emails from the owner’s Yahoo
> `CIC Job Alerts` folder without manual `.eml` export.

**Live close-out 2026-08-11:** SEEK 5/5 enriched+analysed; LinkedIn natural
filter 6 jobs; ledger idempotency proven; **no card-only analysis**. M1.1
closed assess retry + `retry-run` with live recovery of all three LinkedIn
failures. Verdict: **GO** (with M1.1) — M2 not started.
Full criteria + matrix: [M1](fr019_m1_mailbox_intake.md);
[M1.1](fr019_m1_1_reliability_hardening.md).

**Does not** implement `cic daily`.

### M1.1 — Reliability Hardening

Selective Opportunity Assessment validation retries (typed codes only;
`max_attempts=3`) and `cic opportunity retry-run` for terminal failed
analyse/assess checkpoints. LinkedIn title/company metadata swap tracked as
non-blocking debt (not fixed).

### M2 — Daily Batch

`cic daily`: intake → FR-018 ingress → FR-008 → Opportunity SoT → FR-009 recommend
projection → run summary. No new intelligence, submit, or scheduling logic.

### M3 — Review Operability

Productise FR-009 via `cic opportunity recommend` (and minimal queue if needed).
No new ranking algorithm.

### M4 — APPLY Preparation Workflow

One coherent path from APPLY → READY FOR OWNER FINAL REVIEW. Prefer reuse of
`cic agent run` before inventing `cic apply prepare`. Preserve approval, truth
gates, fail-closed, provenance, audit; **no silent submission**.

### M5 — Scheduling & Operational Hardening

Windows Task Scheduler → `cic daily` only after manual daily is proven. Validate
credentials, env, cwd, network, logging, exit codes, partial failure.

### M6 — Live Dogfood & Acceptance

Real Yahoo alerts, SEEK/LinkedIn/Indeed (where supported), recommend, decide,
prep, truth, assisted submit, pipeline. Technical green ≠ product pass; require
meaningful owner-effort reduction.

### Dogfood defect — nested certification claim splitting (2026-08-11)

First operational package for Repurpose It (`opp_01KZQJY6AX3EGX7TGYTHR3ABG1`)
hit a **truth-validator false positive**: overlapping well-known
`AWS Certified Developer` nested inside truthful profile-backed
`AWS Certified Developer - Associate` produced a blocking unsupported twin.

Fixed in FR-014 `extended_claims` label occupancy (longest-first; no gate
weakening). Live revalidation → `external_use: ALLOWED`. Detail:
[docs/08_implementation_notes.md](../08_implementation_notes.md) § FR-019 dogfood
defect; changelog § 1.132. Does not reopen FR-014 exit criteria; does not start M2.

### Dogfood defect — application contact wiring (2026-08-11)

Same application: tailored CV/cover letter omitted contact/navigation though
Master CV and FR-006/FR-007 renderers support it. Root cause: production
defaults never passed `ContactDetails`. Fixed via owner
`config/candidate_contact.yaml` + composition wiring + fail-closed incomplete
config + labelled Portfolio/GitHub cover-letter paragraph. Changelog § 1.133.
Does not start M2.

---

## 6. Definition of Done (FR-019)

Apply the post–FR-008 completion standard. FR-019 is **not** complete until:

- [ ] M0–M6 acceptance criteria met (each milestone has its own record)
- [ ] Unit tests for new intake / ledger / fail-closed policy
- [ ] Functional / integration tests without live Yahoo credentials
- [ ] Repeatable manual validation checklist
- [ ] Live Yahoo / board dogfood evidence (M6)
- [ ] Engineering spike report retained (M0)
- [ ] Acceptance report written and owner-reviewed
- [ ] Functional specification, roadmap, changelog, implementation notes updated
- [ ] Owner confirms the daily workflow reduces search effort in practice
- [ ] Explicit non-goals still hold (no submit automation; no Recruiter Intelligence)

Do **not** mark FR-019 complete on fixtures alone.

---

## 7. Reuse map

### Reused (frozen)

ThinDiscoveryIngress · Email/URL adapters · email_parse · URL enrich · FR-008
runner · Opportunity SoT · FR-009 identity / recommend · package / preparation /
agent / truth · FR-012 assist · FR-013 pipeline (after owner submit)

### New (this FR)

| Component | Milestone |
|-----------|-----------|
| Yahoo IMAP `MailboxIntakeAdapter` | M1 |
| Email-level processed ledger | M1 |
| Secrets loader + example template | M1 |
| `.eml` drop-folder fallback | M1 |
| Content-unavailable fail-closed policy (card-only) | M1 |
| `cic daily` | M2 |
| `cic opportunity recommend` | M3 |
| APPLY prep UX (compose / alias) | M4 |
| Task Scheduler wiring | M5 |

---

## 8. Explicit non-goals

- Recruiter Intelligence / outreach (FR-020+)
- Submission channel automation (SEEK Apply, Easy Apply, ATS drivers)
- Listing/search scraping; Cloudflare / CAPTCHA bypass
- Second Opportunity store or analysis pipeline
- Parallel ranking model
- Dashboard / notification theatre
- Reopening frozen FR-008–FR-018 exit criteria
- Mailbox provider migration without evidence Yahoo is unsuitable
- Feeding card-only alerts into Horizon 1A Job Analysis

---

## 9. Next after FR-019 (planning only)

1. **Submission Automation & Channel Adapters** spike — classify
   AUTOMATABLE / ASSISTED / MANUAL per channel (SEEK Apply, LinkedIn Easy Apply,
   Indeed Apply, Greenhouse, Lever, Workday, custom ATS, email apply).
2. Then **FR-020 Recruiter Intelligence** (deferred until that boundary is agreed).

Do not start either during FR-019 implementation unless the owner explicitly
reprioritises.
