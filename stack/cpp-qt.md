# C++/Qt (CMake) — stack rules

Stack-specific rules for modern C++ (C++20/23) desktop applications on Qt 6 with CMake. General
principles live in [core/](../core/); this file is the canonical stack slot referenced by
[core/quality-gates.md](../core/quality-gates.md) and the roles.

> Provenance: distilled 2026-07 from a production Qt 6 desktop client (mail, multi-protocol) built
> under this regimen — including its autonomous-QA pilot. Field-tested defaults are named as such —
> swap for the project's own choices and keep this file current when practices evolve.

## Version and tools

- C++23 (`CMAKE_CXX_STANDARD 23`, `CMAKE_CXX_EXTENSIONS OFF`): concepts, ranges, `std::expected`,
  designated initializers. Drop to C++20 only for a recorded toolchain constraint.
- Qt 6 LTS ({{6.8+}}): the module set the project actually links ({{Core, Network, Qml, Quick,
  Test, ...}}).
- CMake 3.25+ — the ONLY build system; the root `CMakeLists.txt` is the single source of truth for
  dependencies.
- Dependencies: system packages (Qt, SQLite, OpenSSL, ...) + `FetchContent` **pinned to a tag**.
  There is no lock file in this stack — tag pins in `CMakeLists.txt` ARE the version fixation
  (the CMake-idiomatic substitute for `go.sum`/`Cargo.lock`); a moving branch/`master` pin is
  forbidden.
- `CMakePresets.json`: a `default` preset → `build/` with tests ON and
  `CMAKE_EXPORT_COMPILE_COMMANDS=ON` (clang-tidy/cppcheck feed off `compile_commands.json`).
- Secrets (OAuth creds etc.) enter at configure time from an uncommitted `.env` — never committed,
  never hardcoded.

**Gotcha (field find):** `FetchContent` materializes third-party source trees under
`build-*/_deps/` — exclude those from every `src/`-scoped scan: coverage filters, tidy
`HeaderFilterRegex`, repo-wide doc/link checkers (a vendored README once red-flagged the regimen
doctor), grep-based audits.

## Project structure

Three-tier with a bridge ([architecture/three-tier-with-bridge.md](../architecture/three-tier-with-bridge.md)):

~~~
src/core/     # business logic, protocols, storage. Links QtCore ONLY — no QML/Widgets
src/bridge/   # export to QML: QAbstractListModel, Q_PROPERTY, Q_INVOKABLE. Thin proxy layer
src/ui/       # QML: components/, views/, theme/
tests/        # dev tests: core/, bridge/, qml/, integration/ (+ e2e/, fuzz/ — separate tracks)
ci/           # pipeline, coverage, fuzzers, packaging
scripts/      # clang-tidy.sh, cppcheck.sh and helpers
~~~

- Layers are one-directional: `ui/ → bridge/ → core/` ([core/code-quality.md](../core/code-quality.md)
  CQ-NN-02). `core/` never includes from `bridge/`/`ui/`; business logic lives in neither
  `bridge/` nor QML.
- Each layer is its own static library target; namespaces mirror the layers
  (`{{project}}::core`, `{{project}}::bridge`). Files `PascalCase.h/.cpp`, `#pragma once`.
- LOC limits per code type — QG-NN-03 table in [core/quality-gates.md](../core/quality-gates.md);
  exceeded → split BEFORE merge (or a reasoned cohesion answer).

## Error handling

- `core/` returns errors via `std::expected<T, Error>` (a project-wide `Result<T>` alias), NOT
  exceptions across the layer boundary; the error carries context (what was attempted, with what).
- Silent swallowing is forbidden: an error is either propagated up or handled explicitly (retry,
  fallback, a signal to the UI).
- Network policy is explicit and centralized: connect/command timeouts, bounded retries with
  exponential backoff, auto-reconnect with re-auth — numbers recorded here per project, mocked in
  tests via setters (never real timers in unit tests).

## Concurrency

- All I/O and heavy work — in worker threads (`QThread`/`QThreadPool`); the main (GUI) thread is
  NEVER blocked.
