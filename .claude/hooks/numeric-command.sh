#!/usr/bin/env bash
# UserPromptSubmit hook: makes the numeric-command trigger mechanical. A message consisting
# ONLY of 1–3 numbers is the regimen's dispatch grammar (N / R D / R D T — core/task-protocol.md
# → "System of short commands"), but as bare prose the trigger rides on model compliance alone —
# and a single-token message with no verb is exactly where models hedge ("what would you like
# to work on?") instead of acting. Field case: "35" as the first message of a fresh session got
# back a menu of commands instead of the architect entering day 35.
# On match this hook injects a dispatch order (UserPromptSubmit stdout on exit 0 is added to
# context); any other message produces no output and is untouched — so `R D` / `R D T` and
# ordinary prompts keep working exactly as before. Optional — enabled via .claude/settings.json.
set -euo pipefail

# The prompt comes from the stdin JSON. python3 — the package already requires it
# (new-project.py/selftest.py), which is more portable than jq, which isn't on macOS out of the box.
input="$(cat)"
prompt="$(printf '%s' "$input" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("prompt","") or "")
except Exception:
    print("")' 2>/dev/null || true)"

# 1–3 whitespace-separated integers and nothing else; any other text is a real prompt.
[[ "$prompt" =~ ^[[:space:]]*[0-9]+([[:space:]]+[0-9]+){0,2}[[:space:]]*$ ]] || exit 0

cat <<'EOF'
This message is the regimen's NUMERIC COMMAND, not an ambiguous input (CLAUDE.md → "Quick numeric
commands", core/task-protocol.md → "System of short commands"): one number `N` = the architect
enters day N; two numbers `R D` = role R enters day D's context; three numbers `R D T` = role R
takes task T from docs/day-<D>-guide.md. Dispatch it NOW, exactly as the /role slash command
would (.claude/commands/role.md): resolve the digit against the role table in the entry file and
launch the matching subagent (no subagents set up — read roles/<role>.md and act as that role in
this session). Do NOT reply with a menu of commands, do NOT ask "what would you like to work
on?", do NOT request confirmation — the numbers ARE the request. Sole exception: if your
immediately preceding assistant message asked a question whose direct answer is this number,
treat it as that answer instead.
EOF
exit 0
