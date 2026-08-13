# Flutter / Dart — stack rules

Flutter/Dart-specific code rules (mobile-first; desktop/web notes where they differ). General principles are in [core/](../core/).

## Version and tools

- Dart 3.5+ / Flutter stable (3.44+ as of mid-2026) — the exact SDK is pinned via **FVM** (`.fvmrc` committed) or a recorded channel+version in the entry file; "whatever is on the machine" is toolchain drift, a defect
- `pubspec.yaml` is the single source of truth for dependencies; **`pubspec.lock` is committed for apps** (packages/plugins: not committed — consumers resolve their own)
- Code generation (`build_runner` for riverpod_generator/freezed/drift) runs via `dart run build_runner build --delete-conflicting-outputs`; generated `*.g.dart`/`*.freezed.dart` files are committed so a clean checkout analyzes green

## Project structure

Feature-first folders, layers inside each feature:

~~~
lib/
  features/
    orders/
      domain/          # entities, value objects, repository interfaces — imports NO Flutter
      application/     # controllers/notifiers, use cases
      presentation/    # widgets, screens
  core/                # shared infra: networking, persistence impls, theming, routing
  main.dart            # entry point + composition root only
test/                  # mirrors lib/
~~~

Rules:

- Dependency direction: `presentation` → `application` → `domain`. Back-imports are forbidden; `domain/` imports no `package:flutter` — pure Dart, testable without a widget tree
- `core/` implements the interfaces `domain/` declares; features depend on each other only through `domain` abstractions, never `features/a` → `features/b` directly
- No `utils/` dumping ground — a helper belongs to the feature that needs it or earns a named `core/` module

## Error handling

- Expected, routinely-handled outcomes are **sealed Result hierarchies** with exhaustive `switch` — Dart 3 sealed classes make the compiler enforce completeness; exceptions are for the unexpected:

~~~dart
sealed class PaymentResult {}
final class Approved extends PaymentResult { Approved(this.txId); final String txId; }
final class Declined extends PaymentResult { Declined(this.code); final String code; }
~~~

- Typed exception hierarchy per category (`OrderNotFoundException implements AppException`) with context in fields; bare `catch (e)` to log-and-continue is forbidden — catch the narrowest type you can actually handle, otherwise propagate
- Async errors are never silently dropped: every `Future` is awaited, returned, or explicitly marked `unawaited(...)` (from `dart:async`) with the fire-and-forget reason nearby; the `unawaited_futures` lint enforces this
- `catchError` chains are forbidden in new code — `try`/`catch` around `await` reads and types better

## Async & isolates

- **async/await only**; raw `.then()` chains in new code are a defect — they hide control flow and break `try`/`catch`
- The UI isolate does no CPU-heavy work: parsing large JSON, image processing, crypto → **`Isolate.run`** (or `compute` for a single callable) — jank is a correctness bug, not a polish item
- Cancellation awareness: a controller/notifier that starts work checks it's still alive before applying the result (Riverpod: `ref.onDispose` + check; widgets: `if (!mounted) return;` after every `await` that precedes a `context`/`setState` use)
- No `Timer`/`Future.delayed` polling loops where a `Stream` subscription belongs; every `StreamSubscription` is cancelled in `dispose`

## State management

- **Riverpod** (3.x, code-gen `@riverpod` notifiers) is the default; **bloc** is the sanctioned alternative — pick ONE, record the choice in the entry file, switching mid-project needs an ADR. Mixing both in one app is forbidden
- `setState` for shared or app-level state is forbidden — it couples state to widget lifetime and makes it untestable. **Ephemeral, single-widget state (a text field's focus, an animation flag, an expanded/collapsed toggle) via `setState` is fine and preferred** — don't ceremonialize it into a provider
- State classes are immutable (`final` fields, `copyWith` or freezed); mutation happens only inside the notifier
- Providers are the DI mechanism: repositories/clients are exposed as providers and overridden in tests — no service-locator (`GetIt`-style) reach-ins alongside them

## UI

- Widgets are small and **const-first**: `const` constructors wherever the lint asks (`prefer_const_constructors`) — const widgets skip rebuilds for free
- `build()` is pure: no IO, no side effects, no provider mutation, no navigation from inside `build` — it may be called at any frame, any number of times
- Deep nesting is fixed by **extracting widget classes**, not helper methods returning `Widget` — classes get their own `BuildContext`, const-ability, and rebuild boundary; a `_buildFoo()` method gets none
- Navigation is declarative and centralized (go_router or the recorded alternative), not `Navigator.push` scattered through widgets

## Persistence

- **drift** when the data is relational/queried (typed SQL, migrations-as-code); **shared_preferences** for flags/small key-values; **hive/isar-style** stores only with a recorded reason — pick by need, record the choice in the entry file
- Persistence sits behind a `domain/` repository interface; widgets and notifiers never touch the store type directly
- Migrations are explicit and tested — "clear app data" is not a migration strategy past the first internal build

## Tests

- Unit + widget tests via **flutter_test**; **mocktail** for mocks (no codegen, null-safe); golden tests optional for critical, visually-stable UI only — they're churn magnets elsewhere
- **integration_test** for critical user flows only — slow and flaky by nature; logic coverage belongs in unit tests, widget behavior in widget tests
- No real network in tests — clients are injected (provider overrides / constructor params) and stubbed; no real time — **fake_async** and the **clock** package (`withClock`), never `sleep`/real `Future.delayed` waits
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): `flutter test --coverage`; artifact at `coverage/lcov.info` (HTML view: `genhtml coverage/lcov.info -o coverage/html`)

