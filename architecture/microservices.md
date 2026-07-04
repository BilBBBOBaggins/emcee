# Microservices — architecture pattern

Splitting an application into independently deployable services with their own data and boundaries.

Symmetric alternative to [modular-monolith.md](modular-monolith.md). The choice between them is one of a project's key architectural decisions.

## When to choose microservices

Not preemptively. Only when there are concrete reasons.

### Triggers for migrating to microservices

**Organizational**:

- Several teams work independently, different release cadences
- Conway's law — the organization's structure doesn't match the monolith
- Ownership boundaries are clearer in code than in documentation

**Scaling**:

- One component requires specific scaling (memory-heavy, CPU-heavy, network-heavy)
- Different components have different latency requirements
- Horizontal scaling is only needed for part of the system

**Technology diversity**:

- Different components require different stacks (ML pipeline in Python, API in Go, real-time in Rust)
- Integration with systems that only run on specific stacks

**Availability**:

- Components have different SLA requirements
- Failure isolation — a failure in one shouldn't bring down the others

**Compliance**:

- Part of the system processes data with special regulatory requirements (PCI, HIPAA, government data)
- Physical infrastructure isolation is required by compliance

### When NOT to choose microservices

- Team of up to 10-15 developers
- MVP phase, scope changes fast
- No operational expertise to manage a distributed system
- No observability stack (tracing, metrics, logs aggregation)
- The simplicity of a monolith beats the flexibility of microservices

Rule: **modular monolith until concrete triggers appear**. Don't start with microservices "because it's modern architecture".

## Service boundaries

### Domain-driven boundaries

A service = a Bounded Context in DDD terms:

- Its own ubiquitous language (domain terms)
- Its own data model
- An independent evolution lifecycle
- Minimal dependencies on other contexts

