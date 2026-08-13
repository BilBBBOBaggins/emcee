# Layered Architecture — general layer pattern

Splitting code into layers with a clear direction of dependencies. One of the most fundamental architectural patterns — applicable to any type of application.

## Basic principle

Code is organized into layers, dependencies between them are **one-directional**:

~~~
Layer N   ↓
Layer N-1 ↓
...
Layer 1
~~~

Each layer can use the layers **below** it, but not the layers **above** it. Reverse imports are forbidden.

This is the pattern's only invariant. The number of layers, their purpose, specific names — vary by project.

## When to apply

Almost always. Layered architecture is such a fundamental pattern that it's almost not a choice.

**Not applying it** makes sense only for:

- Simple scripts (< 100 lines)
- Pure libraries with a single function
- Prototype/throwaway code

For everything else — layers.

## Number of layers

Depends on complexity and project type. Typical variants:

### 2 layers — for simple applications

~~~
Application Logic
Data Access
~~~

Or:

~~~
Handlers / Entry Points
Business Logic
~~~

Suitable for: CLI tools, simple APIs, scripts with persistence.

### 3 layers — the most common variant

The classic split:

~~~
Presentation   (UI / API handlers / CLI commands)
Business       (Domain logic, use cases)
Persistence    (Data access, external services)
~~~

Suitable for: most business applications, backend services, web apps.

### 4 layers — with an explicit domain layer

~~~
Presentation   (UI / API)
Application    (Use cases / orchestration)
Domain         (Business rules, entities)
Infrastructure (Persistence, external)
~~~

The difference from the 3-layer version — the application layer orchestrates use cases, and the domain layer contains pure business rules with no dependencies. This structure is close to Clean Architecture and Hexagonal.

Suitable for: complex business applications, projects with a rich domain model, long-lived enterprise systems.

### 5+ layers — usually over-engineering

Exception — specialized systems (financial systems with several compliance slices, multi-tenant SaaS with explicit tenant-level concerns).

For most projects, 5+ layers is a signal that the structure is too complex and needs refactoring.

## Direction of dependencies

The main rule: dependencies go **down**, not up.

What this means in practice:

- Presentation imports Business, not the other way around
- Business uses Persistence only through interfaces Business itself defines — it never imports the
  implementation (how the import edge actually points after that — Dependency Inversion, below)
- Domain doesn't know Presentation exists

### Dependency Inversion

For Business to be able to use Persistence without depending on a specific implementation — Dependency Inversion through interfaces:

Business layer defines the interface it needs:

~~~go
// internal/business/user_service.go
type UserRepository interface {
    FindByID(ctx context.Context, id UserID) (*User, error)
    Save(ctx context.Context, user *User) error
}
~~~

Persistence layer implements this interface:

~~~go
// internal/persistence/postgres_user_repo.go
type PostgresUserRepository struct {
    db *sql.DB
}

func (r *PostgresUserRepository) FindByID(ctx context.Context, id UserID) (*User, error) {
    // ...
}
~~~

Result — Business doesn't import Persistence. The interface is defined in Business, the implementation is in Persistence. The dependency is inverted.

**What "direction" means after inversion.** The layering rule counts **knowledge**, not raw import
lines: after DIP the source-level import (Persistence imports the interface Business published) points
up, and that is the inversion working as designed — not a forbidden back-import. What CQ-NN-02
([core/code-quality.md](../core/code-quality.md)) bans without exception is a lower layer reaching
into an upper layer's *logic or state*; implementing a contract the upper layer published is the
sanctioned mechanism that keeps the ban enforceable.

## Concrete structure variants

### For a backend API (Go/Node/Python)

~~~
handlers/          # HTTP handlers, request/response
service/           # Business logic, use cases
repository/        # Data access
model/             # Domain entities, shared types
~~~

### For a fullstack web app

~~~
frontend/
  components/      # UI components
  hooks/           # React state
  api/             # API client

backend/
  handlers/        # HTTP handlers
  service/         # Business logic
  repository/      # Data access
~~~

Frontend and backend are different physical layers (different processes), each with its own logical layers.

### For a CLI tool

