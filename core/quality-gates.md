# Task Completion Criteria

Automated checks that must be green before a task is considered done.

## Mandatory Run on Completion — [QG-NN-01 · non-negotiable · mechanical: test runner]

After the last change in the task — a full build and run of all tests.

Project command:

~~~bash
{{build-command}} && {{test-command}}
~~~

Mandatory command parameters:

- **Parallelism**: tests run in parallel across cores (`-j12`, `--parallel`, or the equivalent for your runner)
- **Verbose output**: full output for every test, not just the pass/fail result
- **Log retention**: output is written to a file for later analysis without rerunning

Example command with output retention:

~~~bash
{{test-command}} 2>&1 | tee /tmp/test-latest.log
~~~

{{Adapt to your stack and path.}}

## "Don't Lose Logs" Rule

If a test fails — never rerun without analyzing the logs. Rerunning overwrites the log and loses the failure data.

Procedure for a flaky failure:

1. Open the log of the last run
2. Find the specific failure — which assert, which values, which stack trace
3. Decide: is this a real bug or flakiness
4. If it's a real bug — fix it
5. If it's flakiness — find the cause (timing, shared state, an unstable network call) and eliminate it, don't ignore it

## "One Logical Unit = One Run" Rule

The unit of verification is a **completed logical unit of work** (a coherent set of files for one task: class + test + bridge + view), not a single file. Once you've brought the unit to a coherent state → one build + test run.

- **Do not** build after every file — on a compiled stack this is build churn and wasted time (two "code → build → code → build" cycles instead of one).
- **Do not** accumulate changes across a task boundary — several unrelated changes before the first check hide exactly what broke.

Unit boundary = task boundary (`R D T`): verify it atomically.

