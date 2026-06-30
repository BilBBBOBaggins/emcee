# G2 — docs-only на Codex: эмпирический результат (живой бинарь codex 0.138.0)

> Тест проведён P4-агентом на `codex-cli 0.138.0` (`/opt/homebrew/bin/codex`), macOS seatbelt
> (`sandbox-exec`). Метод: `codex sandbox -- <команда>` запускает произвольную команду под той же
> OS-песочницей, что и агент. Это тестирует **аппаратную границу ниже слоя тулов** — `apply_patch`,
> raw-shell и MCP-запись все сводятся к одним и тем же write-syscall'ам, которые seatbelt либо
> пропускает, либо нет. Поэтому тест raw-write под профилем покрывает все три «вектора атаки» сразу.

## Что доказано (аппаратные факты)

| Тир | Codex-конфиг | Результат | Класс |
|---|---|---|---|
| **read-only** (reviewer, auditor) | `sandbox_mode = "read-only"` | Запись в `src/` И `docs/` → `Operation not permitted`. Блокируется seatbelt'ом. Воспроизведено многократно. | **GREEN — аппаратно** |
| **full** (developer, qa-e2e, debugger, devops, architect-код) | `sandbox_mode = "workspace-write"` | Документированный стабильный путь; в реальной агент-сессии делает workspace писибельным. | **GREEN — аппаратно** (стабильный документированный конфиг) |
| **docs-only** (ba, qa-uat, sa, arbiter, red/blue — пишут только в `docs/`/`scratchpad/`, не в `src/`) | стабильный путь структурно неспособен; per-path только через нестабильный `[permissions]`-enum | **ПОДТВЕРЖДЕНО живым агентом:** карв-аут «write `docs/`, deny `src/`» недостижим практическим конфигом (см. ниже). | **RED (стабильный путь) — деградирует в прозу+accountability** |

## Почему docs-only = AMBER, а не GREEN/RED

1. **Машинерия присутствует** (не RED — способность не отсутствует). Реверс схемы из бинаря:
   - Стабильный путь: `sandbox_mode = "workspace-write"` + `[sandbox_workspace_write]` с
     `writable_roots = [...]`, `exclude_tmpdir_env_var`, `exclude_slash_tmp`.
   - Нестабильный путь (gated «unstable features»): `[permissions.<profile>]`-система,
     `default_permissions = "<profile>"` (top-level), `--permissions-profile <name>`. Структура
     профиля (`PermissionProfileToml`): поля `deny_read`, `description`, `extends`, `workspace_roots`
     (`WorkspaceRootsToml`-структ), `filesystem` (`FilesystemPermissionsToml`), `network`. Фильтр
     ФС — `FileSystemSandboxEntry { access, glob/path, permission_profile }`, `glob_scan_max_depth`,
     `entries`. Точную TOML-инкантацию untagged-enum `FilesystemPermissionToml` за разумный таймбокс
     закрыть не удалось (схема недокументирована и помечена нестабильной).
2. **Стабильный путь (`workspace-write` + `writable_roots`) СТРУКТУРНО НЕСПОСОБЕН — подтверждено живым
   агентом.** Решающий тест (`codex exec -s workspace-write`, `writable_roots=["<proj>/docs"]`, агент
   получил задачу записать в `docs/ok.md` И `src/bad.go`): **обе записи прошли** (ground-truth файлы
   на диске подтверждают `src/bad.go` записан). Структурная причина (сверена с бинарём
   `SandboxWorkspaceWrite.ts`): поля = `writable_roots`, `network_access`, `exclude_tmpdir_env_var`,
   `exclude_slash_tmp` — **опции исключить cwd НЕТ**. `writable_roots` **добавляет** к дефолтному
   writable-набору (cwd), а не ограничивает его. cwd всегда писибелен → `src/` под cwd всегда писибелен.
3. **`workspace_roots` (поле профиля) — булевы тумблеры, не список путей** (`expected a boolean` на
   `["docs"]`; поля вида `git`/`local`/`enabled`). Не даёт «writable = только docs».
4. **Единственный per-path-механизм — нестабильный `[permissions].filesystem` untagged-enum**
   (`FilesystemPermissionToml`: `entries`/`glob`/`deny_read`). Помечен «unstable features», точную
   TOML-инкантацию закрыть не удалось за ~15 проб в двух сессиях. Строить docs-only-тир на нём =
   хрупко (схема меняется между версиями codex; 0.138→0.142+ уже вышла) — инженерно не оправдано.

**Вывод (definitive):** аппаратный docs-only на Codex 0.138.0 **недостижим практическим конфигом** —
стабильный путь структурно неспособен (cwd всегда писибелен, доказано живым агентом), `workspace_roots`
= тумблеры, per-path только через нестабильный enum. Это **RED для стабильного пути**, сильнее прежнего
AMBER. **Следствие для матрицы:** docs-only роли = `sandbox_mode="workspace-write"` + **прозовый
констрейнт «пиши только в `docs/`/`scratchpad/`»** (accountability), потому что `read-only` сломал бы их
способность производить артефакты. Клетка деградирует в прозу — закрыто, не TODO.

