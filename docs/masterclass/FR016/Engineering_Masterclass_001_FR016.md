# Engineering Masterclass 001

## Career Intelligence Copilot — FR-016 Multi-Agent Orchestration

### Executive Summary
FR-016 explored when multiple AI specialists are genuinely justified by authority boundaries rather than role names. The accepted design combined a Deterministic Orchestration Supervisor (DOS), the existing Bounded Opportunity Preparation Agent (BOPA), and a read-only Operational Briefing Specialist (OBS). The milestone concluded with **GO AS LEARNING PROOF ONLY**: direct BOPA remains the preferred daily workflow while orchestration provides a validated architectural foundation.

### Engineering Story
FR-015 already solved everyday preparation. FR-016 therefore asked a different question: when does a second specialist create real engineering value? Persona-based splits (Preparation, Truth, Review agents) were rejected as multi-agent theatre because they added complexity without distinct permissions. The accepted solution separated coordination (DOS), bounded preparation (BOPA), and read-only operational synthesis (OBS).

### Architecture Overview
- DOS: observe, delegate, audit, stop; no domain authority.
- BOPA: bounded preparation, verification and truth validation.
- OBS: read-only operational briefing.
- DelegationPolicy controls specialist selection.
- ToolPolicy controls specialist actions.

### Key Engineering Principles
- Authority boundaries justify specialists.
- Supervisors coordinate without inheriting permissions.
- Typed handoffs are safer than conversational delegation.
- Deterministic orchestration is preferable when routing is knowable.
- Technical success does not automatically justify product adoption.

### Trade-offs and Validation
Alternative multi-agent designs were rejected because they lacked meaningful authority separation. Validation demonstrated safe deterministic orchestration and permission isolation. The engineering outcome succeeded, but commercial value remained intentionally limited.

### Interview Preparation
Q: Why introduce multiple agents?
A: To separate authority, not merely responsibilities.

Q: Why is DOS deterministic?
A: Routing was fully expressible from typed state, improving safety and repeatability.

Q: Why is OBS read-only?
A: Independent analysis is stronger when it cannot modify the state being assessed.

Q: Why wasn't orchestration made the default?
A: Direct BOPA remained simpler for everyday preparation.

### Three Things To Remember
1. Specialists are justified by authority boundaries.
2. Supervisors coordinate rather than execute.
3. Simpler architectures remain preferable until additional complexity earns its place.