- Results travel ONLY via Qt signals/slots (pattern: Command → queue → worker → emit).
- Bridge `Q_INVOKABLE` methods return `void`; the result arrives by signal; QML binds to
  `Q_PROPERTY` updated in a slot (the async-safe "void + signals" idiom).
- Races are caught by the TSan lane (§Build circuits); it MUST stay green after any threading
  change.

## Database (if applicable)

- Field default: SQLite via a single access layer in `core/` that also owns migrations.
- Parameterized queries are mandatory — no concatenating user input into SQL.
- A test touching a table with FKs inserts parent rows in `SetUp()`; scoped queries (per-account/
  per-folder filters) are asserted in ALL code paths including delete/reconcile/update.
- Secrets only through a keychain-backed secret-store interface (OS keychain, encrypted file
  fallback); plaintext passwords are never stored.

## Framework / runtime

- UI — QML (Qt Quick Controls 2), built with `qt_add_qml_module` (NOT `qt_add_resources`).
- All user-visible strings through `qsTr()`; colors/typography only through the theme object
  (a context property — `pragma Singleton` is forbidden).
- Every interactive element gets an `objectName`: QML tests (`findChild`) and autonomous UI
  scenarios ([architecture/autonomous-testing.md](../architecture/autonomous-testing.md)) hang off it.
- Replacing a hand-rolled protocol/transport layer with a generic library (or vice versa) — only
  through an ADR.

## Tests

GoogleTest/GMock (C++), Qt Quick Test (QML). Two tracks, never mixed
([core/quality-gates.md](../core/quality-gates.md) §Separation of Testing Tracks):

- **Dev tests** (developer, every task, `build/`): unit + integration + QML, fast, on mocks. No
  real network/timers — timeouts are mocked via setters.
- **E2E / assembled** (QA track, `build-qa/`): the built app against a real server.

Conventions:

- A class in `core/` → `tests/core/Test{ClassName}.cpp`; a new `.cpp` is registered in
  `tests/CMakeLists.txt`.
- QML changed → update `tst_*.qml`; a bridge model that affects QML → a QML-integration test.
- No tests = the task is not done (both C++ and QML).

Full run (the only canonical way):

~~~bash
cmake --build build -j$(nproc 2>/dev/null || sysctl -n hw.logicalcpu) \
  && cd build && ctest -j12 --verbose 2>&1 | tee /tmp/ctest_latest.log && cd ..
~~~

Always `--verbose` with `tee`: without a saved log a flaky failure (especially QML) is unreadable,
and a re-run clobbers `LastTest.log`. Targeted debugging — `ctest -R <suite> --verbose`; task
completion — full run only.

Coverage — **gap diagnostics, NOT a gate** ([core/quality-gates.md](../core/quality-gates.md),
`roles/qa-e2e.md` §Coverage diagnostics): a dedicated `build-cov/` with `--coverage` (gcov) +
lcov/genhtml, filtered to `src/` (and excluding `_deps/` — see the FetchContent gotcha). A high
percentage ≠ assembled reachability (QG-NN-05 is a separate gate).

## Build circuits

The load-bearing discipline of this stack: expensive checks live in DEDICATED build dirs as
**end-of-day/slice circuits**, not per-task gates. The dev cycle stays fast; the heavy lanes stay
green on a cadence.

| Directory | Configuration | Purpose | Cadence |
|---|---|---|---|
| `build/` | tests ON, compile_commands | dev cycle: build + all dev tests. **The QG-NN-02 slot** | every task |
| `build-qa/` | Release + test-driver/E2E ON, dev tests OFF | assembled/E2E track against a real backend | QA track |
| `build-cov/` | Debug + `--coverage` | coverage gap-map | on request |
| `build-tidy/` | Debug, compile_commands | clang-tidy base | end of day |
| `build-asan/` | `-fsanitize=address,undefined -fno-omit-frame-pointer` | ASan+UBSan lane | end of day |
| `build-tsan/` | `-fsanitize=thread` + a suppressions file for framework false positives | TSan lane | after threading changes + end of day |
| `build-fuzz/` | `-fsanitize=fuzzer-no-link,address,undefined` | libFuzzer harnesses for parsers/protocol inputs | on parser changes / nightly |
| `build-release/` | Release | packaging/pipeline | release |

