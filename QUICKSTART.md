# QUICKSTART — how to start and keep discipline

🇷🇺 [Русская версия](QUICKSTART.ru.md)

This package is an **agent work regimen** layered on top of your project: rules, roles, numeric
commands `R D T`, quality gates, and an adversarial panel for important decisions. It doesn't
create the application itself — the agent or a standard tool initializes the stack.

If any of the terms below are unfamiliar, there's a short glossary at the end of [README.md](README.md).

## Choose your track

What comes next depends on where you're starting from:

- **[B — new project](#b--new-project)** — you have an empty directory.
- **[A1 — existing project without our regimen](#a1--existing-project-without-the-harness)** — you
  have code, but no regimen yet.
- **[A2 — existing project with an outdated regimen](#a2--existing-project-with-an-outdated-harness-upgrade)** —
  the regimen was installed from an old version and has fallen behind, and needs an upgrade.

All three tracks converge into the shared [daily cycle](#daily-cycle-common-to-all-tracks) and
[discipline](#how-to-keep-discipline-common-to-all-tracks).

> **The full picture of "how to work"** is in [core/pipeline.md](core/pipeline.md): starting via
> `/kickoff`, moving into ongoing `R D T`, who does what, where day guides come from, an example
> covering every role. Below are the practical steps.

---

## B — new project

Generate the regimen scaffold in an empty directory:

```bash
./new-project.py --name "Acme Teams" --dir ../acme --mode new \
    --backend go --frontend react-nextjs \
    --arch modular-monolith,multi-tenant --domain b2b-saas \
    --testing test-along --wiring yes
```

> **Runtime (`--harness`).** The default is `--harness claude-code`: the project's entry file is
> `CLAUDE.md`, wiring is `.claude/`. For **Codex CLI**, add `--harness codex`: the entry file is
> `AGENTS.md` (Codex auto-reads it; `CLAUDE.md` is not placed in a Codex project), wiring is
> `.codex/` (agent profiles as `*.toml`). The method is shared between both — it lives in `core/`.
> From here on, wherever `CLAUDE.md` is mentioned, on Codex read `AGENTS.md` instead (that's your
> regimen entry file). Details — [README](README.md) → "Claude Code default, Codex built-in",
> [ADR-012](docs/adr/012-entry-file-per-harness.md).

Then:

1. **`/kickoff` — the main step.** This is the command that takes the project from "empty" to
   "has a plan for day 1". The architect asks you short routing questions (what you're building,
   for whom, on what stack), **fills in `CLAUDE.md` itself** (tagging the source of every fact;
   whatever it doesn't know, it leaves as a visible `{{placeholder}}` rather than inventing one),
   records your priorities in `docs/PROJECT-STATE.md`, runs the load-bearing architecture through
   `/panel` → ADR, and produces `docs/day-0-guide.md` and `docs/day-1-guide.md`. You don't need to
   dig through `{{...}}` by hand — you just answer the questions. (Details —
   [core/pipeline.md](core/pipeline.md).)

2. **Check readiness:** `python3 regimen-doctor.py` should give a 🟢. Whatever kickoff couldn't
   fill in from source and left as `{{...}}`, fill in yourself — find it all with:
   `grep -rn '{{' . --include='*.md'`. Re-run the check after making edits.

3. **Day 0 — stack initialization.** The command `1 0 1` (the developer takes task 1 from
   `docs/day-0-guide.md`): the agent itself runs `go mod init` / `create-next-app` / `uv init`,
   fills in the actual build/test commands, and gets a **green baseline** (on the current version
   of the tool, not from a hardcoded scaffold).

4. **Day 1.** The command `1 1 1` — the developer takes the first task from `docs/day-1-guide.md`,
   which kickoff produced.

5. **Commit** — you make the starting commit yourself.

---

## A1 — existing project (without the harness)

Overlay the regimen next to your code in `overlay` mode:

```bash
./new-project.py --name "Acme Teams" --dir ../existing-repo --mode overlay \
    --backend go --testing test-along --wiring yes
```

`overlay` mode **overwrites nothing**: your `README.md`, code, and `CLAUDE.md` are left untouched.
No `day-0-guide` is created, because the project is already initialized. You can drop
`--backend`: the stack is auto-detected from the project's marker files (`pom.xml`/`build.gradle`,
`composer.json`, `go.mod`, `*.dproj`, …) and offered as the default; the detected build/framework
variant (Maven vs Gradle, Laravel vs Symfony) is recorded in the entry file's `## Stack` section.

1. **`CLAUDE.md`.** If you already had your own `CLAUDE.md`, the regimen's copy was placed
   alongside it as `CLAUDE.regimen.md` — merge it into yours by hand (or adopt it as the base). If
   you didn't have one, the package's `CLAUDE.md` is already in place.

2. **Actual commands.** Fill `CLAUDE.md` with your project's real build/test/lint commands instead
   of `{{...}}`. Fill in the remaining placeholders too: `grep -rn '{{' . --include='*.md'`.

3. **Remove what doesn't apply** from `stack/`, `architecture/`, `domain/`; check that no dangling
   links to deleted files remain.

4. **Check readiness:** `python3 regimen-doctor.py` → bring it to 🟢.

5. **First task.** Write up `docs/day-1-guide.md` and run `1 1 1`. Or ask the ad-hoc `auditor` role
   right away to assess the project's state (see [discipline](#how-to-keep-discipline-common-to-all-tracks)
   below) to get a map of the trouble spots.

---

## A2 — existing project (with an outdated harness, upgrade)

The emcee regimen was already installed from an old version and has fallen behind. **`overlay`
mode won't update it** — it deliberately doesn't overwrite existing files. There's no separate
`--mode upgrade` in the generator either: an owned merge engine would be at odds with the
package's scope (see [ADR-006](docs/adr/006-regimen-upgrade.md)). So the regimen is updated by the
**agent**, working from a git diff, while you review and commit.

### Main path — the Upgrader role

Just ask ad hoc: "update the regimen per `roles/upgrader.md`". The agent works report-first:

- generates a fresh regimen into a temporary directory;
- shows you the drift (what has diverged), a list of new files, and the ADR delta;
- auto-updates **only** clean package-owned files;
- merges mixed files and your content in point by point via diff;
- and you do the committing.

### Manual recipe (if you'd rather do it yourself)

The key safety rule: **don't overwrite files that have your filled-in `{{}}`.** What can be
updated automatically, and what only by hand:

| Auto-update (clean package-owned, no `{{}}`) | Merge by hand via `git diff` (your content) |
|---|---|
| clean `core/*.md` (no `{{` in them): constitution, principles, debugging, memory, skills, spec-driven, adversarial-panel, second-model, portability | the entry file — `CLAUDE.md`/`AGENTS.md` (name/stack/commands/rules) |
| `sync-roles.py`, `regimen-doctor.py` **together with `_pack_lib.py`** (the doctor imports it — they upgrade as a pair; a stale copy of either is a silent skew) | `roles.json` (if you renumbered roles) |
| wiring: `.claude/agents/*`, `.claude/commands/*`, `.claude/hooks/*`, `.claude/skills/*`; on Codex — `.codex/agents/*`, `.codex/skills/*` | `docs/` (your day guides, PROJECT-STATE, specs, ADRs) |
| **new** files: anything present in the fresh generation but absent from your project (compare the trees — new `core/*.md`, new roles, new wiring) | `core/*.md` and `roles/*.md` **with filled-in `{{}}`** (core: task-protocol, quality-gates, pipeline, code-quality; roles: architect, developer, qa-e2e, qa-uat, ba, upgrader) |

> ⚠️ **Don't `cp -r core/*`.** The `core/` directory contains files with your filled-in
> `{{placeholders}}` (task-protocol, quality-gates, pipeline, code-quality) — a blind overwrite
> will erase them. (`render-handbook.py` is package-only, isn't copied into the project, and isn't
> in your project at all.)

Steps:

1. **Commit the current state:** `git add -A && git commit -m "before upgrade"`. A clean tree lets
   you review the diff and roll back if needed.
2. **Fresh regimen into a temporary directory**, using the same options you used originally:
   ```bash
   ./new-project.py --name "<name>" --dir /tmp/regimen-new --mode new \
       --backend <stack> --testing <as before> --wiring yes
   ```
3. **Auto-update only the clean package-owned files** (left column of the table): copy over the
   clean core files, the tool scripts (`sync-roles.py`, `regimen-doctor.py` + `_pack_lib.py`),
   the wiring (`.claude/*`; on Codex `.codex/*`), and new files, file by file. Leave files with
   `{{}}` untouched.
4. **Mixed files and your content (right column) — merge by hand** via `git diff` against
   `/tmp/regimen-new/<file>`. Carry over new regimen sections (for example, in `CLAUDE.md` →
   "Situational", add pointers to `second-model` / `designer` / `auditor` / `upgrader`), keeping
   all of your content and `{{}}` intact.
5. **Resync and check:** `python3 sync-roles.py` → `python3 regimen-doctor.py` (🟢?) → `git diff`
   (review everything).
6. **Commit** the upgrade yourself, as a separate commit.

> What exactly changed between versions is visible in [docs/adr/](docs/adr/) — each ADR describes
> one regimen change with its rationale — plus in the package's `git log`.

---

## Daily cycle (common to all tracks)

Numeric commands (decoded in `CLAUDE.md` → "Role map"; source of truth is `roles.json`):

- **`N`** — the architect enters day N: reads the project, reports status and risks.
- **`R D`** — role R enters the context of day D (review, planning), without a specific task.
- **`R D T`** — role R takes task T from `docs/day-<D>-guide.md`. **This is the primary mode.**

The cycle for a single task (`R D T`):

1. **Preflight.** The agent lists the applicable non-negotiable rules from
   [core/constitution.md](core/constitution.md) and any planned deviations. If there's a
   deviation → the agent stops and clears it with you **before** touching code.
2. **Work** through the "Prompt for Claude Code" block from the day guide.
3. **Green gates** — all tests pass, the build is clean (no warnings), file-size limits are
   respected ([core/quality-gates.md](core/quality-gates.md)).
4. **Exit.** A check-back block against the constitution: what was verified, no deviations.
5. **The commit is yours.** The agent prints the ready-made command, but **only you commit**
   (for every task).

---

## How to keep discipline (common to all tracks)

This is the whole point of the package. Here are the levers, in order of how often they're used:

- **Every task:** a preflight/exit check-back against the [constitution](core/constitution.md) +
  green [gates](core/quality-gates.md). Without this, a task isn't considered done.
- **Check-back weight scales with task size (depth tiers):** a trivial edit (typo, one line) →
  **Inline** (one-line micro-exit); a focused logical unit → **Atomic** (a light preflight+exit);
  a feature-sized task → **Full** (the full block). Gates are never relaxed at any tier. See
  `core/constitution.md` → "Depth tiers".
- **A change touching >1 file** (refactor, migration) → start with **plan mode** (Shift-Tab or
  `/plan`): a plan before code, one you can edit in 30 seconds. If an edit broke something —
  native `/rewind` (Esc-Esc). See `core/principles.md`.
- **A load-bearing or irreversible decision** (module boundaries, technology choice, build-vs-buy,
  an expensive-to-reverse call) → **`/panel`:** red team (+codex) → blue team → arbiter → ADR. Not
  for anything trivial. See [core/adversarial-panel.md](core/adversarial-panel.md).
- **An important output from any role** (a significant reviewer finding, a spec before an ADR) →
  **a second pair of eyes:** an opt-in codex pass. See [core/second-model.md](core/second-model.md).
- **A hard contract** (parser, validator, computation) → **C+:** test-first + an independent test
  author + an adversarial review pass on the tests. See [core/spec-driven.md](core/spec-driven.md).
- **A feature with a domain-nontrivial / irreversible cost** → the agent **doesn't start coding
  without sufficient input** (spec/design/ADR): on such a task it stops itself and opens a
  discovery, or asks you, rather than coding blind. This is a **conditional** self-stop, not a
  ceremony for every little thing. Questioning follows the phase: an open question in the divergence phase,
  a pick from a list (`AskUserQuestion` + Other) in the convergence phase. See
  [core/pipeline.md](core/pipeline.md) → phase contracts + [core/task-protocol.md](core/task-protocol.md)
  → "User Q&A" ([ADR-013](docs/adr/013-feature-discovery-trigger.md)).
- **"How are we really doing / what's rotting"** → the ad-hoc `auditor` role ("assess the
  project's state"): a map of the trouble spots, catches cross-task drift. Read-only, fixes
  nothing. See `roles/auditor.md` (dormant).
- **A UI feature** → the `designer` role (dormant): a wireframe as code, generated from the spec.
  See `roles/designer.md`.
- **The regimen has fallen behind a newer package version** → the ad-hoc `upgrader` role ("update
  the regimen"): a report-first, package-owned upgrade driven by git diff, that doesn't touch your
  content. See `roles/upgrader.md` (dormant) and track [A2](#a2--existing-project-with-an-outdated-harness-upgrade)
  above.
- **After any edits to the regimen** → `python3 regimen-doctor.py` (🟢 = the regimen is intact).
- **Closing a slice** → `python3 regimen-doctor.py --qg && <check> && <tests>` on a clean tree —
  the machine done-gate: red = the slice isn't closed, whatever the reports say. Details —
  [core/quality-gates.md](core/quality-gates.md) §Slice-close composite gate (ADR-017).
- **Memory:** keep durable facts in `CLAUDE.md` (update it in place); keep the agent's
  observations in auto-memory; every file <200 lines, a thin index plus lazy loading. See
  [core/memory.md](core/memory.md).
- **PROJECT-STATE is a snapshot, not a journal.** `docs/PROJECT-STATE.md` reflects "where the
  project stands now". On entering a new day, the architect **rewrites it and discards what's been
  resolved**, rather than accumulating — the history of "what happened" stays in git (`git log`),
  the "why" behind decisions goes in ADRs. If the file does bloat anyway,
  `regimen-doctor.py` will gently warn you. More — [core/memory.md](core/memory.md).
- **Debugging** something broken → [core/debugging.md](core/debugging.md): logs from every layer
  at once, the three-attempt rule.

> **About dormant roles.** `designer` and `auditor` are available ad hoc right now (call them by
> name), but they're not in the numeric pipeline — they have no number in `roles.json`. It's worth
> activating them with a number once real-world experience confirms their value (gates in
> [ADR-004](docs/adr/004-second-model-designer.md) / [ADR-005](docs/adr/005-auditor-role.md)).