Exception — an isolated, risky, targeted edit (you're touching a critical invariant/protocol in a single file, and a fast signal matters more than overall pace): verify it immediately, without waiting for the rest.

## "No Warnings" Rule — [QG-NN-02 · non-negotiable · mechanical: stack check command]

Static analysis must be clean — and this is verified by **one fixed project command**, not by the agent deciding "which linters are appropriate here." The specific command and its composition (compiler / typecheck / linter / formatter) are defined in `stack/<stack>.md` → "Clean build" section and are baked in at init. The agent **runs** the command, it doesn't choose it — no tokens or reasoning "about the stack."

~~~bash
{{check-command}}   # one project command, e.g. `make check`; composition is in stack/<stack>.md
~~~

Must be green. Warnings and violations are not permitted, not ignored, not suppressed (`#pragma`, `// @ts-ignore`, `# type: ignore`, `eslint-disable`, `# noqa`, and similar) without an explicit reason in a comment nearby.

If a warning is legitimate — refactor the code so it goes away. If it comes from a third-party library — isolate its integration, don't let it spread.

## "Fast Tests Are Fast" Rule

The full unit+integration test run fits within {{TARGET_TEST_TIME}} (typically 15-30 seconds).

Network timeouts are not waited out for real — they're mocked via a setter:

~~~
service.setTimeoutMs(10)       // in test
service.setRetryDelayMs(5)     // in test
~~~

Tests do not depend on execution order, do not use `sleep()` for synchronization, and do not make real network calls.

If a test requires a real network or a slow operation — it's not a unit test, it's E2E. A separate track (see below).

## Separation of Testing Tracks

**When applicable:** the separation below applies **only if a separate QA E2E track is deployed**
(a complex project — see [pipeline.md](pipeline.md) → solo-collapse). On a simple project (solo-collapse)
there is no separate QA track: the developer implements and runs the necessary acceptance/E2E-like checks
themselves within their own task (this is NOT independent QA signoff, but coverage exists). Deploy a
separate track when "green units, but the button doesn't work" becomes a real risk. But deploying the
track is **not a coverage ceiling**: assembled reachability of every frozen-scope feature (QG-NN-05,
below) is mandatory even on solo-collapse — there the gate owner is the developer themself.

If a project has several types of tests — they are physically separated:

| Track | Who runs it | Build directory | What it checks |
|--------|--------------|-----------------|---------------|
| Dev tests | Developer, after every commit | `build/` | Unit, integration, fast, mocks |
| Assembled contract tests | QA E2E (owner of QG-NN-05) | `build-qa/` (its own target/test directory) | Reachability of frozen features through declared shipping roots: a fast build-level runner, importing only declared roots, no test-only wiring, effect assertion (§QG-NN-05) |
| E2E tests | QA, on request | `build-qa/` | Full stack, real server, everything through the UI |

Separation is ensured by:

- Different build targets
- Different build directories
- Different runners
- Different role responsibilities — the developer doesn't run E2E, QA doesn't run unit tests

The prohibitions on UI-bypassing (qa-e2e.md "Forbidden Patterns", invoke/direct API) apply **in the
E2E track**; in the assembled contract tests track, bypassing the browser is legal by construction —
there, discipline is held by the requirements of §QG-NN-05 (declared root, no bespoke injection,
effect-assert). On **solo-collapse** the tracks collapse into one: a separate build-dir is not required,
but the requirements in substance remain.

Test artifacts of **all** tracks (including `build-qa/` and the assembled suite) fall under QG-NN-01/02
just like product code: QA tests with strict errors that make the working tree's `check` fail = the task
is **NOT done** (empirical evidence: Balatro run 2 — the suite owner did not hold their own files to a
clean build).

This prevents mixing tests and accidentally running slow tests in the dev cycle.

## LOC Thresholds as a Signal — [QG-NN-03 · non-negotiable · accountability: check-loc.sh = warn]

A large file is a **suspicion** of a Single Responsibility violation, not proof. No number distinguishes a long-but-coherent parser from spaghetti — so the threshold doesn't render a verdict by itself, it **wakes up judgment**: a file that crosses the threshold for its type → must get a reasoned answer of "it does one thing, here's why" **or** a split. Silently ignoring it is not allowed (it's recorded in the task's exit report); the reviewer / code-quality skill judges by responsibilities, not lines.

The threshold is a tripwire, not a gate: `check-loc.sh` (a PostToolUse hook, included in `.claude/settings.json.example`) prints a warning for the file that crossed it, but does not block the merge. The decision "split or justifiably keep" is architectural, not arithmetic.

Project tripwire thresholds (a guideline, not a verdict; adapt to your stack):

| Code type | .cpp / .go / .ts limit | .h / header limit |
|----------|------------------------|-------------------|
| Business logic | 500 | 200 |
| Bridge/adapter | 700 | 250 |
| Parser/serializer | 800 | 150 |
| Transport/state machine | 800 | 200 |
| UI view | — | 800 |
| UI component | — | 500 |

Check before every build:

~~~bash
git diff --name-only HEAD | grep -E '\.(cpp|h|ts|go|py)$' | xargs wc -l | sort -rn
~~~

If a file exceeds the threshold — justify its coherence in the exit report OR split by responsibility (see patterns below). Auto-splitting just to hit a number is not the goal.

## Split Patterns

When a file grows past the limit, typical ways to split it:

- **By responsibility**: one class does two things — split it into two classes
- **Partial class**: for bridge models and controllers — one header, implementation spread across several .cpp files by functional group (`AppController.cpp` + `AppControllerActions.cpp`)
- **Sub-components**: for UI — extract reusable parts into separate components
- **Sub-parsers**: for parsers — one parser per response/entity type
- **Phase split**: for a state machine or protocol — by protocol phase

The choice of pattern depends on why the file grew. This is an architectural decision — if the agent is unsure, ask the user.

## "You Broke It, You Fix It" Rule — [QG-NN-04 · non-negotiable · accountability]

Every failing test after your changes is your responsibility. There is no "pre-existing failure" excuse.

- Don't disable a test
- Don't skip it via `skip`/`ignore`/`disabled`
- Don't change the assertion to match the current (broken) behavior
- Don't comment it out

Fix it so the test checks what it should, and passes because the code is correct.

## Assembled Feature Reachability — [QG-NN-05 · non-negotiable · accountability · ratified by the panel — [ADR-015](../docs/adr/015-assembled-reachability-gate.md)]

Green tests prove that **units are correct** — not that **the product does what it promised**. A test
that supplies, by itself, the wiring that the application's composition provides in shipping (passes in
a dependency, calls a trigger, injects config by hand) checks the function in isolation and **stays
silent on whether it's wired in**. A feature can have a green unit contract, **zero production calls**,
and a happy-path e2e that doesn't exercise it — everything green, while it's dead in the assembled
product (a real defect class — [ADR-015](../docs/adr/015-assembled-reachability-gate.md)).

