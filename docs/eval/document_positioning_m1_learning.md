# Document Positioning M1 — Learning Note

This note is source material for the later M6 Gamma presentation. It is not
the Gamma deck.

---

## 1. What PositioningPlan is

A PositioningPlan is a structured answer to: *what is the strongest truthful
case this candidate can make for this job?*

It lists employer needs, how each one relates to real evidence (DIRECT,
RELATED, or UNSUPPORTED), which CareerProfile refs may be used, which claims
are forbidden, whether the career-trajectory story should lead, and whether
the methodology section would help. It is not a CV. It is not a cover letter.

---

## 2. Why it sits between evidence and prose

If generation reads the job ad and the Master CV directly, it will either
reprint the Master (safe, generic) or invent Bedrock (persuasive, false).

The plan is the missing middle: it decides *what may be argued* before any
model decides *how to say it*. M3/M4 will consume this contract. They do not
exist yet.

---

## 3. Why it is deterministic

Hiring arguments that change when the model is swapped are not a contract.
Classification, evidence selection, spine, forbidden claims, trajectory, and
methodology are pure functions of JobAnalysis + CareerProfile. Identical
inputs produce an identical plan. That is how later tests can pin behaviour
without snapshotting recruiter prose.

---

## 4. DIRECT vs RELATED vs UNSUPPORTED

**DIRECT.** The employer asked for RAG. The profile has Retrieval-Augmented
Generation. Same capability. Claim it.

**RELATED.** The employer asked for AWS Bedrock. The profile has AWS, not
Bedrock. Promote AWS. Do not claim Bedrock.

**UNSUPPORTED.** The employer asked for production chatbots. The profile has
none. Record the gap. Do not promote a fake chatbot skill.

---

## 5. Why RELATED is dangerous if modelled poorly

A sloppy “related” flag is how AWS becomes “Bedrock experience”. Related must
mean: *promote a different, real capability, and forbid the requested name.*
`may_claim_requested` is false on RELATED. Forbidden claims list Bedrock
aliases. The spine says “Do not claim AWS Bedrock.”

---

## 6. How provenance stops JD requirements becoming experience

Employer needs come from JobAnalysis. Candidate refs come only from
CareerProfile (`skill:`, `experience:`, `project:`, `certification:`). A JD
technology is never inserted as a skill. Tests poison `key_alignments` with
“AWS Bedrock” and still get RELATED, not DIRECT.

---

## 7. What argument_spine does

Packed claim sentences, not writing. Future bounded generation may express
them. DIRECT: claim this via that evidence. RELATED: promote this, do not
claim that. GAP: must not be claimed. TRAJECTORY: which career story to lead
with. PORTFOLIO: which Master project bodies to point at, without rewriting
them.

---

## 8. What forbidden_claims does

A semantic denylist for later enforcement. It does not list every English
hallucination. For Bedrock-related-via-AWS it forbids Bedrock as candidate
experience. For chatbot gaps it forbids chatbot / conversational-AI aliases.
M3/M4 will apply this to generated prose.

---

## 9. Why trajectory_mode exists

The same career can be told three honest ways:

- **full_chapters** — QA → data engineering → independent AI *is* the argument
  (adoption / enablement jobs).
- **bridge** — testing is packed only as reliability evidence.
- **ai_lead** — lead with AI evidence; do not walk weak testing rows.

The mode does not rewrite employment history. It chooses emphasis. The rule
uses structured `role_family` plus title identity, not a score.

---

## 10. Why include_methodology belongs at positioning level

Globally dropping methodology made every CV quieter, including jobs that asked
for evaluation, orchestration, or governance. Including it always made
adoption CVs noisy. The plan decides per job from employer needs, not from
the company name.

---

## 11. How the four jobs exercise different strategies

- **E1 Allura** — applied AI control: DIRECT Python/APIs, `ai_lead`,
  methodology on.
- **E2 CSK** — mixed-fit: Bedrock RELATED via AWS, RAG DIRECT, chatbot gap.
- **E3 Maincode** — stretch: GPU/Linux/HPC remain gaps; methodology off;
  portfolio packed without claiming datacentre employment.
- **E4 Repurpose** — adoption: Copilot/Claude unclaimed; `full_chapters` is
  the case.

CSK is one case, not a special branch in the builder.

---

## 12. How this resembles production AI engineering

This is retrieval, policy, and a rendering contract — then a bounded model —
then a truth gate. It is the same pattern as a fail-closed assistant: tools
and records decide what is true; the model only phrases approved claims.
“Ask ChatGPT to write a CV” skips the contract. CIC is building the contract
first.