## KL-7 — активация хуков Codex: ПРОВЕРЕНО на живом `codex exec` (6 сессий)

**Вердикт: ни один хук НЕ сработал в headless `codex exec` (0.138.0).** Это не «не тестировано» —
это «тестировано исчерпывающе, не активируется из user/repo-конфига в exec-режиме».

**Что точно установлено:**
- Фича `CodexHooks` включена по умолчанию (видно в session-логе `features=[…,CodexHooks,…]`).
- События (enum, PascalCase в конфиге): `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`,
  `PostCompact`, `SessionStart`, `UserPromptSubmit`, `Stop`, `SubagentStart`, `SubagentStop`.
- **Канонический формат = Claude-Code-совместимый `hooks.json`** (из реальных plugin-хуков
  `~/.codex/.tmp/plugins/*/hooks.json`): `{"hooks":{"PostToolUse":[{"matcher":"Bash","hooks":[{"type":
  "command","command":"./scripts/x.sh"}]}],"Stop":[…]}}`. Ключи событий **PascalCase**, `command` —
  **строка-путь** (не массив), `matcher` — имя тула.
- **Два гейта активации:** (1) фича включена; (2) **persisted trust** — интерактивный промпт TUI
  («These hooks run outside the sandbox after you trust them. [Trust all and continue] / [Continue
  without]»); для автоматизации — флаг `--dangerously-bypass-hook-trust`.
- **Тихий провал валидации:** `[hooks]` в `config.toml` принимает произвольные имена событий и типов
  БЕЗ ошибки (проверено `codex sandbox`). Мисконфиг хука не даёт обратной связи.

**Что НЕ сработало (исчерпывающе):** хук не запустился в `codex exec` при — корректной канонической
схеме (PascalCase `Stop` + строка-путь к реальному `.sh`), `--dangerously-bypass-hook-trust`
(предупреждение «hooks may run without review» подтверждено активным), несколько событий (`Stop`,
`PostToolUse`, `session_start`, `user_prompt_submit`), разные sandbox-режимы, завершившиеся сессии
(тул-коллы исполнялись, агент останавливался). Маркер-файл не появился ни разу.

**Интерпретация:** рабочие хуки в 0.138.0 существуют как **plugin-хуки** (`hooks.json` через
plugin-манифест — отдельный, тяжёлый путь загрузки), а trust-промпт — **TUI-аффорданс**. Путь
«user/repo `[hooks]` в `config.toml` → exec» либо не поддержан, либо требует интерактивной TUI-сессии
для granting trust. В **интерактивном `codex` TUI** хуки, вероятно, срабатывают (после granting trust)
— но это headless-агенту/CI недоступно без интерактива.

**Следствие для регламента:** на Claude Code хуки-гейты (`settings.json`) срабатывают во ВСЕХ режимах
(включая headless). На Codex 0.138.0 регламентные хуки-гейты из конфига в headless-режиме **НЕ
активируются** → клетка матрицы «хуки» = **деградирует в accountability** (обязательство под запись),
а для жёсткого энфорсмента на Codex предпочтительны **CI/pre-commit**, не рантайм-хуки. Это сильнее
прежнего «KL-7-pending»: подтверждено эмпирически, не отложено.

Док-предупреждение (сохраняет силу): `PreToolUse` — не полная граница энфорсмента → docs-only через
PreToolUse-хук был бы ложной гарантией (ADR-010 уже отклонил в пользу permission-profile).

## Статус верификаций (всё закрыто живой сессией)

- [x] **docs-only аппаратность** — ЗАКРЫТО (RED, живой `codex exec`): стабильный путь структурно
      неспособен (cwd всегда писибелен, агент записал `src/`), `workspace_roots`=тумблеры, per-path
      только через нестабильный `[permissions]`-enum. Клетка = проза+accountability. Не TODO.
- [x] **KL-7** — ЗАКРЫТО (живой `codex exec`, 6 сессий): хуки из конфига в headless не срабатывают.
      Клетка хуков = accountability; жёсткий гейт на Codex → CI/pre-commit.
- [ ] **(низкий приоритет, не блокер)** Точная форма `[permissions].filesystem`-профиля — если
      когда-нибудь потребуется аппаратный docs-only/секрет-deny; нестабильная схема, ждать
      стабилизации/доков codex. Сейчас инженерно не оправдано (хрупко по версиям).

---

**Итог G2+KL-7:** обе живые верификации закрыты. Матрица гарантий ([core/portability.md](../../core/portability.md))
полностью заземлена на эмпирике 0.138.0, ни одной «pending»-клетки. Аппаратно на Codex: read-only,
full-write, skills, авточтение входа. Проза/accountability: docs-only, scratchpad-only, no-Bash,
slash-dispatch, хуки. Это осознанная деградация (ADR-010/011), не дефект.
