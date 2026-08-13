# Angular — stack rules

Specific rules for the frontend on Angular + TypeScript. General principles are in [core/](../core/).

## Version and tools

- Angular 21 minimum (zoneless by default, Vitest as the default runner); 22 is current — pin the exact version in `package.json`, upgrade only via `ng update`
- Package manager: npm with a committed `package-lock.json` (or pnpm — pick one, record the choice in the entry file); lockfile drift is a red diff
- **Standalone components only.** NgModules are forbidden in new code — they are a dead abstraction (standalone has been the default since v19) that adds indirection with zero payoff
- **Zoneless change detection** (`provideZonelessChangeDetection()`, the default for new apps since v21). Bringing zone.js back — only with an ADR (legacy migration is the sole legitimate reason)
- `ChangeDetectionStrategy.OnPush` on every component — under zoneless, Default-strategy components hide missed-notification bugs instead of surfacing them
- Strict TypeScript is mandatory: `strict: true`, `noUncheckedIndexedAccess`, `noImplicitReturns`, `noFallthroughCasesInSwitch`; plus `angularCompilerOptions: { "strictTemplates": true }` — a template type error is a build failure, not a style nit

## Project structure

~~~
src/app/
  core/                   # app-wide singletons: interceptors, guards, logger, config — imported once at bootstrap
  shared/                 # presentational UI, pipes, directives — imports nothing from features/
  features/
    orders/               # one folder per feature
      orders.routes.ts    # lazy-loaded route config (loadChildren / loadComponent)
      data/               # HttpClient services, DTO types, DTO ↔ domain mapping
      state/              # feature signal state
      ui/                 # presentational components: input()/output() only
      feature/            # smart components (pages): inject services, wire state to ui/
~~~

- Every feature is lazy-loaded from its `*.routes.ts` — eager feature imports defeat code-splitting
- Dependency direction: `features → shared/core`. Features never import each other — cross-feature reuse goes through `shared/` or a route boundary. Back-imports are forbidden, as in [core/code-quality.md](../core/code-quality.md)
- Smart vs presentational: components in `ui/` take `input()` and emit `output()`, never inject data services — that keeps them testable without TestBed providers and reusable across features

## Error handling

- A global `ErrorHandler` provider is mandatory — the last-resort sink that reports to the logger/monitoring; a blank console on a crashed app is forbidden
- One HTTP error interceptor normalizes `HttpErrorResponse` into a typed app error; components never parse raw HTTP errors
- No swallowed stream errors: every `subscribe` either passes an error callback or subscribes to a stream whose errors are handled upstream (`catchError`). An errored stream dies silently — that's a lost feature, not a handled error
- Subscription lifecycle via `takeUntilDestroyed()` / `DestroyRef` only. Manual `Subscription` fields with `ngOnDestroy` unsubscribe bookkeeping are forbidden — it's leak-prone boilerplate the framework already solves

## State & signals

- **Signals are the default reactivity primitive**: `signal` for state, `computed` for derivations, component IO via `input()` / `output()` / `model()`
- `effect()` only for synchronizing with the outside world (DOM, storage, logging). Deriving state inside an effect is forbidden — that's what `computed` is for; effects hide the dependency graph
- RxJS only where there is genuinely a stream over time: websockets, debounced user input, event composition. Interop at the boundary via `toSignal` / `toObservable` — don't hand-roll bridges
- Shared mutable service state is held in signals, not bare fields — under zoneless, plain-field mutation notifies nobody
- A store library (NgRx SignalStore) — only with an ADR; a signal-in-a-service covers most feature state without the ceremony

## Data fetching

- HTTP lives in typed `HttpClient` services in the feature's `data/` layer. HTTP calls from components are forbidden — they weld fetching to rendering and kill testability
- Interceptors for cross-cutting concerns: auth token attachment, error normalization, correlation headers
- The API boundary is validated at runtime (zod `parse` on responses) unless types are generated from the backend contract (OpenAPI) — a hand-written interface is a wish, not a guarantee

