# Engineering Learning Academy — Masterclass Source

**Purpose:** Stable educational source packages derived from **frozen** engineering
work in this repository.

**Not this folder’s job during FR close-out:** Generate Gamma decks or interview
coaching sessions. Those follow the Lean Masterclass (Markdown + PDF) using the
standards below.

---

## Two learning layers

| Layer | Artefacts | Purpose |
|-------|-----------|---------|
| **Deep learning** | Lean Masterclass (.md), Masterclass PDF, Gamma Learning Presentation (~15–20 slides) | Understanding and reference |
| **Rapid interview revision** | Interview Brief (~1 page), Interview Deck (~3–5 slides) | 2–5 minute refresh; 1–2 minute spoken answer |

Deep learning is **not** replaced. Interview artefacts exist because revising
15–20 slides per FR before an interview is too heavy.

---

## Workflow

```text
Engineering
    ↓
Validation
    ↓
Acceptance
    ↓
Freeze
    ↓
Masterclass Source Package              ← docs/masterclass/FRnnn/
    ↓
Lean Engineering Masterclass (.md)      ← deep learning
    ↓
Masterclass PDF                         ← official study edition
    ↓
Gamma Learning Presentation (15–20)     ← deeper visual learning
    ↓
Interview Brief (1 page)                ← rapid text revision
    ↓
Interview Deck (3–5 slides)             ← rapid visual revision
    ↓
Interview Revision / Coaching           ← conversational practice
```

Frozen acceptance reports and ADRs remain the **canonical engineering record**.

### Artefact roles

| Artefact | Role |
|----------|------|
| Repository documentation | Authoritative engineering truth |
| Lean Masterclass | Authoritative educational source |
| Masterclass PDF | Stable study edition |
| Gamma Learning Presentation | Deeper visual learning (~15–20 slides) |
| Interview Brief | Rapid text revision (~1 page) |
| Interview Deck | Rapid visual revision (~3–5 slides) |
| ChatGPT / interview coaching | Conversational teaching and mock interview |

---

## Standards (permanent)

| Document | Layer |
|----------|-------|
| [LEAN_MASTERCLASS_STANDARD.md](LEAN_MASTERCLASS_STANDARD.md) | Deep learning |
| [MASTERCLASS_GENERATOR_LEAN.md](MASTERCLASS_GENERATOR_LEAN.md) | Deep learning generator prompt |
| [INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md) | Rapid revision — text |
| [INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md) | Rapid revision — visual |

### Lean Masterclass (unchanged spine)

Future Masterclasses **must** follow the Lean standard (~8–12 pages), including:

1. **Runtime Example** — one conceptual engineering flow  
2. **Why Employers Care** — transferable engineering value  
3. **Validation Summary** — compact outcome / counts / recommendation / constraints  
4. **Memorable Closing Statement** — one final takeaway  

PDF after Markdown:

```powershell
python scripts/render_masterclass_pdf.py docs/masterclass/FRnnn/Engineering_Masterclass_00N_FRnnn.md
```

### Interview Brief + Interview Deck

Required for future completed FRs (FR-018+) once deep-learning artefacts exist.
(FR-018 is **Opportunity Discovery & Acquisition** after roadmap § 1.115; do not
assume Recruiter Intelligence.)
Structure and slide count are defined in the standards above — **no rediscovery**.

Do **not** regenerate FR-016 / FR-017 Interview Briefs or Decks unless the owner
explicitly requests them; existing Masterclass and Gamma work stays as-is.

---

## Masterclass Source Package (standard)

After an FR is **Complete / Frozen**, create:

```text
docs/masterclass/FRnnn/
  README.md          # educational bridge (teaching frame)
  MANIFEST.md        # generation contract for Academy AIs
  sources/           # regenerable snapshots of authoritative docs
    …required…
    optional/        # milestone history, etc.
```

After deep-learning generation (typical):

```text
  Engineering_Masterclass_00N_FRnnn.md
  Engineering_Masterclass_00N_FRnnn.pdf
```

After rapid-revision generation (when produced):

```text
  Interview_Brief_FRnnn.md
  (Interview Deck lives in Gamma — optional local export)
```

### How authoritative content is preserved

- Engineering is edited only under `docs/eval/`, `docs/adr/`, and related SoT paths.
- `sources/` files are **generated snapshots** — regenerate; do not hand-edit.
- Regenerate with `python scripts/build_masterclass_package.py FRnnn`.

### Single-folder attachment

Attach `docs/masterclass/FRnnn/` for Academy generation. Follow `MANIFEST.md`, then
Lean Masterclass → PDF → Gamma Learning Presentation → Interview Brief → Interview Deck.

---

## Layout

| Path | Role |
|------|------|
| [LEAN_MASTERCLASS_STANDARD.md](LEAN_MASTERCLASS_STANDARD.md) | Deep learning Masterclass requirements |
| [MASTERCLASS_GENERATOR_LEAN.md](MASTERCLASS_GENERATOR_LEAN.md) | Lean Masterclass generator prompt |
| [INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md) | One-page interview revision |
| [INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md) | 3–5 slide interview deck |
| [FR001/](FR001/) … [FR015/](FR015/) | Placeholders — package when owner requests |
| [FR016/](FR016/) | Packaged — Multi-Agent Orchestration |
| [FR017/](FR017/) | Packaged — Agent Evaluation & Observability |
| [PROJECT/](PROJECT/) | Future overall CIC Masterclass |
| [SUBSYSTEMS/](SUBSYSTEMS/) | Future subsystem Masterclasses |
| [PACKAGING.md](PACKAGING.md) | Snapshot packaging rules |

---

## Rules

1. Package a `FRnnn/` folder only after that FR is **Complete / Frozen**.
2. Register the FR in `scripts/build_masterclass_package.py`, then regenerate `sources/`.
3. Keep acceptance / ADR as canonical engineering; Masterclass as educational source.
4. Do not begin Masterclass generation from unfrozen work.
5. Do not reopen frozen FR exit criteria to improve packaging.
6. Generate Masterclasses to the [Lean Masterclass Standard](LEAN_MASTERCLASS_STANDARD.md).
7. After Markdown Masterclass completion, render the mandatory PDF study edition.
8. Produce Gamma **Learning** Presentation (~15–20) for deep visual learning.
9. Produce Interview Brief + Interview Deck for rapid revision ([standards](INTERVIEW_BRIEF_STANDARD.md)).
10. Do not replace deep-learning artefacts with interview-only materials.
