<!-- CODEX-DELTA-HEADER — the generator inserts this block between the title and the shared entry body (ENTRY-BODY of the shared template) when assembling AGENTS.md. NOT the full entry file; the full body (Stack, Commands, Required reading, Situational, Testing) is shared and comes from the body. -->

> **This is `AGENTS.md` — the regimen entry file on the Codex runtime.** Codex auto-reads `AGENTS.md` at
> the start of a session (the analog of Claude Code's auto-read of `CLAUDE.md`). Below is the **shared
> body of the regimen** (project specifics + routers into the neutral methodological core `core/`); this
> header block above records only what **differs** on Codex from Claude Code. The body of
> methods/roles is not duplicated — it lives in `core/`/`roles/`.

## What differs on Codex vs. Claude Code (harness delta)

- **No slash commands.** `/role`, `/panel`, `/kickoff` below are a Claude Code primitive. On Codex the
  numeric grammar `R D T` remains a **printed convention**: you type "5 3 24" as text, and Codex enters
  the role by reading `.codex/agents/<agent>.toml` + the canonical `roles/<role>.md`. A deliberate prose
  degradation (the guarantee matrix records it), not a loss of method.
- **Roles are custom Codex agents** `.codex/agents/<name>.toml` (`sandbox_mode` + a
  `developer_instructions` pointer into `roles/*`). The `R → role` map is in the body below ("Role
  map"); the file `.codex/agents/<agent>.toml` is that role's sandbox profile. Tool-scoping → by sandbox
  tier: read-only (reviewer/auditor) and workspace-write (developer/qa-e2e/debugger/devops) —
  **hardware**; docs-only (ba/qa-uat/sa/architect) and scratchpad-only (red/blue/arbiter) — **prose**
  (`workspace-write` + honor; G2 RED: a per-path carve-out is unreachable on Codex, cwd is always writable).
- **Skills — `.codex/skills/<name>/SKILL.md`** (format identical to Claude Code; body — a pointer into `core/*.md`).
- **Hook gates = accountability.** KL-7 (live `codex exec`): hooks from config do not fire in headless
  mode → for a hard gate on Codex use local git hooks (pre-commit for per-commit checks like
  LOC/no-todo; the ADR-017 slice-close composite runs only at slice boundaries — orchestrator or a
  local pre-push, no hosted CI is shipped), not runtime hooks. Opt-in example —
  `.codex/hooks.json.example`.
- **Memory** — Codex has its own mechanism (`AGENTS.md` hierarchy + Codex memories opt-in), not the
  Claude-Code `CLAUDE.md` hierarchy; the memory discipline (`core/memory.md`) carries over as-is.
- **Second model for the panel** (`core/adversarial-panel.md`): on the Codex runtime you yourself are
  Codex, so for the second pair of eyes use a **different** model (Claude/another profile), not
  yourself. No second model → honest fallback.

<!-- This file is a fragment that the generator inserts into AGENTS.md at the project ROOT; links in it
     are relative to the project root (e.g. `core/portability.md`), not to the overlays/codex/ directory.
     The package's link checks (selftest/regimen-doctor) skip this file via the CODEX-DELTA-HEADER marker
     on the first line (_pack_lib.dangling): in the materialized AGENTS.md the links resolve.
     Do NOT change `../../`. -->
Full "role × runtime × hardware/prose" matrix — [core/portability.md](core/portability.md).

---
