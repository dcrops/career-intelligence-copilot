# MANIFEST — FR-018 Masterclass Source Package

## Masterclass Title

Opportunity Discovery & Acquisition: Thin Ingress, Email as Discovery, and URL Enrichment

## Functional Requirement

**FR-018** — Opportunity Discovery & Acquisition

## Repository Version

Changelog **1.125** (FR-018 Complete / Frozen / Accepted).

## Current Status

**Complete / Frozen / Accepted** — thin Discovery Ingress + URL/email channel adapters
into frozen Horizon 1A

CLI: `cic opportunity discover` / `cic opportunity discover-email`

## Completion Date

2026-08-07

## Package root (attach this folder)

`docs/masterclass/FR018/`

## Required documents

| Package path | Authoritative repository path | Notes |
|--------------|-------------------------------|-------|
| `sources/acceptance.md` | `docs/eval/fr018_opportunity_discovery_acquisition.md` | Canonical engineering record |
| `sources/adr.md` | `docs/adr/010_opportunity_discovery_ingress.md` | Normative architecture decisions |
| `sources/functional_specification.md` | `docs/04_functional_specification.md` § FR-018 | Requirements status |
| `sources/domain_model.md` | `docs/06_domain_model.md` § FR-018 | Domain concepts |
| `sources/implementation_notes.md` | `docs/08_implementation_notes.md` § FR-018 | Implementation pointers |
| `sources/testing_strategy.md` | `docs/07_testing_strategy.md` § FR-018 | Test expectations |
| `README.md` | (package-local) | Teaching bridge |
| `MANIFEST.md` | (package-local) | This file |

## Optional documents

| Package path | Authoritative repository path | When to include |
|--------------|-------------------------------|-----------------|
| `sources/optional/m0_spike.md` | `docs/eval/fr018_m0_engineering_spike.md` | Thin ingress / URL-first GO |
| `sources/optional/m1.md` | `docs/eval/fr018_m1_discovery_contracts.md` | Contracts |
| `sources/optional/m2.md` | `docs/eval/fr018_m2_url_discovery_ingress.md` | Executable URL ingress |
| `sources/optional/m3.md` | `docs/eval/fr018_m3_production_hardening.md` | SEEK TLS / LinkedIn limits |
| `sources/optional/m4.md` | `docs/eval/fr018_m4_email_job_alert_acquisition.md` | Email + live validation / enrich |

## Regenerating snapshots

```powershell
python scripts/build_masterclass_package.py FR018
```

Snapshots are full-file or mechanical section extracts with a generated banner.
They must not be hand-edited. Repository paths remain authoritative.

The same command **automatically renders sibling PDFs** for:
`Engineering_Masterclass_*.md` (when present), every `sources/*.md`, and every
`sources/optional/*.md`. Use `--no-pdf` for Markdown-only regeneration.
Standalone: `python scripts/render_masterclass_pdf.py --package FR018`.

## Recommended generation order

1. `README.md` — teaching frame  
2. `sources/adr.md` — decisions and out-of-scope  
3. `sources/acceptance.md` — full engineering record (primary)  
4. `sources/optional/m4.md` — original card design → URL enrich lesson  
5. `sources/functional_specification.md` / `domain_model.md`  
6. `sources/optional/m0_spike.md`–`m3.md` for milestone depth  
7. `sources/implementation_notes.md` + `sources/testing_strategy.md`

## Expected outputs

| Artefact | Status |
|----------|--------|
| Lean Masterclass | [Engineering_Masterclass_003_FR018.md](Engineering_Masterclass_003_FR018.md) |
| Masterclass PDF | [Engineering_Masterclass_003_FR018.pdf](Engineering_Masterclass_003_FR018.pdf) |
| Source / optional PDFs | Sibling `.pdf` under [sources/](sources/) (automatic with package build) |
| Gamma Learning Presentation (~15–20) | Owner request |
| Interview Brief / Interview Deck | Owner request |

```powershell
python scripts/build_masterclass_package.py FR018
python scripts/render_masterclass_pdf.py --package FR018
```

## Teaching emphasis (from live acceptance)

1. Unit tests ≠ product readiness for external integrations  
2. Email alerts discover; they are not the JD  
3. Reuse URL acquisition — do not deepen email parse theatre  
4. Live validation improved and simplified design  
5. Live validation is mandatory for board/email integrations  
