# ADR-009: Regimen portability — a boundary, not layers

Date: 2026-06-28
Status: Accepted (the boundary is implemented in `core/portability.md`; serves as the basis for Accepted ADRs 010/011/012)

> Decision reached via an adversarial panel run (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md).

## In short

An external reviewer noticed that the regimen **mixes three heterogeneous layers**: (1) a
model-agnostic core (the SDD cycle, decomposition, separating exploration from production), (2) an
opinionated process ("we like it this way": roles, days, the numeric pipeline), (3) model-specific
patches (anti-tics for a particular model). The obvious fix seemed to be: **physically split the
regimen into three layers**, so the model-specific layer swaps per model, the process layer is
toggleable, and the core stays portable.

The adversarial panel **killed this solution as fatally mis-framed**:

- **The axes aren't orthogonal.** `task-protocol.md` is itself opinionated process;
  `quality-gates.md` ties the verification boundary to the numeric command `R D T`. The cut runs
  **through files**, not between them — a physical layer split would cut through something
  cohesive.
- **The "model-specific" layer is almost empty.** Almost every "Claude" spot is a tie to the
  **Claude Code runtime** (auto-reading `CLAUDE.md`, the `.claude/` directory, hooks, slash commands,
  plan mode, `/rewind`), not a patch for the Opus model. There's nothing to swap in a "model
  profile."
- **Composition manifests/profiles = owned debt.** This is exactly the class already rejected in
  [ADR-001](001-scope-process-overlay.md) (a process overlay without an owned scaffold) and
  [ADR-006](006-regimen-upgrade.md) (manifest + three-way merge rejected). Today composition is
  profile-free and carries no debt.

What survives and is adopted instead of the split is **a portability boundary in prose plus an
in-place provenance marker on rules**, with no composition machinery whatsoever. This honestly
answers the reviewer, breaks nothing, and creates no owned debt.

## Context

`emcee` is decomposed **by topic/concern** (`core/` `roles/` `stack/` `architecture/`
`domain/` `.claude/`), not along a "model binding" axis. A developer-reviewer flagged this mixing as
the main structural defect and recommended "cutting it into layers."

The temptation is to lay a **second, physical** three-layer split on top of the topical division.
The cost of getting it wrong is real: this is a refactor of a working regimen; a bad cut breaks
navigation and auto-reading and burns attention for nothing. So the decision was run through an
adversarial panel.

Before synthesis, one **discovery fact was gathered from the operator (ground truth)**: "is there
a real plan to port the regimen to a non-Claude runtime?" — **yes, there is a plan**. This is the
green gate under which the provenance marker pays for itself (it cheapens a future **manual**
port).

## Decision

**Do not split the regimen physically. Draw the portability boundary in prose and mark rules'
provenance in place — without composition machinery.** Four items (three unconditional + two under
the green migration gate):

1. **"Claude Code first" is stated explicitly** (README, CLAUDE.md). The package is designed for
   the Claude Code runtime; porting to another runtime is **manual work**, not a config swap. This
   drops the straw promise of "swap the model/runtime via a profile," which the package cannot
   deliver. *Unconditional.*

2. **The reviewer's targeted fixes** (north-star work, taking priority over the marker; not the
   panel's subject matter, but included in this decision as mandatory):
   - **(a)** The real "one file = one run" conflict does **not** sit in `quality-gates.md` (which
     already says "a logical unit, not a single file"), but in `roles/developer.md:31-33`
     ("verification after every changed file"), which further down contradicts itself (line 77). The
     fix targets `roles/developer.md`: "verification after a completed logical unit/task," with an
     exception for a risky, targeted edit.
   - **(b)** Linter determinism — invoking it must not be the agent's reasoning about the stack.
     *Checked against fact: this is **already implemented*** in `quality-gates.md:52-58` (QG-NN-02):
     "static checking is verified with a single fixed project command… the agent runs the command, it
     doesn't choose it." No substantive fix is needed. Residual gap (outside this panel's scope): the
     `{{check-command}}` placeholder lives in `quality-gates.md` but isn't wired into `CLAUDE.md`'s
     command section (which has `build/test/fast-test`) and isn't checked by `regimen-doctor.py` —
     wiring it up is deferred as a separate decision.
   - **(c)** LOC (lines of code) is already a signal, not a block (`check-loc.sh` is correct), but the
     short-form wording is out of sync: `code-quality.md`, `code-quality/SKILL.md`, and the
     `check-loc.sh` comment in places say "the decision is always to split." Synchronize all of them
     to: "LOC signal → justify cohesion OR split; a confirmed God Object → split."
   *Unconditional.*

