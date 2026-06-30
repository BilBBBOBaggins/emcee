#!/usr/bin/env python3
"""
render-handbook.py — собирает self-contained HTML-справочник пакета из markdown-источников.

Один навигируемый .html (встроенный CSS, сайдбар, внутренние .md-ссылки → якоря разделов).
Источник истины — сами .md; HTML регенерируется, в гит не коммитится (см. .gitignore).

По умолчанию собирает ДВЕ страницы: handbook.html (полный справочник) + quickstart.html
(отдельная онбординг-страница из QUICKSTART.md, кросс-ссылки ведут вглубь handbook.html).

  python3 render-handbook.py                 # -> handbook.html + quickstart.html
  python3 render-handbook.py --quickstart    # только quickstart.html
  python3 render-handbook.py --out path.html # свой путь для справочника
  python3 render-handbook.py --check         # rc=1, если какой-то файл из оглавления отсутствует

Требует python-markdown (`pip install markdown`). Порядок разделов — ORDER ниже.

Диаграмма пайплайна (`docs/pipeline-diagram.svg`) встраивается в обе страницы как data-URI
<img> (см. pipeline_figure ниже). SVG — источник истины. Однастраничный PDF из него
(`docs/pipeline-diagram.pdf`, gitignored) пересобирается headless-браузером, напр.:

  printf '%s' '<!doctype html><style>@page{size:300mm 237mm;margin:0}html,body{margin:0}\
img{width:300mm;height:auto;display:block}</style><img src="pipeline-diagram.svg">' > /tmp/p.html
  cp docs/pipeline-diagram.svg /tmp/ && \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
    --no-pdf-header-footer --print-to-pdf=docs/pipeline-diagram.pdf /tmp/p.html
"""
from __future__ import annotations
import argparse, base64, glob, html, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# Векторная диаграмма пайплайна (источник истины — docs/pipeline-diagram.svg).
# Встраиваем как data-URI <img>: страница остаётся self-contained, а внутренний
# <style> SVG изолирован (рендерится как изображение → не течёт в CSS документа).
DIAGRAM_SVG = os.path.join(BASE, "docs", "pipeline-diagram.svg")


def pipeline_figure() -> str:
    """<figure> с диаграммой пайплайна или '' если файла нет."""
    if not os.path.exists(DIAGRAM_SVG):
        print(f"⚠ нет диаграммы: {DIAGRAM_SVG}", file=sys.stderr)
        return ""
    raw = open(DIAGRAM_SVG, "rb").read()
    b64 = base64.b64encode(raw).decode("ascii")
    return (
        '<figure class="diagram">'
        f'<img alt="Пайплайн emcee: kickoff, онгоинг по дням, прохождение задачи через роли" '
        f'src="data:image/svg+xml;base64,{b64}">'
        '<figcaption>Пайплайн целиком: KICKOFF (один раз) → онгоинг по дням (цикл R D T) → '
        'как одна задача проходит через роли. Источник: '
        '<code>docs/pipeline-diagram.svg</code>.</figcaption>'
        '</figure>'
    )

