# React + Next.js — правила работы со стеком

Специфические правила для фронтенда на React + Next.js + TypeScript. Общие принципы в [core/](../core/).

## Next.js App Router

- **App Router** стандарт, не Pages Router
- Server Components по умолчанию, Client Components только где нужна интерактивность
- Client Components обозначаются явно через `"use client"` в начале файла
- Минимизировать Client Components — каждый компонент в клиенте увеличивает bundle size

Структура:

~~~
app/
  layout.tsx            # root layout
  page.tsx              # home page
  (auth)/               # route group для auth flow
    login/page.tsx
    register/page.tsx
  dashboard/
    layout.tsx          # nested layout
    page.tsx
components/
  ui/                   # shadcn/ui base components (не модифицировать)
  features/             # feature-specific components (бизнес-логика)
  shared/               # reusable across features
lib/
  utils.ts              # утилиты
  api/                  # API client
hooks/                  # custom React hooks
types/                  # shared TypeScript types
~~~

## TypeScript

Strict mode обязателен. В `tsconfig.json`:

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

Правила:

- Запрет на `any` кроме как в type guards
- `unknown` вместо `any` для типов которые реально неизвестны
- Предпочтение type inference — не аннотировать если TS сам выводит
- `type` vs `interface` — `interface` для объектов которые могут расширяться, `type` для union types и computed types
- Enum'ы через `const` objects с `as const`, не через `enum` keyword (tree-shaking не работает с enum)

## Компоненты

Правила:

- Один компонент — один файл
- Именование: PascalCase.tsx (`UserProfile.tsx`)
- Вспомогательные функции и типы в том же файле если используются только в этом компоненте
- Большие компоненты (> 200 строк) — split на sub-components
- Props типизированы через interface/type в том же файле

Структура файла компонента:

~~~tsx
"use client"  // только если нужно

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

Используется как основа для UI. Правила:

- Базовые компоненты в `components/ui/` (из shadcn CLI) — **не модифицировать напрямую**
- Если нужна кастомизация — создать обёртку в `components/shared/` или `components/features/`
- Обновление shadcn: повторный запуск CLI перезаписывает компоненты, твои модификации в `ui/` потеряются

Пример обёртки:

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

## Стили

- **Tailwind CSS** — единственный способ стилизации
- Запрет на CSS-in-JS (styled-components, emotion)
- Запрет на CSS modules кроме случаев когда Tailwind не справляется (редко — обычно это знак что нужен custom CSS variable или Tailwind plugin)
- Tailwind classes прямо в JSX
- Для сложных conditional классов — `clsx` или `cn` utility
- Design tokens (цвета, spacing) через Tailwind config, не inline

~~~tsx
import { cn } from "@/lib/utils"

<button className={cn(
  "px-4 py-2 rounded-md",
  isActive && "bg-blue-500 text-white",
  isDisabled && "opacity-50 cursor-not-allowed"
)}>
~~~

## State management

По убыванию приоритета:

1. **Local state** через `useState` — для компонент-specific state
2. **Server state** через **TanStack Query** — для данных из API
3. **Global state** через **Zustand** — только если нужен cross-component state который не server state
4. **URL state** через Next.js router и search params — для shareable state

Правило: большинство state — это server state. TanStack Query покрывает caching, invalidation, optimistic updates.

Запрещено:

- Redux — избыточен для большинства случаев, TanStack Query + Zustand решают те же проблемы проще
- Context для global state — работает плохо с re-renders, используй Zustand
- useEffect для data fetching — антипаттерн, используй TanStack Query

## Data fetching

Server Components для initial load:

~~~tsx
// app/dashboard/page.tsx (Server Component by default)
async function DashboardPage() {
  const data = await fetchDashboardData()
  return <Dashboard data={data} />
}
~~~

TanStack Query для мутаций и client-side fetching:

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

API-вызовы типизированы. Типы либо из shared package с бэкендом, либо генерируются из OpenAPI спеки.

## Формы

**React Hook Form + Zod** для валидации:

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

Схема Zod — source of truth. Типы выводятся из неё через `z.infer`. Та же схема может использоваться на бэкенде (если Node.js) для double validation.

## Роутинг

- Next.js file-based routing через App Router
- Параметры URL типизированы через generated types или manual types
- Redirects через middleware или server actions, не через `window.location`
- `<Link>` из Next.js для навигации, не `<a>` (кроме external links)

## Accessibility

- Semantic HTML обязательно — `<button>` для кнопок, `<nav>` для навигации, `<main>` для main content
- `aria-*` attributes где нужно (не везде — семантические теги часто достаточны)
- Клавиатурная навигация работает для всех interactive elements
- Focus states видимы (не `outline: none` без replacement)
- Alt text для изображений
- Form labels связаны с inputs через `htmlFor` или wrapping

Тесты a11y в CI через `@axe-core/playwright` или подобное.

## Тесты

- **Vitest** для unit tests компонентов и утилит
- **Testing Library** для компонентного тестирования
- **Playwright** для E2E

Правила:

- Тестируй что видит пользователь, не implementation details
- `getByRole`, `getByLabelText`, `getByText` — предпочтительнее `getByTestId`
- `data-testid` — fallback, не основной selector
- Snapshot tests только для стабильных компонентов, не для forms и dynamic UI

Пример:

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

- Dynamic imports для больших компонентов не нужных на initial render:

~~~tsx
import dynamic from "next/dynamic"

const HeavyChart = dynamic(() => import("./HeavyChart"), {
  loading: () => <p>Loading chart...</p>,
  ssr: false,
})
~~~

- `next/image` для всех изображений — автоматическая оптимизация, lazy loading, responsive
- `React.memo` только после профилирования, не превентивно — чаще добавляет overhead чем помогает
- `useMemo` / `useCallback` только для реально тяжёлых вычислений или референсов в dependency arrays

## Конфигурация и environment

- `.env.local` для локальных dev values
- `.env.production` для production defaults
- Секреты никогда не в `.env*` файлах коммитящихся в git — только `.env.local` (в .gitignore)
- Environment variables типизированы через schema (Zod) и валидируются при старте:

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

## Чистая сборка (clean build)

«Без warnings» из [core/quality-gates.md](../core/quality-gates.md) для этого стека = три зелёных проверки:

~~~bash
npx tsc --noEmit        # strict typecheck без ошибок
npm run lint            # ESLint / next lint без нарушений
npm run build           # next build без warnings
~~~

Тип-ошибка, ESLint-нарушение или warning сборки = задача не завершена. Подавление (`// @ts-ignore`, `eslint-disable`) — только с причиной в комментарии (см. Запреты ниже).

## Запреты

- `any` — кроме type guards
- `// @ts-ignore` без комментария с причиной — use `// @ts-expect-error: reason` если реально нужно
- Inline styles (`style={{ ... }}`) кроме dynamic values которые нельзя выразить через Tailwind
- `dangerouslySetInnerHTML` без санитизации через DOMPurify или аналог
- `localStorage` / `sessionStorage` для sensitive data — только для UI preferences
- Direct DOM manipulation через `document.*` кроме focus management и analogous edge cases
