#!/usr/bin/env python3
"""regimen-doctor — the regimen readiness gate for YOUR project (read-only).

Run at the root of a generated project any time after edits: checks what the generator
couldn't have known at generation time (because it depends on your subsequent edits) —
unfilled {{...}}, dangling links, role drift, settings.json validity, executable hooks,
whether build/test commands are filled in.

  python3 regimen-doctor.py            # check the current directory
  python3 regimen-doctor.py --dir ../proj

Exit 0 = regimen is green; exit 1 = there's a 🔴 (fix before the first real task).
This is NOT the package's selftest.py (that checks the package itself) — this checks your project.
Changes nothing: only reads and reports.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Shared primitives (finding #4 of the 2026-06-29 audit; consolidation C1 of the 2026-07-03 audit):
# .md traversal, reading, dangling links, placeholders, sandbox modes.
from _pack_lib import md_files, dangling, count_placeholders, read, SANDBOX_MODE_RE, SKIP_DIRS


def check_placeholders(root):
    """Unfilled {{...}} in the remaining .md files (semantics — _pack_lib's count_placeholders,
    the same as in new-project.py's report: the generator and the doctor must not diverge on lists)."""
    hits = []
    for p in md_files(root):
        n = count_placeholders(read(p))
        if n:
            hits.append((os.path.relpath(p, root), n))
    return sorted(hits, key=lambda x: -x[1])


def check_dead_links(root):
    """Dangling local links [text](path). Traversal, filtering and the resolution predicate — the
    shared _pack_lib.dangling primitive (same as in selftest.py); it skips generator fragments
    (CODEX-DELTA-HEADER — links from the root of the materialization point) on its own."""
    return [f"{rel}:{ln}  [{txt}]({t})" for rel, ln, txt, t in dangling(root)]


CANON_DIRS = {"core", "roles", "architecture", "stack", "domain"}


def check_harness_canon_refs(root):
    """Canon paths in the runtime wiring resolve (empirically found during the 2026-06 live
    upgrade: subagents copied with package paths `core/*.md` under a docs-nested layout =
    13 broken canons, silently). check_dead_links does NOT catch this: pointers in the wiring are
    prose in backticks, not markdown links. We scan .claude/**/*.md and .codex/**/*.toml:
    a lowercase token like `dir/…/file.md` with a canon segment (CANON_DIRS) must
    exist from the project root or from the file. Two deliberate narrowings: (1) lowercase
    only — templates `docs/day-D-guide.md`/`<N>`/`{{...}}` are cut off by case/character
    class; (2) canon namespaces only — artifact paths that the agent WILL CREATE
    (day-guides, scratchpad/panel/*) legitimately don't exist before runtime."""
    files = []
    for base, ext in ((".claude", ".md"), (".codex", ".toml")):
        d = os.path.join(root, base)
        if os.path.isdir(d):
            for dp, _, fns in os.walk(d):
                files += [os.path.join(dp, fn) for fn in fns if fn.endswith(ext)]
    tok = re.compile(r"(?<![\w/.<{])((?:[a-z0-9_-]+/)+[a-z0-9_.-]+\.md)(?![\w/])")
    bad = []
    for p in files:
        d = os.path.dirname(p)
        for t in set(tok.findall(read(p))):
            if not CANON_DIRS & set(t.split("/")[:-1]):
                continue
            if not (os.path.exists(os.path.join(root, t))
                    or os.path.exists(os.path.normpath(os.path.join(d, t)))):
                bad.append(f"{os.path.relpath(p, root)}: `{t}`")
    return sorted(set(bad))


def check_roles_sync(root):
    """sync-roles.py --check, if roles.json + sync-roles.py are present in the project."""
    sr = os.path.join(root, "sync-roles.py")
    if not (os.path.exists(sr) and os.path.exists(os.path.join(root, "roles.json"))):
        return None  # not applicable
    r = subprocess.run([sys.executable, sr, "--check"], cwd=root,
                       capture_output=True, text=True)
    return (r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1:] or [""])


def check_settings_json(root):
    """settings.json — must be strictly valid JSON (Claude Code will otherwise reject it)."""
    p = os.path.join(root, ".claude", "settings.json")
    if not os.path.exists(p):
        return None
    try:
        json.loads(read(p))
        return (True, "valid")
    except json.JSONDecodeError as e:
        return (False, f"invalid JSON: {e}")


def check_hooks_executable(root):
    """Hooks referenced by settings.json must be +x."""
    hd = os.path.join(root, ".claude", "hooks")
    if not os.path.isdir(hd):
        return None
    bad = [fn for fn in sorted(os.listdir(hd))
           if fn.endswith(".sh") and not os.access(os.path.join(hd, fn), os.X_OK)]
    return (not bad, bad)


