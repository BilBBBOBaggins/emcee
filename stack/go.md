# Go — stack rules

Go-specific code rules. General principles are in [core/](../core/).

## Version and modules

- Go 1.23+ (required for modern features and performance improvements)
- `go.mod` — single source of truth for dependency versions
- `replace` directives forbidden in production — only for local development on locked branches
- Vendoring (`vendor/` folder) forbidden unless specifically required for air-gapped environments
- Keep `go.sum` regularly updated — dependency security is checked via `govulncheck`

## Project structure

Standard layout:

~~~
cmd/                    # entry points (main.go for each binary)
  api/                  # HTTP API server
  worker/               # background worker
internal/               # closed to external imports
  domain/               # domain entities and business rules
  service/              # use cases
  repository/           # data access
  transport/            # HTTP handlers, middleware
pkg/                    # public API, if the project is a library
api/                    # OpenAPI specs, protobuf definitions
migrations/             # SQL migrations
~~~

Rules:

- `internal/` — closed to external imports, all private code lives here
- `pkg/` — used only if the project exports a library, not for "shared project code"
- `cmd/` — minimal code, only dependency wiring and startup
- Business logic never lives in `cmd/`

## Error handling

Native Go pattern with mandatory wrapping:

~~~go
if err != nil {
    return fmt.Errorf("processing order %s: %w", orderID, err)
}
~~~

Rules:

- Every error is wrapped with context (what was being done, with which parameters)
- `%w` to preserve the chain, not `%v` or `%s`
- Sentinel errors via `errors.Is` and `errors.As`, not string comparison
- Typed errors via custom error types for different categories:

~~~go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}
~~~

- `panic` is forbidden in production code except during initialization (init functions, startup validation)
- `recover` is used only in top-level handlers (HTTP middleware, goroutine wrappers)

## Concurrency

Goroutines + channels as the primary pattern. Rules:

- Launching a goroutine with no way to stop it is forbidden. Always use `context.Context` for cancellation
- `context.Context` — first parameter in public methods that do IO or launch goroutines
- Worker pool pattern for bounded concurrency, not unbounded spawning
- Shared mutable state either doesn't exist (actor pattern via channels) or is protected by `sync.RWMutex`
- `go func() { ... }()` without panic handling is forbidden — every goroutine has a recover at the start

Safe goroutine pattern:

~~~go
func (s *Service) processAsync(ctx context.Context, task Task) {
    go func() {
        defer func() {
            if r := recover(); r != nil {
                s.logger.Error("goroutine panic", "task", task.ID, "panic", r)
            }
        }()

        if err := s.process(ctx, task); err != nil {
            s.logger.Error("task failed", "task", task.ID, "error", err)
        }
    }()
}
~~~

## Database

- **sqlc** to generate typed code from SQL
- **Goose** for migrations
- SQL in separate files, not inline in Go code
- ORMs forbidden (GORM, Ent, and similar) — they hide performance issues, generate bad SQL, complicate debugging
- Prepared statements for all queries with user input — sqlc does this automatically
- Transactions via explicit `tx, err := db.Begin()` with mandatory `defer tx.Rollback()` and explicit `tx.Commit()`

Structure:

~~~
internal/repository/
  queries/              # .sql files for sqlc
    user.sql
    order.sql
  sqlc.yaml             # sqlc config
  db/                   # generated code (not edited by hand)
  user_repo.go          # wrapper over generated code with business logic
migrations/
  001_initial.up.sql
  001_initial.down.sql
~~~

## HTTP framework

Choice, in order of preference:

1. **Echo** — faster than Gin, less magic, good middleware. Recommended for most projects.
2. **Chi** — minimalist, if Echo's richer feature set isn't needed
3. **Standard library** (`net/http` + `http.ServeMux` from Go 1.22+) — for libraries or maximum control

Forbidden without explicit justification:

- Gin (more magic than needed, performance trails Echo in recent versions)
- Fiber (not standard `net/http`, issues with the middleware ecosystem)
- Beego (heavyweight, not Go-way)

## Tests