Run:

~~~bash
flutter test test/features/orders     # fast: one feature
flutter test                          # full unit + widget suite
~~~

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Flutter/Dart. "Clean" = all commands green:

~~~bash
dart format --set-exit-if-changed .   # 0 formatting diffs
flutter analyze                       # 0 errors, warnings AND infos (pure Dart pkg: dart analyze --fatal-infos)
flutter test                          # tests green
~~~

Any of: an analyzer error, warning, or info, a formatting diff, a red test = the task is not done. Suppression (`// ignore:`, `// ignore_for_file:`) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
dart analyze                          # unused_element / unused_field / unused_import surface private dead code
dcm check-unused-code lib && dcm check-unused-files lib   # public dead code + orphan files — DCM is COMMERCIAL (BSL, license required); use only if the project holds one, otherwise skip: there is no honest free equivalent today
~~~

## Logging

- The **`logging`** package (hierarchical `Logger('feature.orders')`) or a thin project facade over it — one choice, recorded; crash/analytics sinks attach at the root listener in the composition root
- `print()`/`debugPrint()` in production code is forbidden — it's unlevelled, unfilterable, and ships to release consoles
- Logging secrets/PII is forbidden: tokens, passwords, card numbers → `[REDACTED]`

## Linting

- **very_good_analysis** as the base (the strictest maintained set), or **flutter_lints + explicit tightening** — pick one, commit `analysis_options.yaml`, record the choice in the entry file
- `analysis_options.yaml` sets `language: strict-casts, strict-inference, strict-raw-types: true` — inference holes are how `dynamic` leaks in
- File-wide `// ignore_for_file:` for a rule the whole team dislikes = change the config instead; per-line ignores follow the Clean-build suppression rule

## Specific prohibitions

- `print()` in production code (repeated because it keeps coming back) — use the logger
- Logic in `build()` — IO, mutations, navigation; `build` computes layout from state, nothing else
- Using a `BuildContext` after an `await` without a `mounted` check (`use_build_context_synchronously` is non-negotiable) — the widget may be gone; it's a crash in the field
- `dynamic` without a written reason — `Object?` + pattern matching or a real type; `dynamic` disables the type system at the point Dart needs it most
- Global mutable singletons holding app state — state is owned by a provider/bloc and injected; hidden globals make tests order-dependent
- GetX-style magic (context-less navigation/DI/state through a global locator) without an ADR — it bypasses the widget tree's ownership model and the chosen state solution
- `!` (null assertion) without an invariant comment on the same line — the fix is usually a better type or a pattern match
- `late` outside genuinely framework-imposed lifecycles — in domain code it's an unmodeled nullable that throws at runtime
- Building lists with `.map(...).toList()` into a scrolling column instead of `ListView.builder` — unbounded eager builds are a memory/jank defect

## Dart-specific patterns

**Sealed UI state + exhaustive switch** — the loading/data/error triad is a closed set the compiler checks; no `default:` hiding future cases:

~~~dart
sealed class OrdersState {}
final class OrdersLoading extends OrdersState {}
final class OrdersData extends OrdersState { OrdersData(this.orders); final List<Order> orders; }
final class OrdersError extends OrdersState { OrdersError(this.message); final String message; }

// in build():  return switch (state) { OrdersLoading() => ..., OrdersData(:final orders) => ..., OrdersError(:final message) => ... };
~~~

**DI via providers, interfaces at the point of use**: `domain` declares `abstract interface class OrderRepository`; `core` implements it; a `@riverpod` provider exposes it and tests override it (`ProviderScope(overrides: [...])`). Pure-Dart classes still take constructor parameters — providers wire, they don't replace injection.

**Records for lightweight tuples** (`(lat: double, lng: double)`) where a named class adds nothing; promote to a class the moment behavior or invariants appear.

**Extension types** for zero-cost typed identifiers (`extension type OrderId(String raw) {}`) — mixing up two `String` parameters should be a compile error, not a production incident.
