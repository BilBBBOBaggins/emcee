# overlays/ — runtime enforcement overlays

This package is designed around a **neutral methodological core** (`core/`, `roles/`, `stack/`,
`architecture/`, `domain/` — byte-identical across all runtimes) plus **thin overlays** that
reproduce the enforcement layer for a specific runtime (agents, commands, hooks, skill wiring +
per-harness entry file). See [ADR-010](../docs/adr/010-multimodel-core-overlays.md),
[ADR-011](../docs/adr/011-process-layer-and-multimodel-build.md), [ADR-012](../docs/adr/012-entry-file-per-harness.md).

**The regimen entry file is a per-harness native file (ADR-012):** `CLAUDE.md` (Claude Code) / `AGENTS.md`
(Codex), one per project. It carries project specifics (stack, routers, testing) + an honest harness-delta,
and points into `core/`. The shared **body** of the entry file is single-sourced (`ENTRY-BODY` markers in
`CLAUDE.md`); the generator renders it under the native name per harness (on Codex: `_agents-header.md` +
body). **A Codex project does NOT get a `CLAUDE.md` file.** The former invariant "overlay = plumbing
only, `CLAUDE.md` = shared core" is superseded by ADR-012: the shared core = `core/` (the method), the
entry file is per-harness.

## Documented mapping: `.claude/` ≡ conceptual `overlays/claude-code/`

**Claude Code is the default runtime, and its overlay stays in its native position `.claude/` at the
package root, NOT in `overlays/claude-code/`.** This is a deliberate decision (verdict of the adversarial
panel `p4form`, [ADR-011](../docs/adr/011-process-layer-and-multimodel-build.md) §C):

- The Claude Code runtime scans `.claude/` **at the project root** — that is its native, required path.
- The generator places the Claude wiring into `target/.claude/` regardless of the source position anyway
  (source↔target asymmetry is inherent to any generator), so moving the source into
  `overlays/claude-code/` **buys no system consistency** — only package layout cosmetics, at the cost of
  a 16-file churn, symlink fragility (Windows `core.symlinks=false`), and a broken self-host.
- The equivalence is recorded **by this documentation paragraph**, not by a layout move (the "C + mapping" form).

**How to read the layout:**

| Path | What it is | Position |
|---|---|---|
| `.claude/` | Overlay of the **Claude Code** runtime (default) | Native position at the root (= conceptual `overlays/claude-code/`) |
| `overlays/<harness>/` | Overlay of a **non-default** runtime whose native position is NOT the root | e.g. `overlays/codex/` |

`overlays/` is created **only for non-default runtimes**. Today it holds [`codex/`](codex/).

**Stop condition (move-later, do NOT act without all three conditions met):** the physical move
`.claude/ → overlays/claude-code/` is reopened ONLY when (a) `overlays/codex/` is actually built
and stable, (b) `sync-roles.py` has become an N-runtime emitter, (c) the cloning invariant is confirmed
(macOS only → symlink is fine; otherwise a documented `core.symlinks` fallback). Until all
three are met — do not move it (see [p4form-arbiter](../docs/evidence/p4form-arbiter.md)).

## How the generator selects the overlay

`new-project.py --harness claude-code|codex` (default `claude-code`) — **static copy of the
git tree**, with no parsing of `origin:` labels and no manifest (stop condition [ADR-009](../docs/adr/009-portability-boundary.md)):

- `--harness claude-code` → neutral core + entry file `CLAUDE.md` (body as-is) + `.claude/` (as before; no regression).
- `--harness codex` → neutral core + entry file `AGENTS.md` (assembled: codex-delta header + shared body,
  ADR-012; **without `CLAUDE.md`**) + `.codex/` wiring.

The neutral core (`core/roles/stack/architecture/domain`, `roles.json`, `sync-roles.py`,
`regimen-doctor.py`) is copied identically in both cases. **The entry file** is per-harness (see above), but
from **a single shared body**, so an edit to the body is reflected in both entry files with no drift.
