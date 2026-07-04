# ADR-002: Spec-driven — we build C+ now, defer the executable layer

Date: 2026-06-27
Status: Accepted (implemented: core/spec-driven.md — the C+ outline in the package)

> Decision reached by running the adversarial panel (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md). Related to [ADR-001](001-scope-process-overlay.md): that ADR established the norm "process overlay, don't build executable code for unmeasured pain" — this ADR applies the same norm to spec-driven.

## In short

The question was whether to automate spec-driven development so that the pipeline "spec → tasks
→ tests → code → integration" runs itself. The answer is no, and here's the key argument:
automation has **no new oracle.** The whole auto-cycle checks against the same single spec, so it
won't catch anything a human wouldn't catch — but it will stop looking. Quality isn't added by
orchestration, but by a **new verification angle** — and that's what we build. This is "C+":
test-first, an independent test author, and an adversarial review pass of the tests themselves. All
in markdown, with no executable code and no maintenance debt.

## Context

Question: should spec-driven automation be added, where the pipeline "spec contract → tasks →
[RED → GREEN → review] → integration" runs itself?

Decision context: solo development; the north star is quality, not token economy; a hard
precondition of "a human gate on high-stakes decisions." A manual pipeline already exists
(role subagents, quality gates, constitution, adversarial panel) — it's triggered manually via
`R D T` commands.

Options considered:

- **A** — full automation: a Workflow orchestrator + auto-debug + a consistency gate.
- **B** — MVP Workflow: loop-until-green per task + 2 checkpoints.
- **C** — formalizing the manual pipeline without executing it.
- **C+** — this is C plus a new oracle step.
- **D** — build nothing.

## Decision

**We build C+ now** (markdown only, zero runtime debt). **We do not build the executable layer**
(A / B / a Workflow / a skill in the repository) **now.** Variant A is rejected. We don't
proactively choose variant D, but it remains a fallback outcome.

**Decisive factor:** automation has no new oracle. The whole cycle checks against one spec — the
auto-cycle doesn't catch what a human wouldn't, but it stops looking. And the executable layer also
violates the ADR-001 norm (don't build for unmeasured pain). Quality isn't added by orchestration,
but by a new verification angle — and that's what we build, debt-free.

**What C+ includes** (we build this, ~2–3 engineer-days, regimen only):

1. **Spec as a contract** — tighten `docs/specs/*` down to a verifiable contract. Automatic test
   derivation — **only for hard contracts** (parsers / computations / validators, i.e. "Variant 3
   TDD" from `CLAUDE.md`), but not for live product domains where the spec drifts.
2. **Test-first (RED → GREEN)** for these contract cases.
3. **A new mandatory oracle step** (this is the real increment): an adversarial review pass of the
   tests themselves (a red lens on the tests — "what do they NOT catch"); an independent test
   author who doesn't overlap with the implementer; a contract check via a second model (codex) on
   high-stakes cases.
4. **The human commit per task is preserved** (as in `roles/reviewer.md`) — not weakened to a
   commit per feature.

**What we don't build:** a Workflow or a skill in the repository. Reject any such PR until both
"pain" thresholds are crossed (see "Risks and open questions") **and** a separate ADR on "layer 2"
exists; even then it's preferable to keep it user-local outside the repository (not take on version
debt per ADR-001). We also don't build: automatic derivation on live domains; a checkpoint per
feature; a half-measure variant B — mitigations for its inherent defects (a bad test in the loop;
formal rubber-stamp checkpoints) inflate it to A's complexity, so it's either a deliberate A later
given data + an ADR, or not at all.

## Consequences

**Pros:** a cheap new verification angle is added (adversarial test review) with no runtime
debt; the human gate is not weakened; the manual `R D T` and the adversarial panel are untouched;
the ADR-001 scope stays intact.

**Risks and open questions:**

- [ ] **The "pain" threshold (decided by the user).** Name the threshold that would justify an
      executable layer ahead of time (e.g. "manual orchestration cost more than X on N features") —
      **before** the experiment, otherwise the condition is unfalsifiable.
- [ ] **Verifying the threshold — mirrors ADR-001.** Run 2–3 real features in C+ mode. If the pain
      hasn't reached the threshold across 3 starts — never build the executable layer.
- [ ] **Whether C+ itself is justified.** If across 2–3 features the adversarial test review pass
      hasn't caught a single class of defect beyond what qa-uat + reviewer catch, roll back to D
      (even the markdown layer didn't pay for itself).
- [ ] **C+ vs D — a values question, decided by the user.** The arbiter ruled for C+, but the final
      decision rests on measured benefit (previous item), not on debate.
- [ ] **Data needed:** mid-run user input in a Workflow — check against Claude Code documentation
      before any "layer 2."

## Alternatives considered

- **A — full automation.** Rejected: no new oracle (same quality, minus the human) + maintenance
  debt for executable code against Claude Code drift (violates ADR-001).
- **B — MVP Workflow.** Rejected precisely as an "MVP": mitigations for its inherent defects (a bad
  test in the loop; formal rubber-stamp checkpoints) inflate B to A's complexity, so there is no
  "half-measure" B.
- **D — don't build.** Not proactively chosen: D leaves a cheap quality gain (the oracle step) on
  the table. It remains a fallback outcome if C+ doesn't pay off across 2–3 features (see "Risks
  and open questions").
