# ADR-015: Assembled reachability of a feature as a done gate (QG-NN-05) — "green tests ≠ wired feature"

Date: 2026-07-01 (Proposed) → 2026-07-02 (Accepted)
Status: Accepted — ratified by the adversarial panel

> Provenance — **empirical** (an autonomous package run over an MVP Balatro clone uncovered a defect class, verified by reading the code) + **panel ratification on 2026-07-02**: red → blue → arbiter, codex gpt-5.5 xhigh symmetrically on both sides. Arbiter's verdict: "build under conditions" — the direction held (no fatal defects), the text was refined with v2 amendments (P1–P8 + 3 arbiter clarifications + closing two loopholes from a targeted red re-check). Acceptance checks passed: (a) an adversarial dry run — a developer agent on the v2 text, unaware of the trap, did NOT smuggle in an outcome handle / a persisted fixture / a lowered root: it honestly presented a red gate, a wiring fix, an effect assertion, and a mutation check, and rejected closing the web feature via a cheap CLI root; (b) two independent agents' QG matrices for the day-1 example converged on the mechanics of atomization and equivalence classes. Panel artifacts live in the session scratchpad (red-r1/blue-r1/arbiter-r1/red-r2-recheck/dryrun-report).

## In short

An autonomous run assembled a playable product over 7 "days" (75 agents, ~4.9M tokens): a green build, **338 unit tests**, **3 e2e tests** — all real (independently re-verified). But the architect declared the MVP done, while the final audit + an independent grep showed: **two frozen-scope features (boss modifiers, planet hand-leveling) are implemented and unit-tested in the engine but NOT wired into the assembled product** — `useGame` calls `startRun` without `bossModifierFor` (bosses are toothless), `levelUp` has zero production call sites and no UI (hands never level up). Both pass all tests: the units exercise functions in isolation, the happy-path e2e neither exercises them nor asserts anything about them.

The cause is **structural, not "a bad auditor"**: acceptance was decomposed into per-component unit contracts. Each agent proved its own piece; **the wiring between pieces is nobody's contract.** The smoking gun is right there in the code: to test the boss, the test **manually wrote in** `bossModifierFor: () => THE_WALL` — the very wiring the assembled application omits.

Decision: introduce **QG-NN-05** — every item of the frozen scope must have ≥1 run through the real composition root (with no bespoke injection), driving the assembled system to the feature's characteristic case and asserting its observability. Owner: QA E2E; under solo-collapse, the developer. Unit contracts remain (they localize the bug); the assembled suite is added on top (it catches "not wired in").

## Context

The experiment: check whether the package closes the development loop **with no human in the loop** (the dispatcher replaced by a Workflow orchestrator, roles are the real `architect/developer/reviewer/qa-e2e/devops/auditor` + panel). A blind spot was named up front: with human UAT removed, there is nobody to say "I played it — never saw the bosses or the leveling." The experiment materialized that blind spot in measurable form.

**What happened (verified by `file:line`, not assumed):**

- `src/engine/blinds.test.ts:568-580` — the boss test calls `startRun({ ..., bossModifierFor: () => THE_WALL })`: **the test itself** supplies the selector. This proves "if the engine is given a selector, the target gets multiplied" — not "the game supplies it." `src/ui/useGame.ts:73` calls `startRun({ seed, config })` → `bossModifierFor ?? NO_BOSS_MODIFIER` → `() => undefined`.
- `src/engine/scoring.test.ts` — `levelUp(before, HandType.Pair)` is invoked directly. Production call sites of `levelUp` — zero; UI trigger/level display — zero.
- `e2e/smoke.spec.ts` — checks the tab title + root visibility. The happy-path cycle passes both without the boss modifier and without leveling; not a single `expect` requires either of them.

Not a single test is "broken" or "wrong." "Green" and "the feature is dead" coexist without contradiction, because **nobody asserted the feature's reachability through the assembled product**.

