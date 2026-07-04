# ADR-010: Multi-model support — core + runtime git overlays, under two field gates

Date: 2026-06-28
Status: Accepted — the build was unblocked and carried out via [ADR-011](011-process-layer-and-multimodel-build.md)
(gate G1 was lifted early by a deliberate project decision; **G2 closed RED**: hardware-enforced docs-only on Codex
is unreachable, the tier degrades to prose/accountability — [g2-findings](../evidence/g2-findings.md); hooks in headless
`codex exec` don't fire — KL-7, same document; the Codex overlay was built accounting for both REDs). The wording in the
body below ("blocked by G1/G2 — build not started", "reproducible in hardware") is **historical**, as of the time of writing
2026-06-28, before the field runs; the current guarantee matrix is [core/portability.md](../../core/portability.md).

> Decision reached via an adversarial panel run (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md).

This is a **direct continuation of [ADR-009](009-portability-boundary.md)**: there the premise was
"one actual runtime" → swap machinery was killed; here the premise has changed (the operator intends
to actually run 2+ runtimes), which ADR-009 itself flagged as a trigger for a new panel.

## In short

The operator wants **full multi-model support** — not being locked into one model/runtime, but
actually working on Claude Code and Codex in parallel (the frontier-model market is alive, leadership
changes). The panel examined the architecture of "a shared **core** (method + role content) +
**overlays** that reproduce the enforcement layer for each runtime."

Verdict: **the structure is sound, there's no fatal defect — but it cannot be built yet.** The
decision rests on two facts that on the current data DO NOT exist, and both can only be learned from
the field, not from debate:

- **G1 — necessity is observed, not merely wished for.** "2+ runtimes" right now is intent, not an
  observation. The main risk (red team): two weeks of enthusiasm, then one default runtime, and the
  second overlay **rots, constraining every core change** — exactly the fate of the swap machine that
  was already killed. Gate: a 6-week necessity log with an un-gameable criterion.
- **G2 — docs-only on Codex is genuinely hardware-enforced.** The panel empirically proved (a live
  test of the codex binary) that Codex's permission profile gives per-path read/write at the OS
  sandbox level → docs-only roles (business analyst/QA/system analyst write docs, not code) are
  reproducible **in hardware**, not by degradation. But the exact TOML form of the profile hasn't been
  finalized — it's a 0.5-day test.

A key refinement from round 2: **if the necessity rests on "need a second model for
cross-checking" (cross-check), the operator doesn't need an overlay, he needs a second model — which
he already has via codex.** Overlays are justified only if the bottleneck is
**runtime-specific primitives/limits** (a capability block).

## Context

After [ADR-009](009-portability-boundary.md) (portability = a manual fork guided by a map, no
machinery), the operator formulated a stronger goal: not a one-time migration but **working in
parallel across multiple runtimes**. ADR-009 had already named this as a trigger for a new panel.

The decision is grounded in **an actual runtime capability map** (`runtime-capability-map.md`,
assembled with codex + direct doc fetches): the method (`core/`) ports over in prose without loss;
the enforcement layer (`.claude/`) is partially reproducible on Codex/Cursor. During the panel the map
was **refined empirically** — blue team, via a live test of the codex 0.138.0 binary, showed that the
docs-only tier on Codex is hardware-reproducible (permission profile, seatbelt/landlock enforcement),
disproving the initial assessment of a "gap." Only **one** guarantee remains unreproducible in
hardware — user-facing slash commands (`/role`, `/panel`), which on Codex degrade to the typed
convention `R D T`.

## Decision

**Split the package into an upstream model/runtime-agnostic CORE + independent per-runtime
git-tree enforcement OVERLAYS. v1 scope — Claude Code + Codex; Cursor deferred. Build only after G1
and G2 go green.**

Structure (adopted as the design; built after the gates):

- `core/` + `roles/*` (content) + `stack/architecture/domain` — **the shared core**, scrubbed of
  harness-isms (precondition P3).
- `overlays/claude-code/` (= today's `.claude/`), `overlays/codex/` (`.codex/agents/*.toml` with
  permission profiles, hooks, AGENTS.md wiring, skills) — **independent trees**; the generator
  statically copies the chosen one (`safe_copy_tree`, the `--wiring` class), **not** branching the
  tooling on `--runtime` and **without** a parsed manifest (otherwise a relapse of ADR-001/006 owned
  debt).
- `roles.json` — already the single source of truth; `sync-roles.py` is extended from Claude
  targets to **N runtime emitters** (P4). Skill generation, which today knows the Claude schema
  (`new-project.py:471`), is moved out into a runtime-specific emitter/overlay.
- **A per-runtime guarantee matrix** (mandatory): "role × runtime × guarantee (hardware-enforced /
  prose / absent)." Honestly shows where a harness is stronger, where weaker. Slash dispatch is the
  only cell that reads "prose on Codex."
- `regimen-doctor` reports **state, not presence** ("hooks active/trusted", not "file exists").

### Field gates — BEFORE any build (load-bearing preconditions)

**G1 — observed necessity (a 6-week window).** An append-only log, one line per task **going
forward** (not written retroactively): `date · task · runtime · why_tag · blocking_artifact`. The
`why_tag` is a closed list. "Necessary" = only `capability-block` (hit a missing primitive/hard limit,
with an artifact) or `cross-check` (the method required a second model, codex, with a written
breakdown). Everything else = "convenient," doesn't count.
- **GREEN (build):** ≥6 `capability-block` entries across ≥4 different weeks, both runtimes
  irreplaceable ≥1 time each. **`cross-check` does not count toward the build decision** (if the
  threshold rests on it — the need is for a second model (codex), not an overlay).
