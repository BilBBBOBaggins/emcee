# День 1 — Пригласить участника по email

**Цель дня:** сквозная фича «пригласить участника в команду по email» — от API до UI, с тестами.

**Предусловие:** проект инициализирован (Go API + Next.js), миграции применяются, `make test` зелёный.

Команды запуска ролей (расшифровка цифр — в [CLAUDE.md](../CLAUDE.example.md)):

- `1 1 1` — developer берёт Задачу 1 (бэкенд).
- `1 1 2` — developer берёт Задачу 2 (фронтенд).
- `0 1 1` — reviewer ревьюит Задачу 1.
- `3 1 2` — BA пишет сценарии для фичи Задачи 2 → файл `scenarios-1-2-…` (назван по фиче, которую описывает; см. конвенцию `<DT>` в [core/task-protocol.md](../../core/task-protocol.md)).
- `4 1 2` — QA UAT превращает сценарии в тест-кейсы → `test-cases-1-2-…`.
- `2 1 2` — QA E2E пишет E2E по тест-кейсам.

---

## Задача 1 — Backend: эндпоинт POST /api/v1/invites

Создать эндпоинт, который заводит приглашение и кладёт его в очередь на отправку письма. Tenant определяется из контекста аутентификации (см. [domain/b2b-saas.md](../../domain/b2b-saas.md), [architecture/multi-tenant.md](../../architecture/multi-tenant.md)).

**Затронутые файлы:**

- `internal/domain/invite.go` (новый) — сущность `Invite`, статусы.
- `internal/service/invite_service.go` (новый) — бизнес-логика создания инвайта.
- `internal/transport/invite_handler.go` (новый) — HTTP-обработчик.
- `internal/repository/queries/invite.sql` (новый) — sqlc-запросы.
- `internal/transport/router.go` (правка) — регистрация маршрута.
- тесты рядом с каждым файлом.

### Промпт для Claude Code

~~~
Реализуй POST /api/v1/invites в Go-проекте по правилам stack/go.md и core/.

Контракт:
- Вход: JSON {"email": string}. Tenant берётся из ctx (middleware уже кладёт tenant_id), НЕ из тела запроса.
- Валидация: email по RFC; пустой/невалидный → 400 с {"error":"invalid email"}.
- Если активный инвайт на этот email в этом tenant уже есть → 409 {"error":"invite already pending"}.
- Успех: создать запись Invite{id, tenant_id, email, status="pending", created_at}, вернуть 201 с телом инвайта.
- Side effect: положить задачу на отправку письма в очередь через InviteService.enqueueEmail (интерфейс, реальная отправка — заглушка-логгер в этой задаче).

Требования:
- Слои: transport → service → repository, обратных импортов нет (core/code-quality.md).
- Ошибки обёрнуты через %w, типизированы (ValidationError, ConflictError).
- sqlc для запросов, никакого inline SQL, prepared statements.
- Unit-тесты на service (валидация, дубль, happy path) и handler (коды ответов). Table-driven.
- Без реальной сети в тестах, таймауты/очередь — через интерфейс с моком.
- LOC-лимиты и «без warnings» (golangci-lint) — core/quality-gates.md.
~~~

### После выполнения

~~~bash
make build && make test 2>&1 | tee /tmp/day1-task1.log
golangci-lint run ./internal/...
~~~

Ожидается: сборка clean, все тесты зелёные, линтер без замечаний. Новые тесты: `TestInviteService_*`, `TestInviteHandler_*`.

### Коммит

~~~bash
git add internal/domain/invite.go internal/service/invite_service.go \
        internal/transport/invite_handler.go internal/transport/router.go \
        internal/repository/queries/invite.sql internal/repository/db/ \
        internal/service/invite_service_test.go internal/transport/invite_handler_test.go
git commit -m "feat(invites): POST /api/v1/invites — create pending invite, enqueue email"
~~~

---

## Задача 2 — Frontend: модалка «Пригласить участника»

Форма приглашения на странице команды: кнопка открывает модалку, ввод email, отправка вызывает API из Задачи 1, обратная связь пользователю.