def check_build_test_cmds(root):
    """build/test commands in the regimen entry file must not remain
    placeholders — without them the quality gates aren't runnable. Entry is per-harness
    (ADR-012): CLAUDE.md on Claude Code, AGENTS.md on Codex."""
    p = next((os.path.join(root, n) for n in ("CLAUDE.md", "AGENTS.md")
              if os.path.exists(os.path.join(root, n))), None)
    if p is None:
        return None
    body = read(p)
    left = [ph for ph in ("{{build-command}}", "{{check-command}}", "{{test-command}}", "{{fast-test-command}}")
            if ph in body]
    return (not left, left)


def detect_harness(root):
    """Which runtime overlays are present in the project (claude-code / codex)."""
    h = []
    if os.path.isdir(os.path.join(root, ".claude")):
        h.append("claude-code")
    if os.path.exists(os.path.join(root, "AGENTS.md")) or os.path.isdir(os.path.join(root, ".codex")):
        h.append("codex")
    return h


def check_claude_hooks_state(root):
    """The STATE of Claude Code hooks, not their presence (P5, ADR-010/011): active (settings.json
    with a hooks section) vs. dormant (.example only) → in the latter case mechanical gates
    degrade to accountability. Returns (level, msg) or None."""
    cl = os.path.join(root, ".claude")
    if not os.path.isdir(cl):
        return None
    sj = os.path.join(cl, "settings.json")
    ex = os.path.join(cl, "settings.json.example")
    if os.path.exists(sj):
        try:
            data = json.loads(read(sj))
        except json.JSONDecodeError:
            return ("red", "Claude Code: settings.json is invalid JSON — the harness will reject the file")
        if data.get("hooks"):
            return ("green", "Claude Code: hook gates are ACTIVE (settings.json → hooks section)")
        return ("warn", "Claude Code: settings.json has no hooks section → mechanical gates degrade to accountability")
    if os.path.exists(ex):
        return ("warn", "Claude Code: hooks are NOT enabled (settings.json.example wasn't renamed) → "
                        "mechanical gates degrade to accountability. Enable: "
                        "mv .claude/settings.json.example .claude/settings.json")
    return None


def check_codex_overlay_state(root):
    """The STATE of the codex overlay, not its presence (P5): entry, agent profiles with sandbox_mode,
    and the HONEST enforcement class (KL-7/G2 — hooks and docs-only tiers = accountability, not
    hardware-enforced). Returns list[(level, msg)] or None."""
    has_codex = os.path.exists(os.path.join(root, "AGENTS.md")) or os.path.isdir(os.path.join(root, ".codex"))
    if not has_codex:
        return None
    out = []
    if os.path.exists(os.path.join(root, "AGENTS.md")):
        out.append(("green", "Codex: entry AGENTS.md is in place (Codex auto-reads it)"))
    else:
        out.append(("red", "Codex: .codex/ is present, but AGENTS.md is missing — Codex won't get auto-context"))
    adir = os.path.join(root, ".codex", "agents")
    rj = os.path.join(root, "roles.json")
    if os.path.isdir(adir) and os.path.exists(rj):
        try:
            roles = json.loads(read(rj)).get("roles", [])
        except (json.JSONDecodeError, KeyError):
            roles = []
        miss, badmode = [], []
        for r in roles:  # mapping completeness: every role in roles.json has a .toml
            if not os.path.exists(os.path.join(adir, f"{r.get('agent','')}.toml")):
                miss.append(r.get("agent", "?"))
        # validate sandbox_mode on ALL .toml files in the directory (incl. dispatch agents outside
        # roles.json: architect/auditor/red-team/blue-team/arbiter) — parity with the claude side
        tomls = sorted(fn for fn in os.listdir(adir) if fn.endswith(".toml"))
        for fn in tomls:
            if not SANDBOX_MODE_RE.search(read(os.path.join(adir, fn))):
                badmode.append(fn[:-5])
        if miss:
            out.append(("red", f"Codex: agent profiles are missing for roles: {miss}"))
        elif badmode:
            out.append(("red", f"Codex: agent profiles without a valid sandbox_mode: {badmode}"))
        else:
            out.append(("green", f"Codex: agent profiles .codex/agents/*.toml are in place, sandbox_mode is set "
                                 f"({len(tomls)} profiles: read-only/workspace-write — hardware-enforced)"))
    elif os.path.isdir(adir):
        out.append(("green", "Codex: agent profiles .codex/agents/ are present"))
    # Honest enforcement class (not "the file exists", but "what it actually provides"):
    out.append(("warn", "Codex: hook gates = accountability (KL-7 — don't fire in headless "
                        "`codex exec`; a hard gate → CI/pre-commit). The docs-only/scratchpad-only "
                        "tiers are also prose (G2 — cwd is always writable). Only read-only/full-write "
                        "are hardware-enforced. Full matrix — core/portability.md."))
    return out


