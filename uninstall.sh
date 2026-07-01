#!/usr/bin/env bash
# Search Agent Skill 3.0 卸载脚本
set -euo pipefail

TARGET_DIR="${TARGET_DIR:-$HOME/.codex/skills}"

echo "将从 $TARGET_DIR 卸载："
echo "  - search-agent/"
echo "  - marketing/"
echo "  - finance/"
read -rp "确认？(y/N) " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "已取消"; exit 0; }

rm -rf "$TARGET_DIR/search-agent" "$TARGET_DIR/marketing" "$TARGET_DIR/finance"
echo "已卸载。FIRECRAWL_API_KEY 环境变量请手动从 shell 配置中移除。"
