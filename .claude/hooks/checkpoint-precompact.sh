#!/usr/bin/env bash
# PreCompact hook: BEFORE context compaction, writes a recovery checkpoint (a pointer to the
# transcript + time + trigger) to docs/checkpoints.md, so details aren't lost silently and work
# can continue after compaction. Optional — enabled via .claude/settings.json.
#
# This is the minimal honest version (fixes a recovery POINT). For a MEANINGFUL summary in the
# checkpoint, extend the script with a model call over the transcript — see core/memory.md.
# Known edge case: PreCompact may not fire on a manual /compact.
# python3 (not jq) — the package already requires python3, which is more portable on macOS.
set -euo pipefail

input="$(cat)"
meta="$(printf '%s' "$input" | python3 -c 'import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get("transcript_path") or "-") + "\t" + (d.get("trigger") or "auto"))
except Exception:
    print("-\tauto")' 2>/dev/null || printf -- '-\tauto')"

tpath="${meta%%$'\t'*}"
trigger="${meta##*$'\t'}"

out="${CLAUDE_PROJECT_DIR:-.}/docs/checkpoints.md"
mkdir -p "$(dirname "$out")"
{
  printf '\n## Compaction (%s) — %s\n' "$trigger" "$(date '+%Y-%m-%d %H:%M:%S')"
  printf -- '- Transcript: %s\n' "$tpath"
  printf -- '- Recovery: read the transcript + `git log`, continue from the last step (see core/memory.md → pruning: this is episodic, clean up/archive).\n'
} >> "$out"

exit 0
