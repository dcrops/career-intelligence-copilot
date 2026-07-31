# FR-010 M0 — Application Package Preparation (Vertical Slice)

**Date:** 2026-07-30  
**Status:** Complete (M0) — historical milestone record. FR-010 closed out:
[fr010_application_package.md](fr010_application_package.md). Succeeded by
[M1 durability](fr010_m1_package_durability.md) and [M2 CLI](fr010_m2_owner_cli.md).  
**Architecture:** Standalone composition service over FR-006 / FR-007; ADR-002 and
ADR-004 boundaries preserved; ADR-003 orchestration unchanged.  
**Preceding capability:** [FR-009 acceptance](fr009_opportunity_review_queue.md)

---

## 1. Architecture implemented

`career_intelligence.application_package.ApplicationPackageService` prepares one
current Application Package for an Opportunity whose owner decision is **`apply`**.

```
Opportunity (decision=apply)
  → OpportunityService.load_artifacts()
  → TailoringPlanService + CvGenerationService (FR-006)
  → CoverLetterPlanService + CoverLetterGenerationService (FR-007)
  → existing draft writers (Markdown / HTML / JSON)
  → ApplicationPackageManifest under data/application_packages/{id}/manifest.json
```

- Does **not** extend the FR-008 runner or change FR-009 review/ranking behaviour.
- Does **not** write `PipelineStatus`.
- Does **not** mutate Opportunity index rows or immutable FR-002–FR-005 snapshots.
- Package identity equals `opportunity_id`; regeneration **replaces** the previous
  package (no versioning in M0).

---

## 2. Public APIs introduced

| API | Role |
|-----|------|
| `ApplicationPackageService.prepare(...)` | Compose FR-006/007 outputs; write drafts; persist manifest |
| `ApplicationPackageService.get(opportunity_id)` | Reload current manifest |
| `ApplicationPackageService.from_paths(...)` | Explicit workspace composition |
| `OpportunityService.load_artifacts(opportunity_id)` | Public rehydration of trusted FR-002–FR-005 snapshots |
| `OpportunityArtifacts` | Typed posting / analysis / assessment / match / strategy bundle |

Callers supply existing FR-006 / FR-007 options (`owner_approved_to_tailor`,
`tailoring_plan_approved`, `owner_approved_to_plan`, `cover_letter_plan_approved`,
optional `override_material_benefit`). The package service invents no new approval
concepts.

---

## 3. Package manifest design

`ApplicationPackageManifest` fields:

| Field | Content |
|-------|---------|
| `opportunity_id` | Package identity (1:1 with Opportunity for M0) |
| `prepared_at` | Preparation timestamp |
| `evidence` | `artifact_paths`, acquisition provenance, optional `strategy_summary` |
| `cv` | Stem + Markdown / HTML / JSON / plan JSON paths |
| `cover_letter` | Stem + Markdown / HTML / JSON / plan JSON paths |
| `owner_review_required` | Always `True` |

Generated document bytes remain under the existing draft directories (or a caller-
supplied workspace). Opportunity persistence is never used as a document store.

---

## 4. Evidence traceability model

The manifest copies:

- Opportunity `artifact_paths` for posting, job analysis, assessment, portfolio match,
  and strategy
- Acquisition identity facets (`source_kind`, URLs, company, title, fingerprint)
- Denormalised `strategy_summary` when present on the Opportunity

Upstream snapshot bytes are asserted unchanged after prepare/regenerate.

---

## 5. Reused components

| Component | Use |
|-----------|-----|
| `TailoringPlanService` / `DeterministicTailoringPlanner` | FR-006 Phase A |
| `CvGenerationService` / `write_tailored_cv_drafts` | FR-006 Phase B + drafts |
| `CoverLetterPlanService` / `DeterministicCoverLetterPlanner` | FR-007 Phase A |
| `CoverLetterGenerationService` / `write_cover_letter_drafts` | FR-007 Phase B + drafts |
| `OpportunityService` | Eligibility + artefact load |
| `CareerProfile` / `CareerProfileService` | Profile input for generation |

---

## 6. New persistence introduced

```
data/application_packages/
  README.md
  {opportunity_id}/
    manifest.json
```

Live manifests are gitignored (`data/application_packages/**` with README exception).
No new Opportunity artefact keys; ADR-002 immutable snapshots remain closed.

---

## 7. Tests added

| Suite | Path |
|-------|------|
| Unit | `tests/unit/application_package/test_service.py` |
| Functional | `tests/functional/test_fr010_application_package.py` |

Coverage: apply eligibility; non-apply refusal; manifest references; evidence
traceability; replace-on-regenerate; FR-006/007 gate enforcement; immutable upstream
artefacts; public `load_artifacts`.

---

## 8. Manual validation performed

```
python scripts/run_fr010_application_package_manual.py demo \
  --workspace data/_fr010_m0_manual
```

Results:

| Check | Result |
|-------|--------|
| Undecided refused | Pass |
| Skip refused | Pass |
| Apply prepares CV + cover letter package | Pass |
| Manifest traces artefact paths + acquisition | Pass |
| Reload equals prepared manifest | Pass |
| Regeneration replaces `prepared_at`, same draft paths | Pass |
| FR-002–FR-005 bytes unchanged | Pass |
| `PipelineStatus` remains `assessed` | Pass |

Offline only — no live acquisition.

---

## 9. Documentation updated

- `docs/04_functional_specification.md` — FR-010 M0 decisions and status
- `docs/06_domain_model.md` — Application Package entity
- `docs/07_testing_strategy.md` — FR-010 M0 coverage
- `docs/08_implementation_notes.md` — architecture notes
- `docs/10_roadmap.md`, `docs/11_changelog.md`, `docs/12_phase_history.md`
- `docs/00_repository_guide.md`, `docs/01_executive_summary.md`
- `AGENTS.md`, `README.md`
- `data/application_packages/README.md`

No new ADR: M0 composes existing boundaries without amending ADR-002/003/004 decisions.

---

## 10. Risks or technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| Material-benefit override often needed for non-platinum/gold apply decisions | implementation complete / known behaviour | Existing FR-006/007 gates; M0 composes them rather than auto-overriding |
| Draft paths stored as absolute strings in the manifest | future enhancement | Adequate for single-user local workspace; relative paths may help portability later |
| No CLI command yet | deliberate deferral | Manual script + public service are enough for M0 |
| `PipelineStatus.preparing` unused | deliberate deferral | Belongs to FR-012; recommendations already recognise the value |
| Orchestration `prepare_package` node unused | deliberate deferral | Reserved id only; M0 intentionally stays outside the runner |

---

## 11. Future recommendations for M1

| Recommendation | Classification |
|----------------|----------------|
| Optional relative path normalisation for draft refs | future enhancement |
| Owner-facing `cic` CLI for prepare/show package | future enhancement |
| Clearer owner UX for material-benefit override when applying then packaging | future enhancement |
| Persist package readiness as a derived signal only (never a second SoT) | deliberate deferral until needed |
| Orchestration / second interrupt integration | deliberate deferral — requires ADR-003 reconsideration evidence |
| PipelineStatus `preparing` write | deliberate deferral — FR-012 |
| Package versioning | deliberate deferral — owner ruled out for M0 |
| Submission / PDF / DOCX | deliberate deferral — later FRs |

Do not expand architecture without failing product evidence. Validate first; change second.

---

## Full suite

```
python -m pytest -q
1031 passed in 19.58s
```

Baseline at FR-009 freeze was 1019; M0 adds 12 focused tests.
