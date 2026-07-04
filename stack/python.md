# Python — stack rules

Python-specific code rules. General principles are in [core/](../core/).

## Version and tools

- Python 3.12+ (modern typing, performance).
- **uv** for dependency and venv management (faster than pip/poetry); the `uv.lock` lock file is committed.
- `pyproject.toml` — single source of truth for dependencies and tool configs. No `setup.py`, no `requirements.txt` as the primary source.
- A virtual environment is mandatory, no global installs of project packages.

## Project structure

~~~
src/
  acme/                 # project package (src-layout)
    domain/             # entities and business rules, no IO
    service/             # use cases
    repository/          # data access
    transport/            # FastAPI routers, middleware
    config.py            # settings via pydantic-settings
tests/
  unit/
  integration/
pyproject.toml
~~~

Rules:

- **src-layout** (package in `src/`) — so tests run against the installed package, not local files.
- Business logic doesn't live in `transport/`. Layers: `transport → service → repository`, no reverse imports ([core/code-quality.md](../core/code-quality.md)).
- Circular imports are forbidden.

## Typing — mandatory

- All functions and methods are annotated (parameters + return). Public API without annotations doesn't pass.
- `mypy --strict` (or `pyright` in strict mode) — part of the gate (see below). No `Any` except at the boundary with untyped libraries, and even then — locally.
- `# type: ignore` — only with a code and a reason: `# type: ignore[arg-type]  # lib stubs incomplete`.
- Prefer `dataclasses` / `pydantic` models over a plain `dict` for structured data.
- `from __future__ import annotations` or PEP 604 (`X | None`) for modern annotations.

## Error handling

- Exceptions are typed — custom classes per domain, not a plain `Exception`:

~~~python
class ValidationError(Exception):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"validation failed on {field}: {message}")
~~~

- No bare `except:` and no `except Exception: pass`. Catch specific types, or log and re-raise.
- Context on re-raise: `raise ServiceError(...) from err` — preserves the chain.
- User-facing errors and internal ones are separated (don't leak tracebacks outward).

## Async

- If the project is async (FastAPI, aiohttp) — **don't mix** sync-blocking calls into the event loop. Blocking IO/CPU — via `asyncio.to_thread` or a pool.
- `async def` for IO-bound work; pure CPU-bound work — a separate process/pool, not a coroutine.
- Any coroutine with a background task has a way to be cancelled (`asyncio.TaskGroup`, `CancelledError` is propagated, not swallowed).
- No bare `asyncio.create_task` without keeping a reference and handling exceptions.

## Database

- **SQLAlchemy 2.0** (typed, `Mapped[...]`) or **asyncpg** directly for simple cases. ORM magic is minimized.
- Migrations — **Alembic**, files are versioned.
- Parameterized queries always — no string concatenation of SQL (protection against injection, [core/code-quality.md](../core/code-quality.md)).
- Transactions are explicit (`async with session.begin():`), transaction boundaries are in the service layer, not in the repository.

## Web framework

- **FastAPI** by default (async, pydantic validation, OpenAPI out of the box).
- Pydantic models for request/response — validation at the boundary, types are the source of truth.
- Dependencies via `Depends`, not global singletons.
- Flask/Django — only if there's an explicit reason (legacy, admin-heavy) and it's recorded in an ADR.

## Tests

- **pytest** + `pytest-asyncio` for async.
- Fixtures for setup, not global state between tests.
- Parametrization via `@pytest.mark.parametrize` (the table-driven equivalent).
- Unit tests — no real network/DB (mocks, in-memory). Integration tests — separate, marked with a marker:

~~~python
@pytest.mark.integration
async def test_repo_persists_invite(db_session): ...
~~~

~~~bash
pytest tests/unit                       # fast
pytest -m integration                   # integration
~~~

- `freezegun`/time injection instead of real time; no `time.sleep()` for synchronization (see [core/quality-gates.md](../core/quality-gates.md)).
- Coverage report (diagnoses gaps, not a target percentage — see `roles/qa-e2e.md` §Coverage diagnostics): `pytest --cov=<package> --cov-report=term-missing` (plugin `pytest-cov`); machine-readable artifact — `--cov-report=json:coverage.json`.

## Logging

- `structlog` or stdlib `logging` with a structured formatter. Not `print()`.
- Structured key-value, not f-strings in the message:

~~~python
logger.info("invite created", invite_id=invite.id, tenant_id=tenant_id)
~~~

- Logging secrets and PII is forbidden (passwords, tokens, email in plaintext where it counts as PII) — `[REDACTED]`.

## Clean build — linting, types, formatting

- **ruff** — linter + formatter (replaces flake8/isort/black). Strict config in `pyproject.toml`.
- **mypy --strict** (or pyright strict) — types.
- This is "no warnings" for Python from [core/quality-gates.md](../core/quality-gates.md):

~~~bash
ruff check .          # lint with no violations
ruff format --check . # formatting
mypy src              # types with no errors
pytest                # tests green
~~~

Any ruff/mypy violation = the task is not done. Suppression (`# noqa`, `# type: ignore`) — only with a code and a reason.

## Specific prohibitions

- Mutable default arguments (`def f(x=[])`) — forbidden, a classic bug.
- `import *` — forbidden.
- Global mutable state with business data — forbidden, everything via DI/dependencies.
- `eval`/`exec` on user input — forbidden.
- `assert` for runtime validation in production code — forbidden (stripped out under `-O`); `assert` only in tests.
- Business logic in `__init__.py` — forbidden (re-export only).
- `requirements.txt` as the primary manifest — use `pyproject.toml` + `uv.lock`.

## Python-specific patterns

**Dependency injection via constructor / FastAPI `Depends`**, not via global singletons:

~~~python
class InviteService:
    def __init__(self, repo: InviteRepository, mailer: Mailer) -> None:
        self._repo = repo
        self._mailer = mailer
~~~

**Pydantic model at the boundary, dataclass inside the domain** — validation outside, clean types inside. DI frameworks (dependency-injector) aren't needed at the start — constructors are sufficient.
