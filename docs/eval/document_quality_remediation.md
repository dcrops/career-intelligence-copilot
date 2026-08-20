# Document Quality Remediation — Close-Out

**Status:** **COMPLETE**  
**Date:** 2026-08-13  
**Owner verdict:** **DOCUMENT REMEDIATION COMPLETE**  
**Not a new FR.** Production path change inside existing FR-006 / FR-007 / FR-010 /
FR-014 boundaries.

**Next engineering work:** Application Assistance, resuming from the successful
AAS-0 Playwright spike
([application_assistance_aas0.md](../spikes/application_assistance_aas0.md)).
Do not restart browser automation from scratch. Do not prioritise Indeed
ingestion ahead of that continuation.

A follow-on **Document Positioning** programme is in M0 owner review and does
not reopen this close-out:
[document_positioning_remediation.md](document_positioning_remediation.md).

---

## 1. Problem that triggered remediation

Controlled production documents for Repurpose It
(`opp_01KZQJY6AX3EGX7TGYTHR3ABG1`) were not yet at owner quality for external
use. Issues included CV prose quality vs the Master CV, cover-letter authenticity
and evidence bounds, Truth false-positives on truthful wording, an unsupported
Master “retail” domain claim, and package/export usability. The work was
owner-sequenced remediation and production integration — not a new capability FR.

---

## 2. Accepted CV architecture

```
Master AI Engineer CV
    ↓
deterministic Master adaptation
    ↓
TailoringPlan relevance / selection / evidence bands
    ↓
generated CV
    ↓
Truth Validation
    ↓
owner review
```

Accepted principles:

- Master CV is the editorial/prose baseline (`adapt_from_master=True`).
- CareerProfile remains the evidence authority.
- TailoringPlan remains responsible for relevance and selection.
- Skill evidence bands: `current_hands_on`, `commercial`, `foundational`.
- No LLM CV rewrite on the production package path (`rewrite_summary=False`).
- No arbitrary recency rule.
- Owner quality threshold: READY or MINOR EDIT.
- Operational Intelligence Copilot omission is a known accepted non-blocking
  planner limitation.

Final controlled Repurpose CV: quality accepted; Truth PASS; 38 supported
claims; 0 blocking; 0 review_required.

---

## 3. Accepted cover-letter architecture

```
deterministic CoverLetterPlan
    ↓
deterministic evidence pack
    ↓
one bounded LLM composition call
    ↓
deterministic document framing
    ↓
Truth Validation
    ↓
owner review
```

Accepted principles:

- Evidence determines WHAT may be claimed; the LLM determines HOW approved
  evidence is expressed.
- One composition call only. No autonomous repair/retry loop.
- No deterministic fallback presented as equivalent after LLM failure.
- Independent AI R&D remains distinct from commercial employment.
- Career trajectory: testing/automation → commercial Data Engineering →
  independent AI Engineering.
- Deterministic header owns contact; signature is name-only.
- Bounded prompt/pack policy requires a concrete opening, a short
  Portfolio/GitHub evidence signpost (no body URL dump), and a concise
  evidence-linked close.
- Owner quality threshold: READY or MINOR EDIT.

Final controlled Repurpose cover letter: quality **MINOR EDIT — accepted**;
Truth PASS; no further regeneration after acceptance.

`CoverLetterGenerationService` remains the legacy deterministic composer for
existing FR-007 unit tests. Production `cic package prepare` uses the bounded
path.

---

## 4. Owner-edit preservation

Generated Markdown receives a generated-content SHA-256 fingerprint
(`cv_generated_markdown_sha256` /
`cover_letter_generated_markdown_sha256`).

Ordinary `prepare`:

- if current Markdown still equals last generated content, normal
  generation/update may proceed as designed;
- if current Markdown differs from the fingerprint, or an older package has no
  fingerprint, preserve owner Markdown, refresh rendering/package artefacts as
  required, and do **not** silently overwrite prose.

Explicit `--regenerate` remains the deliberate overwrite mechanism (applies to
both documents).

**Observed limitation (not a current build priority):** the public CLI has no
document-specific `--regenerate-cv` / `--regenerate-cover-letter`. Underlying
`ApplicationPackageService.prepare` already supports independent CV/cover-letter
preservation via per-document fingerprint checks.

---

## 5. Truth Validation corrections

Evidence-boundary corrections during remediation. Gate policy unchanged. Not a
relaxation of Truth. FR-014 remains frozen.

**Duration.** Supported wording of the form “years of experience across X, Y and
Z” follows existing multi-domain overall-engineering duration semantics rather
than being comma-truncated by the generic duration parser. This does **not**
permit unsupported domain-specific tenure claims such as 10+ years of AI
Engineering or Data Engineering.

**Employment delivery.** First-person delivery such as “At [employer], I
developed …” may be supported by employment evidence when the employer is
identified and the claimed responsibility sufficiently matches that employment
entry’s title/highlights/evidence. Named portfolio project validation remains
intact. Invented/unsupported delivery claims remain fail-closed.

---

## 6. Master CV retail correction

Owner-approved durable wording change at the Master source.

Previous: “across retail and consulting environments (Bakers Delight, Console,
AccessHQ)”

Accepted: “at Bakers Delight, Console, and AccessHQ”

“retail” was a genuine Class A domain claim under Truth; CareerProfile did not
authorise retail as a professional domain; retail expertise is not strategically
relevant to target AI roles. The correct fix was removing the unnecessary
abstraction rather than adding irrelevant profile evidence or weakening Truth.

---

## 7. External package behaviour

Authoritative internal artefacts retain opportunity-oriented identity
(`opp_<ULID>.md` / `.pdf` under `career-documents/`). External upload copies
under `data/application_packages/<id>/export/` use human-readable filenames
derived from those artefacts. Filename responsibility remains with
packaging/export, not Playwright.

Accepted convention:

`David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf`  
`David Cropper - REPURPOSE IT PL - AI Engineer - Cover Letter.pdf`

Windows export copies also budget the absolute destination and atomic
`.pdf.tmp` path (conservative 240 characters). Filename-component caps alone
are not sufficient. Canonical opportunity titles are unchanged; short names
that already fit stay unchanged.

---

## 8. Controlled production validation

Opportunity: `opp_01KZQJY6AX3EGX7TGYTHR3ABG1` — REPURPOSE IT P/L — AI Engineer.

| Artefact | Result |
|----------|--------|
| CV | Truth PASS; 38 supported; 0 blocking; 0 review_required; quality accepted |
| Cover letter | Truth PASS; quality MINOR EDIT — owner accepted |
| Package | integrity intact; external-use ALLOWED; `owner_review_required=True` |
| Exports | human-readable CV and cover-letter PDFs produced |

Regression recorded at owner-accepted close-out: focused **140 passed**; full
suite **1693 passed**. Cover letter remained byte-for-byte unchanged during the
final CV (retail) remediation. A subsequent bounded-composer editorial
correction (changelog § 1.135) regenerated the cover letter only; focused **150
passed**; full suite **1696 passed**. Owner accepted that letter as MINOR EDIT
with no further regeneration.

---

## 9. Final owner verdict

**DOCUMENT REMEDIATION COMPLETE**

---

## 10. Known accepted non-blocking limitations

1. Operational Intelligence Copilot may be omitted by current project selection.
2. Cover-letter quality is MINOR EDIT rather than perfect/benchmark-identical.
3. Public CLI has no document-specific `--regenerate-cv`.
4. Owner review remains mandatory.

These are not blockers and must not be reopened merely to achieve theoretical
completeness.
