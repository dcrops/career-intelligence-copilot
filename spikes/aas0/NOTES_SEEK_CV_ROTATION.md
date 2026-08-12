# AAS spike notes — SEEK CV storage / rotation (dogfood evidence)

Access basis: AAS-0 live Choose Documents screenshots
(`spikes/aas0/runs/20260812T042513Z`, `20260812T065805Z`) + owner clarification.
No additional live SEEK inspection in this change set.

## Observed behaviour

- SEEK Apply → **Choose documents** presents a radio list of previously uploaded
  résumés plus Upload.
- Storage is finite (owner: limited number of stored CVs).
- AAS-0 uploaded `opp_<ULID>.pdf` (internal stem) which appeared in the list and
  became selectable/default.
- Older human-named CVs also appeared (e.g. role-specific “David Cropper … CV.pdf”).
- Cover letters use a separate method-radio flow (Upload / Write / Don’t include).

## Rotation policy (spike recommendation)

Desired flow when no free slot:

1. Prefer free slot → upload.
2. Else delete only **replaceable_tailored** CVs, then upload.
3. Never delete **protect** or **ambiguous**.

Classification helper: `spikes/aas0/session_handoff.py::classify_seek_cv_for_rotation`

| Class | Examples | Auto-delete? |
|-------|----------|--------------|
| replaceable_tailored | `opp_01….pdf`; future `David_Cropper_*_CV.pdf` | Yes (when implemented) |
| protect | `David Cropper CV.pdf`, master/general names | No |
| ambiguous | Other named “David Cropper … Engineer CV.pdf” without CIC marker | No |

## Reliability assessment

- **Reliable:** opportunity-id stems (`opp_*`) and proposed external export pattern.
- **Not reliable enough yet:** generic “looks like a tailored CV” from free-text
  filenames alone — those stay **ambiguous**.
- **Do not implement destructive SEEK deletion** until external filenames ship so
  replaceable docs are machine-identifiable without guessing.

## AAS-1 implication

Implement rotation only after (or with) external export filenames, and only delete
`may_auto_delete_seek_cv(...) == True` entries. Owner confirmation not required for
confident replaceable deletes per owner policy; still fail closed on ambiguity.
