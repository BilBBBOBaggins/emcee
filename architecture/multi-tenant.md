# Multi-tenancy — architectural pattern

Multi-tenancy is designed in from day one. Adding it later means months of rewriting; designing it in from the start takes a few hours.

## Multi-tenancy models

Three main models, in increasing order of isolation:

### Shared DB, shared schema

All tenants in one database, same tables. Distinguished by `tenant_id` in every table.

Pros:
- Cheapest in terms of infra
- Simple migrations (one operation for everyone)
- Simple analytics and reporting

Cons:
- Weak isolation (relies on application-level checks)
- One bad tenant can degrade performance for everyone
- Risk of data leak from bugs

Suitable for: most B2B SaaS, especially starter/SMB tier.

### Shared DB, separate schema

All tenants in one database, but each in its own PostgreSQL schema.

Pros:
- Better isolation at the SQL level
- Tenant-specific schema evolution is possible

Cons:
- Harder migrations (per schema)
- Connection pooling is harder (different search_path)
- Limit on the number of schemas in one database

Suitable for: mid-market, when isolation matters but a separate database is overkill.

### Separate DB per tenant

Each tenant has its own database (or even a separate instance).

Pros:
- Maximum isolation
- Tenant can be on its own hardware (compliance)
- Full performance isolation

Cons:
- Complex infrastructure
- Cross-tenant analytics requires aggregation
- Migrations are parallel operations across many databases

Suitable for: enterprise tier, regulated industries, compliance-heavy domains.

## Recommended approach

For most projects — **shared DB, shared schema** as a start, with an architecture ready to transition to **separate DB** for the enterprise tier.

Architectural consequence: all code works through a "tenant context" abstraction, doesn't know the physical layout of the DB. Moving from shared to separate is a change to the connection resolver, not a change to business logic.

## Rules for the shared schema model

### Every table has tenant_id

~~~sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    -- ...remaining fields
);

CREATE INDEX idx_orders_tenant_id ON orders(tenant_id);
~~~

- `tenant_id NOT NULL` — never nullable
- Index on `tenant_id` — mandatory for performance
- Foreign key on `tenants(id)` — for referential integrity

### All queries filtered by tenant_id

This is protected by two layers.

### Row-Level Security (RLS) in PostgreSQL

~~~sql
-- Enable RLS for the table
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Create a policy — only the current tenant's rows are visible
CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Separate policy for the admin role
CREATE POLICY admin_all_access ON orders
    TO admin_role
    USING (true);
~~~

RLS adds `WHERE tenant_id = current_setting('app.tenant_id')` to every query automatically. This is protection against a forgotten filter in code.

Tenant context is set at the start of the transaction:

~~~sql
SET LOCAL app.tenant_id = '550e8400-e29b-41d4-a716-446655440000';
~~~

### Repository layer in code

Additional protection at the application level. Every repository is wrapped by tenant context:

~~~go
type OrderRepository struct {
    db *sql.DB
}

func (r *OrderRepository) GetByID(ctx context.Context, orderID uuid.UUID) (*Order, error) {
    tenantID, ok := TenantFromContext(ctx)
    if !ok {
        return nil, ErrNoTenantContext
    }

    // RLS will protect us even if we forget tenant_id in WHERE,
    // but we write it explicitly for extra safety
    query := `SELECT * FROM orders WHERE tenant_id = $1 AND id = $2`
    // ...
}
~~~

## Tenant context

Tenant context is the current tenant within request processing. Set at the very beginning and passed through context down the whole stack.

### Sources of tenant identity

In decreasing priority:

1. **Subdomain** — `acme.app.example.com` → tenant "acme"
2. **JWT claim** — token contains `tenant_id`
3. **API key** — key is bound to a tenant
4. **Path parameter** — `/tenants/{tenant_id}/...` (for admin endpoints)

Usually a combination is used: subdomain for UI, JWT for authenticated API calls, API key for server-to-server.

### Middleware sets the context

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

### Database connection sets a session var

When getting a connection from the pool — before use, a SET LOCAL is executed:

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

Admin and platform-level operations may legitimately require access to all tenants. Rules:

- A separate admin role in the DB that bypasses RLS (via `TO admin_role USING (true)`)
- Explicit activation of admin mode in code — not default behavior
- Audit log mandatory for all admin actions
- Admin API endpoints are separate from tenant API endpoints, on separate paths (/admin/*)
- Admin authentication is separate from tenant authentication (e.g., internal SSO instead of tenant JWT)

## Migrations

Migrations in shared schema are applied to all tenants simultaneously. Rules:

### Backwards-compatible migrations

A migration must not break old code running during a rolling deployment:

- Adding a column — nullable or with a default
- Removing a column — first deprecate in code, then remove after several deploys
- Rename — via add new + backfill + remove old, not via ALTER RENAME

Pattern for adding a NOT NULL column:

~~~sql
-- Migration 001: add column nullable
ALTER TABLE orders ADD COLUMN priority INTEGER;

-- Application code: writes priority, but has a fallback for NULL

-- Migration 002 (after deploy): backfill
UPDATE orders SET priority = 0 WHERE priority IS NULL;

-- Migration 003: make NOT NULL
ALTER TABLE orders ALTER COLUMN priority SET NOT NULL;
ALTER TABLE orders ALTER COLUMN priority SET DEFAULT 0;
~~~

### Per-tenant data migrations

If a data migration is needed per tenant (e.g., recomputing cached fields):

- Executed as a batch job, not within the migration transaction
- Tenants processed in parallel or in batches
- Progress tracking for long-running migrations

## Billing and usage tracking

Per-tenant metrics are collected via middleware or an event log:

- Number of API calls
- Storage usage (size in the DB)
- Compute time (for heavy operations)
- Feature usage (which features are used)

Aggregation happens asynchronously:

- Raw events into a dedicated table or time-series store
- Periodic aggregation (hourly/daily) into billing tables
- Billing calculation — a separate module

## Multi-tenancy tests

Mandatory scenarios in the test suite:

### Isolation tests

~~~go
func TestTenantIsolation(t *testing.T) {
    tenantA := createTestTenant(t)
    tenantB := createTestTenant(t)

    // Create an order in tenant A
    orderID := createOrderInTenant(t, tenantA, "test order")

    // Try to read it from tenant B
    ctx := withTenant(context.Background(), tenantB.ID)
    _, err := repo.GetByID(ctx, orderID)

    // Should be ErrNotFound, not tenant A's data
    require.ErrorIs(t, err, ErrNotFound)
}
~~~

### RLS bypass tests

Make sure raw SQL bypassing RLS doesn't work without the admin role:

~~~go
func TestRLSCannotBeBypassed(t *testing.T) {
    // Attempt to read without setting tenant context
    _, err := db.Query("SELECT * FROM orders")

    // Should be an error or an empty result, not the full table
    // ...
}
~~~

### Admin access tests

Admin sees all tenants:

~~~go
func TestAdminSeesAllTenants(t *testing.T) {
    tenantA := createTestTenant(t)
    tenantB := createTestTenant(t)

    createOrderInTenant(t, tenantA, "order A")
    createOrderInTenant(t, tenantB, "order B")

    ctx := withAdminRole(context.Background())
    orders, err := adminRepo.ListAllOrders(ctx)

    require.NoError(t, err)
    require.Len(t, orders, 2) // sees both
}
~~~

## Anti-patterns

- **tenant_id in application memory** — a global variable or thread-local without explicit context. Breaks in async workflows.
- **Optional tenant_id** — a nullable column or an "if tenant_id != nil" check. It must be a mandatory field.
- **Admin bypass through a code flag** — `if isAdmin { skipTenantCheck() }`. Should be at the DB role level, not in application code.
- **Cross-tenant reports at runtime** — "show top-10 products across all tenants". This is an admin function, a separate path, separate authorization.
- **Shared resources without tenant isolation** — uploaded files in one folder without a prefix, cache keys without a tenant prefix. Everything must be tenant-scoped.

## Performance considerations

- `tenant_id` in every query — **an index is mandatory**. Without an index — a full table scan on every query
- Composite indexes must start with `tenant_id`:

~~~sql
CREATE INDEX idx_orders_tenant_status ON orders(tenant_id, status);
CREATE INDEX idx_orders_tenant_created ON orders(tenant_id, created_at);
~~~

- Partitioning by `tenant_id` for very large tables — when one tenant has millions of records and it interferes with the rest
- Connection pooling — watch out for session variables (RLS tenant_id). The pool must handle SET LOCAL correctly (automatically reset on commit/rollback)
