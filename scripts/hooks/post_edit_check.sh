#!/usr/bin/env bash
# PostToolUse hook: after edits to rtl/ or isa/, run a quick lint + ISA-load check.
# ADVISORY ONLY — always exits 0. Hard enforcement of lint-clean lives at commit time
# and in CI (see DECISIONS.md D0.9). Reads the tool payload (JSON) from stdin.
set -u

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

payload="$(cat)"
fp="$(printf '%s' "$payload" | python3 -c '
import sys, json
try:
    print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))
except Exception:
    pass
' 2>/dev/null)"

case "$fp" in
  *"/isa/"*)
    echo "[posttool] isa/ edit -> checking ISA loads"
    if python3 "$ROOT/isa/asm.py" >/dev/null 2>&1 && python3 "$ROOT/isa/sim.py" >/dev/null 2>&1; then
      echo "  [ ok ] ISA.yaml + asm.py + sim.py load"
    else
      echo "  [warn] ISA consumers failed to load — check ISA.yaml / asm.py / sim.py"
    fi
    ;;
esac

case "$fp" in
  *"/rtl/"*)
    echo "[posttool] rtl/ edit -> quick lint"
    if command -v verilator >/dev/null 2>&1; then
      python3 "$ROOT/scripts/lint.py" || echo "  [warn] lint findings above"
    else
      echo "  (verilator absent locally; lint enforced in CI)"
    fi
    ;;
esac

exit 0
