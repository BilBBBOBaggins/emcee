# Event-Driven Architecture — architectural pattern

Components communicate through events, not direct calls. Used for decoupling, async workflows, scalability.

Applicable to: systems with asynchronous workflows, integrations between modules/services, real-time updates, audit requirements.

## Basic principle

Instead of:

~~~
ServiceA.doSomething() → ServiceB.handleIt() → ServiceC.notify()
~~~

(synchronous call chain — tight coupling)

~~~
ServiceA publishes event X
    ↓
Event bus
    ├→ ServiceB subscribed to X, handles
    ├→ ServiceC subscribed to X, handles
    └→ ServiceD subscribed to X, handles
~~~

(async, decoupled — publisher doesn't know consumers)

## When to apply

### Good fit

- **Workflow with multiple reactions to one event** — user signed up triggers: send email, create workspace, start trial, notify admin
- **Audit trail** — every change is an event, storage of all events = audit log
- **Integration between systems** — published events consumed by any interested systems
- **Real-time updates** — events broadcast to UI clients
- **Temporal decoupling** — publisher and consumer can operate at different times (queue buffers events)

### Poor fit

- **Simple request-response** — if a synchronous response is needed, events add complexity
- **Strong consistency requirements** — events → eventual consistency, not ACID
- **Small projects with a single team** — setup overhead may not pay off
- **Low-latency operations** — async by definition adds latency

## In-process event bus vs external message broker

### In-process event bus

Events within a single application — publishers and subscribers in the same process.

~~~go
type EventBus interface {
    Publish(event Event)
    Subscribe(eventType string, handler EventHandler)
}

// Publisher
bus.Publish(OrderCreated{OrderID: id})

// Subscriber in the same process
bus.Subscribe("OrderCreated", func(e Event) {
    // handle
})
~~~

Application: modular monolith — see [modular-monolith.md](modular-monolith.md). Events are a way to communicate between modules without tight coupling.

Pros: simplicity (in-memory), typed events, low latency.

Cons: doesn't survive restart (events in memory), doesn't work cross-process.

### External message broker

Events through a separate middleware: Kafka, RabbitMQ, NATS, Redis Streams, SQS.

~~~go
// Publisher
broker.Publish("order-events", orderCreated)

// Subscriber in another process
broker.Subscribe("order-events", "notification-service", handler)
~~~

Application: microservices, cross-process workflows, durable event storage.

Pros: durability, replay capability, cross-service, scalability.

Cons: operational complexity (the broker is a separate component), higher latency.

## Event structure

### Anatomy of an event

Minimum:

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

- **event_id** — unique, for deduplication
- **event_type** — type, for routing
- **timestamp** — when it happened (not when it was published)
- **version** — schema version
- **data** — payload

### Metadata (optional)

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

- **trace_id** — for distributed tracing
- **causation_id** — which event caused this one
- **correlation_id** — groups related events (saga workflow)
- **actor** — who initiated it
- **source** — which service published it

### Event naming

- **Past tense** — an event describes what already happened (`OrderCreated`, `PaymentProcessed`), not `CreateOrder`, `ProcessPayment`
- **Domain language** — use domain terms, not technical ones (`OrderShipped` vs `OrderStatusUpdated`)
- **Specific** — `OrderCancelled` is better than `OrderUpdated` (the latter requires inspection)

## Schemas and versioning

### Schema evolution

Events live long (in audit log, in archived queues). Schema must evolve backward compatibly.

Compatibility rules:

- **Adding optional fields** — safe
- **Removing fields** — breaking, requires a new version
- **Changing field types** — breaking
- **Renaming fields** — breaking, first add new and deprecate old

Schema registry (Confluent Schema Registry, AWS Glue Schema Registry) helps manage schemas.

### Version in events

An event contains the schema version. The consumer knows how to parse depending on the version:

~~~json
{
  "event_type": "OrderCreated",
  "version": "2.0",  // v1 had different structure
  ...
}
~~~

### Backward compatibility

The consumer must handle at least the current and previous version. Ideally — all versions since the last major breaking change.

## Patterns

### Event notification

The simplest pattern — the event announces "X happened", the consumer reacts:

~~~
UserRegistered event
    ↓
EmailService — sends welcome email
~~~

Data in the event is minimal — only an identifier. The consumer fetches details if needed.

### Event-carried state transfer

The event contains all the state the consumer needs:

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

The consumer doesn't need to make a callback to the publisher — state arrives in the event.

Pros: consumer is independent of publisher availability.

Cons: events are larger, data duplication.

### Event sourcing

The source of truth is a sequence of events. Current state is a projection from events.

~~~
Events: OrderCreated → ItemAdded → ItemAdded → OrderPaid → OrderShipped
    ↓
Projection: Order current state
~~~

Suitable for: financial systems (everything must be traceable), audit-heavy domains, systems where the full history has value.

Not suitable for: simple CRUD, systems where current state is sufficient.

Complexity is substantial — event sourcing is a big commitment.

### CQRS (Command-Query Responsibility Segregation)

Separation of the write side (commands changing state) from the read side (queries reading state):

~~~
Commands → Write Model → Events → Read Models (denormalized for queries)
~~~

Often used with event sourcing, but not required.

Pros: scaling read and write independently, optimized data models for different use cases.

Cons: complexity, eventual consistency between write and read sides.

### Saga pattern

Distributed transaction through a sequence of local transactions and compensating actions.

~~~
Step 1: OrderCreated — reserves inventory
Step 2: PaymentProcessed — charges customer
Step 3: ShipmentInitiated — sends to fulfillment

Failure at step 3:
Compensate step 2 — refund payment
Compensate step 1 — release inventory
~~~

Two styles:

- **Choreography** — each service subscribes to events from the previous step
- **Orchestration** — a central coordinator manages the saga

Details — see [microservices.md](microservices.md).

### Ownership transfer: fencing epochs and the frozen saga

Field-tested rules (2026-07, distributed ticketing with offline-capable edge nodes) for the
hardest saga subclass — **moving ownership of a partition** (a data shard, a seat pool, a device
assignment) between writers:

- **One fenced writer per partition.** Every write carries a monotonic **fencing epoch** token;
  the store rejects writes with a stale epoch. This turns "two nodes both think they own it"
  (split-brain, the offline-edge classic) from silent corruption into a rejected write.
- **Frozen saga for the move itself.** Ownership transfer is two-phase: freeze the partition under
  the old owner (no writes accepted) → transfer → durable ACK from the new owner → unfreeze under
  the new epoch. **No blind timeout-rollback:** an expired timer proves nothing about the other
  side's state — a stuck transfer stays frozen and pages a human/compensator that can READ the
  actual state, rather than guessing.
- **Consistency is a conditional promise, not a property.** Name the invariants your consistency
  rests on (single writer, monotonic epoch, durable ack, ...) — the system is correct WHILE they
  hold, and every named invariant is a thing the design must enforce and tests must attack.
  Unnamed assumptions are where distributed systems rot.

## Consumer patterns

### At-least-once delivery

The broker guarantees the event will be delivered at least once. Duplicates are possible.

The consumer must be idempotent — reprocessing the same event doesn't change the result.

Typical implementation:

- The consumer stores `processed_event_ids` with a TTL
- On receiving an event, checks — already processed?
- If yes — ack and skip
- If no — process, then record as processed, then ack

### At-most-once delivery

The broker doesn't guarantee delivery. Loss is possible.

Rarely used — only when loss is acceptable (metrics, non-critical notifications).

### Exactly-once delivery

A guarantee that the event is processed exactly once. Requires transactional messaging (Kafka transactions, RabbitMQ transactions).

High complexity, there is a performance impact. Used when idempotency is impossible.

### Consumer groups

Several service instances read from one topic, each event is handled by one instance:

~~~
Topic: order-events
    ├→ Consumer group: notification-service
    │   ├── instance 1 (handles partition 1)
    │   ├── instance 2 (handles partition 2)
    │   └── instance 3 (handles partition 3)
    └→ Consumer group: analytics-service
        └── instance 1 (handles all partitions)
~~~

Horizontal scaling — more instances in the group = more throughput.

## Observability

### Events as trace points

Each event is a natural checkpoint in the workflow. Tracing via trace_id in metadata:

- Publisher adds trace_id to the event
- Consumer continues the trace
- End-to-end visibility for the entire saga

### Dead letter queue

Events that couldn't be processed after N retries go to the dead letter queue:

- Don't block the main queue
- Manual inspection later
- Retry mechanism after fix

### Monitoring

Key metrics:

- **Throughput** — events per second (publisher, consumer)
- **Lag** — how far the consumer is behind the publisher
- **Error rate** — % of events in the dead letter queue
- **Processing time** — p95, p99 of consumer processing

## Common pitfalls

### Event spam

Publishing every minor change — events become noise, consumers overloaded.

Solution: events at the granularity of domain-significant changes, not implementation details.

### Breaking schema changes

Removing or renaming a field without a version bump — breaks consumers.

Solution: schema registry, backward compatibility rules, explicit versioning.

### Missing event store

Events are lost on broker restart. Impossible to replay or audit.

Solution: durable storage (Kafka with retention), event store (EventStore DB), database-backed events.

### Sync thinking in an async system

Trying request-response through events — "publish event and wait for response":

~~~
❌ BAD: publish, wait for reply (blocks)
✅ GOOD: publish and continue, handle response event later
~~~

Event-driven requires a mental shift to async.

### Tight coupling through shared schemas

Publisher and all consumers strongly typed to the same schema. Changing the schema — deploy everyone simultaneously.

Solution: consumer-side interacts through a projection/view, tolerant reader pattern (ignores unknown fields).

### No ordering guarantees

Events may arrive out of the order in which they were published (especially cross-partition).

Solution: factor ordering concerns into the design — sequence numbers, timestamps, causation chain.

### Event as API

Events become part of the API contract. All subscribers depend on the schema.

Treated accordingly — versioning, documentation, deprecation process.

### Physical durability mistaken for semantic durability

When integrating with a legacy/downstream system, "the row is written and the WAL is flushed"
(physical durability) is NOT "the downstream application accepted and now owns that state"
(semantic durability). Raw-UPDATEing another system's operational database bypasses its
invariants, caches, and audit trail — the write is durable and wrong.

Solution (anti-corruption rule, field-tested 2026-07): never write another system's tables
directly. Write to an append-only command/import table (or queue) it owns the consumption of, and
treat only its **application-level ACK** as done — the same at-least-once + idempotency discipline
as any other consumer.

## Event storage

### Ephemeral (queue)

Events sit in the queue until consumption, then are deleted (RabbitMQ default, SQS).

Suitable for: task queues, temporary notifications.

### Retained (log-based)

Events are stored in a log for a set time (Kafka, Kinesis).

Allows:

- Replaying events from a specific point
- New consumers get historical events
- Audit trail
- Debug via replay

### Event store

A specialized DB for events (EventStore DB, custom DB):

- Guaranteed ordering
- Efficient append
- Replay capabilities
- Subscriptions

For event sourcing.

## Migration to event-driven

Existing system without events — gradual transition:

### Strangler fig

1. Identify workflow for migration
2. Add event publishing to the existing sync code
3. Create a consumer implementing the integration
4. Validate parity
5. Switch the sync call to event-driven
6. Repeat for the next workflows

### Dual-write pattern

Temporarily — both sync call and event publishing:

- Helps validate the event-driven version
- Provides a rollback option
- Remove the sync call once confident

### Parallel runs

Run both old and new paths in parallel, compare results, only switch when consistent.
