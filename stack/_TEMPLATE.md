# {{STACK_NAME}} — stack rules

> SKELETON for a new stack. Created by the generator, because `stack/{{STACK_SLUG}}.md` hasn't been written yet.
> Fill in the sections below (or ask your coding agent — prompt at the end of the file). Delete this block once filled in.
> Contract: the stack file MUST close out the "Clean build" section — [core/quality-gates.md](../core/quality-gates.md) references it by name. Other sections — modeled on `stack/go.md` / `stack/python.md` (if they're not in the project, look at the sample in the emcee repo). General principles are in [core/](../core/), only language/framework specifics go here.

## Version and tools

- TODO: language/runtime version ({{minimum version and why}}).
- TODO: dependency manager and lock file (what gets committed).
- TODO: single source of truth for project configs (the equivalent of `go.mod` / `pyproject.toml`).

## Project structure

~~~
TODO: canonical directory layout.
Mark where business logic lives and where entry points live.
~~~

- TODO: boundary rule (what can/can't import what). Layers are one-directional, as in [core/code-quality.md](../core/code-quality.md).

## Error handling

- TODO: the stack's idiomatic error mechanism (exceptions / `Result` / codes) with mandatory context.
- TODO: prohibition on silently swallowing errors; error typing.

## Concurrency / async (if applicable)

- TODO: primary pattern (threads/coroutines/actor), cancellation and shared-state rules.
- Delete this section if the stack has no concurrency.

## Database (if applicable)

- TODO: data access, migrations, injection protection (parameterized queries).
- Delete this section if the stack doesn't work with a database.

## Framework / runtime (if applicable)

- TODO: default framework and justification; what's forbidden without an ADR.

## Tests

- TODO: test framework, pattern (table-driven / parametrization), unit/integration separation.
- TODO: run commands (fast vs. full); no real network/timers in unit tests (see [core/quality-gates.md](../core/quality-gates.md)).
- TODO: coverage-report command + path to the artifact. Purpose — **diagnosing gaps** (which files/paths lack tests), NOT a target percentage and NOT a task exit gate. Run by qa-e2e (by developer on solo-collapse) on request; read by auditor/architect (see `roles/qa-e2e.md` §Coverage diagnostics).

## Logging

- TODO: the stack's structured logger, prohibition on logging secrets/PII.

## Clean build — MANDATORY

This is the concretization of the "no warnings" rule from [core/quality-gates.md](../core/quality-gates.md) for {{STACK_NAME}}. Without it, the task-completion gate is undefined for this stack.

"No warnings" for {{STACK_NAME}} = green commands:

~~~bash
# TODO: compilation / typecheck with no errors and no warnings
# TODO: linter with no violations
# TODO: formatter (--check) if present
~~~

Any of: a compile/type error, a warning, a linter violation = the task is not done. Suppression (equivalents of `# noqa`, `// @ts-ignore`, `#pragma`) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

A cheap complement to the assembled test — catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability: a complement, NOT a replacement — an optional parameter with a live default won't be caught by it).

~~~bash
# TODO: the stack's dead-export / unused-symbol command (examples: deadcode ./... — Go; vulture — Python; knip — TS/JS)
~~~

## Linting

- TODO: linter(s) and strict config; list the mandatory rules/checks.

## Specific prohibitions

- TODO: stack anti-patterns that are not allowed (modeled on go.md/python.md "Specific prohibitions").

## {{STACK_NAME}}-specific patterns

- TODO: DI, module organization, idioms — what counts as "our style."

---

<!--
Prompt for the coding agent to fill in this file:

"Fill in stack/{{STACK_SLUG}}.md following the structure of stack/go.md and stack/python.md, but for {{STACK_NAME}}.
All TODO sections — with concrete rules idiomatic to {{STACK_NAME}}.
The "Clean build" section is MANDATORY: which exact commands constitute a clean build for {{STACK_NAME}}
(compiler/typecheck/linter/formatter) — core/quality-gates.md references it.
Delete inapplicable sections (e.g. DB/concurrency if the stack doesn't have them). Delete the warning block at the top."
-->