**Ground truth of the package:** the risk was already partly recognized — `quality-gates.md` §"Separation of tracks" names "green units but the button doesn't work" and advises deploying a QA track; `qa-e2e.md` forbids "invoke bypasses the UI" (anti-pattern #5). The gap: (a) the rule is narrow, about UI bypass, not about integration injection at any layer; (b) under **solo-collapse** there is no QA role, the developer writes both unit and happy-path e2e tests — and the seam stays ownerless precisely where there is no independent check.

## Decision

**Introduce QG-NN-05 "Assembled reachability of a feature" as a non-negotiable done gate** (accountability). Canon: [core/quality-gates.md](../../core/quality-gates.md) §QG-NN-05; a line in the registry [core/constitution.md](../../core/constitution.md); ownership: [roles/qa-e2e.md](../../roles/qa-e2e.md).

Substance:

1. **Every item of the frozen scope → ≥1 run through the real composition root**, with no bespoke injection of wiring that the delivery must supply itself. The test drives the assembled system to the feature's characteristic case and asserts observability.
2. **"Assembled" = through the product's composition point, not necessarily through the browser.** A generalization of the "invoke bypasses the UI" anti-pattern to any layer. Part of the coverage is a fast build-level runner, with a thin e2e layer on top.
3. **Determinism is a precondition**: drive to the state via a **state-selection** control surface (seed / time / persisted data that the delivery itself is able to write), not randomness; outcome / dependency / trigger / wiring handles are forbidden in any packaging (amendment P1). This pulls the determinism control surface into the product itself.
4. **Coverage, not combinatorics**: every feature in its characteristic case, not every combination (otherwise the gate runs off into infinity).
5. **Owner**: QA E2E (an assembled-behavior suite on top of developer contracts); under solo-collapse, the developer themself. A frozen-scope item with no assembled path = the task is NOT done.

Unit contracts (including spec-driven C+, [ADR-002](002-spec-driven-cplus.md)) **remain in place** — they localize "where it's broken"; QG-NN-05 is added on top and catches "what isn't wired in."

### v2 amendments (per the panel's verdict; canon — [quality-gates.md §QG-NN-05](../../core/quality-gates.md))

- **P1 (bypassability):** an allowed determinism handle selects **state** (seed, time, persisted data that the delivery itself is able to write); a handle that sets outcome / dependency / trigger / wiring is bespoke injection in any packaging (config, seed, a data fixture with derived state); the QG run happens in a release-like configuration via public inputs.
- **P2 (root):** the shipping composition root(s) is declared by the architect at kickoff/breakdown, one per delivery artifact; for a multi-artifact product, the criterion is tied to the artifact where the feature is promised; suite validity = mutation falsifiability ("delete the wiring → the suite goes red," spot-checked); the declaration is updated event-driven.
- **P3 (independent verifier):** a reviewer checklist (statically: root / injection / fixture / effect / `@qg` / declared roots) + an optional static adjunct as a per-stack warn slot (catches the subclass of "zero prod call sites," does not replace the assembled test).
- **P4 (referent, strengthened by the arbiter):** the frozen scope = the product-level scope document **plus** the task breakdown; product-facing acceptance is product-observable; downstream artifacts refine, they do not expand; classifying something as "outside the gate" is only on the record. (The arbiter's empirics: a referent of "day guides only" would have missed both cases in the original incident — `day-7-guide` carved the levelUp UI out of the day's scope, while the product-level item lived in `MVP-SCOPE-FREEZE.md` and was left unfulfilled.)
- **P5 (unit of account):** an atomic acceptance criterion (Given/When/Then); a compound one → split or waive; grouping into equivalence classes protects "coverage, not combinatorics."
- **P6 (tracks):** a third track of **assembled contract tests** (a fast build-level runner, importing only declared roots); qa-e2e's UI-bypass prohibitions are scoped to the E2E track; assembled supplements E2E from below, it does not replace it; under solo-collapse the tracks collapse together.
- **P7 (assertion):** observability = an observable **effect** (a feature-on/off differential); a mere presence assertion does not pass the gate; mutation-falsification of the assertion; purely visual features → a waiver, on the record.
- **P8 (evidence):** a durable link `@qg:<scope-id>` (an annotation in the test or a checked-in manifest); PROJECT-STATE holds the reference; presence is machine-checkable, quality is reviewer/spot-checked.

## Consequences

- **+** Autonomous mode cannot declare done with an unwired frozen feature: the assembled run will not show it → red. The closest machine proxy to the removed human UAT.
- **+** A single owner for "the pieces are connected" (previously nobody's contract).
- **−** Requires a deterministic control surface in the product (seed/config override) — otherwise assembled tests are flaky. Useful for many domains anyway; where it's costly, it's recorded as a deviation, on the record.
- **−** A modest rise in acceptance cost (assembled runs are heavier than unit ones). Mitigation: "assembled" ≠ "everything through the browser"; at the composition-root level, a lot of coverage runs in the fast runner.
- **Interaction:** does not overrule the separation of tracks (QA E2E) or spec-driven; it supplements them. Respects solo-collapse ([pipeline.md](../../core/pipeline.md)) — there the gate is carried by the developer.
- **Accepted residuals (explicit, not masked):** (1) under solo-collapse with no CI, the gate is self-attestation with a machine-checkable **presence** of evidence but no guarantee of its quality — a limitation of the accountability class by design; raising the bar further requires mandatory CI for autonomous mode (a strategic question left to the user); (2) the stack-neutral core does not give equal machine guarantees across stacks — the static adjunct is not available everywhere (a guarantee matrix, the ADR-010/011 pattern); (3) the boundaries of equivalence classes and the gray zones of state-vs-outcome are architect/reviewer judgment — the dispute is narrowed, not closed.

**Verification TODO:** (1) how typical this defect class is (n=1) — a second autonomous run or a passive auditor lens on the next 2–3 projects, owner: the user; (2) the share of waivers in nondeterministic domains (external API/ML) — a pilot, owner: the user/auditor; (3) strategic: mandatory CI as a precondition for autonomous mode; the ceremony budget (growth of the non-negotiable registry) — both left to the user.

## Alternatives (rejected)

- **"At least one integration test per feature" tacked on as an afterthought** — weaker: does not make reachability part of the done criterion, easy to forget. QG-NN-05 ties coverage to the frozen-scope list.
- **A full end-to-end run of every combination in the assembled product** — runs into a combinatorial explosion and an infinite gate. Rejected in favor of "each feature's characteristic case."
- **Rely on the auditor** — the auditor catches things after the fact (after `projectDone=true`) and its weighting is subjective from run to run. The gate must live in the done criterion, not in a post-hoc review.
