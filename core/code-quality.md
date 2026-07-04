# Code quality standards

Rules about what counts as good code. This is about the code itself, not about the agent's work
process (see principles.md) and not about automated checks (see quality-gates.md).

## Single Responsibility Principle

A class or module does one thing. One reason to exist.

Signs of a violation:

- The name contains "And" (`UserAndBilling`, `DataLoaderAndValidator`) — almost always split
- More than 10 public methods — consider a split
- Methods form unrelated groups — different responsibilities, split by group
- The name doesn't unambiguously explain what the class does — a bad name = blurred responsibility

On detection — split before merging the task, don't defer it.

## Prohibition on God Objects

Large classes/modules are a frequent source of problems. Signs of a God Object:

- Crossed the LOC threshold (see [quality-gates.md](quality-gates.md)) — this is **a signal that
  wakes up judgment**, not the verdict itself: the threshold obligates a reasoned answer — "it does
  one thing, here's why" — OR a split (QG-NN-03)
- Managing several levels at once (persistence + UI state + business logic + networking in one
  class)
- High fan-in and fan-out — it knows about everything and everything knows about it
- Hard to test — needs mocks for everything

For a **confirmed** God Object (signals converged, not just size), there's one solution — split by
responsibility. Not "a 1500-line class is fine if it's about one thing" — it isn't about one thing.
Nothing about one thing runs 1500 lines. But a LOC threshold crossed on its own doesn't yet prove a
God Object — a long-but-coherent parser gets justified, not cut just to hit a number.

## Layered architecture — one-directional dependencies — [CQ-NN-02 · non-negotiable · accountability]

If a project is split into layers (almost always a good idea), dependencies between layers are
strictly one-directional.

For a project with three layers (the typical case):

~~~
{{layer-ui}} → {{layer-bridge}} → {{layer-core}}
~~~

{{layer-core}} never imports from {{layer-bridge}} or {{layer-ui}}.
{{layer-bridge}} never imports from {{layer-ui}}.

This rule has no exceptions. If a "need" to violate it comes up — the layer is designed wrong;
refactor the layer, don't break the rule.

The concrete layer names and their purposes live in the project's regimen entry file and (if the
corresponding architecture module is kept) in [architecture/layered-architecture.md](../architecture/layered-architecture.md);
for desktop/UI specifics with native+declarative layers — [architecture/three-tier-with-bridge.md](../architecture/three-tier-with-bridge.md).

## Prohibition on TODO/FIXME — [CQ-NN-01 · non-negotiable · mechanical(opt): check-no-todo.sh]

If something needs doing — do it now. If it can't be done now — don't leave a marker in the code,
create a task in the tracker.

A TODO in code is unpaid technical debt that grows unnoticed. Six months later nobody remembers why
it's there or what needs to be done.

There are no exceptions. A "temporary TODO" becomes permanent 99% of the time.

## Prohibition on commented-out code — [CQ-NN-03 · non-negotiable · accountability]

If code isn't needed — delete it. Don't comment it out "just in case."

Git remembers the whole history. If the code is needed again, it can be restored from history.

Commented-out code rots. A month later it's unclear why it was commented out, whether it still
works, whether it's needed. It takes up space in files, confuses grep, and gets in the way of
navigation.

## Naming

General principles (concrete conventions live in `stack/<stack>.md`):

- Names describe **what**, not **how**. `UserRepository`, not `UserMySQLDataLoader`.
- Avoid abbreviations except widely accepted ones (`id`, `url`, `io`). Not `usrMgr`, but
  `userManager`.
- Classes are nouns (`OrderProcessor`).
- Methods are verbs (`processOrder`, `sendEmail`).
- Boolean variables and methods use `is/has/should/can` prefixes (`isActive`, `hasPermission`,
  `shouldRetry`).
- Constants follow the stack's convention (UPPER_SNAKE_CASE in C++/Python, kPascalCase in Google
  style, PascalCase in C#).

A name should be clear without comments. If a comment is needed to explain what a variable is for —
rename it.

## Error handling

Universal principles (concrete mechanisms live in the stack files):

- Errors are never silently ignored. Either handle them or explicitly propagate them.
- Empty catch blocks are forbidden. Either it's logged and handled, or it isn't caught at all.
- Errors are typed — not a generic `Exception`/`Error`, but concrete types with concrete semantics.
- User-facing errors and internal errors are different things. Don't show the user a stack trace
  with technical detail.
- Returning errors from functions goes through the stack's typed mechanism (`Result<T, E>`,
  `std::expected`, `Option`, tuple).

## Async safety

If the project has concurrency (almost always):

- Signals between threads are passed by value, not by reference to shared state
- Shared mutable state is either absent or protected by synchronization
- The main thread never blocks on I/O, network calls, or heavy computation
- Pattern: a Command object goes into a queue, executes in a worker, the result comes back via a
  signal/callback

Concrete mechanisms live in the stack file (goroutines+channels, async/await, signals/slots, actor
model).

## Security minimum — [CQ-NN-04 · non-negotiable · accountability]

Always observed regardless of the project:

- Passwords are never in plaintext in the database, never in code, never in logs
- API keys and secrets go through secrets management (env variables, vault, keychain), not in the
  repository
- User input is never used directly in SQL — only through prepared statements
- User input in HTML/XML is sanitized and escaped
- User input in shell commands is forbidden, or only through a strict whitelist
- PII (personal data) — minimize collection, encryption at rest, an access audit log
- Secrets in git history — on compromise: rotation + rewrite history + notification

This is the baseline minimum. Regulated domains (healthcare, finance, government data) add
requirements — see [domain/regulated.md](../domain/regulated.md) (if this domain module is kept in
the project).

## Readability over "cleverness"

Prefer simple, explicit code over complex and "elegant":

- Two simple methods beat one complex one
- An explicit `if (x != null) { ... }` is clearer than a clever `x?.let { ... }?.also { ... }`
- A chain of 10 `.map().filter().reduce()` — break it into named intermediate variables
- Optimizations without benchmarks are forbidden. "This is faster" without measurement is a
  hallucination.

Code is read 10 times more often than it's written. Optimize for readability.
