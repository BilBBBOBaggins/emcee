# C++ — stack rules

Stack-specific rules for plain modern C++ (servers, CLI tools, libraries, systems code) with CMake.
General principles live in [core/](../core/). **Boundary:** a Qt 6 desktop project uses
[stack/cpp-qt.md](cpp-qt.md) instead — where the two disagree, cpp-qt.md wins on its turf.

## Version and tools

- C++23 (`CMAKE_CXX_STANDARD 23`, `CMAKE_CXX_EXTENSIONS OFF`): concepts, ranges, `std::expected`,
  `std::print`. Drop to C++20 only for a recorded toolchain constraint (same escape as cpp-qt.md).
- CMake 3.28+ — the ONLY build system. **`CMakePresets.json` is committed and is the single source
  of build configs** (every circuit below is a named preset; ad-hoc `-D` flags are not
  configuration); `CMAKE_EXPORT_COMPILE_COMMANDS=ON` in the dev preset feeds clang-tidy.
- Dependencies: **vcpkg (manifest mode, `builtin-baseline` pinned in `vcpkg.json`)** or **Conan 2
  (+ committed lockfile)** — pick one, record the choice in the entry file; mixing is forbidden
  (two resolvers = two truths about versions). Git submodules / vendored copies — only with an ADR
  (they rot silently); `FetchContent` pinned to a tag for small header-only libs at most.

## Project structure

~~~
include/{{project}}/   # public headers (libraries only; apps may go src/-only)
src/                   # implementation + private headers
  main.cpp             # thin entry point: wiring ONLY
tests/                 # unit/ + integration/ (separated by CTest labels)
~~~

- A **core library target** + a thin `main()` that links it — tests link the library, never
  `main.cpp`; business logic never lives in the entry point ([core/code-quality.md](../core/code-quality.md)).
- Layers are one-directional (CQ-NN-02); each layer is its own target so the linker enforces the
  direction. No God "utils"/"common" targets — a grab-bag becomes a dependency magnet.
- `#pragma once` only; include order: stdlib → third-party → project.

## Error handling

- ONE project-wide policy, recorded in the entry file — ad-hoc mixing is forbidden (callers can't
  know what to catch). Default: **`std::expected<T, E>` for recoverable failures**; exceptions at
  subsystem boundaries (startup, config, plugin edges) where unwinding is the point.
- Error types carry context (what was attempted, with what) — a struct/enum with payload, never a
  raw `int` code (`return -1;` tells the caller nothing).
- Silent swallowing is forbidden: an `expected` is checked or propagated, never dropped;
  `catch (...)` ONLY at thread and `main()` boundaries, logging before rethrow/terminate.

## Concurrency

- `std::jthread` + `stop_token` — the default thread; detached threads are forbidden (no join = no
  shutdown, no error path). Cancellation is cooperative via the token.
- Shared data is exactly one of: **immutable**, **message-passed** (queue), or **lock-guarded**
  (`std::mutex` + `std::scoped_lock`). "Probably fine" unsynchronized access is forbidden — that's
  a race by definition; the TSan lane (§Build circuits) catches what slips through.
- Atomics — only for flags/counters, with a comment saying why an atomic suffices; an invariant
  across two variables needs a mutex. Manual `lock()`/`unlock()` is forbidden —
  `std::scoped_lock` only (an early return past a manual unlock is a deadlock).

## Tests

- **GoogleTest/GMock** (or Catch2 — pick one, record it in the entry file); `TEST_P` parameterized
  tests are the table-driven analogue, the standard for multi-case checks.
- Unit tests link the core library and touch NO network/clock/filesystem — inject small interfaces
  ([core/quality-gates.md](../core/quality-gates.md)); integration tests carry the CTest label
  `integration`. No tests = the task is not done.

~~~bash
ctest --test-dir build -LE integration --output-on-failure   # unit (fast, every task)
ctest --test-dir build --output-on-failure                   # full run
~~~

- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage
  diagnostics): gcovr over `build-cov/` — `gcovr -r . --filter 'src/' --html-details
  build-cov/coverage/index.html`; artifact at `build-cov/coverage/index.html`.

## Build circuits

Same discipline as cpp-qt.md: expensive checks live in dedicated preset-backed build dirs as
end-of-day/slice circuits, not per-task gates; a red lane at end of day is a bug to fix next
morning, not noise — the lanes catch what the per-task compiler gate structurally can't.

