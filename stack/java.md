# Java — stack rules

Java-specific code rules. General principles are in [core/](../core/).

## Version and tools

- Java 21 LTS minimum (virtual threads, records, pattern matching); Java 25 LTS allowed — pin the exact version in the toolchain config
- **Maven** as the default build system — `pom.xml` is the single source of truth; the Maven Wrapper (`mvnw`, `.mvn/`) is committed so every machine builds with the same version
- Gradle only with justification in an ADR (multi-module builds with heavy custom logic); if chosen — Kotlin DSL + version catalog (`libs.versions.toml`), same clean-build contract
- Dependency versions are managed in one place (`<dependencyManagement>` / BOM imports); version drift across modules is forbidden
- `maven-enforcer-plugin`: require Java version, ban duplicate/conflicting dependencies

## Project structure

Package-by-feature, layers inside each feature:

~~~
src/main/java/com/example/app/
  order/                  # feature
    domain/               # entities, value objects, domain services — no framework imports
    application/          # use cases, ports (interfaces)
    adapter/              # web controllers, persistence, external clients
  shared/                 # cross-feature value objects only, no "utils" dumping ground
src/main/resources/
  db/migration/           # Flyway SQL migrations
src/test/java/            # mirrors main
~~~

Rules:

- `domain/` imports nothing from Spring or persistence — pure Java
- Dependency direction: `adapter` → `application` → `domain`. Back-imports are forbidden
- The layering rule is enforced by an **ArchUnit** test, not by convention alone:

~~~java
@AnalyzeClasses(packages = "com.example.app")
class ArchitectureTest {
    @ArchTest
    static final ArchRule domainIsClean = noClasses()
        .that().resideInAPackage("..domain..")
        .should().dependOnClassesThat()
        .resideInAnyPackage("..adapter..", "org.springframework..", "jakarta.persistence..");
}
~~~

## Error handling

- Unchecked exceptions with a typed hierarchy per category (`OrderNotFoundException extends DomainException`); checked exceptions from libraries are wrapped at the boundary, never propagated through domain signatures
- Every wrap carries context: `throw new PaymentFailedException("charging order %s".formatted(orderId), e);`
- `catch (Exception e) { }` and `catch (Throwable t)` are forbidden; catch the narrowest type you can handle, otherwise let it propagate
- Exceptions are not control flow — a "not found" that callers routinely handle returns `Optional<T>`, an exceptional failure throws
- `Optional` only as a **return type**. Never a field, never a method parameter, never `Optional.get()` without `isPresent`/`orElseThrow`
- `null` does not cross module boundaries: return `Optional`/empty collections; annotate with JSpecify `@Nullable` where null is unavoidable

## Concurrency

- Virtual threads (Java 21) for IO-bound concurrency; a bounded platform-thread pool for CPU-bound work
- Executors via try-with-resources (`Executors.newVirtualThreadPerTaskExecutor()`); raw `new Thread()` is forbidden
- On Java 21, `synchronized` around IO pins virtual threads — use `ReentrantLock` on hot IO paths (fixed in Java 24+)
- Shared mutable state: prefer immutability (records, `List.copyOf`); otherwise confine to one thread or guard explicitly — no "it's probably safe" data races
- Every async task logs its own failure; fire-and-forget without an error sink is forbidden

## Database

- **Flyway** for migrations, versioned SQL in `src/main/resources/db/migration/`
- Preferred access, in order: **Spring Data JDBC** (explicit, no session magic) or **jOOQ** (typed SQL). JPA/Hibernate allowed with discipline: `ddl-auto: validate` only, no entity-graph magic, no lazy-loading surprises across the service boundary
- Parameterized queries always; string concatenation into SQL is forbidden
- Transactions declared at the use-case (application) layer — `@Transactional` on adapters or domain is a smell

## Framework

- **Spring Boot 3.x** as the default. Alternatives (Quarkus, Micronaut) — via ADR
- **Constructor injection only.** Field injection (`@Autowired` on fields) is forbidden — it hides dependencies and blocks plain-constructor testing
- Configuration via `@ConfigurationProperties` records, not scattered `@Value`

## Tests

- **JUnit 5** + **AssertJ** for assertions + **Mockito** for mocks
- `@ParameterizedTest` as the standard for multiple cases (the table-driven analogue)
- Unit tests run in Surefire (`*Test.java`), integration in Failsafe (`*IT.java`) — separated by naming convention, both wired into `verify`
- Integration tests use **Testcontainers** for real databases/brokers; unit tests touch no network, no clock (`Clock` is injected), no filesystem
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): **JaCoCo** bound to `verify`; artifact at `target/site/jacoco/index.html`

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Java. "Clean" = all commands green:

~~~bash
./mvnw -B verify                        # compile (-Werror), unit + integration tests, JaCoCo
./mvnw -B spotless:check                # formatting (google-java-format / palantir)
./mvnw -B checkstyle:check              # style violations = build failure
~~~

The compiler plugin is configured with `-Xlint:all -Werror` and **Error Prone** as an annotation processor — a compiler warning IS a build failure. Any of: a compile error, an Error Prone finding, a Checkstyle violation, an unformatted file, a red test = the task is not done. Suppression (`@SuppressWarnings`) — only with a reason in a comment right next to it.

## Logging

- **SLF4J** API over **Logback**; JSON output in production via `logstash-logback-encoder`
- `System.out.println` / `e.printStackTrace()` are forbidden everywhere, including tests
- Parameterized messages (`log.info("order {} processed", orderId)`), never string concatenation
- Levels: DEBUG (dev-only), INFO (normal operations), WARN (unusual but recoverable), ERROR (failures needing attention)
- Logging secrets/PII is forbidden: passwords, tokens, card numbers → `[REDACTED]`
- Request/trace correlation via MDC (trace_id, tenant_id)

## Linting

- **Error Prone** — compile-time bug patterns, runs inside `javac`, findings fail the build
- **Checkstyle** with a strict, committed config — imports, naming, complexity limits
- **Spotless** with google-java-format (or palantir-java-format) — formatting is not reviewable style, it's a machine check
- **SpotBugs** optional warn-track addition

Warnings are not allowed — see [quality-gates.md](../core/quality-gates.md).

## Specific prohibitions

- **Lombok is forbidden without an ADR** — records, constructors, and `final` fields cover the legitimate cases on Java 21; `@SneakyThrows` and `@Builder`-everywhere hide real design problems
- Field injection; static mutable state; singletons holding business data
- `java.util.Date` / `Calendar` — only `java.time`; `new Date()` in domain code means an uninjected clock
- Reflection outside serialization frameworks
- Utility-class sprawl (`XxxUtils` accreting unrelated statics) — put behavior on the type that owns the data
- Returning `null` from public methods; `Optional` in fields/parameters
- Catching an exception only to log-and-continue as if it succeeded — propagate or handle for real

## Java-specific patterns

**Immutability first**: value objects and DTOs are `record`s; collections exposed from getters are unmodifiable copies (`List.copyOf`).

**Constructor DI, explicit wiring**:

~~~java
@Service
public class OrderService {
    private final OrderRepository repo;
    private final PaymentClient payments;

    public OrderService(OrderRepository repo, PaymentClient payments) {
        this.repo = repo;
        this.payments = payments;
    }
}
~~~

**Ports at the point of use**: the `application` layer declares the interfaces it needs (`OrderRepository`, `PaymentClient`); `adapter` implements them. Domain never names an adapter type.

**Sealed hierarchies + pattern matching** for closed sets of outcomes (`sealed interface PaymentResult permits Approved, Declined, Retry`) instead of status enums with unchecked switch-cases.