def check_stack_file(root):
    """The stack file: it carries the QG-NN-02 "Clean build" slots, the coverage command (§Tests) and
    the QG-NN-05 static adjunct. Event-driven rule (roles/architect.md §Kickoff): the file appears
    the moment the stack is chosen — at kickoff or after arch analysis; a deliberately deferred stack
    is legitimate (the generator with backend=none doesn't create it either). We distinguish two
    states by the entry file's build/test commands: placeholder commands = the stack isn't chosen yet
    (a soft reminder of the event rule); commands filled in = the stack is de facto chosen, no file =
    an "orphan file" hole. warn, not red: a project may deliberately keep the stack in the entry file,
    but then the slots are closed out there too. We look for stack/ and docs/stack/ (docs-nested layout)."""
    d = next((p for p in (os.path.join(root, "stack"), os.path.join(root, "docs", "stack"))
              if os.path.isdir(p)), None)
    files = [] if d is None else sorted(
        fn for fn in os.listdir(d) if fn.endswith(".md") and fn != "_TEMPLATE.md")
    if not files:
        cmds = check_build_test_cmds(root)
        undecided = cmds is not None and not cmds[0]  # entry commands are still placeholders
        if undecided:
            return ("warn", "the stack isn't chosen yet (entry build/test commands are placeholders) — "
                            "legitimate during the arch-analysis phase; the moment the stack is chosen, "
                            "the task that fixes the choice must create stack/<stack>.md "
                            "(event rule, roles/architect.md §Kickoff)")
        return ("warn", "the stack is de facto chosen (entry commands are filled in), but stack/<stack>.md "
                        "hasn't been created — the \"Clean build\" (QG-NN-02), coverage (§Tests) and "
                        "static-adjunct (QG-NN-05) slots have no canon. Owner is the architect "
                        "(event rule, kickoff/day-0), not the user")
    todo = [fn for fn in files if "TODO:" in read(os.path.join(d, fn))]
    if todo:
        return ("warn", f"stack file(s) with skeleton TODOs: {', '.join(todo)} — finish filling in "
                        f"(owner is the architect/day-0, from project facts)")
    return ("green", f"stack file is filled in ({', '.join(files)})")


QG_SCOPE_HEAD = re.compile(r"^##\s+Frozen scope\b", re.M)
QG_ID_ITEM = re.compile(r"^\s*[-*]\s+`([A-Za-z0-9][A-Za-z0-9_.-]*)`")
QG_ANNOT = re.compile(r"@qg:([A-Za-z0-9][A-Za-z0-9_.-]*)")


def check_qg_evidence(root):
    """QG-NN-05 durable evidence (core/quality-gates.md §Reachability, ADR-015): every
    scope-id from PROJECT-STATE's "## Frozen scope" section must have a checked-in annotation
    `@qg:<scope-id>` somewhere in the project (an assembled test or a generated manifest).
    An item marked "waiver" in the line is outside the check (waiver on record).
    Checks for the PRESENCE of evidence (the gate's machine backing); quality is reviewer/spot-check.
    Returns (ok, missing, total) | ("format", None, None) — the section exists but not a single
    item parses (format drift) | None — no section / still placeholders."""
    p = os.path.join(root, "docs", "PROJECT-STATE.md")
    if not os.path.exists(p):
        return None
    body = read(p)
    m = QG_SCOPE_HEAD.search(body)
    if not m:
        return None
    sect = body[m.end():]
    nxt = re.search(r"^##\s", sect, re.M)
    if nxt:
        sect = sect[:nxt.start()]
    if "{{" in sect:
        return None  # the section is still a stub — the slice isn't frozen
    want, items = [], 0
    for line in sect.splitlines():
        if re.match(r"^\s*[-*]\s", line):
            items += 1
        im = QG_ID_ITEM.match(line)
        if im and "waiver" not in line.lower():
            want.append(im.group(1))
    if not want:
        return ("format", None, None) if items > 1 else None  # 1 item = the shipping-root line
    found = set()
    for dp, _, fns in os.walk(root):
        if any(os.sep + d in dp + os.sep for d in SKIP_DIRS):
            continue
        for fn in fns:
            fp = os.path.join(dp, fn)
            if os.path.abspath(fp) == os.path.abspath(p):
                continue  # PROJECT-STATE holds a reference, not evidence
            try:
                if os.path.getsize(fp) > 2_000_000:
                    continue
                t = read(fp)
            except OSError:
                continue
            if "@qg:" in t:
                found |= set(QG_ANNOT.findall(t))
    missing = [w for w in want if w not in found]
    return (not missing, missing, len(want))


def check_state_size(root, limit=200):
    """PROJECT-STATE is a live snapshot, not a journal. We warn softly (🟡, not 🔴)
    if it's grown past limit lines: usually means it got appended to instead of pruned."""
    p = os.path.join(root, "docs", "PROJECT-STATE.md")
    if not os.path.exists(p):
        return None
    return (len(read(p).splitlines()), limit)


