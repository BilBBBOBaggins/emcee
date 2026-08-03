# Task intake and execution protocol

How the agent receives tasks, enters context, delivers the result.

## System of short commands

The user gives a task via short numeric commands. Decoded in the **regimen entry file** (on Claude Code —
`CLAUDE.md`, on Codex — `AGENTS.md`; auto-read by the runtime at session start) of the main project.

Common patterns:

- **`/kickoff`** = project start (no days/roadmap yet): architect in kickoff mode
  ([roles/architect.md](../roles/architect.md) → "Kickoff", full narrative — [pipeline.md](pipeline.md)).
- **Single number `N`** = architect (lead) enters day N. Reads the whole project, gives status, waits for requests.
- **Two numbers `R D`** = role R enters day D's context without being tied to a task. Planning, review, discussion.
- **Three numbers `R D T`** = role R takes task T from day D's guide. Main working mode.

**Ambiguity of `0`:** single number `0` = architect@day0 (lead); three numbers `0 D T` = role with digit 0
(per `roles.json`). Distinguished by the count of numbers: one → architect-lead; three → role. Starting
"from scratch" is `/kickoff`, not `0`.

If the message doesn't look like a command — it's a direct prompt, execute it as written.

**The trigger is binding (anti-hedge).** A message consisting only of 1–3 numbers IS this command —
dispatch immediately. Replying with a menu of commands, asking "what would you like to work on?", or
requesting confirmation is a protocol violation: a bare number is a single token with no verb, which
is exactly where a model hedges instead of acting (field case: `35` as the first message of a fresh
session got back a command menu instead of the architect entering day 35). Sole exception: the number
directly answers a question the agent itself just asked. On Claude Code the trigger is additionally
enforced mechanically — `.claude/hooks/numeric-command.sh` (a UserPromptSubmit hook, wired in
`settings.json.example`) injects the dispatch order into context on match; on runtimes without
working hooks (Codex headless — KL-7, [portability.md](portability.md)) this prose rule is the only
barrier, which is why it is part of the protocol, not a style hint.

## Canonical artifact names

The whole role pipeline reads and writes files under fixed names. Names are defined **here** — roles
reference this section rather than introducing their own paths. `<D>` — day number, `<T>` — task number,
`<DT>` = `<D>-<T>` (e.g. `41-1`), `<slug>` — short label.

| Artifact | Name / path | Author → consumer |
|----------|-----------|---------------------|
| Day guide | `docs/day-<D>-guide.md` | **architect** (breaks down the next slice from PROJECT-STATE / specs) → developer, reviewer, qa-e2e |
| Project status | `docs/PROJECT-STATE.md` | architect → everyone |
| Discovery notes | `docs/discovery/<YYYY-MM-DD>-<topic>.md` | SA → team |
| Feature spec | `docs/specs/<feature>.md` | SA/architect → developer, qa |
| ADR | `docs/adr/<NNN>-<slug>.md` | architect → everyone |
| User scenarios | `docs/scenarios-<DT>-<slug>.md` | BA/SA → qa-uat |
| Test cases | `docs/test-cases-<DT>-<slug>.md` | qa-uat → qa-e2e |
| Process metrics | `docs/PROCESS-METRICS.md` | architect → operator |
| Audit report (ad-hoc) | `docs/audit-<YYYY-MM-DD>.md` | auditor's map, entered by architect/operator → architect |

Worked examples of key artifacts — in `examples/docs/` of the emcee repo (not copied into the project
itself). If you rename the convention for the project — change it in this table, roles will pick it up.

The role digit map (which digit = which role) — the single source is **`roles.json`**. Tables in every
runtime target are generated from it (on Claude Code — `CLAUDE.md` "Role map" + `.claude/commands/role.md`;
on Codex — `AGENTS.md`): edit `roles.json` → `python3 sync-roles.py` (and `--check` catches drift across all
targets). Role files repeat their digit in the "Invocation format" section only as an example.

## Entering a session

Reading order when receiving task `R D T`:

1. Role file: `roles/{{role-file}}.md` — who you are and how you work
2. Main regimen entry file — project architecture, stack, commands
3. Day guide: `docs/day-<D>-guide.md` (artifact names — "Canonical artifact names" section above; format —
   `examples/docs/day-1-guide.example.md` in emcee) — find "Task T"
4. Code files explicitly named in the task — those only
5. Applicable modules from `stack/`, `architecture/`, `domain/` — via links from the regimen entry file,
   only if the task requires it

Don't read everything "to understand". Don't read other tasks' results. Don't read drafts and archives.

