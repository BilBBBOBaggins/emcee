#!/usr/bin/env python3
"""
selftest.py — самотест пакета emcee.

Генерит матрицу проектов через new-project.py во временный каталог и проверяет
инварианты сгенерированного проекта + здоровье самого пакета. Ловит регрессии,
которые уже случались (висячие ссылки после прунинга; схлопывание {{...}} -> {...}).

Запуск:  ./selftest.py      (exit 0 = всё зелёное, иначе 1)
"""
from __future__ import annotations
import glob, json, os, re, subprocess, sys, tempfile, shutil

PACK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PACK)
from _pack_lib import md_files, iter_links  # общий обход .md + парсинг ссылок (находка #4)

GEN = os.path.join(PACK, "new-project.py")
results: list[tuple[bool, str]] = []


def check(cond: bool, msg: str):
    results.append((bool(cond), msg))


def dangling(root: str) -> list[str]:
    out = []
    for p in md_files(root):
        d = os.path.dirname(p)
        for _ln, _m, t in iter_links(open(p, encoding="utf-8").read()):
            if t is None:
                continue
            if not os.path.exists(os.path.normpath(os.path.join(d, t))):
                out.append(f"{os.path.relpath(p, root)} -> {t}")
    return out


def gen(target: str, **flags) -> subprocess.CompletedProcess:
    args = [sys.executable, GEN, "--dir", target]
    for k, v in flags.items():
        args += [f"--{k}", str(v)]
    return subprocess.run(args, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def validate_project(tag: str, root: str, *, name: str, wiring: bool,
                     stacks: list[str], new_stacks: list[str], variants_expected: int):
    # базовое
    claude = os.path.join(root, "CLAUDE.md")
    check(os.path.exists(claude), f"[{tag}] CLAUDE.md существует")
    txt = open(claude, encoding="utf-8").read() if os.path.exists(claude) else ""
    check(name in txt, f"[{tag}] имя проекта подставлено в CLAUDE.md")
    check("{{PROJECT_NAME}}" not in txt, f"[{tag}] {{{{PROJECT_NAME}}}} не остался")
    check(txt.count("### Вариант") == variants_expected,
          f"[{tag}] testing-вариантов в CLAUDE.md = {variants_expected} (факт {txt.count('### Вариант')})")

    # КЛЮЧЕВОЙ инвариант: ноль висячих ссылок
    dl = dangling(root)
    check(not dl, f"[{tag}] висячих ссылок нет" + (f" (найдено {len(dl)}: {dl[:3]})" if dl else ""))

    # docs/ + регрессия {{...}} -> {...}
    for rel in ("docs/day-1-guide.md", "docs/PROJECT-STATE.md"):
        p = os.path.join(root, rel)
        check(os.path.exists(p), f"[{tag}] {rel} существует")
        if os.path.exists(p):
            b = open(p, encoding="utf-8").read()
            check("{{" in b, f"[{tag}] {rel} сохранил {{{{...}}}} (нет схлопывания .format)")
            check("<<NAME>>" not in b and "<<STACKS>>" not in b, f"[{tag}] {rel} без утёкших сентинелов")

    # стеки
    for s in stacks:
        check(os.path.exists(os.path.join(root, "stack", f"{s}.md")), f"[{tag}] stack/{s}.md есть")
    for s in new_stacks:
        sp = os.path.join(root, "stack", f"{s}.md")
        check(os.path.exists(sp), f"[{tag}] скелет stack/{s}.md создан")
        if os.path.exists(sp):
            sk = open(sp, encoding="utf-8").read()
            check("Чистая сборка" in sk, f"[{tag}] скелет {s} содержит раздел «Чистая сборка»")
            check("{{STACK_NAME}}" not in sk and "{{STACK_SLUG}}" not in sk,
                  f"[{tag}] скелет {s}: плейсхолдеры стека подставлены")

    # обвязка
    adir = os.path.join(root, ".claude")
    if wiring:
        check(os.path.isdir(adir), f"[{tag}] .claude/ скопирован")
        for af in (os.listdir(os.path.join(adir, "agents")) if os.path.isdir(os.path.join(adir, "agents")) else []):
            fm = open(os.path.join(adir, "agents", af), encoding="utf-8").read()[:400]
            check(all(k in fm for k in ("name:", "description:", "tools:")),
                  f"[{tag}] agent {af}: frontmatter полный")
        sj = os.path.join(adir, "settings.json.example")
        if os.path.exists(sj):
            data = None
            try:
                data = json.load(open(sj))
            except Exception:
                pass
            check(data is not None, f"[{tag}] settings.json.example — валидный JSON")
            # строгая схема Claude Code отвергает неизвестные/underscore ключи -> guard
            if isinstance(data, dict):
                check(all(not k.startswith("_") for k in data),
                      f"[{tag}] settings.json без нестандартных ключей (переименование не сломает)")
                check(set(data).issubset({"hooks", "permissions", "env", "model", "includeCoAuthoredBy",
                                          "cleanupPeriodDays", "apiKeyHelper", "statusLine"}),
                      f"[{tag}] settings.json только известные top-level ключи: {sorted(set(data))}")
        # авто-скиллы: универсальные ядра + по одному на выбранный стек, указывают на канон
        sdir = os.path.join(adir, "skills")
        for nm in ("debugging", "code-quality", "memory", "spec-driven"):
            check(os.path.exists(os.path.join(sdir, nm, "SKILL.md")),
                  f"[{tag}] универсальный skill {nm}/SKILL.md на месте")
        for s in (stacks + new_stacks):
            sp = os.path.join(sdir, s, "SKILL.md")
            check(os.path.exists(sp), f"[{tag}] skill стека {s}/SKILL.md создан")
            if os.path.exists(sp):
                b = open(sp, encoding="utf-8").read()
                check(b.startswith("---") and "\nname:" in b and "\ndescription:" in b,
                      f"[{tag}] skill {s}: валидный frontmatter (name+description)")
                check(os.path.exists(os.path.join(root, "stack", f"{s}.md")),
                      f"[{tag}] skill {s} указывает на существующий stack/{s}.md")
                # известные стеки несут path-scoped glob (надёжная активация) + description-фолбэк
                if s in ("go", "python", "react-nextjs"):
                    check("\npaths:" in b, f"[{tag}] skill {s} несёт paths:-glob (path-scoped активация)")
    else:
        check(not os.path.isdir(adir), f"[{tag}] .claude/ отсутствует (wiring=no)")

    # единый источник карты ролей: roles.json + sync-roles.py скопированы и таблицы в синхроне
    check(os.path.exists(os.path.join(root, "roles.json")), f"[{tag}] roles.json скопирован")
    syncp = os.path.join(root, "sync-roles.py")
    check(os.path.exists(syncp), f"[{tag}] sync-roles.py скопирован")
    if os.path.exists(syncp):
        cp = subprocess.run([sys.executable, syncp, "--check"], cwd=root,
                            capture_output=True, text=True)
        check(cp.returncode == 0, f"[{tag}] sync-roles --check зелёный (таблицы ролей в синхроне)")

    # гейт готовности: regimen-doctor.py скопирован и запускается (на свежем проекте с
    # незаполненными {{...}} ожидаем rc=1 = «есть 🔴», не падение)
    docp = os.path.join(root, "regimen-doctor.py")
    check(os.path.exists(docp), f"[{tag}] regimen-doctor.py скопирован")
    if os.path.exists(docp):
        dr = subprocess.run([sys.executable, docp, "--dir", root], cwd=root,
                            capture_output=True, text=True)
        check(dr.returncode in (0, 1) and "regimen-doctor" in dr.stdout,
              f"[{tag}] regimen-doctor запускается и отчитывается (rc={dr.returncode})")
        check("Traceback" not in dr.stderr, f"[{tag}] regimen-doctor без traceback")
        # P5: harness-aware баннер обвязки + состояние (не наличие) хуков на claude-проекте
        check("обвязка рантайма:" in dr.stdout, f"[{tag}] regimen-doctor печатает обвязку рантайма")
        if wiring:
            check("claude-code" in dr.stdout, f"[{tag}] doctor детектит claude-code обвязку")
            check("хуки НЕ включены" in dr.stdout or "хуки-гейты АКТИВНЫ" in dr.stdout,
                  f"[{tag}] doctor рапортует СОСТОЯНИЕ хуков (активны/дормантны), не наличие")


def main() -> int:
    base = tempfile.mkdtemp(prefix="ct-selftest-")
    try:
        # ---- сценарии генерации ----
        s = os.path.join(base, "full")
        r = gen(s, name="Full Stack", backend="go", frontend="react-nextjs",
                arch="modular-monolith,multi-tenant", domain="b2b-saas", testing="bdd", wiring="yes")
        check(r.returncode == 0, "[full] генератор отработал (rc=0)")
        validate_project("full", s, name="Full Stack", wiring=True,
                         stacks=["go", "react-nextjs"], new_stacks=[], variants_expected=1)
        # arch/domain тоже эмитят скиллы, указывающие на канон
        for nm, canon in (("modular-monolith", "architecture"), ("multi-tenant", "architecture"),
                          ("b2b-saas", "domain")):
            sp = os.path.join(s, ".claude", "skills", nm, "SKILL.md")
            check(os.path.exists(sp), f"[skills] {nm}/SKILL.md создан")
            check(os.path.exists(os.path.join(s, canon, f"{nm}.md")),
                  f"[skills] {nm} указывает на существующий {canon}/{nm}.md")

        s = os.path.join(base, "py")
        r = gen(s, name="Py Service", backend="python", frontend="none",
                arch="modular-monolith", domain="regulated", testing="test-along", wiring="no")
        check(r.returncode == 0, "[py] генератор отработал (rc=0)")
        validate_project("py", s, name="Py Service", wiring=False,
                         stacks=["python"], new_stacks=[], variants_expected=1)

        s = os.path.join(base, "newstack")
        r = gen(s, name="Edge Proxy", backend="rust", frontend="none",
                arch="event-driven", domain="none", testing="tdd", wiring="no")
        check(r.returncode == 0, "[newstack] генератор отработал (rc=0)")
        validate_project("newstack", s, name="Edge Proxy", wiring=False,
                         stacks=[], new_stacks=["rust"], variants_expected=1)

        s = os.path.join(base, "minimal")
        r = gen(s, name="Bare", backend="none", frontend="none",
                arch="", domain="", testing="test-along", wiring="no")
        check(r.returncode == 0, "[minimal] генератор отработал (rc=0)")
        validate_project("minimal", s, name="Bare", wiring=False,
                         stacks=[], new_stacks=[], variants_expected=1)

        # ---- мультимодельность: --harness codex кладёт overlays/codex, НЕ .claude ----
        cx = os.path.join(base, "codex")
        r = gen(cx, name="Codex Svc", backend="go", frontend="none",
                arch="modular-monolith", domain="none", testing="test-along",
                wiring="yes", harness="codex")
        check(r.returncode == 0, "[codex] генератор --harness codex (rc=0)")
        check(os.path.exists(os.path.join(cx, "AGENTS.md")), "[codex] AGENTS.md (вход рантайма) на месте")
        check(not os.path.isdir(os.path.join(cx, ".claude")), "[codex] .claude/ НЕ скопирован для codex")
        # ADR-012: codex-проект НЕ несёт ФАЙЛ CLAUDE.md (вход = per-harness нативный AGENTS.md)
        check(not os.path.exists(os.path.join(cx, "CLAUDE.md")), "[codex] CLAUDE.md ФАЙЛА нет (ADR-012)")
        check(os.path.exists(os.path.join(cx, "core", "principles.md")), "[codex] нейтральное ядро (core/) на месте")
        # ADR-012: AGENTS.md несёт КОНТЕНТ (codex-delta-хедер + общее тело), не указатель «читай CLAUDE.md»
        agtxt = open(os.path.join(cx, "AGENTS.md"), encoding="utf-8").read() if os.path.exists(os.path.join(cx, "AGENTS.md")) else ""
        check("Что на Codex иначе" in agtxt, "[codex] AGENTS.md несёт codex-delta-хедер")
        check("## Стек" in agtxt and "## Testing philosophy" in agtxt,
              "[codex] AGENTS.md несёт общее тело (Стек/Testing), не указатель")
        check("[roles/reviewer.md]" in agtxt, "[codex] AGENTS.md несёт нейтральную таблицу ролей (roles/*.md)")
        check("Codex Svc" in agtxt, "[codex] AGENTS.md заполнен именем проекта (вход с контентом)")
        # каждая роль roles.json -> .codex/agents/<agent>.toml существует (полнота маппинга ролей)
        cxroles = json.load(open(os.path.join(cx, "roles.json")))["roles"] if os.path.exists(os.path.join(cx, "roles.json")) else []
        cxadir = os.path.join(cx, ".codex", "agents")
        for rr in cxroles:
            check(os.path.exists(os.path.join(cxadir, f"{rr['agent']}.toml")),
                  f"[codex] роль {rr['agent']} -> .codex/agents/{rr['agent']}.toml")
        # sandbox_mode + developer_instructions валидны у ВСЕХ .toml (вкл. dispatch-агентов вне roles.json:
        # architect/auditor/red-team/blue-team/arbiter) — паритет с claude-стороной (она итерирует listdir агентов)
        for fn in (sorted(os.listdir(cxadir)) if os.path.isdir(cxadir) else []):
            if not fn.endswith(".toml"):
                continue
            tb = open(os.path.join(cxadir, fn), encoding="utf-8").read()
            check(re.search(r'sandbox_mode\s*=\s*"(read-only|workspace-write)"', tb) is not None,
                  f"[codex] {fn}: валидный sandbox_mode")
            check('developer_instructions' in tb and len(tb.split('developer_instructions', 1)[1]) > 40,
                  f"[codex] {fn}: непустой developer_instructions")
        # скиллы стека/арх эмитятся в .codex/skills/ (не .claude/skills/)
        check(os.path.exists(os.path.join(cx, ".codex", "skills", "go", "SKILL.md")),
              "[codex] skill стека эмитится в .codex/skills/")
        check(os.path.exists(os.path.join(cx, ".codex", "skills", "debugging", "SKILL.md")),
              "[codex] универсальный skill в .codex/skills/")
        # C1 аудита: paths:-frontmatter — Claude-only (Codex skill-creator: только name+description,
        # «do not include any other fields»). Ни один codex-скилл не должен нести paths:.
        cxskills = glob.glob(os.path.join(cx, ".codex", "skills", "**", "SKILL.md"), recursive=True)
        paths_leak = [os.path.relpath(p, cx) for p in cxskills
                      if any(l.startswith("paths:") for l in open(p, encoding="utf-8"))]
        check(not paths_leak, "[codex] ноль paths: во frontmatter codex-скиллов (Claude-only ключ)" +
              (f" — {paths_leak}" if paths_leak else ""))
        # sync-roles в codex-проекте зелёный (AGENTS.md в синхроне)
        if os.path.exists(os.path.join(cx, "sync-roles.py")):
            cpc = subprocess.run([sys.executable, "sync-roles.py", "--check"], cwd=cx,
                                 capture_output=True, text=True)
            check(cpc.returncode == 0, "[codex] sync-roles --check зелёный в codex-проекте")
        check(not dangling(cx), "[codex] висячих ссылок нет в codex-проекте")
        # ADR-012: голый/ссылочный «CLAUDE.md» в codex-проекте только по allowlist; ноль (a)/self-ref.
        # neutralize_dead_links голый текст НЕ ловит — проверяем строкой. Allowlist (b honest-delta):
        # любая строка, явно называющая «AGENTS.md» или «Claude Code» (per-harness honest-delta).
        # (c)-метка «Промпт для Claude Code» содержит «Claude Code», не «CLAUDE.md» → не матчится.
        # (b)-homes core/memory.md + core/portability.md насыщены ЛЕГИТИМНЫМИ CLAUDE.md (Claude
        # memory/portability факты), которые построчный allowlist не пропустит. НЕ амнистируем их
        # целиком (это слепое пятно к новой (a)-утечке — B2 аудита): вместо whole-file exempt —
        # ТРИВАЙР по числу вхождений. Новый (a)-leak в эти файлы поднимет счётчик выше baseline →
        # тест падает, требует осознанной сверки и явного bump (как N-overlay debt tripwire).
        B_HOMES = {os.path.join("core", "memory.md"): 9, os.path.join("core", "portability.md"): 8}
        leak_claude, bhome_over = [], []
        for p in md_files(cx):
            rel = os.path.relpath(p, cx)
            text = open(p, encoding="utf-8").read()
            if rel in B_HOMES:
                n = text.count("CLAUDE.md")
                if n > B_HOMES[rel]:
                    bhome_over.append(f"{rel}: {n} > baseline {B_HOMES[rel]}")
                continue
            for ln, line in enumerate(text.splitlines(), 1):
                if "CLAUDE.md" not in line:
                    continue
                if "AGENTS.md" in line or "Claude Code" in line or "Claude-Code" in line:
                    continue  # honest per-harness delta — допустимо
                leak_claude.append(f"{rel}:{ln}")
        check(not leak_claude,
              "[codex] ноль неуместного CLAUDE.md в codex-проекте (a/self-ref)" +
              (f" — {leak_claude[:6]}" if leak_claude else ""))
        check(not bhome_over,
              "[codex] (b)-homes memory/portability без новых CLAUDE.md сверх baseline" +
              (f" — {bhome_over}" if bhome_over else ""))
        # P5: regimen-doctor harness-aware — рапортует СОСТОЯНИЕ codex-оверлея, не наличие
        dcx = subprocess.run([sys.executable, "regimen-doctor.py", "--dir", "."], cwd=cx,
                             capture_output=True, text=True)
        check("Traceback" not in dcx.stderr, "[codex] regimen-doctor без traceback на codex-проекте")
        check("обвязка рантайма: codex" in dcx.stdout, "[codex] doctor детектит codex-обвязку")
        check("агент-профили" in dcx.stdout, "[codex] doctor рапортует состояние codex агент-профилей")
        check("accountability" in dcx.stdout,
              "[codex] doctor честно рапортует accountability-класс хуков/docs-only (KL-7/G2)")

        # ---- codex прозовый режим (wiring=no): AGENTS.md есть, .codex/ обвязки нет ----
        cxp = os.path.join(base, "codex-prose")
        r = gen(cxp, name="Codex Prose", backend="none", frontend="none",
                arch="", domain="", testing="test-along", wiring="no", harness="codex")
        check(r.returncode == 0, "[codex-prose] генератор (rc=0)")
        check(os.path.exists(os.path.join(cxp, "AGENTS.md")), "[codex-prose] AGENTS.md (вход) есть даже без обвязки")
        check(not os.path.isdir(os.path.join(cxp, ".codex")), "[codex-prose] .codex/ обвязки нет (wiring=no)")

        # ---- dual-mode: new создаёт делегирующий Day-0 ----
        d0 = os.path.join(base, "newmode")
        r = gen(d0, name="Kick", backend="go", frontend="none",
                arch="", domain="", testing="test-along", wiring="no", mode="new")
        day0 = os.path.join(d0, "docs", "day-0-guide.md")
        check(r.returncode == 0 and os.path.exists(day0), "[mode-new] day-0-guide.md создан")
        if os.path.exists(day0):
            b = open(day0, encoding="utf-8").read()
            check("go mod init" in b, "[mode-new] day-0 содержит делегирующую init-команду стека")

        # ---- dual-mode: overlay не затирает существующий проект ----
        ov = os.path.join(base, "overlay")
        os.makedirs(ov)
        open(os.path.join(ov, "README.md"), "w").write("# Existing\n")
        open(os.path.join(ov, "CLAUDE.md"), "w").write("# existing entry\n")
        open(os.path.join(ov, "main.go"), "w").write("package main\n")
        r = gen(ov, name="Ov", backend="go", frontend="none",
                arch="", domain="", testing="test-along", wiring="no", mode="overlay")
        check(r.returncode == 0, "[mode-overlay] генератор отработал (rc=0)")
        check(open(os.path.join(ov, "README.md")).read() == "# Existing\n",
              "[mode-overlay] существующий README.md не затёрт")
        check(open(os.path.join(ov, "CLAUDE.md")).read() == "# existing entry\n",
              "[mode-overlay] существующий CLAUDE.md не затёрт")
        check(os.path.exists(os.path.join(ov, "CLAUDE.regimen.md")),
              "[mode-overlay] регламент сохранён как CLAUDE.regimen.md")
        check(os.path.exists(os.path.join(ov, "core", "principles.md")),
              "[mode-overlay] регламент (core/) наложен рядом")
        check(not os.path.exists(os.path.join(ov, "docs", "day-0-guide.md")),
              "[mode-overlay] Day-0 не создаётся (проект уже существует)")

        # ---- отказ при непустом каталоге (режим new по умолчанию) ----
        r2 = gen(s, name="Bare2", backend="none", frontend="none",
                 arch="", domain="", testing="test-along", wiring="no")
        check(r2.returncode != 0, "[safety] повторная генерация (new) в непустой каталог отклонена")

        # ---- регрессии подтверждённых багов (adversarial probe) ----
        e = os.path.join(base, "edge-emptyslug")
        r = gen(e, name="P", backend="стек", frontend="none", arch="", domain="", testing="bdd", wiring="no")
        check(r.returncode == 0 and not os.path.exists(os.path.join(e, "stack", ".md")),
              "[edge] стек с пустым slug не создаёт скрытый stack/.md")
        check("slug" in (r.stderr or ""), "[edge] предупреждение про пустой slug")

        e = os.path.join(base, "edge-collide")
        r = gen(e, name="P", backend="c++", frontend="c#", arch="", domain="", testing="bdd", wiring="no")
        sfiles = sorted(os.listdir(os.path.join(e, "stack"))) if os.path.isdir(os.path.join(e, "stack")) else []
        check(r.returncode == 0 and "дублирует" in (r.stderr or ""),
              "[edge] c++/c# (slug-коллизия) предупреждает, не клобберит молча")
        check(len(sfiles) == 1, f"[edge] коллизия -> один stack-файл (факт {sfiles})")

        e = os.path.join(base, "edge-ws")
        r = gen(e, name="P", backend="  go  ", frontend="none", arch="", domain="", testing="bdd", wiring="no")
        gomd = os.path.join(e, "stack", "go.md")
        body = open(gomd, encoding="utf-8").read() if os.path.exists(gomd) else ""
        check(os.path.exists(gomd) and "СКЕЛЕТ нового стека" not in body,
              "['  go  '] нормализуется в реальный stack/go.md, не в скелет")

        ff = os.path.join(base, "edge-isfile")
        open(ff, "w").write("x")
        r = gen(ff, name="P", backend="none", frontend="none", arch="", domain="", testing="bdd", wiring="no")
        check(r.returncode != 0 and "Traceback" not in (r.stderr or ""),
              "[edge] --dir=файл отклонён без traceback")

        r = subprocess.run([sys.executable, GEN, "--name", "P", "--backend", "none", "--frontend", "none",
                            "--arch", "", "--domain", "", "--testing", "bdd", "--wiring", "no"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        check(r.returncode != 0, "[edge] non-tty без --dir отклонён (не пишет в parent cwd)")

        e = os.path.join(base, "edge-dup")
        gen(e, name="P", backend="go", frontend="go", arch="", domain="", testing="bdd", wiring="no")
        cl = open(os.path.join(e, "CLAUDE.md"), encoding="utf-8").read()
        sec = cl.split("## Стек", 1)[-1].split("##", 1)[0]
        check(sec.count("- go") == 1, "[edge] go+go дедуплицируется в один булет")

        # ---- здоровье самого пакета ----
        bad = ["layered-three-tier", "PROJECT_CONTEXT", "galлюцин", "writeen", "不"]
        hits = []
        for p in md_files(PACK):
            if "/examples/" in p:
                continue
            t = open(p, encoding="utf-8").read()
            for b in bad:
                if b in t:
                    hits.append(f"{os.path.relpath(p, PACK)}:{b}")
        check(not hits, "[pack] нет мёртвых строк/опечаток" + (f" {hits}" if hits else ""))

        cp = subprocess.run([sys.executable, "-m", "py_compile", GEN], capture_output=True, text=True)
        check(cp.returncode == 0, "[pack] new-project.py компилируется")

        # справочник: все файлы оглавления на месте (ORDER не дрейфует под переименования)
        rh = os.path.join(PACK, "render-handbook.py")
        if os.path.exists(rh):
            cp = subprocess.run([sys.executable, "-m", "py_compile", rh], capture_output=True, text=True)
            check(cp.returncode == 0, "[pack] render-handbook.py компилируется")
            cp = subprocess.run([sys.executable, rh, "--check"], capture_output=True, text=True)
            check(cp.returncode == 0, f"[pack] render-handbook --check (все файлы ORDER на месте): {cp.stderr.strip()[:80]}")

        # карта ролей пакета не дрейфует относительно roles.json
        cp = subprocess.run([sys.executable, os.path.join(PACK, "sync-roles.py"), "--check"],
                            capture_output=True, text=True)
        check(cp.returncode == 0, "[pack] sync-roles --check зелёный (roles.json ↔ таблицы)")

        # tripwire: new-project.fill_claude режет секции по ТОЧНЫМ заголовкам шаблона CLAUDE.md
        # (regex `## Стек`→`## Архитектура`, `## Testing philosophy`→`## Специфика проекта`).
        # Переименование любого из них тихо ломает заполнение (try/except → оставит плейсхолдеры).
        # Этот чек падает раньше, заставляя синхронно обновить и шаблон, и fill_claude.
        entry_tmpl = open(os.path.join(PACK, "CLAUDE.md"), encoding="utf-8").read()
        for h in ("## Стек", "## Архитектура", "## Testing philosophy", "## Специфика проекта"):
            check(h in entry_tmpl, f"[pack] шаблон CLAUDE.md содержит заголовок «{h}» (на нём держится fill_claude)")

        # ---- бэкстоп счёта файлов (ADR-010:115): tripwire неподъёмности долга N-оверлеев ----
        # Каждая роль воспроизводится РОВНО ОДНИМ runtime-specific агент-файлом НА КАЖДЫЙ рантайм:
        #   claude-code -> .claude/agents/<agent>.md ; codex -> overlays/codex/.codex/agents/<agent>.toml
        # → добавление роли стоит (N рантаймов) файлов. Этот блок а) проверяет, что footprint роли
        # на рантайм = 1 (не растёт), и б) ТРИГЕРИТ, когда число рантайм-оверлеев превышает порог —
        # заставляя сознательно поднять порог И перечитать предупреждение о долге (ADR-010/011).
        pack_roles = json.load(open(os.path.join(PACK, "roles.json")))["roles"]
        RT_AGENT = {
            "claude-code": lambda a: os.path.join(PACK, ".claude", "agents", f"{a}.md"),
            "codex":       lambda a: os.path.join(PACK, "overlays", "codex", ".codex", "agents", f"{a}.toml"),
        }
        for rt, fn in RT_AGENT.items():
            miss = [r["agent"] for r in pack_roles if not os.path.exists(fn(r["agent"]))]
            check(not miss, f"[backstop] {rt}: каждая роль roles.json имеет ровно один агент-файл (нет: {miss})")
        # число фактически присутствующих рантайм-оверлеев = .claude + каждый подкаталог overlays/
        ovdir = os.path.join(PACK, "overlays")
        runtimes_present = (1 if os.path.isdir(os.path.join(PACK, ".claude")) else 0) + (
            len([d for d in os.listdir(ovdir) if os.path.isdir(os.path.join(ovdir, d))])
            if os.path.isdir(ovdir) else 0)
        # footprint новой роли = (рантаймов) × (1 файл/рантайм). Порог 2 = claude + codex.
        RUNTIME_THRESHOLD = 2
        check(runtimes_present <= RUNTIME_THRESHOLD,
              f"[backstop] рантайм-оверлеев present={runtimes_present} > порог {RUNTIME_THRESHOLD}: "
              f"добавление роли теперь трогает {runtimes_present} файлов. Подними RUNTIME_THRESHOLD "
              f"СОЗНАТЕЛЬНО, перечитав долг N-оверлеев (ADR-010 §Последствия) — это tripwire, не баг.")

        # хуки на месте, исполняемы и прописаны в settings.json.example
        for h in ("check-loc.sh", "checkpoint-precompact.sh", "check-no-todo.sh"):
            hp = os.path.join(PACK, ".claude", "hooks", h)
            check(os.path.exists(hp) and os.access(hp, os.X_OK), f"[pack] хук {h} есть и исполняем")
        sj = json.load(open(os.path.join(PACK, ".claude", "settings.json.example")))
        check("PreCompact" in sj.get("hooks", {}), "[pack] settings.json.example содержит PreCompact-хук")

        # конституция: каждый ID из реестра constitution.md тегирован у канонического правила
        const = open(os.path.join(PACK, "core", "constitution.md"), encoding="utf-8").read()
        ids = set(re.findall(r"\b[A-Z]{2}-NN-\d{2}\b", const))
        check(len(ids) >= 8, f"[pack] constitution.md содержит реестр non-negotiable (нашёл {len(ids)})")
        core_src = ""
        for cf in ("principles.md", "code-quality.md", "quality-gates.md"):
            core_src += open(os.path.join(PACK, "core", cf), encoding="utf-8").read()
        missing = [i for i in ids if i not in core_src]
        check(not missing, f"[pack] каждый ID конституции тегирован у канона (нет тега: {sorted(missing)})")

        check("_TEMPLATE" not in subprocess.run(
            [sys.executable, GEN, "--list"], capture_output=True, text=True).stdout,
            "[pack] _TEMPLATE.md не утёк в список стеков")

        # каждый описанный стек обязан закрыть контракт «Чистая сборка» (на него ссылается
        # core/quality-gates.md); раньше это проверялось только для скелетов из _TEMPLATE.
        for sp in md_files(os.path.join(PACK, "stack")):
            if os.path.basename(sp).startswith("_"):
                continue
            body = open(sp, encoding="utf-8").read()
            check("Чистая сборка" in body,
                  f"[pack] {os.path.relpath(sp, PACK)} содержит раздел «Чистая сборка»")

        # Авторский контекст (имена проектов/людей/инфры) не должен протекать НИКУДА, включая
        # examples/. Сами слова-маркеры держим в гитигнор-файле `.leakwords` (по строке на слово,
        # `#` — комментарий), чтобы имена НЕ жили в трекаемом коде и не ре-лекались самим тестом.
        # Нет файла (например, на чужом клоне) → проверка пропускается, счёт не ломается.
        leakfile = os.path.join(PACK, ".leakwords")
        leak_words = []
        if os.path.exists(leakfile):
            leak_words = [w.strip().lower() for w in open(leakfile, encoding="utf-8")
                          if w.strip() and not w.lstrip().startswith("#")]
        # Сканируем только ТРЕКАЕМЫЕ файлы — ровно то, что уйдёт в push; локальный scratch
        # (гитигнор) с абсолютными путями `/Users/<имя>/…` не должен ронять чек.
        leak_hits = []
        if leak_words:
            tracked = subprocess.run(["git", "-C", PACK, "ls-files", "*.md"],
                                     capture_output=True, text=True)
            scan = ([os.path.join(PACK, x) for x in tracked.stdout.split("\n") if x]
                    if tracked.returncode == 0 and tracked.stdout.strip()
                    else [p for p in md_files(PACK) if "/scratchpad/" not in p.replace(os.sep, "/")])
            for p in scan:
                low = open(p, encoding="utf-8").read().lower()
                for b in leak_words:
                    if b in low:
                        leak_hits.append(f"{os.path.relpath(p, PACK)}:{b}")
        check(not leak_hits, "[pack] нет утёкшего авторского контекста" + (f" {leak_hits}" if leak_hits else ""))
    finally:
        shutil.rmtree(base, ignore_errors=True)

    # ---- отчёт ----
    passed = sum(1 for ok, _ in results if ok)
    failed = [m for ok, m in results if not ok]
    for m in failed:
        print("  ✗", m)
    print(f"\n{passed}/{len(results)} проверок зелёные.")
    if failed:
        print(f"✗ {len(failed)} FAIL")
        return 1
    print("✓ всё зелёное")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
