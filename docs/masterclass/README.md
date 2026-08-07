# Engineering Learning Academy — Masterclass Source

**Purpose:** Stable educational source packages derived from **frozen** engineering
work in this repository.

**Not this folder’s job:** Generate presentations, PowerPoints, interview decks, or
diagrams. Those artefacts are produced later by the Engineering Learning Academy
from a committed **Masterclass Source Package**.

---

## Workflow

```text
Engineering
    ↓
Validation
    ↓
OAT (when applicable)
    ↓
Close-out
    ↓
Freeze
    ↓
Masterclass Source Package   ← docs/masterclass/FRnnn/
    ↓
Commit
    ↓
Engineering Learning Academy
```

Frozen acceptance reports and ADRs remain the **canonical engineering record**.
Each `FRnnn/` package is an attachable folder for Academy generation.

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

### How authoritative content is preserved

- Engineering is edited only under `docs/eval/`, `docs/adr/`, and related SoT paths.
- `sources/` files are **generated snapshots** (full file or mechanical section extract).
- Regenerate with:

```powershell
python scripts/build_masterclass_package.py FR016
```

- Do **not** hand-edit `sources/`. Do **not** rewrite engineering into the package.

### Single-folder attachment

Attach `docs/masterclass/FRnnn/` to ChatGPT (or other Academy tooling). Follow
`MANIFEST.md` for required documents and generation order.

---

## Layout

| Path | Role |
|------|------|
| [FR001/](FR001/) … [FR015/](FR015/) | Placeholders — package only when owner requests |
| [FR016/](FR016/) | **Packaged** — Multi-Agent Orchestration |
| [PROJECT/](PROJECT/) | Future overall CIC Masterclass |
| [SUBSYSTEMS/](SUBSYSTEMS/) | Future subsystem Masterclasses |
| [PACKAGING.md](PACKAGING.md) | How snapshots preserve SoT / future FR adoption |

---

## Rules

1. Package a `FRnnn/` folder only after that FR is **Complete / Frozen**.
2. Register the FR in `scripts/build_masterclass_package.py`, then regenerate `sources/`.
3. Keep `README.md` as a teaching bridge; keep acceptance as canonical engineering.
4. Do not begin Masterclass generation from unfrozen work.
5. Do not reopen frozen FR exit criteria to improve packaging.
