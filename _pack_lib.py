"""_pack_lib.py — общие примитивы тулинга пакета: обход .md и парсинг локальных ссылок.

Единственный источник для selftest.py, regimen-doctor.py и new-project.py — чтобы логика
«какие .md обходим» и «какие [text](path)-ссылки считаем локальными» не расходилась тремя
копиями (аудит 2026-06-29, находка #4: копии уже разъехались по списку SKIP_DIRS).

Копируется в сгенерированный проект вместе с regimen-doctor.py (см. new-project.py copy-set):
doctor импортирует этот модуль и запускается в корне проекта.
"""
from __future__ import annotations
import os
import re

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Каталоги вендоренных зависимостей и артефактов сборки: их .md — чужие
# (напр. Jinja-шаблоны с легитимными {{...}}), не часть регламента.
SKIP_DIRS = (".git", "node_modules", ".venv", "venv", "site-packages",
             "__pycache__", ".tox", "dist", "build", ".mypy_cache")


def md_files(root: str):
    """Все .md под root, минуя вендор/сборку (SKIP_DIRS)."""
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


def iter_links(text: str):
    """Перебор [text](path)-ссылок ВНЕ код-фенсов (``` и ~~~).

    Yield (lineno, match, target), где target — очищенный локальный путь (local_target),
    либо None у пропускаемых ссылок. lineno — 1-based.
    """
    in_fence = False
    for ln, line in enumerate(text.splitlines(), 1):
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in LINK.finditer(line):
            yield ln, m, local_target(m.group(2))
