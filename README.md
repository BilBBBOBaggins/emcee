# Master of Ceremonies

🇷🇺 [Русская версия](README.ru.md)

Agent-driven development regimen for **Claude Code and Codex** — the agent does the main work, not the human. The package and repository's short name is `emcee`.

## What this is

This is an **agent-workflow regimen layer** on top of your project — whether new or already
existing. A "regimen" here is a set of rules that governs how the agent writes code: clear roles
(architect, developer, reviewer, etc.), a task-specification format, numeric commands for invoking
roles, and an adversarial review procedure for important decisions.

The package provides battle-tested rules, task structure, and roles. **It does not create the
application itself.** You initialize the code, `go.mod` / `package.json`, Makefile, and CI with the
standard tool for the job (`go mod init`, `create-next-app`, `uv init`, etc.) — or hand that off to
the agent. In other words, the package is a fast start for the *regimen*, not for the *application*.

Why this is the design is recorded in [ADR-001](docs/adr/001-scope-process-overlay.md): maintaining
an aging scaffold for dozens of stacks is more than one person can own, and the agent already knows
how to initialize a stack with a single command.

### Claude Code default, Codex built-in

The default native runtime is **Claude Code** (Anthropic's CLI/extension): auto-reads `CLAUDE.md`,
the `.claude/` directory (subagents, skills, slash commands, hooks), plan mode. **Codex CLI is a
built-in target, not a manual port:** generate the project with the `--harness codex` flag, and the
package lays down Codex-native wiring — an `AGENTS.md` entry file (Codex auto-reads it; there is no
`CLAUDE.md` in a Codex project), and `.codex/agents/*.toml` agent profiles. The method (roles,
gates, pipeline) is shared: it lives in the neutral `core/` core that both entry points point to.
How this works — [ADR-011](docs/adr/011-process-layer-and-multimodel-build.md) (multi-model build)
and [ADR-012](docs/adr/012-entry-file-per-harness.md) (per-harness entry).

Here's the honest boundary: some gates **degrade from mechanical to accountability** on Codex
(hooks don't fire in headless `codex exec` — for hard CI/pre-commit enforcement); this is
explicitly flagged. Porting to **other** runtimes (Cursor, a custom harness) that have no built-in
target is still manual work guided by a map: what's tied to the runtime and how to port it —
[core/portability.md](core/portability.md); why the boundary lives in prose rather than physical
layers — [ADR-009](docs/adr/009-portability-boundary.md). The fundamental techniques (contract-first
cycle, task decomposition, separating reconnaissance from production, the adversarial method) are
runtime-independent.

## Where to start

**5 minutes — [QUICKSTART.md](QUICKSTART.md).** It walks through three scenarios step by step:

- **a new project** (empty directory);
- **an existing project without our regimen** (laid on top of the existing code);
- **an existing project with an outdated regimen** (needs an upgrade).

Plus the daily working cycle and how to keep the discipline. The rest of this page is reference
material about the package itself: how it's structured, what's in each directory, and the optional
wiring.

## North star: quality of the outcome over token economy

The package's core principle: **the quality of the outcome matters more than saving tokens or
time.** Read every recommendation through this lens:

- Clean-context discipline (thin indexes, lazy file loading) exists not to save money but for the
  agent's **reasoning quality**: less clutter in context, a more accurate answer.
- Wherever quality requires more work — a second model in the adversarial panel, verification
  passes, an independent test author — that's **default behavior**, not "if the budget allows."

## Two modes of use

The `new-project.py` generator has a `--mode` flag with two values.

- **`new`** — kickstart a new project in an empty directory. Generates the regimen scaffold, and
  from there the agent initializes the stack itself with init commands.
- **`overlay`** — lay the regimen onto an **existing** project without overwriting anything. Your
  `README.md`, code, and your own `CLAUDE.md` stay untouched.

The `overlay` mode has two sub-cases: a project **without** our regimen, and a project **with an
outdated** regimen (which needs an upgrade — see track A2 in [QUICKSTART.md](QUICKSTART.md)).

## How the agent works with this

Claude Code automatically reads the `CLAUDE.md` file at the project root at the start of every
session. From there it sees links to the rest of the regimen's files and follows them as needed.

`CLAUDE.md` defines **numeric commands** — a short way to invoke the role you need:

| Command | What it means |
|---|---|
| `N` (one number) | The architect enters day N: reads the project, produces a status. |
| `R D` (two numbers) | Role R enters the context of day D with no specific task (review, planning). |
| `R D T` (three numbers) | Role R takes task T from day D's guide. **This is the primary mode of work.** |

Here **"day"** is an increment of the project plan. A day's tasks live in `docs/day-<N>-guide.md`,
and each task contains a ready-to-use "Prompt for Claude Code" block, an "After completion" section,
and a "Commit" section. A complete worked example of a day, its roles, and the artifact chain
(spec → scenarios → test cases → code) lives in [examples/](examples/).

Executable wiring (subagents, slash commands, hooks) is **optional** — see the
["Optional wiring"](#optional-claude-code-wiring) section below. Without it, the package works in
plain **prose mode**: the agent reads markdown and becomes the role it needs to be.

## Repository structure

~~~
emcee/
├── new-project.py                  # generator: assembles the regimen (--mode new|overlay)
├── sync-roles.py                   # regenerates role tables from roles.json (--check catches drift)
├── regimen-doctor.py               # checks regimen readiness in a project; copied into the project
├── _pack_lib.py                    # shared helpers (doctor/generator import); copied with the doctor as a pair
├── render-handbook.py              # builds HTML: handbook.html (reference) + quickstart.html
├── selftest.py                     # self-test: generator and package-invariant checks
├── roles.json                      # SOLE source of the role map (number → role)
├── CLAUDE.md                       # entry file, adapted to the project
├── QUICKSTART.md                   # step-by-step start (NOT copied into the project)
├── docs/adr/                       # decisions about the package itself (NOT copied into the project)
├── docs/evidence/                  # field evidence for gates (G2/KL-7 etc.; NOT copied)
├── .claude/                        # optional wiring: agents/ skills/ commands/ hooks/
├── overlays/codex/                 # Codex runtime overlay: .codex/ + AGENTS.md fragment
├── core/                           # base agent rules (usually not edited)
├── stack/                          # language/framework rules — pick what you need, delete the rest
├── architecture/                   # architecture patterns — pick what applies
├── domain/                         # domain patterns — pick your own
├── roles/                          # role definitions — usually all of them are needed
└── examples/                       # one fully filled-in end-to-end example (NOT copied into the project)
~~~

These sources are **not copied** into the generated project because they describe the package
itself, not your code: the `docs/adr/` and `docs/evidence/` directories (package decisions and
their field evidence) and `examples/` (demonstration), plus the `QUICKSTART.md` file. The
`overlays/codex/` directory is not copied as-is — the generator assembles `.codex/` and the Codex
project's `AGENTS.md` from it.

### Tooling scripts

- **`new-project.py`** — the regimen generator. Details in the ["How to use it"](#how-to-use-it)
  section below.
- **`sync-roles.py`** — regenerates role tables from `roles.json`. The `--check` flag catches
  drift.
- **`regimen-doctor.py`** — a readiness gate for the regimen in your project: checks for unfilled
  placeholders, dangling links, role-map sync, settings, and commands. Copied into the project
  (together with its import `_pack_lib.py`). The `--qg` flag is the strict **slice-close gate**:
  it reconciles the frozen scope against checked-in `@qg` evidence
  ([core/quality-gates.md](core/quality-gates.md) §QG-NN-05, ADR-017).
- **`render-handbook.py`** — builds two HTML files from the markdown sources: `handbook.html` (the
  full reference) and `quickstart.html` (onboarding). The HTML isn't committed — the `.md` files
  themselves are the source of truth; the HTML is regenerated with `python3 render-handbook.py`.
- **`selftest.py`** — self-test: checks on the generator and the package's invariants (the count
  grows as invariants are added; current count is in the output of `python3 selftest.py`).

## How to use it

### Quick start: the generator (recommended)

The complete step-by-step "from zero to first task" walkthrough (both modes plus discipline) is in
**[QUICKSTART.md](QUICKSTART.md)**. What follows here is reference material on the generator
itself.

`new-project.py` assembles the regimen: it copies `core/` and `roles/`, adds the selected
`stack` / `architecture` / `domain` modules, fills in what it can in `CLAUDE.md`, creates stubs in
`docs/`, and, optionally, lays down the `.claude/` wiring.

How the two `--mode` values differ:

- **`new`** (default) — kickstart a new project in an empty directory. It additionally creates
  `docs/day-0-guide.md` — an initialization guide that **delegates** the work to the agent: the
  agent runs `go mod init` / `create-next-app` / `uv init` itself for the chosen stack (using the
  tool's current version, not a baked-in scaffold), gets a green baseline, and only then picks up
  Day 1.
- **`overlay`** — lay the regimen onto an existing project without overwriting anything. If
  `CLAUDE.md` already exists, the regimen is placed alongside it as `CLAUDE.regimen.md` for manual
  merging; no `day-0-guide` is created (the project is already initialized).

~~~bash
./new-project.py --list                      # available modules
./new-project.py                             # interactive (asks for the mode)

# kickstart a new project:
./new-project.py --name "Acme Teams" --dir ../acme --mode new \
    --backend go --frontend react-nextjs \
    --arch modular-monolith,multi-tenant --domain b2b-saas \
    --testing test-along --wiring yes

# overlay the regimen onto an existing project:
./new-project.py --name "Acme Teams" --dir ../existing-repo --mode overlay \
    --backend go --testing test-along --wiring yes
~~~

After generation, the script prints a checklist: unfilled `{{...}}` placeholders, dangling links to
modules that weren't selected, and — in `overlay` mode — a list of existing files left untouched,
plus next steps.

**What if your stack isn't in `stack/` yet?** Give it any name (`--backend rust`) — the generator
will create a **skeleton** `stack/rust.md` from the [stack/_TEMPLATE.md](stack/_TEMPLATE.md)
template. The skeleton has all the required sections, including the mandatory "Clean build" section
that [core/quality-gates.md](core/quality-gates.md) references. The generator also hands you a
ready-made prompt for Claude Code to fill in the rest of the file. New `architecture/` and
`domain/` files are just free-form `.md` files with no hard contract: drop them in the folder and
you're done.

### By hand (what the generator does)

1. Copy the **contents** of `emcee/` to the root of the new project so that `CLAUDE.md` ends up at
   the repository root, with the `core/ stack/ architecture/ domain/ roles/` directories alongside
   it at the top level. Claude Code auto-reads the root-level `CLAUDE.md` specifically, and the
   relative links inside it assume this layout.

   **Do not move** `CLAUDE.md` into `.claude/` — from there it isn't picked up automatically, and
   every link breaks. The `.claude/` directory is reserved for executable wiring — see
   ["Optional wiring"](#optional-claude-code-wiring).

2. Open `CLAUDE.md` and fill in the `{{...}}` placeholders for your project.

3. Fill in the remaining `{{...}}` **in the core/role/architecture files you kept as well** — not
   just in `CLAUDE.md`. Find them all:

   ~~~bash
   grep -rn '{{' . --include='*.md'
   ~~~

   Pay special attention to `roles/qa-e2e.md` and `roles/qa-uat.md` (~8 placeholders each): without
   them, those roles don't work.

4. Delete the files in `stack/`, `architecture/`, `domain/` that don't apply. After deleting, check
   that no dangling links remain:

   ~~~bash
   grep -rn 'deleted-file-name' . --include='*.md'
   ~~~

   (Links from `core/` to `architecture/` and `domain/` are made conditional — see
   [core/code-quality.md](core/code-quality.md).)

5. Adjust `roles/` if you need custom roles or different numbers. **The number map's sole source is
   `roles.json`:** edit it, then run `python3 sync-roles.py` (it regenerates the tables in
   `CLAUDE.md` and `.claude/commands/role.md`; `--check` catches drift).

6. Commit it as the project's starting commit.

## Directory contents

### core/ — base agent rules

Fundamental principles for how the agent works, independent of stack or project type. The files
fall into two groups based on when they're read.

**Read at the start of every session** (listed in `CLAUDE.md` → "Required reading"):

- `pipeline.md` — the **end-to-end "how to work" narrative**: project start (`/kickoff`) → ongoing
  work (`R D T`), who does what, where day guides come from, a worked example with every role.
- `principles.md` — fact vs. hypothesis, minimal context, visibility of work.
- `task-protocol.md` — how the agent receives and executes tasks.
- `quality-gates.md` — task-completion criteria, file-size signal thresholds, test rules.
- `constitution.md` — load-bearing non-negotiable rules + the preflight/exit check protocol.

**Read on demand** (pulled in by roles and `CLAUDE.md` → "Situational" — a deliberate split so
context isn't loaded with anything unneeded):

- `debugging.md` — how to debug correctly: gathering logs from every layer at once.
- `code-quality.md` — code standards: SRP, naming, security, readability.
- `memory.md` — memory across sessions: the `CLAUDE.md` + auto-memory hierarchy, discipline (<200
  lines per memory file, a thin index plus lazily loaded topic files).
- `spec-driven.md` — the "contract-first" cycle (C+) for tasks with a hard contract: the test is
  written before the code, by an independent author, with an adversarial review pass on the tests
  ([ADR-002](docs/adr/002-spec-driven-cplus.md)).
- `adversarial-panel.md` — an adversarial review of an architectural decision before it's committed
  to: the red team attacks the decision (and brings in codex as a second model), the blue team
  defends it honestly, the arbiter hands down a binding verdict, then a v2 synthesis and an ADR.
  Invoked with the `/panel` command.
- `second-model.md` — codex as a second pair of eyes on any role's important output (opt-in, narrow
  triggers) — generalizes what's already built into the panel and C+
  ([ADR-004](docs/adr/004-second-model-designer.md)).
- `portability.md` — the portability boundary: what's tied to the Claude Code runtime and what
  ports over as an idea; the `origin:` notation and a harness-dependency map for a future fork onto
  another runtime ([ADR-009](docs/adr/009-portability-boundary.md)).

### stack/ — language and framework rules

- `go.md` — Go 1.23+ (Echo, sqlc, slog, testify).
- `python.md` — Python 3.12+ (uv, ruff, mypy strict, FastAPI, pytest).
- `react-nextjs.md` — Next.js App Router, TypeScript strict, shadcn/ui, TanStack Query.

Add new files for your own stacks (see `stack/_TEMPLATE.md`).

### architecture/ — architecture patterns

Pick what applies to your project, delete the rest.

**Composition (the key choice):**
- `layered-architecture.md` — the general layered pattern with one-directional dependencies.
- `modular-monolith.md` — a single deployment, clear internal modules.
- `microservices.md` — independently deployable services.

**Data isolation:**
- `multi-tenant.md` — multi-tenancy with row-level security (RLS) in Postgres (for B2B).

**UI architecture:**
- `three-tier-with-bridge.md` — for desktop/mobile apps combining native and declarative UI.

**Communication:**
- `event-driven.md` — asynchronous interaction via events.

**AI-specific:**
- `ai-heavy.md` — LLM infrastructure, prompt versioning, eval suite, retrieval-augmented generation
  (RAG).
- `agentic-workflows.md` — multi-agent systems, memory, tool use.

**Testing:**
- `autonomous-testing.md` — the TestDriver pattern for UI-heavy applications.

### domain/ — domain patterns

- `b2b-saas.md` — B2B SaaS: onboarding, SSO, billing, audit log, customer success.
- `regulated.md` — compliance, personal data protection, Russia's Federal Law No. 152-FZ, GDPR,
  audits, incidents.

### roles/ — roles for the agentic workflow

**Architect (lead)** — `architect.md`: system design, ADRs, day status. Invoked with a single
number `N` (entering a day) or `/kickoff`. **It has no number in `roles.json`** — it isn't a
participant in the numeric `R D T` pipeline but leads it (see
[ADR-007](docs/adr/007-kickoff-pipeline.md), [core/pipeline.md](core/pipeline.md)).

Active numbered roles (sole source — `roles.json`, numbers 0–7):

- `reviewer.md` (0) — code review, documents problems (doesn't fix them).
- `developer.md` (1) — the primary coding agent.
- `qa-e2e.md` (2) — full-stack end-to-end testing.
- `ba.md` (3) — business analyst, extracts scenarios from the code.
- `qa-uat.md` (4) — writes test cases for the customer.
- `sa.md` (5) — system analyst, interviews domain experts.
- `debugger.md` (6) — a reactive role for specific bugs.
- `devops.md` (7) — CI/CD, pre-commit gates, secrets, deployment (the bridge from local output to
  production).

**Dormant roles** — the method is documented but they have no entry in `roles.json`: no number, no
participation in the numeric pipeline. Available ad hoc (by name); activation with a number requires
a real-world-experience gate (see the ADRs below):

- `designer.md` — for UI features, produces a wireframe **as code** straight from the spec. The
  mockup image is an ephemeral scratch file in `scratchpad/design/`, not committed to git
  ([ADR-004](docs/adr/004-second-model-designer.md)).
- `auditor.md` — a holistic, read-only audit of the whole project's health plus a map of trouble
  spots. Catches cross-task architectural drift that the per-task reviewer and the architect's
  status don't see ([ADR-005](docs/adr/005-auditor-role.md)).
- `upgrader.md` — upgrades a lagging regimen: the agent produces a report-first git-diff analysis,
  auto-updates only clean package-owned files, and a human reviews and commits
  ([ADR-006](docs/adr/006-regimen-upgrade.md)).

### examples/ — one end-to-end example

A fully filled-in example of a single feature ("invite a member" in a B2B SaaS built on Go +
Next.js). It shows the **format** of the artifacts the roles reference: a filled-in `CLAUDE.md`, a
day guide with a "Prompt for Claude Code" block, a status file, the `spec → scenarios → test cases`
chain, an ADR. Not copied into a real project — it's a demonstration. More detail in
[examples/README.md](examples/README.md).

## Optional Claude Code wiring

The package works out of the box in **prose mode**: Claude Code reads `CLAUDE.md`, opens
`roles/<role>.md` on a numeric command, and becomes that role. This is a deliberately simple mode
(see [architecture/agentic-workflows.md](architecture/agentic-workflows.md)).

If you want the rules to be enforced by more than just the agent's discipline, `.claude/` contains
**optional** executable wiring. You can skip copying it — prose mode works without it.

- **`.claude/agents/`** — roles as real subagents with frontmatter. Tool scoping turns prose-mode
  restrictions into hardware guarantees: reviewer and auditor are physically read-only; BA /
  QA-UAT / SA can only write documents; the architect has no Edit/Bash access in production. This is
  also where the adversarial panel lives (`red-team`, `blue-team`, `arbiter` — see
  [core/adversarial-panel.md](core/adversarial-panel.md)) along with the dormant `auditor`
  (dispatched ad hoc without a number, like the panel).
- **`.claude/skills/`** — auto-loaded **knowledge** (Agent Skills). These are thin triggers with a
  `description` that the agent pulls in on its own when relevant, pointing at the canonical
  `core/stack/architecture/domain` files (without duplicating them). The universal `debugging` /
  `code-quality` / `memory` / `spec-driven` skills ship with the package; the generator emits skills
  for whichever stack/architecture/domain modules you selected. Roles (subagents) and the panel
  (`/panel`) are not skills.
- **`.claude/commands/role.md`** — the `/role R D T` slash command: parses the numbers, resolves the
  role from the table in `CLAUDE.md`, and launches the subagent.
- **`.claude/commands/panel.md`** — the `/panel <decision>` slash command: runs the adversarial
  panel (red → blue → arbiter + codex) through to an ADR.
- **`.claude/hooks/` + `settings.json.example`** — gate hooks: `check-loc.sh` (a warning signal
  based on the size of the edited file — prompts SRP judgment, doesn't block),
  `checkpoint-precompact.sh` (a recovery checkpoint before context compaction), `check-no-todo.sh`
  (an opt-in Stop hook for the constitution), plus an optional Stop hook for tests.

Enabling it and further detail — [.claude/README.md](.claude/README.md).

## Decisions about the package (ADRs)

Load-bearing decisions about the package itself are recorded in [docs/adr/](docs/adr/). Each one has
gone through the adversarial panel, and each ADR describes a single regimen change with its
rationale:

| ADR | About |
|---|---|
| [001](docs/adr/001-scope-process-overlay.md) | Scope: a process overlay, not an app bootstrap. |
| [002](docs/adr/002-spec-driven-cplus.md) | Spec-driven C+ now, the executable layer deferred. |
| [003](docs/adr/003-first-km-intake.md) | The "first kilometer": fixing the dangling entry point, the intake pipeline deferred. |
| [004](docs/adr/004-second-model-designer.md) | Second model for every role (opt-in) + dormant Designer. |
| [005](docs/adr/005-auditor-role.md) | Dormant Auditor role. |
| [006](docs/adr/006-regimen-upgrade.md) | Upgrading an outdated regimen. |
| [007](docs/adr/007-kickoff-pipeline.md) | Kickoff mode + the end-to-end pipeline narrative. |
| [008](docs/adr/008-project-state-snapshot.md) | PROJECT-STATE — a snapshot, not a journal (anti-sprawl). |
| [009](docs/adr/009-portability-boundary.md) | Portability — the boundary lives in prose, not physical layers. |
| [010](docs/adr/010-multimodel-core-overlays.md) | Multi-model support — core + git overlays, gated on field evidence G1/G2. |
| [011](docs/adr/011-process-layer-and-multimodel-build.md) | Process layer (RFC) now + unblocking the multi-model build by lifting gate G1 early. |
| [012](docs/adr/012-entry-file-per-harness.md) | Entry point — a thin per-harness native file + the neutral `core/` core; no `CLAUDE.md` in a Codex project. |
| [013](docs/adr/013-feature-discovery-trigger.md) | Feature discovery: an active conditional pre-code self-stop + the AskUserQuestion rule (divergence/convergence); the intake engine stays behind gate O1. |
| [014](docs/adr/014-prompt-canon-consistency-fixes.md) | Consistency fixes for the prompt canon (single source for commands, wording reconciliation). |
| [015](docs/adr/015-assembled-reachability-gate.md) | Assembled reachability as a done-gate (QG-NN-05): "green tests ≠ wired feature." |
| [016](docs/adr/016-panel-second-model-mandatory-when-available.md) | Second model mandatory for the panel when available, symmetric across red/blue. |
| [017](docs/adr/017-machine-checked-plan-invariants.md) | Machine-checked plan invariants: hardened doctor `--qg` + the composite slice-close gate. |

## Template evolution

These templates are living documents. As you work across different projects, you'll notice:

- rules that are missing (add them);
- rules that are over-specialized for context that's gone (remove them);
- patterns that repeat across projects (promote them to `core/` or a new module).

Every few months, review the templates, update them, and push the changes upstream to the master
repository.

### What could be added in the future

Add these not preemptively, but when a real project calls for them:

- **Stack:** `rust.md`, `qt-cpp.md`, `svelte.md`.
- **Architecture:** `hexagonal.md`, `bff-pattern.md` (CQRS and event sourcing are already covered in
  `architecture/event-driven.md`).
- **Domain:** `consumer-product.md`, `marketplace.md`, `internal-tool.md`, `gaming.md`.
- **Roles:** `security-reviewer.md`, `tech-writer.md`.

## Glossary

- **Regimen** — the layer of rules, roles, and commands this package lays onto a project. Not
  code, but how the agent works with the code.
- **Role** — a mode of agent operation with its own rights and responsibilities (architect,
  developer, reviewer, etc.). Invoked with a numeric command or by name.
- **`R D T`** — the numeric command "role R takes task T from day D's guide." The primary mode of
  work.
- **Day** — an increment of the project plan; its tasks live in `docs/day-<N>-guide.md`.
- **PROJECT-STATE** (`docs/PROJECT-STATE.md`) — a snapshot of the project's current state that the
  architect reads on entering a day. **A snapshot, not a journal:** updated by overwriting, with
  resolved items discarded; the history of "what happened" lives in git, and the "why" behind
  decisions lives in ADRs.
- **ADR** (Architecture Decision Record) — a record of a single architectural decision: context,
  decision, consequences, rejected alternatives.
- **Adversarial panel** — the procedure for reviewing an important decision: the red team attacks,
  the blue team defends, the arbiter hands down a verdict. Invoked with `/panel`.
- **C+ / spec-driven** — the "contract-first" cycle for tasks with a hard contract (parsers,
  computations, validators): tests before code, an independent test author, an adversarial review
  pass on the tests.
- **Gate** — a condition without which work isn't considered done. Gates are either **mechanical**
  (objectively checked by a command: green tests, a clean build) or **accountability** (a judgment
  call by the agent, on record: layering, scope, file-size thresholds). File size is a signal that
  prompts SRP judgment, not a hard limit.
- **Owned debt (versioned maintenance debt)** — the obligation to keep a saved artifact maintained
  as it ages. The package deliberately avoids this (see
  [ADR-001](docs/adr/001-scope-process-overlay.md)).
- **Dormant role** — a role whose method is documented but which has no number in `roles.json`;
  available ad hoc, with number-based activation gated on real-world experience.
- **Prose mode** — working without the `.claude/` executable wiring: the agent simply reads
  markdown and becomes the role.