## Tests

- **Vitest** — the CLI default since v21 (builder `@angular/build:unit-test`, jsdom environment); Karma is deprecated. Pick one runner and record it in the entry file; Karma is legitimate only in a legacy project mid-migration
- Component tests via TestBed; assert on rendered DOM and emitted outputs, not on private fields
- HTTP: `provideHttpClientTesting` + `HttpTestingController` (or msw for integration-style tests) — no real network in unit tests (see [core/quality-gates.md](../core/quality-gates.md))
- **Playwright** for critical E2E flows
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): Vitest V8 provider via `ng test --coverage`; artifact at `coverage/`

## Clean build

Concretization of the "no warnings" rule from [quality-gates.md](../core/quality-gates.md) for Angular. "Clean" = all commands green:

~~~bash
ng build                    # production build: no errors/warnings, budgets not exceeded, strictTemplates errors fail here
ng lint                     # @angular/eslint (flat config) with no violations
npx prettier --check .      # formatting
ng test                     # unit tests green (Vitest)
~~~

Any of: a build error or warning, an exceeded bundle budget, a template type error, a lint violation, an unformatted file, a red test = the task is not done. Suppression (`// @ts-expect-error`, `eslint-disable`) — only with a reason in a comment right next to it.

## Static-adjunct QG-NN-05 (optional, warn-track)

A cheap complement to the assembled test — catches the "zero production calls" subclass ([core/quality-gates.md](../core/quality-gates.md) §Assembled reachability):

~~~bash
npx knip                    # dead exports, unused files and dependencies
~~~

## Logging

- A thin injectable `LoggerService` with levels wraps the console/transport — one place to redirect to monitoring later
- `console.log` in production code is forbidden — it bypasses levels and survives into user consoles
- Logging secrets/PII is forbidden: tokens, passwords, personal data → `[REDACTED]`

## Linting

- **@angular/eslint** (v22+), flat config `eslint.config.js` on ESLint 9/10 — the legacy `.eslintrc` format is no longer supported, don't generate it
- Template rules ON: `@angular-eslint/template` recommended + accessibility set — template a11y violations are lint errors
- `@typescript-eslint` strict preset; `no-explicit-any` as an error
- **Prettier** owns formatting; ESLint does not carry formatting rules — the two must not fight

## Specific prohibitions

- NgModules in new code — see Version and tools
- `any` — except inside type guards; use `unknown` and narrow
- Nested subscribes (`subscribe` inside `subscribe`) — hides ordering and error paths; compose with `switchMap`/`concatMap`/`combineLatest`
- Logic in templates beyond trivial expressions — a template is a view, not a program; move it to `computed`
- Manual change-detection hacks (`detectChanges()` sprinkling, `markForCheck` as a fix-it) — under zoneless they paper over a state source that isn't a signal; fix the source
- Constructor logic beyond DI assignment — constructors run before inputs are set; use lifecycle hooks or `afterNextRender`
- Untyped or template-driven forms — typed reactive forms only; an untyped `FormGroup` is `any` wearing a costume
- `@ts-ignore` — use `@ts-expect-error: reason` if genuinely unavoidable

## Angular-specific patterns

**`inject()` over constructor parameters** — the current style, composable into functions (guards, interceptors) where constructors don't exist.

**Signal-based component** — the canonical shape:

~~~ts
@Component({
  selector: "app-order-row",
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span>{{ label() }}</span> <button (click)="remove.emit()">×</button>`,
})
export class OrderRowComponent {
  private readonly logger = inject(LoggerService);

  readonly order = input.required<Order>();
  readonly remove = output<void>();
  readonly label = computed(() => `${this.order().id} — ${this.order().total}`);
}
~~~

**Typed reactive forms**: build with `FormBuilder.nonNullable`, model the value type explicitly; `getRawValue()` at the submit boundary, validated by the same zod schema the data layer uses.
