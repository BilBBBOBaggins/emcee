# Микросервисы — архитектурный паттерн

Разделение приложения на независимо деплоящиеся сервисы с собственными данными и границами.

Симметричная альтернатива [modular-monolith.md](modular-monolith.md). Выбор между ними — одно из ключевых архитектурных решений проекта.

## Когда выбирать микросервисы

Не превентивно. Только когда есть конкретные причины.

### Triggers для миграции в микросервисы

**Organizational**:

- Несколько команд работают независимо, разные release cadence
- Conway's law — структура организации не матчится с монолитом
- Ownership границы понятнее в коде чем в документации

**Scaling**:

- Один компонент требует специфического scaling (memory-heavy, CPU-heavy, network-heavy)
- Разные компоненты имеют разные latency requirements
- Horizontal scaling нужен только для части системы

**Technology diversity**:

- Разные компоненты требуют разных стеков (ML pipeline на Python, API на Go, real-time на Rust)
- Интеграция с системами работающими только на определённых стеках

**Availability**:

- Компоненты имеют разные SLA требования
- Изоляция failures — failure одного не должна ронять другие

**Compliance**:

- Часть системы обрабатывает данные с особыми регуляторными требованиями (PCI, HIPAA, госданные)
- Физическая изоляция инфраструктуры требуется по compliance

### Когда НЕ выбирать микросервисы

- Команда до 10-15 разработчиков
- MVP фаза, scope меняется быстро
- Нет operational expertise для управления распределённой системой
- Нет observability stack (tracing, metrics, logs aggregation)
- Простота монолита побеждает гибкость микросервисов

Правило: **модульный монолит до появления конкретных triggers**. Не начинать с микросервисов "потому что modern architecture".

## Границы сервисов

### Domain-driven boundaries

Сервис = Bounded Context в терминах DDD:

- Собственный ubiquitous language (термины домена)
- Собственная data model
- Независимый жизненный цикл эволюции
- Минимальные dependencies с другими контекстами

Не "сервис на каждую сущность" (это anti-pattern — слишком chatty коммуникация). Сервис покрывает целостную business capability.

### Определение границ

Процесс:

1. **Event storming** с domain experts — выявление business events, commands, actors
2. Группировка events в **aggregates** — то что изменяется вместе
3. Выделение **bounded contexts** — связанные aggregates с общим языком
4. Каждый bounded context — кандидат на отдельный сервис

### Проверка правильности границ

- Transaction scope — транзакции внутри одного сервиса, не cross-service
- Data ownership — нет shared tables между сервисами
- Temporal coupling — изменение одного не требует синхронного изменения другого
- Autonomy — команда может deploy сервис независимо

Если эти свойства нарушаются — границы неправильные, пересмотреть.

## Коммуникация между сервисами

### Синхронные вызовы

REST API (JSON over HTTP) или gRPC (бинарный протокол с schema).

**REST** — default выбор:

- Простота
- Universal tooling
- Debuggable (читаемый JSON)
- HTTP ecosystem (load balancers, caches)

**gRPC** когда:

- Performance критичен (binary protocol, HTTP/2)
- Нужны streaming RPCs
- Сильная типизация через protobuf
- Internal communication (не browser-facing)

### Асинхронные события

Message broker (Kafka, RabbitMQ, NATS, Redis Streams).

Предпочтительный способ для:

- Событий которые многие сервисы хотят знать (fan-out)
- Долгих workflow (сага pattern)
- Decoupling producers от consumers
- Handling bursts и backpressure

### Anti-patterns коммуникации

**Chatty APIs** — вызов A→B→C→D для одной операции. Latency складывается, failure probability умножается. Решение: агрегировать данные в одном вызове или дублировать read-only reference data.

**Distributed monolith** — сервисы коммуницируют синхронно настолько часто, что фактически это монолит с сетью посередине. Хуже монолита: latency, complexity, failures. Решение: или пересмотреть границы, или вернуться к монолиту.

**Shared database** — два сервиса пишут в одну БД. Нарушает независимость deployments, создаёт скрытые coupling. Решение: database per service.

## Database per service

