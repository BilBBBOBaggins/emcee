# overlays/ — рантайм-оверлеи принуждения

Этот пакет спроектирован на **нейтральном методическом ядре** (`core/`, `roles/`, `stack/`,
`architecture/`, `domain/` — побайтово общее для всех рантаймов) плюс **тонкие оверлеи**, которые
воспроизводят слой принуждения под конкретный рантайм (агенты, команды, хуки, проводка скиллов +
per-harness вход). См. [ADR-010](../docs/adr/010-multimodel-core-overlays.md),
[ADR-011](../docs/adr/011-process-layer-and-multimodel-build.md), [ADR-012](../docs/adr/012-entry-file-per-harness.md).

**Вход регламента — per-harness нативный файл (ADR-012):** `CLAUDE.md` (Claude Code) / `AGENTS.md`
(Codex), по одному на проект. Несёт проектную специфику (стек, роутеры, testing) + honest harness-delta,
указывает в `core/`. Общее **тело** входа — одно (маркеры `ENTRY-BODY` в `CLAUDE.md`); генератор
рендерит его в нативное имя per harness (на Codex — `_agents-header.md` + тело). **Codex-проект файла
`CLAUDE.md` НЕ получает.** Прежний инвариант «оверлей = только плумбинг, `CLAUDE.md` = общее ядро»
отменён ADR-012: общее ядро = `core/` (метод), вход — per-harness.

## Documented mapping: `.claude/` ≡ концептуальный `overlays/claude-code/`

**Claude Code — дефолтный рантайм, и его оверлей остаётся в нативной позиции `.claude/` в корне
пакета, а НЕ в `overlays/claude-code/`.** Это сознательное решение (вердикт адверсивной панели
`p4form`, [ADR-011](../docs/adr/011-process-layer-and-multimodel-build.md) §C):

- Рантайм Claude Code сканирует `.claude/` **в корне проекта** — это его нативный, требуемый им путь.
- Генератор всё равно кладёт claude-обвязку в `target/.claude/` независимо от позиции источника
  (асимметрия source↔target врождённая для любого генератора), поэтому перенос источника в
  `overlays/claude-code/` **не покупает консистентность системы** — только косметику layout пакета,
  ценой 16-файлового churn, symlink-хрупкости (Windows `core.symlinks=false`) и слома self-host.
- Эквивалентность фиксируется **этим абзацем доки**, а не layout-переносом (форма «C + mapping»).

**Правило чтения раскладки:**

| Путь | Что это | Позиция |
|---|---|---|
| `.claude/` | Оверлей рантайма **Claude Code** (дефолтный) | Нативная позиция в корне (= концептуальный `overlays/claude-code/`) |
| `overlays/<harness>/` | Оверлей **не-дефолтного** рантайма, нативная позиция которого НЕ в корне | напр. `overlays/codex/` |

`overlays/` заводится **только под не-дефолтные рантаймы**. Сегодня здесь — [`codex/`](codex/).

**Стоп-условие (move-later, не исполнять без выполнения всех трёх условий):** физический перенос
`.claude/ → overlays/claude-code/` переоткрывается ТОЛЬКО когда (а) `overlays/codex/` реально строится
и стабилен, (б) `sync-roles.py` стал N-рантайм-эмиттером, (в) подтверждён инвариант клонирования
(только macOS → symlink ок; иначе — задокументированный `core.symlinks`-fallback). До выполнения всех
трёх — не двигать (см. [p4form-arbiter](../docs/evidence/p4form-arbiter.md)).

## Как генератор выбирает оверлей

`new-project.py --harness claude-code|codex` (дефолт `claude-code`) — **статическое копирование
git-дерева**, без парсинга меток `origin:` и без манифеста (стоп-условие [ADR-009](../docs/adr/009-portability-boundary.md)):

- `--harness claude-code` → нейтральное ядро + вход `CLAUDE.md` (тело как есть) + `.claude/` (как раньше; регрессии нет).
- `--harness codex` → нейтральное ядро + вход `AGENTS.md` (собран: codex-delta-хедер + общее тело,
  ADR-012; **без `CLAUDE.md`**) + `.codex/` обвязка.

Нейтральное ядро (`core/roles/stack/architecture/domain`, `roles.json`, `sync-roles.py`,
`regimen-doctor.py`) копируется одинаково в обоих случаях. **Вход** — per-harness (см. выше), но из
**одного общего тела**, поэтому правка тела отражается в обоих входах без дрейфа.
