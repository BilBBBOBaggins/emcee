# Spec-driven (C+) — the contract-first cycle for hard contracts

A method for tasks with a **hard contract**: the spec is a verifiable contract, the test is written
BEFORE the code by an **independent** author, and the tests themselves go through an adversarial
review pass. The goal is to add a **new verification angle** (an oracle), not to automate passing
gates. The verdict and stop conditions — [ADR-002](../docs/adr/002-spec-driven-cplus.md).

This is a **methodology, not an executable layer**: roles are still invoked manually (`R D T`),
per-task human-commit is preserved. There is NO workflow/skill orchestrator in the repository
(ADR-001/002).

C+ invents nothing — it's a **composition of known practices** for an agentic pipeline:
contract-first testing (test-as-contract before code), independent QA (test author ≠ implementer),
a mutation/adversarial mindset (attack the coverage, not the code). "C+" / "three oracles" are just
local labels for this combination, not a new discipline.

## When to apply it (and when NOT to)

- **YES — only hard contracts:** parsers/serializers, computational functions, validators, data
  transformations, protocols. This is "Option 3: Classic TDD" from the Testing philosophy section
  of the regimen entry file.
- **NO — live product domains:** there the spec drifts as you go; a frozen test locks in a stale
  expectation (the code gets bent to fit a broken test). For those — the regular Test-along/BDD
  pipeline.

Not sure whether the contract is hard → ask the user, don't apply C+ by default.

## Why this delivers quality (not "the same thing without the effort")

The manual pipeline (qa-uat + reviewer) already catches a lot. C+ adds **three independent
oracles** that the regular cycle doesn't have:

1. **Independent test-author ≠ implementer.** The contract tests are written by someone OTHER than
   the implementer — a separate invocation (a developer instance/qa-e2e) with clean context. The
   implementer receives the RED tests as a given. This removes the blind spot of "coded it and
   wrote themselves a convenient test."
2. **Adversarial test-review.** Before implementation — a red lens on the tests THEMSELVES: "what do
   these tests NOT catch?" (boundaries, negative cases, failure modes). The coverage is attacked,
   not the code. Performed by reviewer or the red-team role applied to the tests (on Claude Code —
   a subagent; on another runtime — a prose run of the role).
3. **Codex contract cross-check** on high-stakes work — a second, independent model validates the
   spec/contract (the command is canonically in [second-model.md](second-model.md) §How to call it;
   if unavailable — the fallback is reinforced self-critique with a flag).

## The cycle

1. **Spec-as-contract.** SA/architect bring `docs/specs/<feature>.md` to a verifiable contract:
   input/output, invariants, boundary cases, failure modes — unambiguously, with no "and so on."
2. **RED — the independent author.** A separate invocation writes failing tests strictly to the
   contract. The tests must fail for the right reason (not a compile error).
3. **Adversarial test-review.** "What does the contract/tests miss?" Gaps found → add more tests
   (go back to step 2) BEFORE the code. On high-stakes work — the codex contract cross-check happens
   right here.
4. **GREEN — the implementer.** developer drives it to green. **Doesn't edit the RED tests** to make
   it "go green" (see below). The code changes, not the contract test.
5. **Exit.** The constitution exit ([constitution.md](constitution.md)) + per-task human-commit, as
   usual.

## Guardrails (otherwise the cycle backfires)

- **Don't edit the RED test to make it green.** A wrong test is a contract defect: go back to step 1
  (the spec) and reconcile it, rather than bending the test to the code or the code to a broken
  test.
- **The three-attempt rule** ([debugging.md](debugging.md)): doesn't converge in 3 substantive
  attempts → stop, escalate (an architectural blocker — to architect; a bug — to debugger), don't
  spin the loop blind.
- **Small diff.** If driving to GREEN balloons the diff — that's a signal the task is bigger than
  the contract: stop, send it back for decomposition (architect), rather than piling on.

## Stop conditions (from ADR-002)

- Apply C+ to 2-3 real features and measure: does **adversarial test-review** catch classes of
  defects beyond qa-uat+reviewer. Doesn't catch any in 3 starts → roll back C+ (the method didn't
  pay for itself). **For the measurement to be a fact, not intuition** — keep an opt-in catch log at
  `docs/PROCESS-METRICS.md` (template — `examples/docs/PROCESS-METRICS.example.md`): one line per
  caught defect + a verdict against STOP-3.
- The executable layer (a workflow/orchestrator) — do NOT build it until the pain threshold is
  named and reached (ADR-002, STOP-1/2).
