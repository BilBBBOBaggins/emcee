---
name: code-quality
description: Code quality standards — SRP, no God Objects, unidirectional layers, no TODOs/commented-out code, naming, error handling, security minimum, readability over "cleverness". Use when writing or reviewing code.
---

This project's code standards. **Full rules in the `core/code-quality.md` file** (from the project root): read it in full when writing/reviewing code.

Briefly:

- **SRP / no God Objects:** one class — one responsibility; "And" in a name and >10 public methods → split; crossed the LOC threshold → a signal: justify cohesion OR split (not a verdict by itself); a confirmed God Object → split.
- **Layers are unidirectional:** dependencies go one way only, reverse imports are forbidden.
- **No TODO/FIXME and no commented-out code** — do it now or file a task; git remembers the history.
- **Errors** are typed, never swallowed silently; no empty catches.
- **Security minimum:** no secrets in code/logs; user input only via prepared statements / sanitization.
- **Readability > "cleverness":** simple and explicit beats clever; optimizations without a benchmark are forbidden.
- LOC limits and test rules — in `core/quality-gates.md`.
- **When NOT to:** not for debugging something broken (→ `debugging`) and not for choosing architecture (→ architect/`/panel`) — these are writing/review standards, not root-cause search or a structural decision.
