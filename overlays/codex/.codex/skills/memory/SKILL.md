---
name: memory
description: Project memory architecture across sessions — the runtime's native instruction-file hierarchy and cross-session memory, discipline (<200 lines/file, a thin index + lazy topic files, tiered loading for quality), a pre-compaction checkpoint, pointers to routines/loop. Use when you're organizing project knowledge/notes, setting up memory, or the context is growing.
---

How the project remembers context across sessions. **Full version in `core/memory.md`** (from the project root): read it in full. (Discovery on Codex — this SKILL.md in `.codex/skills/memory/`.)

In short:

- Two memory systems: the **runtime instruction file** (your rules/facts, in the repo — on Codex this is `AGENTS.md`) + **cross-session runtime memory** (outside git).
- Discipline **for reasoning quality, not economy**: <200 lines/file, a thin index + lazy topic files, load only what's relevant, don't duplicate.
- Expensive-but-quality steps (a second model in the panel, verification passes, multi-agent) are the default, not "budget-gated". Context discipline frees up room for reasoning, it does not cut depth.
- Optional: a recovery checkpoint before context compaction; background/iterative work; a human gate on high-stakes items. The concrete hooks/commands for these are runtime-specific.
- **When NOT to:** not for a one-off note in chat — only when organizing knowledge BETWEEN sessions, setting up memory, or when the context is growing.
