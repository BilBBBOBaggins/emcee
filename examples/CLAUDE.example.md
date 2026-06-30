# Acme Teams

B2B SaaS для управления командами и доступами. Веб-приложение: владелец заводит команду, приглашает участников, управляет ролями и биллингом.

> Это пример заполненного `CLAUDE.md` (все `{{...}}` подставлены, оставлен один testing-вариант). Шаблон — в [../CLAUDE.md](../CLAUDE.md). Ссылки в этом файле ведут на `../` только потому, что пример лежит в `examples/`; в реальном проекте `CLAUDE.md` стоит в корне и ссылки идут на `core/...`, `roles/...` напрямую.

## Стек

- Go 1.23 (бэкенд)
- Echo (HTTP), sqlc, Goose (миграции), slog
- TypeScript 5 (фронтенд)
- Next.js 15 (App Router), shadcn/ui, TanStack Query
- PostgreSQL 16 (RLS для multi-tenancy)
- Make (сборка), golangci-lint
- testify (Go), Vitest + Testing Library + Playwright (фронт)

## Архитектура

Модульный монолит (Go) + Next.js фронт. Решение зафиксировано в [docs/adr/001-modular-monolith.example.md](docs/adr/001-modular-monolith.example.md).

Слои бэкенда (строго соблюдать направление зависимостей):

1. **transport** — HTTP-обработчики, middleware. Знает про service, не знает про БД напрямую.
2. **service** — use cases, бизнес-логика. Знает про repository-интерфейсы.
3. **repository** — доступ к данным (sqlc). Не знает про service/transport.

Правило: transport → service → repository. Обратные импорты запрещены.

## Команды

### Быстрые команды через цифры

- Одно число `N` = архитектор входит в день N. Читает весь проект, выводит статус.
- Два числа `R D` = роль R входит в контекст дня D без конкретной задачи (review или планирование).
- Три числа `R D T` = роль R берёт задачу T из гайда дня D ([docs/day-1-guide.example.md](docs/day-1-guide.example.md)).

Маппинг ролей:

| R | Роль | Файл роли |
|---|------|-----------|
| 0 | Reviewer | [../roles/reviewer.md](../roles/reviewer.md) |
| 1 | Developer | [../roles/developer.md](../roles/developer.md) |
| 2 | QA E2E | [../roles/qa-e2e.md](../roles/qa-e2e.md) |
| 3 | Business Analyst | [../roles/ba.md](../roles/ba.md) |
| 4 | QA UAT | [../roles/qa-uat.md](../roles/qa-uat.md) |
| 5 | System Analyst | [../roles/sa.md](../roles/sa.md) |
| 6 | Debugger | [../roles/debugger.md](../roles/debugger.md) |
| 7 | DevOps | [../roles/devops.md](../roles/devops.md) |

Карта цифр — единственный источник истины. Гайды дня и прочие артефакты — по конвенции из [../core/task-protocol.md](../core/task-protocol.md).

### Сборка и тесты

Сборка:

~~~bash
make build
~~~

Все тесты:

~~~bash
make test
~~~

Быстрый прогон конкретного теста:

~~~bash
go test ./internal/service/ -run TestInviteService_Create
npm run test -- --run InviteTeammateModal
~~~

## Обязательно читать в начале каждой сессии

- [../core/principles.md](../core/principles.md) — базовые принципы работы агента
- [../core/task-protocol.md](../core/task-protocol.md) — как агент понимает задачи + имена артефактов
- [../core/quality-gates.md](../core/quality-gates.md) — критерии завершённости задачи

## По ситуации

- Дебаг чего-то сломанного → [../core/debugging.md](../core/debugging.md)
- Вопросы о качестве кода → [../core/code-quality.md](../core/code-quality.md)
- Бэкенд-стек → [../stack/go.md](../stack/go.md)
- Фронтенд-стек → [../stack/react-nextjs.md](../stack/react-nextjs.md)
- Композиция → [../architecture/modular-monolith.md](../architecture/modular-monolith.md), изоляция данных → [../architecture/multi-tenant.md](../architecture/multi-tenant.md)
- Домен → [../domain/b2b-saas.md](../domain/b2b-saas.md)

## Testing philosophy

### Outside-in BDD (для B2B с domain expertise)

Pipeline формирования тестов и кода:

1. SA/BA формирует acceptance criteria на языке домена (Given/When/Then).
2. QA UAT превращает criteria в формальные тест-кейсы с ожидаемым видимым поведением.
3. QA E2E или Developer пишет код тестов.
4. Developer реализует код чтобы тесты проходили.

Тесты — **спецификация**, не проверка. Тест красный = баг в коде (или неполная имплементация), не проблема теста.

Пример сквозной связки для фичи «пригласить участника»: spec → scenarios → test-cases → код — см. [docs/](docs/).

## Специфика проекта

- **Бизнес-контекст:** ранний B2B SaaS, MVP. Activation завязан на onboarding (пригласить команду).
- **Team setup:** 1–2 человека; роли исполняются через переключение Claude Code по цифрам.
- **Внешние зависимости:** email-провайдер ещё не выбран (см. PROJECT-STATE → open questions); сейчас отправка письма — заглушка-логгер.
- **Текущий статус:** [docs/PROJECT-STATE.example.md](docs/PROJECT-STATE.example.md).
- **Критические запреты:** tenant определяется только из auth-контекста, никогда из тела запроса; ПД (email) не пишутся в логи в открытом виде.

## Эволюция этого документа

Живой документ. Правило добавляется когда агент делает ошибку, которую можно предотвратить формализацией; удаляется когда оно over-specialized под ушедший контекст. Раз в 1–3 месяца — review.
