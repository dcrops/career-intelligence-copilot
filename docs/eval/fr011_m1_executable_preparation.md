# FR-011 M1 — Executable Preparation Workflow

**Date:** 2026-07-31  
**Status:** Complete (M1) — historical milestone record. FR-011 closed out:
[fr011_application_preparation.md](fr011_application_preparation.md).  
**Architecture:** Thin `cic preparation` CLI over `ApplicationPreparationOrchestrator`;
no business-rule changes. ADR-002 / ADR-003 / ADR-004 unchanged.  
**Preceding milestone:** [FR-011 M0](fr011_m0_application_preparation.md)

---

## 1. Architectural decisions

| Decision | Choice |
|----------|--------|
| Adapter | Typer `preparation` sub-app — interface only |
| Sequencing | Remains in `ApplicationPreparationOrchestrator` |
| Package rules | Remains in `ApplicationPackageService` |
| Gates | `--approve` required; FR-006/007 options pass through |
| Direct package CLI | `cic package` remains supported (parallel pathway) |
| Failed runs | Orchestrator returns failed state; CLI exits non-zero |

No FR-008 extension, PipelineStatus, resume, or routing module.

---

## 2. Implementation summary

| Command | Behaviour |
|---------|-----------|
| `cic preparation run <opp_id> --approve` | `ApplicationPreparationOrchestrator.run` |
| `cic preparation show <run_id>` | `ApplicationPreparationOrchestrator.get` |

Shared options: `--dir`, `--packages-dir`, `--runs-dir`, `--profile`, `--cv-dir`,
`--cover-letter-dir`, `--yaml`, `--override-material-benefit` (run only).

---

## 3. Validation evidence

### Unit

`tests/unit/application_preparation/test_cli.py`:

- run requires `--approve`
- run → show happy path; package verifyable
- non-apply → failed run, exit 1
- missing run show fails closed
- YAML run output

### Manual

```
python scripts/run_fr011_preparation_manual.py cli --workspace data/_fr011_m1_manual
```

RESULT: PASS (offline).

### Full suite

```
python -m pytest -q
1059 passed in 24.22s
```

Baseline at M0 was 1054; M1 adds 5 CLI tests.

---

## 4. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| `cic package` and `cic preparation` both prepare | accepted | Intentional parallel pathways |
| No resume / retry | deliberate deferral | Out of FR-011 |
| FR-008 `prepare_package` unused | deliberate deferral | ADR-003 |

---

## 5. Readiness for FR-011 close-out (historical)

M0 + M1 delivered the documented FR-011 objective. Close-out completed —
[fr011_application_preparation.md](fr011_application_preparation.md).