A sanitizer/tidy lane that reds at end of day is a bug to fix next morning, not noise: the lanes
exist to catch what the per-task compiler gate structurally can't (races, UB, leaks).

## Logging

- `QLoggingCategory` behind a project logger header: per-subsystem categories
  (`{{project}}.net/storage/sync/ui/...`), `LOG_DEBUG/LOG_WARN/LOG_ERROR(Category, msg)` macros.
- Bare `qDebug()` without a category is forbidden in new code.
- No secrets/PII in logs: passwords, tokens, message bodies, addressees — redact to `[REDACTED]`.

## Clean build — MANDATORY

The concretization of the "no warnings" rule from
[core/quality-gates.md](../core/quality-gates.md) (QG-NN-02) for C++/Qt. **Reasoned stack
exception to the usual "linter in the per-task gate":** a full clang-tidy pass over a large C++
translation-unit set is too slow for every task, so the per-task gate is the COMPILER at maximum
strictness, and clang-tidy/sanitizers run as separate circuits (§Build circuits) — deliberately
NOT a silent weakening: the strictness lives in `-Werror`, the breadth lives in the circuits.

"No warnings" = one green command:

~~~bash
cmake --build build -j$(nproc 2>/dev/null || sysctl -n hw.logicalcpu)   # 0 errors, 0 warnings
~~~

Teeth by construction: first-party library targets compile with `-Wall -Wextra -Wpedantic -Werror`
(MSVC `/W4`) — a warning in `src/` IS a build error. Suppression (`#pragma`, a local `-Wno-*`) —
only with the reason in a comment right next to it; third-party warnings — isolate the include
(SYSTEM includes), don't relax your own flags.

## Static-adjunct QG-NN-05 (optional, warn-track)

C++ has no reliable cross-TU dead-export tool; the cheap "zero production calls" probe is:

~~~bash
grep -rn "<ExportedSymbol>" src/ --include="*.cpp" | grep -v test   # call-site grep
# plus misc-unused-* / -Wunused already active in the tidy circuit and compiler gate
~~~

## Linting

- **clang-tidy** — `.clang-tidy` at the repo root. Recommended baseline: `bugprone-*`,
  `clang-analyzer-*`, `concurrency-mt-unsafe`, `modernize-*`, `performance-*` + selected
  readability/cppcoreguidelines; `WarningsAsErrors` for the memory-safety subset
  (`bugprone-use-after-move`, `bugprone-dangling-handle`, `clang-analyzer-core.*`,
  `clang-analyzer-cplusplus.*`, `concurrency-mt-unsafe`). `HeaderFilterRegex` scoped to
  `src/.*\.h$` (keeps `_deps/` out).
- **cppcheck** — a secondary static pass over `build/compile_commands.json`.
- **clang-format** — ship `.clang-format` and check with `clang-format --dry-run -Werror` (if
  `.clang-tidy` declares `FormatStyle: file`, the file MUST exist — an undeclared formatter is a
  recorded architect decision, not an accident).

## Specific prohibitions

- No raw `new`/`delete` — `std::unique_ptr` by default, `std::shared_ptr` only for real shared
  ownership.
- No business logic in QML or `bridge/` — the bridge only proxies.
- Never block the main thread; worker results — signals only.
- `pragma Singleton` in QML — forbidden (context properties instead).
- Include guards — forbidden; `#pragma once` only.
- `QString` (not `std::string`) in public API; large objects by `const&`/`&&`.
- Protocol/backend-specific fixes live ONLY in that protocol's branches/classes; shared code
  (controllers, sync managers, bridge models) doesn't change without confirming all protocols
  need it.

## C++/Qt-specific patterns

- **void + signals** in the bridge (see §Concurrency) — the single sanctioned async idiom.
- **Partial-class split** for large bridge classes: one header, implementation across several
  `.cpp` files by functional group — satisfies LOC limits without breaking the facade
  (QG-NN-03; a MOC `Q_PROPERTY` facade's header is inherent surface — cap it with a documented
  ceiling + a revisit trigger instead of a mechanical cut).
- Include order: stdlib → Qt → project (`core/...`).
- `target_link_libraries` — `PUBLIC`/`PRIVATE` only; `INTERFACE` only when genuinely needed.
