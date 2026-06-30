#!/usr/bin/env python3
"""
new-project.py — генератор проекта из emcee (cookie-cutter).

Собирает свежий проект: копирует core/ + roles/, выбранные stack/architecture/domain,
заполняет что может в CLAUDE.md, бутстрапит docs/, опционально кладёт .claude/-обвязку,
и — главное — если выбранный стек ещё НЕ описан, генерирует скелет stack/<name>.md
по контракту (с обязательным разделом «Чистая сборка») и выдаёт промпт для дозаполнения.

Примеры:
  ./new-project.py --list
  ./new-project.py --name "Acme Teams" --dir ../acme \
      --backend go --frontend react-nextjs \
      --arch modular-monolith,multi-tenant --domain b2b-saas \
      --testing bdd --wiring yes
  ./new-project.py --name "Edge Proxy" --dir ../edge --backend rust --frontend none
      # rust ещё не описан -> создаст stack/rust.md скелет

Без флагов в терминале — спросит интерактивно.
"""
from __future__ import annotations
import argparse, os, re, shutil, sys

PACK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PACK)
from _pack_lib import LINK, md_files, local_target  # общий обход .md + парсинг ссылок (находка #4)

SKIP_TOP = {"new-project.py", "examples", "README.md", ".git", ".gitignore", "docs"}
TESTING = {"bdd": "Вариант 1", "test-along": "Вариант 2", "tdd": "Вариант 3"}


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-")


def available(folder: str) -> list[str]:
    d = os.path.join(PACK, folder)
    if not os.path.isdir(d):
        return []
    return sorted(
        f[:-3] for f in os.listdir(d)
        if f.endswith(".md") and not f.startswith("_")
    )


def ask(prompt: str, default: str = "") -> str:
    if not sys.stdin.isatty():
        return default
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def ask_multi(prompt: str, options: list[str]) -> list[str]:
    print(f"\n{prompt}")
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    raw = ask("Выбери номера через запятую (пусто = ничего)")
    out = []
    for tok in raw.split(","):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= len(options):
            out.append(options[int(tok) - 1])
        elif tok in options:
            out.append(tok)
    return out


