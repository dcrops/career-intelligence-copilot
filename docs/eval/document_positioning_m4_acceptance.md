# Document Positioning M4 — Engineering / Acceptance Report

**Status:** **Complete — owner approved 2026-08-20; M5 authorised and later blocked on live generation**  
**Date:** 2026-08-20  
**Scope:** Employer-need-driven cover-letter positioning (selection, pack, bounded writer).  
**Programme:** [document_positioning_remediation.md](document_positioning_remediation.md)

`cic package prepare` still uses the pre-M4 bounded cover letter
(`BoundedCoverLetterService` + CoverLetterPlan project selection). M6 owns
wiring this composer into prepare. No CSK regeneration. No SEEK / Playwright /
AAS. No M5 A/B benchmark.

Owner review is required before M5.

---

## 1. Production cover-letter path audit (verified)

```
cic package prepare
  ApplicationPackageService.prepare
        ├─ TailoringPlanService.plan          # M2 catalogue classification
        ├─ CvGenerationService.generate
        │     adapt_from_master=True
        │     NO LLM, NO PositioningPlan
        └─ BoundedCoverLetterService.compose  # UNCHANGED in M4
              CoverLetterPlanService.plan
                DeterministicCoverLetterPlanner
                  select_projects_for_letter  # tag/concern score, designed 2-project cap
              build_cover_letter_evidence_pack
                experience packed as testing → DE → independent AI chapters
              composer (OpenAI or fixture)
              validate_composed_paragraphs
              write drafts + manifest
```

FR-014 remains a **separate** gate (`cic truth validate-package`). Prepare
does not invoke it. Prepare already **fails closed** on bounded-letter
failure; there is no silent deterministic-letter success fallback.

### What is deterministic vs generative today (production)

| Stage | Mode |
|-------|------|
| CoverLetterPlan | DETERMINISTIC |
| Project ranking | DETERMINISTIC score (JD tokens × project tags/concerns + PortfolioMatch emphasis boost) |
| Project count | DETERMINISTIC designed cap: prefer 2; 3 only if the third score is strong |
| Experience packing | DETERMINISTIC chapter walk (testing, data engineering, independent AI) |
| Prose | BOUNDED LLM over that pack |
| Local claim checks | DETERMINISTIC |
| Truth | Separate FR-014 |

### Project-selection findings

