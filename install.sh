#!/usr/bin/env bash
# ================================================================
# Search Agent Skill 3.0 一键安装脚本
# ----------------------------------------------------------------
# 完成以下动作：
#   1. 把当前 search-agent skill 复制/软链到 Codex skills 目录
#   2. 从 GitHub 拉取 marketingskills（44 个营销 skill）
#   3. 从 GitHub 拉取 finance-skills（20+ 个金融 skill）
#   4. 安装 Python 依赖（requests）
#   5. 写入 Firecrawl API Key 到 shell 配置
#   6. 验证安装
#
# 用法：
#   bash install.sh              # 默认安装到 ~/.codex/skills/
#   TARGET_DIR=~/.claude/skills bash install.sh
# ================================================================

set -euo pipefail

# ---------- 配置 ----------
TARGET_DIR="${TARGET_DIR:-$HOME/.codex/skills}"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIRECRAWL_KEY_DEFAULT="${FIRECRAWL_API_KEY:-}"

MARKETING_REPO="https://github.com/coreyhaines31/marketingskills.git"
FINANCE_REPO="https://github.com/himself65/finance-skills.git"

# ---------- 输出美化 ----------
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()     { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()   { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()  { echo -e "${RED}[ERR]${NC}   $*" >&2; }

# ---------- 环境检查 ----------
log "开始安装 Search Agent Skill 3.0"
log "目标目录：$TARGET_DIR"
echo

command -v git    >/dev/null 2>&1 || warn "git 未安装（如果需要在线更新会用到；离线安装不需要）"
command -v python3 >/dev/null 2>&1 || { error "缺少 python3，请先安装"; exit 1; }
command -v pip3   >/dev/null 2>&1 || { warn  "缺少 pip3，Python 依赖需手动安装"; }

ok "环境检查通过"
echo

# ---------- Step 1: 创建目标目录 ----------
log "Step 1/6: 创建 skills 目录"
mkdir -p "$TARGET_DIR"
ok "目录已创建：$TARGET_DIR"
echo

# ---------- Step 2: 部署 search-agent skill ----------
log "Step 2/6: 部署 search-agent skill"
SEARCH_AGENT_DEST="$TARGET_DIR/search-agent"

if [ -e "$SEARCH_AGENT_DEST" ]; then
    warn "$SEARCH_AGENT_DEST 已存在"
    read -rp "覆盖？(y/N) " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        rm -rf "$SEARCH_AGENT_DEST"
    else
        log "跳过 search-agent 部署"
        SKIP_SEARCH_AGENT=1
    fi
fi

if [ -z "${SKIP_SEARCH_AGENT:-}" ]; then
    # 复制（不用软链，避免同事拿到包后路径失效）
    cp -R "$CURRENT_DIR" "$SEARCH_AGENT_DEST"
    # 清理不应进 skills 目录的文件
    rm -rf "$SEARCH_AGENT_DEST/.git" \
           "$SEARCH_AGENT_DEST/install.sh" \
           "$SEARCH_AGENT_DEST/uninstall.sh" \
           "$SEARCH_AGENT_DEST/output" \
           "$SEARCH_AGENT_DEST/__pycache__" 2>/dev/null || true
    find "$SEARCH_AGENT_DEST" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$SEARCH_AGENT_DEST" -name "*.pyc" -delete 2>/dev/null || true
    ok "search-agent 已部署到 $SEARCH_AGENT_DEST"
fi
echo

# ---------- Step 3: 部署 marketingskills ----------
log "Step 3/6: 部署 marketingskills (44 个营销 skill)"
MARKETING_DEST="$TARGET_DIR/marketing"
VENDOR_MARKETING="$CURRENT_DIR/vendor/marketing"

install_from_vendor_or_git() {
    local name="$1" vendor_path="$2" repo_url="$3" dest="$4"

    if [ -d "$dest/.git" ] || [ -f "$dest/SKILL.md" ] || [ -d "$dest/skills" ] || [ -d "$dest/plugins" ]; then
        warn "$name 目标目录已存在：$dest"
        read -rp "覆盖？(y/N) " confirm
        [[ "$confirm" =~ ^[Yy]$ ]] || { log "跳过 $name"; return; }
        rm -rf "$dest"
    fi

    # 优先用内置 vendor（离线可用）
    if [ -d "$vendor_path" ]; then
        log "使用内置 vendor 副本（无需联网）"
        cp -R "$vendor_path" "$dest"
        ok "$name 已从 vendor 部署 → $dest"
        return
    fi

    # 回退到 git clone
    log "vendor 未找到，尝试 git clone（需要网络）"
    if git clone --depth 1 "$repo_url" "$dest" 2>&1 | tail -3; then
        ok "$name 已 git clone → $dest"
    else
        error "$name 部署失败：既无 vendor 也无法 git clone"
        return 1
    fi
}

install_from_vendor_or_git "marketing" "$VENDOR_MARKETING" "$MARKETING_REPO" "$MARKETING_DEST"
echo

# ---------- Step 4: 部署 finance-skills ----------
log "Step 4/6: 部署 finance-skills (20+ 个金融 skill)"
FINANCE_DEST="$TARGET_DIR/finance"
VENDOR_FINANCE="$CURRENT_DIR/vendor/finance"

install_from_vendor_or_git "finance" "$VENDOR_FINANCE" "$FINANCE_REPO" "$FINANCE_DEST"
echo

# ---------- Step 5: 安装 Python 依赖 ----------
log "Step 5/6: 检查 Python 依赖"
if python3 -c "import requests" >/dev/null 2>&1; then
    ok "requests 已安装（Firecrawl 脚本可用）"
elif command -v pip3 >/dev/null 2>&1; then
    log "尝试安装 requests..."
    pip3 install -q --user requests 2>&1 | tail -3 && ok "requests 已安装" \
        || warn "pip 安装失败。如果无网络：Firecrawl 层将不可用，其他层不受影响"
else
    warn "requests 未安装且无 pip3。Firecrawl 层将不可用；如需启用，手动安装 requests"
fi
echo

# ---------- Step 6: 配置 Firecrawl API Key ----------
log "Step 6/6: 配置 Firecrawl API Key"

# 检测 shell 配置文件
SHELL_RC=""
case "${SHELL:-}" in
    */zsh)  SHELL_RC="$HOME/.zshrc" ;;
    */bash) SHELL_RC="$HOME/.bashrc" ;;
    *)      SHELL_RC="$HOME/.profile" ;;