- **RED (revert to ADR-009):** ≤3, OR clustered in <4 weeks, OR one runtime was never
  irreplaceable. **AMBER (+3 weeks, once):** 4–5 with the spread and two-sidedness conditions met.
- Un-gameable: the tag is written forward (not a retroactive judgment); "necessary" requires an
  artifact, not an opinion; the weekly spread + two-sidedness + excluding `cross-check` close the
  loopholes; an unlogged task defaults to RED (laziness → a conservative revert, not a false green).

**G2 — docs-only on Codex is hardware-enforced (≤0.5 day).** Assemble a `docs-only.toml`
(write allowed only in `docs/`, deny in `src/`; the exact form of `FilesystemPermissionToml` — 1
test) + 3 write attacks against `src/` (`apply_patch`, raw shell, MCP). GREEN: all three are blocked.
RED: even one gets through → Codex docs-only is honor-system, roles degrade to prose (the matrix
records it, the decision isn't buried). In parallel — a hook-activation test.

### Sequence after G1+G2 go green

1. A grep sweep for `R D T`/Claude narrative across **the entire** future core (not just three
   files: also `roles/*`, `core/memory.md`, `core/principles.md`, `task-protocol.md`, `pipeline.md`,
   `stack/_TEMPLATE.md`, `architecture/agentic-workflows.md`), neutralize or move into an overlay
   (~1.5 days).
2. `overlays/codex/` + N `sync-roles.py` emitters, **enforced by a file count** in `selftest.py`
   (the threshold for debt becoming unmanageable).
3. The guarantee matrix + a doctor adapter.

## Consequences

**Upsides:** honest multi-model support with hardware guarantees wherever the runtime provides
them (read-only reviewer and docs-only — on both runtimes if G2 is green); owned debt is **justified
for the first time** (it buys real parallel work, not zero as in ADR-009); the structure doesn't
relapse into the parsed-manifest mistake (git trees, not a manifest); the guarantee matrix doesn't
hide degradation, it exposes it.

**Risks (consequences of the decision, not deferred decisions):**

- **Slash dispatch on Codex is a prose degradation**, not a hardware one. `R D T` stays a typed
  convention; the guarantee matrix records it. Accepted knowingly.
- **The debt of N overlays is material** (`.claude/` is already 25 files; the codex overlay = a
  second product). The backstop is the file count in `selftest.py`: if adding a role touches too
  many files × runtimes, the debt is judged unmanageable before it's built.
- **Hook activation ≠ presence**: the doctor must report state, otherwise a false sense of
  enforcement.

**Empirical verification (the only genuine TODOs — knowable from the field, not from debate):**

- [x] Gate G1: the 6-week necessity log. Green → build; red → revert to ADR-009, this structure
      isn't implemented. This is a gate decision, not deferred design: the design is adopted, the
      field decides whether to activate it. → **Outcome: lifted early** by a deliberate operator
      decision (ADR-011), without the full logging window.
- [x] Gate G2: a working `docs-only.toml` + 3 write attacks (≤0.5 day). Red →
      docs-only on Codex downgrades to prose (amends the matrix, doesn't bury it).
      → **Outcome: RED** — a write around the carve-out gets through, docs-only on Codex = prose
      ([g2-findings](../evidence/g2-findings.md)).
- [x] Codex hook-activation test (`Stop`/`PreCompact` actually fire). → **Outcome: RED (KL-7)** —
      in headless `codex exec` hooks don't fire; hook gates on Codex = accountability, hard
      enforcement → CI/pre-commit ([g2-findings](../evidence/g2-findings.md)).

## Alternatives considered

- **Build now, without field gates.** Rejected: "2+ runtimes" right now is intent, not
  observation; a premature build risks a dead overlay that rots and constrains the core (a blocking
  objection).
- **Hook-based docs enforcement on Codex** (a PreToolUse veto on writes outside `docs/`).
  Rejected as **a false guarantee**: a shell write leaks past the hook (Codex docs: PreToolUse isn't a
  complete boundary). Replaced with a permission profile (hardware-enforced).
- **`--runtime` branching in the generator/doctor/selftest + a parsed manifest.** Rejected: a
  relapse of owned debt ([ADR-001](001-scope-process-overlay.md)/[ADR-006](006-regimen-upgrade.md)).
  Chosen instead: copying independent git trees without interpretation.
- **Lowest common denominator** (drop unreproducible guarantees everywhere, including Claude, for
  a single unified harness). Rejected: sacrifices Claude's hardware guarantee for symmetry — a
  direct violation of the north star "quality over simplicity."
- **Separate forks with no shared core** (one fork per runtime). Rejected: duplicates the method,
  the core drifts out of sync; a shared upstream core + overlays is cheaper to maintain (conditional
  on G1).
- **Prose mode everywhere, no overlays.** A viable fallback (the method ports over in prose
  without loss), and it's what a red G1 reverts to. Not chosen as the goal: on Codex you lose the
  hardware read-only/docs-only guarantees and hooks that are **reproducible** there — a harness with
  an overlay is substantially stronger than bare prose (provided 2+ runtimes are genuinely needed).
- **Cursor in v1.** Rejected for now: docs-only is also binary there, slash degrades — add it as
  a separate increment after Claude+Codex.
