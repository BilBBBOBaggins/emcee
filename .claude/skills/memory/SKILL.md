---
name: memory
description: Project memory architecture across sessions — native CLAUDE.md hierarchy and auto-memory, discipline (<200 lines/file, thin index + lazy topic files, tiered loading for quality), PreCompact checkpoint, pointers to routines/loop. Use when organizing project knowledge/notes, setting up memory, or when context is sprawling.
---

How the project remembers context across sessions. **Full version in the `core/memory.md` file** (from the project root): read it in full.

Briefly:

- Two native systems: **CLAUDE.md** (your rules/facts, in the repo) + **auto-memory** (`~/.claude/projects/<proj>/memory/`, Claude's own, outside git).
- Discipline **for the sake of reasoning quality, not economy**: <200 lines/file, thin index + lazy topic files, load only what's relevant, don't duplicate.
- Expensive-but-high-quality steps (second model in the panel, verification passes, multi-agent) are the default, not "budget permitting". Context discipline frees up room for reasoning, it doesn't cut depth.
- Optional: a PreCompact hook for a recovery checkpoint before compaction; routines (`/schedule`) and `/loop` for background/iterative work; a human gate on high-stakes items.
- **When NOT to:** not for a one-off note in chat — only when organizing knowledge BETWEEN sessions, setting up memory, or when context is sprawling.
