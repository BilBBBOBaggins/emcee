# Multi-tenancy — архитектурный паттерн

Multi-tenancy закладывается с первого дня. Добавление потом — месяцы переписывания, закладка сразу — несколько часов.

## Модели multi-tenancy

Три основные модели по возрастанию изоляции:

### Shared DB, shared schema

Все tenants в одной БД, одних таблицах. Различаются по `tenant_id` в каждой таблице.

Плюсы:
- Самый дешёвый по infra
- Простые миграции (одна операция для всех)
- Простой analytics и reporting

Минусы:
- Слабая изоляция (полагается на application-level проверки)
- Один плохой tenant может деградировать performance для всех
- Риск data leak при багах

Подходит для: большинства B2B SaaS, особенно starter/SMB tier.

### Shared DB, separate schema

Все tenants в одной БД, но каждый — в своей PostgreSQL schema.

Плюсы:
- Лучшая изоляция на уровне SQL
- Tenant-specific schema evolution возможен

Минусы:
- Сложнее миграции (для каждого schema)
- Connection pooling сложнее (разные search_path)
- Limit на количество schemas в одной БД

Подходит для: mid-market, когда изоляция важна но отдельная БД избыточна.

### Separate DB per tenant

Каждый tenant — своя БД (или даже отдельный инстанс).

Плюсы:
- Максимальная изоляция
- Tenant может быть на своём железе (compliance)
- Performance isolation полная

Минусы:
- Сложная инфраструктура
- Cross-tenant analytics требует агрегации
- Миграции — параллельные операции над многими БД

Подходит для: enterprise tier, regulated industries, compliance-heavy доменов.

## Рекомендуемый подход

Для большинства проектов — **shared DB, shared schema** как старт, с архитектурой готовой к переходу на **separate DB** для enterprise tier.

Архитектурное следствие: весь код работает через абстракцию "tenant context", не знает physical layout БД. Переход с shared на separate — это изменение connection resolver, не изменение бизнес-логики.

## Правила модели shared schema

### Каждая таблица имеет tenant_id

~~~sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    -- ...остальные поля
);

CREATE INDEX idx_orders_tenant_id ON orders(tenant_id);
~~~

- `tenant_id NOT NULL` — никогда nullable
- Индекс на `tenant_id` — обязателен для performance
- Foreign key на `tenants(id)` — для referential integrity

### Все запросы фильтруются по tenant_id

Это защищается двумя слоями.

### Row-Level Security (RLS) в PostgreSQL

~~~sql
-- Включаем RLS для таблицы
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Создаём policy — видны только строки текущего tenant
CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Отдельная policy для admin роли
CREATE POLICY admin_all_access ON orders
    TO admin_role
    USING (true);
~~~

RLS добавляет `WHERE tenant_id = current_setting('app.tenant_id')` к каждому запросу автоматически. Это защита от забытого фильтра в коде.

Tenant context устанавливается в начале транзакции:

~~~sql
SET LOCAL app.tenant_id = '550e8400-e29b-41d4-a716-446655440000';
~~~

### Repository layer в коде

Дополнительная защита на уровне приложения. Каждый repository обёрнут tenant context:

~~~go
type OrderRepository struct {
    db *sql.DB
}

func (r *OrderRepository) GetByID(ctx context.Context, orderID uuid.UUID) (*Order, error) {
    tenantID, ok := TenantFromContext(ctx)
    if !ok {
        return nil, ErrNoTenantContext
    }

    // RLS защитит даже если забудем tenant_id в WHERE,
    // но пишем явно для дополнительной безопасности
    query := `SELECT * FROM orders WHERE tenant_id = $1 AND id = $2`
    // ...
}
~~~

## Tenant context

Tenant context — это текущий tenant в рамках обработки запроса. Устанавливается на самом начале и передаётся через context по всему стеку.

### Источники tenant identity

По убыванию приоритета:

1. **Subdomain** — `acme.app.example.com` → tenant "acme"
2. **JWT claim** — токен содержит `tenant_id`
3. **API key** — ключ привязан к tenant'у
4. **Path parameter** — `/tenants/{tenant_id}/...` (для admin endpoints)

Обычно используется комбинация: subdomain для UI, JWT для authenticated API calls, API key для server-to-server.

### Middleware устанавливает context

~~~go
func TenantMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        tenantID, err := resolveTenant(r)
        if err != nil {
            http.Error(w, "invalid tenant", http.StatusBadRequest)
            return
        }

        ctx := context.WithValue(r.Context(), tenantContextKey, tenantID)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
~~~

### Database connection устанавливает session var

При получении connection из pool — перед использованием выполняется SET LOCAL:

~~~go
func (db *DB) QueryWithTenant(ctx context.Context, query string, args ...interface{}) (*sql.Rows, error) {
    tenantID := TenantFromContext(ctx)

    conn, err := db.Conn(ctx)
    if err != nil {
        return nil, err
    }
    defer conn.Close()

    _, err = conn.ExecContext(ctx, "SET LOCAL app.tenant_id = $1", tenantID)
    if err != nil {
        return nil, err
    }

    return conn.QueryContext(ctx, query, args...)
}
~~~

