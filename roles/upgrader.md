# Role: Upgrader (DORMANT — upgrading a stale regimen)

> **STATUS: dormant delegating regimen.** Not in `roles.json` (no digit, not in the numeric
> pipeline). Invoked ad hoc: "upgrade the regimen per `roles/upgrader.md`". This is a **delegation
> guide** (the way Day 0 delegates stack init), NOT a generator code feature: `new-project.py`
> deliberately has NO `--mode upgrade` — an owned merge engine + version manifest = a persisted
> versioned owned artifact, forbidden by [ADR-001](../docs/adr/001-scope-process-overlay.md)
> ([ADR-006](../docs/adr/006-regimen-upgrade.md)).
> The upgrade is done by an **agent**, working it out from the git diff; a human reviews and commits.

Applies when the emcee regimen has already been installed from an **older version** and has fallen
behind (the overlay does NOT update it — it doesn't overwrite existing files). The goal is to bring
package-owned parts up to date **without touching** user content.

## Load-bearing principle: report-first, auto only on clean files, a human commits

1. **Candidate base (not an exact 3-way base).** Generate a fresh regimen into a temporary directory
   with the same options the operator confirms (stack/testing/wiring/arch/domain — take from the
   current regimen entry file and file set, **confirm with the operator**, don't guess). This is a
   reconstruction, not preserved provenance — so on disputed option-dependent files do NOT auto-apply.
   ```bash
   ./new-project.py --name "<name>" --dir /tmp/regimen-new --mode new \
       --backend <stack> --testing <as before> --wiring yes
   ```
2. **Classify by FILE** (the owned/user boundary is computable per file, not per line):
   - **clean package-owned** — files WITHOUT user `{{...}}` and without project content: clean
     `core/*.md` (those without `{{`), `sync-roles.py`, `regimen-doctor.py` + executable wiring (on
     Claude Code — `.claude/agents/*`, `.claude/commands/*`, `.claude/hooks/*`, generic
     `.claude/skills/*`; on Codex — `AGENTS.md`, `.codex/agents/*`, `.codex/skills/*`;
     `origin: harness:<name>`). These can be auto-updated.
   - **mixed / user-owned** — the regimen entry file (`CLAUDE.md`/`AGENTS.md`), `roles.json`, `docs/`,
     `core/*.md` WITH `{{...}}` (filled in by the user), `roles/*.md` with filled-in `{{...}}`
     (especially `qa-e2e`, `qa-uat`). **Do NOT auto-touch.**
   - `render-handbook.py` — package-only, NOT copied into the project by the generator → it doesn't
     exist in the project, not part of the upgrade set.
3. **REPORT-FIRST (mandatory).** Before any edits — a report:
   - what has drifted: `git diff` / `diff` between `/tmp/regimen-new/<file>` and the current one, for
     package-owned files;
   - which **new** files have appeared (e.g. `core/second-model.md`, `roles/designer.md`,
     `roles/auditor.md`, `roles/upgrader.md`);
   - **ADR delta** — which `docs/adr/` exist in the new package that didn't exist before: every ADR
     explains WHAT and WHY changed in the regimen (read them, not just the diff).
4. **Auto-apply — only to clean package-owned files** (a write into the working tree). Bring in new
   files. **Never auto-3-way-merge mixed files** — a syntactically clean but semantically
   contradictory merge produces no conflict and passes silently (regimen-doctor doesn't check the
   meaning of the norm).
   **Project layout is law for wiring.** If package-owned parts live in the project at non-package
   paths (e.g. docs-nested: `docs/core/`, `docs/roles/`), auto-applied wiring files
   (`.claude/agents|commands|skills`, `.codex/*`) are NOT copied verbatim: every internal canonical
   path (`core/…`, `roles/…`, `architecture/…`) is rewritten to match the actual layout. The layout
   choice and the fact of rewriting must be recorded in the report. (2026-06 empirical evidence, a
   live upgrade: 13 subagents with package paths under a docs-nested layout = broken canonical paths,
   no gate caught it.)
5. **Mixed files — surgically, showing every diff.** Carry over NEW package content (e.g. new
   pointers in the regimen entry file → "Situational"), preserving all user fills and project content.
   Ambiguous → ask the operator (PR-NN-02). **"Existing ones untouched" is not an option:** "Do NOT
   auto-touch" in the classification means "don't overwrite automatically," not "skip." For EVERY
   mixed file, the report must record a verdict: "new package content: carried over / rejected by the
   operator / no delta." A silent skip = an under-upgrade that must be recorded (the same logic as
   QG-NN-04: lag doesn't disappear just because the file wasn't touched; empirical evidence from the
   same 2026-06 upgrade — 5 roles stayed generations behind next to a freshly upgraded core).
6. **Resync and check:** `python3 sync-roles.py` → `python3 regimen-doctor.py` (🟢?) → `git diff`.
   **Resolution exit gate:** every `.md` path mentioned by the wiring exists in the project tree
   (regimen-doctor checks this mechanically — "wiring canonical paths resolve"); a broken path = the
   upgrade is **NOT done**.
7. **A human reviews the `git diff` and commits it themselves.** The agent changes the working tree
   only after report-first and **never commits** (constitution). A separate "regimen upgrade" commit
   — so the diff is visible in history.

## Forbidden

- Do NOT auto-overwrite files with user `{{...}}` or project content.
- Do NOT build an owned merge engine/manifest into the generator (⊥ ADR-001) — the upgrade = agent-driven analysis.
- Do NOT commit on the user's behalf; an ambiguous merge → stop, ask the operator.

## For those who want tooling

This isn't required. Anyone who wants a formal template-update can run their project under
[copier](https://copier.readthedocs.io/) / [cruft](https://cruft.github.io/cruft/) on their own — the
package doesn't require this and doesn't depend on them (early overlay projects have no provenance
file, retrofitting one is the very migration we're avoiding).
