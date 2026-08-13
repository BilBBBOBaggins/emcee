# Kotlin — stack rules

Kotlin-specific code rules (JVM backend; Android notes where they differ). General principles are in [core/](../core/). JVM infrastructure shared with Java (Flyway, Testcontainers, SLF4J stack) deliberately mirrors [stack/java.md](java.md) — where this file is silent on a JVM matter, java.md's rule applies.

## Version and tools

- Kotlin 2.1+ (K2 compiler); JDK 21 LTS as the toolchain — pin both in the build, not in README prose
- **Gradle with the Kotlin DSL** — `build.gradle.kts` + version catalog (`gradle/libs.versions.toml`) as the single source of truth; the Gradle Wrapper (`gradlew`, `gradle/wrapper/`) is committed
- Dependency versions live only in the version catalog — literals in `build.gradle.kts` are a defect
- `allWarningsAsErrors = true` in the Kotlin compiler options — a warning IS a build failure

## Project structure

Package-by-feature, layers inside each feature (same shape as java.md):

~~~
src/main/kotlin/com/example/app/
  order/                  # feature
    domain/               # entities, value objects, domain services — no framework imports
    application/          # use cases, ports (interfaces)
    adapter/              # web controllers, persistence, external clients
  shared/                 # cross-feature value objects only, no "utils" dumping ground
src/main/resources/
  db/migration/           # Flyway SQL migrations
src/test/kotlin/          # mirrors main
~~~

Rules:

- Dependency direction: `adapter` → `application` → `domain`. Back-imports are forbidden; enforced by an **ArchUnit** test (works on Kotlin bytecode), not by convention alone
- `domain/` imports nothing from Spring/Ktor or persistence — pure Kotlin
- Top-level functions are allowed but belong to a feature package — a global `Utils.kt` accreting unrelated helpers is the utility-class antipattern with nicer syntax

## Error handling

- Unchecked exceptions with a typed hierarchy per category (`OrderNotFoundException : DomainException`); every wrap carries context
- Expected, routinely-handled outcomes are **sealed hierarchies**, not exceptions:

~~~kotlin
sealed interface PaymentResult {
    data class Approved(val transactionId: String) : PaymentResult
    data class Declined(val code: String) : PaymentResult
}
~~~

- `runCatching` is forbidden in coroutine code unless `CancellationException` is rethrown — it catches `Throwable`, which silently swallows cancellation; the same applies to any `catch (e: Exception)` inside a coroutine
- Empty catch blocks are forbidden; catch the narrowest type you can handle, otherwise let it propagate
- `null` is a modeling tool, not an error channel: a function that can fail for a reason returns a sealed result or throws — never `null` meaning "something went wrong"

## Coroutines

- **Structured concurrency only**: coroutines launch inside a scope that owns their lifecycle; `GlobalScope` is forbidden
- A `suspend` function suspends — it does not launch background work; launching is the caller's scope's decision
- Dispatchers are injected (constructor parameter, default `Dispatchers.IO`/`Default`), never hardcoded at the call site — hardcoded dispatchers make tests slow and flaky
- `runBlocking` — only in `main`, tests, and blocking-world adapters; in production request paths it's a defect
- `Flow` for streams: cold by default, `stateIn`/`shareIn` deliberately with an explicit scope; collecting a flow inside `init` blocks is forbidden
- Cancellation safety: long CPU loops check `ensureActive()`; cleanup in `finally` uses `withContext(NonCancellable)` when it must complete

## Framework

- Backend: **Spring Boot 3.x** (mirrors java.md; constructor injection only, `@ConfigurationProperties` data classes) or **Ktor** for lightweight services — the choice is recorded in the entry file, switching mid-project needs an ADR
- Android: **Jetpack Compose** + `ViewModel`; state as a single `StateFlow<UiState>` per screen, events flow up, state flows down; business logic stays out of composables — an Android-first project extends this file with its own section rather than bending the backend rules

## Database

- **Flyway** for migrations, versioned SQL in `src/main/resources/db/migration/`
- Preferred access, in order: **Spring Data JDBC** (explicit, no session magic) or **jOOQ** (typed SQL); **Exposed** acceptable on Ktor projects; JPA/Hibernate with discipline: `ddl-auto: validate` only, entities are NOT data classes (equals/hashCode vs. proxies)
- Parameterized queries always; string concatenation into SQL is forbidden
- Transactions declared at the use-case (application) layer

