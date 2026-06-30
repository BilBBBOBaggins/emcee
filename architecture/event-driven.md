# Event-Driven Architecture — архитектурный паттерн

Компоненты общаются через события, не через прямые вызовы. Используется для decoupling, async workflows, scalability.

Применимо для: систем с asynchronous workflows, интеграций между модулями/сервисами, real-time обновлений, audit требований.

## Базовый принцип

Вместо:

~~~
ServiceA.doSomething() → ServiceB.handleIt() → ServiceC.notify()
~~~

(синхронная цепочка вызовов — tight coupling)

~~~
ServiceA publishes event X
    ↓
Event bus
    ├→ ServiceB subscribed to X, handles
    ├→ ServiceC subscribed to X, handles
    └→ ServiceD subscribed to X, handles
~~~

(async, decoupled — publisher не знает consumers)

## Когда применять

### Хорошо подходит

- **Workflow с несколькими reactions на одно событие** — user signed up triggers: send email, create workspace, start trial, notify admin
- **Audit trail** — каждое изменение — событие, storage всех событий = audit log
- **Integration между системами** — published events consumed любыми заинтересованными системами
- **Real-time updates** — events broadcast to UI clients
- **Temporal decoupling** — publisher и consumer могут работать в разное время (queue buffers events)

### Плохо подходит

- **Simple request-response** — если нужен synchronous ответ, events добавляют complexity
- **Strong consistency требования** — events → eventual consistency, не ACID
- **Малые проекты с одной командой** — overhead setup может не окупиться
- **Low-latency operations** — async по definition добавляет latency

## In-process event bus vs external message broker

### In-process event bus

Events внутри одного приложения — publishers и subscribers в том же процессе.

~~~go
type EventBus interface {
    Publish(event Event)
    Subscribe(eventType string, handler EventHandler)
}

// Publisher
bus.Publish(OrderCreated{OrderID: id})

// Subscriber в том же процессе
bus.Subscribe("OrderCreated", func(e Event) {
    // handle
})
~~~

Применение: модульный монолит — см. [modular-monolith.md](modular-monolith.md). Events — способ коммуникации между модулями без tight coupling.

Плюсы: простота (in-memory), типизированные events, низкая latency.

Минусы: не переживает restart (events in memory), не работает cross-process.

### External message broker

Events через отдельный middleware: Kafka, RabbitMQ, NATS, Redis Streams, SQS.

~~~go
// Publisher
broker.Publish("order-events", orderCreated)

// Subscriber в другом процессе
broker.Subscribe("order-events", "notification-service", handler)
~~~

Применение: микросервисы, cross-process workflows, durable event storage.

Плюсы: durability, replay capability, cross-service, scalability.

Минусы: operational complexity (брокер — отдельный компонент), latency выше.

## Event structure

### Анатомия события

Минимум:

~~~json
{
  "event_id": "evt_abc123",
  "event_type": "OrderCreated",
  "timestamp": "2026-04-18T14:30:00Z",
  "version": "1.0",
  "data": {
    "order_id": "ord_456",
    "user_id": "usr_789",
    "amount": 1000
  }
}
~~~

- **event_id** — unique, для deduplication
- **event_type** — тип, для routing
- **timestamp** — когда произошло (не когда опубликовано)
- **version** — schema версия
- **data** — полезная нагрузка

### Метаданные (опционально)

~~~json
{
  "metadata": {
    "trace_id": "trace_xyz",
    "causation_id": "evt_previous",
    "correlation_id": "corr_saga_1",
    "actor": "usr_789",
    "source": "order-service"
  }
}
~~~

- **trace_id** — для distributed tracing
- **causation_id** — какое событие вызвало это
- **correlation_id** — группирует связанные events (saga workflow)
- **actor** — кто инициировал
- **source** — какой сервис опубликовал

### Именование событий

- **Past tense** — event описывает что уже произошло (`OrderCreated`, `PaymentProcessed`), не `CreateOrder`, `ProcessPayment`
- **Domain language** — используй термины домена, не технические (`OrderShipped` vs `OrderStatusUpdated`)
- **Specific** — `OrderCancelled` лучше чем `OrderUpdated` (last requires inspection)

## Schemas и versioning

### Schema evolution

Events живут долго (в audit log, в archived queues). Schema должна эволюционировать backward compatibly.

Правила совместимости:

- **Adding optional fields** — safe
- **Removing fields** — breaking, требует нового version
- **Changing field types** — breaking
- **Renaming fields** — breaking, сначала add new и deprecate old

Schema registry (Confluent Schema Registry, AWS Glue Schema Registry) помогает управлять schemas.

### Version в events

Событие содержит version schema. Consumer знает как parsing в зависимости от version:

~~~json
{
  "event_type": "OrderCreated",
  "version": "2.0",  // v1 had different structure
  ...
}
~~~

### Backward compatibility

Consumer должен обрабатывать как минимум current и previous version. Ideally — все version since last major breaking change.

## Patterns

### Event notification

Простейший паттерн — событие сообщает "X произошло", consumer reacts:

~~~
UserRegistered event
    ↓
EmailService — sends welcome email
~~~

Data в событии минимальна — только identifier. Consumer fetches details если нужно.

### Event-carried state transfer

Событие содержит всё state необходимое consumer:

~~~json
{
  "event_type": "UserProfileUpdated",
  "data": {
    "user_id": "...",
    "name": "...",
    "email": "...",
    "preferences": {...}
  }
}
~~~

Consumer не нужно делать callback к publisher — state приходит в событии.

Плюсы: consumer независим от publisher availability.

Минусы: события больше, дублирование данных.

### Event sourcing