Каждый сервис — свои данные. Никаких shared tables между сервисами.

### Правила

- Сервис A не читает таблицы сервиса B напрямую. Только через API сервиса B
- Схема БД — internal implementation detail сервиса, может меняться без уведомления других
- Cross-service JOINs — запрещены. Если нужны — либо агрегация на application level, либо event-driven replication

### Data consistency

Без cross-service transactions. Варианты:

**Eventual consistency** через события:

- Сервис A меняет своё состояние
- Публикует событие
- Сервис B подписан, обновляет своё состояние
- Между изменениями есть временной window где состояния расходятся — это OK для большинства случаев

**Saga pattern** для multi-step workflow:

- Разбить transaction на шаги
- Каждый шаг — локальная transaction в одном сервисе
- Compensating actions для rollback
- Orchestrated (central coordinator) или choreographed (через события)

**2-phase commit** — запрещён. Не масштабируется, блокирует, создаёт distributed locks.

## API versioning

Сервисы эволюционируют независимо, consumers — на разных версиях API одновременно.

### Backward compatibility

- Adding fields to response — safe (старые clients игнорируют)
- Adding endpoints — safe
- Adding optional parameters — safe
- Removing fields — breaking change
- Changing field types — breaking change
- Changing semantics — breaking change

При breaking change — новая версия API с параллельной поддержкой старой.

### Versioning strategies

**URL versioning** — `/v1/users`, `/v2/users`. Простой, explicit.

**Header versioning** — `Accept: application/vnd.api.v2+json`. Чище URL, но harder для debugging.

**Content negotiation** — один endpoint, разные response schemas по Accept header. Максимальная гибкость, максимальная сложность.

Для большинства проектов — URL versioning.

### Deprecation process

- Объявление deprecation в docs + headers
- Период параллельной поддержки (минимум 6 месяцев)
- Alerts consumers использующим deprecated
- Ограничение new features только в новой версии
- Final sunset с advance notice

## Service discovery

Как сервис A находит сервис B в runtime.

### DNS-based

Простой случай:

- Каждый сервис — DNS имя в private zone
- Load balancer перед replicas
- Kubernetes делает это из коробки (Services)

### Service mesh

Для более сложных сценариев (Istio, Linkerd, Consul Connect):

- Автоматический service discovery
- Traffic management (retries, timeouts, circuit breaking)
- Mutual TLS между сервисами
- Observability (automatic tracing)

Overhead есть (sidecar proxy на каждый pod), но operational benefits огромны.

### Client-side discovery

Client сам ищет сервис через registry (Consul, Eureka):

- Gives control over load balancing
- Больше code complexity

Менее распространено в современных архитектурах — service mesh покрывает это лучше.

## Observability

Критична для микросервисов. Без неё невозможно отладить распределённую систему.

### Три pillar'а

**Logs** (structured):

- Каждый лог содержит `trace_id` для корреляции между сервисами
- Structured format (JSON) для query в log aggregator
- Централизованный collection (ELK, Loki, Datadog)

**Metrics**:

- RED (Rate, Errors, Duration) для каждого endpoint
- USE (Utilization, Saturation, Errors) для ресурсов
- Custom business metrics
- Prometheus + Grafana или SaaS

**Traces**:

- Distributed tracing (OpenTelemetry) — каждый запрос создаёт trace, spans в каждом сервисе
- Jaeger, Zipkin, Tempo — visualization
- Critical для понимания latency и failures в распределённой системе

### Correlation

Каждый запрос от пользователя → `trace_id` → прокидывается через все сервисы через HTTP headers или message metadata.

В логах и traces этот `trace_id` виден — можно быстро найти все events связанные с конкретным запросом пользователя.

## Resilience patterns

### Timeouts

Каждый cross-service вызов имеет timeout. Без него — cascade failure, сервис ждёт мёртвого dependency.

Типичные timeouts: 1-5 секунд для internal calls, больше для специальных случаев.

### Retries

Automatic retry для transient failures (5xx, timeouts):

- Exponential backoff с jitter
- Максимум 2-3 попытки
- Idempotency — убедиться что операция безопасна для retry