def main():
    ap = argparse.ArgumentParser(description="Regimen readiness gate (read-only).")
    ap.add_argument("--dir", default=".", help="project root (default: current)")
    ap.add_argument("--qg", action="store_true",
                    help="strict QG-NN-05: missing @qg-evidence for the frozen scope = 🔴 "
                         "(a slice's done-gate; for CI/pre-commit/exit)")
    args = ap.parse_args()
    root = os.path.abspath(args.dir)

    red, green, warn = [], [], []

    ph = check_placeholders(root)
    if ph:
        red.append("Unfilled {{...}} placeholders:\n" +
                   "\n".join(f"       {n:3}  {rel}" for rel, n in ph) +
                   "\n       (list them: grep -rn '{{' . --include='*.md')")
    else:
        green.append("{{...}} placeholders are filled in")

    dead = check_dead_links(root)
    if dead:
        red.append("Dangling local links:\n" + "\n".join(f"       {d}" for d in dead))
    else:
        green.append("no dangling links")

    refs = check_harness_canon_refs(root)
    if refs:
        red.append("Canon paths in the wiring do NOT resolve (project layout ≠ the package's? "
                   "rewrite the paths in the wiring — roles/upgrader.md step 4):\n" +
                   "\n".join(f"       {r}" for r in refs))
    else:
        green.append("wiring canon paths resolve")

    for label, res, ok_msg in [
        ("Role map (sync-roles --check)", check_roles_sync(root), "roles in sync"),
        (".claude/settings.json", check_settings_json(root), "settings.json valid"),
        (".claude/hooks executable", check_hooks_executable(root), "hooks executable"),
        ("build/test commands in the entry file", check_build_test_cmds(root), "build/test commands set"),
    ]:
        if res is None:
            continue  # not applicable to this project
        ok, detail = res
        if ok:
            green.append(ok_msg)
        else:
            if isinstance(detail, list):
                detail = ", ".join(detail) if detail else "—"
            elif isinstance(detail, str) is False:
                detail = str(detail)
            if label.startswith(".claude/hooks"):
                detail = f"not executable: {detail} (chmod +x .claude/hooks/*.sh)"
            red.append(f"{label}: {detail}")

    # --- P5: STATE of the runtime wiring (not presence) ---
    bucket = {"green": green, "warn": warn, "red": red}
    cs = check_claude_hooks_state(root)
    if cs is not None:
        bucket[cs[0]].append(cs[1])
    cx = check_codex_overlay_state(root)
    if cx is not None:
        for level, msg in cx:
            bucket[level].append(msg)

    sf = check_stack_file(root)
    bucket[sf[0]].append(sf[1])

    qg = check_qg_evidence(root)
    if qg is not None:
        ok, missing, total = qg
        if ok == "format":
            warn.append("QG-NN-05: PROJECT-STATE's \"Frozen scope\" section exists, but not a "
                        "single item parses — format: \"- `SCOPE-ID` — criterion\" "
                        "(core/quality-gates.md §Reachability)")
        elif ok:
            green.append(f"QG-NN-05: @qg-evidence is in place ({total} scope-id ↔ annotations)")
        else:
            msg = (f"QG-NN-05: frozen-scope criteria WITHOUT @qg-evidence: {', '.join(missing)} "
                   f"({len(missing)}/{total}) — the slice isn't done until evidence is checked in "
                   f"(core/quality-gates.md §Reachability, ADR-015)")
            (red if args.qg else warn).append(msg)

    ss = check_state_size(root)
    if ss is not None:
        n, limit = ss
        if n <= limit:
            green.append(f"PROJECT-STATE is compact ({n} lines)")
        else:
            warn.append(f"PROJECT-STATE.md has grown ({n} lines > {limit}) — this is a snapshot, not a "
                        f"journal: prune what's resolved/stale (history is in git, pruning is reversible). "
                        f"See roles/architect.md → \"Updating PROJECT-STATE\".")

    harnesses = detect_harness(root)
    hlabel = ", ".join(harnesses) if harnesses else "prose mode (no wiring)"
    print(f"\nregimen-doctor — {root}")
    print(f"  runtime wiring: {hlabel}\n")
    for g in green:
        print(f"  🟢 {g}")
    for w in warn:
        print(f"  🟡 {w}")
    for r in red:
        print(f"  🔴 {r}")

    if red:
        print(f"\n  {len(red)} 🔴 — fix before the first real task.\n")
        return 1
    if warn:
        print(f"\n  Regimen is green ({len(warn)} 🟡 — soft, non-blocking). You can take the first task.\n")
        return 0
    print("\n  Regimen is green. You can take the first task.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
