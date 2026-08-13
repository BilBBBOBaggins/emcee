# Svelte / SvelteKit — stack rules

Specific rules for the frontend on Svelte 5 + SvelteKit 2 + TypeScript. General principles are in [core/](../core/).

## Version and tools

- **Svelte 5** with runes (`$state`, `$derived`, `$effect`, `$props`) — the ONLY style for new code. Legacy stores and `$:` reactive statements are allowed solely in unmigrated legacy files; new code in the old style is a defect
- **SvelteKit 2.x**; project scaffolded via `npx sv create` — its layout is the convention, don't fight it
- TypeScript **strict** (`"strict": true` extends the generated `.svelte-kit/tsconfig.json` — don't weaken it); `lang="ts"` in every `<script>`
- Package manager pinned in `package.json` (`packageManager` field); the lock file is committed always
- Adapter (`adapter-node` / `adapter-static` / platform) — pick one, record the choice in the entry file

## Project structure

~~~
src/
  routes/               # file-based routing — pages, layouts, endpoints. Thin: wire load/actions to $lib
    +page.svelte        # UI
    +page.server.ts     # server load + form actions
    +error.svelte       # error boundary for the subtree
  lib/                  # shared code, imported as $lib/... — business logic lives HERE
    server/             # server-only: DB access, secrets, API clients with keys
  hooks.server.ts       # handle / handleError
  app.d.ts              # App.Locals, App.Error, App.PageData types
static/
~~~

Rules:

- Dependency direction: `routes` → `$lib` → `$lib/server`. Back-imports are forbidden ([core/code-quality.md](../core/code-quality.md))
- **`$lib/server` discipline**: secrets, DB clients, and privileged API calls live only there — SvelteKit hard-errors if client code imports it, and that guarantee is the point. Putting a DB client outside `$lib/server` "temporarily" defeats it
- `$env/static/private` / `$env/dynamic/private` for secrets — never `PUBLIC_`-prefixed, never read via `process.env` in app code
- A component file (> ~200 lines) or one containing business rules — split; logic moves to `$lib`

## Error handling

- **Expected** errors (404, 403, validation of a route param): `error(404, { message })` from `@sveltejs/kit` inside `load`/actions — rendered by the nearest `+error.svelte`
- **Unexpected** errors propagate to the `handleError` hook: log there with context, return a safe generic shape (`App.Error`) — internals never reach the client
- Swallowing a `load` failure (try/catch returning empty data so the page "still renders") is forbidden — a page silently missing its data is worse than an error boundary
- Form action failures: `fail(400, { ... })` with field-level details — not thrown errors, not silent re-render

## State & reactivity

- `$derived` first, `$effect` last resort. **An `$effect` that writes state derived from other state is a defect** — that's `$derived`'s job. Effects are for escapes to the outside world (DOM APIs, timers, third-party libs)
- Shared client state: runes in `.svelte.ts` modules under `$lib` (class or closure — see Patterns), imported where needed
- A writable store is still legitimate only for interop with libraries that expect the store contract; new app state doesn't start as a store
- **THE SvelteKit footgun — SSR state leakage**: on the server one module instance serves ALL requests. A module-level mutable singleton (`export const user = $state(...)` in a shared module, a module-level cache keyed by nothing) leaks one user's data into another's response. Per-request state travels through `event.locals`, `load` return values, or context (`setContext`/`getContext`) — never module scope
- URL is state: shareable/reloadable UI state (filters, tabs, pagination) goes in search params via `goto`, not in memory

## Data loading

- `+page.server.ts` `load` by default (DB, private APIs); `+page.ts` (universal) only when the data is public and benefits from running client-side on navigation — the choice is deliberate, not habit
- **Mutations are form actions**, not client `fetch` to ad-hoc endpoints — progressive enhancement via `use:enhance`, the page works without JS
- Every action validates its input **server-side with zod** (`safeParse` on `formData`); client-side validation is UX, never the security boundary
- `fetch` inside a component when a `load` function is the right layer is forbidden — it bypasses SSR, invalidation (`invalidate`/`depends`), and typed `PageData`
- `+server.ts` API routes only for genuine API consumers (webhooks, non-form clients) — not as a detour around actions

## Tests

- **Vitest** for logic and components (`@testing-library/svelte`); **Playwright** for critical user flows
- Test what the user sees: `getByRole`/`getByLabelText` over test ids; no asserting on component internals
- No real network in unit tests — **msw** intercepts; no real timers — `vi.useFakeTimers()` (see [core/quality-gates.md](../core/quality-gates.md))
- `load` functions and actions are plain functions — test them directly with a stubbed `event`, no browser needed
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): `vitest run --coverage` (provider `@vitest/coverage-v8`); artifact at `coverage/index.html`

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for this stack. "Clean" = all commands green:

~~~bash
npx svelte-kit sync                            # generated types up to date (run before check)
npx svelte-check --fail-on-warnings            # 0 errors, 0 warnings (types + a11y)
npx eslint .                                   # 0 violations (eslint-plugin-svelte + typescript-eslint, flat config)
npx prettier --check .                         # formatted (prettier-plugin-svelte)
npx vitest run                                 # tests green
~~~

Any of: a svelte-check error or warning, an ESLint violation, a formatting diff, a red test = the task is not done. Suppression (`// @ts-expect-error`, `eslint-disable`, `<!-- svelte-ignore -->`) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
npx knip                                       # unused exports/files/deps (review, don't gate)
~~~

## Accessibility & styling

- Svelte's compiler a11y warnings are part of the clean build (`svelte-check` surfaces them) — fixed, not `svelte-ignore`d
- Semantic HTML first; `aria-*` where semantics fall short; keyboard reachability for every interactive element; visible focus states
- Styling: scoped `<style>` in components is the default; a utility framework (Tailwind) is fine if adopted project-wide — pick one, record the choice in the entry file. `:global(...)` needs a comment saying why

## Linting

- **eslint-plugin-svelte** + **typescript-eslint** in flat config (`eslint.config.js`), committed; `svelte-eslint-parser` handles `.svelte`/`.svelte.ts`
- **Prettier** with `prettier-plugin-svelte`; formatting is not debated in review
- Rules tuned once at adoption, then obeyed — not disabled per-file

## Specific prohibitions

- `any` (use `unknown` and narrow) and bare `@ts-ignore` — `@ts-expect-error: reason` if genuinely needed
- `$effect` for data derivation — that's `$derived`; an effect reading and writing the same state is a loop waiting to happen
- Legacy `$:` statements or `export let` props in new code — runes only; mixing styles in one file breaks the compiler's mode detection
- Module-scope mutable state on the server (SSR leakage — see State & reactivity)
- `{@html ...}` with untrusted content — XSS; sanitize (DOMPurify) or don't render it
- Direct DOM manipulation bypassing Svelte (`document.querySelector` + mutation) — except focus management and third-party lib mounts inside `$effect`
- Business logic in `.svelte` components — it belongs in `$lib` (client) or `$lib/server`
- Client `fetch` where a `load` function or form action is the right layer
- Secrets in `PUBLIC_` env vars or in universal (`+page.ts`) load code

## Svelte-specific patterns

**Shared state module** — runes in a `.svelte.ts` class, one instance per browser (never imported into server code):

~~~ts
// src/lib/cart.svelte.ts
export class Cart {
  items = $state<CartItem[]>([]);
  total = $derived(this.items.reduce((s, i) => s + i.price * i.qty, 0));
  add(item: CartItem) { this.items.push(item); }
}
export const cart = new Cart();
~~~

**Typed form action** — zod on the boundary, `fail` for validation, typed `ActionData` in the page:

~~~ts
// src/routes/signup/+page.server.ts
import { fail } from '@sveltejs/kit';
import { z } from 'zod';
import type { Actions } from './$types';

const schema = z.object({ email: z.string().email(), password: z.string().min(8) });

export const actions: Actions = {
  default: async ({ request, locals }) => {
    const parsed = schema.safeParse(Object.fromEntries(await request.formData()));
    if (!parsed.success) return fail(400, { errors: parsed.error.flatten().fieldErrors });
    await locals.users.create(parsed.data);
    return { success: true };
  }
};
~~~

- **Snippets over slots** (Svelte 5): components take `children` and named snippets via `$props()`, render with `{@render children()}` — slots are the legacy mechanism
- Cross-component wiring within a subtree: `setContext`/`getContext` with a typed key — not a global module, not prop-drilling through five layers