Not "a service per entity" (that's an anti-pattern — too chatty a communication). A service covers a cohesive business capability.

### Defining boundaries

Process:

1. **Event storming** with domain experts — surfacing business events, commands, actors
2. Grouping events into **aggregates** — what changes together
3. Extracting **bounded contexts** — related aggregates with a common language
4. Each bounded context — a candidate for a separate service

### Verifying boundary correctness

- Transaction scope — transactions within one service, not cross-service
- Data ownership — no shared tables between services
- Temporal coupling — changing one doesn't require synchronously changing another
- Autonomy — a team can deploy a service independently

If these properties are violated — the boundaries are wrong, reconsider them.

## Communication between services

### Synchronous calls

REST API (JSON over HTTP) or gRPC (binary protocol with schema).

**REST** — the default choice:

- Simplicity
- Universal tooling
- Debuggable (readable JSON)
- HTTP ecosystem (load balancers, caches)

**gRPC** when:

- Performance is critical (binary protocol, HTTP/2)
- Streaming RPCs are needed
- Strong typing via protobuf
- Internal communication (not browser-facing)

### Asynchronous events

Message broker (Kafka, RabbitMQ, NATS, Redis Streams).

Preferred approach for:

- Events that many services want to know about (fan-out)
- Long workflows (saga pattern)
- Decoupling producers from consumers
- Handling bursts and backpressure

### Communication anti-patterns

**Chatty APIs** — calling A→B→C→D for a single operation. Latency piles up, failure probability multiplies. Solution: aggregate data in one call, or duplicate read-only reference data.

**Distributed monolith** — services communicate synchronously so often that it's effectively a monolith with a network in the middle. Worse than a monolith: latency, complexity, failures. Solution: either reconsider the boundaries, or go back to a monolith.

**Shared database** — two services write to the same DB. Violates deployment independence, creates hidden coupling. Solution: database per service.

## Database per service

Each service — its own data. No shared tables between services.

### Rules

- Service A doesn't read service B's tables directly. Only through service B's API
- The DB schema is an internal implementation detail of the service, can change without notifying others
- Cross-service JOINs — forbidden. If needed — either application-level aggregation or event-driven replication

### Data consistency

No cross-service transactions. Options:

**Eventual consistency** via events:

- Service A changes its state
- Publishes an event
- Service B is subscribed, updates its state
- There's a time window between the changes where states diverge — this is OK for most cases

**Saga pattern** for multi-step workflows:

- Break the transaction into steps
- Each step — a local transaction in one service
- Compensating actions for rollback
- Orchestrated (central coordinator) or choreographed (via events)

**2-phase commit** — forbidden. Doesn't scale, blocks, creates distributed locks.

## API versioning

Services evolve independently, consumers are on different API versions simultaneously.

### Backward compatibility

- Adding fields to response — safe (old clients ignore them)
- Adding endpoints — safe
- Adding optional parameters — safe
- Removing fields — breaking change
- Changing field types — breaking change
- Changing semantics — breaking change

On a breaking change — a new API version with parallel support for the old one.

### Versioning strategies

**URL versioning** — `/v1/users`, `/v2/users`. Simple, explicit.

**Header versioning** — `Accept: application/vnd.api.v2+json`. Cleaner URL, but harder to debug.

**Content negotiation** — one endpoint, different response schemas by Accept header. Maximum flexibility, maximum complexity.

For most projects — URL versioning.

### Deprecation process

- Announce deprecation in docs + headers
- Period of parallel support (minimum 6 months)
- Alerts to consumers using the deprecated version
- Restrict new features to the new version only
- Final sunset with advance notice

## Service discovery

How service A finds service B at runtime.

### DNS-based

The simple case:

- Each service — a DNS name in a private zone
- Load balancer in front of replicas
- Kubernetes does this out of the box (Services)

### Service mesh

For more complex scenarios (Istio, Linkerd, Consul Connect):

- Automatic service discovery
- Traffic management (retries, timeouts, circuit breaking)
- Mutual TLS between services
- Observability (automatic tracing)

There's overhead (sidecar proxy on every pod), but the operational benefits are huge.

### Client-side discovery

The client itself looks up the service through a registry (Consul, Eureka):

- Gives control over load balancing
- More code complexity

Less common in modern architectures — service mesh covers this better.

## Observability

Critical for microservices. Without it, debugging a distributed system is impossible.

### Three pillars

**Logs** (structured):

- Every log contains a `trace_id` for correlation across services
- Structured format (JSON) for querying in the log aggregator
- Centralized collection (ELK, Loki, Datadog)

**Metrics**:

- RED (Rate, Errors, Duration) for each endpoint
- USE (Utilization, Saturation, Errors) for resources
- Custom business metrics
- Prometheus + Grafana or a SaaS

**Traces**:

- Distributed tracing (OpenTelemetry) — each request creates a trace, spans in each service
- Jaeger, Zipkin, Tempo — visualization
- Critical for understanding latency and failures in a distributed system

### Correlation

Every request from a user → `trace_id` → propagated through all services via HTTP headers or message metadata.

This `trace_id` is visible in logs and traces — you can quickly find all events related to a specific user request.

## Resilience patterns

### Timeouts

Every cross-service call has a timeout. Without one — cascade failure, a service waits on a dead dependency.

Typical timeouts: 1-5 seconds for internal calls, longer for special cases.

### Retries

Automatic retry for transient failures (5xx, timeouts):

- Exponential backoff with jitter
- Maximum 2-3 attempts
- Idempotency — make sure the operation is safe to retry

### Circuit breaker

When a dependency goes down — don't keep bombarding it with requests:

- After N failures over a period — "open" the circuit
- A health check periodically probes it
- After successes — "closed" again

Libraries: resilience4j (Java), Polly (.NET), gobreaker (Go), tenacity (Python).

### Bulkheads

Resource isolation — one slow dependency shouldn't exhaust the whole service's thread pool:

- Separate thread pools for different dependencies
- Separate connection pools
- Resource limits in K8s (CPU, memory)

### Graceful degradation

When a dependency is unavailable — operate in a limited mode:

- Cache the last known value
- Fall back to another source
- A feature flag disables the functionality
- User-visible degraded mode, not a complete outage

## Deployment

### Container-based

Standard — Docker containers, orchestrated via Kubernetes or an equivalent.

- Each service — a separate image
- CI/CD pipeline per service
- Independent deploys

### CI/CD considerations

- Each service — its own pipeline
- Contract tests before deploy — don't break consumers
- Canary deployment for rollout (5% → 25% → 100%)
- Automatic rollback on regression

### Infrastructure as Code

Infrastructure described in code (Terraform, Pulumi, Crossplane). Not "click-ops" in the cloud console.

## Data consistency

Compensating actions for multi-service operations.

### Saga example

A booking service wants to create a reservation:

1. Payment service — charge the card
2. Inventory service — reserve the item
3. Notification service — send confirmation

If step 3 fails:

- Notification — retry
- No full rollback of steps 1 and 2

If step 2 fails:

- Payment service — refund the charge (compensating action)

If step 1 fails:

- Stop, user notified

### Choreography vs orchestration

**Choreography** — services subscribe to each other's events, each knows what to do:

- Simple implementation
- Scales poorly — hard to track the full workflow
- Logic is spread out

**Orchestration** — a central coordinator manages the workflow:

- Clear view of the full process
- The coordinator — a potential bottleneck/SPOF
- Tools: Temporal, AWS Step Functions, Camunda

For complex workflows — orchestration. For simple ones — choreography.

## Monitoring and alerting

Separate from observability (which is for debugging). Alerting — proactive detection of problems.

### What to monitor

- **Availability** — the service responds (health checks)
- **Latency** — p95, p99 response times
- **Error rate** — 5xx errors per minute
- **Resource usage** — CPU, memory, disk
- **Business metrics** — orders per minute, signups per day

### Alert fatigue

Too many alerts — they get ignored. Rules:

- Alert only on actionable issues
- Severity levels (page vs email vs ignore)
- Alert aggregation — not 100 alerts at once
- A runbook for each alert — what to do when it fires

## Migration from the monolith

Strangler fig pattern:

1. Pick a bounded context that can be extracted
2. Create a new service with an API identical to the internal calls from the monolith
3. Gradually redirect traffic from the internal calls to the new service's API
4. When all traffic is on the service — remove the code from the monolith
5. Repeat with the next context

Not a "big bang rewrite" — that almost always fails. Gradual migration works.

## Common pitfalls

### Premature microservicization

A team read a blog post and started splitting a monolith into 20 services. Result: complexity, slow iteration, operational hell. Solution: modular monolith first, microservices when there are triggers.

### Shared libraries hell

Common libraries are used across many services. Update the library → need to redeploy all services → independence is lost. Solution: minimize shared libraries, version them, accept that different services run on different versions.

### Distributed transactions

Trying to reproduce ACID transactions across services. Doesn't work. Solution: eventual consistency, sagas.

### Synchronous chains

A→B→C→D for every request. Latency piles up. A failure anywhere breaks everything. Solution: async events or data aggregation.

### Missing observability

When something goes wrong in a distributed system — impossible to debug without tracing, structured logs, metrics. Solution: observability infrastructure before the first service goes to production.
