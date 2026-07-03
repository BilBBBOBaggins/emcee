"""_pack_lib.py — общие примитивы тулинга пакета: обход .md, чтение, парсинг локальных
ссылок, плейсхолдеры, sandbox-режимы.

Единственный источник для selftest.py, regimen-doctor.py и new-project.py — чтобы логика
«какие .md обходим», «какие [text](path)-ссылки считаем локальными», «ссылка резолвится»,
«незаполненный плейсхолдер» и «валидный sandbox_mode» не расходилась копиями
(аудит 2026-06-29 находка #4: SKIP_DIRS; аудит 2026-07-03 C1: предикат резолва в 3 копиях,
fence-трекинг в 2, определение плейсхолдера в 2, sandbox-regex в 2).

Копируется в сгенерированный проект вместе с regimen-doctor.py (см. new-project.py copy-set):
doctor импортирует этот модуль и запускается в корне проекта.
"""
from __future__ import annotations
import os
import re

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Каталоги вендоренных зависимостей, артефактов сборки и рабочих черновиков: их .md — не
# часть регламента (Jinja-шаблоны с легитимными {{...}}; scratchpad — временные артефакты
# панели/сессий, core/adversarial-panel.md §Процесс прогона, — с черновыми ссылками-заглушками).
SKIP_DIRS = (".git", "node_modules", ".venv", "venv", "site-packages",
             "__pycache__", ".tox", "dist", "build", ".mypy_cache", "scratchpad")

# Маркер генераторного фрагмента (overlays/codex/_agents-header.md): ссылки в нём
# написаны относительно КОРНЯ проекта, куда фрагмент материализуется (AGENTS.md),
# а не относительно каталога файла — линк-чек от каталога файла даёт ложный красный.
GENERATOR_FRAGMENT_MARKER = "CODEX-DELTA-HEADER"

# Валидные sandbox_mode агент-профилей Codex (.codex/agents/*.toml).
VALID_SANDBOX_MODES = ("read-only", "workspace-write")
SANDBOX_MODE_RE = re.compile(r'sandbox_mode\s*=\s*"(%s)"' % "|".join(VALID_SANDBOX_MODES))


def read(p: str) -> str:
    """Единое чтение текста. errors="replace": линтеры/генератор read-only по смыслу и не
    должны падать трейсбеком на одном не-UTF-8 файле (напр. бинарь с расширением .md,
    попавший в дерево); подсчёт {{ и ссылок от замены байтов не страдает."""
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def md_files(root: str):
    """Все .md под root, минуя вендор/сборку/черновики (SKIP_DIRS)."""
    for dp, _, fns in os.walk(root):
        if any(os.sep + d in dp + os.sep for d in SKIP_DIRS):
            continue
        for fn in fns:
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)


def local_target(raw: str):
    """Очищенная цель ссылки [..](raw), которую СТОИТ резолвить как локальный путь, либо
    None для пропуска: http/anchor/mailto/{{...}}/путь-с-пробелом (последнее — код-сниппет
    вида [this](auto messages), не ссылка)."""
    t = raw.split("#")[0].strip()
    if not t or t.startswith(("http", "#", "mailto")) or "{{" in t or " " in t:
        return None
    return t


def target_exists(filedir: str, target: str) -> bool:
    """Локальная цель ссылки резолвится от каталога файла."""
    return os.path.exists(os.path.normpath(os.path.join(filedir, target)))


def iter_lines(text: str, keepends: bool = False):
    """(lineno, line, in_fence) по строкам; строка-переключатель фенса (``` и ~~~)
    сама помечается in_fence=True. lineno — 1-based."""
    in_fence = False
    for ln, line in enumerate(text.splitlines(keepends), 1):
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            yield ln, line, True
            continue
        yield ln, line, in_fence


def iter_links(text: str):
    """Перебор [text](path)-ссылок ВНЕ код-фенсов (``` и ~~~).

    Yield (lineno, match, target), где target — очищенный локальный путь (local_target),
    либо None у пропускаемых ссылок. lineno — 1-based.
    """
    for ln, line, in_fence in iter_lines(text):
        if in_fence:
            continue
        for m in LINK.finditer(line):
            yield ln, m, local_target(m.group(2))


def dangling(root: str):
    """Висячие локальные ссылки по всем .md под root.

    Yield (relpath, lineno, link_text, target). Файлы-генераторные-фрагменты
    (GENERATOR_FRAGMENT_MARKER в первой строке) пропускаются: их ссылки резолвятся
    в точке материализации (корень проекта), не в точке хранения."""
    for p in md_files(root):
        body = read(p)
        if GENERATOR_FRAGMENT_MARKER in body.split("\n", 1)[0]:
            continue
        d = os.path.dirname(p)
        for ln, m, t in iter_links(body):
            if t is None or target_exists(d, t):
                continue
            yield os.path.relpath(p, root), ln, m.group(1), t


def count_placeholders(text: str) -> int:
    """Незаполненные {{...}} в тексте. Fenced-блоки считаются тоже — реальные слоты живут
    именно там ({{build-command}} и т.п.). Игнорируются `{{...}}` внутри inline-бэктиков:
    это документация О синтаксисе плейсхолдера, а не слот для заполнения — иначе регламент
    вечно красен о собственную прозу."""
    return re.sub(r"`[^`\n]*`", "", text).count("{{")
