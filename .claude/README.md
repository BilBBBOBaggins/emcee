# .claude/ — optional executable wiring

This folder turns the package's **prose** roles and numeric commands into real Claude Code mechanisms. It is **optional**.

By default the package runs in prose mode: a single Claude Code reads `roles/<role>.md` and becomes that role — a deliberate choice, simple and workable for a solo/small team. The wiring below is an additive upgrade for those who want the rules to not rest on agent discipline alone. It breaks nothing in the prose model.

## What's inside

### `agents/` — roles as real subagents

Each file wraps a role in frontmatter (`name`, `description`, `tools`), making it a dispatchable subagent. The key benefit — **tool-scoping turns the "don't write" prohibitions into hardware ones**. Since [ADR-018](../docs/adr/018-second-model-reachability-and-panel-burden.md) every role also carries `Bash`, prose-scoped by its body to second-model (codex) calls and non-mutating checks — so "don't run" is a scoped-use prose boundary, while "don't write/edit code" stays physically impossible:

| Subagent | tools | What it enforces |
|----------|-------|--------------------|
| `reviewer`, `auditor` (dormant, ad-hoc — ADR-005) | Read, Grep, Glob, Bash | "do NOT change code" — physically impossible (no Edit/Write); "do NOT run tests, Bash = codex + non-mutating checks only" — prose-scoped (ADR-018) |
| `ba`, `qa-uat`, `sa` | + Write, Bash | write only documents, don't touch code (no Edit); Bash = codex calls only (ADR-018) |
| `architect` | + Write, Task, Bash | documents (ADR/spec) + parallel reading via Task; no Edit; Bash = codex + non-mutating metrics (ADR-018) |
| `developer`, `qa-e2e`, `debugger`, `devops` | + Edit, Write, Bash | write code/tests/configs |
| `red-team`, `blue-team` | Read, Grep, Glob, Bash, Write | adversarial panel: write the attack/defense to `scratchpad/panel/`, Bash — to bring in codex |
| `arbiter` | Read, Grep, Glob, Bash, Write | adversarial panel: judges and writes the verdict; Bash — **only for a narrow codex fact-check of a disputed empirical point** (`core/adversarial-panel.md` §"The arbiter's codex does NOT hand down the verdict"), NOT for ruling on "whose argument is stronger" |

