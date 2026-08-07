# FR-018 — Opportunity Discovery & Acquisition

**Masterclass Source Package** for the Engineering Learning Academy  
**Status:** Complete / Frozen / Accepted (thin Discovery Ingress + URL/email channels)  
**Attach this folder** (`docs/masterclass/FR018/`) when generating the Masterclass.

This package is a **packaging layer**, not a second engineering record.
Authoritative content lives under `docs/eval/`, `docs/adr/`, and related docs.
Files in `sources/` are **generated snapshots** — regenerate; do not hand-edit.

```powershell
python scripts/build_masterclass_package.py FR018
```

---

## What this Functional Requirement teaches

How to scale **lawful opportunity inflow** into a frozen application pipeline:

- keep Discovery Ingress thin — coordinate, do not re-orchestrate
- treat channels as adapters under one framework (not one FR per board)
- reuse canonical URL acquisition when email alerts are discovery cards only
- prefer live owner validation for external integrations
- fail closed without inventing a second Opportunity store

---

## Why it matters

Email job alerts look like content sources but are often **cards**. FR-018 records
the refinement from “parse email body into Horizon 1A” to “email discovers URL;
URL adapter supplies the advertisement” — simpler architecture, better product
readiness, Academy-transferable lesson on validation-driven design.

---

## Prerequisites

- Familiarity with FR-008 `AcquisitionAdapter` / `ApplicationWorkflowRunner`
- FR-009 Opportunity identity / definite duplicates
- Comfort reading ADRs and acceptance reports

---

## Expected learning outcomes

1. Explain thin ingress vs fat discovery orchestrator
2. Distinguish email discovery from authoritative job description
3. Argue why URL enrich reused existing architecture
4. State SEEK vs LinkedIn/Indeed reliability posture
5. Describe definite-identity skip on re-ingest
6. List what stayed out of FR-018 (IMAP, Playwright, Easy Apply, recruiters)

---

## Where the authoritative documents are

| Role | In this package | Repository source of truth |
|------|-----------------|------------------------------|
| Bridge / teaching index | [README.md](README.md) (this file) | — |
| Generation contract | [MANIFEST.md](MANIFEST.md) | — |
| Acceptance (canonical) | [sources/acceptance.md](sources/acceptance.md) | `docs/eval/fr018_opportunity_discovery_acquisition.md` |
| ADR | [sources/adr.md](sources/adr.md) | `docs/adr/010_opportunity_discovery_ingress.md` |
| Functional requirements § | [sources/functional_specification.md](sources/functional_specification.md) | `docs/04_functional_specification.md` § FR-018 |
| Domain model § | [sources/domain_model.md](sources/domain_model.md) | `docs/06_domain_model.md` § FR-018 |
| Implementation notes § | [sources/implementation_notes.md](sources/implementation_notes.md) | `docs/08_implementation_notes.md` § FR-018 |
| Testing strategy § | [sources/testing_strategy.md](sources/testing_strategy.md) | `docs/07_testing_strategy.md` § FR-018 |
| Engineering evaluation (M4) | [sources/optional/m4.md](sources/optional/m4.md) | `docs/eval/fr018_m4_email_job_alert_acquisition.md` |
| Milestone history | [sources/optional/](sources/optional/) | `docs/eval/fr018_m0`–`m4` |

**Edit engineering in the repository paths above — never in `sources/`.**

---

## Package layout

```text
FR018/
  README.md
  MANIFEST.md
  sources/          ← regenerable snapshots
    optional/       ← M0–M4 milestone mirrors
```

CLI demos (repository, not packaged as SoT):
`cic opportunity discover` / `discover-email`

## Generated Masterclass

Lean Masterclass / PDF / Gamma / Interview Brief / Deck are **not** generated in
this close-out unless the owner requests them separately. Follow
[LEAN_MASTERCLASS_STANDARD.md](../LEAN_MASTERCLASS_STANDARD.md) when asked.