Rule: **every atomic acceptance criterion of the frozen scope must have ≥1 run through a declared
shipping composition root** — the same entry point that shipping uses to assemble the feature — **without
bespoke injection** of wiring that the product must supply itself. The test drives the assembled system
to a characteristic case and asserts the feature's **observable effect**.

- **The reference for frozen scope is canonical, not "from memory":** the **product-level scope document**
  (scope-freeze / the scope section of `docs/PROJECT-STATE.md` / fixed promises made to the user) **plus**
  the acceptance items of the current slice's tasks (day guides `docs/day-<N>-guide.md`,
  [task-protocol.md](task-protocol.md) §Canonical artifact names; the slice is frozen by the architect at breakdown
  — [../roles/architect.md](../roles/architect.md) §Breaking the next slice into day guides). For a product-facing feature, acceptance
  must be **product-observable**; reconciliation at slice closeout is against the product-level list, not
  only against the task breakdown (task decomposition can itself push wiring out of a day's scope — that's
  exactly how both features of the ADR-015 incident got lost). Downstream artifacts (qa-uat test cases,
  BA scenarios) **refine** the frozen scope's criteria but do not expand it; ergonomic refinements without
  an output differential (auto-hiding a toast, focus) belong to the E2E track or a waiver, not the gate.
  Classifying something as "out of gate scope" (infra / engine layer / refactor) is only valid **on the
  record** in preflight with a reason; a silent skip is forbidden.
- **The unit of accounting is an atomic acceptance criterion** (Given/When/Then). A compound item → split
  it or an explicit waiver on the record. Atomic criteria are grouped into **equivalence classes** — "one
  characteristic case per behavior class," not a test for each of N variants of the same kind: the goal is
  that every frozen feature is reachable and observable, not exhaustive coverage of every combination.
- **The shipping composition root is declared explicitly.** The architect fixes the root(s) at
  kickoff/breakdown (in PROJECT-STATE / the day guide), **one per shipping artifact** (CLI, web app, …);
  QG tests import/run only declared roots. Formulas like app entry / `useX` / `startX` / DI root are
  **examples, not a menu**: shipping determines the root, the architect fixes it — not the test's
  convenience. For a multi-artifact product, a criterion is tied to the artifact(s) where the feature is
  promised: **≥1 run per such artifact** (a run through a cheap CLI root does not close a feature promised
  on the web); a criterion with no attachment must run through every declared root, or a narrowing on the
  record. The declaration is updated event-driven: a task that changes the shipping entry-point/root must
  update it.
- **Suite validity is mutation falsifiability:** an assembled suite that doesn't turn red when a
  feature's production wiring is removed is fictitious. Checked by the author when creating the suite and
  selectively by the auditor (a spot-check, not a permanent CI matrix).
