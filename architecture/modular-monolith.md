# Modular Monolith — architectural pattern

How to build a monolith the right way: one deployment, one database, but with clear modules and explicit boundaries inside.

## What it is and when to choose it

**Modular monolith** — an architecture where the application is deployed as a single binary/process, but the code is structured as a set of modules with explicit APIs and isolation.

Contrast:

- **Classic monolith** ("big ball of mud") — everything in one pile, any code can call any other code, implicit dependencies
- **Microservices** — different processes, network between components, complex deployment and debugging

When to choose a modular monolith:

- Team of up to 10-20 developers
- Startup/early stage — scope is changing, microservices would slow down iteration
- No specific scaling requirements for individual components
- No organizational scaling (one team responsible for the whole product)

Modular monolith is the correct default choice. Moving to microservices — when concrete reasons appear, not preemptively.

## Module structure

Each module contains:

- **Domain entities** — business objects (Order, User, Task)
- **Use cases** — business logic (CreateOrder, CompleteTask)
- **Ports** — interfaces to the outside world (OrderRepository, NotificationService)
- **Adapters** — implementations of ports (PostgresOrderRepository, EmailNotificationService)

Example structure for Go:

~~~
internal/
  orders/                    # Orders module
    domain/
      order.go              # entity
      status.go             # value objects
    service/
      create_order.go       # use case
      approve_order.go      # use case
    port/
      repository.go         # interface
      notifier.go           # interface
    adapter/
      postgres_repo.go      # implementation
      email_notifier.go     # implementation
    api.go                  # module's public API

  tasks/                     # Tasks module
    ...
~~~

For TypeScript/Node.js similarly, but through the file structure:

~~~
src/
  modules/
    orders/
      domain/
      service/
      port/
      adapter/
      index.ts              # public API
    tasks/
      ...
~~~

## Boundaries between modules

Rule — module A uses module B **only through the public API**. Direct access to internal functions or entities is forbidden.

A module's public API is an explicitly designated set of exports:

- In Go — functions and types starting with an uppercase letter in the module's main package
- In TypeScript — whatever is exported from the module's `index.ts`

Internal implementations are hidden:

- In Go — packages inside the module with lowercase names or via `internal/`
- In TypeScript — files not re-exported from `index.ts`

Boundary enforcement:

- Linter rules that forbid importing from the "internals" of other modules
- In Go — `internal/` packages are automatically inaccessible from outside
- In TypeScript — via `eslint-plugin-boundaries` or `dependency-cruiser`

## Module interaction

Two patterns, choice depends on the situation.

### Synchronous call through the public API

For queries and simple commands:

~~~go
// orders module uses users module
func (s *OrderService) CreateOrder(ctx context.Context, cmd CreateOrderCommand) error {
    user, err := s.usersAPI.GetUser(ctx, cmd.UserID)
    if err != nil {
        return fmt.Errorf("getting user: %w", err)
    }

    if !user.CanPlaceOrder() {
        return ErrUserNotAllowed
    }

    // ... create the order
}
~~~

When to use:

- An immediate answer from another module is needed
- A simple operation without a complex workflow
- Modules are tightly related in meaning (orders are impossible without users)

### Event-driven model through an in-process event bus

For complex workflows and to avoid strong coupling:

~~~go
// orders module publishes an event
func (s *OrderService) CreateOrder(ctx context.Context, cmd CreateOrderCommand) error {
    order := domain.NewOrder(cmd)
    if err := s.repo.Save(ctx, order); err != nil {
        return err
    }

    s.events.Publish(OrderCreated{
        OrderID: order.ID,
        UserID:  order.UserID,
    })

    return nil
}

// notifications module is subscribed to the event
func (s *NotificationService) HandleOrderCreated(ctx context.Context, event OrderCreated) {
    s.sendEmail(ctx, event.UserID, "order_created_template", event)
}

// inventory module is also subscribed
func (s *InventoryService) HandleOrderCreated(ctx context.Context, event OrderCreated) {
    s.reserveItems(ctx, event.OrderID)
}
~~~

When to use:

- One action triggers several independent reactions
- Modules shouldn't know about each other
- Operations can run in parallel or be deferred

## Shared dependencies

In a modular monolith there's often a temptation to create a "shared" module for common code. Rules:

- **shared must not contain business logic** — only infrastructure primitives (logger, config, database connection pool)
- If business logic appears in shared — that's a sign a new module is needed, not shared
- Utilities (formatters, validators) — in separate small modules by topic, not one "utils" dumping ground

## Database

In a modular monolith — one database, but tables split by module:

- Each table "belongs" to one module
- Only the owner does DDL on its table (create, alter, drop)
- Other modules read/write through the owning module's public API, not directly via SQL to someone else's tables
- Foreign keys between tables of different modules — minimize, replace with application-level consistency

This is preparation for a possible future extraction into separate services. If module tables are independent, a module can be extracted along with its tables.

## Transactions and consistency boundaries

- Transactions within one module — an ordinary database transaction
- Transactions between modules — **avoid**. If consistency between modules is needed — use event-driven (eventual consistency) or the saga pattern
- If a transaction between modules is really needed — the modules are split incorrectly, reconsider the boundaries

## When to split into services

Triggers for extracting a module into a separate service:

- **Organizational**: different development teams, different release cadence
- **Scaling**: the module requires specific scaling (memory-heavy, CPU-heavy, network-heavy)
- **Technology**: the module requires a different stack (e.g., an ML pipeline in Python, main application in Go)
- **Availability**: the module has different SLA requirements
- **Compliance**: the module processes data with special regulatory requirements (payments, health data)

Without these triggers — keep it in the monolith.

## Migration monolith → services

If modules are properly isolated, migrating to a service is relatively simple:

1. The module's public API already exists (synchronous calls) — replace with HTTP/gRPC
2. Events already exist — replace the in-process event bus with a message broker (RabbitMQ, Kafka, Redis Streams)
3. The module's tables are moved to a separate database (or schema)
4. Transactions between modules are already replaced with eventual consistency — no changes needed
5. The deployment pipeline is updated for the new service

This is a week-to-month of work per module, not a quarter. If it takes longer — the modules were split incorrectly.

## Anti-patterns

- **Anemic module** — a module contains only data structures with no business logic, the logic is smeared across other modules. Solution: pull the logic into the module.
- **God module** — one module knows about everything else. Solution: split by responsibility.
- **Cyclic dependency** — module A depends on B, B depends on A. Solution: extract a common interface, use dependency injection, or merge the modules if they're really about the same thing.
- **Shared state** — two modules mutate the same data structure. Solution: one data owner, others operate through its API.
- **Leaky abstraction** — a module's public API returns internal types or requires knowledge of internal structure. Solution: DTOs at the module boundary.
