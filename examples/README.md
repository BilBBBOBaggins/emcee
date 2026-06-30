# examples/ — один сквозной рабочий пример

Эта папка показывает, **как выглядят заполненные артефакты** пакета на одном маленьком, но сквозном примере. Она не копируется в реальный проект — это демонстрация формата, на которую ссылаются роли и `core/task-protocol.md`.

## Пример-проект

**Acme Teams** — вымышленный B2B SaaS (управление командами). Стек: Go API (модульный монолит) + Next.js фронтенд. Фича первого дня — **«Пригласить участника по email»**.

Это связка `Go + modular-monolith + b2b-saas` из пакета: backend на [stack/go.md](../stack/go.md), фронт на [stack/react-nextjs.md](../stack/react-nextjs.md), композиция [architecture/modular-monolith.md](../architecture/modular-monolith.md), домен [domain/b2b-saas.md](../domain/b2b-saas.md).

## Что внутри

| Файл | Что демонстрирует | Кто автор в пайплайне |
|------|-------------------|------------------------|
| [CLAUDE.example.md](CLAUDE.example.md) | заполненный `CLAUDE.md` — все `{{...}}` подставлены, оставлен один testing-вариант | — (старт проекта) |
| [docs/day-1-guide.example.md](docs/day-1-guide.example.md) | **ключевой артефакт** — гайд дня с задачами, блоком `Промпт для Claude Code`, `После выполнения`, `Коммит` | architect (разбивает следующий срез) |
| [docs/PROJECT-STATE.example.md](docs/PROJECT-STATE.example.md) | файл статуса, который читает architect на входе в день | architect |
| [docs/specs/invite-teammate.example.md](docs/specs/invite-teammate.example.md) | спецификация фичи | SA |
| [docs/adr/001-modular-monolith.example.md](docs/adr/001-modular-monolith.example.md) | architecture decision record | architect |
| [docs/scenarios-1-2-invite-teammate.example.md](docs/scenarios-1-2-invite-teammate.example.md) | пользовательские сценарии (вход для QA UAT) | BA |
| [docs/test-cases-1-2-invite-teammate.example.md](docs/test-cases-1-2-invite-teammate.example.md) | формальные тест-кейсы (вход для QA E2E) | QA UAT |
| [docs/PROCESS-METRICS.example.md](docs/PROCESS-METRICS.example.md) | **opt-in** лог окупаемости тяжёлого процесса (C+/панель/QA) — для проверки СТОП-гейтов ADR-002/003; для простого проекта не заводить | оператор |

`<DT>` в именах = «день-задача». Здесь фича закреплена за Днём 1, Задачей 2 (фронтенд), поэтому её сценарии и тест-кейсы — `…-1-2-…`. Полная конвенция имён — [core/task-protocol.md](../core/task-protocol.md).

## Как этим пользоваться

1. Прочитай [docs/day-1-guide.example.md](docs/day-1-guide.example.md) — это сердце системы команд `R D T`. Команда `1 1 1` = developer берёт Задачу 1 из этого гайда.
2. Посмотри связку **сценарии → тест-кейсы**: как пользовательский сценарий BA превращается в формальный тест-кейс с UI-селекторами и Given/When/Then.
3. Скопируй нужные форматы в свой `docs/`, переименовав `*.example.md` → `*.md` и заполнив под свою фичу.

Расширение `.example.md` — чтобы файлы не путались с настоящими артефактами проекта и не подхватывались инструментами как реальные задачи.
