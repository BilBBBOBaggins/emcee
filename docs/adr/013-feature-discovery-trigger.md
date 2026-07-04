# ADR-013: Feature discovery — active pre-code trigger + the AskUserQuestion rule (the form-engine remains under gate O1)

Date: 2026-06-29
Status: Accepted (applied)

> Decision made via an adversarial panel run (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md). Related to [ADR-003](003-first-km-intake.md) and [ADR-007](007-kickoff-pipeline.md): does not overrule them and respects gate O1.

## In short

Trigger: a re-analysis of the `brainstorming` skill from the superpowers plugin (a mandatory "door" before any feature: a HARD gate of "no code without an approved design" + user interrogation). The question raised: should such a feature-discovery gate be grafted into the package, at the BA/SA role level, with a Q&A via the native `AskUserQuestion`.

The panel ruled: **the decision-as-a-new-gate is dead** — it re-litigates an object already gated (intake-as-engine, deferred under O1 in ADR-003/007) without new empirics, and three of its four components duplicate what already exists (SA discovery, phase-contract STOPs, kickoff routing). But **two thin amendments survive**, which prior ADRs did not record and which do not require lifting O1: (D1) activating the passive phase contract into one **conditional** pre-code self-stop on the domain-nontrivial-or-irreversible axis; (D2) a rule for using `AskUserQuestion` — legitimate at the **convergence/approve** phase, forbidden as the engine of **divergence**. The upstream form-cosmetics (one question at a time / MC-as-discovery / word limits), per-feature intake machinery, BA-as-holder, and the visual companion — are rejected or remain under O1, as before.

## Context

The question was raised: does the package need a Q&A gate before a feature, modeled on how the superpowers plugin's kickoff/brainstorming interrogates the user. The original proposal (v1) consisted of six theses:

1. there's a gap: no explicit feature-discovery gate;
2. the gate belongs at the BA/SA role level;
3. Q&A via `AskUserQuestion` (pick from options + auto-Other), rejecting the upstream approach of "one open question per message";
4. a HARD gate (no design→code without an approved spec) at BA/SA;
5. port the anti-"too simple to need a design" + "checklist-as-tasks" rules into `quality-gates.md`;
6. do NOT port the visual companion.

**Ground truth of the package, uncovered during the analysis:**

- **Discovery already exists** structurally: `roles/sa.md` (§Discovery process) runs a Socratic Q&A open → happy path → edge → constraints → success → open questions; writes `docs/specs/<feature>.md`.
- **A HARD gate already exists** as "phase contracts (no input artifact → STOP)" ([core/pipeline.md](../../core/pipeline.md)): no artifact from the previous phase → STOP, do not simulate one.
- **This same source material has already been analyzed** in [ADR-003](003-first-km-intake.md) / [ADR-007](007-kickoff-pipeline.md): intake-as-engine and canon artifacts (roadmap/brief/backlog) are deferred under the **empirical gate "O1"** — build them only after a retro on 2–3 real project starts with measured intake loss. The brainstorming form-cosmetics are directly rejected there (structural discovery already exists in `sa.md`; the upstream approach additionally self-commits the spec — against the `task-protocol.md` rule "the agent does not commit"). The design-review subagent is named a candidate mitigation `(O3)` under a separate panel, also under O1.

## Decision

**We build two thin amendments (D1, D2) + record an invariant (D3). Anything that is a form-engine or a canon artifact remains under gate O1 with no change of status.**

**Built now** (pure text edits to existing contracts, 0 new artifacts):

- **D1 — an active conditional pre-code self-stop.** In the developer contract the phase entry `developer | day-guide (+ spec/design)` ([pipeline.md](../../core/pipeline.md), phase-contracts table) is today passive, and `spec/design` are parenthesized = optional; under the solo default (SA collapsed into developer) nothing **requires** discovery to happen before code. Amendment: for a task with a **domain-nontrivial or irreversible** cost, the developer must, before writing code, either have a sufficient existing input (day guide / `docs/specs/` / design / ADR / PROJECT-STATE), or stop and route to the existing discovery phase (route to SA, if deployed; otherwise self-discovery) or to the user. **This is a conditional STOP trigger, NOT a universal pre-code gate** — it does not apply to local, technically obvious, easily reversible tasks. The axis is the same one used by the adversarial panel and spec-driven C+ (cost of error × irreversibility), not "every feature" and not "the project's complexity class."

- **D2 — the `AskUserQuestion` rule: convergence, not divergence.** Discovery = two phases. **Divergence** (surfacing the unknown) requires open dialogue / SA discovery — a pick-list is harmful here, since it requires knowing the options in advance. **Convergence/approve** (choosing among already-surfaced options, confirming a design) is a closed set + Other; here `AskUserQuestion` (pick + auto-Other, multiSelect) is strictly better than free text. **Tie-breaker:** if the set of options has not yet been surfaced, OR the agent cannot justify its completeness → the stage counts as **divergence** (an open question). `Other` is an escape hatch, not a substitute for divergence. This clarifies (does not contradict) the rejection of "MC cosmetics" in [ADR-003](003-first-km-intake.md): that ADR rejects MC-as-discovery, this one legitimizes MC-as-approve.

