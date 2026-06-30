# Runtime Capability Map — substrate for the multi-model regimen decision

**Scope.** FACTUAL map only — does each target runtime have an equivalent to each of the 7
enforcement-layer components of Claude Code, and how strong is it. No design proposed here.

**Method.** Claude Code column = read directly from this repo (`.claude/`, `README.md`,
`core/portability.md`). Codex CLI = consulted local `codex exec` (gpt-5.5, web-enabled) **then
independently re-verified the two load-bearing gap claims** (subagent tool-scoping, custom slash
commands) via direct doc fetch. Cursor = web search + direct doc fetch. Aider/Cline/Roo = web
search only (lighter).

**Verification confidence legend.** `[V]` = verified against a primary/official doc (URL given or
fetched). `[V-codex]` = asserted by codex with a doc citation, not independently re-fetched by me.
`[UNVERIFIED]` = could not confirm against a primary source in this pass.

**Version note.** The local `codex` binary that answered is **v0.138.0**; codex reported the latest
`openai/codex` GitHub release as **0.142.3 (2026-06-26)**. Codex's feature claims describe current
(0.14x) docs, which may be slightly ahead of the installed 0.138.0. Treat Codex feature presence as
"current-docs true", and flag the few that need a local `codex --version`-specific check.

---

## Claude Code enforcement layer — what we are trying to reproduce

From `.claude/` in this repo (the 7 components named in the task):

1. **Subagents with tool-scoping** — `.claude/agents/*.md`, frontmatter `tools:` allowlist.
   `reviewer`/`auditor` = `Read, Grep, Glob` (hardware read-only); `ba`/`qa-uat`/`sa` add `Write`
   (docs only, no code); `architect` adds `Write, Task` (no `Edit`/`Bash`). This is a **per-agent
   allowlist over the agent's core tools**, not just "can/can't write". `[V — read from repo]`
2. **Slash-commands** — `.claude/commands/*.md` → `/role R D T`, `/panel`, `/kickoff`. User-authored
   markdown prompt files invoked by name, parse `$ARGUMENTS`, dispatch a subagent. `[V — read from repo]`
3. **Hook-gates** — `.claude/hooks/*` + `settings.json`: `PostToolUse` (Edit|Write → `check-loc.sh`),
   `PreCompact` (`checkpoint-precompact.sh`), opt-in `Stop` (`check-no-todo.sh`, tests-green). `[V — read from repo]`
4. **Agent Skills** — `.claude/skills/<name>/SKILL.md`, `name`+`description` always visible (~100
   tok), body pulled on relevance (progressive disclosure); stack skills carry `paths:` globs. `[V — read from repo]`
5. **Plan mode, `/rewind`, auto-compaction** — built-in Claude Code behaviors. `[V — repo + Anthropic docs]`
6. **Auto-read `CLAUDE.md`** at session start. `[V — repo]`
7. **Auto-memory / memory hierarchy** — `core/memory.md`: native CLAUDE.md hierarchy + auto-memory. `[V — repo]`

---

## Capability matrix

Rows = the 7 enforcement components. Cells: **есть / частично / нет / другой механизм** + one phrase.

