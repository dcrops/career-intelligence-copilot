# Document Positioning M2 — Engineering / Acceptance Report

**Status:** **Complete — owner approved 2026-08-20; M3 authorised**  
**Date:** 2026-08-20  
**Scope:** Canonical capability identities in the live TailoringPlan planner.  
**Programme:** [document_positioning_remediation.md](document_positioning_remediation.md)

No production document-generation architecture change beyond planner
classification. No CSK regeneration. No SEEK / Playwright / AAS.
PositioningPlan is **not** wired into `cic package prepare`.

Owner approved 2026-08-20. M3 was authorised separately.

---

## 1. What was built

The production `DeterministicTailoringPlanner` now classifies employer
requirements through `classify_requirement()` in
`career_intelligence.document_positioning.catalogue`. PositioningPlan already
used that function. Both plans now share one semantic authority.

M2 is **not** a document-generation milestone. Master-adapt CV generation and
bounded cover-letter composition are unchanged. The planner still emits a
TailoringPlan; it does not write CV or letter prose.

Inspection artefact:
[document_positioning_m2_inspection.md](document_positioning_m2_inspection.md)
(regenerate with `python scripts/inspect_m2_plans.py`).

---

## 2. Live planner audit (before the change)

File: `src/career_intelligence/cv_generation/deterministic_planner.py`.

| Mechanism | Pre-M2 behaviour |
|-----------|------------------|
| DIRECT | `_direct_match`: exact normalised phrase, or compatible token subset (`python` → `python programming`). `Java` ≠ `JavaScript`. |
| RELATED | `_related_match`: **exact** membership in `_RELATED_CAPABILITY_GROUPS`. No substring matching. |
| TailoringPlan | `candidate_support`: `supported` / `related` / `unsupported`. RELATED themes and promotions used the **profile** label. |
| Skill promotion | Per-skill `_direct_match` / `_related_match` against each JD technology. |

Why this failed the CSK-shaped case: `RAG` and `Retrieval-Augmented Generation`
are not a token subset, so acronym matching depended on luck. `AWS` and `AWS
Bedrock` were not in the same group, so Bedrock was unsupported rather than
RELATED. The LLM group included `retrieval augmented generation`, which is
semantically unsafe (a RAG system is not a generic LLM/platform claim).

---

## 3. Canonical catalogue integration

Planner path:

1. `classify_requirement(label, profile_caps)` — catalogue identities.
2. If DIRECT or RELATED, use that result.
3. Else try token-compatible `_direct_match` (preserves `python` /
   `python programming` and similar).
4. If the requested label is still a **known** identity and unmatched →
   UNSUPPORTED. Leftover phrase groups are **not** applied.
5. If the requested label is **unknown**, leftover `_RELATED_CAPABILITY_GROUPS`
   may still RELATED-match.

PositioningPlan continues to call `classify_requirement` directly. Shared
JobAnalysis technologies must agree.

---

## 4. DIRECT

DIRECT means the requested employer capability and candidate evidence resolve
to the **same** canonical identity (or, for unknown labels, exact normalised /
token-compatible match).

Examples proven:

- `RAG` ↔ `Retrieval-Augmented Generation` → identity `rag` → DIRECT.
- Profile skill `LLM application development` + JD `LLM` → identity `llm` →
  DIRECT. Not a RAG shortcut.
- Unknown `TypeScript` + profile `TypeScript` → DIRECT.

The requested identity may be promoted as a candidate skill when DIRECT.
Headline promotion still respects the existing prominence band: professional-
development-only skills are not headlined (`LLM application development` is
DIRECT on E1 but PD-only, so it is classified supported and not added to
`skills_to_promote`).

---

## 5. RELATED

RELATED means the catalogue defines an explicit transfer between **different**
identities. The plan retains:

- requested capability identity
- related candidate capability identity / profile label
- `may_claim_requested=False`

TailoringPlan stores that on `JdPriority` as `candidate_support="related"`,
`related_profile_capability`, `requested_capability_identity`, and
`may_claim_requested`. The requested employer technology is **never** added to
`skills_to_promote`.

Example: JD AWS Bedrock + profile AWS → promote AWS; do not claim Bedrock.

---

## 6. UNSUPPORTED

Known identity with no direct or related profile evidence: UNSUPPORTED.
Unknown label with no exact/token match and no leftover-group partner:
UNSUPPORTED. No dynamically invented RELATED links.

---

## 7. Legacy `_RELATED_CAPABILITY_GROUPS` migration

Migrated into the catalogue (justified by live planner behaviour + eval cases):

| Requested identity | Related profile identities |
|--------------------|----------------------------|
| `aws_bedrock` | `aws` |
| `azure` | `azure_data_factory`, `microsoft_fabric` |
| `azure_data_factory` | `azure`, `microsoft_fabric`, `data_pipeline` |
| `microsoft_fabric` | `azure`, `azure_data_factory` |
| `data_pipeline` | `azure_data_factory` |
| `llm` | `openai`, `langchain` |
| `openai` / `langchain` | `llm`, each other |
| `rest` / `fastapi` | each other |

**Deliberately not migrated (unsafe):** RAG ↔ LLM. The old LLM group included
`retrieval augmented generation`. A retrieval system is not evidence for every
LLM/platform claim. Dropped; covered by a negative test.

**Leftover groups** (after a catalogue miss, including known identities with
no catalogue relation): CI/CD / Jenkins / deployment; observability /
CloudWatch; AI-engineering role-family phrases; bare `pipeline`/`pipelines`
with ADF (so a JD technology named `pipeline` still relates to ADF, without
making the word “pipelines” inside “evaluation pipelines” a catalogue
identity). The unsafe RAG↔LLM pairing is not in leftover groups.