- **D3 — the invariant "an active trigger ≠ an intake engine under O1".** Record the boundary: a discovery amendment that does **not** create an owned PM artifact (roadmap/brief/backlog/intake engine) is outside O1; one that does create such an artifact falls under O1. D1 and D2 introduce zero new canonical artifacts (D1 amends an existing contract, D2 is a wiring rule for `AskUserQuestion`). The invariant protects future targeted discovery amendments from being falsely drowned in O1 AND protects O1 from dilution.

**What we do NOT build** (dead or under O1 — status unchanged relative to ADR-003/007):

- Feature discovery **as a new canonical gate / per-feature intake machinery** — a re-litigation of O1 without new empirics; forbidden by the package's own gate protocol (lifting O1 requires only a retro on 2–3 starts, not a model debate).
- **`AskUserQuestion` as the engine of DIVERGENCE** (replacing the open dialogue with a pick-list in discovery) — kills discovery (a pick-list requires knowing the unknown in advance).
- **BA as the holder of the pre-code gate** — BA is post-code by contract (`roles/ba.md`: reads already-written code), so it logically cannot be a pre-code gate.
- **anti-"too simple" as non-negotiable + "every feature"** — ceremony working against the deliberate lightweight default ([ADR-001](001-scope-process-overlay.md) / [ADR-003](003-first-km-intake.md)).
- **Upstream form-cosmetics** (one question at a time / word limits / spec self-commit) — already rejected in [ADR-003](003-first-km-intake.md).
- **Visual companion** (a browser HTTP server) — foreign to the CLI model; a visual channel already exists as the dormant `designer` role / wireframe-as-code under its own gate ([ADR-004](004-second-model-designer.md)). Thesis 6 is reframed: not "visual is rejected" but "visual already exists under its own gate."

**Deciding criterion (in one phrase):** of the six v1 theses, two thin refinements to existing contracts survived; everything beyond that either duplicates what is already built, or is exactly the object the package deliberately deferred under the empirical gate O1.

## Consequences

**Upsides:** the trigger gap "in solo mode nothing requires starting discovery before code on a domain-irreversible task" is closed without a new artifact and without owned debt (ADR-001's scope stays intact); `AskUserQuestion` wiring got an enforceable rule instead of ad-hoc use; the trigger↔engine boundary is recorded as a reusable invariant; gate O1 is untouched; the lightweight default is not shifted (D1 is conditional, an escape hatch is built in). An independent panel run converged with the conclusion of an earlier analysis of the same source material — convergence raises confidence in the O1 boundary.

**Risks and open questions:**

- [ ] **Solo self-gate (the residual `(O3)`).** In solo mode, D1's holder is the developer themself. There is no independent pre-code check: D1 raises the **visibility** of skipping discovery, but does not eliminate self-rubber-stamping. Independence only appears when routing to SA / design-review / the user. This is a property of solo mode, not a defect of the amendment — the same limitation recorded as unresolved item `(NP2)` in [ADR-001](001-scope-process-overlay.md).
- [ ] **Subjectivity of the trigger axis.** "Domain-nontrivial / irreversible" is the developer's judgment in solo mode, not an automatic check. The same subjectivity as the adversarial panel's launch axis; an acceptable residual, to be checked in practice.
- [ ] **The D2 divergence↔convergence boundary.** This is a rule, not an automatic check; the agent can misjudge the phase. The tie-breaker (unknown whether the option set is complete → treat as divergence) lowers the risk but does not remove it. Refine if the boundary blurs in practice.
- [ ] **Gate O1 (mirrors [ADR-003](003-first-km-intake.md) / [ADR-007](007-kickoff-pipeline.md)).** Canonical intake (roadmap/brief files, intake engine) and **operationalizing the measurement of intake loss** — build only after a retro on 2–3 real project starts. Without a measurement method, O1 risks becoming a permanent veto — operationalizing the measurement itself also remains an open task. A single anecdote does not lift the gate.
- [ ] **The design-review subagent (under a separate panel).** A candidate mitigation for the solo self-gate / `(O3)` risks (a second pair of eyes pre-code) — not expanded here; remains under O1 and a separate panel/ADR.

**Form of the amendments.** D1 — an edit to `core/pipeline.md` (phase contracts + the developer-contract line: an active conditional pre-code self-stop). D2 — an edit to `core/task-protocol.md` (the wiring rule for `AskUserQuestion`: convergence, not divergence). Invariant D3 — next to the O1 reference. The portability tag `origin: process-convention` (D1) + `origin: harness:claude-code` for `AskUserQuestion` wiring (D2), tagged per [core/portability.md](../../core/portability.md).

## Alternatives considered

- **v1 — feature discovery as a new canonical gate at BA/SA + an `AskUserQuestion`-driven Q&A engine.** Rejected: re-litigates O1 without new empirics; duplicates SA discovery + phase contracts; BA cannot be a pre-code holder; pick-list-as-discovery kills divergence; "every feature" works against the lightweight default.
- **A flat STOP line** — "a feature with no spec/design → do not code, route to SA." Recognized as a survivor, but D1/D2 honestly claim **more** than this minimum (a conditional axis + the AskUserQuestion rule), while staying under O1.
- **A full port of brainstorming (HARD gate + one-question-at-a-time + visual companion).** Rejected: form-cosmetics already rejected in [ADR-003](003-first-km-intake.md); the visual companion is foreign to the CLI; the HARD gate already exists as phase contracts.
- **Record nothing (everything stays under O1).** Considered: the panel = validation of what was already decided. Rejected in favor of recording D1/D2 as genuinely new, cheap, non-O1 refinements.
