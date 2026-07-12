#!/usr/bin/env bash
set -euo pipefail
TARGET_DIR="${TARGET_DIR:-$HOME/.codex/skills}"
if [ "${NON_INTERACTIVE:-0}" = "1" ]; then confirm=y; else read -rp "删除 $TARGET_DIR/search-agent？(y/N) " confirm; fi
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "已取消"; exit 0; }
rm -rf "$TARGET_DIR/search-agent"
echo "已卸载 search-agent；未修改其他 Skill 或 shell 配置。"
