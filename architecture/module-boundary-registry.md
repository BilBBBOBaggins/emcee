# Module Boundary Registry — architectural pattern

A machine-checked registry of module ownership for a modular monolith: one declarative file at the
repo root states who owns what and who may read what, and a **boundary lint** (running as an
ordinary test) reddens the build when the code drifts from the declaration. Architecture-as-code:
the boundaries the compiler can't see become a mechanical gate instead of a review convention.

> Provenance: distilled 2026-07 from a production Rust workspace where the registry
> (`boundary-register.toml`) + a lint crate running inside `cargo test` held context-crate
> boundaries that rustc alone cannot express. The pattern is stack-neutral: any language where a
> test can read the repo tree and the dependency manifest can implement it.

## Problem

[modular-monolith.md](modular-monolith.md) prescribes one-way dependencies and per-module data
ownership (CQ-NN-02 in [core/code-quality.md](../core/code-quality.md)), but in most stacks
nothing ENFORCES them: the compiler happily links a backward import, and nothing stops module A
from writing SQL against module B's tables. Drift arrives through a series of small edits — each
locally reasonable, none reviewed as an architecture change (exactly the cross-task drift class
the auditor role exists for). A registry + lint turns that drift into a red build the day it
happens.

## The registry

One committed file at the repo root (TOML/YAML/JSON — whatever the lint reads comfortably), one
entry per module:

~~~toml
[modules.orders]
owns_schemas   = ["orders"]           # data this module owns (schemas/tables/dirs)
reads_schemas  = ["catalog"]          # foreign data it may READ — via the owner's published port
exports_traits = ["OrderPort"]        # the module's published ports (its public contract)
db_role        = "orders_rw"          # per-module DB role, if the stack has one
status         = "active"             # active | planned | frozen — kept honest by the lint
~~~

Rules of the file:

- **Edits to boundaries start HERE, not in code.** A new cross-module read is first a registry
  diff (reviewable as an architecture change), then code.
- **Sanctioned exceptions live here too**, named and commented (e.g. two modules that must commit
  in one transaction sharing one DB role) — an exception in the registry is a decision; the same
  thing appearing only in code is drift.

## The lint

A static check that runs as a normal test inside the standard test command (no new CI step, no
new tool to forget). It reddens on:

1. **Backward dependencies**: module A depends on module B outside the direction the registry
   allows (read from the dependency manifest — workspace members, package.json workspaces, Go
   module graph...).
2. **Foreign-resource literals in source**: a schema/table/path literal that belongs to another
   module appearing in this module's `src/` (a grep-class scan; test dirs and dev-only modules
   are out of scope).
3. **Status drift**: the registry says a module exists/is frozen and the tree disagrees — the
   registry itself is kept honest, not decorative.

Keep the lint dumb and fast: string/graph checks against the declaration. It complements — not
replaces — the assembled-reachability gate (QG-NN-05) and review; its job is only "the code still
matches the declared boundaries."

## When to apply

- A modular monolith with ≥3 modules and shared storage, where module boundaries are a load-bearing
  design decision (bounded contexts, per-module schemas).
- Teams/agent pipelines with many small independent edits — the drift profile the registry catches.

## When NOT to apply

- 1–2 modules, or boundaries that are still churning daily (kickoff phase): the registry would
  change with every task and teach the habit of editing it mechanically. Introduce it when the
  module map stabilizes (typically at the first multi-module slice).
- A stack where the compiler/module system already enforces the same rules natively (e.g. strict
  visibility + separate packages with enforced import rules) — then the registry duplicates the
  language.

## Consequences

**Pros:** boundary drift becomes a red test instead of an audit finding months later; boundary
changes become reviewable diffs of one declarative file; the registry doubles as the module map
for onboarding and for the auditor.

**Cons:** one more file to keep honest (mitigated by the status-drift check); literal-scan rules
need per-stack tuning (false positives in generated code — scope the scan); the lint itself is
code the project owns.