## Tests

- **JUnit 5** + **Kotest assertions** (or AssertJ — pick one, record it) + **MockK** for mocks
- `@ParameterizedTest` / Kotest data-driven tests as the standard for multiple cases
- Coroutine tests via `kotlinx-coroutines-test`: `runTest` + injected `TestDispatcher` — a test that sleeps (`Thread.sleep`, `delay` on a real clock) is a defect
- Integration tests use **Testcontainers** for real databases/brokers; unit tests touch no network, no clock (inject `Clock`), no filesystem
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): **Kover** — `./gradlew koverHtmlReport`; artifact at `build/reports/kover/html/index.html`

Run:

~~~bash
./gradlew test                         # unit tests
./gradlew check                        # everything wired into the build
~~~

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Kotlin. "Clean" = all commands green:

~~~bash
./gradlew build                        # compile (allWarningsAsErrors), unit + integration tests
./gradlew detekt                       # static analysis, 0 findings
./gradlew ktlintCheck                  # formatting, 0 violations
~~~

Any of: a compile warning, a detekt finding, a ktlint violation, a red test = the task is not done. Suppression (`@Suppress`, `@file:Suppress`) — only with a reason in a comment right next to it. A detekt **baseline** is allowed only when adopting the regimen on legacy code, with a burn-down rule: the baseline may only shrink.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
./gradlew detekt                       # with UnusedPrivateMember/UnusedPrivateProperty active; public dead code — review detekt's unused-symbol reports, don't gate
~~~

## Logging

- **kotlin-logging** (io.github.oshai) over SLF4J/Logback; JSON output in production via `logstash-logback-encoder`
- `println` / `e.printStackTrace()` are forbidden everywhere, including tests (Android: `Log.*` only behind a logging facade)
- Lazy message lambdas: `logger.info { "order $orderId processed" }` — interpolation cost only when the level is on
- Levels: DEBUG (dev-only), INFO (normal operations), WARN (unusual but recoverable), ERROR (failures needing attention)
- Logging secrets/PII is forbidden: passwords, tokens, card numbers → `[REDACTED]`; correlation via MDC (trace_id, tenant_id)

## Linting

- **detekt** with a strict, committed config — complexity limits, coroutine rules (`detekt-rules-coroutines`), no baseline except the legacy burn-down above
- **ktlint** (via the Gradle plugin or Spotless — pick one, record it) — formatting is a machine check, not review style
- Compiler flags: `allWarningsAsErrors`, explicit API mode (`explicitApi()`) for library modules

Warnings are not allowed — see [quality-gates.md](../core/quality-gates.md).

## Specific prohibitions

- `!!` in production code — only with an invariant comment on the same line proving non-null; the fix is usually a better type, not the operator
- `lateinit` outside DI/framework lifecycles (Android views, test fixtures) — in domain code it's an unmodeled nullable
- `GlobalScope`; `runBlocking` in production request paths (repeated because they keep coming back)
- `object` singletons holding mutable business state — state is owned and injected
- Companion objects as util dumping grounds — a companion holds factory methods and constants of its own class
- Extension-function soup: extensions on types you don't own live in the feature that needs them, not in a global "extensions" package
- Data-class `copy()` chains as a state-management strategy across module boundaries — model transitions explicitly
- Scope-function pyramids (`let` inside `apply` inside `also`) — more than one level of nesting means write a named function
- Java-isms ported verbatim: builders where named/default arguments suffice, `Optional<T>` instead of `T?`, getters/setters instead of properties

## Kotlin-specific patterns

**Immutability first**: `val` by default, `data class` for values, collections exposed as read-only interfaces (`List`, not `MutableList`).

**Constructor DI, explicit wiring** (framework-agnostic):

~~~kotlin
class OrderService(
    private val repository: OrderRepository,
    private val payments: PaymentClient,
)
~~~

**Ports at the point of use**: `application` declares the interfaces it needs; `adapter` implements them. Domain never names an adapter type.

**Sealed hierarchies + exhaustive `when`** for closed sets of outcomes — no `else ->` branch that hides future cases from the compiler.

**Value classes for identifiers** (`@JvmInline value class OrderId(val raw: UUID)`) — mixing up two `UUID` parameters should be a compile error, not a production incident.
