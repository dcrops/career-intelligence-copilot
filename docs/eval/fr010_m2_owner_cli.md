# FR-010 M2 — Owner Operations & CLI

**Date:** 2026-07-31  
**Status:** Complete (M2) — historical milestone record. FR-010 closed out:
[fr010_application_package.md](fr010_application_package.md).  
**Architecture:** Thin CLI adapter over `ApplicationPackageService`; no business-rule
changes. ADR-002 / ADR-003 / ADR-004 unchanged.  
**Preceding milestones:** [M0](fr010_m0_application_package.md),
[M1](fr010_m1_package_durability.md)

---

## 1. Architecture

`cic package` is a Typer sub-app on the existing CLI. It constructs
`ApplicationPackageService` and maps owner commands to public service methods.
Eligibility, FR-006/007 gates, regeneration, and integrity checks stay in the service.

No orchestration, workflow, persistence-schema, ranking, duplicate, or submission
changes.

---

## 2. CLI design

| Command | Behaviour |
|---------|-----------|
| `prepare <opp_id>` | Requires `--approve` to set FR-006/007 owner-approval gates; optional `--override-material-benefit`; optional `--yaml` |
| `show <opp_id>` | Compact summary or `--yaml`; optional `--no-verify` |
| `verify <opp_id>` | Loads with `verify=True`; prints intact or fails closed |

Shared options: `--dir`, `--packages-dir`, `--profile`, `--cv-dir`, `--cover-letter-dir`.

Without `--approve`, prepare refuses with a clear owner message — gates are not
silently defaulted to true.

---

## 3. Owner operations

Typical offline flow after an apply decision:

```
cic opportunity decide <opp_id> apply
cic package prepare <opp_id> --approve [--override-material-benefit]
cic package show <opp_id>
cic package verify <opp_id>
```

Owner review of generated drafts remains mandatory before external use
(`owner_review_required=True` on the package and artefacts).

---

## 4. Service reuse

| CLI concern | Reused API |
|-------------|------------|
| Prepare / regenerate | `ApplicationPackageService.prepare` |
| Show | `ApplicationPackageService.get` |
| Verify | `ApplicationPackageService.get(verify=True)` |
| Opportunities / profile | `OpportunityService`, `CareerProfileService` |
| Gates | Existing `TailoringOptions` / `CvGenerationOptions` / cover-letter options |

No duplicated document-generation logic.

---

## 5. Tests

`tests/unit/application_package/test_cli.py`:

- prepare requires `--approve`
- prepare → show → verify happy path
- YAML prepare/show
- non-apply refused
- missing package
- verify detects missing draft
- `--no-verify` loads when a draft is missing

---

## 6. Manual validation

```
python scripts/run_fr010_application_package_manual.py cli \
  --workspace data/_fr010_m2_manual
```

| Check | Result |
|-------|--------|
| Prepare without `--approve` refused | Pass |
| Prepare with `--approve` | Pass |
| Show summary | Pass |
| Verify intact | Pass |
| Show `--yaml` includes evidence | Pass |

Offline only.

---

## 7. Documentation

Updated: functional specification, domain model, testing strategy, implementation notes,
roadmap, changelog, phase history, repository guide, executive summary, AGENTS, README,
ADR index, this eval report.

---

## 8. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| CLI does not invent prepared_at (uses wall clock) | implementation complete / accepted | Service default; fine for owner use |
| No interactive plan-review step before render | deliberate deferral | Existing gates are boolean options; richer review UX is optional later |
| Contact overlay flags not exposed | future enhancement | FR-006/007 support contact; not required for M2 |
| Orchestration / submission / PDF | deliberate deferral | Later FRs |

---

## 9. Recommendations after M2 (historical)

| Recommendation | Classification | Close-out disposition |
|----------------|----------------|------------------------|
| Contact / presentation option flags on CLI | future enhancement | Remains future enhancement |
| Optional interactive two-step plan approval UX | future enhancement | Remains future enhancement |
| Package list command across opportunities | future enhancement | Remains future enhancement |
| FR-010 close-out / freeze | deliberate deferral until owner decides | **Done** — [fr010_application_package.md](fr010_application_package.md) |
| Submission / orchestration / PipelineStatus | deliberate deferral | Remains deliberate deferral (FR-011 / FR-012 / ADR-003) |

See the freeze report for the authoritative remaining-debt classification.

---

## Full suite

```
python -m pytest -q
1047 passed in 23.73s
```

Baseline at M1 close was 1040; M2 adds 7 CLI tests.