### Circuit breaker

Когда dependency падает — не продолжать бомбить её запросами:

- После N failures за период — "open" circuit
- Health check периодически пробует
- После успехов — "closed" обратно

Libraries: resilience4j (Java), Polly (.NET), gobreaker (Go), tenacity (Python).

### Bulkheads

Изоляция ресурсов — один медленный dependency не должен истощить thread pool всего сервиса:

- Отдельные thread pools для разных dependencies
- Separate connection pools
- Resource limits в K8s (CPU, memory)

### Graceful degradation

Когда dependency недоступен — работать в ограниченном режиме:

- Cache last known value
- Fallback на другой source
- Feature flag отключает функциональность
- User-visible degraded mode, не полный отказ

## Deployment

### Container-based

Стандарт — Docker containers, orchestrated через Kubernetes или аналог.

- Каждый сервис — отдельный image
- CI/CD pipeline per service
- Independent deploys

### CI/CD considerations

- Каждый сервис — свой pipeline
- Contract tests перед deploy — не сломать consumers
- Canary deployment для rollout (5% → 25% → 100%)
- Automatic rollback при regression

### Infrastructure as Code

Инфраструктура описана в коде (Terraform, Pulumi, Crossplane). Не "click-ops" в облачной консоли.

## Data consistency

Compensated actions для multi-service operations.

### Пример саги

Booking сервис хочет создать резерв:

1. Payment service — charge card
2. Inventory service — reserve item
3. Notification service — send confirmation

Если шаг 3 fails:

- Notification — retry
- Нет полного rollback шагов 1 и 2

Если шаг 2 fails:

- Payment service — refund charge (compensating action)

Если шаг 1 fails:

- Stop, user notified

### Choreography vs orchestration

**Choreography** — сервисы подписаны на события друг друга, каждый знает что делать:

- Простая имплементация
- Плохо масштабируется — сложно отследить full workflow
- Логика размазана

**Orchestration** — central coordinator управляет workflow:

- Clear view of full process
- Coordinator — potential bottleneck/SPOF
- Tools: Temporal, AWS Step Functions, Camunda

Для сложных workflows — orchestration. Для простых — choreography.

## Monitoring и alerting

Отдельно от observability (которая для debugging). Alerting — proactive detection проблем.

### Что мониторить

- **Availability** — сервис отвечает (health checks)
- **Latency** — p95, p99 response times
- **Error rate** — 5xx errors per minute
- **Resource usage** — CPU, memory, disk
- **Business metrics** — orders per minute, signups per day

### Alert fatigue

Слишком много alerts — их игнорируют. Правила:

- Alert только на actionable issues
- Severity levels (page vs email vs ignore)
- Alert aggregation — не 100 alerts одновременно
- Runbook для каждого alert — что делать когда срабатывает

## Migration от монолита

Strangler fig pattern:

1. Выбрать bounded context который можно вынести
2. Создать новый сервис с API идентичным внутренним вызовам из монолита
3. Постепенно перенаправлять трафик с внутренних вызовов на API нового сервиса
4. Когда все трафик на сервисе — удалить код из монолита
5. Повторить с следующим контекстом

Не "big bang rewrite" — почти всегда проваливается. Постепенная миграция работает.

## Common pitfalls

### Premature microservicization

Команда прочитала блог-пост и начала пилить монолит на 20 сервисов. Результат: complexity, slow iteration, operational hell. Решение: модульный монолит сначала, микросервисы когда есть triggers.

### Shared libraries hell

Общие libraries используются в многих сервисах. Update library → нужно redeploy все сервисы → теряется independence. Решение: минимизировать shared libraries, версионировать их, accept что разные сервисы на разных версиях.

### Distributed transactions

Попытка воспроизвести ACID transactions across services. Не работает. Решение: eventual consistency, sagas.

### Synchronous chains

A→B→C→D для каждого запроса. Latency складывается. Failure в любом ломает всё. Решение: async events или агрегация данных.

### Missing observability

Когда что-то идёт не так в распределённой системе — impossible дебажить без tracing, structured logs, metrics. Решение: observability infrastructure до первого сервиса в production.
