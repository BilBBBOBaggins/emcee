#!/usr/bin/env python3
"""
new-project.py — project generator from emcee (cookie-cutter).

Assembles a fresh project: copies core/ + roles/, the chosen stack/architecture/domain,
fills in what it can in CLAUDE.md, bootstraps docs/, optionally lays down the .claude/ wiring,
and — most importantly — if the chosen stack is NOT yet described, generates a skeleton
stack/<name>.md per the contract (with a mandatory "Clean build" section) and prints a
prompt to finish filling it in.

Examples:
  ./new-project.py --list
  ./new-project.py --name "Acme Teams" --dir ../acme \
      --backend go --frontend react-nextjs \
      --arch modular-monolith,multi-tenant --domain b2b-saas \
      --testing bdd --wiring yes
  ./new-project.py --name "Edge Proxy" --dir ../edge --backend rust --frontend none
      # rust isn't described yet -> creates a stack/rust.md skeleton

No flags in a terminal — asks interactively.
"""
from __future__ import annotations
import argparse, os, re, shutil, sys

PACK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PACK)
# Shared primitives (finding #4; consolidation C1 of the 2026-07-03 audit)
from _pack_lib import LINK, md_files, local_target, target_exists, iter_lines, count_placeholders, read

SKIP_TOP = {"new-project.py", "examples", "README.md", ".git", ".gitignore", "docs"}
TESTING = {"bdd": "Option 1", "test-along": "Option 2", "tdd": "Option 3"}


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
    raw = ask("Pick numbers, comma-separated (empty = none)")
    out = []
    for tok in raw.split(","):
        tok = tok.strip()
        if tok.isdigit() and 1 <= int(tok) <= len(options):
            out.append(options[int(tok) - 1])
        elif tok in options:
            out.append(tok)
    return out


