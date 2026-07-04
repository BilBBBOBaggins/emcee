# ADR-001: Modular monolith instead of microservices at the start

Date: 2026-04-15
Status: Accepted

## In short

We're starting as a **modular monolith**, not microservices: a single deployment with hard internal
module boundaries (`transport → service → repository`, cross-module only via service interfaces)
and multi-tenancy via Postgres RLS. This gives an early B2B SaaS with a 1–2 person team enough MVP
speed, while the domain boundaries are already set in code — a module can be split out into a
service later without a rewrite.

## Context

Acme Teams is an early B2B SaaS, a 1–2 person team, MVP in weeks. Need to iterate fast while
keeping clean domain boundaries (teams, invites, billing) so something can be split out into a
service later without a rewrite. Format — [roles/architect.md](../../../roles/architect.md),
composition — [architecture/modular-monolith.md](../../../architecture/modular-monolith.md).

## Decision

A single deployment (modular monolith) with hard internal module boundaries under `internal/` and
one-directional dependencies `transport → service → repository`. Cross-module interaction only
through service interfaces, never direct access to another module's tables. Multi-tenancy via
Postgres RLS on `tenant_id`.

## Consequences

**Pros:** simple deployment and local development; a single transactional DB; boundaries set by
code, not by the network; cheap refactoring.
**Cons:** no independent scaling of modules; boundary discipline rests on review, not the network —
needs a contract test forbidding reverse imports.
**Risks:** as the team grows, temptation to "cut a corner" via another module's table. Mitigation:
an import-boundary lint rule + a check in review ([roles/reviewer.md](../../../roles/reviewer.md)).

## Alternatives considered

- **Microservices from day one** ([architecture/microservices.md](../../../architecture/microservices.md)) — rejected: the operational complexity doesn't pay off for an MVP with a 1–2 person team.
- **Monolith with no module boundaries** — rejected: cheaper now, but turns into a big ball of mud and blocks splitting out services later.
