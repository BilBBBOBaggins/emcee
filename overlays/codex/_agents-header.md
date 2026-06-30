<!-- CODEX-DELTA-HEADER — генератор вставляет этот блок между title и общим телом входа (ENTRY-BODY общего шаблона) при сборке AGENTS.md. НЕ полный вход; полное тело (Стек, Команды, Обязательно читать, По ситуации, Testing) — общее, приезжает из тела. -->

> **Это `AGENTS.md` — вход регламента на рантайме Codex.** Codex авто-читает `AGENTS.md` в начале
> сессии (аналог авточтения `CLAUDE.md` у Claude Code). Ниже — **общее тело регламента** (проектная
> специфика + роутеры в нейтральное методическое ядро `core/`); этот верхний блок фиксирует только то,
> что на Codex **отличается** от Claude Code. Корпус методов/ролей не дублируется — он в `core/`/`roles/`.

## Что на Codex иначе, чем на Claude Code (харнесс-дельта)

- **Slash-команд нет.** `/role`, `/panel`, `/kickoff` ниже — примитив Claude Code. На Codex числовая
  грамматика `R D T` остаётся **печатной конвенцией**: пишешь «5 3 24» текстом, и Codex входит в роль,
  читая `.codex/agents/<агент>.toml` + канонический `roles/<роль>.md`. Сознательная прозовая
  деградация (матрица гарантий её фиксирует), не потеря метода.
- **Роли — кастомные агенты Codex** `.codex/agents/<имя>.toml` (`sandbox_mode` +
  `developer_instructions`-указатель в `roles/*`). Карта `R → роль` — в теле ниже («Маппинг ролей»);
  файл `.codex/agents/<agent>.toml` — sandbox-профиль этой роли. Tool-scoping → тиром песочницы:
  read-only (reviewer/auditor) и workspace-write (developer/qa-e2e/debugger/devops) — **аппаратно**;
  docs-only (ba/qa-uat/sa/architect) и scratchpad-only (red/blue/arbiter) — **проза** (`workspace-write`
  + honor; G2 RED: per-path карв-аут на Codex недостижим, cwd всегда писибелен).
- **Скиллы — `.codex/skills/<имя>/SKILL.md`** (формат идентичен Claude Code; тело — указатель в `core/*.md`).
- **Хуки-гейты = accountability.** KL-7 (живой `codex exec`): хуки из конфига в headless не срабатывают
  → для жёсткого гейта на Codex CI/pre-commit, не рантайм-хуки. Опт-ин пример — `.codex/hooks.json.example`.
- **Память** — у Codex свой механизм (`AGENTS.md`-иерархия + Codex memories opt-in), не Claude-Code-иерархия `CLAUDE.md`; дисциплина памяти (`core/memory.md`) переносится как есть.
- **Вторая модель для панели** (`core/adversarial-panel.md`): на рантайме Codex ты сам — Codex, поэтому
  второй парой глаз бери **иную** модель (Claude/иной профиль), не себя. Нет второй модели → честный фолбэк.

<!-- Этот файл — фрагмент, который генератор вставляет в AGENTS.md в КОРНЕ проекта; ссылки в нём
     относительны корню проекта (напр. `core/portability.md`), а не каталогу overlays/codex/.
     Линтер/regimen-doctor, запущенный на самом пакете, пометит их «висячими» — это ложное
     срабатывание: в материализованном AGENTS.md они резолвятся. На `../../` НЕ менять. -->
Полная матрица «роль × рантайм × аппаратно/проза» — [core/portability.md](core/portability.md).

---
