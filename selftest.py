#!/usr/bin/env python3
"""
selftest.py — self-test for the emcee package.

Generates a matrix of projects via new-project.py into a temp directory and checks
the generated project's invariants + the package's own health. Catches regressions
that have already happened (dangling links after pruning; {{...}} -> {...} collapse).

Run:  ./selftest.py      (exit 0 = all green, otherwise 1)
"""
from __future__ import annotations
import glob, json, os, re, subprocess, sys, tempfile, shutil

PACK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PACK)
from _pack_lib import md_files, read, SANDBOX_MODE_RE  # shared primitives (finding #4; consolidation C1)
from _pack_lib import dangling as _dangling

GEN = os.path.join(PACK, "new-project.py")
results: list[tuple[bool, str]] = []


def check(cond: bool, msg: str):
    results.append((bool(cond), msg))


def dangling(root: str) -> list[str]:
    # resolution predicate + marker-skip for generator fragments — shared _pack_lib.dangling
    return [f"{rel} -> {t}" for rel, _ln, _txt, t in _dangling(root)]


def gen(target: str, **flags) -> subprocess.CompletedProcess:
    args = [sys.executable, GEN, "--dir", target]
    for k, v in flags.items():
        args += [f"--{k}", str(v)]
    return subprocess.run(args, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def qg_tree(base: str, name: str, scope_body: str | None, files=(), git=True,
            files_after_add=()):
    """Synthetic project for the hardened QG-NN-05 checker (ADR-017): docs/PROJECT-STATE.md
    with the given Frozen-scope section body (None = no section) + extra files.
    "Checked-in" = the git index, so trees are `git init` + `git add -A` by default;
    files_after_add land in the worktree only (the unstaged-evidence case)."""
    root = os.path.join(base, name)
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    state = "# PROJECT-STATE — t\n\n## Snapshot\n- x\n"
    if scope_body is not None:
        state += "\n## Frozen scope (QG-NN-05)\n" + scope_body + "\n## Next day\n- x\n"
    with open(os.path.join(root, "docs", "PROJECT-STATE.md"), "w", encoding="utf-8") as f:
        f.write(state)
    for rel, body in files:
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    if git:
        subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    for rel, body in files_after_add:
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    return root


def doctor(root: str, qg: bool = False) -> subprocess.CompletedProcess:
    args = [sys.executable, os.path.join(PACK, "regimen-doctor.py"), "--dir", root]
    if qg:
        args.append("--qg")
    return subprocess.run(args, capture_output=True, text=True)


def validate_project(tag: str, root: str, *, name: str, wiring: bool,
                     stacks: list[str], new_stacks: list[str], variants_expected: int):
    # basics
    claude = os.path.join(root, "CLAUDE.md")
    check(os.path.exists(claude), f"[{tag}] CLAUDE.md exists")
    txt = open(claude, encoding="utf-8").read() if os.path.exists(claude) else ""
    check(name in txt, f"[{tag}] project name substituted into CLAUDE.md")
    check("{{PROJECT_NAME}}" not in txt, f"[{tag}] {{{{PROJECT_NAME}}}} didn't remain")
    check(txt.count("### Option") == variants_expected,
          f"[{tag}] testing options in CLAUDE.md = {variants_expected} (actual {txt.count('### Option')})")

    # KEY invariant: zero dangling links
    dl = dangling(root)
    check(not dl, f"[{tag}] no dangling links" + (f" (found {len(dl)}: {dl[:3]})" if dl else ""))

    # docs/ + {{...}} -> {...} collapse regression
    for rel in ("docs/day-1-guide.md", "docs/PROJECT-STATE.md"):
        p = os.path.join(root, rel)
        check(os.path.exists(p), f"[{tag}] {rel} exists")
        if os.path.exists(p):
            b = read(p)
            check("{{" in b, f"[{tag}] {rel} kept {{{{...}}}} (no .format collapse)")
            check("<<NAME>>" not in b, f"[{tag}] {rel} has no leaked sentinels")

    # stacks
    for s in stacks:
        check(os.path.exists(os.path.join(root, "stack", f"{s}.md")), f"[{tag}] stack/{s}.md is present")
    for s in new_stacks:
        sp = os.path.join(root, "stack", f"{s}.md")
        check(os.path.exists(sp), f"[{tag}] skeleton stack/{s}.md created")
        if os.path.exists(sp):
            sk = open(sp, encoding="utf-8").read()
            check("Clean build" in sk, f"[{tag}] skeleton {s} contains the \"Clean build\" section")
            check("{{STACK_NAME}}" not in sk and "{{STACK_SLUG}}" not in sk,
                  f"[{tag}] skeleton {s}: stack placeholders substituted")

    # wiring
    adir = os.path.join(root, ".claude")
    if wiring:
        check(os.path.isdir(adir), f"[{tag}] .claude/ copied")
        for af in (os.listdir(os.path.join(adir, "agents")) if os.path.isdir(os.path.join(adir, "agents")) else []):
            fm = open(os.path.join(adir, "agents", af), encoding="utf-8").read()[:800]
            check(all(k in fm for k in ("name:", "description:", "tools:")),
                  f"[{tag}] agent {af}: frontmatter is complete")
        sj = os.path.join(adir, "settings.json.example")
        if os.path.exists(sj):
            data = None
            try:
                data = json.load(open(sj))
            except Exception:
                pass
            check(data is not None, f"[{tag}] settings.json.example — valid JSON")
            # Claude Code's strict schema rejects unknown/underscore keys -> guard
            if isinstance(data, dict):
                check(all(not k.startswith("_") for k in data),
                      f"[{tag}] settings.json has no nonstandard keys (a rename won't break it)")
                check(set(data).issubset({"hooks", "permissions", "env", "model", "includeCoAuthoredBy",
                                          "cleanupPeriodDays", "apiKeyHelper", "statusLine"}),
                      f"[{tag}] settings.json has only known top-level keys: {sorted(set(data))}")
        # auto-skills: universal cores + one per chosen stack, pointing at the canon
        sdir = os.path.join(adir, "skills")
        for nm in ("debugging", "code-quality", "memory", "spec-driven"):
            check(os.path.exists(os.path.join(sdir, nm, "SKILL.md")),
                  f"[{tag}] universal skill {nm}/SKILL.md is in place")
        for s in (stacks + new_stacks):
            sp = os.path.join(sdir, s, "SKILL.md")
            check(os.path.exists(sp), f"[{tag}] stack skill {s}/SKILL.md created")
            if os.path.exists(sp):
                b = open(sp, encoding="utf-8").read()
                check(b.startswith("---") and "\nname:" in b and "\ndescription:" in b,
                      f"[{tag}] skill {s}: valid frontmatter (name+description)")
                check(os.path.exists(os.path.join(root, "stack", f"{s}.md")),
                      f"[{tag}] skill {s} points at an existing stack/{s}.md")
                # known stacks carry a path-scoped glob (reliable activation) + a description fallback
                if s in ("go", "python", "react-nextjs"):
                    check("\npaths:" in b, f"[{tag}] skill {s} carries a paths: glob (path-scoped activation)")
    else:
        check(not os.path.isdir(adir), f"[{tag}] .claude/ is absent (wiring=no)")

    # single source of the role map: roles.json + sync-roles.py copied and tables in sync
    check(os.path.exists(os.path.join(root, "roles.json")), f"[{tag}] roles.json copied")
    syncp = os.path.join(root, "sync-roles.py")
    check(os.path.exists(syncp), f"[{tag}] sync-roles.py copied")
    if os.path.exists(syncp):
        cp = subprocess.run([sys.executable, syncp, "--check"], cwd=root,
                            capture_output=True, text=True)
        check(cp.returncode == 0, f"[{tag}] sync-roles --check is green (role tables in sync)")

    # readiness gate: regimen-doctor.py copied and runs (on a fresh project with
    # unfilled {{...}} we expect rc=1 = "there's a 🔴", not a crash)
    docp = os.path.join(root, "regimen-doctor.py")
    check(os.path.exists(docp), f"[{tag}] regimen-doctor.py copied")
    if os.path.exists(docp):
        dr = subprocess.run([sys.executable, docp, "--dir", root], cwd=root,
                            capture_output=True, text=True)
        check(dr.returncode in (0, 1) and "regimen-doctor" in dr.stdout,
              f"[{tag}] regimen-doctor runs and reports (rc={dr.returncode})")
        check("Traceback" not in dr.stderr, f"[{tag}] regimen-doctor has no traceback")
        # P5: harness-aware wiring banner + hook STATE (not presence) on a claude project
        check("runtime wiring:" in dr.stdout, f"[{tag}] regimen-doctor prints the runtime wiring")
        if wiring:
            check("claude-code" in dr.stdout, f"[{tag}] doctor detects claude-code wiring")
            check("hooks are NOT enabled" in dr.stdout or "hook gates are ACTIVE" in dr.stdout,
                  f"[{tag}] doctor reports the hooks' STATE (active/dormant), not their presence")


def main() -> int:
    base = tempfile.mkdtemp(prefix="ct-selftest-")
    try:
        # ---- generation scenarios ----
        s = os.path.join(base, "full")
        r = gen(s, name="Full Stack", backend="go", frontend="react-nextjs",
                arch="modular-monolith,multi-tenant", domain="b2b-saas", testing="bdd", wiring="yes")
        check(r.returncode == 0, "[full] generator ran (rc=0)")
        validate_project("full", s, name="Full Stack", wiring=True,
                         stacks=["go", "react-nextjs"], new_stacks=[], variants_expected=1)
        # arch/domain also emit skills that point at the canon
        for nm, canon in (("modular-monolith", "architecture"), ("multi-tenant", "architecture"),
                          ("b2b-saas", "domain")):
            sp = os.path.join(s, ".claude", "skills", nm, "SKILL.md")
            check(os.path.exists(sp), f"[skills] {nm}/SKILL.md created")
            check(os.path.exists(os.path.join(s, canon, f"{nm}.md")),
                  f"[skills] {nm} points at an existing {canon}/{nm}.md")

        # QG-NN-05 doctor evidence check (2026-07-03 audit S2): freeze a scope of 2 ids,
        # annotate one — the doctor must name the second; --qg must yield rc=1
        stub_state = os.path.join(s, "docs", "PROJECT-STATE.md")
        stub_body = open(stub_state, encoding="utf-8").read()
        check("## Frozen scope (QG-NN-05)" in stub_body,
              "[qg] the PROJECT-STATE stub carries the Frozen scope section")
        open(stub_state, "w", encoding="utf-8").write(
            "# PROJECT-STATE — QG fixture\n\n## Frozen scope (QG-NN-05)\n\n"
            "- Shipping root(s): `cmd/app/main.go`\n"
            "- `QGT-01` — criterion with evidence\n"
            "- `QGT-02` — criterion without evidence\n"
            "- `QGT-03` — ergonomics — waiver: no output differential\n")
        os.makedirs(os.path.join(s, "tests"), exist_ok=True)
        open(os.path.join(s, "tests", "assembled_test.go"), "w", encoding="utf-8").write(
            "// @qg:QGT-01\nfunc TestAssembled(t *testing.T) {}\n")
        # "checked-in" = the git index (ADR-017): the fixture must be a repo with staged files
        subprocess.run(["git", "init", "-q"], cwd=s, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=s, capture_output=True)
        dq = subprocess.run([sys.executable, os.path.join(s, "regimen-doctor.py"), "--dir", s],
                            cwd=s, capture_output=True, text=True)
        check("WITHOUT checked-in @qg-evidence" in dq.stdout and "QGT-02 (1/2)" in dq.stdout,
              "[qg] the doctor names exactly the uncovered scope-id (QGT-02; waiver QGT-03 is outside the check)")
        dqs = subprocess.run([sys.executable, os.path.join(s, "regimen-doctor.py"), "--dir", s, "--qg"],
                             cwd=s, capture_output=True, text=True)
        check(dqs.returncode == 1 and "QGT-02" in dqs.stdout,
              "[qg] strict --qg: an uncovered criterion = rc=1 (a slice's done-gate)")
        open(os.path.join(s, "tests", "assembled_test.go"), "a", encoding="utf-8").write("// @qg:QGT-02\n")
        subprocess.run(["git", "add", "-A"], cwd=s, capture_output=True)  # stage the new evidence
        dqg = subprocess.run([sys.executable, os.path.join(s, "regimen-doctor.py"), "--dir", s, "--qg"],
                             cwd=s, capture_output=True, text=True)
        check("@qg-evidence is in place (2 scope-id" in dqg.stdout and "waived: QGT-03" in dqg.stdout,
              "[qg] evidence was added — the doctor is green on QG-NN-05 (2/2) and lists the waiver")
        open(stub_state, "w", encoding="utf-8").write(stub_body)  # restore the stub — the full project isn't touched further

        # scan for "N D T" digits (2026-07-03 audit S3/D2): a stale digit in a subagent's prose
        # must red-flag sync-roles --check, while the tables remain in sync
        bap = os.path.join(s, ".claude", "agents", "ba.md")
        ba_body = open(bap, encoding="utf-8").read()
        check("`3 D T`" in ba_body, "[digits] fixture: ba.md carries the digit 3 D T")
        open(bap, "w", encoding="utf-8").write(ba_body.replace("`3 D T`", "`9 D T`"))
        cd = subprocess.run([sys.executable, os.path.join(s, "sync-roles.py"), "--check"], cwd=s,
                            capture_output=True, text=True)
        check(cd.returncode == 1 and "9 D T" in cd.stderr and "ba.md" in cd.stderr,
              "[digits] a stale digit in a subagent's prose = --check rc=1 with the file name")
        open(bap, "w", encoding="utf-8").write(ba_body)
        cd2 = subprocess.run([sys.executable, os.path.join(s, "sync-roles.py"), "--check"], cwd=s,
                             capture_output=True, text=True)
        check(cd2.returncode == 0, "[digits] the digit was restored — --check is green again")

        s = os.path.join(base, "py")
        r = gen(s, name="Py Service", backend="python", frontend="none",
                arch="modular-monolith", domain="regulated", testing="test-along", wiring="no")
        check(r.returncode == 0, "[py] generator ran (rc=0)")
        validate_project("py", s, name="Py Service", wiring=False,
                         stacks=["python"], new_stacks=[], variants_expected=1)

        s = os.path.join(base, "newstack")
        r = gen(s, name="Edge Proxy", backend="rust", frontend="none",
                arch="event-driven", domain="none", testing="tdd", wiring="no")
        check(r.returncode == 0, "[newstack] generator ran (rc=0)")
        validate_project("newstack", s, name="Edge Proxy", wiring=False,
                         stacks=[], new_stacks=["rust"], variants_expected=1)

        s = os.path.join(base, "minimal")
        r = gen(s, name="Bare", backend="none", frontend="none",
                arch="", domain="", testing="test-along", wiring="no")
        check(r.returncode == 0, "[minimal] generator ran (rc=0)")
        validate_project("minimal", s, name="Bare", wiring=False,
                         stacks=[], new_stacks=[], variants_expected=1)

        # ---- multi-model: --harness codex lays down overlays/codex, NOT .claude ----
        cx = os.path.join(base, "codex")
        r = gen(cx, name="Codex Svc", backend="go", frontend="none",
                arch="modular-monolith", domain="none", testing="test-along",
                wiring="yes", harness="codex")
        check(r.returncode == 0, "[codex] generator --harness codex (rc=0)")
        check(os.path.exists(os.path.join(cx, "AGENTS.md")), "[codex] AGENTS.md (runtime entry) is in place")
        check(not os.path.isdir(os.path.join(cx, ".claude")), "[codex] .claude/ NOT copied for codex")
        # ADR-012: a codex project carries NO CLAUDE.md FILE (entry = a per-harness native AGENTS.md)
        check(not os.path.exists(os.path.join(cx, "CLAUDE.md")), "[codex] there's no CLAUDE.md FILE (ADR-012)")
        check(os.path.exists(os.path.join(cx, "core", "principles.md")), "[codex] the neutral core (core/) is in place")
        # ADR-012: AGENTS.md carries CONTENT (codex-delta header + shared body), not a "read CLAUDE.md" pointer
        agtxt = open(os.path.join(cx, "AGENTS.md"), encoding="utf-8").read() if os.path.exists(os.path.join(cx, "AGENTS.md")) else ""
        check("What differs on Codex" in agtxt, "[codex] AGENTS.md carries the codex-delta header")
        check("## Stack" in agtxt and "## Testing philosophy" in agtxt,
              "[codex] AGENTS.md carries the shared body (Stack/Testing), not a pointer")
        check("[roles/reviewer.md]" in agtxt, "[codex] AGENTS.md carries the neutral role table (roles/*.md)")
        check("Codex Svc" in agtxt, "[codex] AGENTS.md is filled with the project name (entry with content)")
        # every role in roles.json -> .codex/agents/<agent>.toml exists (role-map completeness)
        cxroles = json.load(open(os.path.join(cx, "roles.json")))["roles"] if os.path.exists(os.path.join(cx, "roles.json")) else []
        cxadir = os.path.join(cx, ".codex", "agents")
        for rr in cxroles:
            check(os.path.exists(os.path.join(cxadir, f"{rr['agent']}.toml")),
                  f"[codex] role {rr['agent']} -> .codex/agents/{rr['agent']}.toml")
        # sandbox_mode + developer_instructions are valid on ALL .toml files (incl. dispatch agents outside
        # roles.json: architect/auditor/red-team/blue-team/arbiter) — parity with the claude side (it iterates listdir of agents)
        for fn in (sorted(os.listdir(cxadir)) if os.path.isdir(cxadir) else []):
            if not fn.endswith(".toml"):
                continue
            tb = open(os.path.join(cxadir, fn), encoding="utf-8").read()
            check(SANDBOX_MODE_RE.search(tb) is not None,
                  f"[codex] {fn}: valid sandbox_mode")
            check('developer_instructions' in tb and len(tb.split('developer_instructions', 1)[1]) > 40,
                  f"[codex] {fn}: non-empty developer_instructions")
        # stack/arch skills are emitted into .codex/skills/ (not .claude/skills/)
        check(os.path.exists(os.path.join(cx, ".codex", "skills", "go", "SKILL.md")),
              "[codex] stack skill is emitted into .codex/skills/")
        check(os.path.exists(os.path.join(cx, ".codex", "skills", "debugging", "SKILL.md")),
              "[codex] universal skill in .codex/skills/")
        # audit C1: paths: frontmatter — Claude-only (Codex skill-creator: only name+description,
        # "do not include any other fields"). No codex skill must carry paths:.
        cxskills = glob.glob(os.path.join(cx, ".codex", "skills", "**", "SKILL.md"), recursive=True)
        paths_leak = [os.path.relpath(p, cx) for p in cxskills
                      if any(l.startswith("paths:") for l in read(p).splitlines())]
        check(not paths_leak, "[codex] zero paths: in codex-skill frontmatter (a Claude-only key)" +
              (f" — {paths_leak}" if paths_leak else ""))
        # sync-roles is green in the codex project (AGENTS.md in sync)
        if os.path.exists(os.path.join(cx, "sync-roles.py")):
            cpc = subprocess.run([sys.executable, "sync-roles.py", "--check"], cwd=cx,
                                 capture_output=True, text=True)
            check(cpc.returncode == 0, "[codex] sync-roles --check is green in the codex project")
        check(not dangling(cx), "[codex] no dangling links in the codex project")
        # ADR-012: a bare/referential "CLAUDE.md" in a codex project only via allowlist; zero (a)/self-ref.
        # neutralize_dead_links does NOT catch bare text — we check by string. Allowlist (b honest-delta):
        # any line explicitly naming "AGENTS.md" or "Claude Code" (per-harness honest delta).
        # The (c) label "Prompt for Claude Code" contains "Claude Code", not "CLAUDE.md" → doesn't match.
        # The (b)-homes core/memory.md + core/portability.md are saturated with LEGITIMATE CLAUDE.md
        # mentions (Claude memory/portability facts) that a line-by-line allowlist wouldn't pass. We do NOT
        # amnesty them wholesale (that's a blind spot for a new (a)-leak — audit B2): instead of a whole-file
        # exempt — a TRIPWIRE on the occurrence count. A new (a)-leak into these files raises the count above
        # baseline → the test fails, requiring a deliberate check and an explicit bump (like the N-overlay debt tripwire).
        B_HOMES = {os.path.join("core", "memory.md"): 9, os.path.join("core", "portability.md"): 8}
        leak_claude, bhome_over = [], []
        for p in md_files(cx):
            rel = os.path.relpath(p, cx)
            text = read(p)
            if rel in B_HOMES:
                n = text.count("CLAUDE.md")
                if n > B_HOMES[rel]:
                    bhome_over.append(f"{rel}: {n} > baseline {B_HOMES[rel]}")
                continue
            for ln, line in enumerate(text.splitlines(), 1):
                if "CLAUDE.md" not in line:
                    continue
                if "AGENTS.md" in line or "Claude Code" in line or "Claude-Code" in line:
                    continue  # an honest per-harness delta — acceptable
                leak_claude.append(f"{rel}:{ln}")
        check(not leak_claude,
              "[codex] zero misplaced CLAUDE.md in the codex project (a/self-ref)" +
              (f" — {leak_claude[:6]}" if leak_claude else ""))
        check(not bhome_over,
              "[codex] (b)-homes memory/portability with no new CLAUDE.md beyond baseline" +
              (f" — {bhome_over}" if bhome_over else ""))
        # P5: regimen-doctor is harness-aware — reports the codex overlay's STATE, not its presence
        dcx = subprocess.run([sys.executable, "regimen-doctor.py", "--dir", "."], cwd=cx,
                             capture_output=True, text=True)
        check("Traceback" not in dcx.stderr, "[codex] regimen-doctor has no traceback on a codex project")
        check("runtime wiring: codex" in dcx.stdout, "[codex] doctor detects the codex wiring")
        check("agent profiles" in dcx.stdout, "[codex] doctor reports the state of codex agent profiles")
        check("accountability" in dcx.stdout,
              "[codex] doctor honestly reports the accountability class of hooks/docs-only (KL-7/G2)")

        # ---- codex prose mode (wiring=no): AGENTS.md exists, no .codex/ wiring ----
        cxp = os.path.join(base, "codex-prose")
        r = gen(cxp, name="Codex Prose", backend="none", frontend="none",
                arch="", domain="", testing="test-along", wiring="no", harness="codex")
        check(r.returncode == 0, "[codex-prose] generator (rc=0)")
        check(os.path.exists(os.path.join(cxp, "AGENTS.md")), "[codex-prose] AGENTS.md (entry) exists even without wiring")
        check(not os.path.isdir(os.path.join(cxp, ".codex")), "[codex-prose] no .codex/ wiring (wiring=no)")

        # ---- dual-mode: new creates a delegating Day-0 ----
        d0 = os.path.join(base, "newmode")
        r = gen(d0, name="Kick", backend="go", frontend="none",
                arch="", domain="", testing="test-along", wiring="no", mode="new")
        day0 = os.path.join(d0, "docs", "day-0-guide.md")
        check(r.returncode == 0 and os.path.exists(day0), "[mode-new] day-0-guide.md created")
        if os.path.exists(day0):
            b = open(day0, encoding="utf-8").read()
            check("go mod init" in b, "[mode-new] day-0 contains the stack's delegating init command")

        # ---- dual-mode: overlay doesn't overwrite an existing project ----
        ov = os.path.join(base, "overlay")
        os.makedirs(ov)
        open(os.path.join(ov, "README.md"), "w").write("# Existing\n")
        open(os.path.join(ov, "CLAUDE.md"), "w").write("# existing entry\n")
        open(os.path.join(ov, "main.go"), "w").write("package main\n")
        r = gen(ov, name="Ov", backend="go", frontend="none",
                arch="", domain="", testing="test-along", wiring="no", mode="overlay")
        check(r.returncode == 0, "[mode-overlay] generator ran (rc=0)")
        check(open(os.path.join(ov, "README.md")).read() == "# Existing\n",
              "[mode-overlay] the existing README.md wasn't overwritten")
        check(open(os.path.join(ov, "CLAUDE.md")).read() == "# existing entry\n",
              "[mode-overlay] the existing CLAUDE.md wasn't overwritten")
        check(os.path.exists(os.path.join(ov, "CLAUDE.regimen.md")),
              "[mode-overlay] the regimen was saved as CLAUDE.regimen.md")
        check(os.path.exists(os.path.join(ov, "core", "principles.md")),
              "[mode-overlay] the regimen (core/) was laid alongside")
        check(not os.path.exists(os.path.join(ov, "docs", "day-0-guide.md")),
              "[mode-overlay] Day-0 isn't created (the project already exists)")

        # ---- refusal on a non-empty directory (default mode new) ----
        r2 = gen(s, name="Bare2", backend="none", frontend="none",
                 arch="", domain="", testing="test-along", wiring="no")
        check(r2.returncode != 0, "[safety] a repeat generation (new) into a non-empty directory is rejected")

        # ---- regressions of confirmed bugs (adversarial probe) ----
        e = os.path.join(base, "edge-emptyslug")
        r = gen(e, name="P", backend="???", frontend="none", arch="", domain="", testing="bdd", wiring="no")
        check(r.returncode == 0 and not os.path.exists(os.path.join(e, "stack", ".md")),
              "[edge] a stack with an empty slug doesn't create a hidden stack/.md")
        check("slug" in (r.stderr or ""), "[edge] a warning about the empty slug")

        e = os.path.join(base, "edge-collide")
        r = gen(e, name="P", backend="c++", frontend="c#", arch="", domain="", testing="bdd", wiring="no")
        sfiles = sorted(os.listdir(os.path.join(e, "stack"))) if os.path.isdir(os.path.join(e, "stack")) else []
        check(r.returncode == 0 and "duplicates" in (r.stderr or ""),
              "[edge] c++/c# (a slug collision) warns, doesn't clobber silently")
        check(len(sfiles) == 1, f"[edge] collision -> one stack file (actual {sfiles})")

        e = os.path.join(base, "edge-ws")
        r = gen(e, name="P", backend="  go  ", frontend="none", arch="", domain="", testing="bdd", wiring="no")
        gomd = os.path.join(e, "stack", "go.md")
        body = open(gomd, encoding="utf-8").read() if os.path.exists(gomd) else ""
        check(os.path.exists(gomd) and "SKELETON for a new stack" not in body,
              "['  go  '] is normalized to the real stack/go.md, not a skeleton")

        ff = os.path.join(base, "edge-isfile")
        open(ff, "w").write("x")
        r = gen(ff, name="P", backend="none", frontend="none", arch="", domain="", testing="bdd", wiring="no")
        check(r.returncode != 0 and "Traceback" not in (r.stderr or ""),
              "[edge] --dir=a file is rejected without a traceback")

        r = subprocess.run([sys.executable, GEN, "--name", "P", "--backend", "none", "--frontend", "none",
                            "--arch", "", "--domain", "", "--testing", "bdd", "--wiring", "no"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        check(r.returncode != 0, "[edge] non-tty without --dir is rejected (doesn't write into the parent cwd)")

        e = os.path.join(base, "edge-dup")
        gen(e, name="P", backend="go", frontend="go", arch="", domain="", testing="bdd", wiring="no")
        cl = open(os.path.join(e, "CLAUDE.md"), encoding="utf-8").read()
        sec = cl.split("## Stack", 1)[-1].split("##", 1)[0]
        check(sec.count("- go") == 1, "[edge] go+go is deduplicated into one bullet")

        # ---- health of the package itself ----
        bad = ["layered-three-tier", "PROJECT_CONTEXT", "galлюцин", "writeen", "不"]
        hits = []
        for p in md_files(PACK):
            if "/examples/" in p:
                continue
            t = read(p)
            for b in bad:
                if b in t:
                    hits.append(f"{os.path.relpath(p, PACK)}:{b}")
        check(not hits, "[pack] no dead strings/typos" + (f" {hits}" if hits else ""))

        cp = subprocess.run([sys.executable, "-m", "py_compile", GEN], capture_output=True, text=True)
        check(cp.returncode == 0, "[pack] new-project.py compiles")

        # handbook: all table-of-contents files are in place (ORDER doesn't drift under renames)
        rh = os.path.join(PACK, "render-handbook.py")
        if os.path.exists(rh):
            cp = subprocess.run([sys.executable, "-m", "py_compile", rh], capture_output=True, text=True)
            check(cp.returncode == 0, "[pack] render-handbook.py compiles")
            cp = subprocess.run([sys.executable, rh, "--check"], capture_output=True, text=True)
            check(cp.returncode == 0, f"[pack] render-handbook --check (all ORDER files are in place): {cp.stderr.strip()[:80]}")

        # the package's role map doesn't drift relative to roles.json
        cp = subprocess.run([sys.executable, os.path.join(PACK, "sync-roles.py"), "--check"],
                            capture_output=True, text=True)
        check(cp.returncode == 0, "[pack] sync-roles --check is green (roles.json ↔ tables)")

        # README ADR tables don't lag behind docs/adr/ — this drifted twice with no gate
        # (audit 2026-07-03 E1: stuck at 013; audit 2026-07-06 S1: stuck at 016).
        adr_files = sorted(glob.glob(os.path.join(PACK, "docs", "adr", "[0-9][0-9][0-9]-*.md")))
        if adr_files:
            latest_adr = os.path.basename(adr_files[-1])
            for readme in ("README.md", "README.ru.md"):
                t = open(os.path.join(PACK, readme), encoding="utf-8").read()
                check(f"](docs/adr/{latest_adr})" in t,
                      f"[pack] {readme} ADR table includes the latest ADR ({latest_adr})")

        # tripwire: new-project.fill_claude cuts sections by the EXACT headings of the CLAUDE.md template
        # (regex `## Stack`→`## Architecture`, `## Testing philosophy`→`## Project specifics`).
        # Renaming any of them silently breaks the fill-in (try/except → leaves placeholders behind).
        # This check fails earlier, forcing both the template and fill_claude to be updated in sync.
        entry_tmpl = open(os.path.join(PACK, "CLAUDE.md"), encoding="utf-8").read()
        for h in ("## Stack", "## Architecture", "## Testing philosophy", "## Project specifics"):
            check(h in entry_tmpl, f"[pack] the CLAUDE.md template contains the heading \"{h}\" (fill_claude relies on it)")

        # ---- file-count backstop (ADR-010:115): tripwire for unbearable N-overlay debt ----
        # Every role is reproduced by EXACTLY ONE runtime-specific agent file PER RUNTIME:
        #   claude-code -> .claude/agents/<agent>.md ; codex -> overlays/codex/.codex/agents/<agent>.toml
        # → adding a role costs (N runtimes) files. This block a) checks that a role's per-runtime
        # footprint = 1 (doesn't grow), and b) TRIGGERS when the number of runtime overlays exceeds a
        # threshold — forcing a deliberate raise of the threshold AND a re-read of the debt warning (ADR-010/011).
        pack_roles = json.load(open(os.path.join(PACK, "roles.json")))["roles"]
        RT_AGENT = {
            "claude-code": lambda a: os.path.join(PACK, ".claude", "agents", f"{a}.md"),
            "codex":       lambda a: os.path.join(PACK, "overlays", "codex", ".codex", "agents", f"{a}.toml"),
        }
        for rt, fn in RT_AGENT.items():
            miss = [r["agent"] for r in pack_roles if not os.path.exists(fn(r["agent"]))]
            check(not miss, f"[backstop] {rt}: every role in roles.json has exactly one agent file (missing: {miss})")
        # the number of runtime overlays actually present = .claude + every overlays/ subdirectory
        ovdir = os.path.join(PACK, "overlays")
        runtimes_present = (1 if os.path.isdir(os.path.join(PACK, ".claude")) else 0) + (
            len([d for d in os.listdir(ovdir) if os.path.isdir(os.path.join(ovdir, d))])
            if os.path.isdir(ovdir) else 0)
        # a new role's footprint = (runtimes) × (1 file/runtime). Threshold 2 = claude + codex.
        RUNTIME_THRESHOLD = 2
        check(runtimes_present <= RUNTIME_THRESHOLD,
              f"[backstop] runtime overlays present={runtimes_present} > threshold {RUNTIME_THRESHOLD}: "
              f"adding a role now touches {runtimes_present} files. Raise RUNTIME_THRESHOLD "
              f"DELIBERATELY, after re-reading the N-overlay debt (ADR-010 §Consequences) — this is a tripwire, not a bug.")

        # hooks are in place, executable and wired into settings.json.example
        for h in ("check-loc.sh", "checkpoint-precompact.sh", "check-no-todo.sh", "numeric-command.sh"):
            hp = os.path.join(PACK, ".claude", "hooks", h)
            check(os.path.exists(hp) and os.access(hp, os.X_OK), f"[pack] hook {h} exists and is executable")
        sj = json.load(open(os.path.join(PACK, ".claude", "settings.json.example")))
        check("PreCompact" in sj.get("hooks", {}), "[pack] settings.json.example contains the PreCompact hook")
        check("UserPromptSubmit" in sj.get("hooks", {}),
              "[pack] settings.json.example contains the UserPromptSubmit hook (numeric-command dispatch)")

        # numeric-command.sh contract: 1-3 bare numbers -> injects the dispatch order; text -> silent
        ncmd = os.path.join(PACK, ".claude", "hooks", "numeric-command.sh")
        for p, wants in (("35", True), ("1 5 24", True), ("0 5", True),
                         ("how are you", False), ("35 files changed", False), ("1.5", False)):
            out = subprocess.run([ncmd], input=json.dumps({"prompt": p}),
                                 capture_output=True, text=True)
            check(out.returncode == 0 and bool(out.stdout.strip()) == wants,
                  f"[pack] numeric-command.sh({p!r}) -> {'inject' if wants else 'silent'}, rc=0")

        # constitution: every ID from constitution.md's registry is tagged on the canonical rule
        const = open(os.path.join(PACK, "core", "constitution.md"), encoding="utf-8").read()
        ids = set(re.findall(r"\b[A-Z]{2}-NN-\d{2}\b", const))
        check(len(ids) >= 8, f"[pack] constitution.md contains the non-negotiable registry (found {len(ids)})")
        core_src = ""
        for cf in ("principles.md", "code-quality.md", "quality-gates.md"):
            core_src += open(os.path.join(PACK, "core", cf), encoding="utf-8").read()
        missing = [i for i in ids if i not in core_src]
        check(not missing, f"[pack] every constitution ID is tagged on the canon (untagged: {sorted(missing)})")

        check("_TEMPLATE" not in subprocess.run(
            [sys.executable, GEN, "--list"], capture_output=True, text=True).stdout,
            "[pack] _TEMPLATE.md didn't leak into the stack list")

        # every described stack must close out the "Clean build" contract (core/quality-gates.md
        # references it by name); this used to be checked only for skeletons from _TEMPLATE.
        for sp in md_files(os.path.join(PACK, "stack")):
            if os.path.basename(sp).startswith("_"):
                continue
            body = open(sp, encoding="utf-8").read()
            check("Clean build" in body,
                  f"[pack] {os.path.relpath(sp, PACK)} contains the \"Clean build\" section")

        # Author context (project/people/infra names) must not leak ANYWHERE, including
        # examples/. The marker words themselves are kept in the gitignored `.leakwords` file (one word
        # per line, `#` — a comment), so names don't live in tracked code and don't get re-leaked by the test itself.
        # No file (e.g. on someone else's clone) → the check is skipped, the count doesn't break.
        leakfile = os.path.join(PACK, ".leakwords")
        leak_words = []
        if os.path.exists(leakfile):
            leak_words = [w.strip().lower() for w in open(leakfile, encoding="utf-8")
                          if w.strip() and not w.lstrip().startswith("#")]
        # Scan only TRACKED files — exactly what will go out in a push; local scratch
        # (gitignored) with absolute paths `/Users/<name>/…` must not break the check.
        leak_hits = []
        if leak_words:
            tracked = subprocess.run(["git", "-C", PACK, "ls-files", "*.md"],
                                     capture_output=True, text=True)
            scan = ([os.path.join(PACK, x) for x in tracked.stdout.split("\n") if x]
                    if tracked.returncode == 0 and tracked.stdout.strip()
                    else [p for p in md_files(PACK) if "/scratchpad/" not in p.replace(os.sep, "/")])
            for p in scan:
                low = read(p).lower()
                for b in leak_words:
                    if b in low:
                        leak_hits.append(f"{os.path.relpath(p, PACK)}:{b}")
        check(not leak_hits, "[pack] no leaked author context" + (f" {leak_hits}" if leak_hits else ""))

        # ---- QG-NN-05 hardened checker (ADR-017 phase 1) ----
        # The pre-hardening checker had PROVEN false-green paths (vacuous pass, prose spoofing,
        # no git awareness) and false-reds (`build-qa/` skipped by a substring match) — each case
        # below pins one of them. Fixture vocabulary:
        ROOTS = "Shipping root(s): `src/main.ts` (web) — fixed by the architect.\n"
        ITEM = "- `INV-01` — invite flow works end to end.\n"
        EVID = ("tests/assembled/invite.test.ts", "// @qg:INV-01\n")
        qbase = os.path.join(base, "qg")

        r = doctor(qg_tree(qbase, "vac-nostate", None, git=False), qg=True)
        check(r.returncode == 1 and "vacuous" in r.stdout,
              "[qg] --qg: missing Frozen-scope section = 🔴 vacuous (was: silent exit 0)")
        r = doctor(qg_tree(qbase, "vac-nostate2", None, git=False))
        check(r.returncode == 0 and "QG-NN-05:" not in r.stdout,
              "[qg] soft run: missing section stays silent (kickoff/mid-slice is legitimate)")
        r = doctor(qg_tree(qbase, "vac-empty", ROOTS), qg=True)
        check(r.returncode == 1 and "vacuous" in r.stdout,
              "[qg] --qg: section with only the roots line = 🔴 vacuous (no scope items)")

        drift = qg_tree(qbase, "drift", ROOTS + "- [ ] INV-01 done\n- [ ] INV-02 done\n")
        r = doctor(drift, qg=True)
        check(r.returncode == 1 and "parse as neither" in r.stdout,
              "[qg] --qg: format drift = 🔴 (was: 🟡 even under --qg)")
        r = doctor(drift)
        check(r.returncode == 0 and "🟡 QG-NN-05" in r.stdout,
              "[qg] soft run: format drift = 🟡, non-blocking")
        r = doctor(qg_tree(qbase, "partial", ROOTS + ITEM + "- INV-02 without backticks\n",
                           files=[EVID]), qg=True)
        check(r.returncode == 1 and "parse as neither" in r.stdout,
              "[qg] --qg: partially drifted section = 🔴, no silent scope shrink")

        r = doctor(qg_tree(qbase, "prose-spoof", ROOTS + ITEM,
                           files=[("docs/day-1-guide.md", "assembled path: @qg:INV-01\n")]), qg=True)
        check(r.returncode == 1 and "INV-01" in r.stdout,
              "[qg] --qg: @qg in committed prose (.md) is NOT evidence (allowlist)")
        r = doctor(qg_tree(qbase, "ok-buildqa", ROOTS + ITEM,
                           files=[("build-qa/invite.test.ts", "// @qg:INV-01\n")]), qg=True)
        check(r.returncode == 0 and "1 scope-id" in r.stdout,
              "[qg] --qg: evidence in build-qa/ IS seen (was: false-red via substring SKIP_DIRS)")
        r = doctor(qg_tree(qbase, "unstaged", ROOTS + ITEM, files_after_add=[EVID]), qg=True)
        check(r.returncode == 1 and "INV-01" in r.stdout,
              "[qg] --qg: worktree-only evidence (not in the git index) doesn't count as checked-in")
        nogit = qg_tree(qbase, "nogit", ROOTS + ITEM, files=[EVID], git=False)
        r = doctor(nogit, qg=True)
        check(r.returncode == 1 and "not a git repository" in r.stdout,
              "[qg] --qg: non-git tree = 🔴 (checked-in semantics unverifiable)")
        check(doctor(nogit).returncode == 0, "[qg] soft run: non-git tree = 🟡, non-blocking")

        r = doctor(qg_tree(qbase, "dup", ROOTS + ITEM + "- `INV-01` — duplicated criterion.\n",
                           files=[EVID]), qg=True)
        check(r.returncode == 1 and "duplicate" in r.stdout,
              "[qg] --qg: duplicate scope-ids = 🔴 (one annotation must not close several criteria)")
        r = doctor(qg_tree(qbase, "waiver", ROOTS + ITEM +
                           "- `INV-03` — toast auto-hides — waiver: ergonomics, no output differential.\n",
                           files=[EVID]), qg=True)
        check(r.returncode == 0 and "waived: INV-03" in r.stdout,
              "[qg] --qg: explicit `waiver: <reason>` excluded from reconciliation AND listed")
        r = doctor(qg_tree(qbase, "waiver-legacy", ROOTS +
                           "- `INV-04` — supports the waiver flow end to end.\n"), qg=True)
        check(r.returncode == 1 and "INV-04" in r.stdout,
              "[qg] --qg: the bare word \"waiver\" (no colon) no longer smuggles an item out")
        r = doctor(qg_tree(qbase, "wrapped", ROOTS +
                           "- `INV-05` — a long criterion that wraps onto\n  the next indented line.\n",
                           files=[("tests/a.test.ts", "// @qg:INV-05\n")]), qg=True)
        check(r.returncode == 0,
              "[qg] --qg: indented continuation of a wrapped item is legal (example-file style)")
        # the two allowlist/parser branches previously without a fixture (audit 2026-07-06 S9):
        r = doctor(qg_tree(qbase, "manifest", ROOTS + ITEM,
                           files=[("qg-manifest.txt",
                                   "@qg:INV-01 tests/assembled/invite.test.ts::e2e\n")]), qg=True)
        check(r.returncode == 0 and "1 scope-id" in r.stdout,
              "[qg] --qg: evidence carried only by a generated qg-manifest.* counts (second carrier)")
        r = doctor(qg_tree(qbase, "html-comment", ROOTS +
                           "<!-- one atomic criterion per line -->\n" + ITEM +
                           "<!-- multi-line\nfill-in hint\n-->\n", files=[EVID]), qg=True)
        check(r.returncode == 0 and "1 scope-id" in r.stdout,
              "[qg] --qg: HTML comments (incl. multi-line) inside the section parse, not unparseable")

        # segment-match SKIP_DIRS: a project under a parent build/ is still fully scanned,
        # build/ INSIDE the project is still pruned (md_files blast radius, _pack_lib)
        pb = qg_tree(os.path.join(qbase, "build"), "inner", None, git=False,
                     files=[("docs/leftover.md", "unfilled {{x}}\n")])
        check(doctor(pb).returncode == 1 and "placeholders" in doctor(pb).stdout.lower(),
              "[qg] project under a parent build/ dir is scanned (was: whole tree silently skipped)")
        mt = os.path.join(qbase, "mdtest")
        for rel in ("build/skip.md", "build-qa/seen.md", "src/seen2.md",
                    "build-tidy/_deps/gtest/README.md", "target/doc/skip.md"):
            p = os.path.join(mt, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").close()
        got = {os.path.relpath(p, mt) for p in md_files(mt)}
        check(got == {os.path.join("build-qa", "seen.md"), os.path.join("src", "seen2.md")},
              f"[qg] md_files: build//_deps//target/ pruned as segments, build-qa/ visible "
              f"(got: {sorted(got)})")

        # ---- link-gate extension: internal links check_dead_links can't see ----
        # Field lesson: a single broken internal markdown link in a project doc turned the doctor
        # red only PARTIALLY and froze a whole working day. check_link_extensions closes three blind
        # spots beyond single-line [text](path) — each must turn the doctor 🔴 (a hard gate).
        lbase = os.path.join(base, "links")

        def link_proj(name, files):
            root = os.path.join(lbase, name)
            for rel, body in files:
                p = os.path.join(root, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(body)
            return root

        # clean: a valid self-#anchor (incl. a two-hyphen slug from a removed em-dash — the GitHub
        # rule that a whitespace-collapsing slug would false-red), a valid reference def+use, and a
        # multi-line link to a real file → all resolve → green + rc=0.
        clean = link_proj("clean", [
            ("README.md",
             "# Title\n\n## Real Heading\n\n## A — dashed heading\n\n"
             "- jump to [the section](#real-heading)\n"
             "- and to [the dashed one](#a--dashed-heading)\n"
             "- a [reference link][home] resolves\n"
             "- a target that wraps onto\n  [the next line](\n  other.md)\n\n"
             "[home]: other.md\n"),
            ("other.md", "# Other\n")])
        rok = doctor(clean)
        check(rok.returncode == 0 and
              "anchors / multi-line / reference-style links resolve" in rok.stdout,
              "[links] clean anchors/multi-line/reference-style links pass (rc=0)")

        # (a) a dead #anchor — the file exists but the heading doesn't (invisible to check_dead_links)
        ra = doctor(link_proj("anchor", [("d.md", "# Title\n\nsee [x](#no-such-heading)\n")]))
        check(ra.returncode == 1 and "Broken internal links" in ra.stdout
              and "no-such-heading" in ra.stdout,
              "[links] dead #anchor = 🔴 (was invisible: check_dead_links doesn't validate fragments)")

        # (b) a multi-line link whose target does not resolve (the single-line scanner never sees it)
        rb = doctor(link_proj("multiline", [("d.md", "# T\n\n[text](\nmissing.md)\n")]))
        check(rb.returncode == 1 and "multi-line link" in rb.stdout and "missing.md" in rb.stdout,
              "[links] multi-line link to a missing file = 🔴")

        # (c) a reference-style link with no matching definition
        rf = doctor(link_proj("refstyle", [("d.md", "# T\n\nan [orphan][undef] link\n")]))
        check(rf.returncode == 1 and "reference-style link" in rf.stdout and "undef" in rf.stdout,
              "[links] reference-style link with an undefined reference = 🔴")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    # ---- report ----
    passed = sum(1 for ok, _ in results if ok)
    failed = [m for ok, m in results if not ok]
    for m in failed:
        print("  ✗", m)
    print(f"\n{passed}/{len(results)} checks green.")
    if failed:
        print(f"✗ {len(failed)} FAIL")
        return 1
    print("✓ all green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
