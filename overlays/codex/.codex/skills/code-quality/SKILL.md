---
name: code-quality
description: Code quality standards — SRP, a ban on God Objects, one-directional layers, a ban on TODO/commented-out code, naming, error handling, a security minimum, readability over "cleverness". Use when writing or reviewing code.
---

This project's code standards. **Full rules in `core/code-quality.md`** (from the project root): read it in full when writing/reviewing code. (Discovery on Codex — this SKILL.md in `.codex/skills/code-quality/`.)

In short:

- **SRP / no God Objects:** one class — one responsibility; "And" in a name and >10 public methods → split; crossing the LOC threshold → a signal: justify cohesion OR split (not the verdict itself); a confirmed God Object → split.
- **Layers are one-directional:** dependencies flow one way only, reverse imports are forbidden.
- **No TODO/FIXME and no commented-out code** — do it now or file a task; git remembers history.
- **Errors** are typed, never swallowed silently; no empty catch blocks.
- **Security minimum:** no secrets in code/logs; user input only through prepared statements / sanitization.
- **Readability > "cleverness":** simple and explicit beats clever; optimizations without a benchmark are forbidden.
- LOC limits and test rules are in `core/quality-gates.md`.
- **When NOT to:** not for debugging something broken (→ `debugging`) and not for choosing an architecture (→ architect/panel) — this is writing/review standards, not root-cause finding or a structural decision.
