# ADR-005: The Auditor role — a dormant read-only health map, the number under a gate

Date: 2026-06-27
Status: Accepted (the role + the `.claude/agents/auditor.md` subagent are implemented dormant;
numeric activation of the digit 8 remains open — under a stop condition)

> Decision reached by running the adversarial panel (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md).

Applies the norm of [ADR-004](004-second-model-designer.md) / [ADR-003](003-first-km-intake.md): a capability is activated with a number under a retrospective gate, not on speculation.

## In short

The operator requested a role that holistically assesses the state of the entire project and
produces a map of its pain points. No such role existed: reviewer looks at code per-task, and the
architect's status looks half a page ahead. Auditor's unique subject matter is **cross-task
architectural drift**: a violation that holds true in each individual task but accumulates across N
tasks. The role is built **dormant** and **hardware-enforced read-only** (Read/Grep/Glob, no Bash),
available ad-hoc right now. Numeric activation (the digit 8) is deferred under a gate: it will be
granted after the first confirmed, unique catch of drift.

## Context

The operator (solo) requested an "audit panel" — an assessment of the project's state and pain
points — as a separate **numeric role** (not a skill, not an architect mode), run through the
panel. Today this is only partially covered: architect gives a status (a half-page-ahead look),
reviewer covers per-task code. There is no tool for a holistic, backward-looking assessment of the
whole project — and that's exactly what the operator was doing by hand when auditing the package
itself.

## Decision

**We build the role dormant (read-only), and put the number under a gate.** The arbiter's
verdict: the role is real and unique, but immediate numeric activation would violate the package's
own precedent.

**Built now** (dormant, zero runtime debt):

- `roles/auditor.md` — a dormant regimen (like designer's): **not in `roles.json`**, available
  ad-hoc.
- `.claude/agents/auditor.md` — a subagent with **hardware-enforced read-only** access (`Read,
  Grep, Glob`; Bash removed). A precedent for dispatch without a number already exists — that's
  red team / blue team / arbiter.
- **Unique subject matter:** cross-task architectural drift — a violation that's true in each
  individual task but accumulates across N tasks. Structurally it sits outside reviewer (locked to
  per-task) and the architect's status (limited to a forward-looking view). It's a separate actor,
  not a mode — the operator's choice is technically correct.
- **Against noise:** a bounded context (fan-out by module), the "file:line or discarded" rule
  (PR-NN-03), a mandatory second-model (codex) pass on high-stakes findings on top of the opt-in
  `core/second-model.md`.
- **A forced consumer of the result:** the map is written into `docs/PROJECT-STATE.md` (the Risks /
  Open questions / Next day sections), from which the architect draws the slice for day guides.
  Auditor doesn't fix — it documents.
- **Scope of responsibility:** it reports a pattern spanning ≥2 modules / commits / day-tasks **or**
  violating an ADR/invariant; a single local bug goes to reviewer/debugger.

**Under a gate (not now):** activating the digit 8 (edits to `roles.json`, `sync-roles`,
`task-protocol`, the generator, the self-test invariant). The digit 8 is a proposal, not a
reservation: designer ([ADR-004](004-second-model-designer.md), gate O1-D) is also activated with
a free digit; if it activates first, the specific number is resolved in `roles.json` at
activation time (a duplicate is mechanically caught by `sync-roles.py`'s `validate()`).

## What was discarded (fatal, per the panel's decision)

- Immediate digit 8 (contradicts the ADR-003/004 precedent).
- General Bash access in a read-only role (would turn a hardware lock into a prompt-level
  discipline).
- Auditing "the whole project at once" without bounded retrieval (contradicts minimal context;
  noise and hallucinations).

## Consequences

**Pros:** the operator gets a real Auditor immediately (ad-hoc, hardware-enforced read-only); a
unique catch (drift) with a forced consumer; zero runtime debt; the ADR-001/003/004 norms stay
intact; role numbers 0–7 are untouched.

**Risks and open questions:**

- [ ] **Stop condition for activating the auditor's digit.** Activate digit 8 after **the first
      confirmed, unique, actionable drift**: Auditor found real cross-task drift missed by reviewer
      and architect, and it was logged into PROJECT-STATE / a day guide. Not just any finding —
      specifically a unique catch. This gate is lighter than designer's (2–3 starts there): there's
      no technical gap here, and the need has already been observed.
- [ ] **False-positive rate.** On the first real audit, measure the false-positive rate after
      PR-NN-03 + the second model. High → narrow the lenses or strengthen bounded retrieval before
      activation.
- [ ] **The "drift vs. per-task" boundary.** The rule "≥2 modules/commits/day-tasks or an ADR" is
      verified by running it, not by debate; refine it if it blurs in practice.

## Alternatives considered

- **Numeric role 8 immediately (v1).** Rejected: contradicts the gate precedent (ADR-003/004);
  Bash broke read-only; auditing the whole project without bounded retrieval produces noise.
- **A deep-audit mode inside architect.** Rejected by both the operator and the panel: cross-task
  drift conflicts with the forward cap and the hot path of the status; a separate actor is cleaner.
- **A thin `/audit` skill without a role.** Absorbed into the dormant form: the same read-only
  method, but as a role/subagent (the operator chose a role; tool scoping gives hardware-enforced
  read-only).
