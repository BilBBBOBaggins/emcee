#!/usr/bin/env python3
"""regimen-doctor — гейт готовности регламента в ТВОЁМ проекте (read-only).

Запускается в корне сгенерированного проекта в любой момент после правок:
проверяет то, что генератор не мог знать в момент генерации (потому что зависит от
твоих последующих правок) — незаполненные {{...}}, висячие ссылки, рассинхрон ролей,
валидность settings.json, executable-хуки, заполненность build/test-команд.

  python3 regimen-doctor.py            # проверить текущий каталог
  python3 regimen-doctor.py --dir ../proj

Exit 0 = регламент зелёный; exit 1 = есть 🔴 (чинить до первой реальной задачи).
Это НЕ selftest.py пакета (тот проверяет сам пакет) — этот проверяет твой проект.
Ничего не меняет: только читает и сообщает.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pack_lib import md_files, iter_links  # общий обход .md + парсинг ссылок (находка #4)


def read(p):
    # errors="replace": доктор read-only и не должен падать на одном
    # не-UTF-8 файле (напр. бинарь с расширением .md, попавший в дерево
    # при запуске не из корня проекта). Подсчёт {{ и ссылок от этого не страдает.
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def check_placeholders(root):
    """Незаполненные {{...}} в оставленных .md (вне код-блоков считаем тоже —
    плейсхолдер в любом месте = недозаполнено)."""
    hits = []
    for p in md_files(root):
        n = read(p).count("{{")
        if n:
            hits.append((os.path.relpath(p, root), n))
    return sorted(hits, key=lambda x: -x[1])


def check_dead_links(root):
    """Висячие локальные ссылки [text](path). Обход и фильтрация ссылок — общий примитив
    _pack_lib (тот же, что в selftest.py/new-project.py)."""
    dead = []
    for p in md_files(root):
        d = os.path.dirname(p)
        for ln, m, t in iter_links(read(p)):
            if t is None:
                continue
            if not os.path.exists(os.path.normpath(os.path.join(d, t))):
                dead.append(f"{os.path.relpath(p, root)}:{ln}  [{m.group(1)}]({t})")
    return dead


def check_roles_sync(root):
    """sync-roles.py --check, если roles.json + sync-roles.py есть в проекте."""
    sr = os.path.join(root, "sync-roles.py")
    if not (os.path.exists(sr) and os.path.exists(os.path.join(root, "roles.json"))):
        return None  # не применимо
    r = subprocess.run([sys.executable, sr, "--check"], cwd=root,
                       capture_output=True, text=True)
    return (r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1:] or [""])


def check_settings_json(root):
    """settings.json — строгий валидный JSON (Claude Code отвергнет иначе)."""
    p = os.path.join(root, ".claude", "settings.json")
    if not os.path.exists(p):
        return None
    try:
        json.loads(read(p))
        return (True, "валиден")
    except json.JSONDecodeError as e:
        return (False, f"невалидный JSON: {e}")


def check_hooks_executable(root):
    """Хуки, на которые ссылается settings.json, должны быть +x."""
    hd = os.path.join(root, ".claude", "hooks")
    if not os.path.isdir(hd):
        return None
    bad = [fn for fn in sorted(os.listdir(hd))
           if fn.endswith(".sh") and not os.access(os.path.join(hd, fn), os.X_OK)]
    return (not bad, bad)


def check_build_test_cmds(root):
    """build/test-команды во входном файле регламента не должны остаться
    плейсхолдерами — без них quality-gates неисполнимы. Вход per-harness
    (ADR-012): на Claude Code — CLAUDE.md, на Codex — AGENTS.md."""
    p = next((os.path.join(root, n) for n in ("CLAUDE.md", "AGENTS.md")
              if os.path.exists(os.path.join(root, n))), None)
    if p is None:
        return None
    body = read(p)
    left = [ph for ph in ("{{build-command}}", "{{check-command}}", "{{test-command}}", "{{fast-test-command}}")
            if ph in body]
    return (not left, left)


def detect_harness(root):
    """Какие рантайм-оверлеи присутствуют в проекте (claude-code / codex)."""
    h = []
    if os.path.isdir(os.path.join(root, ".claude")):
        h.append("claude-code")
    if os.path.exists(os.path.join(root, "AGENTS.md")) or os.path.isdir(os.path.join(root, ".codex")):
        h.append("codex")
    return h


def check_claude_hooks_state(root):
    """СОСТОЯНИЕ хуков Claude Code, не наличие (P5, ADR-010/011): активны (settings.json
    с секцией hooks) vs дормантны (только .example) → во втором случае mechanical-гейты
    деградируют в accountability. Возвращает (level, msg) или None."""
    cl = os.path.join(root, ".claude")
    if not os.path.isdir(cl):
        return None
    sj = os.path.join(cl, "settings.json")
    ex = os.path.join(cl, "settings.json.example")
    if os.path.exists(sj):
        try:
            data = json.loads(read(sj))
        except json.JSONDecodeError:
            return ("red", "Claude Code: settings.json невалидный JSON — харнесс отвергнет файл")
        if data.get("hooks"):
            return ("green", "Claude Code: хуки-гейты АКТИВНЫ (settings.json → секция hooks)")
        return ("warn", "Claude Code: settings.json без секции hooks → mechanical-гейты в accountability")
    if os.path.exists(ex):
        return ("warn", "Claude Code: хуки НЕ включены (settings.json.example не переименован) → "
                        "mechanical-гейты деградируют в accountability. Включить: "
                        "mv .claude/settings.json.example .claude/settings.json")
    return None


def check_codex_overlay_state(root):
    """СОСТОЯНИЕ codex-оверлея, не наличие (P5): вход, агент-профили с sandbox_mode, и
    ЧЕСТНЫЙ класс энфорсмента (KL-7/G2 — хуки и docs-only тиры = accountability, не аппаратно).
    Возвращает list[(level, msg)] или None."""
    has_codex = os.path.exists(os.path.join(root, "AGENTS.md")) or os.path.isdir(os.path.join(root, ".codex"))
    if not has_codex:
        return None
    out = []
    if os.path.exists(os.path.join(root, "AGENTS.md")):
        out.append(("green", "Codex: вход AGENTS.md на месте (авточтение Codex)"))
    else:
        out.append(("red", "Codex: .codex/ есть, но AGENTS.md нет — Codex не получит авто-контекст"))
    adir = os.path.join(root, ".codex", "agents")
    rj = os.path.join(root, "roles.json")
    if os.path.isdir(adir) and os.path.exists(rj):
        try:
            roles = json.loads(read(rj)).get("roles", [])
        except (json.JSONDecodeError, KeyError):
            roles = []
        miss, badmode = [], []
        for r in roles:  # полнота маппинга: каждая роль roles.json имеет .toml
            if not os.path.exists(os.path.join(adir, f"{r.get('agent','')}.toml")):
                miss.append(r.get("agent", "?"))
        # sandbox_mode валидируем у ВСЕХ .toml в каталоге (вкл. dispatch-агентов вне roles.json:
        # architect/auditor/red-team/blue-team/arbiter) — паритет с claude-стороной
        tomls = sorted(fn for fn in os.listdir(adir) if fn.endswith(".toml"))
        for fn in tomls:
            if not re.search(r'sandbox_mode\s*=\s*"(read-only|workspace-write)"', read(os.path.join(adir, fn))):
                badmode.append(fn[:-5])
        if miss:
            out.append(("red", f"Codex: агент-профили отсутствуют для ролей: {miss}"))
        elif badmode:
            out.append(("red", f"Codex: агент-профили без валидного sandbox_mode: {badmode}"))
        else:
            out.append(("green", f"Codex: агент-профили .codex/agents/*.toml на месте, sandbox_mode задан "
                                 f"({len(tomls)} профилей: read-only/workspace-write — аппаратно)"))
    elif os.path.isdir(adir):
        out.append(("green", "Codex: агент-профили .codex/agents/ присутствуют"))
    # Честный класс энфорсмента (не «файл есть», а «что он реально даёт»):
    out.append(("warn", "Codex: хуки-гейты = accountability (KL-7 — в headless `codex exec` не "
                        "срабатывают; жёсткий гейт → CI/pre-commit). Тиры docs-only/scratchpad-only — "
                        "тоже проза (G2 — cwd всегда писибелен). Аппаратны только read-only/full-write. "
                        "Полная матрица — core/portability.md."))
    return out


def check_state_size(root, limit=200):
    """PROJECT-STATE — горячий снимок, не журнал. Мягко предупреждаем (🟡, не 🔴),
    если разросся > limit строк: обычно значит, что в него дописывали вместо прунинга."""
    p = os.path.join(root, "docs", "PROJECT-STATE.md")
    if not os.path.exists(p):
        return None
    return (len(read(p).splitlines()), limit)


def main():
    ap = argparse.ArgumentParser(description="Гейт готовности регламента (read-only).")
    ap.add_argument("--dir", default=".", help="корень проекта (по умолчанию текущий)")
    root = os.path.abspath(ap.parse_args().dir)

    red, green, warn = [], [], []

    ph = check_placeholders(root)
    if ph:
        red.append("Незаполненные {{...}} плейсхолдеры:\n" +
                   "\n".join(f"       {n:3}  {rel}" for rel, n in ph) +
                   "\n       (перечислить: grep -rn '{{' . --include='*.md')")
    else:
        green.append("плейсхолдеры {{...}} заполнены")

    dead = check_dead_links(root)
    if dead:
        red.append("Висячие локальные ссылки:\n" + "\n".join(f"       {d}" for d in dead))
    else:
        green.append("висячих ссылок нет")

    for label, res, ok_msg in [
        ("Карта ролей (sync-roles --check)", check_roles_sync(root), "роли в синхроне"),
        (".claude/settings.json", check_settings_json(root), "settings.json валиден"),
        (".claude/hooks executable", check_hooks_executable(root), "хуки executable"),
        ("build/test-команды во входном файле", check_build_test_cmds(root), "build/test-команды заданы"),
    ]:
        if res is None:
            continue  # не применимо к этому проекту
        ok, detail = res
        if ok:
            green.append(ok_msg)
        else:
            if isinstance(detail, list):
                detail = ", ".join(detail) if detail else "—"
            elif isinstance(detail, str) is False:
                detail = str(detail)
            if label.startswith(".claude/hooks"):
                detail = f"не executable: {detail} (chmod +x .claude/hooks/*.sh)"
            red.append(f"{label}: {detail}")

    # --- P5: состояние обвязки рантайма (не наличие) ---
    bucket = {"green": green, "warn": warn, "red": red}
    cs = check_claude_hooks_state(root)
    if cs is not None:
        bucket[cs[0]].append(cs[1])
    cx = check_codex_overlay_state(root)
    if cx is not None:
        for level, msg in cx:
            bucket[level].append(msg)

    ss = check_state_size(root)
    if ss is not None:
        n, limit = ss
        if n <= limit:
            green.append(f"PROJECT-STATE компактен ({n} строк)")
        else:
            warn.append(f"PROJECT-STATE.md разросся ({n} строк > {limit}) — это снимок, не журнал: "
                        f"прунь решённое/устаревшее (история в git, прунинг обратим). "
                        f"См. roles/architect.md → «Обновление PROJECT-STATE».")

    harnesses = detect_harness(root)
    hlabel = ", ".join(harnesses) if harnesses else "прозовый режим (обвязки нет)"
    print(f"\nregimen-doctor — {root}")
    print(f"  обвязка рантайма: {hlabel}\n")
    for g in green:
        print(f"  🟢 {g}")
    for w in warn:
        print(f"  🟡 {w}")
    for r in red:
        print(f"  🔴 {r}")

    if red:
        print(f"\n  {len(red)} 🔴 — почини до первой реальной задачи.\n")
        return 1
    if warn:
        print(f"\n  Регламент зелёный ({len(warn)} 🟡 — мягкое, не блокирует). Можно брать первую задачу.\n")
        return 0
    print("\n  Регламент зелёный. Можно брать первую задачу.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
