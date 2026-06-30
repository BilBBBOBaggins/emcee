# Регулируемый домен — compliance-требования

Для проектов работающих с регулируемыми данными: ПД, медицинские данные, финансы, госданные, тендерные документы.

Файл содержит общие принципы + специфику для РФ (ФЗ-152, 44-ФЗ, 223-ФЗ).

## Применимые законы и регуляции

### Российская Федерация

- **ФЗ-152 "О персональных данных"** — обработка ПД российских граждан
- **ФЗ-149 "Об информации, информационных технологиях и о защите информации"** — общие требования к информационным системам
- **44-ФЗ** — госзакупки для государственных и муниципальных нужд
- **223-ФЗ** — закупки отдельными видами юридических лиц (госкомпании, естественные монополии)
- **275-ФЗ** — гособоронзаказ (если применимо)
- **Требования ФСТЭК** — если система обрабатывает ИСПДн определённого уровня защиты

### International

- **GDPR** — для EU-клиентов или EU-residents' данных
- **CCPA/CPRA** — California Consumer Privacy Act для California residents
- **HIPAA** — US health data (не применимо без явного scope)
- **SOC 2** — certification для B2B SaaS обрабатывающих customer data

## Data residency

### Требование

ПД российских граждан хранятся и обрабатываются на серверах на территории РФ. Это жёсткое требование ФЗ-152, не рекомендация.

Архитектурные следствия:

- Отдельная БД или отдельный инстанс для российских пользователей
- Нельзя хранить ПД российских граждан в US/EU cloud regions
- CDN и static hosting — можно глобально, но с требованием отсутствия ПД
- Backup — тоже в РФ

### Реализация

Варианты по убыванию compliance:

1. **Полностью РФ** — сервера в российском data center, российские облачные провайдеры (Yandex Cloud, VK Cloud, Selectel). Простая история, но ограниченный выбор провайдеров
2. **Hybrid** — основная обработка в РФ, вспомогательные сервисы (email delivery, file storage без ПД) global. Сложнее но более гибко
3. **Sovereignty-aware globally distributed** — глобальная архитектура с data locality. Complex, для больших компаний

Для тендерного продукта (и большинства российских B2B SaaS) — вариант (1) самый практичный.

### Cross-border transfer

Если трансграничная передача нужна — требуется:

- Нотификация Роскомнадзора о трансграничной передаче
- Адекватный уровень защиты в стране-получателе (белый список) или согласие субъекта ПД
- Трансфер мехнизмы (SCC для EU, явное согласие пользователя)

Без этих мер cross-border transfer ПД — нарушение.

## Классификация данных

Каждое поле в БД классифицируется и эта классификация влияет на хранение, доступ, логирование.

### Уровни классификации

- **Public** — открытые данные, не требуют защиты (каталог продуктов, публичные профили)
- **Internal** — внутренние бизнес-данные, не ПД, но коммерческая ценность (метрики, конфигурации)
- **Personal (ПД)** — персональные данные субъекта (ФИО, email, телефон, адрес)
- **Sensitive Personal (ЧСПДн)** — специальные категории ПД (здоровье, национальность, политические взгляды, биометрия)
- **Confidential Business** — коммерческая тайна (контракты, финансы tenants, proprietary algorithms)

### Маркировка в схеме БД

Через комментарии к колонкам или внешнюю конфигурацию:

~~~sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,  -- classification: personal
    full_name VARCHAR(255),        -- classification: personal
    tax_id VARCHAR(20),            -- classification: sensitive_personal
    created_at TIMESTAMPTZ
);
~~~

Или через отдельную таблицу metadata:

~~~sql
CREATE TABLE data_classification (
    table_name VARCHAR(64),
    column_name VARCHAR(64),
    classification VARCHAR(32),
    notes TEXT,
    PRIMARY KEY (table_name, column_name)
);
~~~

### Правила доступа по классам

- Public — доступ без ограничений
- Internal — only authenticated users of tenant
- Personal — only users с permission, audit log on access
- Sensitive Personal — только специфичные permissions, mandatory audit log, возможно approval workflow
- Confidential Business — compartmentalized access, strong audit

## Минимизация данных

Принцип: собираем только то что нужно для функции. Не "на всякий случай", не "может пригодиться".

Правила:

- Каждое поле в форме регистрации/настроек — обосновано конкретным use case
- Нет полей "прочая информация", "комментарии" без чёткого purpose
- Регулярный review полей (раз в полгода-год) — remove obsolete поля
- Privacy Impact Assessment при добавлении новых полей с ПД