## Cross-tenant operations

Admin и platform-level операции могут легитимно требовать доступа ко всем tenants. Правила:

- Отдельная admin роль в БД с bypass RLS (через `TO admin_role USING (true)`)
- Явная активация admin-режима в коде — не default behavior
- Audit log обязателен на все admin-действия
- Admin API endpoints отдельны от tenant API endpoints, на отдельных путях (/admin/*)
- Admin authentication отдельна от tenant authentication (например, internal SSO вместо tenant JWT)

## Миграции

Миграции в shared schema применяются ко всем tenants одновременно. Правила:

### Backwards-compatible migrations

Миграция не должна ломать старый код, работающий в процессе rolling deployment:

- Добавление колонки — nullable или с default
- Удаление колонки — сначала deprecate в коде, потом удалить через несколько deploys
- Rename — через add new + backfill + remove old, не через ALTER RENAME

Паттерн для добавления NOT NULL колонки:

~~~sql
-- Migration 001: add column nullable
ALTER TABLE orders ADD COLUMN priority INTEGER;

-- Application code: пишет в priority, но fallback для NULL

-- Migration 002 (после deploy): backfill
UPDATE orders SET priority = 0 WHERE priority IS NULL;

-- Migration 003: make NOT NULL
ALTER TABLE orders ALTER COLUMN priority SET NOT NULL;
ALTER TABLE orders ALTER COLUMN priority SET DEFAULT 0;
~~~

### Миграции данных per tenant

Если миграция данных нужна per-tenant (например, пересчёт cached fields):

- Выполняется batch job, не в transaction миграции
- Tenants обрабатываются параллельно или пакетами
- Progress tracking для long-running миграций

## Billing и usage tracking

Per-tenant метрики собираются через middleware или event log:

- Количество API вызовов
- Storage usage (размер в БД)
- Compute time (для heavy operations)
- Feature usage (какие features используются)

Агрегация происходит асинхронно:

- Raw events в специальную таблицу или time-series store
- Периодическая агрегация (hourly/daily) в billing tables
- Billing calculation — отдельный модуль

## Тесты multi-tenancy

Обязательные сценарии в test suite:

### Isolation tests

~~~go
func TestTenantIsolation(t *testing.T) {
    tenantA := createTestTenant(t)
    tenantB := createTestTenant(t)

    // Создаём order в tenant A
    orderID := createOrderInTenant(t, tenantA, "test order")

    // Пытаемся прочитать из tenant B
    ctx := withTenant(context.Background(), tenantB.ID)
    _, err := repo.GetByID(ctx, orderID)

    // Должно быть ErrNotFound, не данные tenant A
    require.ErrorIs(t, err, ErrNotFound)
}
~~~

### RLS bypass tests

Убедиться что raw SQL минуя RLS не работает без admin-роли:

~~~go
func TestRLSCannotBeBypassed(t *testing.T) {
    // Попытка прочитать без установки tenant context
    _, err := db.Query("SELECT * FROM orders")

    // Должна быть ошибка либо пустой результат, не полная таблица
    // ...
}
~~~

### Admin access tests

Admin видит всех tenants:

~~~go
func TestAdminSeesAllTenants(t *testing.T) {
    tenantA := createTestTenant(t)
    tenantB := createTestTenant(t)

    createOrderInTenant(t, tenantA, "order A")
    createOrderInTenant(t, tenantB, "order B")

    ctx := withAdminRole(context.Background())
    orders, err := adminRepo.ListAllOrders(ctx)

    require.NoError(t, err)
    require.Len(t, orders, 2) // видит обоих
}
~~~

## Антипаттерны

- **tenant_id в application memory** — global variable или thread-local без explicit context. Ломается в async workflows.
- **Опциональный tenant_id** — nullable колонка или проверка "if tenant_id != nil". Обязательное поле.
- **Admin bypass через code flag** — `if isAdmin { skipTenantCheck() }`. Должно быть на уровне БД роли, не в application code.
- **Cross-tenant reports в runtime** — "показать топ-10 продуктов across all tenants". Это admin-функция, отдельный путь, отдельная авторизация.
- **Shared resources без tenant isolation** — uploaded files в одной папке без префикса, cache keys без tenant prefix. Всё с tenant scope.

## Performance considerations

- `tenant_id` в каждом query — **обязательно индекс**. Без индекса — full table scan для каждого запроса
- Composite indexes должны начинаться с `tenant_id`:

~~~sql
CREATE INDEX idx_orders_tenant_status ON orders(tenant_id, status);
CREATE INDEX idx_orders_tenant_created ON orders(tenant_id, created_at);
~~~

- Partitioning по `tenant_id` для очень больших таблиц — когда один tenant имеет миллионы записей и это мешает остальным
- Connection pooling — watch out за session variables (RLS tenant_id). Pool должен правильно обрабатывать SET LOCAL (автоматически сбрасывается при commit/rollback)
