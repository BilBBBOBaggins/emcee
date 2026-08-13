# Pipeline: how to actually work — from an empty repo to features

A connected narrative on top of roles and commands. Answers "deployed the harness — what's next?":
where the roadmap and day guides come from, who does what, how one task passes through roles.

**Main rule — process weight scales with project complexity, not headcount.** A simple project (bot,
script) lives in one window: `developer` (+`reviewer`). A complex one (multi-service, regulated, external
experts) deploys the full pipeline. Below, **the default is lightweight**; the full pipeline is marked
"[complex]".

## PHASE 0 — KICKOFF (once: a new project OR adopting an existing one)

The `R D T` grammar operates on an ALREADY-existing roadmap and days. At the start there is none —
so starting a project = **`/kickoff`** (not "enter a number").

`/kickoff` launches the **architect in kickoff mode** ([roles/architect.md](../roles/architect.md) →
"Kickoff"). It:

1. **Figures out the essence — routing questions only** (one at a time): what product, for whom, stack, and
   **routing signals** (whether a separate QA track is needed, a domain with an expert, UI) — to choose
   lightweight vs full mode, stack, which roles to stand up, the first slice. **Stop rule:** the architect
   does NOT collect happy path, edge cases, business rules, acceptance criteria, current process — that's
   domain discovery → **a separate task for SA** ([roles/sa.md](../roles/sa.md)), don't duplicate it.
   Lightweight-by-default: a simple bot = a couple of questions; a complex SaaS-class product = deeper + SA.
2. **Fills in the regimen entry file** from the answers — stack, architecture, build/test commands — and
   **owns `stack/<stack>.md`** (event rule: the file appears the moment the stack is chosen — at kickoff
   or later, when the choice came from arch-analysis/`/panel`; filling in the rest is a day-0 task; not the
   user — [roles/architect.md](../roles/architect.md) §Kickoff). **Provenance
   rule (for agent kickoff-filling):** each field is tagged with its source — `[from user]` /
   `[code:path]` / `[output:cmd]`; whatever it doesn't know from a source it **leaves as a visible
   `{{placeholder}}`, does NOT guess** (a silent invention in config is worse than a visible hole). Mechanical
   substitutions by the generator (`new-project.py`: name/stack/testing from arguments) are a separate
   generator-fill, provenance = "new-project args", not covered by this rule.
