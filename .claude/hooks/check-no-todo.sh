#!/usr/bin/env bash
# Stop-хук (OPT-IN): блокирует завершение, если в ДОБАВЛЕННОМ коде есть comment-like TODO/FIXME
# (конституция CQ-NN-01, core/code-quality.md). exit 2 → stderr возвращается агенту как фидбэк.
#
# Узкий контракт (минимум ложных срабатываний):
# - только добавленные строки (git diff -U0 HEAD) + новые untracked-файлы;
# - только кодовые расширения; исключены vendor/node_modules/dist/build/coverage/generated;
# - ловим только comment-like маркеры (// # /* * -- ; перед TODO/FIXME), не произвольный литерал;
# - печатает file:line. НЕ включён по умолчанию — добавь вручную в settings.json (см. .claude/README.md).
set -uo pipefail

python3 - <<'PY'
import subprocess, re, os, sys

CODE = re.compile(r'\.(go|ts|tsx|js|jsx|py|cpp|cc|cxx|h|hpp|rs|java|kt|rb|php|swift|c)$')
EXCL = re.compile(r'(^|/)(vendor|node_modules|dist|build|coverage|\.git|__pycache__|generated)/')
MARK = re.compile(r'(//|#|/\*|\*|--|;)\s*(TODO|FIXME)\b')

def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout

hits = []

# 1) добавленные строки в отслеживаемых файлах
cur, newln = None, 0
for ln in git("diff", "-U0", "HEAD").splitlines():
    if ln.startswith('+++ b/'):
        cur = ln[6:]; continue
    if ln.startswith('@@'):
        m = re.search(r'\+(\d+)', ln); newln = int(m.group(1)) if m else 0; continue
    if ln.startswith('+'):  # добавленная строка (+++ уже отсеян выше)
        if cur and CODE.search(cur) and not EXCL.search(cur) and MARK.search(ln[1:]):
            hits.append(f"{cur}:{newln}: {ln[1:].strip()}")
        newln += 1

# 2) новые untracked-файлы — весь файл
for f in git("ls-files", "--others", "--exclude-standard").split():
    if not CODE.search(f) or EXCL.search(f) or not os.path.isfile(f):
        continue
    try:
        for i, line in enumerate(open(f, encoding="utf-8", errors="ignore"), 1):
            if MARK.search(line):
                hits.append(f"{f}:{i}: {line.strip()}")
    except OSError:
        pass

if hits:
    sys.stderr.write("Constitution CQ-NN-01 (без TODO/FIXME): маркеры в добавленном коде —\n")
    for h in hits[:50]:
        sys.stderr.write("  " + h + "\n")
    sys.stderr.write("Убери TODO/FIXME (делай сейчас или заведи задачу) — core/code-quality.md.\n")
    sys.exit(2)
sys.exit(0)
PY
