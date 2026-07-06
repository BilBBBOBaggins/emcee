# Rust — stack rules

Stack-specific rules for Rust code. General principles live in [core/](../core/); day commands — in
the regimen entry file (§"Build and tests"); this file is the canonical stack slot, duplicating
commands with the entry file is allowed.

> Provenance: distilled 2026-07 from a production Rust workspace (event-ticketing, money-grade
> domain) built under this regimen. Field-tested defaults are named as such — swap them for the
> project's own choices and keep this file current when practices evolve.

## Version and tools

- Rust **stable**; decide explicitly whether to pin the toolchain (`rust-toolchain.toml`) or track
  stable in CI (e.g. `dtolnay/rust-toolchain@stable`) — record the choice here.
- `edition` set once at `[workspace.package]` in the root `Cargo.toml`.
- `Cargo.lock` is committed for a workspace that ships binaries/deliverables (NOT for a crates.io
  library).
- The root `Cargo.toml` is the single source of truth: `resolver = "2"`, members `crates/*`;
  standalone bench/experiment crates stay OUT of the workspace so CI doesn't build them.
- **License gate (HARD):** every new dependency — only `{{allowed licenses, e.g. MIT / Apache-2.0}}`;
  enforced by `cargo deny check licenses`, composition and justifications live in `deny.toml`.
  Exceptions — only as an explicit `deny.toml` entry with a reason. Same file: `wildcards = "deny"`,
  `yanked = "deny"`, sources — crates.io only.
- `cargo-deny` is mandatory locally: `cargo install cargo-deny --locked` (without it the check
  script fails at step one).

## Project structure

Workspace layout (adapt names; the shape is the rule):

~~~
crates/
  {{project}}-core/    # domain core: domain types and invariants, NO I/O
  {{project}}-types/   # contract vocabulary: newtype ids, shared keys (no I/O, no domain logic)
  ctx-{{name}}/        # one crate per bounded context
  infra-{{name}}/      # infrastructure wrappers (DB pool, outbox, ...)
  {{project}}-bin/     # entry-point binary: wiring ONLY, no business logic
  test-util/           # dev-only test harness (dev-dependency only)
migrations/            # SQL migrations (see §Database)
bench/                 # standalone bench crates, outside the workspace
~~~

Boundary rules:

- Dependency direction is one-way ([core/code-quality.md](../core/code-quality.md) CQ-NN-02);
  reverse imports between context crates are forbidden.
- Read a foreign context's data ONLY through its published port (a trait or an inherent method of
  a published type), never by direct cross-schema SQL.
- If module ownership needs machine enforcement, keep a boundary registry + lint —
  [architecture/module-boundary-registry.md](../architecture/module-boundary-registry.md).
- The core/types crates carry no I/O; the binary carries no business logic (wiring only).
- `test-util` and other dev harness crates must never appear in `[dependencies]` of production
  crates (dev-dependencies only).

## Error handling

- **thiserror** — typed errors in every crate with fallible logic; `anyhow` is NOT used in the
  workspace — don't pull it in without an ADR: context boundaries are public contracts, they need
  typed errors, not an opaque box.
- One error type per infrastructure boundary (e.g. the DB wrapper crate owns the DB error type);
  new failure kinds extend it instead of spawning parallel types.
- `Result` propagates with context; silent swallowing (`let _ = fallible()`, `.ok()` with no
  handling) is forbidden.
- `unwrap()` / `expect()` are forbidden in production code except provable invariants — then
  `expect("why this is impossible")` with the reason. In tests and dev harnesses they're fine; a
  deliberate panic with a clear message as a harness contract is legal.
- Numeric/money code: no silent arithmetic — checked conversions at type boundaries
  (bigint/integer ↔ u64/i32 and friends); clippy `all = "warn"` exists precisely to not stay
  silent on potential loss/overflow.

## Concurrency / async

- Runtime — **tokio** (`rt-multi-thread`, `macros`) as the field-tested default; async code stays
  at the I/O boundary (infra crates, tests); the domain core is synchronous, no I/O.
- Connection pooling — pool per context/module under that module's DB role; pools are not shared
  across contexts (any sanctioned exception is recorded in the boundary registry, not implied).
- A transaction is NOT hidden behind a facade: a multi-step money-grade TX is composed explicitly,
  against a concrete type, in one transaction (in-tx entry points are deliberately inherent
  methods, not trait methods).
- Integration-test pattern: run the test body inside a `tokio::spawn` harness wrapper — the
  JoinHandle catches assert panics so temp-DB cleanup is guaranteed.

## Database (if applicable)

- Field-tested default: PostgreSQL via pure-Rust `tokio-postgres` + `deadpool-postgres`; if the
  project bans FFI drivers (libpq etc.), record that as an ADR-level invariant.
- Migrations — **refinery**: `migrations/V{n}__{name}.sql`, run transactionally and idempotently
  through the app's migration runner (history in `refinery_schema_history`). Manual `psql -f`
  against `migrations/` is forbidden — it bypasses the history.
- Queries — parameterized placeholders only; string-concatenating SQL with data is forbidden.
- Multi-tenancy (if present) — a `SET LOCAL` tenant GUC through the DB wrapper, not hand-rolled
  session SETs.
