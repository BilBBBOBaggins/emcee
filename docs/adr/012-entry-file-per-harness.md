# ADR-012: Regimen entry — thin per-harness native file + neutral methodological core (codex without CLAUDE.md)

Date: 2026-06-29
Status: Accepted

> Decision made via an adversarial panel run (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md).

Clarifies/corrects P4 from [ADR-011](011-process-layer-and-multimodel-build.md); does not affect the position of `.claude/` in the package.

## In short

The generated **Codex project contains a `CLAUDE.md` file** at its root plus 69 mentions of `CLAUDE.md`, while `AGENTS.md` says "read CLAUDE.md, ignore the name" — a Codex user with no Claude gets confused. Root cause: **the entry file name `CLAUDE.md` is a harness-ism that P3 missed**. The earlier design (AGENTS.md → pointer to CLAUDE.md, with CLAUDE.md living in the Codex project) rested on the **wrong** rationale that "extracting content = a second source of truth."

Decision: the entry = **a thin per-harness native file** (`CLAUDE.md` for Claude Code / `AGENTS.md` for Codex, one per project), carrying project specifics + an honest harness delta and pointing to the **neutral methodological core `core/`** (already neutral). **The Codex project does not get a `CLAUDE.md`.** A separate `REGIMEN.md` is NOT introduced (redundant — the payload is already `core/`).

## Context

P4 (ADR-011) built the codex overlay. A "did we break anything" check exposed a user-experience defect: the codex project carries a `CLAUDE.md` file and is permeated with Claude entry-file naming. The panel established:

- **The entry name `CLAUDE.md` is a harness-ism** (tied to a specific runtime). P3 neutralized plan-mode/`/rewind`/`.claude/`, but missed the entry file's name.
- **A literal "rename CLAUDE.md→AGENTS.md" (Option B) fails qualitatively:** the entry content is genuinely Claude-specific — `"this CLAUDE.md"`, the memory hierarchy, slash commands, the "Prompt for Claude Code" label. Under the name AGENTS.md, some lines would become **false** for Codex.
- **Some mentions are a Claude runtime FACT:** the memory hierarchy (`core/memory.md`), the matrix (`core/portability.md:92` "AGENTS→CLAUDE"). Neutralizing them would mean lying.
- **The earlier rationale is wrong** (it lived in the pre-reform codex entry — the `AGENTS.md`→`CLAUDE.md` pointer, which no longer exists in the package; see the fix below): one template → a native name is normal generation (the way `sync-roles` renders into two targets), NOT a second source of truth.

## Decision

**The entry is a per-harness native file; "thin" = it does not carry the body of methods/roles (that lives in `core/`), it carries project specifics (stack, routers, testing) + an honest harness delta.**

1. **The generator writes the entry to the native name WITH CONTENT** (not a pointer): claude-code → `CLAUDE.md`; codex → `AGENTS.md` carries the content. The Codex project does NOT get a `CLAUDE.md`.
2. **Two classes of `CLAUDE.md` mentions + an allowlist for labels** (different handling):
   - **(a) generic "entry file"** (routers, "read CLAUDE.md" in roles) → **neutralize** to "regimen entry file" (resolves to the native name per harness).
   - **(b) Claude runtime FACT** (memory hierarchy, matrix:92, native auto-read) → **leave explicit** as a Claude fact in the harness delta. Do not neutralize.
   - **(c) process-convention label** ("Prompt for Claude Code") → **leave as is** (canonical Claude flavor, ADR-011).
3. **`.codex/agents/*.toml` reference `AGENTS.md`**, not `CLAUDE.md`.
4. **New selftest invariant:** catch **bare prose** `CLAUDE.md` in codex output (not just markdown links — `neutralize_dead_links` skips those). Criterion: zero (a)/self-ref in the codex project; (b)-delta and (c)-label follow the allowlist.
5. **`selftest.py:214` is inverted:** the codex project must NOT have a **file** `CLAUDE.md` at its root.
6. **Remove the wrong "second source" rationale** from the pre-reform codex entry. Implemented by **deletion, not rewriting**: the `overlays/codex/AGENTS.md`→`CLAUDE.md` pointer was replaced by the delta header `overlays/codex/_agents-header.md`, which carries no such rationale at all (the package no longer has an `overlays/codex/AGENTS.md`; only the generator materializes the full `AGENTS.md` in the project).
7. **`REGIMEN.md` is NOT introduced** (the neutral payload is already `core/`; a third name = an extra hop, zero anti-drift gain).

## Consequences

**Upsides (quality):** the Codex user gets a clean project — a native `AGENTS.md`, no `CLAUDE.md` and no "read CLAUDE.md despite the name"; Claude facts honestly live in the per-harness delta, not masked; the `core/` payload is neutral by construction; one source per project, no drift.

**Overturns the invariant** "overlay = plumbing only, `CLAUDE.md` = shared core" (`overlays/README.md:5-6,47`): the entry is now per-harness native, and the shared core = `core/` (the method), not `CLAUDE.md`. The wrong "second source" rationale **was removed** along with the pre-reform `overlays/codex/AGENTS.md` pointer — its place was taken by the delta header `overlays/codex/_agents-header.md` (without that rationale).

**Implementation (executed and verified):**

- [x] Classify all 69 mentions of `CLAUDE.md` into classes (a/b/c). Reduced to 26 legitimate occurrences: (b)-facts for memory/portability plus neutralized (a) with an explicit per-harness note. No (b)-fact without a home in the harness delta was found.
- [x] Generator: writes the entry to the native name for each runtime; codex without `CLAUDE.md` (verified: the codex project carries `AGENTS.md` with content, no `CLAUDE.md` file).
- [x] Neutralized (a)-references; `.codex/agents/*.toml` → `AGENTS.md`; fixed the rationale; inverted the invariant in `selftest.py:214` plus an invariant for bare prose text (triage for (b)-homes).
- [x] After the fix: a codex project was generated — zero (a)/self-ref `CLAUDE.md`, zero dangling links, the doctor green.

## Alternatives considered

- **Option B (literally rename CLAUDE.md→AGENTS.md).** Rejected: the entry content is Claude-specific, a literal render would be a lie for Codex.
- **`REGIMEN.md` (a third neutral name for the payload).** Rejected: redundant — the neutral methodological payload is already `core/`; a third name is extra indirection, zero anti-drift gain.
- **The current pointer (CLAUDE.md in the codex project + AGENTS.md→CLAUDE.md).** Rejected: a user-experience defect (the Codex user gets confused) plus the "second source of truth" rationale is wrong.
- **Refined-B plus an allowlist without fixing the generator.** The allowlist is necessary, but without writing the entry to the native name it still leaves a `CLAUDE.md` file in the codex project — a half-measure that misses the goal.