- **Observability = observable effect:** the difference in product output between feature-on and
  feature-off, not the presence of the feature's artifacts. A presence assert ("element exists", "label
  renders", "property is set") does not pass the gate — assert anti-patterns #1–#4 from
  [qa-e2e](../roles/qa-e2e.md#forbidden-patterns-in-tests) apply here to **any** executor of the gate,
  including the developer on solo-collapse (#5 "invoke bypasses the UI" is E2E-specific; in the assembled
  track its role is played by the ban on bespoke injection). Assert validity uses the same mutation: turn
  off the effect while keeping the label — the gate must fail. A feature with no clear output differential
  (purely visual/aesthetic) → a waiver on the record.
- **"Assembled" means through the composition root, not necessarily through the browser.** Part of the
  coverage lives in the **assembled contract tests** track (a fast build-level runner — see the tracks
  table above), with thin e2e on top. The prohibition isn't "too slow" — it's **injecting integration
  wiring that shipping omits** (a generalization of qa-e2e anti-pattern #5 "invoke bypasses the UI" to any
  layer: a test that wires things in itself is checking a unit, not the product).
- **Determinism is a precondition, but the handle selects state, not outcome.** Driving the assembled
  system to the needed state happens through an explicit **state-selection** control surface of the
  product (seeded RNG, time, initial persisted data), not randomness. A handle that sets the **outcome /
  dependency / trigger / wiring** (`testOverrides: {bossModifierFor: …}` and any repackaging of it — as
  "config," a seed, persisted data, or any other framing) is bespoke injection. Persisted data is
  state-selection **only if the shipping product itself is able to write such data**; a fixture with
  derived state that the wiring must compute (a save with an already-materialized `activeModifier`) sets
  an outcome. The QG run happens in a **release-like configuration**, only through the product's public
  inputs. A correctly chosen state exercises real wiring: with no wiring, no seed will produce an effect,
  and the test fails.
- **Durable evidence:** the link "scope criterion ↔ assembled test" is materialized checked-in — a
  `@qg:<scope-id>` annotation in the test, or a generated manifest; PROJECT-STATE holds a reference, not
  a copy. The presence of evidence is machine-checkable (reconciling annotations against the scope list);
  quality is reviewer + spot-check. **Machine reference and checker:** the `## Frozen scope (QG-NN-05)`
  section in `docs/PROJECT-STATE.md`, items of the form ``- `SCOPE-ID` — atomic criterion`` (a `waiver`
  marker on the line = out of reconciliation); `regimen-doctor.py` performs the presence check (🟡 in a
  normal run, `--qg` — strict 🔴 as a slice done-gate for CI/pre-commit/exit). Example fill-in —
  `examples/docs/PROJECT-STATE.example.md`.
- **Optional static adjunct (warn):** dead-export / grepping production calls catches the "zero prod
  calls" subclass cheaply, but does NOT catch an optional parameter with a default at a live call site
  (the boss case of ADR-015) — a complement, not a replacement for the assembled test. The command is
  per-stack in `stack/<stack>.md` (following the pattern of `{{check-command}}` in QG-NN-02); core holds
  only the slot.
- **Unit contracts are not discarded.** They localize the bug ("where it's broken"); the assembled run
  catches "what isn't wired in." Units below give correctness, the assembled suite above gives
  reachability; the layers complement each other.

**Gate owner:** QA E2E ([../roles/qa-e2e.md](../roles/qa-e2e.md)) — the assembled-behavior suite as a
blocking done-gate on top of the developer's contracts. **On solo-collapse** (no separate QA track) the
owner is the developer themself: this is exactly where the hole hurts most (no one to independently check
the seam), so the gate applies even without a deployed QA; the static check of assembled evidence is done
by the reviewer ([../roles/reviewer.md](../roles/reviewer.md), a read-only checklist). A frozen-scope
criterion with no assembled path = the task is **NOT done** (on the record, like QG-NN-04). In the
exit/QA report: for every atomic criterion — the assembled path + the effect assert + a
`@qg:<scope-id>` reference.
**Accepted gaps** (explicitly, [ADR-015](../docs/adr/015-assembled-reachability-gate.md)): on
solo-collapse without CI, the gate is self-attestation with machine-checkable evidence presence, without
a guarantee of its quality; on stacks without a static adjunct the machine backing is weaker (a matrix of
guarantees, the ADR-010/011 pattern).

## "Don't Bisect Tests" Rule

If a test fails — read the error, find the cause in your code, fix it.

Don't run the test 10 times "to see if it's flaky or stable." The first failed run is a fact. Analyze it.

## Completion Verification Format (Proof, Not "I'm Done")

"I'm done" is **not** verification. When finishing a task, present a structured **proof** that the change
matches the contract/spec — four blocks:

~~~
COMPLETENESS  — every task requirement has code AND a test
CORRECTNESS   — behavior matches expectations (tests are green for the right reason, not rigged)
EVIDENCE      — specifics: N tests passed/failed, which commands were run, which criteria were checked
⚠ WARNINGS    — gaps/risks you did NOT close (an uncovered case, an assumption, something deferred)
~~~

This is the output format for **task exit, reviewer, and QA**. "All green" with no specifics versus
"done, but one warning" — the second is more honest: an empty `WARNINGS` is acceptable only if there
really are no gaps, not because you didn't look for them. It accompanies the constitution exit
([constitution.md](constitution.md)), it does not replace it. (= [principles.md](principles.md) PR-NN-03:
findings are verified against actual `file:line`, not asserted.)
