# FR-019 M0 — Core Loop Operationalisation Engineering Spike

**Status:** **Complete — Accepted / GO** (owner 2026-08-11)  
**FR:** [FR-019 Core Loop Operationalisation](fr019_core_loop_operationalisation.md)  
**Full spike report (authoritative body):**
[core_loop_operationalisation_m0_engineering_spike.md](core_loop_operationalisation_m0_engineering_spike.md)  
**Succeeded by:** [M1 Automatic Mailbox Intake](fr019_m1_mailbox_intake.md)

This file is the **FR-numbered canonical entry** for the M0 spike. The complete
thirty-section engineering spike (Yahoo investigation, mailbox options, SEEK
discovery vs acquisition, LinkedIn, Indeed fail-closed, intake contract,
idempotency, secrets, `cic daily` / scheduling boundaries, reuse audit, and GO
decision) lives in the linked document — written before the FR number was
assigned, then updated in place after **M0 GO** and FR-019 formalisation
([changelog § 1.128](../11_changelog.md)).

## Verdict (accepted)

| Decision | Choice |
|----------|--------|
| Mailbox | Keep **Yahoo Mail**; IMAP `imap.mail.yahoo.com:993` + app password |
| Production organisation | Dedicated folder **`CIC Job Alerts`** + Yahoo routing rules |
| SEEK auto-discovery | Alert email → mailbox → FR-018 (not board search/scrape) |
| LinkedIn | Alert → URL enrich (unchanged) |
| Indeed | Fail closed when authoritative content unavailable |
| M1 | Narrow mailbox intake only — **GO** |
| After FR-019 | Submission Automation spike; Recruiter Intelligence deferred (**FR-020**) |

Do not treat this alias as a second spike. Edit the full report when correcting M0 evidence.
