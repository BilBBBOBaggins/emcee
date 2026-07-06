#!/usr/bin/env python3
"""
render-handbook.py — assembles a self-contained HTML handbook for the package from markdown sources.

One navigable .html (inline CSS, a sidebar, internal .md links → section anchors).
The .md files themselves are the source of truth; the HTML is regenerated, not committed to git (see .gitignore).

By default assembles TWO pages: handbook.html (the full handbook) + quickstart.html
(a separate onboarding page from QUICKSTART.md, cross-links go deeper into handbook.html).

  python3 render-handbook.py                 # -> handbook.html + quickstart.html
  python3 render-handbook.py --quickstart    # only quickstart.html
  python3 render-handbook.py --out path.html # custom path for the handbook
  python3 render-handbook.py --check         # rc=1 if some file from the table of contents is missing

Requires python-markdown (`pip install markdown`). Section order — ORDER below.

The pipeline diagram (`docs/pipeline-diagram.svg`) is embedded in both pages as a data-URI
<img> (see pipeline_figure below). The SVG is the source of truth. A single-page PDF from it
(`docs/pipeline-diagram.pdf`, gitignored) is rebuilt with a headless browser, e.g.:

  printf '%s' '<!doctype html><style>@page{size:300mm 237mm;margin:0}html,body{margin:0}\
img{width:300mm;height:auto;display:block}</style><img src="pipeline-diagram.svg">' > /tmp/p.html
  cp docs/pipeline-diagram.svg /tmp/ && \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
    --no-pdf-header-footer --print-to-pdf=docs/pipeline-diagram.pdf /tmp/p.html
"""
from __future__ import annotations
import argparse, base64, glob, html, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# Vector pipeline diagram (source of truth — docs/pipeline-diagram.svg).
# Embedded as a data-URI <img>: the page stays self-contained, and the SVG's internal
# <style> is isolated (rendered as an image → doesn't leak into the document's CSS).
DIAGRAM_SVG = os.path.join(BASE, "docs", "pipeline-diagram.svg")


def pipeline_figure() -> str:
    """<figure> with the pipeline diagram, or '' if the file is missing."""
    if not os.path.exists(DIAGRAM_SVG):
        print(f"⚠ no diagram: {DIAGRAM_SVG}", file=sys.stderr)
        return ""
    raw = open(DIAGRAM_SVG, "rb").read()
    b64 = base64.b64encode(raw).decode("ascii")
    return (
        '<figure class="diagram">'
        f'<img alt="emcee pipeline: kickoff, ongoing by day, a task passing through the roles" '
        f'src="data:image/svg+xml;base64,{b64}">'
        '<figcaption>The whole pipeline: KICKOFF (once) → ongoing by day (the R D T cycle) → '
        'how a single task passes through the roles. Source: '
        '<code>docs/pipeline-diagram.svg</code>.</figcaption>'
        '</figure>'
    )

