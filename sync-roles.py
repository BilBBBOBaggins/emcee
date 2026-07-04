#!/usr/bin/env python3
"""
sync-roles.py — single source of truth for the role map.

roles.json (digit -> role) is the canon. This script regenerates the role tables between the
ROLES-TABLE markers in ALL runtime targets, so they do NOT drift:
  - CLAUDE.md and .claude/commands/role.md          (Claude Code runtime)
  - AGENTS.md at the root of a codex project          (Codex runtime; the same neutral table — the
                                                       entry is rendered from the shared body, ADR-012)
Missing targets are skipped (apply() returns None) — one script serves any generated
project (claude / codex) and the package itself.

  python3 sync-roles.py           # regenerate the tables from roles.json
  python3 sync-roles.py --check   # rc=1 if the tables have drifted out of sync, links are broken,
                                  # or the "N D T" digits in role prose ≠ roles.json (for CI/selftest)

Renumbering/removing roles: edit roles.json, then run sync. The tables regenerate
themselves; sync can't fix the "N D T" digits in the PROSE of role surfaces — it checks them
(--check = rc 1) and names the files for a manual fix. Table markers:
  <!-- ROLES-TABLE:START ... -->  ...table...  <!-- ROLES-TABLE:END -->
"""
from __future__ import annotations
import json, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r"(<!-- ROLES-TABLE:START.*?-->)(.*?)(<!-- ROLES-TABLE:END -->)", re.S)
DTT = re.compile(r"(?:`|Numeric command:\s*`?)(\d)\s+D\s+T")


def load_roles() -> list[dict]:
    data = json.load(open(os.path.join(BASE, "roles.json"), encoding="utf-8"))
    return data["roles"]


def claude_table(roles: list[dict]) -> str:
    out = ["| R | Role | Role file |", "|---|------|-----------|"]
    out += [f"| {r['num']} | {r['name']} | [{r['file']}]({r['file']}) |" for r in roles]
    return "\n".join(out)


def role_cmd_table(roles: list[dict]) -> str:
    out = ["| R | Role | Subagent |", "|---|------|----------|"]
    out += [f"| {r['num']} | {r['name']} | {r['agent']} |" for r in roles]
    return "\n".join(out)


def apply(path: str, table: str, check: bool):
    """Returns: None (no file/markers — skip), True (in sync/written), False (drift under --check)."""
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
        errs.append("duplicate digits in roles.json")
    for r in roles:
        if not all(k in r for k in ("num", "name", "agent", "file")):
            errs.append(f"role {r} missing required fields (num/name/agent/file)")
            continue
        if not os.path.exists(os.path.join(BASE, r["file"])):
            errs.append(f"roles.json: role file not found — {r['file']}")
        adir = os.path.join(BASE, ".claude", "agents")
        if os.path.isdir(adir) and not os.path.exists(os.path.join(adir, f"{r['agent']}.md")):
            errs.append(f"roles.json: subagent not found — .claude/agents/{r['agent']}.md")
        # codex overlay: in the package — overlays/codex/.codex/agents/, in a codex project — .codex/agents/.
        # Checked only if the directory exists (a claude project doesn't have it — skip).
        cdir = next((d for d in (os.path.join(BASE, "overlays", "codex", ".codex", "agents"),
                                 os.path.join(BASE, ".codex", "agents")) if os.path.isdir(d)), None)
        if cdir and not os.path.exists(os.path.join(cdir, f"{r['agent']}.toml")):
            errs.append(f"roles.json: codex agent not found — {os.path.relpath(cdir, BASE)}/{r['agent']}.toml")
    return errs


def check_digit_refs(roles: list[dict]) -> list[str]:
    """Hardcoded digits like "N D T" in the prose of role surfaces (roles/*.md,
    .claude/agents/*.md, codex .toml) are checked against roles.json: a renumber that didn't
    fix the prose leaves a stale dispatch behind green tables (2026-07-03 audit S3/D2)."""
    errs = []
    cdir = next((d for d in (os.path.join(BASE, "overlays", "codex", ".codex", "agents"),
                             os.path.join(BASE, ".codex", "agents")) if os.path.isdir(d)), None)
    for r in roles:
        paths = [os.path.join(BASE, r["file"]),
                 os.path.join(BASE, ".claude", "agents", f"{r['agent']}.md")]
        if cdir:
            paths.append(os.path.join(cdir, f"{r['agent']}.toml"))
        for p in paths:
            if not os.path.exists(p):
                continue
            for d in set(DTT.findall(open(p, encoding="utf-8").read())):
                if int(d) != r["num"]:
                    errs.append(f"digit \"{d} D T\" in {os.path.relpath(p, BASE)} ≠ roles.json "
                                f"({r['name']} = {r['num']}) — fix the prose by hand")
    return errs


def main() -> int:
    check = "--check" in sys.argv
    roles = load_roles()
    errs = validate(roles) + check_digit_refs(roles)
    # The entry (CLAUDE.md / AGENTS.md) carries ONE neutral role table (claude_table: R → roles/*.md);
    # codex-AGENTS.md is rendered from the same body (ADR-012), so the table is identical. Codex
    # dispatch (.codex/agents/*.toml) is prose in the codex-delta header, not a separate sync table.
    targets = [(os.path.join(BASE, "CLAUDE.md"), claude_table(roles)),
               (os.path.join(BASE, ".claude", "commands", "role.md"), role_cmd_table(roles)),
               # codex project: AGENTS.md at the root (the package has no root-AGENTS.md → apply() returns None, skip).
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
                print(f"✗ role tables have drifted out of sync: {drift} → run: python3 sync-roles.py",
                      file=sys.stderr)
            return 1
        print("✓ roles.json is valid, role tables are in sync")
        return 0

    if errs:
        for e in errs:
            print("✗", e, file=sys.stderr)
        return 1
    print("✓ sync-roles: role tables regenerated from roles.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
