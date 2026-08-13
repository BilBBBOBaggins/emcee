# Node.js / TypeScript — stack rules

Node/TypeScript-specific rules for backend services and APIs. General principles are in [core/](../core/). This file covers the **backend** stack; the frontend (React/Next.js) lives in [stack/react-nextjs.md](react-nextjs.md) — don't mix their rules.

## Version and tools

- Node 24 LTS+ (Active LTS; 22 is already in maintenance) — pin in `.nvmrc` (committed) AND `"engines": { "node": ">=24" }` in `package.json`, so both version managers and CI refuse a wrong runtime
- TypeScript 5.x with `strict: true` **plus** `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` — strict alone still lets indexed access and optional-property bugs through
- **ESM only**: `"type": "module"` in `package.json`; CommonJS (`require`, `module.exports`) is forbidden in project code — dual-mode codebases rot at the interop seam
- Package manager: **pnpm** (or npm — pick one, record the choice in the entry file); the lockfile is committed always; mixing managers is forbidden because two lockfiles = two dependency truths
- `package.json` is the single source of truth for scripts — CI runs the same `pnpm run <script>` commands developers run locally

## Project structure

~~~
src/
  config.ts             # typed env config (the ONLY place that reads process.env)
  server.ts             # entry point: wiring + listen, no business logic
  routes/               # HTTP boundary: parse/validate input, call a service, shape the response
  services/             # use cases — business logic lives HERE
  domain/               # entities, value types, domain errors — imports nothing below
  repositories/         # data access (DB, external APIs)
  lib/                  # domain-independent helpers
migrations/             # committed SQL/ORM migrations
test/                   # integration tests (unit tests sit next to the code as *.test.ts)
~~~

- Dependency direction: `routes` → `services` → `repositories`/`domain`. Back-imports are forbidden ([core/code-quality.md](../core/code-quality.md))
- Business logic in a route handler is a defect — handlers validate, delegate, respond
- `process.env` is read **only** in `src/config.ts`, parsed by a schema at startup — a typo'd env var must crash boot, not surface as `undefined` three layers deep

## Error handling

- Typed error classes with cause chains — never throw strings or bare objects (they lose stack traces and can't be discriminated):

~~~ts
export class AppError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options)
    this.name = new.target.name
  }
}
export class PaymentFailedError extends AppError {}

// at the call site — wrap, preserving the chain:
throw new PaymentFailedError(`charging order ${orderId}`, { cause: e })
~~~

- Every `catch (e)` either rethrows with context, handles explicitly (retry, fallback, mapped response), or is deleted — `catch {}` and log-and-continue swallow failures
- One top-level error handler per transport (Fastify `setErrorHandler`) maps domain errors → status codes; scattering `try/catch` with status logic through handlers duplicates the mapping

## Async discipline

- No floating promises — every promise is `await`ed, `return`ed, or explicitly `void`ed with a comment; enforced by `@typescript-eslint/no-floating-promises` (an unawaited rejection is a silent crash)
- `AbortSignal` is threaded through all IO APIs (`fetch`, DB clients, queue consumers) — work that can't be cancelled leaks on timeouts and shutdown
- Sync IO (`readFileSync`, `execSync`, sync crypto) is forbidden on request paths — it blocks the event loop for every concurrent request; startup/CLI code may use it
- CPU-bound work (parsing large payloads, hashing, image work) goes to `worker_threads` or a job queue — the event loop is a shared resource, not a compute budget
- `Promise.all` only when all inputs must succeed; partial-failure flows use `Promise.allSettled` and handle each outcome

## Database

- Pick **one**: **Drizzle** (SQL-first, lightest) or **Prisma** (schema-first, richest tooling) or **Kysely** (typed query builder, no ORM layer) — record the choice in the entry file; mixing them is forbidden
- Migrations are generated, committed, and applied by tool command — schema changes never happen by hand against a live DB
- Parameterized queries only; interpolating any variable into a SQL string (including `sql.raw` with user data) is forbidden — the injection classic
- Transactions are declared at the service layer, not inside repositories — the use case knows the atomicity boundary

## Framework

- **Fastify** is the default — schema-based validation, structured logging (pino) built in, honest async support
- **NestJS** is acceptable when the team explicitly wants imposed structure (decorators, modules, DI container) — record the choice in the entry file; don't half-adopt it
- **Express** is legacy-only: maintain it where it exists, never start on it — its middleware model predates async/await and swallows rejections
- **Zod** (or valibot — pick one) at ALL external boundaries: HTTP input, env vars (the config module), queue/webhook payloads. Types are inferred from schemas (`z.infer`), never hand-duplicated — two sources of truth drift
- Data crossing a boundary unvalidated is a defect — `as MyType` on a parsed body is a lie to the compiler

