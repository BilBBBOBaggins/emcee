# B2B SaaS — доменные паттерны

Паттерны и правила которые применяются для B2B SaaS продуктов. Надстройка над [architecture/multi-tenant.md](../architecture/multi-tenant.md).

## Onboarding

B2B onboarding — многоуровневый процесс, не просто регистрация.

Типичная последовательность:

1. **Организация регистрируется** — email первого пользователя, название компании, базовая информация
2. **Первый админ создаёт tenant** — верификация email, выбор tier или trial
3. **Admin приглашает команду** — email invites, роли назначаются
4. **Initial setup** — настройки tenant (branding, integrations, policies)
5. **First value** — первая успешная операция (первый заказ, первая аналитика, первый отчёт)

Каждый шаг измеряется метрикой. Drop-off на шаге — сигнал для улучшения UX.

### Правила онбординга

- **Минимум шагов до первой ценности** — не 15 форм перед показом продукта, а быстрый путь к "wow moment"
- **Skip-friendly** — опциональные шаги можно пропустить и вернуться позже
- **Progress visible** — пользователь видит где он находится в процессе
- **Empty states helpful** — когда tenant пустой, UI показывает что делать, не blank screen
- **Setup wizard отдельно от main UI** — не смешивать onboarding flow с повседневным использованием

### Trial и activation

Для SaaS с trial периодом:

- Trial length — зависит от сложности продукта (7 дней для простых, 14-30 для сложных)
- Clear expiration communication — за 3 дня до конца, в день окончания
- Grace period — несколько дней после expiration на апгрейд без потери данных
- Data retention policy — если не апгрейдили, сколько хранить данные

## Authentication и SSO

### По tier'ам

- **Starter/SMB tier** — email/password + MFA (TOTP)
- **Professional** — добавить Google/Microsoft OAuth
- **Enterprise** — SAML 2.0 / OIDC для SSO с их identity provider + SCIM для user provisioning

### MFA обязателен для админов

Admin role не может существовать без MFA. При попытке повышения роли до admin без MFA — принудительный setup.

### SSO specifics

SAML/OIDC конфигурация per tenant:

- Metadata URL или upload
- Attribute mapping (name, email, roles)
- Domain whitelist — только email'ы с этих доменов auto-provisioned через SSO
- Just-in-time provisioning — user появляется в системе при первом SSO login

### SCIM для enterprise

Автоматическое управление пользователями из external identity provider:

- Provisioning — создание users при добавлении в SSO group
- De-provisioning — deactivation users при удалении из SSO group
- Attribute sync — имена, роли синхронизируются
- SCIM endpoints в API под отдельной auth (bearer token от SCIM client)

## Roles и permissions

### Минимальный RBAC

Для большинства B2B SaaS минимум трёх ролей:

- **Admin** — управляет tenant'ом (users, billing, settings, all data access)
- **Manager** — работает с content (create/edit/delete business entities), но не управляет tenant-level settings
- **User** — базовое использование (view, create в рамках разрешённого)

### Права проверяются на API-уровне

UI скрывает кнопки по ролям, но это не защита — только UX. Реальная проверка — в API handler'ах:

~~~go
func (h *Handler) DeleteOrder(w http.ResponseWriter, r *http.Request) {
    user := UserFromContext(r.Context())
    if !user.HasPermission("orders:delete") {
        http.Error(w, "forbidden", http.StatusForbidden)
        return
    }
    // ...
}
~~~

Никогда не доверять фронтенду. Никогда не проверять права только в UI.

### Attribute-Based Access Control (ABAC)

Для более сложных cases чем RBAC:

- Права зависят от attributes: owner, team, region, tag
- "User может редактировать только свои orders" — это ABAC, не RBAC
- Реализация через policy engine (Casbin, OPA) или inline проверки

### Custom roles

Enterprise tier часто требует custom roles. Структура:

- Permissions — атомарные (`orders:create`, `orders:delete`, `users:invite`)
- Roles — наборы permissions
- System roles — immutable (Admin, User)
- Custom roles — tenant может создавать свои

## Billing

### Subscription tiers

Типичная структура:

- **Free/Trial** — limited usage, time-bounded
- **Starter** — small team, basic features, monthly subscription
- **Professional** — bigger team, advanced features, annual discount
- **Enterprise** — custom pricing, SSO, dedicated support, custom contract

### Usage-based billing

Где применимо (API calls, storage, compute):

- Metered usage tracked per tenant
- Monthly aggregation в invoice
- Overage charges — если usage превысил plan limits
- Transparent dashboard показывающий current usage vs limits

### Proration при апгрейдах

User апгрейдит mid-cycle:

- Старый plan pro-rated refund
- Новый plan pro-rated charge
- Единый invoice с обоими строками

Downgrade обычно — с начала следующего cycle (не refund).

### Payment methods

- **Credit card** — для Starter и Professional, автоматическое списание
- **Invoice (NET 30/60/90)** — для Enterprise, отправляется email, оплата переводом
- **Bank transfer / ACH** — для Enterprise
- **Custom** — какие-то enterprise клиенты имеют non-standard billing terms

### Dunning — обработка failed payments

- Автоматические retry по расписанию (3 дня, 7 дней, 14 дней)
- Email notifications о failed payment
- Grace period до deactivation
- Downgrade to free (если есть) или suspend service
- Win-back flows для churned accounts

## Admin panel

Два уровня админки:

### Tenant admin panel

Для клиентских админов. Scope — только их tenant.

Views:

- **Users** — список, invite, роли, deactivate
- **Usage** — current period, history, trends
- **Billing** — текущий plan, invoice history, payment methods, upgrade
- **Settings** — branding, integrations, security policies
- **Audit log** — действия внутри их tenant

