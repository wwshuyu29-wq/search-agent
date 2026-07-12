#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${TARGET_DIR:-$HOME/.codex/skills}"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$TARGET_DIR/search-agent"
mkdir -p "$TARGET_DIR"
if [ -e "$DEST" ]; then
  if [ "${NON_INTERACTIVE:-0}" = "1" ]; then confirm=y; else read -rp "覆盖 $DEST？(y/N) " confirm; fi
  [[ "$confirm" =~ ^[Yy]$ ]] || { echo "安装取消"; exit 0; }
  rm -rf "$DEST"
fi
cp -R "$CURRENT_DIR" "$DEST"
rm -rf "$DEST/.git" "$DEST/install.sh" "$DEST/uninstall.sh" "$DEST/output" "$DEST/.venv"
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -name '*.pyc' -delete 2>/dev/null || true
if [ "${SKIP_PYTHON_BOOTSTRAP:-0}" != "1" ]; then
  "$DEST/scripts/bootstrap_python311.sh" || echo "WARN: Python 环境未创建，请参考 USAGE.md" >&2
fi
if [ "${SKIP_SHELL_RC:-0}" != "1" ] && [ -n "${FIRECRAWL_API_KEY:-}" ]; then
  case "${SHELL:-}" in */zsh) rc="$HOME/.zshrc";; */bash) rc="$HOME/.bashrc";; *) rc="$HOME/.profile";; esac
  grep -q FIRECRAWL_API_KEY "$rc" 2>/dev/null || printf '\nexport FIRECRAWL_API_KEY="%s"\n' "$FIRECRAWL_API_KEY" >> "$rc"
fi
for path in SKILL.md references/frameworks.md references/workflow.md references/external-skills.md references/codex-execution.md specialists/catalog.json specialists/vendor.lock.json; do
  [ -e "$DEST/$path" ] || { echo "缺失: $DEST/$path" >&2; exit 1; }
done
echo "Search Agent 已安装为唯一顶层 Skill: $DEST"
echo "16 个内部 specialists 位于 $DEST/specialists；vendor 快照保留在内部。"