# Курируемый порядок чтения справочника: (относительный путь, заголовок в сайдбаре).
ORDER = [
    ("README.md", "Обзор пакета"),
    ("QUICKSTART.md", "Быстрый старт"),
    ("core/pipeline.md", "Пайплайн: как работать"),
    ("core/principles.md", "Принципы работы агента"),
    ("core/task-protocol.md", "Протокол задач"),
    ("core/quality-gates.md", "Гейты качества"),
    ("core/constitution.md", "Конституция (non-negotiable)"),
    ("core/code-quality.md", "Качество кода"),
    ("core/debugging.md", "Дебаг"),
    ("core/memory.md", "Память между сессиями"),
    ("core/spec-driven.md", "Spec-driven (C+)"),
    ("core/adversarial-panel.md", "Адверсивная панель"),
    ("core/second-model.md", "Вторая модель (codex)"),
    ("core/portability.md", "Граница переносимости"),
    ("roles/architect.md", "Роль: Архитектор"),
    ("roles/sa.md", "Роль: System Analyst"),
    ("roles/ba.md", "Роль: Business Analyst"),
    ("roles/developer.md", "Роль: Developer"),
    ("roles/reviewer.md", "Роль: Reviewer"),
    ("roles/qa-e2e.md", "Роль: QA E2E"),
    ("roles/qa-uat.md", "Роль: QA UAT"),
    ("roles/debugger.md", "Роль: Debugger"),
    ("roles/devops.md", "Роль: DevOps"),
    ("roles/designer.md", "Роль: Designer (дормант)"),
    ("roles/auditor.md", "Роль: Auditor (дормант)"),
    ("roles/upgrader.md", "Роль: Upgrader (дормант)"),
    (".claude/README.md", "Обвязка .claude/"),
    ("docs/adr/001-scope-process-overlay.md", "ADR-001: Охват"),
    ("docs/adr/002-spec-driven-cplus.md", "ADR-002: Spec-driven C+"),
    ("docs/adr/003-first-km-intake.md", "ADR-003: Первый километр"),
    ("docs/adr/004-second-model-designer.md", "ADR-004: Вторая модель + Designer"),
    ("docs/adr/005-auditor-role.md", "ADR-005: Роль Auditor"),
    ("docs/adr/006-regimen-upgrade.md", "ADR-006: Обновление регламента"),
    ("docs/adr/007-kickoff-pipeline.md", "ADR-007: Kickoff + пайплайн"),
    ("docs/adr/008-project-state-snapshot.md", "ADR-008: PROJECT-STATE — снимок"),
    ("docs/adr/009-portability-boundary.md", "ADR-009: Граница переносимости"),
    ("docs/adr/010-multimodel-core-overlays.md", "ADR-010: Мультимодель — ядро + оверлеи"),
    ("docs/adr/011-process-layer-and-multimodel-build.md", "ADR-011: Process-слой + сборка мультимодели"),
    ("docs/adr/012-entry-file-per-harness.md", "ADR-012: Входной файл per-harness"),
    ("docs/adr/013-feature-discovery-trigger.md", "ADR-013: Триггер feature-discovery"),
    ("docs/adr/014-prompt-canon-consistency-fixes.md", "ADR-014: Фиксы консистентности промпт-канона"),
]


