# Feature: Пригласить участника по email

Status: approved
Owner: SA
Related ADRs: [ADR-001](../adr/001-modular-monolith.example.md)
Last updated: 2026-04-17

Формат — [roles/sa.md](../../../roles/sa.md). Это вход для architect (тех. спецификация) и developer (acceptance criteria).

## Context

Чтобы команда начала пользоваться продуктом, владелец должен пригласить коллег. Без приглашений продукт мёртв на старте onboarding (см. [domain/b2b-saas.md](../../../domain/b2b-saas.md) — onboarding/activation). Первый шаг: отправка приглашения; приём инвайта — отдельная фича (День 2).

## Users and use cases

Primary users:
- **Team owner / admin**: приглашает коллег по email, видит подтверждение отправки.

Secondary users (affected but not primary):
- **Приглашённый**: получает письмо (приём — вне scope этой spec).

## User stories

### Story 1: Отправить приглашение

As a team admin,
I want to invite a teammate by email,
So that they can join my team without me sharing credentials.

**Priority**: P0
**Estimate**: M

Acceptance criteria:

1. **Scenario: Успешная отправка**
   Given я админ команды и открыл форму приглашения
   When я ввожу валидный email и нажимаю Send
   Then создаётся pending-инвайт в моём tenant
   And я вижу подтверждение «Invitation sent to <email>».

2. **Scenario: Повторное приглашение**
   Given на этот email уже есть pending-инвайт в моей команде
   When я пытаюсь пригласить его снова
   Then система не создаёт второй инвайт
   And я вижу «This person already has a pending invite».

3. **Scenario: Невалидный email**
   Given форма приглашения открыта
   When email пуст или невалиден
   Then отправка заблокирована (кнопка Send неактивна).

## Non-functional requirements

- **Security:** email из тела запроса не определяет tenant — tenant строго из auth-контекста (изоляция, [architecture/multi-tenant.md](../../../architecture/multi-tenant.md)).
- **Performance:** ответ API < 300 ms; отправка письма асинхронна (очередь), не блокирует ответ.
- **Compliance:** email — ПД, в логи не писать в открытом виде ([core/code-quality.md](../../../core/code-quality.md), [domain/regulated.md](../../../domain/regulated.md) если применимо).

## Data model changes

Новая сущность `invites`: `id`, `tenant_id`, `email`, `status` (pending|accepted|revoked|expired), `created_at`. Уникальность: один активный (pending) инвайт на (`tenant_id`, `email`).

## Open questions

- [ ] Email-провайдер (SES / Postmark / SMTP)? — блокер реальной отправки, нужно решение пользователя.
- [ ] Лимит pending-инвайтов на tenant и срок жизни инвайта? — уточнить у domain expert.

## Assumptions

- We assume auth-middleware уже кладёт `tenant_id` в контекст. Verified: реализовано в каркасе (PROJECT-STATE).
- We assume приём инвайта делается отдельной фичей. If wrong — расширить scope на День 1.

## Out of scope

- Приём приглашения по токену из письма (День 2).
- Bulk-инвайты, инвайт по ссылке, роли при приглашении.
