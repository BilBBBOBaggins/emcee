# Go — правила работы со стеком

Специфические правила для Go-кода. Общие принципы в [core/](../core/).

## Версия и модули

- Go 1.23+ (требуется для современных features и performance improvements)
- `go.mod` — single source of truth для версий зависимостей
- Запрет на `replace` directives в production — только для локальной разработки в заблокированных ветках
- Запрет на vendoring (папка `vendor/`) если не требуется специально для air-gapped сред
- Регулярное обновление `go.sum` — безопасность зависимостей проверяется через `govulncheck`

## Структура проекта

Стандартная layout:

~~~
cmd/                    # entry points (main.go для каждого бинаря)
  api/                  # HTTP API server
  worker/               # background worker
internal/               # закрыто от внешних импортов
  domain/               # domain entities и business rules
  service/              # use cases
  repository/           # data access
  transport/            # HTTP handlers, middleware
pkg/                    # публичный API, если проект как библиотека
api/                    # OpenAPI specs, protobuf definitions
migrations/             # SQL миграции
~~~

Правила:

- `internal/` — закрыт от внешних импортов, всё приватное кладётся сюда
- `pkg/` — используется только если проект экспортирует библиотеку, не для "общего кода проекта"
- `cmd/` — минимум кода, только wiring зависимостей и запуск
- Бизнес-логика никогда не живёт в `cmd/`

## Обработка ошибок

Native Go pattern с обязательным wrapping:

~~~go
if err != nil {
    return fmt.Errorf("processing order %s: %w", orderID, err)
}
~~~

Правила:

- Каждая ошибка wrapped с контекстом (что делали, с какими параметрами)
- `%w` для сохранения цепочки, не `%v` или `%s`
- Sentinel errors через `errors.Is` и `errors.As`, не через строковое сравнение
- Типизированные ошибки через custom error types для разных категорий:

~~~go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}
~~~

- `panic` запрещён в production коде кроме инициализации (init functions, startup validation)
- `recover` используется только в top-level handlers (HTTP middleware, goroutine wrappers)

## Concurrency

Goroutines + channels как основной паттерн. Правила:

- Запуск goroutine без способа её остановить — запрещён. Всегда `context.Context` для cancellation
- `context.Context` — первый параметр в public методах которые делают IO или запускают горутины
- Worker pool pattern для bounded concurrency, не unbounded spawning
- Shared mutable state либо отсутствует (actor pattern через каналы), либо защищён `sync.RWMutex`
- `go func() { ... }()` без обработки panic запрещён — каждая goroutine имеет recover в начале

Паттерн безопасной goroutine:

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

## База данных

- **sqlc** для генерации типизированного кода из SQL
- **Goose** для миграций
- SQL в отдельных файлах, не inline в Go-коде
- Запрет на ORM (GORM, Ent и подобные) — они скрывают performance issues, генерируют плохой SQL, усложняют дебаг
- Prepared statements для всех запросов с user input — sqlc делает это автоматически
- Транзакции через explicit `tx, err := db.Begin()` с обязательным `defer tx.Rollback()` и явным `tx.Commit()`

Структура:

~~~
internal/repository/
  queries/              # .sql файлы для sqlc
    user.sql
    order.sql
  sqlc.yaml             # конфиг sqlc
  db/                   # сгенерированный код (не редактируется вручную)
  user_repo.go          # обёртка над сгенерированным кодом с бизнес-логикой
migrations/
  001_initial.up.sql
  001_initial.down.sql
~~~

## HTTP-фреймворк

Выбор в порядке предпочтения:

1. **Echo** — быстрее Gin, меньше магии, хорошие middleware. Рекомендуется для большинства проектов.
2. **Chi** — минималистичный, если не нужен богатый функционал Echo
3. **Стандартная библиотека** (`net/http` + `http.ServeMux` из Go 1.22+) — для библиотек или максимального контроля

Запрещено без явного обоснования:

