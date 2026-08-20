# Document Positioning M2 — Learning Note

This note is source material for the later M6 Gamma presentation. It is not
the Gamma deck.

---

## 1. Why keyword matching was insufficient

The live planner treated skills as strings. Exact phrases and token subsets
caught `Python` / `python programming`. They missed `RAG` versus
`Retrieval-Augmented Generation`, because those tokens do not overlap. They
also could not say “AWS is useful evidence for a Bedrock role without being
Bedrock.” Related groups were bidirectional bags of phrases: if two labels
sat in the same bag, they were “related,” even when that was unsafe (RAG
inside the LLM bag).

Keyword matching answers “do these strings look alike?” Hiring documents need
“is this the same capability, a justified transfer, or a gap?”

---

## 2. Canonical identity vs alias

An **identity** is the capability itself: `rag`, `aws`, `aws_bedrock`, `llm`.

An **alias** is recruiter or candidate phrasing that names that identity:
`RAG`, `Retrieval-Augmented Generation`, `retrieval augmented generation`.

Aliases collapse onto one identity. They do not create new capabilities. If
the catalogue has no identity for a label, the system does not guess a
neighbour.

---

## 3. DIRECT vs RELATED

**DIRECT:** the employer asked for identity X and the candidate has evidence
for identity X. Claiming X is allowed.

**RELATED:** the employer asked for identity X and the candidate has evidence
for a *different* identity Y that the catalogue explicitly links. Promote Y.
Do not claim X.

**UNSUPPORTED:** neither of those. Record the gap.

---

## 4. Why RELATED is dangerous if collapsed into DIRECT

If RELATED is stored as “supported,” downstream generation will write the
employer's word. AWS becomes “Bedrock experience.” Azure becomes “the
candidate is a Fabric engineer.” The whole remediation exists to stop that
collapse. `may_claim_requested=False` is the lock.

---

## 5. AWS vs AWS Bedrock

The employer asked for AWS Bedrock. The candidate has commercial AWS and an
AWS certification. That is transferable cloud evidence. It is not Bedrock.

Correct: promote AWS; keep Bedrock as a gap/transfer context.

Incorrect: “built systems with Bedrock.”

If the profile later contains Bedrock evidence, the same request becomes
DIRECT. The identity did not change; the evidence did.

---

## 6. RAG vs Retrieval-Augmented Generation

These are the same identity. The acronym is not a lucky token. Catalogue
aliases make `RAG` on the JD and `Retrieval-Augmented Generation` on the
profile DIRECT. That is identity matching, not fuzzy language similarity.

---

## 7. Why Java / JavaScript is a useful negative test

The strings share a prefix. Naive substring matching would treat them as the
same skill. They are different identities with no RELATED pair. The test
proves the catalogue does not “soundalike” its way into a claim. It is the
cheap version of the Bedrock mistake.

---

## 8. Why a catalogue should be deliberately small and explicit

A large ontology will invent transfers: every AWS service, every LLM product,
every pipeline synonym. Each RELATED pair is a licence to promote one real
capability next to someone else's requested name. Keep the list short enough
that every pair can be justified from live planner behaviour or eval cases.
Unknown tools stay exact-match DIRECT or UNSUPPORTED. That is a feature.

---

## 9. Why tests should preserve genuine old semantics during migration

The live Azure group already related Microsoft Fabric and ADF. Replacing it
with a tidy `azure` ↔ `adf` pair would have silently dropped Fabric. M2
inventoried groups, migrated justified pairs, added regression tests, then
retired the redundant phrases. Leftover groups remain for CI/CD and similar
unknown labels. Clean-up is not the product.

One pair was **not** preserved: RAG inside the LLM bag. That was a real
semantic error, reported and dropped, with a negative test so it cannot
return as an E1 shortcut.

---

## 10. How PositioningPlan and TailoringPlan share semantic truth without
becoming the same component

Both call `classify_requirement`. If Bedrock is RELATED in one plan, it must
not be SUPPORTED in the other.

They still do different jobs:

- **PositioningPlan** answers what may be argued: evidence refs, forbidden
  claims, trajectory, methodology.
- **TailoringPlan** answers what the current CV emphasises: headline skills,
  projects, summary themes. Prominence bands and role-family anchors still
  apply.

Shared catalogue. Separate consumers. M3 may pack from PositioningPlan.
Package prepare must not import PositioningPlan until that milestone.
