---
name: spec-driven
description: Contract-first cycle (C+) for tasks with a HARD contract — parsers, computations, validators, transformations, protocols. The test is written BEFORE the code, by an independent author; tests undergo an adversarial review pass. Use when the task = a hard contract with unambiguous input/output. NOT for live product domains.
---

The C+ method for hard contracts: it adds a **new angle of verification** (an oracle), not automation.
**Full version in `core/spec-driven.md`** (from the project root): read it in full if the task is contractual. (Discovery on Codex — this SKILL.md in `.codex/skills/spec-driven/`.)

In short:

- **When:** only hard contracts (parser/computation/validator/transformation = "Variant 3 TDD").
  NOT for live domains (the spec drifts → a frozen test would lock in a wrong expectation).
- **Three oracles:** (1) tests are written by an **independent author ≠ the implementer**; (2) an **adversarial test review**
  of "what the tests do NOT catch"; (3) a **codex contract check** on high-stakes tasks.
- **Cycle:** spec-as-contract → RED (independent) → adversarial review pass on the tests → GREEN (the implementer,
  **does not edit the RED test just to turn it green**) → constitution exit + per-task commit.
- **Safeguard:** a wrong test = a contract defect (escalate to the architect/user, don't just patch it); the three-attempt
  rule; a bloated diff → the task is bigger than the contract, decompose it.
- This is a methodology, not an executable layer; the manual `R D T` and human commit are preserved (ADR-002).
- **When NOT to:** only for a hard contract. A live product domain (spec drifts) → regular Test-along/BDD, not C+. Not sure — ask, don't apply it by default.