**Затронутые файлы:**

- `components/features/InviteTeammateModal.tsx` (новый)
- `components/features/InviteButton.tsx` (новый)
- `lib/api/invites.ts` (новый) — типизированный клиент.
- `app/teams/[teamId]/page.tsx` (правка) — встроить кнопку.
- тесты рядом.

### Промпт для Claude Code

~~~
Реализуй UI «Пригласить участника» по правилам stack/react-nextjs.md и core/.

Поведение:
- Кнопка "Invite teammate" (objectName/testid: inviteButton) на странице команды открывает модалку (testid: inviteModal).
- В модалке: поле email (testid: inviteEmailInput), кнопка Send (testid: inviteSubmit), кнопка Cancel (testid: inviteCancel).
- Кнопка Send неактивна пока email пуст или невалиден (клиентская валидация Zod).
- Send → POST /api/v1/invites через lib/api/invites.ts (TanStack Query useMutation).
  - 201 → toast (testid: inviteToast) "Invitation sent to <email>", модалка закрывается, список инвайтов инвалидируется.
  - 409 → инлайн-ошибка под полем (testid: inviteError) "This person already has a pending invite".
  - 400/прочее → инлайн-ошибка "Could not send invite, try again".
- Во время запроса Send показывает спиннер и неактивна (без двойной отправки).

Требования:
- Server/Client Components по правилам; модалка — Client Component.
- Форма: React Hook Form + Zod, схема — source of truth типов.
- Никаких внутренних свойств в UI-тексте; пользователь видит только тексты выше.
- Тесты (Vitest + Testing Library): неактивная кнопка при пустом/невалидном email, успешная отправка вызывает мутацию, 409 показывает инлайн-ошибку. getByRole/getByLabelText, не testid где есть роль.
~~~

### После выполнения

~~~bash
npm run build && npm run test -- --run 2>&1 | tee /tmp/day1-task2.log
npm run lint && npx tsc --noEmit
~~~

Ожидается: typecheck без ошибок, линтер чист, тесты зелёные.

### Коммит

~~~bash
git add components/features/InviteTeammateModal.tsx components/features/InviteButton.tsx \
        lib/api/invites.ts app/teams/\[teamId\]/page.tsx \
        components/features/InviteTeammateModal.test.tsx
git commit -m "feat(invites): invite teammate modal wired to POST /api/v1/invites"
~~~

---

## Задача 3 — BA: сценарии фичи «пригласить»

`3 1 2`. BA читает код Задач 1–2 и пишет пользовательские сценарии по формату [roles/ba.md](../../roles/ba.md).

- **Вход:** код инвайт-фичи (handler, service, модалка).
- **Выход:** `docs/scenarios-1-2-invite-teammate.md` (пример: [scenarios-1-2-invite-teammate.example.md](scenarios-1-2-invite-teammate.example.md)).
- **Референс для сравнения:** Slack / Notion (приглашение в workspace).

---

## Задача 4 — QA UAT: тест-кейсы

`4 1 2`. QA UAT читает `scenarios-1-2-…` и код (за UI-селекторами), пишет формальные тест-кейсы по [roles/qa-uat.md](../../roles/qa-uat.md).

- **Вход:** `docs/scenarios-1-2-invite-teammate.md` + код.
- **Выход:** `docs/test-cases-1-2-invite-teammate.md` (пример: [test-cases-1-2-invite-teammate.example.md](test-cases-1-2-invite-teammate.example.md)).

---

## Задача 5 — QA E2E: автотесты

`2 1 2`. QA E2E переводит тест-кейсы из `test-cases-1-2-…` в E2E по [roles/qa-e2e.md](../../roles/qa-e2e.md): действие через UI → видимый результат → серверная верификация (инвайт реально создан) → UI после ответа сервера.

- **Вход:** `docs/test-cases-1-2-invite-teammate.md`.
- **Выход:** E2E-тесты в контуре `build-qa/` (см. [core/quality-gates.md](../../core/quality-gates.md) — разделение контуров).