- Gin (больше магии чем нужно, performance уступает Echo в новых версиях)
- Fiber (не стандартный `net/http`, проблемы с middleware ecosystem)
- Beego (тяжеловесный, не Go-way)

## Тесты

- **testify** для assertions (`require` когда дальше нельзя продолжать тест, `assert` когда можно)
- **gomock** или `testify/mock` для моков
- Table-driven tests как стандарт для multiple cases
- Integration tests в том же пакете что unit tests, разделение через build tags

Паттерн table-driven:

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

Build tags для разделения:

~~~go
//go:build integration

package repository_test
~~~

Запуск:

~~~bash
go test ./...                          # unit tests
go test -tags=integration ./...        # integration tests
~~~

## Чистая сборка (clean build)

Конкретизация правила «без warnings» из [quality-gates.md](../core/quality-gates.md) для Go. «Чисто» = все команды зелёные:

~~~bash
go build ./...                          # компиляция без ошибок
go vet ./...                            # подозрительные конструкции
golangci-lint run                       # линтеры (см. ниже) без нарушений
test -z "$(gofmt -l .)"                 # 0 неотформатированных файлов
go test ./...                           # unit-тесты зелёные
~~~

Любое из: ошибка компиляции, замечание `go vet`, нарушение линтера, неотформатированный файл, красный тест = задача не завершена. Подавление (`//nolint`, `//nolint:errcheck`) — только с причиной в комментарии рядом.

## Логирование

- **slog** из стандартной библиотеки (Go 1.21+)
- Запрет на `logrus`, `zap`, `log/v2` и сторонние логгеры — стандарт языка достаточен
- Structured logging через ключ-значение:

~~~go
logger.Info("order processed",
    "order_id", orderID,
    "user_id", userID,
    "duration_ms", elapsed.Milliseconds(),
)
~~~

- Уровни: Debug (dev-only), Info (normal operations), Warn (unusual but recoverable), Error (failures)
- Запрет на логирование sensitive data: пароли, токены, ПД, номера карт. Если поле содержит что-то из этого — `[REDACTED]`
- Context-aware logging через `slog.Default()` с context values (trace_id, tenant_id)

## Линтинг

**golangci-lint** с строгим конфигом. Обязательные линтеры:

- `errcheck` — необработанные ошибки
- `govet` — подозрительные конструкции
- `staticcheck` — bugs, unused code, performance
- `gofmt` / `goimports` — форматирование
- `gosec` — security issues
- `ineffassign` — присваивания которые не используются
- `unconvert` — ненужные type conversions
- `misspell` — опечатки в строках и комментариях
- `revive` — стилистические правила

Warnings не допускаются — см. [quality-gates.md](../core/quality-gates.md).

Пример `.golangci.yml` в проекте.

## Специфические запреты

- `init()` функции — только для регистрации (database drivers, encoding formats). Никакой бизнес-логики, никаких side effects
- Global state (global variables with business data) — запрещён. Всё через dependency injection
- `reflect` — только для сериализации (JSON, protobuf). Не для "метапрограммирования"
- `unsafe` — запрещён без явного обоснования и ADR
- `iota` для non-sequential enumerations — избегать, писать явно
- Named return values для функций длиннее 10 строк — затрудняет чтение
- `interface{}` / `any` в public API — избегать, использовать generics или типизированные интерфейсы

## Go-специфичные паттерны

**Dependency injection через struct embedding или explicit**:

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

Запрет на DI-фреймворки (wire, fx) на старте — конструкторы достаточны.

**Interfaces определяются в месте использования**, не в месте реализации. Если `OrderService` использует `OrderRepository`, интерфейс `OrderRepository` объявлен рядом с `OrderService`, не рядом с конкретной реализацией.

**Ошибки пробрасываются, не обрабатываются молча**. `log.Println(err); return nil` — запрещено. Либо ошибка пробрасывается вверх, либо обрабатывается явно (retry, fallback, user notification).
