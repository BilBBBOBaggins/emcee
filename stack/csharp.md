# C# / .NET — stack rules

C#/.NET-specific code rules. General principles are in [core/](../core/).

## Version and tools

- .NET 10 LTS minimum (released Nov 2025, supported to Nov 2028); pin the SDK in `global.json` — "whatever is installed" is not a build input
- **Directory.Build.props** at the repo root is the single source of truth for compiler settings; per-project overrides of the non-negotiables below are forbidden:

~~~xml
<Project>
  <PropertyGroup>
    <Nullable>enable</Nullable>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
~~~

- **Central package management**: `Directory.Packages.props` with `ManagePackageVersionsCentrally=true` — version literals in `.csproj` files are a defect; version drift across projects is forbidden
- `<Nullable>disable</Nullable>` anywhere, including tests, needs an ADR — nullable annotations are the type system, not a style choice

## Project structure

Feature-oriented solution, layers as **projects** (same shape as java.md):

~~~
src/
  App.Domain/             # entities, value objects, domain services — references NOTHING
  App.Application/        # use cases, ports (interfaces) — references Domain only
  App.Adapters/           # persistence (EF Core), external clients — references Application
  App.Api/                # ASP.NET Core host, endpoints, DI wiring — composition root
tests/
  App.Domain.Tests/       # mirrors src per project
  App.Api.IntegrationTests/
~~~

- Dependency direction: `Api` → `Adapters` → `Application` → `Domain`. Back-references are forbidden — **enforced by project references**, the idiomatic .NET boundary mechanism: an illegal import is a compile error, not a convention. Intra-project layering (if a small project collapses layers into folders) gets an ArchUnitNET test instead
- `Domain` has zero NuGet framework dependencies — no ASP.NET, no EF Core, no `Microsoft.Extensions.*`

## Error handling

- Exceptions with a typed hierarchy per category (`OrderNotFoundException : DomainException`); every wrap carries context (`throw new PaymentFailedException($"charging order {orderId}", ex);`)
- `catch (Exception)` to log-and-continue as if it succeeded is forbidden — catch the narrowest type you can handle, otherwise let it propagate; a global exception handler (`IExceptionHandler`) owns the last resort
- Exceptions are not control flow: expected, routinely-handled outcomes are modeled as closed sets — abstract record + derived records, matched exhaustively (see patterns below)
- `null` does not cross module boundaries as an error channel: nullable annotations model "absent", results model "failed" — `null!` and `!` (null-forgiving) only with an invariant comment on the same line

## Concurrency / async

- `async void` is forbidden except UI event handlers — exceptions escape the caller and kill the process; return `Task`
- Blocking on async (`.Result`, `.Wait()`, `.GetAwaiter().GetResult()`) is forbidden in production code — deadlocks and thread-pool starvation; async is viral, propagate it
- **`CancellationToken` flows through every public async API** and reaches the outermost IO call; ASP.NET Core hands you `HttpContext.RequestAborted` — dropping it means work survives the client
- `Task.Run` is for offloading CPU-bound work only — wrapping sync IO in `Task.Run` inside a request path is fake async
- `ConfigureAwait(false)` in library projects (`Domain`, `Application`); irrelevant noise in ASP.NET Core hosts
- Fire-and-forget without an error sink is forbidden — background work goes through `IHostedService`/`BackgroundService` with its own logging

## Database

- **EF Core** as the default, with discipline: migrations committed and reviewed (`dotnet ef migrations add`), `EnsureCreated` forbidden outside throwaway tests; **lazy-loading proxies are forbidden** (`UseLazyLoadingProxies` never) — loading is explicit via `Include`/projection; read queries default to `AsNoTracking()`
- **Dapper** for hot paths and reporting SQL where EF's shape fights you — the choice per area is recorded, not mixed ad hoc
- Parameterized queries only; string interpolation into SQL is forbidden (`FromSqlInterpolated` is fine — it parameterizes; `FromSqlRaw` with concatenation is not)
- Transactions declared at the use-case (application) layer

## Framework

- **ASP.NET Core** as the default host. Rule for the API style: **minimal APIs with endpoint groups** for services; controllers only when the project genuinely needs their filter/model-binding ecosystem — pick one per project, record the choice in the entry file, mixing both is forbidden
- **Constructor injection only**, via the built-in container; property injection and `IServiceProvider` passed around as a dependency (service locator) are forbidden — they hide the dependency graph
- Configuration via the **options pattern**: `IOptions<T>` bound to record types with `ValidateDataAnnotations().ValidateOnStart()`; raw `IConfiguration["Some:Key"]` reads outside the composition root are forbidden (stringly-typed config)

## Tests