| Preset / dir | Configuration | Purpose | Cadence |
|---|---|---|---|
| `build/` | Debug, `-Wall -Wextra -Werror`, tests ON, compile_commands | dev cycle. **The QG-NN-02 slot** | every task |
| `build-asan/` | `-fsanitize=address,undefined -fno-omit-frame-pointer` | ASan+UBSan lane | end of day |
| `build-tsan/` | `-fsanitize=thread` | data races | after threading changes + end of day |
| `build-fuzz/` | `-fsanitize=fuzzer-no-link,address,undefined` | libFuzzer harnesses — MANDATORY for parsers/protocol inputs | on parser changes / nightly |
| `build-cov/` | Debug + `--coverage` | coverage gap-map | on request |
| `build-release/` | Release (+LTO if used) | deliverable | release |

## Clean build — MANDATORY

The concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md)
(QG-NN-02) for C++. "Clean" = all commands green:

~~~bash
cmake --preset default && cmake --build --preset default      # 0 errors, 0 warnings (-Wall -Wextra -Werror via preset)
git ls-files '*.h' '*.hpp' '*.cpp' | xargs clang-format --dry-run --Werror   # 0 formatting diffs
run-clang-tidy -p build $(git ls-files 'src/*.cpp')           # committed .clang-tidy, 0 findings
ctest --test-dir build --output-on-failure                    # tests green
~~~

If the translation-unit set grows too slow for per-task tidy, move clang-tidy to an end-of-day
`build-tidy/` circuit as cpp-qt.md does — a recorded decision, not a silent skip. Third-party
warnings — SYSTEM includes, never relaxing your own flags. Any of: a compile error, a warning, a
clang-format diff, a clang-tidy finding, a red test = the task is not done. Suppression
(`#pragma`, a local `-Wno-*`, `// NOLINT`) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

C++ has no reliable cross-TU dead-export tool; the cheap "zero production calls" probe:

~~~bash
grep -rn "<ExportedSymbol>" src/ --include="*.cpp" | grep -v test   # call-site probe; misc-unused-* / IWYU run warn-track in tidy
~~~

## Logging

- **spdlog** (or the project's chosen structured logger — pick one, record it): named
  per-subsystem loggers, levels, structured fields. `printf`/`std::cout` logging in production
  code is forbidden — unleveled and unfilterable (fine in tests and dev harnesses).
- No secrets/PII in logs: passwords, tokens, user payloads — redact to `[REDACTED]`.

## Linting

- **clang-tidy** — `.clang-tidy` committed. Baseline: `bugprone-*`, `clang-analyzer-*`,
  `concurrency-mt-unsafe`, `modernize-*`, `performance-*`, `cppcoreguidelines-owning-memory` +
  selected readability; `WarningsAsErrors` for the memory-safety subset (`bugprone-use-after-move`,
  `bugprone-dangling-handle`, `clang-analyzer-core.*/cplusplus.*`, `concurrency-mt-unsafe`).
- **clang-format** — `.clang-format` committed; checked in the clean build.

## Specific prohibitions

- Raw owning pointers, raw `new`/`delete` outside RAII/container internals, and `malloc`/`free` in
  C++ code — ownership must be visible in the type; `malloc` bypasses constructors.
- C-style casts — `static_cast`/`const_cast` name the intent; type punning via unions or
  `reinterpret_cast` — UB; use `std::bit_cast`.
- Macros for constants/functions — `constexpr`/templates exist; macros dodge scopes and types.
- `using namespace std;` in headers — pollutes every includer.
- Uninitialized variables — always initialize (`{}`); reading indeterminate values is UB.
- Singletons with mutable state — hidden global coupling; inject dependencies instead.
- `catch (...)` swallowing (§Error handling); detached threads; manual lock/unlock (§Concurrency).

## C++-specific patterns

- **Rule of zero** by default: no destructor/copy/move unless the class owns a raw resource — and
  then it's a dedicated RAII wrapper, rule of five, nothing else in the class:

~~~cpp
class FileHandle {
    FILE* f_ = nullptr;
public:
    explicit FileHandle(const char* path) : f_(std::fopen(path, "rb")) {}
    ~FileHandle() { if (f_) std::fclose(f_); }
    FileHandle(const FileHandle&) = delete;  FileHandle& operator=(const FileHandle&) = delete;
    FileHandle(FileHandle&& o) noexcept : f_(std::exchange(o.f_, nullptr)) {}
    FileHandle& operator=(FileHandle&& o) noexcept { std::swap(f_, o.f_); return *this; }
};
~~~

- **Ownership vocabulary**: `unique_ptr` default; `shared_ptr` is a design decision (documented
  shared ownership), not a convenience; raw pointers/references = non-owning observation only.
- **`span`/`string_view` discipline**: views are parameters, never members or return values of
  anything that outlives the viewed data — a dangling view is UB with no diagnostic.
- **Strong types**: `enum class` for options; newtype wrappers for ids
  (`struct UserId { int64_t v; };`) — a bare `int64_t` id swaps silently with any other.
- **Ports at point of use**: a small pure-virtual interface declared next to its consumer,
  injected via constructor — same rule as go.md; no DI frameworks.
