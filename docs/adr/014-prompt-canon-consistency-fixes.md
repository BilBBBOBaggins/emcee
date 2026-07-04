# ADR-014: Prompt-canon consistency fixes (analysis of an external verdict)

Date: 2026-06-30 · Status: Accepted

> Decision made via an adversarial panel run (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md).

## In short

An external reviewer proposed "loosen the prompts — they're too rigid a runtime prompt" (seven items). The adversarial panel plus an actual subagent run ruled: **both extreme frames are wrong.** "Loosen" is a category error: hardware tool-scoping (restricting the tool set at the runtime level) is a load-bearing guarantee of the package — the scope must not be opened. "Everything is by-design" (the first line of defense) also did not survive: the canon in places **violates its own principle** (it demands from Bash-less roles things the scope took away from them) and contains an **unfulfilled item from ADR-001**. The decision is **between the two**: roughly 15–18 targeted documentation edits that bring the canon into agreement with its own load-bearing principle. Zero engineer-months, zero changes to roles' tool sets (the `tools:` scope).

The most valuable part: the empirical subagent run **disproved** a conclusion the reading had converged on — that the architect cannot compute metrics without Bash (it can, via task delegation), and that the reviewer silently fabricates a result (no, it honestly flags the gap). Empirics outweigh a converged reading.

## Context

`emcee` uses `tools:` scoping in `.claude/agents/*.md` as a **hardware** boundary between roles (reviewer read-only, architect docs-only, etc.) — this is a differentiator of the package (`core/portability.md`). North star: quality > tokens; the strictness is deliberate. The external verdict proposed softening that strictness. Checking the verdict matters because the canon is copied into every project — a defect gets replicated.

The panel ran the seven items through red team, blue team, and arbiter (with an independent Bash fact-check), then closed the open stop condition with an actual run of reviewer and architect subagents.

## Decision

Frame: **protect the scope, but the canon must stop demanding from Bash-less roles what the scope took from them.** The package of edits (all are prompt/documentation edits, files and lines verified):

1. **Handoff exit→dispatch.** `roles/developer.md` — the exit report must contain a **list of actually changed files**; `.claude/commands/role.md` and `core/task-protocol.md` — the previous role's exit report is passed through to the next one (in solo mode, to the user or orchestrator).
2. **Reviewer ↔ diff (the strongest hit).** `core/pipeline.md` — the reviewer's input is "an exit report with a list of changed files," NOT "a ready-made diff"; `roles/reviewer.md` — a disclaimer that "the actual git diff is not verified within the role (read-only by hardware)." Fixes a self-violation of the canon's own principle.
3. **arbiter and Bash.** `.claude/agents/arbiter.md` (which has Bash) is right; bring the stale `.claude/README.md` **and the matrix line in `core/portability.md`** in line with "the arbiter has Bash for a narrow codex fact-check."
4. **Fulfill the binding item from ADR-001.** Extract the codex command into a single source (`core/second-model.md`) with a model placeholder; synchronize the `.claude/commands/panel.md` fallback ("codex either way") with `adversarial-panel.md` and ADR-001 ("recommended, not mandatory"); remove the reference to the private `~/.claude/CLAUDE.md`.
5. **Legalize "[data needed: X]".** `core/principles.md` — a missing EXTERNAL fact (no logs/CI/access) → name the fact and the path to obtaining it; this is NOT guessing. The anti-guessing rule is preserved.
6. **QA UAT.** `roles/qa-uat.md` — build into the priority block: an explicit business rule from BA/SA overrides common sense; expectations beyond BA/SA are a recommendation, not silent acceptance.
7. **The frame for a strict rule** — replace "strictness = a feature" with a four-part test (input artifact / owner / exception path / cheap verification). A minor fix: `roles/developer.md` "before every action" → "before every **significant** action."

**The architect's radius (corrected by empirics):** `roles/architect.md` — sanction delegating metric collection to a **read-only measurer** (Bash limited to git/test/wc, NOT write — otherwise docs-only gets diluted); no delegation or metrics → label it "[metrics not obtained]," not eyeballing.

## Consequences

**Positive:** the canon comes into agreement with its own load-bearing principle; the unfulfilled binding item from ADR-001 is resolved; the unfulfillable class (debugging without access) is legalized; the reviewer guarantee is narrowed to one that is honestly fulfillable. Cheap and reversible.

**Cost and residual risks:**

- The gap "developer self-declaration ≠ verified diff" cannot be zeroed out. The empirical run disproved "structural invisibility": via `Glob` the reviewer lists the file tree and **finds** even an undeclared file (in the test it caught a `config.json` with a live secret). The real limit is **change attribution**: without a diff you cannot reliably tell a *changed* file from a pre-existing one; in a small project the tree review catches extras by accident, in a **large repo** an undeclared change slips through in practice, unreferenced. Fix #2 makes the limit visible (the disclaimer). Full closure comes via a dispatcher with Bash that feeds a real `git diff`, without opening the reviewer's scope.
- "docs-only **by hardware**" for the architect (and any holder of delegated tasks) is in practice a **soft** guarantee: a delegated task can spawn a write-capable descendant. The architect-radius fix restricts the delegate to read-only, but the `portability.md` matrix as a whole overstates "hardware-ness" for such roles — a separate revision of the matrix's wording is needed.
- Cheap check: confirm the reviewer's blindness to unrelated files by a run (prompt = `A.ts`, fact = an unrelated `config.json`). Expected to be confirmed; fix #2 closes it.
- Do not build a heavy verified-diff protocol. The `/role` dispatcher runs in the main session (it has Bash) → it computes `git diff --name-only` itself and feeds the reviewer an **authoritative** change set, cross-checking the developer's self-declaration. This closes change attribution in a repo of any size, **without giving the reviewer Bash** (the scope stays intact). The prose floor without a Bash dispatcher: self-declaration + `Glob` + disclaimer. State the public guarantee precisely: "reviewer is read-only by hardware (does not run code); checks the change set it was handed (on Claude Code — a real git diff from the dispatcher; in prose mode — developer self-declaration + a tree review); does NOT claim independent verification of the working tree." Do not sell "reviews the diff" as independent verification.
- The ~15–18 canon edits themselves are **not applied** by this ADR — it records the decision. Applying them is a separate step subject to the owner's confirmation (agentic boundaries: canon edits get replicated into every project).

## Alternatives considered

- **"Loosen the prompts" (the reviewer's verdict)** — rejected: opening the scope would destroy the read-only/docs-only guarantees, a load-bearing differentiator of the package. Red itself acknowledged the "protect the scope" direction was correct.
- **"Everything is by-design, just a doc-sync" (the original version)** — rejected: factually wrong (`pipeline.md` itself demands a diff from a Bash-less reviewer) and relied on a half-existing handoff; the north star was being used as an unfalsifiable shield against valid criticism.
- **Give reviewer/architect a narrow read-only Bash** — rejected: breaks the hardware read-only/docs-only guarantee. Task delegation (architect) and the handoff list (reviewer) solve the problem without opening the scope.