~~~
cmd/               # Command parsing, entry points
app/               # Application logic
domain/            # Core entities, rules
infra/             # File system, network, APIs
~~~

### For a desktop app with native UI and declarative UI

A special case — see [three-tier-with-bridge.md](three-tier-with-bridge.md). The pattern includes a middle layer (bridge/adapter) between native code and declarative UI.

### For a game

~~~
engine/            # Game engine, rendering
gameplay/          # Game rules, entities
scripting/         # Scripted content
content/           # Assets
~~~

### For an ML pipeline

~~~
ingestion/         # Data collection
preprocessing/     # Cleaning, feature engineering
training/          # Model training
inference/         # Model serving
api/               # External API
~~~

## Layer rules

### A layer does one thing

Each layer has a clear responsibility:

- Presentation — transforming input/output (HTTP → domain, domain → HTTP)
- Business — enforcement of business rules
- Persistence — saving and loading data

If a layer does several unrelated things — it may need to be split into two layers or a separate component extracted.

### A layer doesn't know about layers above it

Business doesn't know about HTTP. Domain doesn't know about UI. Persistence doesn't know about use cases.

This gives the following properties:

- Business logic is tested without HTTP
- Domain is tested without a DB
- Persistence can be replaced (PostgreSQL → MongoDB) without changing Business

### DTOs at layer boundaries

Objects that cross layer boundaries are DTOs (Data Transfer Objects), not domain entities.

Why:

- A domain entity has business methods that aren't needed outside
- A DTO is a simple structure, easily serializable
- Changing a domain entity doesn't break the external API

### Anti-corruption layer

Between the domain and external systems (third-party APIs, legacy systems) — an anti-corruption layer:

- Transforms external models into domain models
- Protects the domain from changes in external systems
- Localizes knowledge of the external format in one place

## Anti-patterns

### Leaky abstraction

The upper layer knows implementation details of the lower layer:

~~~go
// BAD: business code works with SQL exceptions
func (s *UserService) Register(ctx context.Context, email string) error {
    err := s.repo.Save(ctx, user)
    if pgErr, ok := err.(*pq.Error); ok && pgErr.Code == "23505" {
        return ErrDuplicateEmail
    }
}
~~~

Solution: Persistence converts SQL errors into domain errors.

### God layer

One layer has grown to do everything:

- A "service layer" of 1000 LOC contains business logic, HTTP handling, caching, and retry logic

Solution: split into smaller layers or components with clear responsibilities.

### Bypassing layers

Presentation directly reaches into Persistence, bypassing Business:

~~~go
// BAD: controller directly queries the DB
func (h *Handler) GetUser(w http.ResponseWriter, r *http.Request) {
    user := h.db.QueryUserByID(userID)  // bypasses service
    json.NewEncoder(w).Encode(user)
}
~~~

Solution: all requests go through the Business layer.

### Cyclic dependencies

Business imports Persistence, Persistence imports Business. Violates the fundamental principle.

Solution: Dependency Inversion through interfaces.

### Shared utilities that grow into god modules

"Utils" or "Common" imported by everyone. Becomes highly coupled.

Solution: small specialized modules, each about one topic.

## Checking correctness of the split

Questions to ask yourself:

1. Can I test Business without Persistence and without HTTP?
2. Can I replace the DB (PostgreSQL → SQLite for tests) without changing Business?
3. Does the Domain layer know about HTTP or the DB? (It shouldn't)
4. How many files need to change to add a new field to an entity? (Should be 2-3, not 10+)

If the answers are "no" or "many" — the layers are split incorrectly.

## Evolution of the pattern

Layered architecture isn't dogma. As the project grows, adaptations are possible:

- **Hexagonal / Ports and Adapters** — a generalization of layered with several input and output ports
- **Clean Architecture** — Uncle Bob's formalization with strict dependency rules
- **Onion Architecture** — similar to Clean, with domain at the center and layers around it
- **Vertical slicing / Feature folders** — an alternative where instead of layers there are vertical slices by features

All these patterns are variations on the same theme of one-directional dependencies. Worth studying when the basic layered approach starts limiting you.

For most projects, a classic 3-4 layer split with Dependency Inversion is sufficient for years ahead.