## Tests

- **Vitest** for unit and integration tests; unit tests live next to the code (`*.test.ts`), integration under `test/`
- No real network in unit tests — **msw** for HTTP, or inject fake clients through constructor args; a test that hits the internet is flaky by design (see [core/quality-gates.md](../core/quality-gates.md))
- No real clock — `vi.useFakeTimers()` / `vi.setSystemTime()` for anything time-dependent
- **Testcontainers** for integration tests against a real DB/queue — mocked SQL proves nothing about SQL
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): `vitest run --coverage` (provider `@vitest/coverage-v8`); artifact at `coverage/index.html`

~~~bash
pnpm vitest run src/          # fast: unit only
pnpm vitest run               # full: unit + integration
~~~

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Node/TypeScript. "Clean" = all commands green:

~~~bash
pnpm tsc --noEmit             # typecheck: 0 errors
pnpm eslint .                 # flat config, typescript-eslint strict-type-checked: 0 violations
pnpm prettier --check .       # 0 unformatted files
pnpm vitest run               # tests green
~~~

Any of: a type error, an ESLint violation, an unformatted file, a red test = the task is not done. Suppression (`// @ts-expect-error`, `// eslint-disable-next-line`, `prettier-ignore`) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
pnpm knip                     # unused exports, deps, files (review findings, don't hard-gate)
~~~

## Logging

- **pino** — structured JSON, the ecosystem standard and Fastify's native logger; `console.log` in production code is forbidden (unstructured, unleveled, unredactable)
- Child loggers carry request context: `req.log` (Fastify) or `logger.child({ requestId })` — grep-ability across a request's lines is the point of structure
- Context goes in fields, not interpolated prose: `log.info({ orderId, durationMs }, "order processed")`
- Secrets/PII never reach logs — pino `redact` paths for tokens, passwords, card numbers, emails; redaction is configured and verified, not assumed. Redacted fields render as `[REDACTED]`

## Linting

- **ESLint 9 flat config** (`eslint.config.js`) — the legacy `.eslintrc.*` format is dead
- **typescript-eslint** with the `strict-type-checked` + `stylistic-type-checked` presets — type-aware rules are the ones that catch real bugs (floating promises, unsafe `any` flows, misused promises in conditions)
- **Prettier** for formatting; ESLint does not fight it (no formatting rules in the ESLint config)
- Warnings are not allowed — see [quality-gates.md](../core/quality-gates.md)

## Specific prohibitions

- `any` and `as any` — forbidden outside true serialization boundaries (and there, parse with a schema instead); `unknown` + narrowing is the honest version
- `@ts-ignore` — forbidden; `@ts-expect-error` with a reason comment if genuinely needed (it self-expires when the error goes away)
- `require()` in project code — this is an ESM codebase
- Default exports in library/shared code — they break rename-refactors and grep; named exports only (framework files that demand a default export are the exception)
- Barrel-file sprawl (`index.ts` re-exporting whole directories) — it defeats tree-shaking, invites import cycles, and hides the real dependency graph; import from the concrete module
- Business logic in route handlers — it lives in services
- Monkey-patching globals or prototypes (`Array.prototype.*`, patching `fetch`) — forbidden without an ADR; wrap instead
- `npx <package>` for untrusted/unpinned packages in scripts — it executes arbitrary code from the registry; dev tools are declared in `devDependencies` and run via the lockfile
- `process.exit()` outside the entry point — it skips graceful shutdown and open handles

## TypeScript-specific patterns

**Dependency injection via factory functions / constructor args** — no DI container at the start (a container is machinery you pay for before you need it; NestJS projects get theirs from the framework):

~~~ts
export function makeOrderService(deps: { repo: OrderRepository; payments: PaymentPort; log: Logger }) {
  return {
    async place(cart: Cart): Promise<Order> { /* ... */ },
  }
}
~~~

- **Ports at the point of use**: the interface a service depends on (`PaymentPort`) is declared next to the service, not next to the implementation — the consumer owns the contract
- **Discriminated unions + exhaustive `switch`** for outcomes with variants (`{ kind: "ok" } | { kind: "declined" } | ...`); a `default` case that asserts `never` makes adding a variant a compile error, not a silent fall-through
- **Branded types for ids** (`type OrderId = string & { readonly __brand: "OrderId" }`) — stops passing a `UserId` where an `OrderId` belongs, which plain `string` happily allows