3. **A provenance marker for a rule's origin** — the existing label notation gains an `origin:`
   coordinate with values `universal` / `process-convention` / `harness:claude-code`. **Strictly: in
   the rule's body, not in frontmatter, does not drive composition, is not parsed by tooling.** *Under
   the green migration gate — we do it.*

4. **A "Portability boundary" section** — a single thin index (README or `core/portability.md`,
   < 200 lines) of what's tied to the Claude Code runtime and will need manual re-cutting on a port:
   auto-reading `CLAUDE.md`, the `.claude/` directory, plan mode, `/rewind`, numeric commands as a UX
   convention. This is **a map for a future manual fork**, not an automation mechanism. *Under the
   green migration gate — we do it.*

**Stop condition for the `origin:` marker (a load-bearing constraint of this decision).** The
marker stays outside owned debt only as long as ALL three hold: (1) it lives in the rule's body, not
in frontmatter; (2) it does not drive composition; (3) it is not parsed/validated for decisions by any
tooling (`new-project.py`, `selftest.py`, `regimen-doctor.py`, `sync-roles.py`). Passive rendering in
the handbook and visibility in `upgrader`'s diff are allowed (this is prose being surfaced, not
machine reading). **Breaking any of these points turns the marker into a synchronized artifact → a
relapse of ADR-001/006 → the marker gets rolled back.** The absence of a hidden path by which the
marker could become machine-readable was checked with a separate review pass.

## Consequences

**Upsides:** an honest answer to the reviewer with no owned debt; zero code and zero new
composition machinery; nothing breaks (the topical split, auto-reading, numeric commands, ADR-001 —
untouched); the targeted fixes (developer.md, linters, LOC sync) are direct north-star work; the
marker and the boundary genuinely cheapen a future manual port to another runtime (under the
operator's named plan).

**Settled (closed on the current data, not a TODO):**

- **The migration target runtime is the Codex CLI** (the likely target, named by the operator:
  GPT-x is outgrowing the previous leader, the frontier market is alive). The ADR decision (marker +
  map) **does not depend** on the exact target and is adopted in full — the target only strengthens
  the payoff.
- **A "toggleable process" (toggling roles/days/pipeline) — we are NOT building it and not
  planning to.** The operator (the only possible bearer of this pain, ground truth) confirmed: the
  idea is dead, process is the package's core of value. This is **a "no" decision**, not a deferred
  question; no tripwire is needed. Process stays `origin: process-convention` (marked for a future
  port), but there is no toggle mechanism.

**Risks (consequences of the decision, not deferred decisions):**

- **The `origin:` marker's stop condition is discipline, not a gate.** If someone later teaches
  tooling to parse `origin:` for decisions, the marker will silently become owned debt. The backstop
  is the explicit stop condition above; we deliberately don't add a hard check (it would itself be
  the very tooling that reads the marker).

**Empirical verification (the one honest TODO — knowable only from the field, not from debate):**

- [ ] Verify on an actual move that the map paid off. When it comes to an actual migration to
      Codex — run it as **a separate fork** (the experimental branch
      `regimen/portability-boundary` already exists) and confirm that the `origin:` marker and the
      Portability boundary section actually cheapened finding harness dependencies. This is a
      field test of items 3–4 of the decision, not an unresolved question: the decision has been made,
      this is its subsequent confirmation.

## Alternatives considered

- **A physical three-layer split (layer directories `layer-core/` etc.).** Rejected: the axes
  aren't orthogonal, the cut runs through cohesive files; directories break `CLAUDE.md` auto-reading.
- **Composition manifests/profiles (`profile: claude+team`, `profile: portable-core`) in the
  generator.** Rejected: a synchronized, engine-readable artifact = owned debt, already killed by
  ADR-001 and ADR-006. The current profile-free composition carries no debt.
- **Swap the "model-specific layer" for the target model.** Rejected: genuinely model-specific
  rules ≈ 0; almost everything "Claude"-specific is **runtime** specificity of Claude Code, not
  rule values tied to a model. There's nothing to swap.
- **Toggling opinionated process as a feature.** Firmly rejected (not "not yet"): the operator —
  the only possible bearer — confirmed the idea is dead, process is the core of value. We mark it
  (`origin: process-convention`), we don't make it toggleable.
- **Bare cosmetics (only "Claude Code first" + targeted fixes, no marker and no section).** This
  is the fallback if the operator judges the marker superfluous. Not chosen because **the migration
  gate is green** — under the named porting plan the marker and boundary pay off, and their cost is
  ≈ zero above the existing label.