Не видят: других tenants, system-level данных.

### Platform admin (internal)

Для операторов платформы. Scope — все tenants.

Views:

- **Tenants overview** — все tenants, их plans, usage, health
- **Impersonation** — войти в tenant как admin для support (с audit log)
- **Feature flags** — включение features для конкретных tenants
- **System metrics** — infrastructure health, error rates
- **Support queue** — tickets, escalations

Отдельная auth от tenant auth. Сильный audit log — каждое impersonation логируется, уведомление tenant'у.

## Audit log

Все значимые действия логируются.

### Что логируется

- User lifecycle: create, invite, role change, deactivate, delete
- Authentication: login, logout, failed attempts, MFA events
- Authorization: permission grants, revocations
- Data access: read sensitive data, export, bulk download
- Data modification: create, update, delete business entities
- Settings changes: tenant configuration, billing info
- Admin actions: impersonation, feature flag changes

### Структура audit event

~~~go
type AuditEvent struct {
    ID         uuid.UUID
    Timestamp  time.Time
    TenantID   uuid.UUID
    ActorID    uuid.UUID        // кто сделал
    ActorType  string           // user / system / api_key
    Action     string           // "order.deleted"
    Resource   string           // "order:abc-123"
    Changes    map[string]any   // before/after для updates
    IP         string
    UserAgent  string
    Metadata   map[string]any
}
~~~

### Read-only, append-only

Audit log не редактируется и не удаляется. Storage:

- Отдельная таблица/БД с write-only permissions для app, read-only для audit viewer
- Или append-only log (S3 с versioning, cloud-native audit service)
- Export для compliance — возможность выгрузить за период

### Retention

Зависит от compliance requirements. Типично 1-7 лет. Для regulated industries — по нормативам.

## Notifications

### Каналы

- **Email** — для важных событий (billing, security, invites)
- **In-app** — для workflow-событий (task assigned, mention)
- **SMS** — опционально, для critical security events (MFA, suspicious login)
- **Webhooks** — для integration с клиентскими системами
- **Slack/Teams** — для B2B often важнее чем email

### User preferences

Каждый user управляет своими notification preferences:

- Per category (security, billing, workflow, marketing)
- Per channel (email, in-app, SMS)
- Digest vs immediate — некоторые предпочитают batched, некоторые real-time
- Quiet hours — не шлём в нерабочее время (уважая timezone)

### Unsubscribe обязателен

Для marketing/promotional emails — unsubscribe link обязателен по закону (CAN-SPAM, GDPR).
Для transactional emails (billing, security) — unsubscribe не требуется, но preferences должны позволять отключить что-то.

## Customer success

### Product analytics

Tracking:

- **Feature usage** — какие features используются, кем, как часто
- **User engagement** — DAU/MAU, session duration, return rate
- **Adoption metrics** — % users активировавших key features
- **Cohort analysis** — retention по когортам (по месяцу signup)

Tools: Mixpanel, Amplitude, PostHog, или self-hosted equivalents.

### Health scores

Per account indicator "вероятность churn":

- Usage trends (растёт/падает)
- Feature adoption (используют mission-critical features или только basic)
- Support tickets (частота и severity)
- User engagement (все users активны или только один)
- Renewal proximity (how close to contract end)

Low health score — triggers outreach от customer success team.

### Automated alerts

Customer success получает alerts:

- Account не logged in X days
- Usage drop > 30% месяц к месяцу
- Multiple failed payments
- Support ticket с severity "high"
- User count увеличился (upsell opportunity)

## Support

### Ticket system

- Email-to-ticket интеграция
- In-app widget для создания tickets
- Priority levels с response time SLA per tier
- Escalation paths (L1 → L2 → Engineering)

### Response time SLA

По tier'ам:

- Free: best effort
- Starter: 24h business hours
- Professional: 8h business hours
- Enterprise: 1h 24/7 for critical, с явным SLA в контракте

### Knowledge base

- Public help center с articles
- Search по всему контенту
- Video tutorials для complex workflows
- Release notes с screenshots и примерами

### In-app chat

Для paid tiers — live chat:

- Business hours coverage
- После hours — async, response когда команда доступна
- Integration с user context (kto на какой странице, какой tier)

## Data export

Пользователи имеют право экспортировать свои данные. Обязательно по GDPR, хорошая практика везде.

Форматы:

- **CSV** — для табличных данных
- **JSON** — для структурированных данных
- **PDF** — для reports
- **Полный export** — zip со всем в machine-readable формате

UI для экспорта:

- В settings → "Export data"
- Выбор scope (specific data types или всё)
- Email notification когда export готов (для больших exports async job)
- Download link действует ограниченное время

## Terms и contracts

### Click-through для self-serve

- Starter/Professional tier — user accepts ToS при signup
- Text должен быть read-friendly, не юридический wall of text
- Updates — email notification + re-acceptance при significant changes

### MSA для enterprise

- Custom contracts с legal review
- Signed through DocuSign или аналог
- Effective dates, renewal terms, termination clauses
- MSA отдельно от specific services (SOW)

### DPA для GDPR compliance

Data Processing Addendum — отдельный документ:

- Data controller / processor relationship
- Processing purposes
- Sub-processors (третьи стороны к которым уходят данные)
- Data transfer mechanisms (SCC для EU→US)
- Security measures
- Breach notification procedures

Обязателен для EU клиентов, полезен везде.

### Change notifications

При изменении условий ToS/Privacy Policy/Pricing:

- Email всем affected users
- В email — summary изменений + ссылка на full document
- Advance notice — обычно 30 дней для material changes
- Возможность opt-out (для pricing changes — cancellation без penalty)
