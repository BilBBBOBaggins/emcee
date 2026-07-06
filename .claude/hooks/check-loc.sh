#!/usr/bin/env bash
# PostToolUse hook (Edit|Write): checks that the file that was JUST edited
# (tool_input.file_path from the stdin JSON, not the whole repo diff) hasn't exceeded the LOC
# limit from core/quality-gates.md. This way the "justify cohesion or split" signal hits your
# edit, not a fail from someone else's/an old large file. Optional — enabled via .claude/settings.json.
#
# PostToolUse can't UNDO the write (the tool has already run); exit 2 returns stderr to the
# agent as feedback — it will see the signal and, as its next action, justify cohesion or split.
# A hard PREVENTIVE block needs PreToolUse (see the Claude Code hooks docs).
# Adjust the limits and extension list to match your table in core/quality-gates.md.
set -euo pipefail

CODE_LIMIT="${LOC_LIMIT:-500}"          # code: .go/.ts/.py/.cpp…
HEADER_LIMIT="${LOC_HEADER_LIMIT:-250}" # headers: .h/.hpp — should be leaner

# We get the edited file's path from the stdin JSON. python3 — the package already requires it
# (new-project.py/selftest.py), which is more portable than jq, which isn't on macOS out of the box.
input="$(cat)"
f="$(printf '%s' "$input" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("tool_input",{}).get("file_path","") or "")
except Exception:
    print("")' 2>/dev/null || true)"

# No path, or the file is gone already — nothing to check.
[[ -n "$f" && -f "$f" ]] || exit 0

case "$f" in
  *.h|*.hpp|*.hh|*.hxx) lim=$HEADER_LIMIT ;;
  *.go|*.ts|*.tsx|*.py|*.cpp|*.cc|*.cxx|*.rs|*.qml) lim=$CODE_LIMIT ;;
  *) exit 0 ;;
esac

n=$(wc -l < "$f" | tr -d ' ')
if (( n > lim )); then
  echo "LOC signal: $f = $n lines (> $lim). Justify cohesion (single responsibility) OR split by responsibility — core/quality-gates.md QG-NN-03." >&2
  exit 2
fi
exit 0
