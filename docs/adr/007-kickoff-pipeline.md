# ADR-007: Onboarding — kickoff mode + end-to-end narrative (doc layer), canonical intake under gate O1

Date: 2026-06-27
Status: Accepted (implemented: /kickoff + core/pipeline.md, end-to-end narrative; canonical intake — under O1 from ADR-003)

> Decision reached via an adversarial panel run (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md). Related to [ADR-003](003-first-km-intake.md): does not supersede it and respects gate O1.

## In short

Operator complaint: "I deployed the regimen — I don't know what's next; I haven't worked the pipeline
for a month, I'm drifting on my own." The pain is real, but it's ~90% documentation-shaped — it's
fixable without building engines. So we build a **doc/onboarding layer**: an end-to-end narrative in
`core/pipeline.md` ("how to work" from kickoff to ongoing) + an **architect kickoff mode** that takes
the project from "empty" to "day 1 plan" and fills in `CLAUDE.md` itself. Canonical intake (roadmap/brief
files + an intake engine), however, **is not built** — the "haven't worked for a month" complaint means
zero starts, i.e. gate O1 from ADR-003 has not been passed.

## Context

Operator (solo, ground truth): "I deployed the regimen — I don't know what's next; haven't worked the
pipeline for a month, I'm drifting on my own." Concrete gaps:

- no coherent "how to work" narrative;
- the roadmap and guides appear "out of nowhere" in the docs;
- there's no clean way to invoke the architect at the start (it has no entry in `roles.json`; the
  command `0` is ambiguous; at the start there are no days yet);
- placeholders get filled in by hand ("I don't know where anything lives").

This is the very intake that ADR-003 deferred under gate **O1** ("build only if a retro on 2–3
STARTS shows loss at the entry point"). The panel ruled: **signal O1 has not passed** — "haven't worked
for a month" means non-use, zero starts, unmeasured loss at entry (ADR-003 explicitly flags "no
uptake" as a signal to revisit scope, not to build intake). But **the pain is real and ~90%
documentation-shaped** — fixable without lifting O1.

## Decision

**We build a doc/onboarding layer (prose and patches, zero owned engine). Canonical intake stays under
gate O1.**

**Built now:**

1. **`core/pipeline.md`** — end-to-end narrative: PHASE 0 KICKOFF → ongoing (`R D T`); the chain of
   "where the slice / guides / specs come from"; a best-case example with all roles (marked
   "[complex]"); while **solo-collapse is the default.**
2. **Kickoff mode in `roles/architect.md`** (prose): the `/kickoff` command takes the project from
   "empty" to "day 1 plan". **Lightweight by default**; asks **only routing questions** (stop rule:
   domain discovery belongs to the system analyst, don't duplicate it); **fills in `CLAUDE.md` itself
   under the provenance rule** (`[from user]` / `[from code]` / `[inferred]`; no source → a visible
   `{{placeholder}}`, never guess); records what was said in the `PROJECT-STATE` section (user
   priorities, no invented roadmap scheme); a load-bearing decision → `/panel` → ADR; produces the
   first day guides.
3. **A thin `/kickoff` command** (`.claude/commands/kickoff.md`) — a pointer to kickoff mode (same
   class as `/role` and `/panel`; owned debt ≈ same as `panel.md`). Does not duplicate the process and
   does not replace day-0-guide.
4. **Command grammar** (`core/task-protocol.md`): `/kickoff` for the start; the ambiguity of `0` is
   removed (one number = architect-lead; three numbers = role).
5. **QA solo-collapse** — the narrative's default + scoping in `quality-gates.md`, `developer.md`,
   `qa-e2e.md`, `qa-uat.md`: the split between QA loops applies **only** when a separate QA E2E is
   deployed (a complex project). On a simple project the developer covers acceptance / E2E-like
   testing (but this is not an independent signoff).

**Not built** (under gate O1 or dropped):

- Canonical `roadmap.md` / `product-brief.md` as **files** + an entry in task-protocol + bootstrap via
  the generator (this is owned PM debt, contradicting ADR-001; lifting O1 has not passed). Instead — a
  snapshot of priorities in `PROJECT-STATE`.
- Intake interview as an engine or workflow.
- Auto-fill without a provenance marker — this would seed an untraceable defect into the product (O3).
- Duplicating SA discovery in the architect (stop rule).

## Consequences

**Upsides:** the question "I deployed it, now what?" is closed by the narrative + kickoff mode;
the operator's choices (`/kickoff`, agent-fill) survived (with provenance); zero owned engine and no
canonical PM (ADR-001/003 scope stays intact); the grammar ambiguity is removed; QA solo-collapse
resolved the contradiction between the narrative and the roles.

**Risks and open questions:**

- [ ] Gate O1 (a mirror of ADR-003) — empirical: canonical intake (roadmap/brief files, an intake
      engine) is to be built only after a retrospective on **2–3 real starts** with measured loss at
      entry. A single operator anecdote of "drifting" does not lift the gate (otherwise the package's
      gates are decorative).
- [ ] Provenance discipline (O3): auto-fill with a source marker makes a defect visible, but a
      solo review can still rubber-stamp it. Acknowledged residual: the risk is reduced (made
      visible), not eliminated.
- [ ] The "routing / domain discovery" boundary. The rule "the architect routes, the system analyst
      interviews the domain" is validated by running it; refine if it blurs in practice.

## Alternatives considered

- **Full v1: `/kickoff` + canonical roadmap.md/PROJECT-BRIEF.md + an intake engine, lifting O1.**
  Rejected: lifting O1 on an anecdote contradicts the gate itself (would make gates 003–006
  decorative); PM canon contradicts ADR-001.
- **Give the architect a number in `roles.json`.** Rejected: breaks the convention "one number =
  architect-lead" + requires revising the whole grammar; `/kickoff` is cleaner.
- **Merge qa-uat and qa-e2e.** Rejected: they're complementary (case design vs. coding + running +
  diagnosing); instead of merging — solo-collapse by default (on a simple project the developer covers
  both).
