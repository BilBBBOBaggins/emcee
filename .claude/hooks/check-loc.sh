#!/usr/bin/env bash
# PostToolUse-хук (Edit|Write): проверяет, что ИМЕННО отредактированный файл
# (tool_input.file_path из stdin-JSON, а не весь diff репозитория) не превысил LOC-лимит
# из core/quality-gates.md. Так сигнал «обоснуй цельность или split» бьёт по твоей правке, а не
# падает из-за чужого/старого большого файла. Опционально — включается через .claude/settings.json.
#
# PostToolUse не может ОТМЕНИТЬ запись (инструмент уже отработал); exit 2 возвращает stderr
# агенту как обратную связь — он увидит сигнал и следующим действием обоснует цельность или split.
# Для жёсткой ПРЕВЕНТИВНОЙ блокировки нужен PreToolUse (см. docs Claude Code hooks).
# Подстрой лимиты и список расширений под свою таблицу в core/quality-gates.md.
set -euo pipefail

CODE_LIMIT="${LOC_LIMIT:-500}"          # код: .go/.ts/.py/.cpp…
HEADER_LIMIT="${LOC_HEADER_LIMIT:-250}" # заголовки: .h/.hpp — должны быть лаконичнее

# Путь отредактированного файла берём из stdin-JSON. python3 — пакет и так требует его
# (new-project.py/selftest.py), это переносимее, чем jq, которого на macOS нет из коробки.
input="$(cat)"
f="$(printf '%s' "$input" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("tool_input",{}).get("file_path","") or "")
except Exception:
    print("")' 2>/dev/null || true)"

# Нет пути или файла больше нет — проверять нечего.
[[ -n "$f" && -f "$f" ]] || exit 0

case "$f" in
  *.h|*.hpp|*.hh|*.hxx) lim=$HEADER_LIMIT ;;
  *.go|*.ts|*.tsx|*.py|*.cpp|*.cc|*.cxx) lim=$CODE_LIMIT ;;
  *) exit 0 ;;
esac

n=$(wc -l < "$f" | tr -d ' ')
if (( n > lim )); then
  echo "LOC-сигнал: $f = $n строк (> $lim). Обоснуй цельность (одна ответственность) ИЛИ split по responsibility — core/quality-gates.md QG-NN-03." >&2
  exit 2
fi
exit 0
