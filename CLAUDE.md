# {{PROJECT_NAME}}

{{One sentence about the project. What it is, who it's for, why.}}

<!-- ENTRY-BODY:START — shared entry body: the generator renders it under the native entry-file name per harness. Edit it here ONCE. The harness delta is separate (on Codex the generator inserts the codex block before this body). -->

## Stack

- {{backend language}} (version)
- {{backend framework}}
- {{frontend language}} (if any)
- {{frontend framework}}
- {{database}}
- {{build system}}
- {{test framework}}

## Architecture

{{A short description of the layers or modules. If there are ADRs — link to them.}}

Layers (strictly respect the dependency direction):

1. **{{layer-1}}** — {{purpose}}. {{What's allowed, what's forbidden.}}
2. **{{layer-2}}** — {{purpose}}.
3. **{{layer-3}}** — {{purpose}}.

Rule: {{layer-1}} → {{layer-2}} → {{layer-3}}. Back-imports are forbidden.

## Commands

### Quick numeric commands

- **`/kickoff`** = project start (no days exist yet): the architect in kickoff mode — essence → regimen entry file → first slice → day guides. Full pipeline: [core/pipeline.md](core/pipeline.md).
- A single number `N` = the architect (lead) enters day N. Reads the whole project, produces a status.
- Two numbers `R D` = role R enters the context of day D with no specific task (usually for review or planning).
- Three numbers `R D T` = role R takes task T from day D's guide.

Role map:

<!-- ROLES-TABLE:START (generated from roles.json; do not edit by hand — change roles.json and run `python3 sync-roles.py`) -->
| R | Role | Role file |
|---|------|-----------|
| 0 | Reviewer | [roles/reviewer.md](roles/reviewer.md) |
| 1 | Developer | [roles/developer.md](roles/developer.md) |
| 2 | QA E2E | [roles/qa-e2e.md](roles/qa-e2e.md) |
| 3 | Business Analyst | [roles/ba.md](roles/ba.md) |
| 4 | QA UAT | [roles/qa-uat.md](roles/qa-uat.md) |
| 5 | System Analyst | [roles/sa.md](roles/sa.md) |
| 6 | Debugger | [roles/debugger.md](roles/debugger.md) |
| 7 | DevOps | [roles/devops.md](roles/devops.md) |
<!-- ROLES-TABLE:END -->

{{Keep only the roles the project actually uses. **The single source of truth is `roles.json`**: reassign/remove digits there, then run `python3 sync-roles.py` (it regenerates this table in the entry file; on Claude Code — also the table in `.claude/commands/role.md`). The "N D T" digits in the prose of role surfaces (`roles/*.md` §Invocation format, `.claude/agents/*.md`, `.codex/agents/*.toml`) are checked by `sync-roles.py --check` against roles.json: a renumber that didn't fix the prose is red, and the script names the files. Canonical pipeline artifact names — [core/task-protocol.md](core/task-protocol.md).}}

**A "day"** is an increment of the project plan. A day's tasks live in `docs/day-<N>-guide.md`: each contains a "Prompt for Claude Code" block, an "After completion" section, and a "Commit" section. Format and a working example — `examples/docs/day-1-guide.example.md`. Names of all pipeline artifacts — [core/task-protocol.md](core/task-protocol.md).

### Build and tests

{{Concrete commands for your stack. Examples below — adapt:}}

Build:

~~~bash
{{build-command}}
~~~

Static checks (linter / typecheck — referenced by QG-NN-02 in [core/quality-gates.md](core/quality-gates.md)):

~~~bash
{{check-command}}
~~~

All tests:

~~~bash
{{test-command}}
~~~

Fast run of a specific test:

~~~bash
{{fast-test-command}}
~~~

## Required reading at the start of every session

- [core/pipeline.md](core/pipeline.md) — how the whole pipeline works: project start (`/kickoff`) → ongoing (`R D T`), who does what, where the day guides come from
- [core/principles.md](core/principles.md) — the agent's base working principles
- [core/task-protocol.md](core/task-protocol.md) — how the agent understands tasks
- [core/quality-gates.md](core/quality-gates.md) — task completion criteria
- [core/constitution.md](core/constitution.md) — the load-bearing non-negotiable rules + the preflight/exit check protocol

## Situational

This is a **router of skills and regimens**: situation on the left → the ready-made skill/file on the right. When a situation matches —
**invoke the existing skill, don't reinvent** it inline (gut-feel debugging instead of `debugging`,
a homegrown quality check instead of `code-quality`). The skill already encapsulates the method; reinventing it loses
its guarantees and burns context. Not sure which skill — ask the user, don't guess.

- Debugging something broken → [core/debugging.md](core/debugging.md)
- Code quality questions → [core/code-quality.md](core/code-quality.md)
- Memory between sessions (entry-file hierarchy, auto-memory, the <200-lines-per-memory-file discipline) → [core/memory.md](core/memory.md)
- **Writing or editing a skill** → [core/skills.md](core/skills.md) (the standard: a router-pointer not a manual, a "when to create one" quality bar, a mandatory When-NOT, good/bad triggers)
- A task with a **hard contract** (parser/computation/validator/transformation) → [core/spec-driven.md](core/spec-driven.md) (C+: test-first + an independent test author + an adversarial review pass on the tests)
- **A non-trivial / irreversible architectural decision or a strategic bet** → [core/adversarial-panel.md](core/adversarial-panel.md) (launch: `/panel`)
- **A high-stakes role output that needs a second pair of eyes** (opt.) → [core/second-model.md](core/second-model.md) (an opt-in codex pass; narrow triggers, not on every step)
- **A UI feature: a wireframe/mockup is needed** → [roles/designer.md](roles/designer.md) (the role is DORMANT — activation is behind gate O1-D, see ADR-004)
- **Assessing project health / pain points** (ad-hoc "assess the project") → [roles/auditor.md](roles/auditor.md) (a holistic read-only audit, catches cross-task drift; the role is DORMANT — its digit is behind a gate, see ADR-005)
- **Updating a regimen that has fallen behind** (ad-hoc "update the regimen") → [roles/upgrader.md](roles/upgrader.md) (report-first upgrade of package-owned files by git diff; the role is DORMANT, see ADR-006)
- **Porting the regimen to another runtime / the question "what depends on Claude Code"** → [core/portability.md](core/portability.md) (the portability boundary, the `origin:` notation, the map of harness dependencies; ADR-009)
- Working with the stack → [stack/<stack-file>.md](stack/)
- Architecture patterns → [architecture/](architecture/)
- Domain specifics → [domain/](domain/)

**The rule before committing to architecture.** Before sinking engineering months into a load-bearing decision (module/service boundaries, consistency model, technology/platform choice, build-vs-buy, a strategic bet) or into anything expensive to roll back — run [core/adversarial-panel.md](core/adversarial-panel.md): red team (attacks + brings in codex) → blue team (defends honestly) → arbiter (binding verdict) → v2 synthesis → ADR. Not for the trivial and easily revertible — that's the regular architect's job. Every ADR carries a `Panel: run/skipped because …` field (the skip reason is reviewed, not taken on faith); decisions touching frozen semantics, money/CAS/crypto/PII, boundaries or migration contracts get a compact panel with codex on all three roles — no skip (see the panel file, "Burden of proof is inverted").

## Testing philosophy

{{Pick one of the three patterns and keep only its section. Delete the others.}}

### Option 1: Outside-in BDD (for B2B with domain expertise)

The pipeline that produces tests and code:

1. The system analyst or BA writes acceptance criteria in the domain's language (Given/When/Then).
2. QA UAT turns the criteria into formal test cases with expected visible behavior.
3. QA E2E or the Developer writes the test code.
4. The Developer implements the code to make the tests pass.

Tests are a **specification**, not a check. A red test = a bug in the code (or an incomplete implementation), not a problem with the test.

Apply to: B2B products, regulated domains, products with external domain experts.

### Option 2: Test-along (for solo development)

The agent writes code and tests simultaneously within one task.

- Tests cover critical paths and edge cases
- No chasing 100% coverage
- Unit tests for business logic are mandatory
- Integration tests — for modules at the seams

Apply to: solo development, fast iteration, when there's no domain expert on the team.

### Option 3: Classic TDD (for sharply defined components)

The strict red-green-refactor cycle is applied selectively to modules where the contract is crystal clear:

- Format parsers
- Computational functions
- Data transformations
- Validators

Everything else is developed Test-along.

Apply to: libraries, SDKs, components with a hard contract.

## Project specifics

{{This is the project's unique part, not covered by the templates. Examples:}}

- Business context: {{what domain, what makes it special}}
- Team setup: {{who does what}}
- External dependencies: {{services, APIs, partners}}
- Current status: {{phase, what's done, what's planned}}
- Critical project prohibitions: {{what must never be touched and why}}

## Documentation: human readability

Docs are written for their audience, and differently per audience:

- **Human-facing** (README, QUICKSTART, guides, ADRs) — **self-contained and human-readable**:
  they don't assume the whole `.md` set has been read; abbreviations are expanded on first use;
  long nested parentheses are broken into sentences, lists, or tables; every ADR opens with an
  "In short" section carrying the gist of the decision.
- **Agent-facing** (`core/`, `roles/`, this regimen entry file, the runtime wiring `.claude/`/`.codex/`) —
  **density is deliberate**: it saves the agent's context. Don't "simplify" them for humans.

Editing a human-facing doc — keep it human-readable; creating a new ADR — include an "In short" section.

## Evolution of this document

This regimen entry file is alive. Rules are added when the agent makes a mistake that formalization can prevent. Rules are removed when they are over-specialized for a context that's gone. Every 1–3 months — review the whole document and delete what's stale.

If you as the user notice the agent making the same mistake across different tasks — that's a signal the regimen entry file needs a new rule. Add it to the appropriate section.

<!-- ENTRY-BODY:END -->