`select_projects_for_letter` ranks by tag overlap, concern-cluster hits, maturity,
AI-family boosts, and `portfolio_emphasis` score boost. It does **not** consume
PositioningPlan DIRECT/RELATED/UNSUPPORTED. The two-project cap is a design
choice (M0 correction #4), not an accidental OIC drop. PortfolioMatch can rank
OIC #1 while the letter drops it because a higher tag-density pair filled the cap.

### Biography / trajectory findings

The production pack always includes testing and data-engineering employment when
those titles exist, then independent AI, and instructs the writer to keep chapters
in that order. `PositioningPlan.trajectory_mode` is not consulted. AI-engineer
letters therefore often spend space on QA → DE → AI even when `ai_lead` would
be the stronger argument.

### Discrepancy vs remediation plan

The plan described the production letter as already fail-closed. **Code agrees:**
`ApplicationPackageService._compose_cover_letter` raises
`ApplicationPackageGenerationError` and does not fall back to
`CoverLetterGenerationService`. M4 does not change that path.

---

## 2. Architecture after M4

```
JobAnalysis + CareerProfile + ApplicationStrategy.portfolio_emphasis (ranks only)
        ↓
build_positioning_plan          # deterministic (M1)
        ↓
select_cover_letter_evidence    # employer-need coverage (M4)
        ↓
CoverLetterPositioningPack      # typed, serialisable
        ↓
CoverLetterPositioningComposer  # fixture in tests; OpenAI implemented, unwired
        ↓
validate_cover_letter_positioning_output
        ↓
paragraphs + inspection markdown
```

Public API: `BoundedCoverLetterPositioningService.compose(...)`.

Not called by `ApplicationPackageService.prepare`.

---

## 3. Employer-need coverage model

PositioningPlan is the semantic authority. For each important need the selector
records DIRECT, RELATED, or UNSUPPORTED and which candidate source supports it.

High-priority needs: DIRECT needs (up to 4) plus RELATED needs with rank ≤ 3.
UNSUPPORTED needs never become coverage targets.

Coverage is identity-based (catalogue), not tag density. A source covers a
DIRECT need when it evidences that identity or a supporting identity (for
example FastAPI supports REST). A source covers a RELATED need only via the
**promotable** profile identity (AWS for Bedrock), never by claiming the
requested identity.

This is greedy explainable selection, not an optimiser.

---

## 4. Evidence-source types

Cover-letter evidence may be:

- portfolio project
- commercial employment
- independent engineering
- certification (when it resolves to a catalogue identity)
- trajectory (QA → DE → AI), when `trajectory_mode` is `full_chapters` or `bridge`

Methodology is packed as a writer constraint/flag, not as a counted source,
unless later evidence requires it.

---

## 5. Evidence-count policy

- Default: **two** sources.
- Maximum: **three**.
- A third source is added only when it covers a remaining high-priority
  DIRECT/RELATED need that the first two do not represent.
- If no actionable needs exist (E3 stretch), fall back to two truthful AI
  portfolio sources rather than inventing infrastructure evidence.

---

## 6. PortfolioMatch relationship

PortfolioMatch ranks (`ApplicationStrategy.portfolio_emphasis.source_rank`)
break ties when coverage is equal. They are not the sole authority.

PositioningPlan may override a high-ranked project when another source covers
a high-priority need the ranked project does not. Override reasons are stored
on `portfolio_overrides` and copied onto selected sources.

Example (E2 inspection): CIC rank 1 dropped because Governance RAG covers
DIRECT RAG and nbn employment covers RELATED Bedrock.

---

## 7. trajectory_mode behaviour

| Mode | Evidence strategy |
|------|-------------------|
| `ai_lead` | Testing employment is not a selectable source. No forced QA → DE → AI walk. |
| `bridge` | After the lead source, include one testing/DE employment transfer source. |
| `full_chapters` | Trajectory is a first-class selected source; portfolio supports it. |

Modes shape selection and writer constraints. They are not canned paragraph
templates (the fixture still uses explicit wording for policy tests).

---

## 8. Evidence-pack contract

`CoverLetterPositioningPack` (`letter_pack.py`):

- Role/employer context, including `prose_role_title` (sanitised when the
  posting title contains forbidden/unsupported identities)
- Employer needs with DIRECT / RELATED / UNSUPPORTED
- Argument spine, forbidden claims, trajectory, methodology flag
- Selected sources with purpose, needs covered, PM rank, override reason
- Opening / body / closing facts
- Allowed organisations, project names, technologies
- Constraints for the writer

`OpportunityAssessment` is accepted and **ignored** (`assessment_ignored=True`).

---

## 9. Bounded writer

Reuses the M3 pattern: one structured call over the pack only.

May write 3–5 paragraphs. Must preserve DIRECT vs RELATED, omit unsupported
identities, avoid invented metrics/years/commercial AI/ML, avoid generic
openings, and mention each selected source.

---

## 10. Opening and body strategy

Opening: employer + role label + strongest truthful argument + one or two
packed anchors. Generic patterns (`I am excited to apply`, `I am writing to
apply`, …) fail validation.

Body: one paragraph per selected source, organised around the need that source
covers. RELATED sources use transfer language and must not name the requested
identity as candidate experience. A third paragraph exists only when a third
source was selected. Closing is a short packed-fit sentence.

---

## 11. Validation / fail-closed

| Failure | Result |
|---------|--------|
| Provider / unexpected composer exception | `CoverLetterPositioningProviderError` |
| Empty/malformed structured output | `CoverLetterPositioningValidationError` |
| Forbidden / unsupported / RELATED requested identity as a claim | `CoverLetterPositioningValidationError` |
| Invented metric or years | `CoverLetterPositioningValidationError` |
| Generic opening, duplicate paragraphs, missing selected source | `CoverLetterPositioningValidationError` |
| `ai_lead` forced biography markers | `CoverLetterPositioningValidationError` |

There is **no** successful return that substitutes the legacy generic letter.

FR-014 remains `cic truth validate-package`. M4 validators are local composer
guards, not Truth PASS.

---

## 12. CV / cover-letter consistency

Both composers build the same PositioningPlan classifications. Tests assert
matching DIRECT / RELATED / UNSUPPORTED labels, trajectory mode, and that
neither side claims Bedrock on the specialist job. Wording may differ.

---

## 13. Production wiring status

| Surface | Live after M4? |
|---------|----------------|
| Catalogue in TailoringPlan planner | Yes (M2) |
| `BoundedCvPositioningService` | Implemented, **not** in prepare (M3) |
| `BoundedCoverLetterPositioningService` | Implemented, **not** in prepare (M4) |
| Package cover letter | Still `BoundedCoverLetterService` + tag/concern selection |
| Package CV summary | Still Master baseline |
| PositioningPlan import in prepare/CLI | No |

M6 activates production integration.

---

## 14. E1–E4 (fixture composer)

See [document_positioning_m4_inspection.md](document_positioning_m4_inspection.md).
Regenerate with `python scripts/inspect_m4_letters.py` (`PYTHONPATH=src`).

| Job | Result |
|-----|--------|
| E1 | `ai_lead`; RAG + OIC; Public Holiday rank 1 overridden; GCP/MLOps/DevOps unclaimed |
| E2 | RAG project + nbn AWS employment; CIC/OIC overridden; Bedrock/chatbot unclaimed |
| E3 | Two truthful AI projects (no need overlap); GPU/Linux/HPC unclaimed; stretch risk remains |
| E4 | `full_chapters` trajectory + RAG; Copilot/Claude unclaimed |

Fixture prose is pack-faithful, not recruiter-literary. M5 owns preference.

---

## 15. Tests

`tests/unit/document_positioning/test_m4_cover_letter_positioning.py` (A–Z plus
pack invariants) and `test_eval_jobs_m4.py`.

`python -m pytest tests/unit/document_positioning -q` → **132 passed**.

M0–M3 tests were not weakened. Cover-letter and package production-integration
regressions in this slice stayed green.

---

## 16. Definition of Done

- [x] Current production cover-letter path audited
- [x] Current project-selection logic audited
- [x] Current biography/trajectory policy audited
- [x] Employer-need coverage model implemented
- [x] Evidence-source selection deterministic and inspectable
- [x] Projects are selected for employer-need contribution
- [x] Non-project evidence can be selected where stronger
- [x] Evidence-source count policy explicit and bounded
- [x] PortfolioMatch relationship explicit
- [x] PortfolioMatch override rationale inspectable
- [x] trajectory_mode controls narrative strategy
- [x] Cover-letter evidence pack typed/serialisable
- [x] Bounded writer consumes only approved pack
- [x] DIRECT claims allowed
- [x] RELATED requested claims forbidden
- [x] UNSUPPORTED claims forbidden
- [x] Generic opening policy implemented
- [x] Deterministic evidence/quality validators implemented
- [x] Provider / malformed / validation failures fail closed
- [x] No silent generic-letter fallback
- [x] CV / cover-letter semantic consistency tested
- [x] E1–E4 offline inspection completed
- [x] Maincode checked for over-positioning
- [x] CSK checked for Bedrock/chatbot overclaim
- [x] Repurpose checked for trajectory quality
- [x] Focused M4 tests pass
- [x] Existing cover-letter regressions pass
- [x] M0–M3 document-positioning regressions pass
- [x] Relevant package/generation regressions pass
- [x] M5 A/B benchmark NOT run
- [x] CSK live package NOT regenerated
- [x] SEEK / Playwright / AAS NOT run
- [x] M4 acceptance report written
- [x] M4 inspection report written
- [x] M4 learning note written
- [x] Documentation/changelog updated
- [x] Owner review required before M5