# Curated reading order for the handbook: (relative path, sidebar title).
ORDER = [
    ("README.md", "Package overview"),
    ("QUICKSTART.md", "Quickstart"),
    ("core/pipeline.md", "Pipeline: how to work"),
    ("core/principles.md", "Agent working principles"),
    ("core/task-protocol.md", "Task protocol"),
    ("core/quality-gates.md", "Quality gates"),
    ("core/constitution.md", "Constitution (non-negotiable)"),
    ("core/code-quality.md", "Code quality"),
    ("core/debugging.md", "Debugging"),
    ("core/memory.md", "Memory across sessions"),
    ("core/spec-driven.md", "Spec-driven (C+)"),
    ("core/adversarial-panel.md", "Adversarial panel"),
    ("core/second-model.md", "Second model (codex)"),
    ("core/portability.md", "Portability boundary"),
    ("roles/architect.md", "Role: Architect"),
    ("roles/sa.md", "Role: System Analyst"),
    ("roles/ba.md", "Role: Business Analyst"),
    ("roles/developer.md", "Role: Developer"),
    ("roles/reviewer.md", "Role: Reviewer"),
    ("roles/qa-e2e.md", "Role: QA E2E"),
    ("roles/qa-uat.md", "Role: QA UAT"),
    ("roles/debugger.md", "Role: Debugger"),
    ("roles/devops.md", "Role: DevOps"),
    ("roles/designer.md", "Role: Designer (dormant)"),
    ("roles/auditor.md", "Role: Auditor (dormant)"),
    ("roles/upgrader.md", "Role: Upgrader (dormant)"),
    (".claude/README.md", ".claude/ wiring"),
    ("docs/adr/001-scope-process-overlay.md", "ADR-001: Scope"),
    ("docs/adr/002-spec-driven-cplus.md", "ADR-002: Spec-driven C+"),
    ("docs/adr/003-first-km-intake.md", "ADR-003: First kilometer"),
    ("docs/adr/004-second-model-designer.md", "ADR-004: Second model + Designer"),
    ("docs/adr/005-auditor-role.md", "ADR-005: Auditor role"),
    ("docs/adr/006-regimen-upgrade.md", "ADR-006: Regimen upgrade"),
    ("docs/adr/007-kickoff-pipeline.md", "ADR-007: Kickoff + pipeline"),
    ("docs/adr/008-project-state-snapshot.md", "ADR-008: PROJECT-STATE — a snapshot"),
    ("docs/adr/009-portability-boundary.md", "ADR-009: Portability boundary"),
    ("docs/adr/010-multimodel-core-overlays.md", "ADR-010: Multi-model — core + overlays"),
    ("docs/adr/011-process-layer-and-multimodel-build.md", "ADR-011: Process layer + multi-model build"),
    ("docs/adr/012-entry-file-per-harness.md", "ADR-012: Per-harness entry file"),
    ("docs/adr/013-feature-discovery-trigger.md", "ADR-013: Feature-discovery trigger"),
    ("docs/adr/014-prompt-canon-consistency-fixes.md", "ADR-014: Prompt-canon consistency fixes"),
    ("docs/adr/015-assembled-reachability-gate.md", "ADR-015: Assembled feature reachability (QG-NN-05)"),
    ("docs/adr/016-panel-second-model-mandatory-when-available.md",
     "ADR-016: Second model for the panel — mandatory when available"),
    ("docs/adr/017-machine-checked-plan-invariants.md",
     "ADR-017: Machine-checked plan invariants (hardened --qg gate)"),
]


