# Python — правила работы со стеком

Специфические правила для Python-кода. Общие принципы в [core/](../core/).

## Версия и инструменты

- Python 3.12+ (современный typing, performance).
- **uv** для управления зависимостями и venv (быстрее pip/poetry); lock-файл `uv.lock` коммитится.
- `pyproject.toml` — single source of truth для зависимостей и конфигов инструментов. Никаких `setup.py`, `requirements.txt` как основного источника.
- Виртуальное окружение обязательно, никаких глобальных установок пакетов проекта.

## Структура проекта

~~~
src/
  acme/                 # пакет проекта (src-layout)
    domain/             # сущности и бизнес-правила, без IO
    service/            # use cases
    repository/         # доступ к данным
    transport/          # FastAPI routers, middleware
    config.py           # настройки через pydantic-settings
tests/
  unit/
  integration/
pyproject.toml
~~~

Правила:

- **src-layout** (пакет в `src/`) — чтобы тесты гоняли установленный пакет, не локальные файлы.
- Бизнес-логика не живёт в `transport/`. Слои: `transport → service → repository`, обратных импортов нет ([core/code-quality.md](../core/code-quality.md)).
- Циклические импорты запрещены.

## Типизация — обязательна

- Все функции и методы аннотированы (параметры + возврат). Публичный API без аннотаций не проходит.
- `mypy --strict` (или `pyright` в strict) — часть гейта (см. ниже). Никакого `Any` кроме границы с нетипизированными библиотеками, и тогда — локально.
- `# type: ignore` — только с кодом и причиной: `# type: ignore[arg-type]  # lib stubs неполные`.
- Предпочитать `dataclasses` / `pydantic` модели голым `dict` для структурированных данных.
- `from __future__ import annotations` или PEP 604 (`X | None`) для современных аннотаций.

## Обработка ошибок

- Исключения типизированы — свои классы под домен, не голый `Exception`:

~~~python
class ValidationError(Exception):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"validation failed on {field}: {message}")
~~~

- Никаких «голых» `except:` и `except Exception: pass`. Ловить конкретные типы, либо логировать и пробрасывать.
- Контекст при перевыбросе: `raise ServiceError(...) from err` — сохраняет цепочку.
- User-facing ошибки и internal — разделены (не отдавать traceback наружу).

## Async

- Если проект async (FastAPI, aiohttp) — **не смешивать** sync-блокирующие вызовы в event loop. Блокирующее IO/CPU — через `asyncio.to_thread` или пул.
- `async def` для IO-bound; чистый CPU-bound — отдельный процесс/пул, не корутина.
- Любая корутина с фоновой задачей имеет способ отмены (`asyncio.TaskGroup`, `CancelledError` пробрасывается, не глотается).
- Никаких голых `asyncio.create_task` без хранения ссылки и обработки исключений.

## База данных

- **SQLAlchemy 2.0** (typed, `Mapped[...]`) или **asyncpg** напрямую для простых случаев. ORM-магия минимизируется.
- Миграции — **Alembic**, файлы версионируются.
- Параметризованные запросы всегда — никакой строковой конкатенации SQL (защита от инъекций, [core/code-quality.md](../core/code-quality.md)).
- Транзакции явные (`async with session.begin():`), границы транзакции — в service-слое, не в repository.

## Web-фреймворк

- **FastAPI** по умолчанию (async, pydantic-валидация, OpenAPI из коробки).
- Pydantic-модели для request/response — валидация на границе, типы — source of truth.
- Зависимости через `Depends`, не глобальные синглтоны.
- Flask/Django — только если есть явная причина (legacy, admin-heavy) и это зафиксировано в ADR.

## Тесты

- **pytest** + `pytest-asyncio` для async.
- Фикстуры для setup, не глобальное состояние между тестами.
- Параметризация через `@pytest.mark.parametrize` (аналог table-driven).
- Unit-тесты — без реальной сети/БД (моки, in-memory). Integration — отдельно, помечены маркером:

~~~python
@pytest.mark.integration
async def test_repo_persists_invite(db_session): ...
~~~

~~~bash
pytest tests/unit                       # быстрые
pytest -m integration                   # интеграционные
~~~

- `freezegun`/инъекция времени вместо реального времени; никаких `time.sleep()` для синхронизации (см. [core/quality-gates.md](../core/quality-gates.md)).

## Логирование

- `structlog` или stdlib `logging` со structured-форматтером. Не `print()`.
- Structured key-value, не f-строки в сообщении:

~~~python
logger.info("invite created", invite_id=invite.id, tenant_id=tenant_id)
~~~

- Запрет на логирование секретов и ПД (пароли, токены, email в открытом виде где это ПД) — `[REDACTED]`.

## Чистая сборка (clean build) — линтинг, типы, формат

- **ruff** — линтер + форматтер (заменяет flake8/isort/black). Строгий конфиг в `pyproject.toml`.
- **mypy --strict** (или pyright strict) — типы.
- Это и есть «без warnings» для Python из [core/quality-gates.md](../core/quality-gates.md):

~~~bash
ruff check .          # линт без нарушений
ruff format --check . # формат
mypy src              # типы без ошибок
pytest                # тесты зелёные
~~~

Любое нарушение ruff/mypy = задача не завершена. Подавление (`# noqa`, `# type: ignore`) — только с кодом и причиной.

## Специфические запреты

- Мутабельные дефолтные аргументы (`def f(x=[])`) — запрещены, классический баг.
- `import *` — запрещён.
- Глобальное мутабельное состояние с бизнес-данными — запрещено, всё через DI/зависимости.
- `eval`/`exec` на пользовательском вводе — запрещено.
- `assert` для рантайм-валидации в production-коде — запрещён (вырезается при `-O`); assert только в тестах.
- Бизнес-логика в `__init__.py` — запрещена (только реэкспорт).
- `requirements.txt` как основной манифест — использовать `pyproject.toml` + `uv.lock`.

## Python-специфичные паттерны

**Dependency injection через конструктор / FastAPI Depends**, не через глобальные синглтоны:

~~~python
class InviteService:
    def __init__(self, repo: InviteRepository, mailer: Mailer) -> None:
        self._repo = repo
        self._mailer = mailer
~~~

**Pydantic-модель на границе, dataclass внутри домена** — валидация снаружи, чистые типы внутри. DI-фреймворки (dependency-injector) на старте не нужны — конструкторов достаточно.