Источник правды — последовательность событий. Current state — projection из событий.

~~~
Events: OrderCreated → ItemAdded → ItemAdded → OrderPaid → OrderShipped
    ↓
Projection: Order current state
~~~

Подходит для: financial systems (всё должно быть traceable), audit-heavy domains, systems где полная история value.

Не подходит для: простых CRUD, систем где current state достаточен.

Complexity существенный — event sourcing это big commitment.

### CQRS (Command-Query Responsibility Segregation)

Разделение write-side (commands изменяющие state) от read-side (queries читающие state):

~~~
Commands → Write Model → Events → Read Models (denormalized for queries)
~~~

Часто используется с event sourcing, но не обязательно.

Плюсы: scaling read и write независимо, optimized data models для разных use cases.

Минусы: complexity, eventual consistency между write и read sides.

### Saga pattern

Distributed transaction через последовательность местных transactions и compensating actions.

~~~
Step 1: OrderCreated — reserves inventory
Step 2: PaymentProcessed — charges customer
Step 3: ShipmentInitiated — sends to fulfillment

Failure в шаге 3:
Compensate step 2 — refund payment
Compensate step 1 — release inventory
~~~

Два стиля:

- **Choreography** — каждый сервис подписан на события предыдущего шага
- **Orchestration** — central coordinator управляет saga

Детали — см. [microservices.md](microservices.md).

## Consumer patterns

### At-least-once delivery

Broker гарантирует что событие доставится хотя бы раз. Возможны дубликаты.

Consumer должен быть idempotent — повторная обработка того же события не меняет результат.

Типичная имплементация:

- Consumer сохраняет `processed_event_ids` с TTL
- При получении события проверяет — уже обработано?
- Если да — ack и skip
- Если нет — process, потом записать в processed, потом ack

### At-most-once delivery

Broker не гарантирует delivery. Возможна потеря.

Redко используется — только когда loss приемлемо (metrics, non-critical notifications).

### Exactly-once delivery

Гарантия что событие обработано ровно один раз. Требует transactional messaging (Kafka transactions, RabbitMQ transactions).

Complexity высокая, performance impact есть. Используется когда идемпотентность невозможна.

### Consumer groups

Несколько instance сервиса читают из одного topic, каждое событие обрабатывается одним instance:

~~~
Topic: order-events
    ├→ Consumer group: notification-service
    │   ├── instance 1 (handles partition 1)
    │   ├── instance 2 (handles partition 2)
    │   └── instance 3 (handles partition 3)
    └→ Consumer group: analytics-service
        └── instance 1 (handles all partitions)
~~~

Horizontal scaling — больше instances в group = больше throughput.

## Observability

### Events как trace points

Каждое событие — natural checkpoint в workflow. Tracing через trace_id в метаданных:

- Publisher добавляет trace_id в событие
- Consumer продолжает trace
- End-to-end visibility для всей saga

### Dead letter queue

События которые не удалось обработать после N retries — в dead letter queue:

- Не блокируют основной queue
- Manual inspection позже
- Retry mechanism после fix

### Monitoring

Ключевые metrics:

- **Throughput** — events per second (publisher, consumer)
- **Lag** — насколько consumer отстаёт от publisher
- **Error rate** — % событий в dead letter queue
- **Processing time** — p95, p99 обработки consumer

## Common pitfalls

### Event spam

Публикация каждого мелкого изменения — events become noise, consumers overloaded.

Решение: events на granularity domain-significant changes, не implementation details.

### Breaking schema changes

Удаление или переименование поля без version bump — ломает consumers.

Решение: schema registry, backward compatibility rules, explicit versioning.

### Missing event store

Events теряются при restart broker. Невозможно replay или audit.

Решение: durable storage (Kafka с retention), event store (EventStore DB), database-backed events.

### Sync thinking in async system

Trying to request-response через events — "publish event and wait for response":

~~~
❌ BAD: publish, wait for reply (blocks)
✅ GOOD: publish and continue, handle response event later
~~~

Event-driven требует mental shift к async.

### Tight coupling через shared schemas

Publisher и всех consumers strongly typed to same schema. Changing schema — деплой всех одновременно.

Решение: consumer-side взаимодействует через projection/view, tolerant reader pattern (игнорирует unknown fields).

### No ordering guarantees

Events могут приходить не в том порядке в котором опубликованы (особенно cross-partition).

Решение: включай ordering concerns в design — sequence numbers, timestamps, causation chain.

### Event as API

Events становятся частью API contract. Все subscribers depend on schema.

Treated accordingly — versioning, documentation, deprecation process.

## Хранение событий

### Ephemeral (queue)

События в queue до consumption, потом удаляются (RabbitMQ default, SQS).

Подходит для: task queues, temporary notifications.

### Retained (log-based)

События хранятся в log на заданное время (Kafka, Kinesis).

Позволяет:

- Replay события с определённого момента
- Новые consumers получают historical events
- Audit trail
- Debug через replay

### Event store

Специализированная БД для событий (EventStore DB, custom БД):

- Guaranteed ordering
- Efficient append
- Replay capabilities
- Subscriptions

Для event sourcing.

## Миграция к event-driven

Существующая система без events — постепенный переход:

### Strangler fig

1. Identify workflow для migration
2. Add event publishing в существующий sync код
3. Create consumer реализующий integration
4. Validate parity
5. Switch sync call на event-driven
6. Repeat для следующих workflows

### Dual-write pattern

Temporarily — и sync call, и event publishing:

- Helps validate event-driven version
- Provides rollback option
- Remove sync call после confidence

### Parallel runs

Run both old и new paths в parallel, compare results, only switch когда consistent.
