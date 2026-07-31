# FR-010 M1 — Application Package Durability & Regeneration

**Date:** 2026-07-31  
**Status:** Complete (M1) — historical milestone record. FR-010 closed out:
[fr010_application_package.md](fr010_application_package.md). Followed by
[M2 owner CLI](fr010_m2_owner_cli.md).  
**Architecture:** Standalone `ApplicationPackageService` preserved; ADR-002 / ADR-003 /
ADR-004 unchanged.  
**Preceding milestone:** [FR-010 M0](fr010_m0_application_package.md)

---

## 1. Architecture changes

No architectural expansion. M1 hardens durability inside the existing service:

| Change | Purpose |
|--------|---------|
| Relative draft path persistence | Deterministic, portable manifests |
| Path resolution on `get` / `prepare` return | Callers still receive absolute usable paths |
| `exists` / `verify_artefacts` | Explicit load and integrity surface |
| Documented write-order commit point | Clear regeneration / failure semantics |
| M0 absolute-path compatibility | Existing manifests remain loadable |

Still out of scope: orchestration, versioning, PipelineStatus, submission, PDF/DOCX.

---

## 2. Regeneration model

1. Generate Tailoring Plan, CV, Cover Letter Plan, and Cover Letter **in memory**.
2. Overwrite CV drafts under the stable stem `opportunity_id`.
3. Overwrite cover-letter drafts under the same stem.
4. Atomically replace `manifest.json` (temp-then-replace).
5. Resolve paths and verify draft files before returning.

Identity remains 1:1 with Opportunity. There is no package history.

---

## 3. Failure behaviour

| Failure point | Result |
|---------------|--------|
| Gate / generation error before writes | No durable change; prior package unchanged |
| Draft write error before manifest save | Prior **manifest** remains current; some draft files may already be overwritten |
| Missing drafts on `get(verify=True)` | `ApplicationPackageIntegrityError` |
| `get(verify=False)` | Loads manifest without checking draft files |

This is the smallest deterministic safeguard: the manifest is the commit point.
Re-running `prepare` converges draft bytes and the current package.

---

## 4. Idempotency guarantees

Given identical:

- Opportunity artefacts / strategy
- Career profile
- FR-006 / FR-007 options
- `prepared_at`

repeated `prepare` calls produce:

- identical resolved manifests
- identical persisted relative manifests
- identical draft file bytes

Changing only `prepared_at` updates that field and overwrites the same draft paths.

---

## 5. Persistence changes

Persisted draft refs now use relative filenames:

```json
"cv": {
  "stem": "opp_…",
  "output_dir": ".",
  "markdown_path": "opp_….md",
  "html_path": "opp_….html",
  ...
}
```

`ApplicationPackageService.get` resolves them against the configured CV / cover-letter
output directories. Absolute paths from M0 manifests still resolve and verify.

---

## 6. Tests added

| Suite | Coverage |
|-------|----------|
| `tests/unit/application_package/test_durability.py` | exists/reload; relative persistence; byte idempotency; repeated regen; failed regen keeps prior package; integrity check; M0 absolute compat; immutable evidence |
| `tests/functional/test_fr010_application_package.py` | durability journey: reload → regenerate → failed regen safety |

Focused FR-010 suites: **21 passed**.

---

## 7. Manual validation

```
python scripts/run_fr010_application_package_manual.py demo \
  --workspace data/_fr010_m1_manual
```

| Check | Result |
|-------|--------|
| Create package after apply | Pass |
| `exists` / reload equal | Pass |
| Relative persistence + absolute resolve | Pass |
| Idempotent prepare (same stamp) | Pass |
| Repeated regeneration same paths | Pass |
| Upstream FR-002–FR-005 immutable | Pass |

Offline only — no live acquisition.

---

## 8. Documentation updates

- Functional specification — M1 durability guarantees
- Domain model, testing strategy, implementation notes
- Roadmap, changelog, phase history, repository guide, executive summary
- `AGENTS.md`, `README.md`, `data/application_packages/README.md`, ADR index

No new ADR — behaviour stays inside existing boundaries.

---

## 9. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| Partial draft overwrite on mid-write failure | implementation complete / accepted | Manifest commit point; re-prepare converges |
| Temp-dir then rename for both draft sets | future enhancement | Would avoid partial draft overwrite; not required for single-user M1 |
| CLI / owner UX | deliberate deferral | M2 candidate |
| PipelineStatus `preparing` | deliberate deferral | FR-012 |
| Orchestration package node | deliberate deferral | ADR-003 reconsideration evidence required |
| Package versioning | deliberate deferral | Owner ruled out |

---

## 10. Recommendations for M2

| Recommendation | Classification |
|----------------|----------------|
| Owner-facing `cic` package prepare/show command | future enhancement |
| Clearer material-benefit override UX when applying then packaging | future enhancement |
| Optional transactional draft staging (temp → rename) | future enhancement |
| Orchestration / submission / PipelineStatus integration | deliberate deferral |
| Package versioning | deliberate deferral |

Validate first. Change second. Do not expand architecture without failing product evidence.

---

## Full suite

```
python -m pytest -q
1040 passed in 21.63s
```

Baseline at M0 close was 1031; M1 adds 9 focused durability tests.