def anchor_for(relpath: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", relpath.lower()).strip("-")


def slugify_unicode(value: str, separator: str = "-") -> str:
    """GitHub-compatible slug (unicode): lowercase, strip punctuation (incl. "—"),
    each space -> separator (no collapsing). This way QUICKSTART.md headings
    get ids that match its internal links like #b--new-project."""
    v = value.strip().lower()
    v = re.sub(r"[^\w\s-]", "", v, flags=re.UNICODE)
    return re.sub(r"\s", separator, v)


# basename(.md) -> anchor, so internal links like [..](../core/x.md) lead to the handbook section
BASENAME_TO_ANCHOR = {os.path.basename(p): anchor_for(p) for p, _ in ORDER}

CSS = """
:root { --fg:#1b1b1f; --muted:#5b5b66; --bg:#fff; --side:#f6f7f9; --line:#e2e4e9;
        --accent:#2f6feb; --code-bg:#f3f4f6; }
* { box-sizing: border-box; }
body { margin:0; font:16px/1.62 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
       color:var(--fg); background:var(--bg); }
#layout { display:flex; align-items:flex-start; }
#side { width:290px; min-width:290px; height:100vh; position:sticky; top:0; overflow:auto;
        background:var(--side); border-right:1px solid var(--line); padding:20px 16px; }
#side h2 { font-size:13px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:18px 0 8px; }
#side a { display:block; padding:4px 8px; color:var(--fg); text-decoration:none; border-radius:6px; font-size:14px; }
#side a:hover { background:#e8eaee; }
#side .top { font-weight:700; font-size:16px; margin-bottom:4px; }
main { max-width:860px; padding:40px 48px 120px; margin:0 auto; }
section { padding-top:24px; border-top:1px solid var(--line); margin-top:40px; }
section:first-of-type { border-top:none; margin-top:0; }
h1 { font-size:30px; line-height:1.2; margin:.2em 0 .6em; }
h2 { font-size:23px; margin:1.4em 0 .5em; padding-bottom:.2em; border-bottom:1px solid var(--line); }
h3 { font-size:18px; margin:1.2em 0 .4em; }
a { color:var(--accent); }
code { background:var(--code-bg); padding:.12em .35em; border-radius:4px; font-size:.88em;
       font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
pre { background:var(--code-bg); padding:14px 16px; border-radius:8px; overflow:auto; border:1px solid var(--line); }
pre code { background:none; padding:0; font-size:13px; line-height:1.5; }
blockquote { margin:1em 0; padding:.4em 1em; border-left:4px solid var(--accent); background:#f7f9ff; color:#333; }
table { border-collapse:collapse; width:100%; margin:1em 0; font-size:14px; display:block; overflow:auto; }
th,td { border:1px solid var(--line); padding:6px 10px; text-align:left; vertical-align:top; }
th { background:var(--side); }
hr { border:none; border-top:1px solid var(--line); margin:2em 0; }
.tag { display:inline-block; background:#eef1ff; color:#2f4fc0; border:1px solid #d6ddff;
       border-radius:5px; padding:0 6px; font-size:12px; }
figure.diagram { margin:1.6em 0; padding:14px; background:#fff; border:1px solid var(--line);
       border-radius:10px; overflow:auto; }
figure.diagram img { display:block; width:100%; height:auto; }
figure.diagram figcaption { margin-top:10px; font-size:13px; color:var(--muted); text-align:center; }
@media print { #side{display:none;} main{max-width:none;padding:0;} section{break-inside:avoid;}
       figure.diagram{break-inside:avoid;} }
"""


def rewrite_links(html_text: str) -> str:
    """Internal .md links (by basename) -> handbook section anchors."""
    def repl(m):
        href = m.group(1)
        if href.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        target = href.split("#")[0]
        base = os.path.basename(target)
        if base in BASENAME_TO_ANCHOR:
            return f'href="#{BASENAME_TO_ANCHOR[base]}"'
        return m.group(0)
    return re.sub(r'href="([^"]+)"', repl, html_text)


def build(out_path: str) -> int:
    try:
        import markdown
    except ImportError:
        print("✗ needs python-markdown: pip install markdown", file=sys.stderr)
        return 1

    sections, nav = [], []
    for relpath, title in ORDER:
        full = os.path.join(BASE, relpath)
        if not os.path.exists(full):
            print(f"⚠ skipping (no file): {relpath}", file=sys.stderr)
            continue
        md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"])
        body = rewrite_links(md.convert(open(full, encoding="utf-8").read()))
        anc = anchor_for(relpath)
        if relpath == "core/pipeline.md":
            # the diagram goes right after the section heading (the first <h1>/<h2>);
            # a replacement function so \-escapes in the figure HTML aren't interpreted
            fig = pipeline_figure()
            body = re.sub(r"(</h[12]>)", lambda m: m.group(1) + "\n" + fig, body, count=1)
        sections.append(f'<section id="{anc}">\n{body}\n</section>')
        nav.append((relpath, anc, title))

    # sidebar: group by top-level directory
    groups: dict[str, list] = {}
    for relpath, anc, title in nav:
        top = relpath.split("/")[0] if "/" in relpath else "Package"
        groups.setdefault(top, []).append((anc, title))
    nav_html = ['<div class="top">📘 emcee</div>']
    GROUP_LABEL = {"Package": "", "core": "core/ — the core", "roles": "roles/ — roles",
                   ".claude": "wiring", "docs": "decisions (ADR)"}
    for top, items in groups.items():
        label = GROUP_LABEL.get(top, top)
        if label:
            nav_html.append(f"<h2>{html.escape(label)}</h2>")
        for anc, title in items:
            nav_html.append(f'<a href="#{anc}">{html.escape(title)}</a>')

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>emcee — handbook</title>
<style>{CSS}</style></head>
<body><div id="layout">
<nav id="side">{''.join(nav_html)}</nav>
<main>{''.join(sections)}</main>
</div></body></html>"""

    open(out_path, "w", encoding="utf-8").write(doc)
    print(f"✓ handbook assembled: {out_path}  ({len(nav)} sections, {len(doc)//1024} KB)")
    return 0


def rewrite_links_standalone(html_text: str) -> str:
    """For the standalone page: keep internal #-anchors (work within the page);
    cross-file .md links -> deeper into handbook.html#<section> (if such a section exists)."""
    def repl(m):
        href = m.group(1)
        if href.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        anchor = href.split("#")[-1] if href.startswith("#") else ""
        base = os.path.basename(href.split("#")[0])
        if base in BASENAME_TO_ANCHOR:
            return f'href="handbook.html#{BASENAME_TO_ANCHOR[base]}"'
        return m.group(0)
    return re.sub(r'href="([^"]+)"', repl, html_text)


def build_quickstart(out_path: str) -> int:
    try:
        import markdown
    except ImportError:
        print("✗ needs python-markdown: pip install markdown", file=sys.stderr)
        return 1
    src = os.path.join(BASE, "QUICKSTART.md")
    if not os.path.exists(src):
        print("✗ no QUICKSTART.md", file=sys.stderr)
        return 1
    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"],
                           extension_configs={"toc": {"slugify": slugify_unicode}})
    body = rewrite_links_standalone(md.convert(open(src, encoding="utf-8").read()))
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>emcee — quickstart</title>
<style>{CSS}</style></head>
<body><main>
<p style="margin:0 0 8px"><a href="handbook.html">📘 Full handbook</a></p>
{pipeline_figure()}
{body}
</main></body></html>"""
    open(out_path, "w", encoding="utf-8").write(doc)
    print(f"✓ quickstart assembled: {out_path}  ({len(doc)//1024} KB)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="HTML handbook for the package, from markdown")
    ap.add_argument("--out", default=os.path.join(BASE, "handbook.html"))
    ap.add_argument("--check", action="store_true", help="rc=1 if a file from ORDER is missing")
    ap.add_argument("--quickstart", action="store_true", help="build only quickstart.html")
    a = ap.parse_args()

    if a.check:
        missing = [p for p, _ in ORDER if not os.path.exists(os.path.join(BASE, p))]
        if missing:
            print(f"✗ missing table-of-contents files: {missing}", file=sys.stderr)
            return 1
        # reverse tripwire: every ADR on disk must be in ORDER (otherwise it silently drops out of the handbook)
        in_order = {p for p, _ in ORDER}
        orphan_adr = sorted(
            os.path.relpath(p, BASE)
            for p in glob.glob(os.path.join(BASE, "docs/adr/*.md"))
            if os.path.relpath(p, BASE) not in in_order
        )
        if orphan_adr:
            print(f"✗ ADR on disk but outside ORDER (will drop out of the handbook): {orphan_adr}", file=sys.stderr)
            return 1
        print(f"✓ all {len(ORDER)} table-of-contents files are in place; the ADR directory is covered")
        return 0

    qs_out = os.path.join(os.path.dirname(a.out) or BASE, "quickstart.html")
    if a.quickstart:
        return build_quickstart(qs_out)
    # default: both pages (handbook + separate quickstart)
    rc = build(a.out)
    return rc or build_quickstart(qs_out)


if __name__ == "__main__":
    raise SystemExit(main())