3. **Records what you said in `docs/PROJECT-STATE.md`** — in existing sections ("Next day" /
   "Open questions" / "In progress"), with provenance. Priorities — **from you**; the architect structures
   what was said, doesn't invent an order and does NOT set up a separate roadmap scheme. This is a
   snapshot of state, not product management (boundary: PM starts where a stable priorities/backlog scheme
   appears that the agent is obligated to maintain/sort — that's not the case here).
4. **Load-bearing architecture** (module boundaries, technology choice, consistency model) → run
   `/panel` → ADR in `docs/adr/` ([core/adversarial-panel.md](adversarial-panel.md)).
5. **First day guides** — from the slice: `docs/day-0-guide.md` (stack init via the standard tool, if the
   project is new) + `docs/day-1-guide.md` (first set of tasks, each assigned to a role).

**Existing project:** the architect first reads the code (via subagents per module), reconstructs the
architecture/stack in the regimen entry file, then the same slice-roadmap for the rest. The regimen was already
in place from an old version and has fallen behind → first [roles/upgrader.md](../roles/upgrader.md) (upgrade
the regimen), then `/kickoff` (set up the plan).

After kickoff: `python3 regimen-doctor.py` (🟢 = regimen filled in) → take Day 1.

## ONGOING — day by day onward (`R D T`)

The cycle repeats as long as there's a roadmap slice:

1. **Architect** (single number `N` — enters day N, status) breaks off the next slice → writes
   `docs/day-<N>-guide.md`: tasks, each with "Prompt for Claude Code", "After completion", "Commit", and
   an assigned role.
2. **Roles execute** their tasks (`R D T`). Every task: constitution preflight → work → gates
   green → constitution exit → **your commit** (the agent doesn't commit; sole exception —
   autonomous run / guide-assigned commit, [task-protocol.md](task-protocol.md)).
3. **Periodically:** status (`N`), replanning, `/panel` on load-bearing decisions, ad-hoc `auditor` on drift.
4. Complexity grows → more roles get brought in (SA for a new domain; designer stays ad-hoc — its
   digit activation remains behind gate O1-D, ADR-004).

**Where things come from (the chain):**

```
your priorities ─/kickoff→ state snapshot (PROJECT-STATE) ─architect→ day guide (day-N-guide)
                                                                          │
        spec/scenarios/test-cases (SA/BA/qa-uat, as needed) ←─────────────┘
```

**Closing a slice — the done boundary is machine-gated ([ADR-017](../docs/adr/017-machine-checked-plan-invariants.md)).**
"Slice done" / "MVP done" is declared only after the composite slice-close gate passes on a clean
tree at the project root:

~~~bash
python3 regimen-doctor.py --qg && {{check-command}} && {{test-command}}
~~~

An **orchestrator driving the pipeline autonomously** (a dispatcher over the roles) MUST run this
gate itself before accepting `projectDone`/slice-done from the architect — the architect's
self-assessment is not the done signal (the ADR-015/017 incident class: an over-declared "done"
with implemented-but-unwired features). Red = the slice is not closed, whatever the role report
says. In interactive mode the same command is run at slice close by the architect (the user
commits); a local `pre-push` hook on the slice branch is optional hardening. Deliberately NOT
per-commit and NOT mid-slice, and no hosted-CI integration is shipped — details and rationale in
[quality-gates.md](quality-gates.md) §Slice-close composite gate.

**Early assembled-integration checkpoint ([ADR-022](../docs/adr/022-obligations-governance-autonomous-profile.md)).**
Integration is paid in small installments, not at the end: **integrate what is ratified as early
as possible** — never "integrate everything now". Load-bearing forks keep their own order (panel →
verdict → ADR → wire-STOPs); but once a contract is ratified, a **thin** assembled path through
the real shipping root lands promptly — one route, reachability evidence, not feature
completeness — instead of integration deferring for many slices (the field failure: dozens of
autonomous "days" with zero product endpoints, the integration risk surfacing only at
acceptance). In overlay mode, where the product is already end-to-end, the same rule degenerates
to: **wire new work into the existing skeleton continuously** — the QG-NN-05 **discipline**
applied continuously (the composite **checker** still runs once, at slice close — see
[quality-gates.md](quality-gates.md) §Slice-close composite gate); accumulating an
implemented-but-unwired layer to merge at the end is exactly the ADR-015 incident class.

## How one task passes through roles

**Default (lightweight, solo; a.k.a. solo-collapse) — most tasks:**

`developer` takes a task from the guide → writes code + tests (including user-facing checks) →
`reviewer` reads the set of changed files declared by the developer, in a clean context → you commit. Bug →
`debugger`. A load-bearing fork along the way → stop, `/panel`. **qa-e2e as a separate track is NOT
needed — the developer codes and runs the tests themselves.**

**[Complex] full pipeline — a feature with a domain and UI** (complex SaaS-class):

1. **SA** — discovery with an expert → `docs/specs/<feature>.md` (requirements, acceptance in
   Given/When/Then).
2. **BA** — from the spec → `docs/scenarios-<DT>-<slug>.md` (user scenarios; this is BA's
   **spec-first mode** — the same role also has an extraction mode for existing code, see
   [roles/ba.md](../roles/ba.md) → "Two modes").
3. **designer** (dormant) — a wireframe from the spec (if it's a UI feature).
4. **architect** — tech spec / breakdown into day tasks.
5. **developer** — implementation per the guide.
6. **qa-uat** — from the scenarios → `docs/test-cases-<DT>-<slug>.md` (expectations in user-visible
   terms, + negative/stress/concurrency). **Designs cases, doesn't write code.**
7. **qa-e2e** — codes and runs the cases on the full stack, diagnoses chain breaks. **Separate track.**
8. **reviewer** — static check. Systemic problems → `auditor`/`architect`.

**qa-uat vs qa-e2e — not a duplicate:** qa-uat = *what* to check (the product benchmark, user-visible);
qa-e2e = *codes and runs* + diagnoses. On a simple project both collapse into the developer (this is
**solo-collapse**); the split pays off where "green unit tests but the button doesn't work" is a real
risk.

## Phase contracts (no input artifact → STOP)

The pipeline above is not "suggestions" — these are **contracts**: each phase requires the previous
phase's input artifact. Artifact missing or empty → **STOP**: return to the previous phase or ask the
user, **don't simulate progress** (don't write code without a spec, don't write test cases without
scenarios, don't review without a list of changed files — from the dispatcher or the developer's
exit report, see [task-protocol.md](task-protocol.md) → "Authoritative change set").

| Phase | Requires as input | Produces |
|------|------------------|------------|
| SA | request + domain expert | `docs/specs/<feature>.md` |
| BA | spec (spec-first) / code files named by the task (extraction — [roles/ba.md](../roles/ba.md)) | `docs/scenarios-<DT>-<slug>.md` |
| architect | spec (+ scenarios) | task breakdown / `docs/day-<N>-guide.md` |
| developer | day-guide (+ spec/design) | code + tests |
| qa-uat | scenarios | `docs/test-cases-<DT>-<slug>.md` |
| qa-e2e | test-cases | run on the full stack |
| reviewer | authoritative change-set from the dispatcher, else the developer's exit report | static analysis (write-less by hardware; shell prose-scoped to non-mutating checks — ADR-018) |

At the lightweight level (one developer) phases collapse — but the rule holds: **don't pass off an
empty or invented artifact as a ready input.** A broken/empty input is a defect of the previous phase, not
a reason to fabricate (= [principles.md](principles.md) "fact, not hypothesis"; [spec-driven.md](spec-driven.md)
"a broken test = a contract defect, to the architect/user, don't force it to fit").

**The developer's active pre-code self-stop (conditional, [ADR-013](../docs/adr/013-feature-discovery-trigger.md)).**
The entry `developer | day-guide (+ spec/design)` is passive, and `spec/design` in parentheses is
optional: at the solo default (SA collapsed into developer) nothing **obligates** starting discovery before
code. So for a task with a **domain-nontrivial or irreversible** cost (the same axis as `/panel` and
[spec-driven.md](spec-driven.md) C+ — cost of error × irreversibility) the developer, before writing code, must
**either** have sufficient existing input (day-guide / `docs/specs/` / design / ADR / PROJECT-STATE),
**or** stop and route to discovery (route to SA if deployed; otherwise self-discovery), **or**
ask the user. This is a **conditional STOP trigger, NOT a universal pre-code gate**: it does not apply to
local, technically obvious, easily reversible tasks (otherwise ceremony creeps back in against the
lightweight default). In solo mode this is a self-stop that raises the visibility of skipped discovery, **not**
an independent signoff — independence appears only when routed to SA/the user (the remainder of solo mode).

## Command grammar (cheat sheet)

| Input | What it means |
|------|-----------|
| `/kickoff` | project start: architect in kickoff mode (Phase 0). No days yet. |
| `N` (single number) | architect enters day N: reads the project, gives status/risks. Lead mode. |
| `R D` (two numbers) | role R enters day D's context without a task (review, planning). |
| `R D T` (three numbers) | role R takes task T from day D's guide. **Main mode.** |
| `/panel <decision>` | adversarial panel on a load-bearing/irreversible decision → ADR. |

The role digit map (`R`) — in the regimen entry file → "Role map" (source — `roles.json`). The architect is
NOT a digit in `R D T`; it's called by a single number `N` (lead) or `/kickoff` (start).

**This is `origin: process-convention`, not a runtime binding.** Commands (`/kickoff`, `R D T`, `N`,
`/panel`) and artifact labels ("Prompt for Claude Code") are the Claude-Code flavor of *input*; on
another runtime the same role/day/task convention holds, with a different invocation mechanism (slash/number
→ runtime equivalent, see [portability.md](portability.md)). The guarantee matrix (ADR-010/011) records:
slash-dispatch on Codex degrades to typed `R D T` — the convention holds, there's no hardware-level
invocation.

## What is NOT automated (deliberately)

The canonical `roadmap.md`/`product-brief.md` as separate files + an intake-interview-as-engine —
**deferred under a gate** ([ADR-003](../docs/adr/003-first-km-intake.md) O1 / [ADR-007](../docs/adr/007-kickoff-pipeline.md)):
built only if a retro of 2-3 real project starts shows a real loss. For now — kickoff mode (prose)
+ a snapshot in PROJECT-STATE. This is deliberate, not an omission.

**The trigger↔engine boundary invariant ([ADR-013](../docs/adr/013-feature-discovery-trigger.md) D3).** So
gate O1 doesn't blur and doesn't drag innocent edits down with it: a discovery edit that does **not**
create an owned PM artifact (roadmap / brief / backlog / intake engine) is **outside** O1; one that creates
such an artifact is **under** O1. The developer's active self-stop (above) and the `AskUserQuestion` rule
([task-protocol.md](task-protocol.md) → "User Q&A") introduce zero new canonical artifacts →
outside O1.
