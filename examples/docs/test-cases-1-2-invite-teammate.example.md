# Тест-кейсы: Пригласить участника (День 1, Задача 2)

Автор: QA UAT. Формат — [roles/qa-uat.md](../../roles/qa-uat.md). Источник сценариев: [scenarios-1-2-invite-teammate.example.md](scenarios-1-2-invite-teammate.example.md).
Вход для: QA E2E. Референс: Slack + common sense.

## TC-INVITE-001: Отправка приглашения (happy path)

**Приоритет:** P0 Critical
**Источник:** Сценарий 1.1 из scenarios-1-2-invite-teammate.md
**Автоматизация:** Да

### Предусловие
- Пользователь залогинен, открыта страница своей команды.
- В команде нет инвайта на `newdev@example.com`.

### Шаги

| # | Given (состояние) | When (действие) | Then (ожидание) | UI selector |
|---|-------------------|-----------------|-----------------|-------------|
| 1 | Страница команды | Нажать «Invite teammate» | Модалка открыта, поле email в фокусе и пустое, кнопка Send серая/неактивная | inviteButton, inviteModal, inviteEmailInput, inviteSubmit |
| 2 | Модалка открыта | Ввести `newdev@example.com` | Кнопка Send активна | inviteEmailInput, inviteSubmit |
| 3 | Email введён | Нажать Send | Send показывает спиннер и неактивна; затем toast «Invitation sent to newdev@example.com»; модалка закрывается | inviteSubmit, inviteToast |

### Тестовые данные
- Email: `newdev@example.com`

### Критерий прохождения
- [ ] Toast с точным текстом показан и автоскрылся.
- [ ] Модалка закрыта, фокус вернулся на страницу.
- [ ] **Серверная проверка:** в БД появился `Invite{email:"newdev@example.com", status:"pending"}` в нужном tenant.

## TC-INVITE-002: Валидация email (кнопка Send заблокирована)

**Приоритет:** P1 High
**Источник:** Сценарий 1.2 из scenarios-1-2-invite-teammate.md
**Автоматизация:** Да

### Предусловие
- Модалка приглашения открыта.

### Шаги

| # | Given (состояние) | When (действие) | Then (ожидание) | UI selector |
|---|-------------------|-----------------|-----------------|-------------|
| 1 | Поле email пустое | — | Кнопка Send неактивна | inviteEmailInput, inviteSubmit |
| 2 | Поле email пустое | Ввести `not-an-email` | Кнопка Send остаётся неактивной | inviteEmailInput, inviteSubmit |
| 3 | Невалидный ввод | Исправить на `ok@example.com` | Кнопка Send активируется | inviteEmailInput, inviteSubmit |

### Тестовые данные
- Невалидный: `not-an-email`; валидный: `ok@example.com`

### Критерий прохождения
- [ ] При пустом и невалидном вводе отправка невозможна (никакого запроса к API не уходит).

## TC-INVITE-003: Повторное приглашение (409)

**Приоритет:** P1 High
**Источник:** Сценарий 1.3 из scenarios-1-2-invite-teammate.md
**Автоматизация:** Да

### Предусловие
- На `dup@example.com` в этой команде уже есть pending-инвайт (создать через API в setup).

### Шаги

| # | Given (состояние) | When (действие) | Then (ожидание) | UI selector |
|---|-------------------|-----------------|-----------------|-------------|
| 1 | Модалка открыта | Ввести `dup@example.com`, нажать Send | Модалка не закрывается; под полем инлайн-ошибка «This person already has a pending invite» | inviteEmailInput, inviteSubmit, inviteError |
| 2 | Показана ошибка | Изменить email на `fresh@example.com` | Ошибка исчезает, Send активна | inviteEmailInput, inviteError, inviteSubmit |

### Тестовые данные
- Дубль: `dup@example.com` (pending-инвайт создан в setup); новый: `fresh@example.com`

### Критерий прохождения
- [ ] Дубль не создаёт второй инвайт (серверная проверка: ровно один pending на `dup@example.com`).
- [ ] Сообщение об ошибке видно пользователю и исчезает при исправлении.
