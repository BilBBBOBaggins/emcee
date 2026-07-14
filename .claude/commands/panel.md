---
description: Launch the adversarial panel to review an architectural/strategic decision (red → blue → arbiter + codex)
argument-hint: "[decision/question or path to a spec] — what we're reviewing"
---

Run the adversarial panel per `core/adversarial-panel.md`. Decision under review: `$ARGUMENTS` (if empty — ask the user what we're reviewing, and/or take the architecture currently under discussion).

Steps (in full — in `core/adversarial-panel.md`):

0. **v1.** Write out the decision under review in `scratchpad/panel/architecture-v1.md`: load-bearing theses (each a separate, checkable claim), context, constraints. Extract a numbered list of load-bearing assumptions. Show it to the user before launching the attack — they can kill a bad premise right away.
1. **Red-team r1** → the `red-team` subagent on `scratchpad/panel/architecture-v1.md` + the assumptions. It **must** bring in codex as a second model (when available — ADR-016; if physically unavailable, an honest fallback). Result: `scratchpad/panel/red-r1.md`. Show the verdict + kill list.
2. **Blue-team r1** → the `blue-team` subagent on `scratchpad/panel/architecture-v1.md` + `scratchpad/panel/red-r1.md`. Result: `scratchpad/panel/blue-r1.md`. Show the defensibility summary.
3. **Arbiter r1** → the `arbiter` subagent on all three. Result: `scratchpad/panel/arbiter-r1.md`. Show the verdict + actions.
4. **Second round** — only if the arbiter calls for it: targeted red↔blue on the open items, then arbiter r2.
5. **v2 synthesis** → `panel/architecture-v2.md` from the arbiter's verdict.
6. **Final codex pass** → review v2 for internal contradictions (`codex exec … -m <codex-model-id> -c model_reasoning_effort=<max-effort>`). Fix what's found.
7. **ADR** → record the decision in `docs/adr/` (format — `roles/architect.md` → "ADR process"); carry open questions and survival preconditions into Consequences as TODOs with an owner.

If subagents (`.claude/agents/`) are not set up in the project — run the roles sequentially in the current session per their prompts in `.claude/agents/{red-team,blue-team,arbiter}.md` (prose mode). codex is **mandatory when available** (ADR-016, symmetric on red/blue); if physically unavailable — don't skip the panel, switch to the honest fallback (`core/adversarial-panel.md` → "Second model"). `<codex-model-id>` is a placeholder, see `core/second-model.md`.

Consensus = a fixed point (a round with no new decision-changing objection, or what remains = named empirical unknowns → TODO for discovery). Cap of 4-5 rounds; if still diverging — present the user with the CRUX.
