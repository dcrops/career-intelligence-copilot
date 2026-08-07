# MANIFEST — FR-016 Masterclass Source Package

## Masterclass Title

Multi-Agent Orchestration: Deterministic Supervisor, Bounded Specialists, and Anti-Theatre Design

## Functional Requirement

**FR-016** — Multi-Agent Orchestration

## Repository Version

Changelog **1.104+** (Masterclass packaging); engineering freeze recorded as **1.102 / 1.103**.

## Current Status

**Complete / Frozen / Accepted** — learning proof only (**GO AS LEARNING PROOF ONLY**)

Ordinary preparation remains: `cic agent run`  
Orchestration CLI (optional): `cic agent orchestrate …`

## Completion Date

2026-08-06

## Package root (attach this folder)

`docs/masterclass/FR016/`

## Required documents

Use these snapshots inside the package (regenerated from repository SoT):

| Package path | Authoritative repository path | Notes |
|--------------|-------------------------------|-------|
| `sources/acceptance.md` | `docs/eval/fr016_multi_agent_orchestration.md` | Canonical engineering record + study-aid source |
| `sources/adr.md` | `docs/adr/008_multi_agent_orchestration.md` | Normative architecture decisions |
| `sources/functional_specification.md` | `docs/04_functional_specification.md` § FR-016 | Requirements / acceptance criteria status |
| `sources/domain_model.md` | `docs/06_domain_model.md` § FR-016 | Domain concepts |
| `sources/implementation_notes.md` | `docs/08_implementation_notes.md` § FR-016 M1–M4 | Implementation pointers |
| `sources/testing_strategy.md` | `docs/07_testing_strategy.md` § FR-016 coverage | Test expectations |
| `README.md` | (package-local) | Teaching bridge — not a substitute for acceptance |
| `MANIFEST.md` | (package-local) | This file |

## Optional documents

| Package path | Authoritative repository path | When to include |
|--------------|-------------------------------|-----------------|
| `sources/optional/m0_spike.md` | `docs/eval/fr016_m0_engineering_spike.md` | Theatre rejection / topology rationale |
| `sources/optional/m1.md` | `docs/eval/fr016_m1_orchestration_contracts.md` | Contracts deep dive |
| `sources/optional/m2.md` | `docs/eval/fr016_m2_supervisor_runtime.md` | Runtime + go/no-go evidence |
| `sources/optional/m3.md` | `docs/eval/fr016_m3_owner_cli.md` | Owner CLI |
| `sources/optional/m4.md` | `docs/eval/fr016_m4_evaluation.md` | Final corpus / product-value honesty |

## Regenerating snapshots

```powershell
python scripts/build_masterclass_package.py FR016
```

Snapshots are full-file or mechanical section extracts with a generated banner.
They must not be hand-edited. Repository paths remain authoritative.

## Recommended generation order

1. `README.md` — teaching frame, outcomes, constraints  
2. `sources/adr.md` — decisions and out-of-scope  
3. `sources/acceptance.md` — full engineering record (primary)  
4. `sources/functional_specification.md` — requirements status  
5. `sources/domain_model.md` — concept map  
6. `sources/optional/m0_spike.md` — why theatre was rejected  
7. `sources/optional/m2.md` — go/no-go evidence  
8. `sources/optional/m4.md` — corpus and product-value verdict  
9. `sources/implementation_notes.md` + `sources/testing_strategy.md` — ops/test anchors  
10. Optional: `m1.md`, `m3.md` for depth  

## Expected outputs

Academy generators should produce (outside this repository unless later requested):

- Engineering Masterclass narrative (architecture, authority, handoffs)
- Interview Q&A grounded in acceptance study-aid source (§25)
- Diagrams derived from acceptance Mermaid (do not invent new architecture)
- Explicit statement: learning proof; prefer direct BOPA for ordinary prep

**Do not** invent new specialists, waive truth, claim strong near-term product value,
or contradict ADR-008.

## Design contract

| Principle | How this package satisfies it |
|-----------|-------------------------------|
| Single folder attachment | Attach `FR016/` |
| Minimal manual effort | Regenerable `sources/` + this manifest |
| No duplicated engineering | Snapshots only; edit SoT in `docs/` |
| Repository remains authoritative | Banner + regenerate script |
| Easy regeneration | `scripts/build_masterclass_package.py` |
| Future-proof | Register new FRs in the build script after freeze |
