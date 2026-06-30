#!/usr/bin/env python3
"""
sync-roles.py — единый источник истины для карты ролей.

roles.json (цифра -> роль) — канон. Этот скрипт перегенерирует таблицы ролей между маркерами
ROLES-TABLE во ВСЕХ runtime-таргетах, чтобы они НЕ дрейфовали:
  - CLAUDE.md и .claude/commands/role.md          (рантайм Claude Code)
  - AGENTS.md в корне codex-проекта                 (рантайм Codex; та же нейтральная таблица — вход
                                                     рендерится из общего тела, ADR-012)
Отсутствующие таргеты пропускаются (apply() возвращает None) — один скрипт обслуживает любой
сгенерированный проект (claude / codex) и сам пакет.

  python3 sync-roles.py           # перегенерировать таблицы из roles.json
  python3 sync-roles.py --check   # rc=1, если таблицы рассинхронились или ссылки битые (для CI/selftest)

Renumber/удаление ролей: правишь roles.json, потом запускаешь sync. Маркеры:
  <!-- ROLES-TABLE:START ... -->  ...таблица...  <!-- ROLES-TABLE:END -->
"""
from __future__ import annotations
import json, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r"(<!-- ROLES-TABLE:START.*?-->)(.*?)(<!-- ROLES-TABLE:END -->)", re.S)


def load_roles() -> list[dict]:
    data = json.load(open(os.path.join(BASE, "roles.json"), encoding="utf-8"))
    return data["roles"]


def claude_table(roles: list[dict]) -> str:
    out = ["| R | Роль | Файл роли |", "|---|------|-----------|"]
    out += [f"| {r['num']} | {r['name']} | [{r['file']}]({r['file']}) |" for r in roles]
    return "\n".join(out)


def role_cmd_table(roles: list[dict]) -> str:
    out = ["| R | Роль | Субагент |", "|---|------|----------|"]
    out += [f"| {r['num']} | {r['name']} | {r['agent']} |" for r in roles]
    return "\n".join(out)


def apply(path: str, table: str, check: bool):
    """Возвращает: None (нет файла/маркеров — пропуск), True (в синхроне/записано), False (дрейф при --check)."""
    if not os.path.exists(path):
        return None
    txt = open(path, encoding="utf-8").read()
    if not PAT.search(txt):
        return None
    new = PAT.sub(lambda m: m.group(1) + "\n" + table + "\n" + m.group(3), txt)
    if check:
        return txt == new
    if new != txt:
        open(path, "w", encoding="utf-8").write(new)
    return True


def validate(roles: list[dict]) -> list[str]:
    errs = []
    nums = [r["num"] for r in roles]
    if len(nums) != len(set(nums)):
        errs.append("дубли цифр в roles.json")
    for r in roles:
        if not all(k in r for k in ("num", "name", "agent", "file")):
            errs.append(f"роль {r} без обязательных полей (num/name/agent/file)")
            continue
        if not os.path.exists(os.path.join(BASE, r["file"])):
            errs.append(f"roles.json: файл роли не найден — {r['file']}")
        adir = os.path.join(BASE, ".claude", "agents")
        if os.path.isdir(adir) and not os.path.exists(os.path.join(adir, f"{r['agent']}.md")):
            errs.append(f"roles.json: субагент не найден — .claude/agents/{r['agent']}.md")
        # codex-оверлей: в пакете — overlays/codex/.codex/agents/, в codex-проекте — .codex/agents/.
        # Проверяем только если каталог существует (claude-проект его не имеет — пропуск).
        cdir = next((d for d in (os.path.join(BASE, "overlays", "codex", ".codex", "agents"),
                                 os.path.join(BASE, ".codex", "agents")) if os.path.isdir(d)), None)
        if cdir and not os.path.exists(os.path.join(cdir, f"{r['agent']}.toml")):
            errs.append(f"roles.json: codex-агент не найден — {os.path.relpath(cdir, BASE)}/{r['agent']}.toml")
    return errs


def main() -> int:
    check = "--check" in sys.argv
    roles = load_roles()
    errs = validate(roles)
    # Вход (CLAUDE.md / AGENTS.md) несёт ОДНУ нейтральную таблицу ролей (claude_table: R → roles/*.md);
    # codex-AGENTS.md рендерится из того же тела (ADR-012), потому таблица идентична. Codex-диспатч
    # (.codex/agents/*.toml) — проза в codex-delta-хедере, не отдельная синк-таблица.
    targets = [(os.path.join(BASE, "CLAUDE.md"), claude_table(roles)),
               (os.path.join(BASE, ".claude", "commands", "role.md"), role_cmd_table(roles)),
               # codex-проект: AGENTS.md в корне (в пакете root-AGENTS.md нет → apply() вернёт None, пропуск).
               (os.path.join(BASE, "AGENTS.md"), claude_table(roles))]
    drift = []
    for path, table in targets:
        res = apply(path, table, check)
        if check and res is False:
            drift.append(os.path.relpath(path, BASE))

    if check:
        if errs or drift:
            for e in errs:
                print("✗", e, file=sys.stderr)
            if drift:
                print(f"✗ таблицы ролей рассинхронились: {drift} → запусти: python3 sync-roles.py",
                      file=sys.stderr)
            return 1
        print("✓ roles.json валиден, таблицы ролей в синхроне")
        return 0

    if errs:
        for e in errs:
            print("✗", e, file=sys.stderr)
        return 1
    print("✓ sync-roles: таблицы ролей перегенерированы из roles.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