def anchor_for(relpath: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", relpath.lower()).strip("-")


def slugify_unicode(value: str, separator: str = "-") -> str:
    """GitHub-совместимый slug (юникод): lower, убрать пунктуацию (вкл. «—»),
    каждый пробел -> separator (без схлопывания). Так заголовки QUICKSTART.md
    получают id, совпадающие с его внутренними ссылками вида #б--новый-проект."""
    v = value.strip().lower()
    v = re.sub(r"[^\w\s-]", "", v, flags=re.UNICODE)
    return re.sub(r"\s", separator, v)


# basename(.md) -> anchor, чтобы внутренние ссылки вида [..](../core/x.md) вели на раздел справочника
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
    """Внутренние .md-ссылки (по basename) -> якоря разделов справочника."""
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
        print("✗ нужен python-markdown: pip install markdown", file=sys.stderr)
        return 1

    sections, nav = [], []
    for relpath, title in ORDER:
        full = os.path.join(BASE, relpath)
        if not os.path.exists(full):
            print(f"⚠ пропуск (нет файла): {relpath}", file=sys.stderr)
            continue
        md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"])
        body = rewrite_links(md.convert(open(full, encoding="utf-8").read()))
        anc = anchor_for(relpath)
        if relpath == "core/pipeline.md":
            # диаграмма — сразу после заголовка раздела (первого <h1>/<h2>);
            # функция-замена, чтобы не интерпретировать \-эскейпы в figure-HTML
            fig = pipeline_figure()
            body = re.sub(r"(</h[12]>)", lambda m: m.group(1) + "\n" + fig, body, count=1)
        sections.append(f'<section id="{anc}">\n{body}\n</section>')
        nav.append((relpath, anc, title))

    # сайдбар: группируем по верхнему каталогу
    groups: dict[str, list] = {}
    for relpath, anc, title in nav:
        top = relpath.split("/")[0] if "/" in relpath else "Пакет"
        groups.setdefault(top, []).append((anc, title))
    nav_html = ['<div class="top">📘 emcee</div>']
    GROUP_LABEL = {"Пакет": "", "core": "core/ — ядро", "roles": "roles/ — роли",
                   ".claude": "обвязка", "docs": "решения (ADR)"}
    for top, items in groups.items():
        label = GROUP_LABEL.get(top, top)
        if label:
            nav_html.append(f"<h2>{html.escape(label)}</h2>")
        for anc, title in items:
            nav_html.append(f'<a href="#{anc}">{html.escape(title)}</a>')

    doc = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>emcee — справочник</title>
<style>{CSS}</style></head>
<body><div id="layout">
<nav id="side">{''.join(nav_html)}</nav>
<main>{''.join(sections)}</main>
</div></body></html>"""

    open(out_path, "w", encoding="utf-8").write(doc)
    print(f"✓ справочник собран: {out_path}  ({len(nav)} разделов, {len(doc)//1024} KB)")
    return 0


def rewrite_links_standalone(html_text: str) -> str:
    """Для отдельной страницы: внутренние #-якоря оставить (работают внутри страницы);
    кросс-файловые .md-ссылки -> вглубь handbook.html#<раздел> (если такой раздел есть)."""
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
        print("✗ нужен python-markdown: pip install markdown", file=sys.stderr)
        return 1
    src = os.path.join(BASE, "QUICKSTART.md")
    if not os.path.exists(src):
        print("✗ нет QUICKSTART.md", file=sys.stderr)
        return 1
    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"],
                           extension_configs={"toc": {"slugify": slugify_unicode}})
    body = rewrite_links_standalone(md.convert(open(src, encoding="utf-8").read()))
    doc = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>emcee — quickstart</title>
<style>{CSS}</style></head>
<body><main>
<p style="margin:0 0 8px"><a href="handbook.html">📘 Полный справочник</a></p>
{pipeline_figure()}
{body}
</main></body></html>"""
    open(out_path, "w", encoding="utf-8").write(doc)
    print(f"✓ quickstart собран: {out_path}  ({len(doc)//1024} KB)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="HTML-справочник пакета из markdown")
    ap.add_argument("--out", default=os.path.join(BASE, "handbook.html"))
    ap.add_argument("--check", action="store_true", help="rc=1 если файл из ORDER отсутствует")
    ap.add_argument("--quickstart", action="store_true", help="собрать только quickstart.html")
    a = ap.parse_args()

    if a.check:
        missing = [p for p, _ in ORDER if not os.path.exists(os.path.join(BASE, p))]
        if missing:
            print(f"✗ отсутствуют файлы оглавления: {missing}", file=sys.stderr)
            return 1
        # обратный tripwire: каждый ADR на диске обязан быть в ORDER (иначе тихо выпадет из справочника)
        in_order = {p for p, _ in ORDER}
        orphan_adr = sorted(
            os.path.relpath(p, BASE)
            for p in glob.glob(os.path.join(BASE, "docs/adr/*.md"))
            if os.path.relpath(p, BASE) not in in_order
        )
        if orphan_adr:
            print(f"✗ ADR на диске, но вне ORDER (выпадут из справочника): {orphan_adr}", file=sys.stderr)
            return 1
        print(f"✓ все {len(ORDER)} файлов оглавления на месте; ADR-каталог покрыт")
        return 0

    qs_out = os.path.join(os.path.dirname(a.out) or BASE, "quickstart.html")
    if a.quickstart:
        return build_quickstart(qs_out)
    # дефолт: обе страницы (справочник + отдельный quickstart)
    rc = build(a.out)
    return rc or build_quickstart(qs_out)


if __name__ == "__main__":
    raise SystemExit(main())
