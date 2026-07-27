# Delphi — stack rules

Delphi (Object Pascal) specific code rules. General principles are in [core/](../core/).

## Version and tools

- Delphi 12 Athens or newer; the platform toolset is pinned by the `.dproj`
- Builds run through **MSBuild** against the `.dproj` (`msbuild Project.dproj /t:Build /p:Config=Release`) — the `.dproj` is the single source of truth for compiler options; per-developer IDE overrides that diverge from it are forbidden
- Dependencies: prefer vendoring into `libs/` with pinned versions, or the **Boss** package manager if the team adopts it — either way the version is recorded in the repo, never "whatever GetIt installed"
- Committed: `.dpr`, `.dproj`, `.pas`, `.dfm`/`.fmx`. Never committed: `.dcu`, `.exe`, `__history/`, `__recovery/`, `.local`, `.identcache`

## Project structure

~~~
src/
  Project.Domain.*.pas        # entities, business rules — no VCL/FMX imports
  Project.Services.*.pas      # use cases, orchestration
  Project.Data.*.pas          # FireDAC access, persistence
  Project.UI.*.pas            # forms, frames — thin views only
tests/
  Tests.dproj                 # separate DUnitX console project
  Tests.*.pas
migrations/                   # versioned SQL scripts (001_initial.sql, ...)
~~~

Rules:

- Dotted unit namespaces (`Project.Domain.Orders`), one area per unit — no `Utils.pas` dumping ground
- Dependency direction: `UI` → `Services` → `Domain`; `Data` implements interfaces declared by `Services`. Back-imports (Domain using UI/Data units) are forbidden
- Forms and event handlers are thin: a handler validates nothing and computes nothing — it delegates to a service and displays the result

## Error handling

- Exceptions only; a typed hierarchy per category (`EOrderNotFound = class(EDomainError)`)
- Every wrap carries context: `raise EPaymentFailed.CreateFmt('charging order %s', [OrderId]);`
- Empty handlers (`except end`) are **forbidden** — the classic Delphi silent-swallow is a defect wherever it appears
- Re-raise with bare `raise` (preserves the original), not `raise E` (destroys the call context)
- `on E: Exception do` (the base class) only at top-level boundaries (application handler, thread wrapper); everywhere else catch the narrowest type

## Memory and ownership

- Every locally created object: `try..finally Free` — no exceptions to this rule
- Fields: `FreeAndNil(FField)` in the destructor; locals: plain `.Free` inside `finally`
- Collections own their elements explicitly: `TObjectList<T>.Create(True)` — ownership is stated at the creation site, not assumed
- Components created with an `Owner` are freed by the owner — don't double-free them
- Interface references are reference-counted: never call `Free` on an object also held through an interface variable, and don't mix manual lifetime with refcounted lifetime for the same instance

## Concurrency

- **PPL** (`System.Threading`: `TTask`, `ITask`, `TParallel`) as the primary pattern; raw `TThread` subclassing only when a long-lived worker genuinely needs it
- UI access from any non-main thread only via `TThread.Queue` (preferred) or `TThread.Synchronize` — touching VCL/FMX controls directly from a task is forbidden
- `Application.ProcessMessages` as fake asynchrony is forbidden — that's what tasks are for
- Shared mutable state is protected (`TMonitor`, `TCriticalSection`) or replaced with immutable snapshots passed into the task
- Every task body has its own `try..except` that logs the failure — a task that dies silently is a defect

## Database

- **FireDAC**; parameterized queries only (`Query.ParamByName('id').AsInteger := ...`) — concatenating any variable into SQL text is forbidden
- Migrations: versioned SQL scripts in `migrations/` + a schema-version table applied by a small runner; the schema never changes by hand
- Data access lives in `Project.Data.*` behind interfaces declared by the service layer — no `TFDQuery` in forms

## Tests

- **DUnitX** (not legacy DUnit) in a separate console test project; **TestInsight** for in-IDE runs
- `[TestCase('...', '...')]` attributes as the standard for multiple cases (the table-driven analogue)
- Unit tests touch no network, no real clock (inject a clock interface), no database; integration tests (FireDAC against a local database) live in their own fixture group
- Service seams are interfaces, so unit tests substitute them with hand-rolled fakes or **Delphi-Mocks** / Spring4D mocks
- CI runs the console runner and trusts its exit code:

~~~
tests\bin\Tests.exe            # DUnitX console runner; non-zero exit = failures
~~~

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Delphi. "Clean" = all steps green (Windows CI, PowerShell):

~~~powershell
msbuild Tests.dproj  /t:Rebuild /p:Config=Release
msbuild Project.dproj /t:Rebuild /p:Config=Release | Tee-Object build.log
Select-String -Path build.log -Pattern '(Warning|Hint): ' -Quiet   # must be False
tests\bin\Tests.exe                                                 # exit code 0
~~~

All compiler warnings **and hints** are enabled in the `.dproj` and treated as failures — the grep step is the gate, since dcc has no global warnings-as-errors switch. Any of: a compile error, a warning, a hint, a red test = the task is not done. Suppression (`{$WARN <id> OFF}`) — only narrowly scoped with a reason in a comment right next to it, never project-wide.

## Logging

- One logging seam behind an interface (`ILogger`) injected everywhere — no `Writeln`/`OutputDebugString` scattered through business code; adapter over LoggerPro, QuickLogger, or a thin file logger
- Structured context in the message (key=value), levels: Debug (dev-only), Info (normal operations), Warning (unusual but recoverable), Error (failures)
- Logging secrets/PII is forbidden: passwords, tokens, card numbers → `[REDACTED]`

## Linting

- **DelphiLint** (SonarDelphi) as the static analyzer where the team can run it — findings are treated like linter violations, not suggestions
- Commercial analyzers (Pascal Analyzer, FixInsight) optional additions
- The compiler itself is the first linter: hints and warnings at maximum, gated by the clean-build step above

## Specific prohibitions

- **`with` statements** — forbidden; they destroy readability and create silent scope-capture bugs
- Global variables in unit `interface` sections (typed constants and types are fine) — state travels via constructor injection
- Business logic in form units or event handlers — handlers delegate
- `Variant` outside COM/OLE interop; `goto`; `Application.ProcessMessages`
- `initialization` sections with side effects beyond registration (class registration, format settings)
- `AnsiString`/`ShortString`/`PChar` juggling outside a real interop boundary — `string` (UTF-16) everywhere else
- String-typed state ("status" as `string` compared by literal) — use enums and records
- Hard-coded absolute paths; paths are composed with `TPath`

## Delphi-specific patterns

**Interfaces as service seams** (also gives refcounted lifetime and mockability):

~~~pascal
type
  IOrderRepository = interface
    ['{B1F6C6A0-3C6B-4D5E-9A1F-2E7D8C4B5A01}']
    function FindById(const OrderId: string): TOrder;
  end;

  TOrderService = class
  private
    FRepo: IOrderRepository;
    FLogger: ILogger;
  public
    constructor Create(const ARepo: IOrderRepository; const ALogger: ILogger);
  end;
~~~

- **Constructor injection by hand first**; a DI container (Spring4D) only when wiring genuinely outgrows constructors — via ADR
- **Records for value types** (`TMoney = record`), with class operators where equality/arithmetic is part of the contract
- **Forms as passive views**: the form exposes intent methods (`ShowOrders(const AOrders: TArray<TOrderView>)`), a presenter/service decides what happens — this is what makes the logic testable without the UI