- **testify** for assertions (`require` when the test can't continue further, `assert` when it can)
- **gomock** or `testify/mock` for mocks
- Table-driven tests as the standard for multiple cases
- Integration tests in the same package as unit tests, separated via build tags
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): `go test ./... -coverprofile=coverage.out && go tool cover -func=coverage.out`; HTML map — `go tool cover -html=coverage.out -o coverage.html`

Table-driven pattern:

~~~go
func TestValidateEmail(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        wantErr bool
    }{
        {"valid email", "user@example.com", false},
        {"empty string", "", true},
        {"no @ sign", "userexample.com", true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := ValidateEmail(tt.input)
            if tt.wantErr {
                require.Error(t, err)
            } else {
                require.NoError(t, err)
            }
        })
    }
}
~~~

Build tags for separation:

~~~go
//go:build integration

package repository_test
~~~

Run:

~~~bash
go test ./...                          # unit tests
go test -tags=integration ./...        # integration tests
~~~

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Go. "Clean" = all commands green:

~~~bash
go build ./...                          # compiles without errors
go vet ./...                            # suspicious constructs
golangci-lint run                       # linters (see below) with no violations
test -z "$(gofmt -l .)"                 # 0 unformatted files
go test ./...                           # unit tests green
~~~

Any of: a compile error, a `go vet` finding, a linter violation, an unformatted file, a red test = the task is not done. Suppression (`//nolint`, `//nolint:errcheck`) — only with a reason in a comment right next to it.

## Logging

- **slog** from the standard library (Go 1.21+)
- `logrus`, `zap`, `log/v2`, and third-party loggers are forbidden — the language standard is sufficient
- Structured logging via key-value:

~~~go
logger.Info("order processed",
    "order_id", orderID,
    "user_id", userID,
    "duration_ms", elapsed.Milliseconds(),
)
~~~

- Levels: Debug (dev-only), Info (normal operations), Warn (unusual but recoverable), Error (failures)
- Logging sensitive data is forbidden: passwords, tokens, PII, card numbers. If a field contains any of this — `[REDACTED]`
- Context-aware logging via `slog.Default()` with context values (trace_id, tenant_id)

## Linting

**golangci-lint** with a strict config. Required linters:

- `errcheck` — unhandled errors
- `govet` — suspicious constructs
- `staticcheck` — bugs, unused code, performance
- `gofmt` / `goimports` — formatting
- `gosec` — security issues
- `ineffassign` — assignments that are never used
- `unconvert` — unnecessary type conversions
- `misspell` — typos in strings and comments
- `revive` — stylistic rules

Warnings are not allowed — see [quality-gates.md](../core/quality-gates.md).

Example `.golangci.yml` in the project.

## Specific prohibitions

- `init()` functions — only for registration (database drivers, encoding formats). No business logic, no side effects
- Global state (global variables with business data) — forbidden. Everything via dependency injection
- `reflect` — only for serialization (JSON, protobuf). Not for "metaprogramming"
- `unsafe` — forbidden without explicit justification and an ADR
- `iota` for non-sequential enumerations — avoid, write explicitly
- Named return values for functions longer than 10 lines — hurts readability
- `interface{}` / `any` in public API — avoid, use generics or typed interfaces

## Go-specific patterns

**Dependency injection via struct embedding or explicit construction**:

~~~go
type OrderService struct {
    repo     OrderRepository
    payments PaymentService
    logger   *slog.Logger
}

func NewOrderService(repo OrderRepository, payments PaymentService, logger *slog.Logger) *OrderService {
    return &OrderService{repo: repo, payments: payments, logger: logger}
}
~~~

DI frameworks (wire, fx) are forbidden at the start — constructors are sufficient.

**Interfaces are defined at the point of use**, not at the point of implementation. If `OrderService` uses `OrderRepository`, the `OrderRepository` interface is declared next to `OrderService`, not next to the concrete implementation.

**Errors are propagated, not silently swallowed**. `log.Println(err); return nil` is forbidden. Either the error is propagated upward, or it's handled explicitly (retry, fallback, user notification).
