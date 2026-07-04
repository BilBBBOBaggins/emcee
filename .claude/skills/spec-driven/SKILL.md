---
name: spec-driven
description: Contract-first cycle (C+) for tasks with a HARD contract — parsers, computations, validators, transformations, protocols. The test is written BEFORE the code, by an independent author, and the tests pass an adversarial review. Use when the task is a hard contract with an unambiguous input/output. NOT for live product domains.
---

The C+ method for hard contracts: it adds a **new verification angle** (an oracle), not automation.
**Full version in `core/spec-driven.md`** (from the project root): read it in full if the task is contract-shaped.

Briefly:

- **When:** only hard contracts (parser/computation/validator/transformation = "Variant 3 TDD").
  NOT for live domains (the spec drifts → a frozen test locks in a wrong expectation).
- **Three oracles:** (1) tests are written by an **independent author ≠ the implementer**; (2) an **adversarial test review**
  for "what the tests do NOT catch"; (3) a **codex contract check** on high-stakes items.
- **Cycle:** spec-as-contract → RED (independent) → adversarial test review → GREEN (implementer,
  **does not edit the RED test to make it pass**) → constitution exit + per-task commit.
- **Safeguard:** a broken test is a contract defect (goes to the architect/user, not adjusted to pass); the three-attempt rule;
  a bloated diff → the task is bigger than the contract, decompose it.
- This is a methodology, not an executable layer; manual `R D T` and human commits remain (ADR-002).
- **When NOT to:** only for hard contracts. A live product domain (spec drifts) → regular Test-along/BDD, not C+. Not sure — ask, don't apply by default.
