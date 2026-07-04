#!/usr/bin/env bash
# Stop hook (OPT-IN): blocks completion if the ADDED code contains a comment-like TODO/FIXME
# (constitution CQ-NN-01, core/code-quality.md). exit 2 → stderr is returned to the agent as feedback.
#
# Narrow contract (minimizes false positives):
# - only added lines (git diff -U0 HEAD) + new untracked files;
# - only code extensions; vendor/node_modules/dist/build/coverage/generated are excluded;
# - catches only comment-like markers (// # /* * -- ; before TODO/FIXME), not an arbitrary literal;
# - prints file:line. NOT enabled by default — add it manually to settings.json (see .claude/README.md).
set -uo pipefail

python3 - <<'PY'
import subprocess, re, os, sys

CODE = re.compile(r'\.(go|ts|tsx|js|jsx|py|cpp|cc|cxx|h|hpp|rs|java|kt|rb|php|swift|c)$')
EXCL = re.compile(r'(^|/)(vendor|node_modules|dist|build|coverage|\.git|__pycache__|generated)/')
MARK = re.compile(r'(//|#|/\*|\*|--|;)\s*(TODO|FIXME)\b')

def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout

hits = []

# 1) added lines in tracked files
cur, newln = None, 0
for ln in git("diff", "-U0", "HEAD").splitlines():
    if ln.startswith('+++ b/'):
        cur = ln[6:]; continue
    if ln.startswith('@@'):
        m = re.search(r'\+(\d+)', ln); newln = int(m.group(1)) if m else 0; continue
    if ln.startswith('+'):  # an added line (+++ was already filtered out above)
        if cur and CODE.search(cur) and not EXCL.search(cur) and MARK.search(ln[1:]):
            hits.append(f"{cur}:{newln}: {ln[1:].strip()}")
        newln += 1

# 2) new untracked files — the whole file
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
    sys.stderr.write("Constitution CQ-NN-01 (no TODO/FIXME): markers in added code —\n")
    for h in hits[:50]:
        sys.stderr.write("  " + h + "\n")
    sys.stderr.write("Remove the TODO/FIXME (do it now or file a task) — core/code-quality.md.\n")
    sys.exit(2)
sys.exit(0)
PY
