# Ruby on Rails — stack rules

Ruby/Rails-specific code rules. General principles are in [core/](../core/).

## Version and tools

- Ruby 3.3+ (YJIT on by default, stable pattern matching); pin in `.ruby-version` (committed) — version managers (mise/rbenv) and CI read it
- Rails 7.2+ (8.0 for new projects); `config.load_defaults` matches the Rails major.minor — no cherry-picking old defaults without a comment explaining why
- **Bundler** — `Gemfile` is the single source of truth; `Gemfile.lock` is committed always
- `bin/setup` is the one-command bootstrap and stays working — a new machine goes from clone to green tests with `bin/setup && bin/rails test:prepare`

## Project structure

Rails conventions plus one explicit layer for use cases:

~~~
app/
  controllers/            # HTTP boundary — parse params, call a service, render. No business logic
  models/                 # ActiveRecord models: persistence, validations, scopes, small domain methods
  services/               # use cases (POROs with a single public `call`) — business logic lives HERE
  jobs/                   # Active Job classes — thin wrappers that call a service
  mailers/                # thin, like controllers
  views/                  # templates — presentation only, no queries
lib/                      # domain-independent code (would make sense outside this app)
config/
db/migrate/
spec/                     # mirrors app/ (or test/ with Minitest)
~~~

Rules:

- Dependency direction: `controllers`/`jobs`/`mailers` → `services` → `models`. Views call helpers/presenters, never services
- A controller action longer than ~10 lines or containing a conditional business rule = the logic belongs in a service
- Queries live in models (scopes) or query objects — never inline in controllers or views
- `app/helpers/` is for view formatting only — a helper touching the database is a defect

## Error handling

- Exceptions only; a typed hierarchy per category under a base `ApplicationError < StandardError`, with context in the message:

~~~ruby
raise PaymentFailed, "charging order #{order.id}: #{gateway_error.code}"
~~~

- Bare `rescue` and `rescue nil` are **forbidden** — rescue the narrowest class you can handle, otherwise let it propagate
- `rescue Exception` is forbidden everywhere (it swallows signals and syntax errors) — `StandardError` is the widest allowed, and only at top-level boundaries: `rescue_from` in `ApplicationController`, `retry_on`/`discard_on` in `ApplicationJob`
- Service failures the caller must branch on are exceptions the controller rescues — not `nil` returns, not `[ok, value]` arrays

## Database

- **Active Record** with discipline; migrations mandatory and reversible (`change` when Rails can invert it, explicit `up`/`down` otherwise) — schema changes never happen by hand
- `db/schema.rb` committed (or `structure.sql` when the schema uses DB features Rails can't dump — the choice is recorded once)
- Parameterized queries only: `where("email = ?", email)` or hash conditions; interpolating any variable into an SQL string is forbidden, including "safe" ones
- N+1 is a defect, not a style issue: `includes`/`preload` at the query site; **bullet** enabled in development and test, its findings are fixed, not silenced
- `default_scope` is forbidden — it leaks into every query and join invisibly
- Skipping validations (`save(validate: false)`, `update_attribute`, `update_columns`) — only in migrations/backfills with a comment stating why it's safe
- Transactions are declared at the service layer, not inside models

## Background jobs

- **Active Job** over **Solid Queue** (Rails 8 default) or **Sidekiq** — the choice is recorded in the entry file
- Jobs are thin: deserialize args, call a service. Business logic in a job class is a defect
- Arguments are ids and primitives, never model instances or hashes of state — the record is re-fetched inside the job
- Every job is idempotent (re-running it is safe) — retries are a fact of queue life

## Frontend

- **Hotwire (Turbo + Stimulus)** is the default — server-rendered HTML, no separate SPA without an ADR
- JS bundling via **importmap** (no build step) or **esbuild** when npm packages are genuinely needed
- Stimulus controllers are small and generic (behavior, not page logic); page state lives on the server

## Tests

- **RSpec** + **FactoryBot** as the standard (Minitest + fixtures acceptable if adopted project-wide — record the choice); **Capybara** for system specs
- Layer separation: model/service specs (fast, no HTTP), request specs for the API/controller boundary, system specs for critical user flows only
- No real network in specs — **WebMock** blocks it globally, HTTP interactions are stubbed or recorded via VCR; no real clock — `travel_to`/`freeze_time` from `ActiveSupport::Testing::TimeHelpers`
- Factories are minimal by default (only what validity requires); traits for variants — a factory that creates five associated records "just in case" makes every spec slow
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): **SimpleCov**, artifact at `coverage/index.html`