Прямое следствие — при сомнении "добавить поле или нет" — не добавлять. Лучше потом добавить когда use case появится, чем собирать данные которые не используются.

## Encryption

### At-rest

- Database storage encrypted на уровне диска/storage (LUKS, cloud provider encryption)
- Для чувствительных полей — application-level encryption поверх database encryption
- Application-level encryption обязательна для:
  - Паролей (bcrypt/argon2, не reversible encryption)
  - API keys и tokens (AES-256-GCM с ключом из KMS)
  - Financial data (card numbers — PCI-DSS tokenization)
  - Biometric data

### In-transit

- TLS 1.2+ для всех сетевых соединений
- TLS 1.3 предпочтительно
- Internal services тоже TLS (mTLS для production environments)
- Certificate validation обязательна, не disable

### Key management

- Ключи никогда не в коде, не в config файлах, не в environment variables коммитящихся
- Использование KMS (AWS KMS, Vault, Yandex KMS)
- Automated rotation по расписанию (90 дней для short-lived, yearly для long-lived)
- Revocation процесс для compromised keys

## Audit log для compliance

Отдельно от general audit (см. [b2b-saas.md](b2b-saas.md)). Для regulated data — более строгие требования.

### Что логируется

Для каждого доступа к ПД или Sensitive data:

- Кто (authenticated user ID, service account, system)
- Когда (timestamp с millisecond precision)
- Что (какая запись, какое поле)
- Зачем (purpose — часть request context)
- Result (success/denied, какие данные возвращены)

### Immutability

Audit log не редактируется и не удаляется. Реализация:

- Append-only storage (write-once, read-many)
- Cryptographic hash chain (каждая запись содержит hash предыдущей) — tampering detection
- Или blockchain-like approach если критично
- Или отдельная БД с IAM политиками запрещающими update/delete

### Retention

Зависит от регуляции. Типично:

- ФЗ-152: 3 года после прекращения обработки
- GDPR: отдельное DPIA для каждого processing activity
- SOC 2: обычно 7 лет
- Финансовые регуляторы: 5-10 лет

Retention автоматический — old entries не удаляются вручную, политика в storage.

## User rights (права субъекта ПД)

### Access

Пользователь имеет право получить копию своих данных:

- Полный export всех данных в machine-readable формате (JSON, CSV)
- Включая метаданные (когда создано, кем, откуда)
- Обработка запроса — в течение 30 дней (ФЗ-152) или 30 дней (GDPR)
- Free — нельзя брать деньги за первый запрос в период

### Rectification

Право на исправление неточных данных:

- UI для самостоятельного редактирования где возможно
- Для полей которые user не может редактировать (verified name, например) — процесс через support с ID verification

### Erasure / Right to be forgotten

Право на удаление (с ограничениями):

- User инициирует запрос
- System удаляет ПД из production БД
- Cascading delete — все связанные данные (logs, analytics)
- **Ограничения**:
  - Данные необходимые для legal compliance (billing records, audit logs) сохраняются с обоснованием
  - Anonymization вместо deletion — acceptable в некоторых cases
  - Контрактные обязательства могут требовать сохранения

Processing time — 30 дней максимум.

### Portability

Право получить данные в формате позволяющем передать другому provider:

- Structured machine-readable format
- Industry standards где возможно (iCalendar для календарей, vCard для контактов)

### Withdrawal of consent

Право отозвать согласие на обработку:

- UI для отзыва — по категориям (marketing, analytics, etc.)
- Withdrawal → prompt остановка processing
- Withdrawal не касается обработки на других legal basis (contract performance, legal obligation)

## Согласие на обработку ПД

### Фиксация согласия

- Записывается event "consent given" с:
  - User ID
  - Timestamp
  - Версия текста согласия (важно!)
  - IP адрес
  - Какие purposes (cannot be bundled — separate consent для каждой цели)
- Хранится минимум столько же сколько ПД

### Versioning текста

- Каждая версия consent text — отдельная запись
- При изменении text — новая версия, users должны re-consent
- Grandfather clause — old users остаются на old version если не было material change

### Granularity

Отдельные консенты для разных purposes:

- Product functionality (обязательно, contract basis)
- Marketing emails (separate, optional)
- Product analytics (separate, optional или legitimate interest)
- Third-party sharing (separate, explicit, по каждому третьему лицу)

Не bundling "я согласен со всем".