**Constitution preflight (before implementation).** After reading the task, write a short block: which
non-negotiables from [constitution.md](constitution.md) apply to this task and whether any deviations are
planned. A deviation from a non-negotiable is planned → STOP, align with the user **before**
coding (see "Protocol for ambiguity" below). Silent deviation is not allowed. **The block's size scales
by the task's depth tier** ([constitution.md](constitution.md) §Depth tiers — canon: the Inline tier
requires no preflight at all; the full form here is for a feature-sized task).

## Definition of Ready — premises are verified against source, not assumed

A task is dispatched only when it is **ready**: the premises it builds on are checked against the code on
disk, not asserted from a plausible-sounding guide. The producer of the guide owns this gate
([roles/architect.md](../roles/architect.md) → "Breaking the next slice into day guides"; reviewer applies
it when reviewing a guide) — [ADR-019](../docs/adr/019-definition-of-ready-premise-executability.md). Four
grep-verifiable checks, each recorded as a source hit (file:line / command output), not a claim:

1. **Preconditions exist on disk** — every file/module/migration/fixture/declared root the task builds on
   is present now, at the named path (not "an earlier unconfirmed task will create it").
2. **The consumer's read-port exists** — for every resource the task assumes gets read/consumed (a schema
   column read by a query, a config key loaded by a component, an event consumed by a handler, a symbol
   imported across a boundary), the read-port on that consumer is grep-verifiable. A value written with no
   reader, or a reader that does not exist yet, is a **premise defect**.
3. **Mandate + tools cover the task** — the assigned role can perform it with the tools it has (read-only
   isn't asked to edit; a shell-less surface isn't handed a shell task — cf. ADR-018).
4. **Cited precedents are verified** — any "we already do X / this follows pattern Y" justification is
   checked against the source it cites; a precedent that contradicts doctrine is worse than none.

**On intake, the executor applies the same lens:** if the task rests on a premise you cannot point at in
the source (a missing read-port, an absent precondition, a precedent that isn't there), do not build on it —
STOP and flag the gap (see "Protocol for ambiguity" below) rather than cascade a whole task off a false
premise. Field root: in a long autonomous run, plausible-but-non-executable premises in the plan were the
single most repeated cause of lost days.

## Exiting a task

Exit completeness also scales by depth tier ([constitution.md](constitution.md) §Depth tiers: Inline tier —
a one-line micro-exit). The full form for a feature-sized task, in this order:

1. Final test run per [quality-gates.md](quality-gates.md), saving logs to a file
2. Check that static checks are clean — compilation / typecheck / linter with no warnings (whatever applies to the stack, see `stack/`)
3. **Constitution exit** — a check block against [constitution.md](constitution.md): status of mechanical
   gates (tests/clean build/LOC/TODO) + accountability (scope, layers, commented-out code, secrets) +
   deviations. A deviation found only now = the task is **NOT done** until it's fixed or the user explicitly
   accepts the risk.
4. Structured report — what was done, what was checked, what wasn't done and why
5. If the role issues a commit command, print the ready-to-copy command for the user
6. Don't commit yourself

## Report format

The exact format varies by role (details in `roles/*.md`), but at minimum includes:

- What was done: **a list of actually changed files (full paths)** + a brief description
- What was checked: which tests passed, which logs were reviewed
- What wasn't done: if parts were deferred — list them explicitly with the reason
- Verdict: task done / needs rework / blocked

The report is short. Long explanations aren't needed — the user can read the code.

**Exit report as handoff input.** In a chained role invocation (developer → reviewer, any role →
architect-status), the previous role's exit report is a **required input** for the next one, primarily the
list of changed files: hardware-scoped roles (reviewer read-only, architect docs-only) **don't gather the
diff/metrics themselves**. On a runtime with an auto-dispatcher the report is passed to the subagent; in
solo mode it's **passed by the user/orchestrator** as context for the next call (not dispatch magic). A
role that didn't receive the needed input **explicitly flags the gap** ("[list of changed files not
passed]", "[metrics not received]") rather than faking completeness.

**Authoritative change set (where the dispatcher has Bash).** The dispatcher (`/role` running in the main
session with Bash) computes the real `git diff --name-only` before launching the reviewer and supplies it
as the **authoritative** list — it takes priority over the developer's self-declaration (which may omit a
file) and over a tree survey via `Glob` (which sees existence, not the fact of change). This closes the
read-only reviewer's change-attribution gap **without granting it Bash**. Without a Bash dispatcher (prose
mode) — the floor: self-declaration + `Glob` survey + disclaimer.

## Commit commands

