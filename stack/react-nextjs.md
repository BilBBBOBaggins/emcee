# React + Next.js — stack rules

Specific rules for the frontend on React + Next.js + TypeScript. General principles are in [core/](../core/).

## Next.js App Router

- **App Router** is the standard, not the Pages Router
- Server Components by default, Client Components only where interactivity is needed
- Client Components are marked explicitly via `"use client"` at the top of the file
- Minimize Client Components — every component sent to the client increases bundle size

Structure:

~~~
app/
  layout.tsx            # root layout
  page.tsx              # home page
  (auth)/               # route group for the auth flow
    login/page.tsx
    register/page.tsx
  dashboard/
    layout.tsx          # nested layout
    page.tsx
components/
  ui/                   # shadcn/ui base components (do not modify)
  features/             # feature-specific components (business logic)
  shared/               # reusable across features
lib/
  utils.ts              # utilities
  api/                  # API client
hooks/                  # custom React hooks
types/                  # shared TypeScript types
~~~

## TypeScript

Strict mode is mandatory. In `tsconfig.json`:

~~~json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitAny": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
~~~

Rules:

- `any` is forbidden except in type guards
- `unknown` instead of `any` for types that are genuinely unknown
- Prefer type inference — don't annotate if TS already infers it
- `type` vs `interface` — `interface` for objects that may be extended, `type` for union types and computed types
- Enums via `const` objects with `as const`, not the `enum` keyword (tree-shaking doesn't work with `enum`)

## Components

Rules:

- One component — one file
- Naming: PascalCase.tsx (`UserProfile.tsx`)
- Helper functions and types in the same file if used only by that component
- Large components (> 200 lines) — split into sub-components
- Props typed via interface/type in the same file

Component file structure:

~~~tsx
"use client"  // only if needed

import { useState } from "react"
// imports

type UserProfileProps = {
  userId: string
  showEmail?: boolean
}

export function UserProfile({ userId, showEmail = false }: UserProfileProps) {
  // hooks
  // handlers
  // render
}
~~~

## shadcn/ui

Used as the UI foundation. Rules:

- Base components in `components/ui/` (from the shadcn CLI) — **do not modify directly**
- If customization is needed — create a wrapper in `components/shared/` or `components/features/`
- Updating shadcn: re-running the CLI overwrites components, your modifications in `ui/` will be lost

Wrapper example:

~~~tsx
// components/shared/PrimaryButton.tsx
import { Button } from "@/components/ui/button"

export function PrimaryButton({ children, ...props }) {
  return (
    <Button variant="default" size="lg" {...props}>
      {children}
    </Button>
  )
}
~~~

## Styling

- **Tailwind CSS** — the only styling method
- CSS-in-JS is forbidden (styled-components, emotion)
- CSS modules are forbidden except when Tailwind can't cope (rare — usually a sign that a custom CSS variable or a Tailwind plugin is needed)
- Tailwind classes directly in JSX
- For complex conditional classes — `clsx` or the `cn` utility
- Design tokens (colors, spacing) via the Tailwind config, not inline

~~~tsx
import { cn } from "@/lib/utils"

<button className={cn(
  "px-4 py-2 rounded-md",
  isActive && "bg-blue-500 text-white",
  isDisabled && "opacity-50 cursor-not-allowed"
)}>
~~~

## State management

In decreasing order of priority:

1. **Local state** via `useState` — for component-specific state
2. **Server state** via **TanStack Query** — for data from the API
3. **Global state** via **Zustand** — only if cross-component state is needed that isn't server state
4. **URL state** via the Next.js router and search params — for shareable state

Rule: most state is server state. TanStack Query covers caching, invalidation, optimistic updates.

Forbidden:

- Redux — excessive for most cases, TanStack Query + Zustand solve the same problems more simply
- Context for global state — works poorly with re-renders, use Zustand
- `useEffect` for data fetching — an anti-pattern, use TanStack Query

## Data fetching

Server Components for initial load:

~~~tsx
// app/dashboard/page.tsx (Server Component by default)
async function DashboardPage() {
  const data = await fetchDashboardData()
  return <Dashboard data={data} />
}
~~~

TanStack Query for mutations and client-side fetching:

~~~tsx
"use client"

import { useMutation, useQuery } from "@tanstack/react-query"

function OrderList() {
  const { data, isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: fetchOrders,
  })

  const mutation = useMutation({
    mutationFn: createOrder,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orders"] }),
  })
}
~~~