The body of pipeline roles is short and points to the canonical `roles/<role>.md`. The body of `red-team`/`blue-team`/`arbiter` is a self-contained system prompt (the method's source is [../core/adversarial-panel.md](../core/adversarial-panel.md)).

### Adversarial panel

`red-team` → `blue-team` → `arbiter` — an adversarial review of a non-trivial architectural decision before commit. Red is required to bring in **codex** as a second, independent model; the arbiter hands down a binding verdict; at the end codex reviews the v2 synthesis for internal contradictions. Full method and run process — [../core/adversarial-panel.md](../core/adversarial-panel.md). These agents are dispatched not by a digit but by the panel orchestrator (the `/panel` command, or manually per `core/adversarial-panel.md`).

### `skills/` — auto-pulled knowledge (Agent Skills)

A thin layer over **knowledge** (not over actions). Each skill is a folder `skills/<name>/SKILL.md` with
frontmatter (`name` + `description`) and a short body. The description is always visible to the agent (~100 tokens),
and the body is pulled in **only when the agent itself judges the skill relevant to the task** (progressive
disclosure). This way the needed knowledge is "woken up" more reliably than a link in a wall-of-text CLAUDE.md.

**Additive and dedup-free:** a skill is a trigger that points to the **canonical file**
(`core/*.md`, `stack/*.md`, `architecture/*.md`, `domain/*.md`), not a copy of it. There is one
source of truth. Delete `skills/` — prose mode (the "Situational" links in CLAUDE.md) keeps working.

**Authoring standard — [../core/skills.md](../core/skills.md):** a skill = router-pointer (Purpose /
When-to-use / **When-NOT** / decision-tree if needed / pointer), a quality bar for "when to even create one"
(frequent ∨ expensive failure ∨ recurring review comments; NOT for one-off / vague / policy-prose),
good/bad triggers. Skill content is harness-neutral; the discovery mechanism is per-harness (P4).

- **Universal (in the package):** `debugging`, `code-quality`, `memory`, `spec-driven` → `core/*.md`.
- **Per project choice (emitted by the generator):** one skill per chosen `stack` /
  `architecture` / `domain`, pointing to the copied canonical file. **Stack skills carry a
  `paths:` glob** (e.g. `**/*.go`) — reliable path-scoped activation on matching files, plus
  `description` as a fallback (model-decided is ~50% reliable on its own). Arch/domain rely on `description`
  (they don't map to a file type). `paths:` is recent (Claude Code v2.1.84+) and buggy in places — hence
  keeping both triggers.

**What is deliberately NOT a skill:**
- **Roles** — remain subagents (`agents/`) + numeric commands `R D T`. A separate primitive.
- **The adversarial panel** — remains **explicit** (`/panel`): it is expensive and high-stakes, needing
  a deliberate user gate, not an auto-run on the agent's guess.
- **principles / task-protocol / quality-gates** — read EVERY session, living in CLAUDE.md's
  "Required reading", not in conditional skills.

### `commands/role.md` — numeric command as a slash command

`/role 1 5 24` parses `$ARGUMENTS`, resolves the digit against the table in `CLAUDE.md`, opens the day guide, and launches the right subagent. It makes the `R D T` grammar invocable, not a chat incantation.

### `commands/panel.md` — launching the adversarial panel

`/panel <decision or question>` runs the panel from `core/adversarial-panel.md`: fixes v1 → `red-team` (+ codex) → `blue-team` → `arbiter` → v2 synthesis → final codex review → ADR. Each round is shown to the user.

### `hooks/check-loc.sh` + `settings.json.example` — gates as hooks

`check-loc.sh` — a PostToolUse hook: after every Edit/Write it checks that the **edited file** (`tool_input.file_path` from stdin, not the whole diff) hasn't exceeded the LOC limit from [core/quality-gates.md](../core/quality-gates.md).

`checkpoint-precompact.sh` — a PreCompact hook: before context compaction it writes a recovery checkpoint (time, trigger, transcript path) to `docs/checkpoints.md`, so state isn't lost on compaction (see [core/memory.md](../core/memory.md)).

`numeric-command.sh` — a UserPromptSubmit hook: if the user's message consists **only of 1–3 numbers** (the `N` / `R D` / `R D T` grammar), it injects a dispatch order into context — "this is the numeric command, launch the role now, don't answer with a menu". The bare-number trigger is otherwise prose-only and models sometimes hedge on a single-token message instead of dispatching (field case: `35` in a fresh session got a command menu instead of the architect entering day 35 — see [core/task-protocol.md](../core/task-protocol.md) → "The trigger is binding"). Any other message produces no output — ordinary prompts and `/role` are untouched.

All three are enabled by renaming `settings.json.example` → `settings.json` (it already has `UserPromptSubmit`, `PostToolUse` and `PreCompact` wired in).

`settings.json` is strict JSON: **no comments and no extra keys** (Claude Code will reject a file with unknown fields). That's why `settings.json.example` is clean, valid JSON — it can be renamed as-is.

`check-no-todo.sh` — an **opt-in** constitution Stop hook (CQ-NN-01): blocks completion if the added code contains a comment-like TODO/FIXME (a narrow contract: only added lines + new files, code file extensions, vendor/build excluded, doesn't catch an arbitrary string literal `"TODO"`). Deliberately NOT in the default `settings.json.example` (a Stop gate is more intrusive) — enable it manually:

~~~json
"Stop": [
  { "hooks": [ { "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/check-no-todo.sh" } ] }
]
~~~

Optional — a Stop hook that blocks completion until tests are green (constitution QG-NN-01). Add to the same `Stop` array (plugging in your own test command):

~~~json
{ "hooks": [ { "type": "command",
  "command": "<test-command> || (echo 'tests not green (core/quality-gates.md)' >&2; exit 2)" } ] }
~~~

## How to enable

1. Copy `.claude/` into the project root (next to `CLAUDE.md`).
2. Subagents and `/role` are picked up automatically.
3. For hooks: `mv .claude/settings.json.example .claude/settings.json`; optionally add the Stop hook (above) and adjust the LOC limits to match the table in `core/quality-gates.md`.

Don't want the wiring — just don't copy `.claude/`. Prose mode (digits → `roles/*.md` manually) works without it.