- **xUnit** as the framework; `[Theory]` + `[InlineData]`/`[MemberData]` as the standard for multiple cases (the table-driven analogue)
- Assertions: **AwesomeAssertions** (the community Apache-2.0 fork) or **Shouldly** — pick one, record it. **FluentAssertions v8+ is a paid commercial license** (Xceed, per-seat) — adding it needs an ADR with the license cost acknowledged
- Mocks: **NSubstitute** preferred; test doubles at ports (the interfaces `Application` declares), not deep inside adapters
- Integration tests: **Testcontainers** for real databases/brokers, `WebApplicationFactory<Program>` for in-process API tests; unit tests touch no network, no clock (inject `TimeProvider`), no filesystem
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): **coverlet** — `dotnet test --collect:"XPlat Code Coverage"`; artifact at `TestResults/<guid>/coverage.cobertura.xml` (HTML via `reportgenerator`)

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for C#/.NET. "Clean" = all commands green:

~~~bash
dotnet build -warnaserror              # compile + Roslyn analyzers; a warning IS a build failure
dotnet format --verify-no-changes      # formatting + .editorconfig style, 0 pending changes
dotnet test                            # unit + integration tests green
~~~

`TreatWarningsAsErrors` in Directory.Build.props makes `-warnaserror` redundant belt-and-braces — keep both so a stray project opting out still fails CI. Any of: a compile error, an analyzer warning, a formatting diff, a red test = the task is not done. Suppression (`#pragma warning disable`, `[SuppressMessage]`, `.editorconfig` severity downgrades) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
dotnet format analyzers --verify-no-changes   # with IDE0051/IDE0052 (unused private member/property) raised to warning in .editorconfig
~~~

Honest limits: Roslyn only sees unused **private** symbols; public dead code across project boundaries needs a periodic manual sweep (or ReSharper CLI `inspectcode`) — review the report, don't gate on it.

## Logging

- **`Microsoft.Extensions.Logging` abstractions** (`ILogger<T>`) in all code; **Serilog** as the provider with structured JSON output in production — code never references Serilog outside the composition root
- `Console.WriteLine` / `Debug.WriteLine` are forbidden everywhere, including tests
- Message templates, never interpolation: `log.LogInformation("order {OrderId} processed", orderId)` — interpolated strings destroy structure (and CA2254 flags them)
- Levels: Debug (dev-only), Information (normal operations), Warning (unusual but recoverable), Error (failures needing attention)
- Logging secrets/PII is forbidden: passwords, tokens, card numbers → `[REDACTED]`; correlation via scopes (`BeginScope` with trace_id, tenant_id)

## Linting

- **Roslyn analyzers** are the linter, wired into the compiler: `AnalysisLevel=latest-recommended` minimum (`latest-all` for greenfield); findings are warnings and warnings are errors — no separate lint step to skip
- **.editorconfig** committed with a strict config — naming rules, `csharp_style_*`, per-diagnostic severities; it is the single style authority for `dotnet format`
- **SonarAnalyzer.CSharp** optional warn-track addition

Warnings are not allowed — see [quality-gates.md](../core/quality-gates.md).

## Specific prohibitions

- `async void` (outside event handlers); `.Result` / `.Wait()` / sync-over-async — repeated because they keep coming back
- Public mutable statics and singletons holding business data — state is owned and injected
- Service locator: injecting `IServiceProvider` to resolve at will — declare dependencies in the constructor
- `#region` — it exists to fold code a class shouldn't have; a class needing regions needs splitting
- `DateTime.Now` / `DateTime.UtcNow` / `Stopwatch.StartNew` in domain code — inject **`TimeProvider`** (in the BCL since .NET 8); an uninjected clock makes time-dependent logic untestable
- `dynamic` outside genuine interop boundaries — it deletes the compiler
- Stringly-typed config reads (`IConfiguration` indexing) outside the composition root — use `IOptions<T>` records
- Reflection outside serialization/DI frameworks; `GC.Collect()` in application code

## C#-specific patterns

**Immutability first**: value objects and DTOs are `record` types with `init` setters; collections exposed as `IReadOnlyList<T>`, not `List<T>`.

**Sealed by default**: every class is `sealed` unless designed for inheritance — unsealing is a deliberate API decision, and the JIT devirtualizes sealed types for free.

**Constructor DI, explicit wiring** (primary constructors keep it terse):

~~~csharp
public sealed class OrderService(IOrderRepository repository, IPaymentClient payments)
{
    public async Task<PlacementResult> PlaceAsync(Order order, CancellationToken ct) =>
        await payments.ChargeAsync(order.Total, ct) is ChargeDeclined d
            ? new PlacementResult.Declined(d.Code)
            : new PlacementResult.Placed(await repository.SaveAsync(order, ct));
}
~~~

**Ports at the point of use**: `Application` declares the interfaces it needs (`IOrderRepository`, `IPaymentClient`); `Adapters` implements them. Domain never names an adapter type.

**Closed result sets as abstract records** (`public abstract record PaymentResult { public sealed record Approved(string TxId) : PaymentResult; public sealed record Declined(string Code) : PaymentResult; }`) matched with switch expressions — C# has no exhaustiveness check across an open hierarchy, so keep the set nested in one file and let CS8509 flag unhandled patterns.
