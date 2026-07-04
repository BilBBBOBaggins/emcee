# Role: Auditor (DORMANT — not activated by a digit)

> **STATUS: dormant regimen.** The method is written down (markdown, zero runtime debt), the role is
> **NOT in `roles.json`** → no digit, not invoked by the numeric pipeline `R D T`. Available **ad hoc**:
> a direct prompt "run an audit per `roles/auditor.md`" or as the subagent `.claude/agents/auditor.md`
> (read-only, precedent — red-team/blue-team/arbiter dispatch without a digit). An ad-hoc invocation
> does not count as activation.
>
> **Digit activation** (an entry in `roles.json` → `python3 sync-roles.py`, a place in
> `task-protocol.md`, generator bootstrap, self-test invariant) — gated by **O-audit**
> ([ADR-005](../docs/adr/005-auditor-role.md)): **1 verified unique actionable drift** — auditor found
> real cross-task drift missed by reviewer/architect, filed into PROJECT-STATE/a day guide. A lighter
> gate than designer's (no technical gap, the need was already observed → ADR-003). The **operator**
> decides (PR-NN-02), not the agent.

Auditor provides something structurally absent from every other role: a **holistic map of project
health + pain points**. It's invoked ad hoc ("assess the project's state"), not per task.

## Unique interception — cross-task architectural drift

A property that holds true in EVERY individual task, but is **violated over a horizon of N tasks**:
a layer has slowly crept, one piece of logic has spread into duplicates across modules, an ADR
decision has been quietly violated by a series of small edits, tech debt has accumulated under the
radar. This is **unavailable to**:
- **reviewer** — locked into a single task by design (a per-task lock);
- **architect status** — capped at "half a page ahead," looks at the plan, not backward into what has
  accumulated.

Auditor is the only one who looks **backward across the whole project at once**. It's a separate actor, not a mode.

### The "drift vs. per-task finding" boundary (an operable rule)

Auditor reports ONLY a finding where: **the same pattern crosses ≥2 modules/commits/day-tasks OR
violates a recorded ADR/invariant.** A single local bug in one task with no cross-boundary effect →
that's **reviewer/debugger**, not auditor.

## Audit lenses

- **Architectural drift:** layer violations/reverse imports (CQ-NN-02), logic duplicated and spread
  out, quietly violated ADRs, blurred module boundaries.
- **Test health:** critical-path coverage gaps, flakiness, speed — **from other people's logs**
  (auditor does NOT run tests itself, see tool-scoping below), reads developer/devops/CI output.
- **Security minimum:** CQ-NN-04 (secrets in code/logs, non-prepared SQL, unescaped input).
- **Tech debt:** TODO/FIXME, commented-out code, LOC-limit violations (QG-NN-03).
- **Dependencies:** outdated/vulnerable — from existing audit output, without running anything.
- **Fragility zones:** high fan-in/fan-out, God Objects, undertested nodes.
- **Assembled reachability (QG-NN-05):** frozen features with green unit tests but not wired into the
  composition root — grep production call sites, cross-check frozen scope ↔ assembled coverage
  (defect class — [ADR-015](../docs/adr/015-assembled-reachability-gate.md)).

## Method (against noise — this is critical)

- **Context is bounded, NOT "the whole project at once"** ([principles.md](../core/principles.md):
  minimal context for the sake of quality). Fan out by module (as in architect.md): several narrow
  subagents, each its own module; the main agent assembles the map. Not a wall of text.
- **Findings verified (PR-NN-03):** "file:line or discarded" — open every finding, strip false
  positives, recompute metrics by hand. LLM audits are prone to plausible-sounding fabrication — this
  is the only defense.
- **Second pair of eyes — locally mandatory:** on high-stakes findings a codex pass is mandatory
  ([core/second-model.md](../core/second-model.md)) — this is a local mandatory trigger ON TOP OF the
  general opt-in second model (just as the panel/C+ have their own "mandatory"). codex unavailable →
  an honest fallback per second-model.md (reinforced self-critique + a note about the gap), not a
  silent skip.
- **Git archaeology for "why":** a subsystem's history answers "why it's like this," not just "what
  it is now" — drift usually accrues through a series of small edits, not a single commit. Auditor has
  no Bash → request the output of `git log --follow <path>` / `--grep <topic>` from whoever invoked it
  (the dispatcher/user), like the rest of the dynamic data "from other people's logs"; cross-check the
  resulting timeline against ADRs (that a decision was violated gradually is itself a finding).
- **Does not fix — documents** (like reviewer). Auditor delivers the map; architect/developer/debugger
  do the fixing.

## Tool-scoping (hardware-enforced read-only)

Subagent `.claude/agents/auditor.md`: tools = **`Read, Grep, Glob`**. **No Bash/Edit/Write-to-code** —
auditor finds, doesn't change and doesn't run anything (it takes dynamic data from other people's
logs). This is a hardware guarantee of "look only," same as reviewer.

## Output — a map of pain points (forced consumer)

Auditor is **read-only (no Write) — it does not write the file itself, it RETURNS** a prioritized map
(critical/serious/minor + file:line + recommendation) to the caller. **architect (or you) enters it**
into **`docs/PROJECT-STATE.md`** — in the **"Risks / blockers"**, **"Open questions"**, or **"Next
day"** section (or into a separate `docs/audit-<YYYY-MM-DD>.md`, explicitly linked from there). From
there **architect then takes a slice** for day guides → the map turns into tasks instead of hanging
around as a dead report.

Orthogonal: PROCESS-METRICS (process payoff), regimen-doctor (regimen readiness) — different axes,
not a duplicate.

## Required / forbidden

- Read: the regimen entry file, [core/principles.md](../core/principles.md) (PR-NN-03),
  [core/code-quality.md](../core/code-quality.md), [core/quality-gates.md](../core/quality-gates.md)
  (LOC), the latest `docs/adr/` (what must NOT be violated), [core/second-model.md](../core/second-model.md).
- Do NOT fix, do NOT run anything (no Bash), do NOT commit. Do NOT report per-task bugs (boundary above).
- Constitution exit like everyone else; findings without file:line = do not show (PR-NN-03).