def read(p): return open(p, encoding="utf-8").read()
def write(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(t)


def neutralize_dead_links(target: str) -> int:
    """[text](path) -> text для ссылок, чья цель не существует в сгенерированном
    проекте (ссылки на модули, которые не выбрали). Обход .md и фильтрация ссылок —
    общий примитив _pack_lib (тот же, что в selftest.py/regimen-doctor.py); здесь —
    переписывание строки, поэтому код-фенсы трекаем локально."""
    fixed = 0
    for p in md_files(target):
        d = os.path.dirname(p)
        in_fence = False
        out_lines = []
        changed = False
        for line in read(p).splitlines(keepends=True):
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                out_lines.append(line)
                continue
            if in_fence:
                out_lines.append(line)
                continue

            def repl(m):
                nonlocal changed
                tt = local_target(m.group(2))
                if tt is None or os.path.exists(os.path.normpath(os.path.join(d, tt))):
                    return m.group(0)
                changed = True
                return m.group(1)  # мёртвая ссылка -> оставить только текст

            out_lines.append(LINK.sub(repl, line))
        if changed:
            write(p, "".join(out_lines))
            fixed += 1
    return fixed


# ---------- CLAUDE.md transforms (each best-effort, never fatal) ----------

def fill_claude(text: str, name: str, stacks: list[str], testing: str, warns: list[str]) -> str:
    text = text.replace("{{PROJECT_NAME}}", name)

    # Стек: заменить блок между "## Стек" и "## Архитектура"
    try:
        bullets = "\n".join(f"- {s}" for s in stacks) or "- {{стек проекта}}"
        text = re.sub(r"(## Стек\n).*?(\n## Архитектура)",
                      lambda m: m.group(1) + "\n" + bullets + "\n" + m.group(2),
                      text, count=1, flags=re.S)
    except Exception:
        warns.append("не смог заполнить секцию '## Стек' — заполни вручную")

    # Testing philosophy: оставить выбранный вариант
    if testing in TESTING:
        keep = TESTING[testing]
        try:
            m = re.search(r"(## Testing philosophy\n).*?(\n## Специфика проекта)", text, flags=re.S)
            if m:
                variants = re.split(r"(?=### Вариант )", m.group(0))
                head = variants[0]
                head = re.sub(r"\{\{Выбери один из трёх[^}]*\}\}\n*", "", head)
                chosen = [v for v in variants[1:] if v.startswith(f"### {keep}")]
                newblock = head + ("".join(chosen) if chosen else "")
                text = text[:m.start()] + newblock + text[m.end():]
        except Exception:
            warns.append("не смог сократить 'Testing philosophy' до одного варианта — оставлены все")
    return text


# ---------- per-harness вход (ADR-012) ----------

ENTRY_BODY_MARK = "<!-- ENTRY-BODY:START"


def assemble_codex_entry(filled_entry: str, warns: list[str]) -> str:
    """ADR-012: codex-вход `AGENTS.md` = title/desc + codex-delta-хедер + ОБЩЕЕ ТЕЛО (ENTRY-BODY) из
    заполненного шаблона входа. Тело — единственный источник (то же, что у CLAUDE.md), хедер —
    per-harness. Так codex-проект получает нативный вход С КОНТЕНТОМ, без файла CLAUDE.md и без
    указателя «читай CLAUDE.md»."""
    header_path = os.path.join(PACK, "overlays", "codex", "_agents-header.md")
    if ENTRY_BODY_MARK not in filled_entry or not os.path.exists(header_path):
        warns.append("codex-вход: нет ENTRY-BODY-маркера или _agents-header.md — AGENTS.md = тело как есть")
        return filled_entry
    head, _, body_rest = filled_entry.partition(ENTRY_BODY_MARK)
    body = ENTRY_BODY_MARK + body_rest
    header = read(header_path)
    return head.rstrip() + "\n\n" + header.strip() + "\n\n" + body.lstrip() + "\n"


# ---------- docs/ bootstrap ----------

DAY_GUIDE_STUB = """# День 1 — <<NAME>>

**Цель дня:** {{первая фича/итерация}}.

> Формат и рабочий пример — в emcee/examples/docs/day-1-guide.example.md.
> Числовые команды (`R D T`) и имена артефактов — в core/task-protocol.md.

## Задача 1 — {{название}}

**Затронутые файлы:** {{...}}

### Промпт для Claude Code

~~~
{{Точное ТЗ для developer: контракт, требования, какие файлы, какие тесты.}}
~~~

### После выполнения

~~~bash
{{build+test команда с сохранением лога}}
~~~

### Коммит

~~~bash
git add {{файлы}}
git commit -m "{{тип}}: {{описание}}"
~~~
"""

PROJECT_STATE_STUB = """# PROJECT-STATE — <<NAME>>

**Снимок текущего состояния, не журнал.** Architect читает на входе в день и
перезаписывает на месте в конце дня: решённое — убирает, устаревшее — затирает.
История («что и когда сделано») живёт в git (`git log`), решения «почему» — в
`docs/adr/`. Здесь — только то, что нужно, чтобы продолжить СЕЙЧАС. Цель ≤ ~1 экран.

Last updated: {{YYYY-MM-DD}}

## Снимок
- Фаза: старт.
- Стек/команды — во входном файле регламента (здесь не дублировать).

## В работе
- {{первая фича}}

## Риски / блокеры
- {{...}}

## Open questions
- [ ] {{...}}

## Следующий день
- {{...}}
"""

# Делегирующая инициализация: команды стандартных тулов, а не сохранённый scaffold —
# актуальная версия тула всегда свежее зашитой копии (см. docs/adr/001-scope-process-overlay.md).
INIT_CMDS = {
    "go": "go mod init <module-path>",
    "python": "uv init   # или: python -m venv .venv && . .venv/bin/activate && pip install -e .",
    "react-nextjs": "npx create-next-app@latest .",
    "rust": "cargo init",
    "node": "npm init -y",
    "svelte": "npx sv create .",
}

# glob-паттерны для path-scoped активации стек-скиллов (`paths:` во frontmatter скилла).
# Срабатывают НАДЁЖНО на матчащих файлах (в отличие от model-decided `description` ~50%).
# Неизвестный стек -> нет paths (остаётся только description). См. docs Claude Code → skills/memory.
STACK_PATHS = {
    "go": "**/*.go, go.mod, go.sum",
    "python": "**/*.py, pyproject.toml",
    "react-nextjs": "**/*.tsx, **/*.ts, **/*.jsx, **/*.js",
    "rust": "**/*.rs, Cargo.toml",
    "node": "**/*.js, **/*.ts, package.json",
    "svelte": "**/*.svelte, **/*.ts, **/*.js",
}


def init_commands_for(stacks: list[str]) -> str:
    lines = []
    for s in stacks:
        cmd = INIT_CMDS.get(slugify(s), f"# TODO: инициализируй {s} стандартным тулом этого стека")
        lines.append(f"  {cmd}")
    return "\n".join(lines) or "  # TODO: инициализируй проект стандартным тулом выбранного стека"


DAY0_GUIDE_STUB = """# День 0 — инициализация проекта <<NAME>>

**Цель:** превратить пустой каталог в собранный каркас приложения, на котором `{{test-command}}`
зелёный, ПРЕЖДЕ чем брать День 1. Пакет даёт регламент, но НЕ владеет тулчейном —
инициализацию делегируем стандартным тулам (их актуальная версия всегда свежее зашитого скелета).

> Запусти как developer: `1 0 1`. Имена артефактов и числовые команды — core/task-protocol.md.

## Задача 1 — инициализировать стек и получить зелёный baseline

### Промпт для Claude Code

~~~
Инициализируй проект стандартными тулами под выбранный стек, затем впиши во входной файл регламента
фактические команды сборки/тестов вместо {{build-command}}/{{test-command}}. Шаги:

<<INIT_COMMANDS>>

Затем: добавь .gitignore под стек; создай минимальный «hello world» + один проходящий тест,
чтобы появился зелёный baseline. Убедись, что clean build (stack/<stack>.md → «Чистая сборка»)
проходит без warnings.
~~~

### После выполнения

~~~bash
{{build+test команда}}   # должна быть зелёной — это baseline, от которого стартует День 1
~~~

### Коммит

~~~bash
git add -A
git commit -m "chore: инициализация каркаса проекта (День 0)"
~~~
"""


def safe_copy_file(src: str, dst: str, overlay: bool, skipped: list[str], target: str) -> bool:
    """Копирует файл. В overlay-режиме НЕ перезаписывает существующий — копит в skipped."""
    if overlay and os.path.exists(dst):
        skipped.append(os.path.relpath(dst, target))
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def safe_copy_tree(src_dir: str, dst_dir: str, overlay: bool, skipped: list[str], target: str):
    """Рекурсивно копирует дерево, не затирая существующие файлы в overlay-режиме."""
    for root, _, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        for fn in files:
            d = os.path.normpath(os.path.join(dst_dir, rel, fn))
            safe_copy_file(os.path.join(root, fn), d, overlay, skipped, target)


def safe_write(path: str, text: str, overlay: bool, skipped: list[str], target: str) -> bool:
    """Пишет сгенерированный файл. В overlay не затирает существующий."""
    if overlay and os.path.exists(path):
        skipped.append(os.path.relpath(path, target))
        return False
    write(path, text)
    return True


def main():
    ap = argparse.ArgumentParser(description="Генератор проекта из emcee")
    ap.add_argument("--list", action="store_true", help="показать доступные модули и выйти")
    ap.add_argument("--name")
    ap.add_argument("--dir", help="каталог нового проекта (не должен существовать или пуст)")
    ap.add_argument("--backend", default=None, help="имя стека бэкенда (или новое имя -> сгенерится скелет; none)")
    ap.add_argument("--frontend", default=None, help="имя стека фронта (или новое имя; none)")
    ap.add_argument("--arch", default=None, help="архитектуры через запятую")
    ap.add_argument("--domain", default=None, help="домены через запятую")
    ap.add_argument("--testing", choices=list(TESTING), default=None)
    ap.add_argument("--wiring", choices=["yes", "no"], default=None, help="класть исполняемую обвязку рантайма")
    ap.add_argument("--harness", choices=["claude-code", "codex"], default=None,
                    help="целевой рантайм: claude-code (дефолт, обвязка в .claude/) или codex "
                         "(AGENTS.md + .codex/ из overlays/codex/). Статическое копирование git-дерева.")
    ap.add_argument("--mode", choices=["new", "overlay"], default=None,
                    help="new = кикстарт нового проекта (пустой каталог + Day-0 init); "
                         "overlay = наложить регламент на существующий проект (не затирая файлы)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    stacks_av, arch_av, dom_av = available("stack"), available("architecture"), available("domain")

    if a.list:
        print("stack/:       ", ", ".join(stacks_av))
        print("architecture/:", ", ".join(arch_av))
        print("domain/:      ", ", ".join(dom_av))
        print("testing:      ", ", ".join(TESTING))
        return 0

    if not sys.stdin.isatty():
        missing = [f for f, v in (("--name", a.name), ("--dir", a.dir)) if v is None]
        if missing:
            print(f"✗ В неинтерактивном режиме обязательны: {', '.join(missing)}.", file=sys.stderr)
            return 1

    name = a.name or ask("Название проекта", "My Project")
    target = a.dir or ask("Каталог проекта", f"../{slugify(name)}")
    target = os.path.abspath(target)

    def pick_stack(role, flag):
        if flag is not None:
            return flag
        v = ask(f"{role} стек (из [{', '.join(stacks_av)}], новое имя, или none)", "none")
        return v

    backend = pick_stack("Backend", a.backend)
    frontend = pick_stack("Frontend", a.frontend)

    archs = (a.arch.split(",") if a.arch is not None else ask_multi("Архитектурные паттерны:", arch_av))
    archs = [x.strip() for x in archs if x.strip()]
    doms = (a.domain.split(",") if a.domain is not None else ask_multi("Домены:", dom_av))
    doms = [x.strip() for x in doms if x.strip()]
    # Дефолт — test-along (лёгкий solo-режим): заявленная аудитория пакета — solo/small team,
    # для которой полный BDD-конвейер (SA→BA→QA-UAT→QA-E2E) — оверхед. BDD за явным выбором.
    # (ADR об охвате: docs/adr/001-scope-process-overlay.md)
    testing = a.testing or ask(f"Testing philosophy ({'/'.join(TESTING)})", "test-along")
    harness = a.harness or ask("Целевой рантайм (claude-code/codex)", "claude-code")
    if harness not in ("claude-code", "codex"):
        print(f"⚠ неизвестный рантайм '{harness}', использую 'claude-code'", file=sys.stderr)
        harness = "claude-code"
    _wlabel = ".claude/" if harness == "claude-code" else ".codex/"
    wiring = (a.wiring or ask(f"Класть опциональную {_wlabel} обвязку? (yes/no)", "yes")) == "yes"
    # Режим: new = кикстарт (пустой каталог + Day-0 init-guide); overlay = наложить регламент
    # на существующий проект, ничего не затирая (см. docs/adr/001-scope-process-overlay.md).
    mode = a.mode or ask("Режим (new = новый проект / overlay = существующий)", "new")
    if mode not in ("new", "overlay"):
        print(f"⚠ неизвестный режим '{mode}', использую 'new'", file=sys.stderr)
        mode = "new"
    overlay = mode == "overlay"

    # валидация выборов
    for x in archs:
        if x not in arch_av:
            print(f"⚠ архитектура '{x}' не найдена, пропускаю", file=sys.stderr)
    for x in doms:
        if x not in dom_av:
            print(f"⚠ домен '{x}' не найден, пропускаю", file=sys.stderr)
    archs = [x for x in archs if x in arch_av]
    doms = [x for x in doms if x in dom_av]

    # классификация стеков: нормализуем имя, матчим существующие по slug, дедупим по slug
    existing_by_slug = {slugify(x): x for x in stacks_av}
    existing_stacks, new_stacks, seen_slugs = [], [], set()
    for s in (backend, frontend):
        if not s:
            continue
        s = s.strip()
        if not s or s.lower() == "none":
            continue
        sl = slugify(s)
        if not sl:
            print(f"⚠ стек '{s}' даёт пустой slug — пропускаю", file=sys.stderr)
            continue
        if sl in seen_slugs:
            print(f"⚠ стек '{s}' (slug '{sl}') дублирует уже выбранный — пропускаю", file=sys.stderr)
            continue
        seen_slugs.add(sl)
        if sl in existing_by_slug:
            existing_stacks.append(existing_by_slug[sl])   # реальный пакетный стек
        else:
            new_stacks.append(s)                            # будет скелет stack/<slug>.md

    print("\n--- План ---")
    print(f"  Проект:        {name}")
    print(f"  Режим:         {mode}  ({'кикстарт нового' if not overlay else 'наложение на существующий, без затирания'})")
    print(f"  Каталог:       {target}")
    print(f"  Стек (есть):   {existing_stacks or '—'}")
    print(f"  Стек (новый):  {new_stacks or '—'}  (будет создан скелет stack/<name>.md)")
    print(f"  Архитектура:   {archs or '—'}")
    print(f"  Домен:         {doms or '—'}")
    print(f"  Testing:       {testing}")
    print(f"  Рантайм:       {harness}")
    print(f"  Обвязка:       {('да' if wiring else 'нет')}  ({_wlabel})")
    if a.dry_run:
        print("\n(dry-run — ничего не записано)")
        return 0

    if os.path.exists(target) and not os.path.isdir(target):
        print(f"\n✗ {target} существует и это не каталог. Останавливаюсь.", file=sys.stderr)
        return 1
    # new требует пустой каталог; overlay сознательно пишет в существующий проект (не затирая).
    if not overlay and os.path.isdir(target) and os.listdir(target):
        print(f"\n✗ {target} существует и не пуст (режим new). Для существующего проекта: --mode overlay.",
              file=sys.stderr)
        return 1

    warns: list[str] = []
    skipped: list[str] = []                      # overlay: файлы, которые уже были — не тронули
    created_target = not os.path.isdir(target)
    stack_bullets = existing_stacks + [slugify(s) for s in new_stacks]
    try:
        # 1) core/ + roles/
        safe_copy_tree(os.path.join(PACK, "core"), os.path.join(target, "core"), overlay, skipped, target)
        safe_copy_tree(os.path.join(PACK, "roles"), os.path.join(target, "roles"), overlay, skipped, target)

        # 2) стеки
        for s in existing_stacks:
            safe_copy_file(os.path.join(PACK, "stack", f"{s}.md"),
                           os.path.join(target, "stack", f"{s}.md"), overlay, skipped, target)
        for s in new_stacks:
            tmpl = read(os.path.join(PACK, "stack", "_TEMPLATE.md"))
            tmpl = tmpl.replace("{{STACK_NAME}}", s).replace("{{STACK_SLUG}}", slugify(s))
            safe_write(os.path.join(target, "stack", f"{slugify(s)}.md"), tmpl, overlay, skipped, target)

        # 3) architecture/ + domain/
        for x in archs:
            safe_copy_file(os.path.join(PACK, "architecture", f"{x}.md"),
                           os.path.join(target, "architecture", f"{x}.md"), overlay, skipped, target)
        for x in doms:
            safe_copy_file(os.path.join(PACK, "domain", f"{x}.md"),
                           os.path.join(target, "domain", f"{x}.md"), overlay, skipped, target)

        # 4) Вход регламента — per-harness нативный файл С КОНТЕНТОМ (ADR-012). Общее тело (ENTRY-BODY)
        #    одно (в шаблоне CLAUDE.md); генератор рендерит в нативное имя: claude-code → CLAUDE.md;
        #    codex → AGENTS.md (title + codex-delta-хедер + то же тело), и CLAUDE.md в codex НЕ кладётся.
        entry_filled = fill_claude(read(os.path.join(PACK, "CLAUDE.md")), name, stack_bullets, testing, warns)
        if harness == "codex":
            entry_text, entry_name = assemble_codex_entry(entry_filled, warns), "AGENTS.md"
        else:
            entry_text, entry_name = entry_filled, "CLAUDE.md"
        entry_path = os.path.join(target, entry_name)
        if overlay and os.path.exists(entry_path):
            regimen_name = entry_name.replace(".md", ".regimen.md")
            write(os.path.join(target, regimen_name), entry_text)
            warns.append(f"{entry_name} уже существует — регламент сохранён как {regimen_name}, слей вручную")
        else:
            write(entry_path, entry_text)

        # 4b) единый источник карты ролей + синхронизатор (нужны и в прозовом режиме:
        #     таблица ролей в CLAUDE.md генерируется из roles.json через sync-roles.py).
        for tool in ("roles.json", "sync-roles.py", "regimen-doctor.py", "_pack_lib.py"):
            src = os.path.join(PACK, tool)
            if os.path.exists(src):
                safe_copy_file(src, os.path.join(target, tool), overlay, skipped, target)

        # 5) Обвязка рантайма — СТАТИЧЕСКОЕ КОПИРОВАНИЕ git-дерева выбранного оверлея (по --harness),
        #    БЕЗ парсинга меток origin: и без манифеста (стоп-условие ADR-009/010/011). Общее ядро
        #    выше идентично для обоих рантаймов; здесь — только плумбинг.
        #    - claude-code: .claude/ (нативная позиция дефолтного рантайма = концептуальный
        #      overlays/claude-code/; см. overlays/README.md → documented mapping).
        #    - codex: вход AGENTS.md уже собран в секции 4 (ADR-012); здесь — только overlays/codex/.codex/
        #      обвязка (под --wiring). Файл CLAUDE.md в codex-проект НЕ кладётся.
        skills_dir = ".claude"  # куда генератор эмитит авто-скиллы стека/арх/домена
        if harness == "codex":
            skills_dir = ".codex"
            if wiring:
                cx = os.path.join(PACK, "overlays", "codex", ".codex")
                if os.path.isdir(cx):
                    safe_copy_tree(cx, os.path.join(target, ".codex"), overlay, skipped, target)
        else:  # claude-code
            if wiring and os.path.isdir(os.path.join(PACK, ".claude")):
                safe_copy_tree(os.path.join(PACK, ".claude"), os.path.join(target, ".claude"), overlay, skipped, target)

        # 5b) Авто-скиллы под выбранные модули (часть обвязки рантайма). Аддитивно: скилл — тонкий
        #     триггер с описанием, указывает на канонический файл (без дублей). Универсальные
        #     скиллы ядра (debugging/code-quality/memory/spec-driven) приехали выше с обвязкой.
        #     Роли, числовые команды и панель НЕ затрагиваются — это отдельный примитив. Формат
        #     SKILL.md идентичен на Claude Code и Codex; различается только каталог discovery
        #     (.claude/skills/ vs .codex/skills/).
        if wiring:
            def emit_skill(skill_name, canonical, desc, summary, paths=None):
                fm = f"---\nname: {skill_name}\ndescription: {desc}\n"
                # paths: — path-scoped glob-триггер. ПОДДЕРЖИВАЕТ ТОЛЬКО Claude Code (офиц. docs,
                # SKILL.md frontmatter: «glob patterns that limit when skill is activated»). Codex
                # skill-creator: «name + description — the only fields Codex reads; do not include
                # any other fields» → на Codex paths: не эмитим (неподдерживаемый ключ, утечка
                # Claude-изма + риск отлупа валидатором). Discovery у Codex — по description (C1 аудита).
                if paths and skills_dir == ".claude":
                    fm += f"paths: {paths}\n"
                fm += "---\n"
                body = (f"{fm}\n{summary}\n\n"
                        f"Полные правила — в `{canonical}` (от корня проекта). Прочитай файл целиком.\n")
                safe_write(os.path.join(target, skills_dir, "skills", skill_name, "SKILL.md"),
                           body, overlay, skipped, target)
            for s in stack_bullets:
                emit_skill(s, f"stack/{s}.md",
                           f"Конвенции стека {s} в этом проекте: структура, обработка ошибок, тесты, "
                           f"чистая сборка. Используй, когда пишешь или ревьюишь {s}-код.",
                           f"Правила работы со стеком {s}.",
                           paths=STACK_PATHS.get(s))
            for x in archs:
                emit_skill(x, f"architecture/{x}.md",
                           f"Архитектурный паттерн «{x}»: границы модулей, направление зависимостей, "
                           f"антипаттерны. Используй при проектировании или ревью структуры, "
                           f"затрагивающей этот паттерн.",
                           f"Архитектурный паттерн «{x}».")
            for x in doms:
                emit_skill(x, f"domain/{x}.md",
                           f"Доменные правила «{x}»: специфика, ограничения, compliance. Используй "
                           f"при работе с фичами этого домена.",
                           f"Домен «{x}».")

        # 6) docs/ bootstrap
        stacks_str = ", ".join(stack_bullets) or "—"
        safe_write(os.path.join(target, "docs", "PROJECT-STATE.md"),
                   PROJECT_STATE_STUB.replace("<<NAME>>", name).replace("<<STACKS>>", stacks_str),
                   overlay, skipped, target)
        # Day-0 (делегирующий init) — только для кикстарта нового проекта.
        if not overlay:
            day0 = DAY0_GUIDE_STUB.replace("<<NAME>>", name).replace(
                "<<INIT_COMMANDS>>", init_commands_for(stack_bullets))
            write(os.path.join(target, "docs", "day-0-guide.md"), day0)
        safe_write(os.path.join(target, "docs", "day-1-guide.md"),
                   DAY_GUIDE_STUB.replace("<<NAME>>", name), overlay, skipped, target)
        for sub in ("adr", "specs"):
            safe_write(os.path.join(target, "docs", sub, ".gitkeep"), "", overlay, skipped, target)

        # 7) проектный README — только для нового проекта (у существующего свой, не трогаем)
        if not overlay:
            write(os.path.join(target, "README.md"),
                  f"# {name}\n\nСгенерирован из emcee. Правила агента и команды — в [{entry_name}]({entry_name}).\n")

        # 8) почистить ссылки на невыбранные модули
        cleaned = neutralize_dead_links(target)
    except Exception as e:
        if created_target:
            shutil.rmtree(target, ignore_errors=True)
        print(f"\n✗ ошибка генерации: {e}"
              + (" (частичный результат удалён)" if created_target else
                 " (overlay — частичный результат оставлен, проверь вручную)"), file=sys.stderr)
        return 1

    # ---------- отчёт ----------
    print("\n✓ Регламент наложен на:" if overlay else "\n✓ Проект создан:", target)
    if overlay and skipped:
        print(f"\n  ⚠ overlay: {len(skipped)} существующих файлов НЕ тронуты:")
        for rel in sorted(skipped)[:12]:
            print(f"     • {rel}")
        if len(skipped) > 12:
            print(f"     … ещё {len(skipped) - 12}")
        print("     Если нужна свежая версия из пакета — сравни вручную (diff) и слей.")
    print("\nДальше:")
    print(f"  1. Заполни специфику в {entry_name} (архитектура, команды сборки/тестов, '## Специфика проекта').")
    if warns:
        print("     ⚠ авто-заполнение частично:")
        for w in warns:
            print("       -", w)

    if new_stacks:
        print("\n  2. НОВЫЕ СТЕКИ (создан скелет — дозаполни обязательно раздел «Чистая сборка»):")
        for s in new_stacks:
            f = f"stack/{slugify(s)}.md"
            print(f"     • {f}")
            print(f"       Промпт для Claude Code:")
            print(f'       «Заполни {f} по структуре stack/go.md и stack/python.md, но для {s}.')
            print(f'        ОБЯЗАТЕЛЬНО раздел «Чистая сборка»: какие команды значат clean build для {s}')
            print(f'        (компилятор/typecheck/линтер) — на него ссылается core/quality-gates.md.')
            print(f'        Удали неприменимые секции и верхний блок-предупреждение.»')

    # оставшиеся плейсхолдеры
    left = []
    for p in md_files(target):
        n = read(p).count("{{")
        if n:
            left.append((os.path.relpath(p, target), n))
    if left:
        print("\n  3. Незаполненные {{...}} плейсхолдеры:")
        for rel, n in sorted(left, key=lambda x: -x[1]):
            print(f"     {n:3}  {rel}")
        print("     Перечислить: grep -rn '{{' . --include='*.md'")

    # ссылки на невыбранные модули — нейтрализованы автоматически
    if cleaned:
        print(f"\n  4. Ссылки на невыбранные модули нейтрализованы в {cleaned} файл(ах) "
              f"([текст](битый-путь) → текст). Висячих ссылок не осталось.")

    if overlay:
        print(f"\n  5. Регламент лёг рядом с твоим кодом. Команды сборки/тестов в {entry_name} укажи "
              "фактические (проект уже инициализирован). Затем опиши docs/day-1-guide.md и запусти: '1 1 1'.")
    else:
        print("\n  5. Сначала День 0 (инициализация каркаса): запусти '1 0 1' по docs/day-0-guide.md — "
              "агент инициализирует стек стандартным тулом и получит зелёный baseline. "
              "Потом опиши docs/day-1-guide.md и запусти '1 1 1'.")
    print("\n  6. Перед первой реальной задачей прогони гейт готовности: python3 regimen-doctor.py "
          "(🟢 = регламент дозаполнен; 🔴 = плейсхолдеры/ссылки/команды чинить). Запускай повторно по мере правок.")
    if wiring:
        if harness == "codex":
            print("     Обвязка .codex/ скопирована (агенты-роли + скиллы). Вход рантайма — AGENTS.md "
                  "(Codex авто-читает). Хуки (опт-ин, KL-7-pending): см. .codex/hooks.json.example.")
        else:
            print("     Обвязка .claude/ скопирована (субагенты + /role). Хуки: mv .claude/settings.json.example .claude/settings.json")
    elif harness == "codex":
        print("     Прозовый режим Codex: AGENTS.md (вход) скопирован, .codex/ обвязки нет — "
              "роли как промпты (читай roles/<роль>.md), числовые команды R D T печатной конвенцией.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
