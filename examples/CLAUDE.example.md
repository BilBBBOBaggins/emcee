# Acme Teams

B2B SaaS for team and access management. Web app: an owner sets up a team, invites teammates, manages roles and billing.

> This is an example of a filled-in `CLAUDE.md` (all `{{...}}` substituted, one testing variant kept). The template is at [../CLAUDE.md](../CLAUDE.md). Links in this file point at `../` only because the example lives under `examples/`; in a real project `CLAUDE.md` sits at the repo root and links go straight to `core/...`, `roles/...`.

## Stack

- Go 1.23 (backend)
- Echo (HTTP), sqlc, Goose (migrations), slog
- TypeScript 5 (frontend)
- Next.js 15 (App Router), shadcn/ui, TanStack Query
- PostgreSQL 16 (RLS for multi-tenancy)
- Make (build), golangci-lint
- testify (Go), Vitest + Testing Library + Playwright (frontend)

## Architecture

Modular monolith (Go) + Next.js frontend. The decision is recorded in [docs/adr/001-modular-monolith.example.md](docs/adr/001-modular-monolith.example.md).

Backend layers (strictly respect the direction of dependencies):

1. **transport** — HTTP handlers, middleware. Knows about service, doesn't know about the DB directly.
2. **service** — use cases, business logic. Knows about repository interfaces.
3. **repository** — data access (sqlc). Doesn't know about service/transport.

Rule: transport → service → repository. Reverse imports are forbidden.

## Commands

### Quick numeric commands

- **`/kickoff`** = project start (no days yet): architect in kickoff mode — essence → entry file → first slice → day guides. Full pipeline: [../core/pipeline.md](../core/pipeline.md).
- A single number `N` = the architect enters day N. Reads the whole project, outputs status.
- Two numbers `R D` = role R enters the context of day D without a specific task (review or planning).
- Three numbers `R D T` = role R takes task T from the guide for day D ([docs/day-1-guide.example.md](docs/day-1-guide.example.md)).

Role map:

| R | Role | Role file |
|---|------|-----------|
| 0 | Reviewer | [../roles/reviewer.md](../roles/reviewer.md) |
| 1 | Developer | [../roles/developer.md](../roles/developer.md) |
| 2 | QA E2E | [../roles/qa-e2e.md](../roles/qa-e2e.md) |
| 3 | Business Analyst | [../roles/ba.md](../roles/ba.md) |
| 4 | QA UAT | [../roles/qa-uat.md](../roles/qa-uat.md) |
| 5 | System Analyst | [../roles/sa.md](../roles/sa.md) |
| 6 | Debugger | [../roles/debugger.md](../roles/debugger.md) |
| 7 | DevOps | [../roles/devops.md](../roles/devops.md) |

The role map is the single source of truth. Day guides and other artifacts follow the convention in [../core/task-protocol.md](../core/task-protocol.md).

### Build and tests

Build:

~~~bash
make build
~~~

All tests:

~~~bash
make test
~~~

Quick run of a specific test:

~~~bash
go test ./internal/service/ -run TestInviteService_Create
npm run test -- --run InviteTeammateModal
~~~

## Required reading at the start of every session

- [../core/pipeline.md](../core/pipeline.md) — how the whole pipeline works: kickoff → ongoing, who does what
- [../core/principles.md](../core/principles.md) — base principles of agent work
- [../core/task-protocol.md](../core/task-protocol.md) — how the agent understands tasks + artifact names
- [../core/quality-gates.md](../core/quality-gates.md) — task completion criteria
- [../core/constitution.md](../core/constitution.md) — load-bearing non-negotiables + the preflight/exit check protocol

## Situational

- Debugging something broken → [../core/debugging.md](../core/debugging.md)
- Code quality questions → [../core/code-quality.md](../core/code-quality.md)
- Memory between sessions → [../core/memory.md](../core/memory.md)
- Writing or editing a skill → [../core/skills.md](../core/skills.md)
- A task with a hard contract (parser/computation/validator) → [../core/spec-driven.md](../core/spec-driven.md)
- A non-trivial / irreversible architectural decision → [../core/adversarial-panel.md](../core/adversarial-panel.md) (launch: `/panel`)
- A high-stakes role output that needs a second pair of eyes (opt.) → [../core/second-model.md](../core/second-model.md)
- UI wireframe/mockup → [../roles/designer.md](../roles/designer.md) (DORMANT, gate O1-D) · project health → [../roles/auditor.md](../roles/auditor.md) (DORMANT) · stale regimen → [../roles/upgrader.md](../roles/upgrader.md) (DORMANT)
- Porting the regimen to another runtime → [../core/portability.md](../core/portability.md)
- Backend stack → [../stack/go.md](../stack/go.md)
- Frontend stack → [../stack/react-nextjs.md](../stack/react-nextjs.md)
- Composition → [../architecture/modular-monolith.md](../architecture/modular-monolith.md), data isolation → [../architecture/multi-tenant.md](../architecture/multi-tenant.md)
- Domain → [../domain/b2b-saas.md](../domain/b2b-saas.md)

## Testing philosophy

### Outside-in BDD (for B2B with domain expertise)

Test-and-code formation pipeline:

1. SA/BA forms acceptance criteria in domain language (Given/When/Then).
2. QA UAT turns criteria into formal test cases with the expected visible behavior.
3. QA E2E or the developer writes the test code.
4. The developer implements the code so the tests pass.

Tests are a **specification**, not a check. A red test = a bug in the code (or an incomplete implementation), not a problem with the test.

An end-to-end example of this chain's **artifacts** for the "invite teammate" feature: spec → scenarios → test-cases → code — see [docs/](docs/). Note the demo day-1 guide compresses the chain into one day and runs BA in **extraction mode** (scenarios written from the freshly built code — [roles/ba.md](../roles/ba.md) → "Two modes"); on a full-size feature the chain runs pre-code, with BA in spec-first mode, exactly in the order above.

## Project specifics

- **Business context:** early B2B SaaS, MVP. Activation hinges on onboarding (inviting the team).
- **Team setup:** 1–2 people; roles are executed by switching Claude Code via numbers.
- **External dependencies:** the email provider isn't chosen yet (see PROJECT-STATE → open questions); sending mail is currently a logger stub.
- **Current status:** [docs/PROJECT-STATE.example.md](docs/PROJECT-STATE.example.md).
- **Critical prohibitions:** the tenant is determined only from the auth context, never from the request body; PII (email) is never written to logs in the clear.

## Evolution of this document

A living document. A rule is added when the agent makes a mistake that formalization can prevent; it is removed when it becomes over-specialized for context that's gone. Review every 1–3 months.
