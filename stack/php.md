# PHP — stack rules

PHP-specific code rules. General principles are in [core/](../core/).

## Version and tools

- PHP 8.3+ (typed class constants, readonly deep-freeze semantics, performance); pin the minor version in `composer.json` → `"php": "^8.3"`
- **Composer** — `composer.json` is the single source of truth; `composer.lock` is committed always (apps *and* internal libraries)
- `declare(strict_types=1);` — the first statement in **every** PHP file, no exceptions; a file without it is a defect
- PSR-4 autoloading; no manual `require`/`include` outside the entry point

## Project structure

~~~
public/                   # web entry point (index.php only — no logic)
bin/                      # CLI entry points
src/
  Order/                  # feature
    Domain/               # entities, value objects — no framework imports
    Application/          # use cases, ports (interfaces)
    Infrastructure/       # persistence, HTTP clients, framework glue
  Shared/                 # cross-feature value objects only, no "Helpers" dumping ground
config/
migrations/
tests/                    # mirrors src/ (Unit/ and Integration/ suites)
~~~

Rules:

- `Domain/` imports no framework code (no Symfony/Laravel classes, no facades, no container access)
- Dependency direction: `Infrastructure` → `Application` → `Domain`. Back-imports are forbidden
- Superglobals (`$_GET`, `$_POST`, `$_SERVER`, `$_SESSION`) are touched only by the framework's Request layer — never in `src/` code

## Error handling

- Exceptions only — no error-code returns, no `false`-on-failure functions crossing module boundaries (wrap stdlib functions that do)
- Typed hierarchy per category (`OrderNotFound extends DomainException`); every wrap carries context:

~~~php
throw new PaymentFailed(sprintf('charging order %s', $orderId), previous: $e);
~~~

- The `@` error-suppression operator is **forbidden** — everywhere, including one-liners
- Empty `catch` blocks are forbidden; catch the narrowest type you can handle, otherwise let it propagate
- `catch (\Throwable $t)` only at top-level boundaries (kernel error handler, worker loop, CLI entry)

## Framework

- **Symfony** recommended (explicit DI, less magic). **Laravel** acceptable for product velocity — with discipline: constructor injection everywhere, **no facades and no global helpers (`app()`, `request()`, `config()`) in `Domain/` or `Application/`**
- The DI container is configuration, not a service locator — injecting the container itself is forbidden

## Database

- **Doctrine DBAL/ORM** (Symfony) or **Eloquent** (Laravel); raw access via PDO prepared statements when no ORM fits
- Migrations mandatory and versioned (Doctrine Migrations / Laravel migrations) — schema changes never happen by hand
- Parameterized queries only; interpolating any variable into an SQL string is forbidden, including "safe" ones
- Transactions declared at the use-case (Application) layer

## Tests

- **PHPUnit 11**; data providers as the standard for multiple cases (the table-driven analogue)
- `Unit` and `Integration` as separate suites in `phpunit.xml` — unit tests touch no network, no real clock (inject a `ClockInterface`), no database
- Integration tests run against a real database (local container), not sqlite-in-memory pretending to be MySQL/Postgres
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): **PCOV** (not Xdebug — faster) + `vendor/bin/phpunit --coverage-html coverage/`; artifact at `coverage/index.html`

Run:

~~~bash
vendor/bin/phpunit --testsuite Unit          # fast
vendor/bin/phpunit                           # full
~~~

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for PHP. "Clean" = all commands green:

~~~bash
composer validate --strict                   # composer.json is coherent
vendor/bin/php-cs-fixer check                # formatting (PER-CS 2.0), 0 diffs
vendor/bin/phpstan analyse                   # level max, 0 errors
vendor/bin/phpunit                           # tests green
~~~

Any of: a parse error, a PHPStan finding, a formatting diff, a red test = the task is not done. Suppression (`@phpstan-ignore-line`) — only with a reason in a comment right next to it. A PHPStan **baseline** is allowed only when adopting the regimen on legacy code, with a burn-down rule: the baseline may only shrink.

## Static-adjunct QG-NN-05 (optional, warn-track)

Catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
vendor/bin/phpstan analyse                   # with tomasvotruba/unused-public enabled
composer unused                              # composer-unused: declared deps nothing imports
~~~

## Logging

- **Monolog** behind the **PSR-3** interface; inject `LoggerInterface`, never call a static logger
- Structured context via the array argument: `$logger->info('order processed', ['order_id' => $id]);` — no data interpolated into the message string
- Levels: debug (dev-only), info (normal operations), warning (unusual but recoverable), error (failures)
- Logging secrets/PII is forbidden: passwords, tokens, card numbers → `[REDACTED]`

## Linting

- **PHPStan at `level: max`** with strict rules (`phpstan-strict-rules`); the config is committed
- **PHP-CS-Fixer** with the PER-CS 2.0 ruleset — formatting is a machine check, not review style
- **Rector** optional, for mechanical upgrades (PHP/framework version bumps) — its diffs are reviewed like any code

Warnings are not allowed — see [quality-gates.md](../core/quality-gates.md).

## Specific prohibitions

- `eval()`, `extract()`, variable variables (`$$name`) — forbidden
- The `@` suppression operator (repeated because it keeps coming back)
- Untyped properties, untyped parameters/returns, `mixed` in public signatures — everything is typed; `mixed` only at true serialization boundaries
- Associative arrays as pseudo-DTOs crossing module boundaries — use readonly classes/enums; array shapes are for PHPStan-annotated internals only
- Magic `__get`/`__set`/`__call` in `Domain/`/`Application/`
- `die()`/`exit()` outside entry points; short open tags; closing `?>` in pure-PHP files
- Business logic in controllers/commands — they parse input, call a use case, format output

## PHP-specific patterns

**Value objects as readonly classes** with constructor promotion:

~~~php
final readonly class Money
{
    public function __construct(
        public int $amountMinor,
        public Currency $currency,
    ) {
        if ($this->amountMinor < 0) {
            throw new InvalidMoney('amount must be non-negative');
        }
    }
}
~~~

- **`final` by default** — inheritance is opt-in via interfaces, not open classes
- **Native enums** (backed where serialized) instead of class-constant "enums"
- **Ports at the point of use**: `Application/` declares the interfaces it needs; `Infrastructure/` implements them. Domain never names an infrastructure class
