# ADR-006: Upgrading a stale regimen — a delegating role, not a code engine

Date: 2026-06-27
Status: Accepted (implemented: delegating roles/upgrader.md, report-first)

> Decision reached by running the adversarial panel (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md).

The decision directly applies the decisive criterion from [ADR-001](001-scope-process-overlay.md): a delegating command — yes, a stored owned result — no.

## In short

Whoever adopted the package from an old version falls behind: `--mode overlay` doesn't
overwrite existing files, so a stale regimen doesn't update itself. The obvious solution —
`--mode upgrade` with auto-overwrite — was rejected: "package-owned vs. user-owned" doesn't split
cleanly by file (`core/*.md` and `roles/*.md` carry your filled-in `{{placeholders}}`), and an
owned merge engine is exactly the version debt that ADR-001 forbids. Instead of an engine —
a **dormant `upgrader` role**: an agent updates the regimen from a git diff, report-first,
auto-applies edits only to clean files, and a human reviews and commits.

## Context

Whoever adopted emcee from an old version falls behind: `new-project.py --mode overlay` doesn't
overwrite existing files, so a stale regimen doesn't update itself. An upgrade path is needed. The
naive idea (`--mode upgrade` with auto-overwrite of package-owned files) ran into two facts:

1. **"package-owned vs. user-owned" doesn't split cleanly by file.** The files `core/*.md` and
   `roles/*.md` carry user-filled `{{placeholders}}` (in core: quality-gates, code-quality,
   principles, task-protocol; in roles: qa-e2e/qa-uat with 8 each, and others). A naive `cp -r
   core/*` would erase them.
2. **But the boundary is computable per file.** Part of `core/` ships without `{{` (that's pure
   package-owned), and the whole `.claude/agents|commands|hooks` tree is also without `{{`.

## Decision

**The upgrade is a delegating role, `roles/upgrader.md`** (the way Day 0 delegates init), **not
a generator code feature. Zero owned code.**

- **We don't build** `new-project.py --mode upgrade` with a manifest/hashes/3-way merge engine:
  that's a stored, versioned, owned result + its migrations — exactly what ADR-001 forbids (by the
  same test that killed the app scaffold). We also don't build a dependency on copier/cruft: early
  overlay projects have no provenance file, and retrofitting one is the same migration.
- **`roles/upgrader.md` (dormant, ad-hoc):** the agent updates the regimen itself, under this
  contract:
  - **a candidate baseline from git:** a fresh regimen is generated into a temp directory with the
    same options (confirmed with the operator, not guessed) — this is a reconstruction, not stored
    provenance; on files that depend on contested options, auto-apply is not allowed;
  - **classification per file:** clean package-owned (no `{{`) → can be automatic;
    mixed/user (`CLAUDE.md`, `roles.json`, `docs/`, files with filled-in `{{}}`) → automation
    leaves them alone;
  - **report-first is mandatory:** show the drift (`git diff`) + new files + the ADR delta
    **before** any edits;
  - **automatic only on clean files** (a write to the working tree); **never auto 3-way merge on
    mixed files** (a clean-but-wrong merge would pass silently, and regimen-doctor doesn't check
    the meaning of the norm);
  - **the human reviews the `git diff` and commits themselves** (the agent doesn't commit).

**Fixed immediately and independently** (bugs found by the panel):

- **`QUICKSTART.md`, track A2:** the `cp -r core/*` instruction erased filled-in `{{}}`. Rewritten
  into a safe recipe (automatic only on clean files, mixed files via git diff) + a pointer to
  upgrader.
- **A latent doctor bug at the source.** Generic references `stack/{{stack}}.md` / `{{stack-file}}`
  / `{{layers}}` were caught by `regimen-doctor` as unfilled → the project could never turn green.
  Fixed by **notation**, not a code allowlist (an allowlist isn't tied to a path and is therefore
  unsafe): generic meta-variables were converted to `<stack>` / `<stack-file>` (as already adopted
  for `<D>` / `<T>` / `<slug>`), and `{{layers}}` was replaced with a concrete example. Now
  `{{...}}` is exclusively a user-fill signal, and doctor is correct with no code changes.

## Consequences

**Pros:** the operator gets a working upgrade immediately (ad-hoc upgrader); zero owned code and
debt (the ADR-001/003 scope stays intact); two real bugs are fixed; `{{...}}` is once again a clean
user-fill signal → regimen-doctor can reach 🟢 on a filled-in project.

**Risks and open questions:**

- [ ] The candidate baseline may turn out inaccurate: reconstructing generation options from the
      current tree may diverge from the project's actual provenance. That's why, on files that
      depend on options, upgrader doesn't auto-apply edits and instead routes them to a manual
      merge. The residual risk is accepted (we don't build a version manifest for the sake of
      accuracy).
- [ ] The frequency of upgrade episodes is unknown: if upgrades turn out to be frequent and
      painful, revisit the decision (but it will still remain delegating, not an owned engine).

## Alternatives considered

- **`--mode upgrade` (owned merge + manifest).** Rejected: a stored, versioned, owned result
  contradicts ADR-001; a version manifest + hashes are not enough for a 3-way merge (a full
  answer-context is needed — effectively a fresh `.copier-answers.yml`); auto 3-way merging on the
  regimen produces clean-but-wrong results silently.
- **A copier/cruft dependency.** Rejected: retrofitting provenance onto early projects is the same
  migration; excessive for solo use. Mentioned in `roles/upgrader.md` as an option for those who
  want their own tooling.
- **An `{{stack}}` allowlist in regimen-doctor.** Rejected in favor of the `<stack>` notation: a
  token allowlist isn't tied to a path, so it could hide a genuinely unfilled `{{}}` in `docs/` or
  `CLAUDE.md`.