esac

if grep -q "FIRECRAWL_API_KEY" "$SHELL_RC" 2>/dev/null; then
    ok "FIRECRAWL_API_KEY 已存在于 $SHELL_RC"
else
    cat >> "$SHELL_RC" <<EOF

# Search Agent Skill 3.0 - Firecrawl API Key
# 添加于 $(date '+%Y-%m-%d %H:%M:%S')
export FIRECRAWL_API_KEY="$FIRECRAWL_KEY_DEFAULT"
EOF
    ok "已写入 $SHELL_RC"
    warn "请执行 'source $SHELL_RC' 或重开终端使其生效"
fi
echo

# ---------- 验证安装 ----------
log "验证安装"
echo

check() {
    local name="$1" path="$2"
    if [ -e "$path" ]; then
        ok "$name: $path"
    else
        error "$name 缺失: $path"
        return 1
    fi
}

check "search-agent SKILL.md"      "$SEARCH_AGENT_DEST/SKILL.md"
check "search-agent frameworks.md" "$SEARCH_AGENT_DEST/references/frameworks.md"
check "search-agent workflow.md"   "$SEARCH_AGENT_DEST/references/workflow.md"
check "search-agent external-skills.md" "$SEARCH_AGENT_DEST/references/external-skills.md"
check "firecrawl_search.py"        "$SEARCH_AGENT_DEST/scripts/firecrawl_search.py"
check "finance-rss-reader"         "$SEARCH_AGENT_DEST/lib/finance-rss-reader"
check "marketingskills"            "$MARKETING_DEST/skills"
check "finance-skills"             "$FINANCE_DEST/plugins"

echo
# 验证 Firecrawl 脚本能运行
if python3 "$SEARCH_AGENT_DEST/scripts/firecrawl_search.py" --help >/dev/null 2>&1; then
    ok "firecrawl_search.py --help 通过"
else
    error "firecrawl_search.py 无法运行"
fi

echo
ok "=================================================="
ok "  Search Agent Skill 3.0 安装完成"
ok "=================================================="
echo
echo "已安装 skill:"
echo "  - search-agent  (调研编排大脑)"
echo "  - marketing/*   (44 个营销专家 skill)"
echo "  - finance/*     (20+ 个金融专家 skill)"
echo
echo "下一步："
echo "  1. source $SHELL_RC  # 加载 FIRECRAWL_API_KEY"
echo "  2. 在 Codex 里唤起 search-agent skill 试试："
echo "     '帮我调研拼多多 2026 年的下沉市场竞争格局'"
echo
echo "文档索引："
echo "  - $SEARCH_AGENT_DEST/SKILL.md              (主入口)"
echo "  - $SEARCH_AGENT_DEST/references/frameworks.md    (31 分析框架)"
echo "  - $SEARCH_AGENT_DEST/references/external-skills.md (外部 skill 挂载矩阵)"
echo