---

## 8. LLM capability finding

CareerProfile contains skill **`LLM application development`** (evidence:
`experience:ai-engineering-development-2025`) plus OpenAI APIs, LangChain, and
RAG.

Chosen semantics:

- Alias `llm application development` / `llm` / `llms` → identity `llm`.
- E1 JD `LLM` is therefore **DIRECT**.
- `RAG` remains a **different** identity. `classify_requirement("LLM",
  ["Retrieval-Augmented Generation"])` is UNSUPPORTED.
- Profile with OpenAI APIs + LangChain **without** the LLM skill (existing
  planner fixture) stays **RELATED** for a JD `LLM` requirement.

This models what the candidate can truthfully claim. It does not optimise E1's
match count via a RAG→LLM shortcut.

Limitation (existing prominence policy, not new): the LLM skill is
professional-development-only, so TailoringPlan classifies DIRECT but does not
headline that skill. OpenAI APIs may still appear via stronger evidence or
role-family anchors.

---

## 9. PositioningPlan / TailoringPlan consistency

Both consume `classify_requirement`. Tests assert agreement on every shared
JobAnalysis **technology** for the specialist synthetic job and E1–E4.

They are not the same component: PositioningPlan selects evidence refs, spine,
forbidden claims, trajectory, and methodology. TailoringPlan decides CV
emphasis (projects, headline skills, summary themes). Shared **truth** is the
catalogue; shared **prose** is not.

Catalogue expansion side effect (PositioningPlan only): E1 responsibility text
contains “data pipelines”, now a `data_pipeline` alias, so PositioningPlan
adds a RELATED need (promote ADF, do not claim the generic pipeline identity).
That need is not a JobAnalysis technology, so it does not appear on the
TailoringPlan technology table. Conservative and explicit.

---

## 10. E1–E4 inspection

See [document_positioning_m2_inspection.md](document_positioning_m2_inspection.md).

| Job | Result |
|-----|--------|
| E1 Allura | Python DIRECT; REST APIs DIRECT; LLM DIRECT via `LLM application development`; Google Cloud / MLOps / DevOps UNSUPPORTED |
| E2 CSK | RAG DIRECT; AWS Bedrock RELATED via AWS (`may_claim_requested=False`); chatbot/conversational AI UNSUPPORTED; Bedrock not in `skills_to_promote` |
| E3 Maincode | GPU / Linux / HPC UNSUPPORTED; role-family anchors may still headline truthful AI skills (Python/FastAPI/…) — not GPU employment |
| E4 Repurpose | Copilot / Claude / AI tools UNSUPPORTED; PositioningPlan `trajectory_mode=full_chapters` unchanged |

Correct gaps are success. M2 is not “more green matches.”

---

## 11. Tests

- `tests/unit/document_positioning/test_m2_semantics.py` — A–R plus OpenAI-only
  RELATED LLM and leftover CI/CD.
- `tests/unit/document_positioning/test_eval_jobs_m2.py` — E1–E4 planner +
  agreement.
- Catalogue additions in `test_catalogue_v1.py` (LLM DIRECT, RAG↛LLM, Fabric).
- Isolation test updated: planner may import **catalogue only**, not
  `PositioningPlan` / `build_positioning_plan`.

`python -m pytest tests/unit/document_positioning -q` → **69 passed**.

Planner / package regressions kept green:
`test_deterministic_planner.py`, `test_planner_corpus_regression.py`,
`test_azure_jd_promotes_azure_data_factory`, `test_plan_service.py`,
`test_generation_service.py`, `test_master_adapt.py`,
`test_production_integration.py`.

M0/M1 tests were not weakened.

---

## 12. Schema

Bounded optional fields on `JdPriority`:

- `requested_capability_identity`
- `may_claim_requested`

Existing `candidate_support` + `related_profile_capability` already distinguished
promote-profile vs gap-requested. The extra fields preserve catalogue provenance
for M3 without redesigning TailoringPlan.

---

## 13. Known catalogue limits

- The catalogue is still small and explicit. Unknown tools do not invent RELATED.
- Bare `pipeline` is not a catalogue alias (would fire on “evaluation pipelines”).
- Token-compatible DIRECT remains for unknown labels and as a fallback for known
  identities (`python programming`).
- Prominence bands still suppress PD-only headline skills.
- Role-family anchors still fill sparse JD overlap (E3). That is pre-M2 behaviour.

---

## 14. Definition of Done

- [x] Existing live capability planner audited
- [x] Canonical identities integrated into live TailoringPlan planning
- [x] RAG alias DIRECT behaviour proven
- [x] AWS→Bedrock RELATED behaviour proven
- [x] RELATED never promotes requested skill as candidate capability
- [x] LLM classification investigated from actual CareerProfile evidence
- [x] Java/JavaScript negative case preserved
- [x] RAG/chatbot negative case preserved
- [x] Existing justified Azure/ADF/Fabric semantics preserved
- [x] PositioningPlan and TailoringPlan use consistent semantic authority
- [x] Four frozen jobs inspected
- [x] Semantic unit tests pass
- [x] Relevant existing planner/package regressions pass
- [x] Production document generation architecture otherwise unchanged
- [x] PositioningPlan still not wired into package generation
- [x] No CV/cover-letter regeneration
- [x] No SEEK/Playwright/AAS
- [x] M2 acceptance report written
- [x] Learning note written
- [x] Documentation/changelog updated
- [x] Owner review required before M3