- Integration tests never touch the dev DB directly: a `with_temp_db`-style harness creates/drops
  uniquely-named temp databases (`DROP ... WITH (FORCE)`) and applies the real `migrations/`.

## Tests

Split by an environment marker (e.g. a `PGURL` env var), not by build features:

- **Unit** — no external dependencies, always run: `cargo test --workspace` without the marker.
  Real network/timers in unit tests are forbidden ([core/quality-gates.md](../core/quality-gates.md)).
- **Integration** — a live database via the env marker; without it they **skip loudly** (a printed
  skip, a deliberate solo floor) — a green run without the marker is INCOMPLETE. In CI the marker
  is always set (DB service container). A malformed marker (e.g. a DSN without a dbname) panics
  the harness rather than silently falling back.

~~~bash
cargo test --workspace                          # unit (integration tests skip)
PGURL={{dev DSN}} cargo test --workspace        # full run
cargo test -p {{crate}} <test_name>             # fast run of one test
~~~

Coverage report — **gap diagnostics** (which files/critical paths have no tests), NOT a target
percentage and NOT a task exit gate ([core/quality-gates.md](../core/quality-gates.md),
`roles/qa-e2e.md` §Coverage diagnostics). Field default: `cargo llvm-cov`
(`cargo +stable install cargo-llvm-cov --locked`, dev-only tool):

~~~bash
PGURL={{dev DSN}} cargo llvm-cov --workspace --html   # artifact: target/llvm-cov/html/index.html
# run WITH the integration marker, otherwise integration paths drop out of the map
~~~

## Logging

- Structured logging: `tracing` + `tracing-subscriber` as the default candidate (passes a
  MIT/Apache license gate); record the project's actual choice here at the first runtime-binary
  task.
- No secrets/PII in logs — PII fields only as `[REDACTED]`. `println!`/`eprintln!` in production
  code is not logging (fine in dev harnesses and tests).

## Clean build — MANDATORY

The concretization of the "no warnings" rule from
[core/quality-gates.md](../core/quality-gates.md) (QG-NN-02) for Rust. Keep the same set in a
`ci/check.sh`-style script, CI, and an optional pre-push hook so all three run one canon. "Clean" =
all commands green:

~~~bash
cargo fmt --all --check                                # 0 unformatted files
cargo clippy --workspace --all-targets -- -D warnings  # compile + lint, warnings = errors
cargo test --workspace                                 # tests green (full run — with the env marker)
cargo deny check licenses                              # license gate
~~~

Any of: a compile error, a rustc/clippy warning, an unformatted file, a red test, a forbidden
license in the dependency tree = the task is not done. Suppression (`#[allow(...)]`,
`#[expect(...)]`) — only point-scoped and with the reason in a comment right next to it (pattern:
`#[allow(clippy::new_without_default)] // Default would create a UUID implicitly`).

## Static-adjunct QG-NN-05 (optional, warn-track)

A cheap complement to the assembled test ([core/quality-gates.md](../core/quality-gates.md)
§Assembled reachability — a complement, NOT a replacement):

~~~bash
cargo +nightly udeps --workspace     # unused dependencies (whole-crate "zero prod calls")
# within-crate dead code is already covered by rustc's dead_code lint in the clean build;
# for a cross-crate unused PUBLIC port, grep production call sites of the exported trait/type
~~~

## Linting

- **clippy** — the mandatory linter: `[workspace.lints.clippy] all = "warn"` in the root
  `Cargo.toml`, inherited per-crate via `[lints] workspace = true`, plus `-D warnings` in the gate
  command ⇒ any clippy finding = a red build.
- **rustfmt** — default config unless the project records its own `rustfmt.toml`; checked with
  `--check` in the gate.
- **cargo-deny** — licenses/duplicates/yanked/sources, config in `deny.toml`.
- LOC thresholds — QG-NN-03 ([core/quality-gates.md](../core/quality-gates.md)): for `.rs` apply
  the code column (business logic 500, bridge/adapter 700, parser 800) as a stretch signal, not a
  verdict. The optional `.claude/hooks/check-loc.sh` scans `.rs`.

## Specific prohibitions

- `unsafe` — forbidden without an ADR.
- A dependency with a license outside the allowed set — not "add and see": first an exception
  entry in `deny.toml` with a justification, otherwise the gate is red.
- Direct SQL against a foreign module's schema — forbidden; boundary edits start at the boundary
  registry, not at the code.
- Manual `psql -f` over `migrations/` — forbidden (bypasses migration history).
- Git dependencies and unknown registries — `deny` in `deny.toml`; crates.io only.
- Wildcard versions (`*`) in manifests — `deny`.
- `panic!` as control flow in production code — forbidden (§Error handling); panics are
  contract-only, with a reason message.

## Rust-specific patterns

- **Newtype id discipline**: domain ids are newtype wrappers in the types crate, not bare
  `i64`/`Uuid`; conversions to DB types are checked, at the boundary.
- **A context boundary is a trait** (a published port); contexts see each other only through
  published ports — any concrete-type in-tx composition is a recorded, sanctioned exception.
- **Explicit side-value generation**: no constructors that implicitly create UUIDs/timestamps.
- **DI — explicit constructors and parameters**; no DI frameworks in the workspace, don't pull
  one in.
- **Provenance comments in manifests**: every new dependency in `Cargo.toml` carries a "why +
  license under the gate" line.
