# Swift — stack rules

Swift-specific code rules (Apple platforms; server-side notes where they differ). General principles are in [core/](../core/).

## Version and tools

- Swift 6.x with **strict concurrency = complete** — Swift 6 language mode is the default for new targets; a target left in Swift 5 mode carries a comment saying why and a migration TODO
- Xcode 16+ pinned per project (`.xcode-version` or the CI config states it); toolchain drift between machines is a defect
- **SwiftPM** — `Package.swift` is the single source of truth for dependencies; `Package.resolved` is committed always
- App targets: the `.xcodeproj` is committed as-is, or generated via **Tuist**/**XcodeGen** if adopted — the choice is recorded in the entry file; mixing both is forbidden

## Project structure

Feature modules as local SPM packages, a thin app target on top:

~~~
App/                      # app target: entry point, DI wiring, no business logic
Packages/
  Features/               # one package (or target) per feature
    Orders/
      Sources/Orders/     # views, view models, feature logic
      Tests/OrdersTests/
  Domain/                 # entities, value objects, use-case protocols — imports nothing UI
  Core/                   # networking, persistence, shared clients
~~~

Rules:

- Dependency direction: `App` → `Features` → `Domain`/`Core`. `Domain` imports no SwiftUI/UIKit
- Business logic never lives in views — a view computes layout from state; decisions live in the view model or domain
- Cross-feature imports go through `Domain` protocols, never feature → feature directly

## Error handling

- Typed error enums per domain, conforming to `Error`, with context in associated values:

~~~swift
enum PaymentError: Error {
    case declined(orderID: Order.ID, code: String)
    case gatewayUnreachable(underlying: Error)
}
~~~

- `try?` across a module boundary is forbidden — it silently discards the reason; handle or propagate
- `try!` and force-unwrap (`!`) in production code — only with an invariant comment on the same line proving it can't fail
- `fatalError`/`precondition` for programmer errors (broken invariants), thrown errors for everything runtime can cause
- `Result` only at storage/callback boundaries where `throws` doesn't reach — async code uses `throws`, not `Result` chains

## Concurrency

- **async/await + actors** as the only pattern for new code; GCD (`DispatchQueue`, `DispatchSemaphore`) — legacy interop only, never for new logic
- UI state is `@MainActor`; a view model is a `@MainActor @Observable` class
- Every `Task { }` has an owner responsible for its cancellation — fire-and-forget tasks without an error sink are forbidden; `Task.detached` requires a justification comment
- `Sendable` is respected, not silenced: `@unchecked Sendable` — only with a comment stating the manual synchronization that makes it true
- Blocking a thread to wait for async work (semaphores, `DispatchGroup.wait`) is forbidden

## UI framework

- **SwiftUI** is the default; UIKit via representables where SwiftUI genuinely can't (record each case)
- State management with the `@Observable` macro (iOS 17+); `ObservableObject`/`@Published` only when the deployment target forces it
- A view body over ~50 lines or with nested conditionals = extract subviews; `AnyView` is a smell — use generics or `@ViewBuilder`
- Navigation is state-driven (`NavigationStack` + path binding), not imperative pushes scattered through views

## Persistence

- **SwiftData** for new apps on iOS 17+; **GRDB** when SQL control or migrations-as-code matter; Core Data only in legacy — the choice is recorded in the entry file
- Persistence sits behind a `Domain` protocol; views and view models never touch the store type directly
- Schema migrations are explicit and tested — "delete and reinstall" is not a migration strategy past the first TestFlight build

## Tests

- **Swift Testing** (`@Test`, `#expect`) for new unit tests; **XCTest** remains for UI tests and legacy suites — don't rewrite green tests for style
- Parameterized tests via `@Test(arguments:)` as the standard for multiple cases (the table-driven analogue)
- No real network in unit tests — clients are protocols injected at init, stubbed in tests; time via an injected `Clock`/`Date` provider, never `Date()` inside domain logic
- UI tests cover critical user flows only — they're slow and flaky by nature; logic coverage belongs in unit tests
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): `swift test --enable-code-coverage` + `xcrun llvm-cov report`; in Xcode — the coverage tab of the test result bundle

Run:

~~~bash
swift test --filter OrdersTests        # fast: one package
swift test                             # full (SPM targets)
~~~

App targets: `xcodebuild test -scheme App -destination 'platform=iOS Simulator,name=iPhone 16'`.

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Swift. "Clean" = all commands green:

~~~bash
swift build -Xswiftc -warnings-as-errors   # compiles, 0 warnings (app targets: SWIFT_TREAT_WARNINGS_AS_ERRORS=YES)
swiftlint --strict                         # 0 violations (warnings count)
swiftformat --lint .                       # 0 formatting diffs
swift test                                 # tests green
~~~

Any of: a compile warning, a SwiftLint violation, a formatting diff, a red test = the task is not done. Suppression (`// swiftlint:disable`) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
periphery scan                             # unused declarations across targets (config committed)
~~~

## Logging

- **os.Logger** (unified logging) with per-subsystem/category loggers; `print()` in production code is forbidden
- Interpolated values are `.private` by default in release builds — mark `.public` deliberately, never blanket-public a whole message
- Logging secrets/PII is forbidden: tokens, passwords, card numbers → `[REDACTED]` (privacy annotations are not a substitute for not logging them)

## Linting

- **SwiftLint** with a strict, committed config — opt into the analyzer rules where the build time allows
- **SwiftFormat** (or apple/swift-format — pick one, record it) — formatting is a machine check, not review style
- Warnings are not allowed — see [quality-gates.md](../core/quality-gates.md)

## Specific prohibitions

- Force-unwrap/`try!`/`as!` without an invariant comment (repeated because it keeps coming back)
- Implicitly unwrapped optionals (`var x: T!`) — only for `@IBOutlet`/framework-imposed lifecycles
- Singletons holding business state — `.shared` is for system frameworks; your services are injected
- `DispatchSemaphore`/blocking waits bridging sync and async code
- `NotificationCenter` for in-app domain events — use delegates, closures, or `AsyncStream`; notifications are for system events
- Massive views/view controllers — extraction is the fix, not `// MARK:` folding
- Stringly-typed identifiers (segue names, userInfo keys, dictionary-shaped models) crossing module boundaries — use types
- `@testable import` as a design substitute — if a test needs internals constantly, the API boundary is wrong

## Swift-specific patterns

**Value types first**: model data as `struct`/`enum`; a `class` exists only for identity or reference semantics (and is `final` by default).

**DI via initializer, protocol at the point of use**:

~~~swift
protocol OrderRepository: Sendable {
    func fetch(id: Order.ID) async throws -> Order
}

@MainActor @Observable
final class OrdersViewModel {
    private let repository: any OrderRepository

    init(repository: any OrderRepository) {
        self.repository = repository
    }
}
~~~

- The feature declares the protocols it needs; `Core` implements them. DI containers are unnecessary at the start — initializers and environment values are enough
- **Exhaustive `switch` over sealed state**: model UI/domain state as enums with associated values; no `default:` that hides future cases
- **`AsyncStream`/`AsyncSequence`** for event streams instead of callback arrays or Combine in new code (Combine only where SwiftUI/frameworks hand it to you)
