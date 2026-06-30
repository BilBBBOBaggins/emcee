#!/usr/bin/env bash
# PreCompact-хук: ПЕРЕД компакцией контекста пишет recovery-чекпойнт (указатель на транскрипт +
# время + триггер) в docs/checkpoints.md, чтобы детали не терялись молча и можно было продолжить
# работу после сжатия. Опционально — включается через .claude/settings.json.
#
# Это минимальный честный вариант (фиксирует ТОЧКУ восстановления). Для СМЫСЛОВОГО summary в
# чекпойнт расширь скрипт вызовом модели по транскрипту — см. core/memory.md.
# Известный edge-case: PreCompact может не сработать на ручном /compact.
# python3 (а не jq) — пакет и так требует python3, это переносимее на macOS.
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
  printf '\n## Компакция (%s) — %s\n' "$trigger" "$(date '+%Y-%m-%d %H:%M:%S')"
  printf -- '- Транскрипт: %s\n' "$tpath"
  printf -- '- Восстановление: прочитай транскрипт + `git log`, продолжи с последнего шага (см. core/memory.md → прунинг: это эпизодическое, чисти/архивируй).\n'
} >> "$out"

exit 0
