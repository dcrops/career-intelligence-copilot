# Engineering Learning Academy — Masterclass Generator (Lean Edition)

**Use this prompt** when generating an Engineering Masterclass from a frozen
Masterclass Source Package (`docs/masterclass/FRnnn/`).

**Binding standard:** [LEAN_MASTERCLASS_STANDARD.md](LEAN_MASTERCLASS_STANDARD.md)  
**Do not** invent engineering that contradicts the package acceptance report or ADR.

---

## Prompt (copy for Academy generation)

```text
# Engineering Learning Academy
# Masterclass Generator — Lean Edition

The attached files are the complete Masterclass Source Package for one frozen
Functional Requirement.

Treat the package as the authoritative educational source for this generation.
Repository acceptance reports and ADRs remain the engineering source of truth;
do not invent conflicting architecture.

## Objective

Generate ONE Engineering Masterclass narrative.

Teach the engineering. Do NOT reproduce repository documentation.

## Required teaching focus

• the engineering problem
• why previous approaches were insufficient
• the chosen architecture
• the engineering principles
• the validation
• the trade-offs
• the interview preparation
• the three engineering lessons to remember

## Permanent required sections (Academy standard)

Also include these short sections — mandatory for every Masterclass:

1. Runtime Example
   - Exactly ONE simple conceptual engineering runtime flow
   - Engineering-focused; no implementation detail
   - Suitable for Gamma to turn into a diagram

2. Why Employers Care
   - Short explanation of transferable engineering value to an employer
   - No salary, recruiting, or marketing language

3. Validation Summary
   - Compact callout: major outcome, key counts, recommendation, important constraints
   - Suitable for Gamma visual callout boxes

4. Memorable Closing Statement
   - One concise engineering takeaway at the end
   - Memorable enough to become the final presentation slide

## Constraints

• Lean Edition — target approximately 8–12 pages
• Do not significantly inflate length to satisfy the permanent sections
• Do not generate slides
• Do not generate presentation notes
• Do not generate image prompts

## Output

A single Masterclass markdown document that prepares an experienced software
engineer to explain this Functional Requirement confidently in a technical
interview, and that can later be imported into Gamma.
```

---

## Operator notes

- Attach `docs/masterclass/FRnnn/` (README, MANIFEST, `sources/`).  
- After generation, store the narrative beside the package when the owner requests
  in-repo retention (e.g. `Engineering_Masterclass_00N_FRnnn.md`).  
- **Mandatory next step:** render the official PDF study edition:

```powershell
python scripts/render_masterclass_pdf.py docs/masterclass/FRnnn/Engineering_Masterclass_00N_FRnnn.md
```

- Packaging (`sources/` snapshots) is separate from Masterclass generation — see
  [PACKAGING.md](PACKAGING.md).  
- Deep learning workflow: Markdown Masterclass → **Masterclass PDF** → Gamma
  **Learning** Presentation (~15–20).  
- Rapid revision (after deep learning): **Interview Brief** → **Interview Deck**
  → coaching — see [INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md) and
  [INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md).  
- This generator produces the Lean Masterclass only — not Briefs, Decks, or slides.
