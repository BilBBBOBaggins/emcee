# Portability boundary — what's tied to the runtime and what ports over

This package is designed for the **Claude Code runtime** (Anthropic's CLI/extension). Porting the
regimen to another runtime (Codex CLI, Cursor, a custom harness) is **manual work guided by this
map**, not a config switch. Why not a swap mechanism — see [ADR-009](../docs/adr/009-portability-boundary.md):
the axes "universal / process / runtime-bound" are not orthogonal, and composition profiles are
owned debt, already rejected by [ADR-001](../docs/adr/001-scope-process-overlay.md)/[ADR-006](../docs/adr/006-regimen-upgrade.md).

This map is insurance against a fast-moving frontier-model market: leadership shifts, and a move
(e.g. Claude → Codex) is likely. The map makes a one-off fork **fast**, without requiring machinery
between moves.

## Model vs. runtime — two different migrations

"Moving from Claude to Codex" is **simultaneously** a model change and a runtime change, at
different costs:

- **Runtime change** (Claude Code → Codex CLI): the *plumbing* changes — auto-reading `CLAUDE.md`,
  the `.claude/` directory, hooks, slash commands, plan mode, `/rewind`. A different runtime has its
  own mechanisms (`AGENTS.md`, its own config). This is rewritten by hand. **The bulk of the move's
  cost is here, and no config automates it.**
- **Model change** (Opus → GPT-x): only the *patches for model tics* change (see `origin:
  harness:claude-code`, the model-tic subclass below). There are few of them.

## Provenance notation `origin:`

An extension of the rule tag (`[ID · class · gate]`, see [constitution.md](constitution.md)). The
label lives **in the rule's body as prose**; the coordinate is optional. Three values:

| `origin:` | What it means | When porting |
|---|---|---|
| `universal` | A technique independent of model and runtime (contract-first cycle, decomposition, reconnaissance vs. production, adversarial method, debugging method) | **Keep the idea**, rephrase it in the new runtime's idiom |
| `process-convention` | A process "preference" (roles, days, `R D T` commands, pipeline artifacts) | Keep the convention, **rewire the mechanism** (subagents/slashes → runtime equivalents) |
| `harness:claude-code` | Bound to the Claude Code runtime | **Rewrite by hand** for the new runtime (or drop it if there's no equivalent mechanism) |

The subclass `harness:claude-code/model-tic` is a patch for a specific model's tic (e.g. "no
pre-existing failure as an excuse" — a Claude tic). On a model change — **revisit** it for the new
model: it has different tics.

**The label's stop condition (load-bearing, [ADR-009](../docs/adr/009-portability-boundary.md)).**
`origin:` stays outside owned debt only as long as: (1) it's in the rule's body, not in frontmatter;
(2) it doesn't drive composition; (3) it isn't parsed/validated for decisions by tooling
(`new-project.py`, `selftest.py`, `regimen-doctor.py`, `sync-roles.py`). Passive rendering in the
handbook and visibility in a diff are allowed. Violate any of these → the label has become a
synchronized artifact → revert.

Tagging with `origin:` is **lazy and incremental**: it's applied as a rule is touched, not in a
blanket sweep (a blanket sweep for completeness's sake is exactly the effort↔value inversion the
panel rejected). Most `core/` rules are `universal`; the tag is needed where the provenance isn't
obvious.

## Harness-dependency map (what to rewrite on a fork)

An index of what's tied to the Claude Code runtime. This is the TODO list for a future manual port:

| Dependency | Where | What to change it to in another runtime |
|---|---|---|
| Auto-reading `CLAUDE.md` at session start | root `CLAUDE.md` | the runtime's auto-context mechanism (e.g. `AGENTS.md` for Codex) |
| The `.claude/` directory (agents/skills/commands/hooks) | `.claude/` | the runtime's subagent/command/hook equivalents, or prose mode |
| Subagents with tool-scoping | `.claude/agents/*` | if there are no subagents — roles as prose modes (role = prompt) |
| Slash commands (`/role`, `/panel`, `/kickoff`) | `.claude/commands/*` | the runtime's commands/macros, or a manual run from the md |
| Hook gates (`check-loc`, `check-no-todo`, precompact, `numeric-command` dispatch) | `.claude/hooks/*` + `settings.json` | the runtime's hook mechanism, or move it out to CI/pre-commit (numeric dispatch: the anti-hedge prose rule in the entry file / task-protocol.md) |
| Plan mode, `/rewind`, auto-compacting context | Claude Code behavior | runtime analogs or manual discipline |
| Numeric commands `R D T` as UX | `CLAUDE.md` + `roles.json` | the runtime's UX convention (same idea, different input) |
| Auto-memory | `core/memory.md` | the runtime's memory mechanism + the `CLAUDE.md` hierarchy |

**What's NOT in this table ports over as an idea:** the `core/` methods (spec-driven, debugging,
adversarial-panel, principles, code-quality) are `universal` — their substance doesn't depend on the
runtime.

**AGENTS.md is a substrate for content, not for guarantees.** Auto-reading on Codex/Cursor goes
through `AGENTS.md` — a mature format (de facto AAIF/Linux Foundation standard), but it carries
**content/conventions**, NOT hardware-enforced guarantees. Read-only/docs-only roles and hooks are
provided by a **per-runtime permission profile** (`.codex/` and analogs), not by generic markdown.
So AGENTS.md carries neutral role content; enforcement lives in the runtime overlay (`origin:
harness:<name>`), and its strength is captured by the guarantee matrix below.

## Per-runtime guarantee matrix (role/rule × runtime × strength)

What each runtime actually provides: **hardware-enforced** (the OS/harness physically prevents the
violation), **prose** (an honor instruction in `developer_instructions`/AGENTS.md — a degradation, a
commitment held on record), or **absent**. The source for Codex is an empirical test of the live
binary `codex 0.138.0` ([docs/evidence/g2-findings.md](../docs/evidence/g2-findings.md)); the
implementation is [`overlays/codex/`](../overlays/codex/).

| Guarantee (role rule) | Roles | Claude Code | Codex (0.138.0) |
|---|---|---|---|
| **read-only** (no writes/execution) | reviewer, auditor | hardware-enforced — `tools: Read,Grep,Glob` | **hardware-enforced** — `sandbox_mode="read-only"`, seatbelt blocks writes (G2-verified) |
| **full write** (code/tests/build) | developer, qa-e2e, debugger, devops | hardware-enforced — +Edit,Write,Bash | **hardware-enforced** — `sandbox_mode="workspace-write"` |
| **docs-only** (Write, but not code) | ba, qa-uat, sa, architect | hardware-enforced — `tools` without Edit/Bash | **prose** — `workspace-write`+accountability. G2 RED (live agent): a stable path is structurally impossible (cwd is always writable — the agent wrote to `src/`), `workspace_roots`=toggles, per-path only via the unstable `[permissions]` enum |
| **scratchpad-only** (writes analysis, not code) | red-team, blue-team, arbiter | hardware-enforced — scoped tools | **prose** — `workspace-write`+accountability (same reason as docs-only) |
| **Bash only for narrow codex fact-checks** (judges what's presented; doesn't hand down the model's verdict) | arbiter | `tools` includes Bash, but the role prompt confines it to a narrow fact-check of the disputed empirical point (`adversarial-panel.md` §"The arbiter's codex does NOT hand down the verdict") — **a prose boundary, not a hardware one** | **prose** — no per-tool deny on Codex |
| **slash dispatch** `/role /panel /kickoff` | all | hardware-enforced — `.claude/commands/*` | **prose** — the typed `R D T` convention (no custom slash) |
| **hook gates** (LOC/precompact/no-todo/numeric-dispatch) | — | hardware-enforced — `settings.json` hooks (fire in all modes, incl. headless) | **prose/accountability** — KL-7 (live `codex exec`, 6 sessions): hooks configured this way do NOT fire in headless even with `--dangerously-bypass-hook-trust`; working hooks = plugin manifest + interactive TUI trust. For a hard gate on Codex — CI/pre-commit; for numeric dispatch — the anti-hedge rule in AGENTS.md/task-protocol.md |
| **skills** (progressive disclosure) | — | hardware-enforced — `.claude/skills/` (supports `paths:` glob-scoping) | **hardware-enforced** — `.codex/skills/`, the same primitive; the `SKILL.md` body is shared (`name`+`description`), but **`paths:` is Claude-only** (Codex reads only name+description, discovery by description) |
| **auto-reading the entry file** (session context) | — | hardware-enforced — `CLAUDE.md` | **hardware-enforced** — `AGENTS.md` (carries the content itself, a per-harness native entry file — ADR-012; NOT a pointer to CLAUDE.md — there is no CLAUDE.md file in a codex project) |
| **auto-memory** | — | hardware-enforced — native hierarchy | partial — Codex memories (opt-in), otherwise AGENTS.md |

**Reading the matrix:** where it says "prose," the commitment doesn't disappear — it rests on the
agent's discipline held on record (accountability), not on hardware. **Both live verifications are
closed** (live `codex exec`): **KL-7** (6 sessions) — hooks configured this way do NOT fire in
headless → the hooks cell = accountability (a hard gate on Codex → CI/pre-commit); **docs-only** — a
stable path is structurally impossible (the agent wrote to `src/` under
`writable_roots=["docs"]`, because cwd is always writable) → the docs-only cell = accountability.
Not a single "pending" cell: the matrix is fully grounded in 0.138.0 empirics. Details —
[g2-findings.md](../docs/evidence/g2-findings.md). Slash-dispatch and the docs/scratchpad tiers on
Codex are a deliberately accepted degradation (ADR-010/011), not a defect.

**A caveat on `Task` (ADR-014, empirically confirmed).** "docs-only **hardware-enforced**" for
architect means "doesn't write code itself"; but architect carries `Task` and **can delegate** a
Bash measurement to a read-only child (a subagent run confirmed: architect obtained exact
git/test/LOC metrics without its own Bash). So the "hardware-enforced-ness" of docs-only for
Task-bearing roles is **softer than for pure read-only**: the discipline is that the delegate is a
read-only measurer, not a write-capable child (otherwise the boundary is bypassed). For metrics this
is a deliberate, working path (see [../roles/architect.md](../roles/architect.md)); for the "doesn't
write code" guarantee, it rests on the delegate not being given Edit/Write access to code.

## Discipline going forward: keep the core clean of the runtime

To keep the portable volume from shrinking, when adding a **new** rule:

- A `universal` rule (a method, not plumbing) **must not** grow into `.claude/`-isms, slash-command
  names, plan mode, hook formats. Describe the technique, not the tool.
- Move the runtime-bound part into a rule tagged `origin: harness:claude-code` and/or add to the map
  above — don't smear it inside the universal method.
- If a new technique is universal in substance but it's convenient to lean on a Claude Code
  feature — split it: the universal substance in the method, the reliance on the feature as a
  separate note, "on this runtime — like this."

The cleaner `core/` is of the runtime, the more ports over "as is" on a move, and the cheaper the
fork.

## When the map isn't enough — parallel runtimes (BUILT)

The map above is designed for a **migration** (a one-off fork from one runtime to another). The
case of "**running two runtimes at once**" (Claude *and* Codex in parallel, live) is no longer a
fork but "a shared upstream core + thin per-runtime overlays" (git-level, not the rejected
manifest). This case went through a new panel and **has been built**:

- Decision — [ADR-010](../docs/adr/010-multimodel-core-overlays.md) (core + per-runtime git
  overlays) + [ADR-011](../docs/adr/011-process-layer-and-multimodel-build.md) (unblocking the
  build, in the form of a C+ mapping).
- Implementation — [`overlays/codex/`](../overlays/codex/) (the codex overlay), `new-project.py
  --harness claude-code|codex` (a static copy of the git tree, **without** parsing labels),
  `sync-roles.py` as an N-runtime emitter, the guarantee matrix above, a debt tripwire in
  `selftest.py`.
- The layout (`.claude/` stays in its native position, `overlays/` is only for non-default
  runtimes) and the documented mapping — [`overlays/README.md`](../overlays/README.md).

**The stop condition on the labels holds:** the overlay is selected by the `--harness` flag (static
copying), NOT by machine reading of `origin:`. Bringing back label parsing by tooling = another new
panel (see [ADR-009](../docs/adr/009-portability-boundary.md)).
