# Constitution — the project's load-bearing non-negotiable rules

A short **index** of load-bearing prohibitions that may not be silently violated. This is NOT the source of
the rules — the text of each rule lives in its canonical file (the ID tag sits right next to it). Here —
only the list, gate type, and check protocol. Read every session (see the regimen entry file →
"Required reading").

**Gate type:**
- **mechanical** — checked by a hook/command (objectively).
- **accountability** — agent judgment; "enforced" via a **visible contract**: the agent must explicitly
  report on applicable rules and deviations (see the protocol below). Judge of itself — but on the record.
- **Degradation (multi-runtime):** on a runtime where a mechanical gate has **no enforcer** (hook/
  command), it degrades to accountability — the agent confirms on the record, **the obligation doesn't
  vanish**, only the class of enforcement changes. Which gate is hardware-backed on which runtime — in the
  guarantee matrix ([ADR-010](../docs/adr/010-multimodel-core-overlays.md)/[ADR-011](../docs/adr/011-process-layer-and-multimodel-build.md)).

## Registry

| ID | Rule (brief) | Canon | Gate |
|----|------------------|-------|------|
| QG-NN-01 | All tests green at completion | [quality-gates.md](quality-gates.md) | mechanical: test runner |
| QG-NN-02 | Clean build with no warnings | [quality-gates.md](quality-gates.md) + `stack/*` "Clean build" | mechanical: compiler/linter |
| QG-NN-03 | LOC thresholds: crossed → justify cohesion or split | [quality-gates.md](quality-gates.md) | accountability (warn: `.claude/hooks/check-loc.sh`) |
| QG-NN-04 | "Broke it — fix it": don't disable/skip/weaken tests | [quality-gates.md](quality-gates.md) | accountability |
| QG-NN-05 | Every atomic frozen-scope criterion is observable by effect under assembled reachability (declared shipping root, no bespoke injection; state-selection is allowed, an outcome/wiring handle is not) — [ADR-015](../docs/adr/015-assembled-reachability-gate.md) | [quality-gates.md](quality-gates.md) | accountability (quality) + mechanical (evidence presence: `regimen-doctor.py --qg` strict 🔴 at slice close, ADR-017; warn slot: static-adjunct per-stack) |
| CQ-NN-01 | No TODO/FIXME | [code-quality.md](code-quality.md) | mechanical(opt): `.claude/hooks/check-no-todo.sh` |
| CQ-NN-02 | Layers unidirectional, no back-imports | [code-quality.md](code-quality.md) | accountability |
| CQ-NN-03 | No commented-out code | [code-quality.md](code-quality.md) | accountability |
| CQ-NN-04 | Security minimum: secrets not in code/logs, prepared statements | [code-quality.md](code-quality.md) | accountability |
| PR-NN-01 | Don't touch what's outside the task; forbidden git operations (stash/reset --hard/checkout --/bisect/rebase -i) | [principles.md](principles.md) | accountability |
| PR-NN-02 | Don't make architectural decisions unilaterally; don't commit for the user; don't end the session yourself | [principles.md](principles.md) | accountability |
| PR-NN-03 | Verification pass on any findings (check every file:line before showing it) | [principles.md](principles.md) | accountability |

The gate column names the enforcer on **Claude Code** (`.claude/hooks/*`); on Codex these mechanical gates
have no enforcer from config (KL-7: hooks don't fire in headless mode) → they degrade to accountability or
get moved out to **CI/pre-commit**. Which gate is hardware-backed where — the guarantee matrix
([portability.md](portability.md)).

`stack/*` constitutions (stack specifics) and domain non-negotiables (`domain/*`) — add them here too, as
rows, linking to the corresponding file. The list is curated: 8–15 load-bearing items, not a dump of every
rule.

## Check protocol (Phase −1 and exit)

**Preflight (before task implementation)** — a short block at the start of the work:

~~~
Constitution preflight:
- Applicable: QG-NN-01, CQ-NN-02, PR-NN-01   (only what's relevant to the task)
- Planned deviations: none
~~~

**Is a deviation from a non-negotiable planned?** → STOP, align with the user BEFORE implementation
(see [task-protocol.md](task-protocol.md) → protocol for ambiguity). Silent deviation is not allowed.

**Exit (before marking "done")** — in the task report:

~~~
Constitution exit:
- Mechanical: tests ✓ · clean build ✓ · (TODO hook ✓)
- Accountability: scope not expanded · layers not violated · LOC thresholds (justified/split) · no commented-out code · no secrets
- Deviations: none
~~~

**A deviation found only at exit** = the task is **NOT done** until fixed OR the user explicitly accepts
the risk. A silent "constitution OK" with no specifics is not a report (= [principles.md](principles.md) →
PR-NN-03: without evidence it doesn't count).

## Depth tiers — ceremony scaled to task size (Inline / Atomic / Full)

A full preflight/exit is sized for a feature-sized task; on small things it costs more than the work
itself. Three tiers — how much check-in weight scales to **what the task touches** (not line count):

- **Inline** — a trivial edit: one file, doesn't touch contracts/layers/schema/secrets/external
  interface, adds no dependency, easily reverted (a typo, doc text, one line, renaming a local variable, a
  format fix). → **one-line micro-exit**:
  ~~~
  Constitution micro-exit: trivial (1 file, contracts/layers/secrets untouched) · build/test ✓ · no deviations
  ~~~
- **Atomic** — one focused change = a logical unit (may touch 2-3 related files), but does **not
  introduce** a new contract/layer/architecture/dependency/external interface. → **light preflight** (one
  line: applicable rules + "no deviations") + **light exit** (mechanical ✓ + one accountability line:
  scope not expanded, layers/secrets untouched).
- **Full** — a feature-sized task: introduces or changes a contract, layer, schema, external interface,
  dependency, or a multi-file refactor. → **full preflight + exit block** (above).

Atomic = the unit of the "one logical unit = one run" check ([quality-gates.md](quality-gates.md)).

Tier rules (otherwise they're a loophole):
- **Mechanical gates are NOT weakened at any tier:** green tests + clean build (QG-NN-01/02) are
  mandatory everywhere — a hard gate, not a report.
- **Any signal of larger size → raise the tier** (Inline→Atomic→Full): a contract/layer/secret/external
  boundary surfaces, the edit creeps beyond the unit, or a deviation from a non-negotiable is planned. When
  in doubt about "which tier" — take the higher one.
- This shortens the **report**, not the rules. All non-negotiables apply at every tier; only their
  confirmation is shorter.
