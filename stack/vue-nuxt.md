# Vue / Nuxt — stack rules

Specific rules for the frontend on Vue + Nuxt + TypeScript. General principles are in [core/](../core/).

## Version and tools

- Vue 3.5+ (`useTemplateRef`, `useId`, reactive props destructure); Nuxt 4.x — Nuxt 3 is end-of-life since 2026-07, starting a project on it needs an ADR
- TypeScript strict everywhere; `nuxt.config.ts` is the single source of project config — no parallel `.env`-driven config trees
- One package manager (pnpm by default); the lock file is committed always
- `<script setup lang="ts">` is the **only** component style. Options API in new code is forbidden — two styles in one codebase doubles the reading cost and Options API loses type inference for props/emits/expose

## Project structure

Nuxt conventions carry the layout — don't invent a parallel one:

~~~
app/
  pages/                # file-based routes — thin: compose components, no business logic
  components/           # UI; feature subfolders (components/orders/), shared/ for cross-feature
  composables/          # reusable logic — the unit of extraction (auto-imported)
  utils/                # pure functions, no reactivity
server/
  api/                  # server routes (Nitro) — the typed API layer, zod-validated input
  utils/                # server-only helpers (never imported by app code paths)
shared/                 # types/schemas used by both app/ and server/
~~~

Rules:

- Dependency direction: `pages` → `components` → `composables` → `utils`. `server/` is a separate world: app code talks to it only via `$fetch`/`useFetch`, never by importing from `server/`
- A composable is a **nameable behavior** (`useOrderPolling`, `useDebouncedSearch`), not a dumping ground — "useHelpers" or a composable returning 15 unrelated things is a defect
- Business logic lives in composables and `server/api`, not in components — a component with branching domain rules gets its logic extracted

## Error handling

- `createError({ statusCode, statusMessage })` in server routes and route middleware — never throw bare strings; the status code is part of the contract
- Client-side boundaries: `<NuxtErrorBoundary>` around feature islands that may fail independently; `onErrorCaptured` only inside reusable wrappers, not scattered per-component
- Swallowed fetch errors are forbidden: every `useFetch`/`useAsyncData` call site either renders the `error` ref or explicitly propagates it (`throw createError(...)`) — an ignored `error` return is a defect
- `error.vue` at the app root handles fatal errors; it is a real page, not a TODO

## State management

- **Pinia** for global state, **setup-store style only** (`defineStore('cart', () => { ... })`) — options-style stores reintroduce the Options API split
- Component-local state stays in `ref`/`computed` in the component; promote to a store only when 2+ unrelated components need it — premature stores are global variables with extra steps
- Server data is not store state by default: `useFetch`/`useAsyncData` already cache per key. A store holding a copy of API responses needs a stated reason (cross-page mutation, optimistic updates)
- Mutating props is forbidden (including through `reactive` unwrapping) — props flow down, events flow up; two-way needs `defineModel`

## Data fetching

- `useFetch` / `useAsyncData` for anything rendered on first paint — they are SSR-safe (no double fetch, payload transferred). Raw `$fetch` inside `setup` for initial data is forbidden: it runs twice and loses the payload
- `$fetch` is for event handlers and server-side code
- The API layer is `server/api/*` with **zod**-validated input; types are shared via `shared/`:

~~~ts
// server/api/orders.post.ts
import { orderSchema } from '~~/shared/schemas/order'

export default defineEventHandler(async (event) => {
  const body = orderSchema.parse(await readBody(event))  // ZodError → 400 via createError wrapper
  return createOrder(body)
})
~~~

- The zod schema is the source of truth; client types come from `z.infer`, not hand-written duplicates

## Tests

- **Vitest** + **@vue/test-utils** for components and composables; **@nuxt/test-utils** when Nuxt runtime (auto-imports, `useFetch`, server routes) is involved. Vitest browser mode is stable in Vitest 4 but still rough with Nuxt — adopting it is a recorded choice, not a default
- **Playwright** for E2E of **critical flows only** — E2E is the expensive tier, not the default tier
- No real network in unit/component tests — **msw** intercepts; a test hitting a live endpoint is a defect (see [core/quality-gates.md](../core/quality-gates.md))
- Test what the user sees: assert rendered output and emitted events, not internal refs
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): `vitest run --coverage` (provider `@vitest/coverage-v8`); artifact at `coverage/index.html`

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for this stack. "Clean" = all commands green:

~~~bash
npx nuxi typecheck        # vue-tsc over the whole app, 0 errors
npx eslint .              # 0 violations (flat config, see Linting)
npx prettier --check .    # formatting clean
npx vitest run            # tests green
~~~

Any of: a type error, an ESLint violation, a formatting diff, a red test = the task is not done. Suppression (`// @ts-expect-error`, `eslint-disable`) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability) — with auto-imports, dead composables are especially invisible:

~~~bash
npx knip                  # unused exports/files/deps (review, don't gate)
~~~

## Linting

- **@nuxt/eslint** (flat config) as the base — it knows Nuxt's auto-imports and directory semantics; extend, don't replace with a generic preset
- `vue/*` recommended rules stay on; `@typescript-eslint` strict rules on — weakening a rule project-wide needs a comment in the config stating why
- Formatting: **prettier** (chosen here — pick one formatter, record the choice in the entry file; running both prettier and ESLint stylistic rules produces fights)

## Specific prohibitions

- Options API in new code — see Version and tools
- `any` — except type guards; `unknown` for genuinely unknown types
- `// @ts-ignore` — use `// @ts-expect-error: reason` if suppression is genuinely needed
- `v-html` with anything not sanitized at render time (DOMPurify or equivalent) — the canonical Vue XSS hole
- A `watch` where a `computed` suffices — watchers are for side effects, not derived state
- `{ deep: true }` watchers on large objects — O(tree) on every change; watch the specific path or restructure
- Prop drilling past 2 levels — `provide`/`inject` with a typed key, or a Pinia store
- Direct DOM manipulation (`document.*`, manual `el.style`) — except focus management; the template is the render authority
- Business logic in components — belongs in composables or `server/`
- Importing from `server/` in app code — the boundary is the HTTP call

## Vue-specific patterns

**Composable extraction** — state + behavior behind a name, dependencies as arguments:

~~~ts
// app/composables/useDebouncedSearch.ts
export function useDebouncedSearch(fetcher: (q: string) => Promise<Result[]>, ms = 300) {
  const query = ref('')
  const results = ref<Result[]>([])
  watchDebounced(query, async (q) => { results.value = q ? await fetcher(q) : [] }, { debounce: ms })
  return { query, results }
}
~~~

- **Typed provide/inject**: always `InjectionKey<T>` constants in a shared module — string keys lose the type and collide silently
- **`defineModel`** for every v-model contract — no manual `modelValue` prop + `update:modelValue` emit pairs
- **`useTemplateRef('name')`** (Vue 3.5) for template refs — not `ref(null)` with a matching variable name