The agent never commits. But if a role is responsible for finalizing a task (reviewer, lead), the agent
prints a ready-to-run commit command from the task guide at the end of the report, as:

~~~
git add <file list>
git commit -m "<message from the guide>"
~~~

The user copies and runs it manually.

### Anti-pattern: stranding your own approved substance on a green gate

The rule above is the **human-in-the-loop** default: the agent prints, the user runs. Where committing is
instead the executing role's own responsibility — an **autonomous run**, or a day guide that assigns the
commit to the role — the invariant is: **each role commits its OWN produced substance the moment its gate
is green.** Approved work must land in git on the green gate, committed by whoever owns the commit.

The **forbidden anti-pattern**: a role that produced and got approval for substance leaves it **uncommitted**
and defers it to "the owner" or "the human" — citing a handoff that **does not actually exist**. This
fabricates a mismatch between the approved record and git history: the day closes **red** (the gate saw
green work that never got committed), and any downstream courier or gate that reads history instead of the
in-flight record **STOP-cascades** on the phantom gap. If you produced it and it passed the gate, you commit
it — do not invent a "someone else commits this" step to hand your own green substance off into limbo.
(This does not license a role to commit *outside* its lane: a read-only or docs-only role still commits only
what its mandate lets it produce; the point is not to strand what you *were* entitled to produce.)

### Commit message format

The message is `<type>(<scope>): <what changed>`, in the imperative mood. Type: `feat` / `fix` /
`docs` / `refactor` / `test` / `chore` / `perf`. Example from a day guide:
`feat(invites): POST /api/v1/invites — create a pending invite, queue the email`.

Why this is formal: git is the project's **searchable cold memory** (the history of "what and when"), not a
dumping ground. Meaningful messages make `git log --oneline`, `git log --grep`, `git log <path>` genuinely
useful — then history does NOT need to be kept "hot" in PROJECT-STATE. Three layers of project memory:
**hot snapshot** (`docs/PROJECT-STATE.md`, overwritten) + **curated "why"** (`docs/adr/`, a bounded set of
load-bearing decisions) + **searchable git** (queried as needed, never loaded whole). A thousand commits
don't overflow context — it's never read in full, only pointwise (`--since` / `--grep` / `<path>` / `shortlog`).

## Protocol for ambiguity

If ambiguity arises during work that cannot be resolved by a minimal interpretation of the prompt:

1. Stop work
2. Formulate the question to the user as specifically as possible
3. If several reasonable answers are possible — list them
4. Wait for the answer before continuing

Don't second-guess, don't do things "just in case", don't pick the most likely option without confirmation.

## User Q&A: divergence vs convergence — [ADR-013](../docs/adr/013-feature-discovery-trigger.md) D2

When the agent questions the user (discovery, clarification, design confirmation), distinguish **two
phases** — the **form** of the question depends on them:

- **Divergence** — surfacing what's still unknown (what the feature is, what scenarios, what the
  boundaries are). The set of options is **not yet identified**. Form: **an open question** (one at a
  time, not dumped in a batch), Socratic questioning (structure — in [roles/sa.md](../roles/sa.md)
  §Discovery process). A picklist here is **harmful** — it requires knowing the options in advance, and in
  divergence they don't exist yet; a closed menu forces false framing.
- **Convergence / approve** — choosing among **already-identified** options or confirming a finished
  design. The set of options is known and justifiably complete. Form: native `AskUserQuestion` (pick from
  options + auto-`Other`, multiSelect where appropriate) — strictly better than free text: the user
  doesn't type into the chat, the choice is explicit. `origin: harness:claude-code` — on another runtime,
  the equivalent wiring (see [portability.md](portability.md)).

**Tie-breaker:** not sure whether it's divergence or convergence, OR can't justify that the set of
options is complete → treat it as **divergence** (open question). `Other` in `AskUserQuestion` is an
escape hatch for the unaccounted-for case, **not** a substitute for the divergence phase: if answers
consistently land in `Other` — you picklisted something that should have been surfaced openly.

## Parallel subtasks

If a task naturally parallelizes (reading independent modules, generating several files with no
interdependencies) — use subagents.

Rules:

- Explicitly tell the user that parallel operations are being launched
- Each parallel task has a clear brief and doesn't overlap with the others
- Each brief declares its perimeter as default-deny — what the subagent MAY modify; everything else
  is read-only, and a blocked path is a report after 2–3 retries, not an improvised workaround
  ([principles.md](principles.md) → PR-NN-04)
- Results from subagents are collected into shared context by the main agent
- Don't parallelize what has dependencies — sequencing matters more than speed