| # | Component (Claude Code) | Claude Code | Codex CLI | Cursor |
|---|---|---|---|---|
| 1 | **Subagents with per-tool allowlist** | **есть** — `tools:` frontmatter is a true allowlist over core tools (reviewer literally has no Edit/Bash). `[V]` | **частично** — custom agents under `~/.codex/agents/` or `.codex/agents/` (TOML) set `model`, `developer_instructions`, **`sandbox_mode`**, `mcp_servers`, `skills.config`. Read-only reviewer = `sandbox_mode="read-only"`. **No per-agent core-tool allowlist** (cannot say "has Bash but not Edit"); only MCP tools get `enabled_tools`/`disabled_tools`. `[V — fetched subagents doc: only sandbox_mode + MCP tool filter; no built-in-tool disable]` | **частично** — subagents in `.cursor/agents/*.md` (also reads `.claude/agents/`, `.codex/agents/`), frontmatter `name`/`description`/`model`/**`readonly`**/`is_background`. `readonly:true` = no edits + no state-changing shell. **No granular per-tool allowlist** — only the binary `readonly`. Needs Cursor 2.4+. `[V — fetched subagents doc]` |
| 2 | **Slash-commands (user-defined)** | **есть** — `.claude/commands/*.md`, arbitrary user prompts as `/name`, parse `$ARGUMENTS`. `[V]` | **нет (для кастомных)** — ~50 built-in slash commands (`/plan`,`/compact`,`/skills`,`/agent`,`/review`,`/hooks`…), but **no user-defined markdown slash-command / `~/.codex/prompts/` mechanism found**. Closest surrogates: skills (`$skill`), custom agents (`/agent`), hooks, plugins. `[V — fetched slash-commands doc: built-ins only, no custom-command system]` | **другой механизм** — no first-class custom `/command` like Claude's; **skills** (`$skill`, Cursor 2.4+) and **subagents** (delegated by description) are the invocation surface. Rules cover always/auto-attach context. `[V — docs]` |
| 3 | **Hook-gates (lifecycle events)** | **есть** — `PostToolUse`/`PreCompact`/`Stop` etc. via `settings.json`, shell command hooks. `[V]` | **есть** — hooks on by default; in `~/.codex/hooks.json` / `config.toml` / repo `.codex/`. Events: `SessionStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, **`PreCompact`/`PostCompact`**, `UserPromptSubmit`, `SubagentStart/Stop`, **`Stop`**. Caveat: docs warn `PreToolUse` is **not yet a complete enforcement boundary** (doesn't intercept every path). `[V-codex — hooks doc cited; not re-fetched]` | **есть (новее, иной набор)** — Cursor Hooks (2026): `onPreEdit` (can veto edit), `onPostEdit`, `onPreCommit`, `onApprove`. Event-scoped to edit/commit/approve, not a generic tool-use/Stop/compact lifecycle. `[V — web, multiple 2026 sources]` |
| 4 | **Agent Skills (progressive disclosure)** | **есть** — `SKILL.md`, description always visible, body on-demand, `paths:` globs. `[V]` | **есть** — Codex Agent Skills (CLI/IDE/app): name+description+path first, full `SKILL.md` on selection; `/skills` or `$skill` explicit, or implicit by description match. Dirs: repo `.agents/skills`, `~/.agents/skills`, `/etc/codex/skills`, bundled. **Same primitive.** `[V-codex — skills doc cited]` (and the running codex itself loaded a skill mid-answer — observed behavior) | **есть** — Cursor Skills (2.4+): on-demand knowledge, `$skill`, description-triggered. Same idea. `[V — docs/web]` |
| 5 | **Plan mode / rewind / auto-compaction** | **есть** — plan mode, `/rewind`, auto-compact built in. `[V]` | **частично** — **Plan**: `/plan` (+ `update_plan` tool seen in-session). **Compaction**: `/compact` + `PreCompact`/`PostCompact` hooks (manual+auto). **Rewind/undo**: **no documented direct "undo last turn"**; has `/fork`,`/side`,`/resume` (branch/resume, not rewind). `[V — fetched slash-commands list: has /plan /compact /fork /side, no undo/rewind verb]` | **частично** — Plan/Agent modes exist; auto-compaction exists; **no documented Claude-style `/rewind` checkpoint-restore** found. `[UNVERIFIED — rewind specifically]` |
| 6 | **Auto-read project instructions at session start** | **есть** — root `CLAUDE.md` auto-read. `[V]` | **есть (и богаче иерархия)** — `AGENTS.md` auto-read; global `~/.codex/AGENTS[.override].md` + project root→CWD chain (one file/dir), nested overrides later, cap `project_doc_max_bytes=32 KiB`. Also reads `.codex/config.toml`. `[V-codex — agents-md doc cited]` | **есть** — `.cursor/rules/*.mdc` (frontmatter `description`/`globs`/`alwaysApply`), legacy `.cursorrules`, **and `AGENTS.md` at root as cross-IDE fallback**. `alwaysApply:true` = always in prompt. `[V — docs/web]` |
| 7 | **Auto-memory / memory hierarchy** | **есть** — native CLAUDE.md hierarchy + auto-memory (`core/memory.md`). `[V]` | **есть (opt-in)** — Codex **memories**: generates local memory files from prior threads, injects into future sessions; `~/.codex/memories/`; `memories.generate_memories` / `use_memories`. **Off by default.** Docs say required/team guidance belongs in `AGENTS.md`, not memory. `[V-codex — memories doc cited]` | **частично / другой механизм** — no native cross-session auto-memory primitive equivalent; community pattern = a "memory" rule/`.mdc` file the agent edits. Rules are the persistence surface. `[UNVERIFIED — no official auto-memory feature confirmed]` |

### Optional runtimes (lighter pass — web only)

- **Aider** — `CONVENTIONS.md` (auto-context via `.aider.conf.yml`), `.aiderignore`. No subagents, no
  hooks, no skills, no slash-command-as-prompt system, no per-role tool-scoping. Method-as-prose only.
  `[V — web: config covers conventions/ignore, nothing agentic]`
- **Cline** — `.clinerules/` (all `.md`/`.txt`, optional `paths:` glob frontmatter, no-frontmatter =
  always active); moving toward reading `AGENTS.md`. No per-tool-scoped subagents surfaced. `[V — Cline docs]`
- **Roo Code** — relevant outlier: **custom modes** (`.roomodes`) support a `fileRegex`-based
  **edit-restriction** per mode (a mode that can only edit files matching a regex). That's a real,
  if coarse, enforcement primitive — closer to "BA writes only docs" than Codex/Cursor's binary
  read-only. `[UNVERIFIED — from general knowledge + Roo issue thread, not re-fetched this pass]`

---

## Наименьший общий знаменатель (что выживает везде)

**Гарантии, переживающие переезд на ЛЮБОЙ из Codex/Cursor (и даже Aider/Cline):**

- **Auto-read project instructions** — universal. `CLAUDE.md`→`AGENTS.md`/`.cursor/rules`/`.clinerules`.
  Every runtime reads *some* always-on instruction file. The role-router prose, the "обязательно
  читать", the constitution — all survive verbatim as instruction text. **This is the backbone that
  always lands.**
- **Roles-as-prose** — universal. A role = a prompt. Every runtime can be told "you are now Reviewer,
  obey roles/reviewer.md". The *discipline* survives; only the *hardware enforcement* of it varies.
- **Skills (progressive-disclosure knowledge)** — survives on Codex and Cursor as the SAME primitive
  (description-triggered, body-on-demand). Lost only on Aider/Cline (degrades to always-on rule text).

**Гарантии, выживающие на Codex/Cursor но НЕ на слабых (Aider/Cline):**

- **Read-only enforcement for a reviewer/auditor** — survives as `sandbox_mode="read-only"` (Codex)
  or `readonly:true` (Cursor). The *binary* "this agent cannot touch files" is reproducible. Lost on
  Aider/Cline (no subagent isolation).
- **Lifecycle hook-gates** — survive on Codex (rich event set incl. `Stop`/`PreCompact`, matching
  ours closely) and Cursor (edit/commit-scoped only). Lost on Aider/Cline.
- **Plan mode + auto-compaction** — survive on Codex/Cursor. Lost on Aider/Cline.

**Гарантии, которые ТЕРЯЮТСЯ или деградируют даже на сильных рантаймах (Codex/Cursor):**

- **Granular per-tool subagent allowlist** — **LOST on both Codex and Cursor.** Our regimen distinguishes
  three write-tiers: read-only (reviewer), docs-only-Write (BA/QA/SA), and code (developer). Codex and
  Cursor both collapse this to **binary read-only vs. full** (`sandbox_mode`/`readonly`). The
  middle tier — "can Write `.md` docs but not touch code" — has **no hardware equivalent** on either.
  It degrades to a prose/honor instruction, or to a hook that vetoes writes outside `docs/`.
  (Roo's `fileRegex` is the only surveyed runtime that could re-create the docs-only tier in hardware.)
- **User-defined `/role`, `/panel`, `/kickoff` slash commands** — **LOST on Codex** (no custom-command
  primitive), **degraded on Cursor** (no first-class custom `/command`; remap to a skill or subagent
  invoked by description). The *grammar* `R D T` survives as a typed convention; the *one-keystroke
  dispatch* does not.
- **`/rewind` checkpoint-restore** — no verified equivalent on Codex (branch/resume only) or Cursor.
  Degrades to git discipline.

---

## Что переносится прозой без потерь (метод, НЕ слой принуждения)

Гипотеза задачи («метод переносится весь, принуждение — нет») **подтверждается**. Всё в `core/`,
помеченное `origin: universal` в `portability.md`, — это просто текст инструкции, и любой рантайм с
auto-read instruction-файлом исполнит его одинаково:

- **spec-driven (C+ / contract-first)** — test-first, independent test author, adversarial test
  read-through. Pure method. Lands verbatim. `[перенос без потерь]`
- **debugging** — simultaneous multi-layer log collection, no-guessing, rule-of-three. Pure method. `[без потерь]`
- **adversarial-panel** — red→blue→arbiter→synthesis→ADR. The *process* is prose; only the
  `/panel` *launcher* and the red/blue/arbiter *subagents* are harness-bound. The method itself is
  runtime-agnostic, AND on Codex/Cursor the panel agents can still be real subagents (just without
  the per-tool allowlist; sandbox/readonly suffices since panel agents mostly read+write scratchpad).
  Codex is *already* the "second model" the panel calls — so on Codex the panel's external-model leg
  is native. `[метод без потерь; launcher и tool-scoping — перепаять]`
- **principles, code-quality, task-protocol, constitution** — non-negotiable rules as prose. Land verbatim.
- **roles as prompts** — the role *definitions* (`roles/*.md`) are prose and transfer 1:1. Only their
  *enforcement* (tool-scoping) and *dispatch* (`R D T` slash) are harness-bound.

**Вывод по методу:** the entire `core/` method layer + role *content* is portable as ideas with zero
loss. This matches `portability.md`'s own claim that `universal`-tagged rules "переносятся как идея".

---

## Самые большие неизвестные (что не подтвердил + каким экспериментом проверить)

1. **Codex per-agent tool granularity beyond sandbox** `[partially verified — gap confirmed]`.
   Confirmed via doc fetch: custom-agent TOML = `sandbox_mode` + MCP `enabled_tools`/`disabled_tools`,
   **no built-in-tool (edit/apply_patch/shell) disable**. *Residual unknown:* whether a future/0.14x
   field adds it. **Experiment:** `codex` → create `.codex/agents/reviewer.toml`, try to express
   "no apply_patch"; inspect `codex --help`/`/agent` and `config.toml` schema for a tools key.
2. **Docs-only write tier on Codex/Cursor** `[UNVERIFIED that a hook can cleanly do it]`. Hypothesis:
   a `PreToolUse`/`onPreEdit` hook vetoing writes outside `docs/` re-creates the BA/QA "docs-only"
   tier. But Codex docs *warn* `PreToolUse` isn't a complete boundary. **Experiment:** write a
   Codex `PreToolUse` hook that rejects edits to non-`docs/` paths; confirm it actually blocks an
   `apply_patch` to `src/`. If `PreToolUse` doesn't fire for that path → hard gap.
3. **Codex `update_plan` tool reality** `[partially]`. Seen in-session, but only `/plan` verified
   from public docs. **Experiment:** inspect tool list in a live Codex run / docs for `update_plan`.
4. **Codex memories at installed version** `[V-codex, not version-checked]`. Memories are doc-current
   (0.14x) but the local binary is 0.138.0. **Experiment:** `codex` → `/memories`; check
   `~/.codex/config.toml` for `[memories]` support on the installed build.
5. **Cursor `/rewind` and auto-memory** `[UNVERIFIED]`. Could not confirm a checkpoint-restore or a
   native auto-memory primitive. **Experiment:** Cursor docs/changelog search for "checkpoint"/"rewind"
   and "memory"; or test in-app.
6. **Hook enforcement completeness on Codex** `[V-codex caveat, not stress-tested]`. Docs say
   `PreToolUse` is "not a complete enforcement boundary". **Experiment:** attempt to bypass a
   `PreToolUse` deny-hook via different tool paths (shell vs apply_patch) and see what slips through —
   this directly bounds how much enforcement (vs. honor-system) survives on Codex.
7. **Roo `fileRegex` edit-restriction** `[UNVERIFIED this pass]`. If real, Roo is the *only* surveyed
   runtime that reproduces the docs-only middle tier in hardware. **Experiment:** read Roo Code custom-modes
   docs for the `fileRegex`/`groups: [edit, fileRegex]` schema.

---

## Sources

- Repo (read directly): `.claude/`, `README.md`, `core/portability.md`.
- Codex CLI: local `codex exec` (gpt-5.5, web-enabled) + direct fetch of
  `developers.openai.com/codex/subagents`, `…/cli/slash-commands` (re-verified gap claims);
  codex-cited: `…/guides/agents-md`, `…/concepts/sandboxing`, `…/hooks`, `…/memories`, `…/skills`, `…/mcp`.
- Cursor: `cursor.com/docs/subagents`, `cursor.com/docs/rules`, `cursor.com/changelog/2-4`, plus 2026 web write-ups.
- Aider/Cline/Roo: Cline docs (`docs.cline.bot/customization/cline-rules`), comparison write-ups, Roo issue threads.
