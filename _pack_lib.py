"""_pack_lib.py — shared tooling primitives of the package: .md traversal, reading,
local-link parsing, placeholders, sandbox modes.

The single source for selftest.py, regimen-doctor.py and new-project.py — so that the logic
of "which .md files we traverse", "which [text](path) links count as local", "the link
resolves", "an unfilled placeholder" and "a valid sandbox_mode" doesn't drift apart in copies
(audit 2026-06-29 finding #4: SKIP_DIRS; audit 2026-07-03 C1: the resolve predicate in 3
copies, fence tracking in 2, the placeholder definition in 2, the sandbox regex in 2).

Copied into the generated project together with regimen-doctor.py (see the new-project.py
copy-set): the doctor imports this module and runs in the project root.
"""
from __future__ import annotations
import os
import re

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Directories of vendored dependencies, build artifacts and working drafts: their .md files
# are not part of the regimen (Jinja templates with legitimate {{...}}; scratchpad — temporary
# panel/session artifacts, core/adversarial-panel.md §Run process — with draft stub links).
SKIP_DIRS = (".git", "node_modules", ".venv", "venv", "site-packages",
             "__pycache__", ".tox", "dist", "build", ".mypy_cache", "scratchpad")

# Generator-fragment marker (overlays/codex/_agents-header.md): its links are written
# relative to the PROJECT ROOT where the fragment materializes (AGENTS.md), not relative
# to the file's own directory — a link check from the file's directory gives a false red.
GENERATOR_FRAGMENT_MARKER = "CODEX-DELTA-HEADER"

# Valid sandbox_mode values of Codex agent profiles (.codex/agents/*.toml).
VALID_SANDBOX_MODES = ("read-only", "workspace-write")
SANDBOX_MODE_RE = re.compile(r'sandbox_mode\s*=\s*"(%s)"' % "|".join(VALID_SANDBOX_MODES))


def read(p: str) -> str:
    """Unified text reading. errors="replace": the linters/generator are read-only in spirit
    and must not die with a traceback on a single non-UTF-8 file (e.g. a binary with an .md
    extension that got into the tree); counting {{ and links is unaffected by byte replacement."""
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def md_files(root: str):
    """All .md under root, skipping vendor/build/drafts (SKIP_DIRS).

    SKIP_DIRS are matched as exact path segments BELOW root (walk pruning), not as
    substrings of the absolute path: `build-qa/` (the canonical QA circuit) is not `build/`,
    and a project that happens to live under a parent directory named `build/`/`dist/` must
    not silently drop out of every scan (both were real bugs — ADR-017 phase 1)."""
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)


def local_target(raw: str):
    """The cleaned target of a [..](raw) link that is WORTH resolving as a local path, or
    None to skip it: http/anchor/mailto/{{...}}/path-with-a-space (the latter is a code
    snippet like [this](auto messages), not a link)."""
    t = raw.split("#")[0].strip()
    if not t or t.startswith(("http", "#", "mailto")) or "{{" in t or " " in t:
        return None
    return t


def target_exists(filedir: str, target: str) -> bool:
    """A local link target resolves from the file's directory."""
    return os.path.exists(os.path.normpath(os.path.join(filedir, target)))


def iter_lines(text: str, keepends: bool = False):
    """(lineno, line, in_fence) per line; the fence-toggling line itself (``` and ~~~)
    is marked in_fence=True. lineno is 1-based."""
    in_fence = False
    for ln, line in enumerate(text.splitlines(keepends), 1):
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            yield ln, line, True
            continue
        yield ln, line, in_fence


def iter_links(text: str):
    """Iterate [text](path) links OUTSIDE code fences (``` and ~~~).

    Yield (lineno, match, target), where target is the cleaned local path (local_target),
    or None for skipped links. lineno is 1-based.
    """
    for ln, line, in_fence in iter_lines(text):
        if in_fence:
            continue
        for m in LINK.finditer(line):
            yield ln, m, local_target(m.group(2))


def dangling(root: str):
    """Dangling local links across all .md under root.

    Yield (relpath, lineno, link_text, target). Generator-fragment files
    (GENERATOR_FRAGMENT_MARKER in the first line) are skipped: their links resolve
    at the materialization point (project root), not at the storage point."""
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
    """Unfilled {{...}} in the text. Fenced blocks are counted too — the real slots live
    exactly there ({{build-command}} and the like). `{{...}}` inside inline backticks is
    ignored: that's documentation ABOUT the placeholder syntax, not a slot to fill — otherwise
    the regimen stays forever red against its own prose."""
    return re.sub(r"`[^`\n]*`", "", text).count("{{")
