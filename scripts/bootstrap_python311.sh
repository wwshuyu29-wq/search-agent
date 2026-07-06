#!/usr/bin/env bash
# Create a project-local Python 3.11+ virtual environment for Search Agent.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${SEARCH_AGENT_VENV:-$ROOT_DIR/.venv}"

find_python() {
  if command -v python3.11 >/dev/null 2>&1; then
    command -v python3.11
    return 0
  fi

  if [ -x "$HOME/.local/bin/python3.11" ]; then
    printf '%s\n' "$HOME/.local/bin/python3.11"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import sys
if sys.version_info >= (3, 11):
    print(sys.executable)
else:
    raise SystemExit(1)
PY
    return 0
  fi

  return 1
}

PYTHON_BIN="$(find_python || true)"
if [ -z "${PYTHON_BIN:-}" ]; then
  cat >&2 <<'EOF'
[ERROR] Python 3.11+ not found.
Install Python 3.11 first, then rerun:
  brew install python@3.11
or use your company's standard Python 3.11 runtime.
EOF
  exit 1
fi

echo "[INFO] Using Python: $PYTHON_BIN"
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"

echo "[OK] Search Agent venv ready: $VENV_DIR"
echo "Activate it with:"
echo "  source \"$VENV_DIR/bin/activate\""
echo "Then verify:"
echo "  python scripts/search_agent_doctor.py --live"