def write(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(t)


def neutralize_dead_links(target: str) -> int:
    """[text](path) -> text for links whose target doesn't exist in the generated
    project (links to modules that weren't chosen). .md traversal, fence-tracking and the
    resolution predicate — shared _pack_lib primitives (same as selftest.py/regimen-doctor.py)."""
    fixed = 0
    for p in md_files(target):
        d = os.path.dirname(p)
        out_lines = []
        changed = False
        for _ln, line, in_fence in iter_lines(read(p), keepends=True):
            if in_fence:
                out_lines.append(line)
                continue

            def repl(m):
                nonlocal changed
                tt = local_target(m.group(2))
                if tt is None or target_exists(d, tt):
                    return m.group(0)
                changed = True
                return m.group(1)  # dead link -> keep only the text

            out_lines.append(LINK.sub(repl, line))
        if changed:
            write(p, "".join(out_lines))
            fixed += 1
    return fixed


# ---------- CLAUDE.md transforms (each best-effort, never fatal) ----------

def fill_claude(text: str, name: str, stacks: list[str], testing: str, warns: list[str]) -> str:
    text = text.replace("{{PROJECT_NAME}}", name)

    # Stack: replace the block between "## Stack" and "## Architecture"
    try:
        bullets = "\n".join(f"- {s}" for s in stacks) or "- {{project stack}}"
        text = re.sub(r"(## Stack\n).*?(\n## Architecture)",
                      lambda m: m.group(1) + "\n" + bullets + "\n" + m.group(2),
                      text, count=1, flags=re.S)
    except Exception:
        warns.append("couldn't fill in the '## Stack' section — fill it in by hand")

    # Testing philosophy: keep only the chosen option
    if testing in TESTING:
        keep = TESTING[testing]
        try:
            m = re.search(r"(## Testing philosophy\n).*?(\n## Project specifics)", text, flags=re.S)
            if m:
                variants = re.split(r"(?=### Option )", m.group(0))
                head = variants[0]
                head = re.sub(r"\{\{Pick one of the three[^}]*\}\}\n*", "", head)
                chosen = [v for v in variants[1:] if v.startswith(f"### {keep}")]
                newblock = head + ("".join(chosen) if chosen else "")
                text = text[:m.start()] + newblock + text[m.end():]
        except Exception:
            warns.append("couldn't trim 'Testing philosophy' down to one option — left all of them")
    return text


# ---------- per-harness entry (ADR-012) ----------

ENTRY_BODY_MARK = "<!-- ENTRY-BODY:START"


def assemble_codex_entry(filled_entry: str, warns: list[str]) -> str:
    """ADR-012: the codex entry `AGENTS.md` = title/desc + codex-delta header + the SHARED BODY (ENTRY-BODY)
    from the filled-in entry template. The body is the single source (same as CLAUDE.md's), the header is
    per-harness. This way a codex project gets a native entry WITH CONTENT, no CLAUDE.md file and no
    "read CLAUDE.md" pointer."""
    header_path = os.path.join(PACK, "overlays", "codex", "_agents-header.md")
    if ENTRY_BODY_MARK not in filled_entry or not os.path.exists(header_path):
        warns.append("codex entry: no ENTRY-BODY marker or _agents-header.md — AGENTS.md = body as-is")
        return filled_entry
    head, _, body_rest = filled_entry.partition(ENTRY_BODY_MARK)
    body = ENTRY_BODY_MARK + body_rest
    header = read(header_path)
    return head.rstrip() + "\n\n" + header.strip() + "\n\n" + body.lstrip() + "\n"


# ---------- docs/ bootstrap ----------

DAY_GUIDE_STUB = """# Day 1 — <<NAME>>

**Goal for the day:** {{first feature/iteration}}.

> Format and a working example — in emcee/examples/docs/day-1-guide.example.md.
> Numeric commands (`R D T`) and artifact names — in core/task-protocol.md.

## Task 1 — {{name}}

**Affected files:** {{...}}

### Prompt for Claude Code

~~~
{{Exact spec for the developer: contract, requirements, which files, which tests.}}
~~~

### After completion

~~~bash
{{build+test command, saving the log}}
~~~

### Commit

~~~bash
git add {{files}}
git commit -m "{{type}}: {{description}}"
~~~
"""

PROJECT_STATE_STUB = """# PROJECT-STATE — <<NAME>>

**A snapshot of the current state, not a journal.** The architect reads this on entering a day and
overwrites it in place at the end of the day: removes what's resolved, wipes what's stale.
History ("what was done and when") lives in git (`git log`); "why" decisions live in
`docs/adr/`. This holds only what's needed to continue RIGHT NOW. Target ≤ ~1 screen.

Last updated: {{YYYY-MM-DD}}

## Snapshot
- Phase: start.
- Stack/commands — in the regimen entry file (don't duplicate here).

## Frozen scope (QG-NN-05)
<!-- Filled in by the architect when a slice is frozen (core/quality-gates.md §Reachability).
     The section is strictly machine-owned (ADR-017): items «- `SCOPE-ID` — atomic criterion»
     (waiver form: «… — waiver: <reason>»), scope-ids unique across slices, prose notes go
     OUTSIDE the section. Durable evidence = annotation @qg:SCOPE-ID in a CHECKED-IN code/test
     file or qg-manifest.* (a mention in .md prose doesn't count).
     Evidence check: python3 regimen-doctor.py (slice-close done-gate: --qg). -->
- Shipping root(s): {{delivery artifact → entry-point}}
- {{SCOPE-ID and criterion}}

## In progress
- {{first feature}}

## Risks / blockers
- {{...}}

## Open questions
- [ ] {{...}}

## Next day
- {{...}}
"""

# Delegating init: standard-tool commands, not a stored scaffold — the tool's current
# version is always fresher than a baked-in copy (see docs/adr/001-scope-process-overlay.md).
INIT_CMDS = {
    "go": "go mod init <module-path>",
    "python": "uv init   # or: python -m venv .venv && . .venv/bin/activate && pip install -e .",
    "react-nextjs": "npx create-next-app@latest .",
    "rust": "cargo init",
    "node": "npm init -y",
    "svelte": "npx sv create .",
}

# glob patterns for path-scoped activation of stack skills (`paths:` in the skill frontmatter).
# Fire RELIABLY on matching files (unlike the model-decided `description`, ~50%).
# Unknown stack -> no paths (only description remains). See Claude Code docs → skills/memory.
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
        cmd = INIT_CMDS.get(slugify(s), f"# TODO: initialize {s} with that stack's standard tool")
        lines.append(f"  {cmd}")
    return "\n".join(lines) or "  # TODO: initialize the project with the chosen stack's standard tool"


DAY0_GUIDE_STUB = """# Day 0 — initializing project <<NAME>>

**Goal:** turn an empty directory into an assembled application scaffold on which `{{test-command}}`
is green, BEFORE taking on Day 1. The package provides the regimen but does NOT own the toolchain —
init is delegated to standard tools (their current version is always fresher than a baked-in skeleton).

> Run as developer: `1 0 1`. Artifact names and numeric commands — core/task-protocol.md.

## Task 1 — initialize the stack and get a green baseline

### Prompt for Claude Code

~~~
Initialize the project with standard tools for the chosen stack, then write the actual
build/test commands into the regimen entry file in place of {{build-command}}/{{test-command}}. Steps:

<<INIT_COMMANDS>>

Then: add a .gitignore for the stack; create a minimal "hello world" + one passing test,
so a green baseline appears. Make sure the clean build (stack/<stack>.md → "Clean build")
passes with no warnings.
~~~

### After completion

~~~bash
{{build+test command}}   # must be green — this is the baseline Day 1 starts from
~~~

### Commit

~~~bash
git add -A
git commit -m "chore: initialize project scaffold (Day 0)"
~~~
"""


def safe_copy_file(src: str, dst: str, overlay: bool, skipped: list[str], target: str) -> bool:
    """Copies a file. In overlay mode, does NOT overwrite an existing one — accumulates it in skipped."""
    if overlay and os.path.exists(dst):
        skipped.append(os.path.relpath(dst, target))
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return True


def safe_copy_tree(src_dir: str, dst_dir: str, overlay: bool, skipped: list[str], target: str):
    """Recursively copies a tree, without overwriting existing files in overlay mode."""
    for root, _, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        for fn in files:
            d = os.path.normpath(os.path.join(dst_dir, rel, fn))
            safe_copy_file(os.path.join(root, fn), d, overlay, skipped, target)


def safe_write(path: str, text: str, overlay: bool, skipped: list[str], target: str) -> bool:
    """Writes a generated file. In overlay mode, doesn't overwrite an existing one."""
    if overlay and os.path.exists(path):
        skipped.append(os.path.relpath(path, target))
        return False
    write(path, text)
    return True


def main():
    ap = argparse.ArgumentParser(description="emcee project generator")
    ap.add_argument("--list", action="store_true", help="show available modules and exit")
    ap.add_argument("--name")
    ap.add_argument("--dir", help="new project directory (must not exist or must be empty)")
    ap.add_argument("--backend", default=None, help="backend stack name (or a new name -> generates a skeleton; none)")
    ap.add_argument("--frontend", default=None, help="frontend stack name (or a new name; none)")
    ap.add_argument("--arch", default=None, help="architectures, comma-separated")
    ap.add_argument("--domain", default=None, help="domains, comma-separated")
    ap.add_argument("--testing", choices=list(TESTING), default=None)
    ap.add_argument("--wiring", choices=["yes", "no"], default=None, help="lay down executable runtime wiring")
    ap.add_argument("--harness", choices=["claude-code", "codex"], default=None,
                    help="target runtime: claude-code (default, wiring in .claude/) or codex "
                         "(AGENTS.md + .codex/ from overlays/codex/). Static copy of the git tree.")
    ap.add_argument("--mode", choices=["new", "overlay"], default=None,
                    help="new = kickstart a new project (empty directory + Day-0 init); "
                         "overlay = lay the regimen onto an existing project (without overwriting files)")
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
            print(f"✗ Required in non-interactive mode: {', '.join(missing)}.", file=sys.stderr)
            return 1

    name = a.name or ask("Project name", "My Project")
    target = a.dir or ask("Project directory", f"../{slugify(name)}")
    target = os.path.abspath(target)

    def pick_stack(role, flag):
        if flag is not None:
            return flag
        v = ask(f"{role} stack (from [{', '.join(stacks_av)}], a new name, or none)", "none")
        return v

    backend = pick_stack("Backend", a.backend)
    frontend = pick_stack("Frontend", a.frontend)

    archs = (a.arch.split(",") if a.arch is not None else ask_multi("Architectural patterns:", arch_av))
    archs = [x.strip() for x in archs if x.strip()]
    doms = (a.domain.split(",") if a.domain is not None else ask_multi("Domains:", dom_av))
    doms = [x.strip() for x in doms if x.strip()]
    # Default is test-along (a light solo mode): the package's declared audience is a solo/small
    # team, for which the full BDD pipeline (SA→BA→QA-UAT→QA-E2E) is overhead. BDD is opt-in.
    # (Scope ADR: docs/adr/001-scope-process-overlay.md)
    testing = a.testing or ask(f"Testing philosophy ({'/'.join(TESTING)})", "test-along")
    harness = a.harness or ask("Target runtime (claude-code/codex)", "claude-code")
    if harness not in ("claude-code", "codex"):
        print(f"⚠ unknown runtime '{harness}', using 'claude-code'", file=sys.stderr)
        harness = "claude-code"
    _wlabel = ".claude/" if harness == "claude-code" else ".codex/"
    wiring = (a.wiring or ask(f"Lay down optional {_wlabel} wiring? (yes/no)", "yes")) == "yes"
    # Mode: new = kickstart (empty directory + Day-0 init guide); overlay = lay the regimen onto
    # an existing project, without overwriting anything (see docs/adr/001-scope-process-overlay.md).
    mode = a.mode or ask("Mode (new = new project / overlay = existing)", "new")
    if mode not in ("new", "overlay"):
        print(f"⚠ unknown mode '{mode}', using 'new'", file=sys.stderr)
        mode = "new"
    overlay = mode == "overlay"

    # validate choices
    for x in archs:
        if x not in arch_av:
            print(f"⚠ architecture '{x}' not found, skipping", file=sys.stderr)
    for x in doms:
        if x not in dom_av:
            print(f"⚠ domain '{x}' not found, skipping", file=sys.stderr)
    archs = [x for x in archs if x in arch_av]
    doms = [x for x in doms if x in dom_av]

    # stack classification: normalize the name, match existing ones by slug, dedupe by slug
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
            print(f"⚠ stack '{s}' yields an empty slug — skipping", file=sys.stderr)
            continue
        if sl in seen_slugs:
            print(f"⚠ stack '{s}' (slug '{sl}') duplicates one already chosen — skipping", file=sys.stderr)
            continue
        seen_slugs.add(sl)
        if sl in existing_by_slug:
            existing_stacks.append(existing_by_slug[sl])   # a real package stack
        else:
            new_stacks.append(s)                            # will get a stack/<slug>.md skeleton

    print("\n--- Plan ---")
    print(f"  Project:       {name}")
    print(f"  Mode:          {mode}  ({'kickstart new' if not overlay else 'overlay onto existing, no overwrite'})")
    print(f"  Directory:     {target}")
    print(f"  Stack (have):  {existing_stacks or '—'}")
    print(f"  Stack (new):   {new_stacks or '—'}  (a stack/<name>.md skeleton will be created)")
    print(f"  Architecture:  {archs or '—'}")
    print(f"  Domain:        {doms or '—'}")
    print(f"  Testing:       {testing}")
    print(f"  Runtime:       {harness}")
    print(f"  Wiring:        {('yes' if wiring else 'no')}  ({_wlabel})")
    if a.dry_run:
        print("\n(dry-run — nothing written)")
        return 0

    if os.path.exists(target) and not os.path.isdir(target):
        print(f"\n✗ {target} exists and is not a directory. Stopping.", file=sys.stderr)
        return 1
    # new requires an empty directory; overlay deliberately writes into an existing project (no overwrite).
    if not overlay and os.path.isdir(target) and os.listdir(target):
        print(f"\n✗ {target} exists and is not empty (mode new). For an existing project: --mode overlay.",
              file=sys.stderr)
        return 1

    warns: list[str] = []
    skipped: list[str] = []                      # overlay: files that already existed — left untouched
    created_target = not os.path.isdir(target)
    stack_bullets = existing_stacks + [slugify(s) for s in new_stacks]
    try:
        # 1) core/ + roles/
        safe_copy_tree(os.path.join(PACK, "core"), os.path.join(target, "core"), overlay, skipped, target)
        safe_copy_tree(os.path.join(PACK, "roles"), os.path.join(target, "roles"), overlay, skipped, target)

        # 2) stacks
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

        # 4) Regimen entry — a per-harness native file WITH CONTENT (ADR-012). The shared body
        #    (ENTRY-BODY) is one (in the CLAUDE.md template); the generator renders it to the native
        #    name: claude-code → CLAUDE.md; codex → AGENTS.md (title + codex-delta header + the same
        #    body), and CLAUDE.md is NOT placed in a codex project.
        entry_filled = fill_claude(read(os.path.join(PACK, "CLAUDE.md")), name, stack_bullets, testing, warns)
        if harness == "codex":
            entry_text, entry_name = assemble_codex_entry(entry_filled, warns), "AGENTS.md"
        else:
            entry_text, entry_name = entry_filled, "CLAUDE.md"
        entry_path = os.path.join(target, entry_name)
        if overlay and os.path.exists(entry_path):
            regimen_name = entry_name.replace(".md", ".regimen.md")
            write(os.path.join(target, regimen_name), entry_text)
            warns.append(f"{entry_name} already exists — the regimen was saved as {regimen_name}, merge by hand")
        else:
            write(entry_path, entry_text)

        # 4b) single source of the role map + synchronizer (needed even in prose mode:
        #     the role table in CLAUDE.md is generated from roles.json via sync-roles.py).
        for tool in ("roles.json", "sync-roles.py", "regimen-doctor.py", "_pack_lib.py"):
            src = os.path.join(PACK, tool)
            if os.path.exists(src):
                safe_copy_file(src, os.path.join(target, tool), overlay, skipped, target)

        # 5) Runtime wiring — STATIC COPY of the chosen overlay's git tree (per --harness),
        #    WITHOUT parsing origin: markers and without a manifest (stop condition ADR-009/010/011).
        #    The shared core above is identical for both runtimes; here — only plumbing.
        #    - claude-code: .claude/ (the default runtime's native position = conceptual
        #      overlays/claude-code/; see overlays/README.md → documented mapping).
        #    - codex: the AGENTS.md entry is already assembled in section 4 (ADR-012); here — only
        #      overlays/codex/.codex/ wiring (under --wiring). CLAUDE.md is NOT placed in a codex project.
        skills_dir = ".claude"  # where the generator emits auto-skills for stack/arch/domain
        if harness == "codex":
            skills_dir = ".codex"
            if wiring:
                cx = os.path.join(PACK, "overlays", "codex", ".codex")
                if os.path.isdir(cx):
                    safe_copy_tree(cx, os.path.join(target, ".codex"), overlay, skipped, target)
        else:  # claude-code
            if wiring and os.path.isdir(os.path.join(PACK, ".claude")):
                safe_copy_tree(os.path.join(PACK, ".claude"), os.path.join(target, ".claude"), overlay, skipped, target)

        # 5b) Auto-skills for the chosen modules (part of the runtime wiring). Additive: a skill is a
        #     thin trigger with a description, pointing at the canonical file (no duplication). The
        #     universal core skills (debugging/code-quality/memory/spec-driven) arrived above with the
        #     wiring. Roles, numeric commands and the panel are NOT touched — that's a separate
        #     primitive. SKILL.md format is identical on Claude Code and Codex; only the discovery
        #     directory differs (.claude/skills/ vs .codex/skills/).
        if wiring:
            def emit_skill(skill_name, canonical, desc, summary, paths=None):
                fm = f"---\nname: {skill_name}\ndescription: {desc}\n"
                # paths: — a path-scoped glob trigger. SUPPORTED ONLY BY Claude Code (official docs,
                # SKILL.md frontmatter: "glob patterns that limit when skill is activated"). Codex
                # skill-creator: "name + description — the only fields Codex reads; do not include
                # any other fields" → we don't emit paths: on Codex (an unsupported key, a leak of
                # Claude-isms + risk of the validator rejecting it). Discovery on Codex is by
                # description (C1 of the audit).
                if paths and skills_dir == ".claude":
                    fm += f"paths: {paths}\n"
                fm += "---\n"
                body = (f"{fm}\n{summary}\n\n"
                        f"Full rules are in `{canonical}` (from the project root). Read the whole file.\n")
                safe_write(os.path.join(target, skills_dir, "skills", skill_name, "SKILL.md"),
                           body, overlay, skipped, target)
            for s in stack_bullets:
                emit_skill(s, f"stack/{s}.md",
                           f"Conventions of the {s} stack in this project: structure, error handling, tests, "
                           f"clean build. Use when writing or reviewing {s} code.",
                           f"Rules for working with the {s} stack.",
                           paths=STACK_PATHS.get(s))
            for x in archs:
                emit_skill(x, f"architecture/{x}.md",
                           f"Architectural pattern \"{x}\": module boundaries, dependency direction, "
                           f"antipatterns. Use when designing or reviewing structure "
                           f"that touches this pattern.",
                           f"Architectural pattern \"{x}\".")
            for x in doms:
                emit_skill(x, f"domain/{x}.md",
                           f"Domain rules for \"{x}\": specifics, constraints, compliance. Use "
                           f"when working on features in this domain.",
                           f"Domain \"{x}\".")

        # 6) docs/ bootstrap
        safe_write(os.path.join(target, "docs", "PROJECT-STATE.md"),
                   PROJECT_STATE_STUB.replace("<<NAME>>", name),
                   overlay, skipped, target)
        # Day-0 (delegating init) — only for kickstarting a new project.
        if not overlay:
            day0 = DAY0_GUIDE_STUB.replace("<<NAME>>", name).replace(
                "<<INIT_COMMANDS>>", init_commands_for(stack_bullets))
            write(os.path.join(target, "docs", "day-0-guide.md"), day0)
        safe_write(os.path.join(target, "docs", "day-1-guide.md"),
                   DAY_GUIDE_STUB.replace("<<NAME>>", name), overlay, skipped, target)
        for sub in ("adr", "specs"):
            safe_write(os.path.join(target, "docs", sub, ".gitkeep"), "", overlay, skipped, target)

        # 7) project README — only for a new project (an existing one has its own, don't touch it)
        if not overlay:
            write(os.path.join(target, "README.md"),
                  f"# {name}\n\nGenerated from emcee. Agent rules and commands are in [{entry_name}]({entry_name}).\n")

        # 8) clean up links to unselected modules
        cleaned = neutralize_dead_links(target)
    except Exception as e:
        if created_target:
            shutil.rmtree(target, ignore_errors=True)
        print(f"\n✗ generation error: {e}"
              + (" (partial result removed)" if created_target else
                 " (overlay — partial result left in place, check by hand)"), file=sys.stderr)
        return 1

    # ---------- report ----------
    print("\n✓ Regimen laid onto:" if overlay else "\n✓ Project created:", target)
    if overlay and skipped:
        print(f"\n  ⚠ overlay: {len(skipped)} existing files NOT touched:")
        for rel in sorted(skipped)[:12]:
            print(f"     • {rel}")
        if len(skipped) > 12:
            print(f"     … {len(skipped) - 12} more")
        print("     If you need the fresh package version — diff by hand and merge.")
    print("\nNext:")
    print(f"  1. Fill in the specifics in {entry_name} (architecture, build/test commands, '## Project specifics').")
    if warns:
        print("     ⚠ auto-fill was partial:")
        for w in warns:
            print("       -", w)

    if new_stacks:
        print("\n  2. NEW STACKS (a skeleton was created — you MUST finish filling in the \"Clean build\" section):")
        for s in new_stacks:
            f = f"stack/{slugify(s)}.md"
            print(f"     • {f}")
            print(f"       Prompt for Claude Code:")
            print(f'       "Fill in {f} following the structure of stack/go.md and stack/python.md, but for {s}.')
            print(f'        The \"Clean build\" section is MANDATORY: which commands mean a clean build for {s}')
            print(f'        (compiler/typecheck/linter) — core/quality-gates.md references it by name.')
            print(f'        Remove sections that don\'t apply and the warning block at the top."')

    # remaining placeholders (count_placeholders semantics — same as regimen-doctor's:
    # the generator's "step 3" list and the doctor's 🔴 must not diverge)
    left = []
    for p in md_files(target):
        n = count_placeholders(read(p))
        if n:
            left.append((os.path.relpath(p, target), n))
    if left:
        print("\n  3. Unfilled {{...}} placeholders:")
        for rel, n in sorted(left, key=lambda x: -x[1]):
            print(f"     {n:3}  {rel}")
        print("     List them: grep -rn '{{' . --include='*.md'")

    # links to unselected modules — neutralized automatically
    if cleaned:
        print(f"\n  4. Links to unselected modules were neutralized in {cleaned} file(s) "
              f"([text](dead-path) → text). No dangling links remain.")

    if overlay:
        print(f"\n  5. The regimen was laid alongside your code. Give the actual build/test commands in "
              f"{entry_name} (the project is already initialized). Then describe docs/day-1-guide.md and run: '1 1 1'.")
    else:
        print("\n  5. First, Day 0 (scaffold init): run '1 0 1' per docs/day-0-guide.md — "
              "the agent will initialize the stack with a standard tool and get a green baseline. "
              "Then describe docs/day-1-guide.md and run '1 1 1'.")
    print("\n  6. Before the first real task, run the readiness gate: python3 regimen-doctor.py "
          "(🟢 = the regimen is filled in; 🔴 = fix placeholders/links/commands). Rerun as you make edits.")
    if wiring:
        if harness == "codex":
            print("     .codex/ wiring copied (agent roles + skills). Runtime entry — AGENTS.md "
                  "(Codex auto-reads it). Hooks (opt-in, KL-7-pending): see .codex/hooks.json.example.")
        else:
            print("     .claude/ wiring copied (subagents + /role). Hooks: mv .claude/settings.json.example .claude/settings.json")
    elif harness == "codex":
        print("     Codex prose mode: AGENTS.md (entry) copied, no .codex/ wiring — "
              "roles as prompts (read roles/<role>.md), numeric commands R D T by typed convention.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
