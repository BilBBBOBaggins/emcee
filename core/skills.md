# Skills as routers — the authoring standard

A skill is a **thin router to canonical knowledge**, not a manual and not a copy of one. The
skill's job: given a relevant situation, wake up the right method (point at `core/*.md` /
`stack/*` / `architecture/*` / `domain/*`), not spell it out. A fat skill = a duplicate of the
source of truth + context clutter.

`origin: process-convention` — this is our skill design, not a runtime binding. The content and
template below are **harness-neutral**; the discovery mechanism (how the harness surfaces a skill)
is per-harness, see the end.

## What SKILL.md carries (the template)

- **Purpose** — what it encapsulates, one line.
- **When to use** — concrete triggers (in `description`, always visible to the agent).
- **When NOT to use** — where NOT to apply it and what not to confuse it with. This is
  **anti-misfire and anti-reinvention**: an explicit boundary keeps the skill from firing on the
  wrong thing or from having its method reinvented inline (debugging by gut feeling instead of
  `debugging`, a homemade check instead of `code-quality`).
- **Routing / decision-tree** — *only if* the skill leads to several procedures: a tree of
  "situation → specific reference." A skill that just points to one canonical file doesn't need a
  tree.
- **Key constraints** — the domain's load-bearing prohibitions, briefly.
- **Pointer** — a link to the canonical file (the source of truth), NOT a copy.

The body is short (~10-15 lines): enough to not go wrong even without opening the canon, but not a
retelling.

## Quality bar — when to create a skill at all

Create one only if at least one of these holds:
- the process is **frequent**;
- the cost of error is **high**;
- review comments on the topic **keep recurring**;
- the agent **consistently picks the wrong path** without a nudge;
- there's a **clear step order** that improves safety.

Do NOT create a skill for:
- one-off tasks;
- a vague, broad topic with no trigger;
- **policy prose with no operational steps** (that's a rule in `core/`/the constitution, not a
  skill);
- a domain overview with no procedure.

Not every recurring task needs a skill — only where there's clear value. An unnecessary skill
clutters discovery and competes for attention with the one that's actually needed.

## Triggers: good vs. bad

- **Good** (concrete, falsifiable): "a test is failing / there's a stack trace," "you're writing a
  parser with a hard contract," "context is growing before compaction."
- **Bad** (vague): "you're doing backend work," "you're working with code," "something about
  quality."

A bad trigger either never fires or always fires — both are useless.

## Discovery — per-harness (P4, ADR-010/011)

The content and template above are harness-neutral. HOW the harness surfaces a skill is
runtime-specific and lives in the overlay, not here:

- **Claude Code:** `skills/<name>/SKILL.md` + frontmatter (`name` + `description`); stack skills
  carry a `paths:` glob for path-scoped activation, with `description` as the fallback.
- **Other runtimes:** the equivalent in `overlays/<harness>/` (`origin: harness:<name>`).

There's one source of truth — the canonical file. Delete the discovery layer, and prose mode (the
"Situational" router in the regimen entry file) keeps working.
