# overlays/codex/ — оверлей принуждения для рантайма Codex CLI

Воспроизводит слой принуждения регламента на **Codex CLI** (OpenAI). Несёт **только плумбинг** —
контент метода и ролей живёт в общем ядре (`core/`, `roles/`, …), побайтово общем с claude-оверлеем.
Структура и форма — [ADR-010](../../docs/adr/010-multimodel-core-overlays.md) / [ADR-011](../../docs/adr/011-process-layer-and-multimodel-build.md);
карта возможностей Codex — [runtime-capability-map](../../docs/evidence/runtime-capability-map.md);
эмпирика песочницы — [g2-findings](../../docs/evidence/g2-findings.md).

Генератор кладёт содержимое этого каталога в **корень** целевого проекта: `AGENTS.md` + `.codex/`.

## Что внутри

### `AGENTS.md` — вход (авточтение Codex), собирается генератором

Per-harness нативный вход (ADR-012): Codex авто-читает `AGENTS.md`. **Несёт КОНТЕНТ сам** (проектная
специфика + роутеры в `core/`), НЕ указатель «читай CLAUDE.md»; файла `CLAUDE.md` в codex-проекте нет.
Генератор собирает его из двух частей: `_agents-header.md` (codex-delta: нет slash → печатная `R D T`,
роли = `.codex/agents/*.toml` + тиры песочницы, хуки = accountability, память, вторая модель) **+ общее
тело входа** (`ENTRY-BODY` из шаблона `CLAUDE.md` — одно на оба рантайма, без дрейфа). Маркеры
`ROLES-TABLE` в теле — нейтральную таблицу `R → roles/*.md` генерит `sync-roles.py`.

В пакете лежит только фрагмент `_agents-header.md` (полный `AGENTS.md` появляется при генерации проекта).

### `.codex/agents/*.toml` — роли как кастомные агенты Codex

Каждый — `sandbox_mode` + `developer_instructions`-указатель в канонический `roles/<роль>.md`.
Tool-scoping ролей воспроизводится **тиром песочницы Codex**:

| Тир | Роли | Codex | Гарантия |
|---|---|---|---|
| read-only | reviewer, auditor | `sandbox_mode="read-only"` | **аппаратно** (seatbelt, G2-verified) |
| workspace-write | developer, qa-e2e, debugger, devops | `sandbox_mode="workspace-write"` | **аппаратно** |
| docs-only | ba, qa-uat, sa, architect | `workspace-write` + прозовый запрет | **проза** (G2 RED, живой агент — карв-аут структурно недостижим на Codex 0.138.0: cwd всегда писибелен) |
| scratchpad-only | red-team, blue-team, arbiter | `workspace-write` + прозовый запрет | **проза** |

Codex схлопывает три write-тира Claude Code (read-only / docs-only-Write / code) в бинарное
read-only vs workspace-write; средний тир («пишет .md, но не код») аппаратного эквивалента на
Codex 0.138.0 **не имеет** → деградирует в прозу. Матрица гарантий ([core/portability.md](../../core/portability.md))
фиксирует это честно.

### `.codex/skills/*/SKILL.md` — авто-подтяг знания

Формат идентичен Claude Code (`name`+`description` frontmatter, тело — указатель в `core/*.md`,
контент не дублируется). Universal-скиллы: `debugging`, `code-quality`, `memory`, `spec-driven`.
Discovery — нативный Codex Agent Skills (репо-каталог `.codex/skills/` у codex 0.138.0).

### `.codex/hooks.json.example` — хуки-гейты (опт-ин)

Аналог `.claude/settings.json.example`. Канонический формат = **Claude-Code-совместимый `hooks.json`**
(события PascalCase `PostToolUse`/`Stop`/`PreCompact`, `command`-строка-путь, `matcher`-имя тула —
сверено с реальными plugin-хуками codex 0.138.0). **KL-7 (живой `codex exec`, 6 сессий):** из
user/repo-конфига в **headless** режиме хуки **НЕ срабатывают** даже с `--dangerously-bypass-hook-trust`
и корректной схемой — рабочие хуки 0.138.0 = plugin-манифест + интерактивный TUI-trust («Trust all and
continue»). Плюс: `[hooks]` в `config.toml` принимает мусор без ошибки (тихий провал валидации). →
Регламентный хук-гейт на Codex **деградирует в accountability**; для жёсткого энфорсмента —
**CI/pre-commit**. Reference-скрипты `.claude/hooks/` под Codex-payload требуют адаптации (в `.codex/hooks/`).
Детали — [g2-findings → KL-7](../../docs/evidence/g2-findings.md).

## Известные деградации (проза вместо аппаратного)

- **Slash-команды** (`/role`, `/panel`, `/kickoff`) — на Codex нет кастомного slash-примитива. `R D T`
  остаётся печатной конвенцией.
- **docs-only / scratchpad-only тиры** — проза (G2 RED, живой агент: cwd всегда писибелен, карв-аут недостижим).
- **Запрет Bash у арбитра** (на Claude Code аппаратно через отсутствие Bash) — на Codex проза.
- **Хуки** — wired, активация KL-7-pending.

Все деградации — в матрице гарантий [core/portability.md](../../core/portability.md); эмпирика
G2/KL-7 — в [g2-findings](../../docs/evidence/g2-findings.md).

**Проверка готовности (P5):** `python3 regimen-doctor.py` harness-aware — детектит обвязку (codex),
рапортует **состояние, не наличие**: вход `AGENTS.md`, агент-профили `.codex/agents/*.toml` с валидным
`sandbox_mode` (read-only/full = аппаратно), и честный класс хуков/docs-only-тиров (= accountability,
KL-7/G2). На Claude Code тот же doctor рапортует, активны хуки или дормантны (`settings.json` vs `.example`).