API calls are typed. Types either come from a package shared with the backend, or are generated from the OpenAPI spec.

## Forms

**React Hook Form + Zod** for validation:

~~~tsx
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})

type FormValues = z.infer<typeof schema>

function LoginForm() {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
  })
  // ...
}
~~~

The Zod schema is the source of truth. Types are inferred from it via `z.infer`. The same schema can be used on the backend (if Node.js) for double validation.

## Routing

- Next.js file-based routing via App Router
- URL parameters typed via generated types or manual types
- Redirects via middleware or server actions, not via `window.location`
- `<Link>` from Next.js for navigation, not `<a>` (except for external links)

## Accessibility

- Semantic HTML is mandatory — `<button>` for buttons, `<nav>` for navigation, `<main>` for main content
- `aria-*` attributes where needed (not everywhere — semantic tags are often enough)
- Keyboard navigation works for all interactive elements
- Focus states are visible (no `outline: none` without a replacement)
- Alt text for images
- Form labels linked to inputs via `htmlFor` or wrapping

A11y tests in CI via `@axe-core/playwright` or similar.

## Tests

- **Vitest** for unit tests of components and utilities
- **Testing Library** for component testing
- **Playwright** for E2E
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): `vitest run --coverage` (provider `@vitest/coverage-v8`, artifacts in `coverage/`)

Rules:

- Test what the user sees, not implementation details
- `getByRole`, `getByLabelText`, `getByText` — preferred over `getByTestId`
- `data-testid` — a fallback, not the primary selector
- Snapshot tests only for stable components, not for forms and dynamic UI

Example:

~~~tsx
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

test("clicking submit calls onSubmit with form data", async () => {
  const onSubmit = vi.fn()
  render(<LoginForm onSubmit={onSubmit} />)

  await userEvent.type(screen.getByLabelText(/email/i), "test@example.com")
  await userEvent.type(screen.getByLabelText(/password/i), "password123")
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }))

  expect(onSubmit).toHaveBeenCalledWith({
    email: "test@example.com",
    password: "password123",
  })
})
~~~

## Performance

- Dynamic imports for large components not needed on initial render:

~~~tsx
import dynamic from "next/dynamic"

const HeavyChart = dynamic(() => import("./HeavyChart"), {
  loading: () => <p>Loading chart...</p>,
  ssr: false,
})
~~~

- `next/image` for all images — automatic optimization, lazy loading, responsive
- `React.memo` only after profiling, not preemptively — more often adds overhead than helps
- `useMemo` / `useCallback` only for genuinely heavy computations or references in dependency arrays

## Configuration and environment

- `.env.local` for local dev values
- `.env.production` for production defaults
- Secrets never in `.env*` files committed to git — only `.env.local` (in .gitignore)
- Environment variables typed via a schema (Zod) and validated at startup:

~~~ts
// lib/env.ts
import { z } from "zod"

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url(),
  DATABASE_URL: z.string(),
  AUTH_SECRET: z.string().min(32),
})

export const env = envSchema.parse(process.env)
~~~

## Clean build

"No warnings" from [core/quality-gates.md](../core/quality-gates.md) for this stack = three green checks:

~~~bash
npx tsc --noEmit        # strict typecheck with no errors
npm run lint            # ESLint / next lint with no violations
npm run build           # next build with no warnings
~~~

A type error, an ESLint violation, or a build warning = the task is not done. Suppression (`// @ts-ignore`, `eslint-disable`) — only with a reason in a comment (see Prohibitions below).

## Prohibitions

- `any` — except in type guards
- `// @ts-ignore` without a comment stating the reason — use `// @ts-expect-error: reason` if it's genuinely needed
- Inline styles (`style={{ ... }}`) except for dynamic values that can't be expressed via Tailwind
- `dangerouslySetInnerHTML` without sanitization via DOMPurify or an equivalent
- `localStorage` / `sessionStorage` for sensitive data — only for UI preferences
- Direct DOM manipulation via `document.*` except for focus management and analogous edge cases