Run:

~~~bash
bundle exec rspec spec/models spec/services   # fast
bundle exec rspec                             # full
~~~

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Rails. "Clean" = all commands green:

~~~bash
bundle exec rubocop                          # 0 offenses
bin/rails zeitwerk:check                     # autoloading coherent (all constants resolvable)
bundle exec brakeman -q --no-pager           # 0 security warnings
bundle exec rspec                            # tests green
~~~

Any of: a RuboCop offense, a Zeitwerk error, a Brakeman warning, a red test = the task is not done. Suppression (`# rubocop:disable`, a Brakeman ignore entry) — only with a reason in a comment right next to it. A `.rubocop_todo.yml` is allowed only when adopting the regimen on legacy code, with a burn-down rule: the todo file may only shrink.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
bundle exec debride --rails app/ lib/        # methods with no static call site (noisy: review, don't gate)
~~~

## Logging

- `Rails.logger` with **tagged logging** (`config.log_tags = [:request_id]`); a structured/JSON formatter in production so logs are machine-parseable
- Context travels in tags or key-value pairs, not interpolated prose
- Secrets/PII never reach logs: `config.filter_parameters` covers passwords, tokens, card numbers (Rails' default list + the project's own fields) — filtering is verified, not assumed

## Linting

- **RuboCop** with `rubocop-rails`, `rubocop-rspec`, `rubocop-performance`; the config is committed; metrics cops (`Metrics/*`) tuned once, then obeyed — not disabled per-file
- **Brakeman** — security static analysis, part of the clean build, not a "sometimes" scan
- Warnings are not allowed — see [quality-gates.md](../core/quality-gates.md)

## Specific prohibitions

- Business logic in controllers, views, helpers, or callbacks — it lives in services/models
- Model callbacks with side effects beyond the record itself (`after_save` sending email, touching other tables, enqueuing jobs conditionally) — that's a service's job; callbacks are for the record's own derived state
- Monkey-patching core classes or gems — forbidden without an ADR; wrap or subclass instead
- `method_missing`/`define_method` metaprogramming in `app/` code — Rails provides enough magic; yours needs a strong justification
- `default_scope` (repeated because it keeps coming back)
- `rescue nil`, bare `rescue`, `rescue Exception`
- `Thread.new` in application code — concurrency goes through jobs
- `puts`/`pp` debugging left in code; `binding.irb` in a commit
- Fat concerns as a dumping ground — a concern is a genuinely shared, nameable behavior, not "the rest of a 500-line model"

## Rails-specific patterns

**Service object** — a PORO with one public entry point, dependencies in the constructor:

~~~ruby
class Orders::Place
  def initialize(payment_gateway: PaymentGateway.new)
    @payment_gateway = payment_gateway
  end

  def call(cart:, user:)
    Order.transaction do
      order = Order.create!(user: user, lines: cart.lines)
      @payment_gateway.charge!(order)
      order
    end
  end
end
~~~

- Namespaced by domain (`Orders::Place`, not `PlaceOrderService`); raises typed errors, returns the domain object
- **Scopes compose, class methods orchestrate**: query fragments are scopes; anything with branching is a class method or query object
- **Presenters/view models** for view logic heavier than formatting — not helpers, not logic in ERB