### Withdrawal

- Должно быть так же легко как и consent given
- Один клик где возможно
- Не требует contacting support

## Инциденты и breach notification

### Incident response plan

Documented procedure:

1. **Detection** — monitoring triggers alert
2. **Assessment** — что произошло, что скомпрометировано, кто затронут
3. **Containment** — остановить дальнейший ущерб
4. **Investigation** — root cause, scope
5. **Notification** — регулятор + затронутые users
6. **Remediation** — fix vulnerability, prevent recurrence
7. **Post-mortem** — lessons learned, process improvements

### Notification timelines

Сроки уведомления регулятора:

- **GDPR**: 72 часа с момента awareness
- **ФЗ-152**: ФЗ не устанавливает точный срок, но "без неоправданной задержки" — обычно 72 часа как best practice
- **SOC 2**: по контракту с клиентами, обычно 24-72 часа

Сроки уведомления пользователей:

- **GDPR**: без неоправданной задержки, если high risk
- **ФЗ-152**: аналогично
- **Форма**: email + in-app + возможно SMS для critical

### Документирование

Breach log с каждым инцидентом:

- Dates (detection, containment, notification)
- Scope (records affected, data types, users)
- Root cause
- Remediation steps
- Communication log

Для regulator audits.

## Третьи стороны

### Data Processing Agreements (DPA)

Любая третья сторона получающая доступ к данным — DPA:

- Processing purposes
- Types of data
- Duration
- Security measures
- Sub-processors (если они используют других)
- Return/deletion of data after contract

### Список sub-processors

Публичный список (на сайте или в DPA) всех третьих сторон:

- Name, jurisdiction
- Purpose (что делают с данными)
- Data types
- Location of processing

При изменении списка — notification клиентам, often с opportunity to object.

### Due diligence

Перед использованием третьей стороны:

- Security assessment
- Compliance certifications (SOC 2, ISO 27001)
- References
- Contract review legal team

## Специфика тендеров (44-ФЗ / 223-ФЗ)

Если продукт связан с тендерной системой:

### Публичность данных

- Тендерная документация на ЕИС — **публичная**, не ПД
- Профили участников (юр.лица) — **публичные** через ЕГРЮЛ/ЕГРИП
- Контактные лица юр.лиц — **гибридный** case, обычно публичные но с nuances

### Коммерческая тайна клиентов

Внутренние данные клиентов продукта:

- Их собственные analytics по тендерам (winrate, pricing strategies) — коммерческая тайна
- Их custom setup и preferences — коммерческая тайна
- Их выигранные контракты — могут быть public, но аналитика — их

Разделение этих категорий критично в архитектуре данных.

### Интеграция с ЕИС

API ЕИС для получения тендеров:

- API публичные, rate-limited
- Некоторые данные требуют регистрации как user
- Определённые operations требуют ЭЦП (electronic signature)
- Для разработки — sandbox environment

### Audit trail для контрактов

Если продукт помогает готовить заявки и контракты:

- Полная история изменений каждого документа
- Electronic signature integration где требуется
- Retention требования согласно 44-ФЗ

## Secrets и ключи

### Политика хранения

- API keys клиентов — **application-level encrypted**, никогда plaintext
- Secrets окружения — в secrets manager (Vault, AWS Secrets Manager, Yandex Lockbox)
- Нет secrets в:
  - Git history
  - Docker images
  - Config files которые коммитятся
  - Environment files на shared filesystems

### Rotation по расписанию

- Database passwords — rotate monthly or on incident
- API keys — expirable с automatic rotation
- Signing keys (JWT) — rotation + overlap period для graceful transition
- TLS certificates — automated renewal (Let's Encrypt, ACM)

### Audit access to secrets

- Каждый access к secret логируется
- Usage patterns monitored — unusual access triggers alert
- Service accounts — минимальные permissions, short-lived credentials where possible

### Revocation процесс

При компрометации:

- Немедленная revocation скомпрометированного secret
- Генерация нового
- Rolling deployment с новым secret (по возможности without downtime)
- Rotate связанных secrets если lateral movement возможно
- Post-mortem — как произошло, как предотвратить

### Git history compromise

Если secret попал в git history:

- Rotate immediately
- Rewrite history (git filter-branch или BFG Repo-Cleaner)
- Force push (с координацией с командой)
- Notify всех с репо чтобы re-clone
- Add pre-commit hook (detect-secrets или аналог) чтобы предотвратить повторение
