# Search Agent Skill 3.0

## Internal specialist architecture

Installation exposes Search Agent as a **single top-level Skill**. Sixteen curated **internal specialists** are loaded through `specialists/catalog.json`; their non-discoverable `prompt.md` resources remain inside Search Agent. Full upstream snapshots stay under `vendor/`, with provenance and manual synchronization metadata in `specialists/vendor.lock.json`.

Update explicitly with `git pull origin main` followed by `bash install.sh`. Internal outputs remain subject to Source QA, Citation Audit, and every T1-T9 human/evidence gate. — 快速开始

一个基于 **31 个商业分析框架** 与 **多源分层搜索** 的通用调研 skill，覆盖竞品、产品、行业、用户、营销、财报与风险等场景。系统会推荐 3 套差异化大纲，由用户确认后严格按所选结构生成带可跳转引文的深度报告，不再强制所有报告套用倒金字塔。

## 一分钟安装

```bash
# 1. 解压
tar -xzf search-agent-skill-v3.0.tar.gz
cd search-agent-skill3.0

# 2. 一键安装（**完全离线可用**，外部 skill 已内嵌在 vendor/）
bash install.sh

# 3. 加载环境变量
source ~/.zshrc   # 或 ~/.bashrc

# 4. 完成。在 Codex 里试试：
#    "帮我调研拼多多 2026 年下沉市场竞争格局"
```

**无外网环境**：`install.sh` 会自动使用内置的 `vendor/marketing` 和 `vendor/finance` 副本，不需要访问 github.com。

**有外网时**（可选）：脚本会跳过 vendor，直接 `git clone` 最新版本。

## 装了什么？

安装脚本会在 `~/.codex/skills/` 下创建三个 skill：

| Skill | 内容 | 来源 |
|---|---|---|
| `search-agent/` | 调研编排大脑（本仓库） | 本地 |
| `marketing/` | 44 个营销/增长/SEO/CRO/内容 skill | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) |
| `finance/` | 20+ 金融/估值/情绪/市场数据 skill | [himself65/finance-skills](https://github.com/himself65/finance-skills) |

Firecrawl API Key 会自动写入 `~/.zshrc` 或 `~/.bashrc`。

## 工作流一览

```
用户输入调研需求
    ↓
Step 0 意图识别 → 输出【审核卡片】→ ⏸ 用户确认框架
    ↓
Step 1 多源分层检索（6 层）：
    Layer 1 官方(IR/SEC) → Layer 2 业绩会 → Layer 3 Firecrawl 深度分析
    Layer 4 中文媒体 → Layer 5 财经 RSS → Layer 6 垂直专家 skill
    ↓ 输出 YAML 源清单（source_id + confidence + key_facts）
    ↓
Step 2 结构化分析：
    - 金融题 → 优先调 finance/company-valuation / earnings-recap / ...
    - 营销题 → 优先调 marketing/copywriting / cro / seo-audit / ...
    - 通用题 → 走内置 31 框架
    ↓
T4 三套候选大纲 + Codex 推荐
    ↓ 用户在 T5 选择/组合/修改并确认
T6 确定性 Evidence Synthesis Writer 按 ApprovedOutline 综合多个 claim（无在线 SDK 时不伪称 LLM）
    ↓
T7 OutlineCompliance passed → Humanizer → FinalReport → IntegrityDiff passed → final_report_review
```

## 文档索引

- [`SKILL.md`](./SKILL.md) — Codex 主入口（此文件被 skill loader 读取）
- [`references/frameworks.md`](./references/frameworks.md) — 31 个分析框架的完整定义（战略 / 营销 / 金融三类）
- [`references/external-skills.md`](./references/external-skills.md) — 外部 skill 在 Step 0/1/2/3 每个节点的调用矩阵
- [`references/workflow.md`](./references/workflow.md) — Mermaid 工作流图
- [`references/team-workflow-guide.md`](./references/team-workflow-guide.md) — 给非技术同事看的完整使用说明、确认闸门和提示词模板
- [`CHANGELOG.md`](./CHANGELOG.md) — v1.0 → v3.0 演进
- [`CLAUDE.md`](./CLAUDE.md) — 原始 Claude 版调研助手（保留参考）

## 使用方式

### 方式 1：Codex 原生（推荐）

在 Codex 里直接说 "帮我调研 XX"，skill 会自动加载并按 Step 0→1→2→3 走完整流程。每个审核点会停下等你确认。

### 方式 2：Python CLI

```bash
# 交互式（含审核点）
python3 bin/search_agent.py "帮我分析英伟达 2026 Q2 财报"

# 自动模式只推进到大纲闸门，不会替用户批准大纲
python3 bin/search_agent.py "对比拼多多和淘宝" --auto

# 状态机恢复：先确认 T1，再选择大纲；自定义章节可由 JSON 数组输入
python3 bin/search_agent.py --workflow-resume 确认 --state-file search_agent_state.json
python3 bin/search_agent.py --workflow-resume A --sections-file custom-sections.json --state-file search_agent_state.json
```

**注意**：CLI 后端 (`lib/*.py`) 的搜索方法目前是 mock 数据示例。Codex 原生流程才能取到真实搜索结果（通过内置的 realtime_search 工具 + Firecrawl 脚本 + 外部 skill）。

## 卸载

```bash
bash uninstall.sh
```

## 快速排错

**Q：`install.sh` 报 git clone 失败？**
A：检查网络能否访问 github.com。如果内网需配代理：`git config --global http.proxy http://your-proxy`。

**Q：Codex 里找不到 search-agent skill？**
A：确认 `~/.codex/skills/search-agent/SKILL.md` 存在。Codex 会自动扫描该目录。

**Q：Firecrawl 返回 401 未授权？**
A：默认 key 可能已过期或额度用完。到 [firecrawl.dev](https://firecrawl.dev) 注册免费账号，把新 key 写入 `~/.zshrc` 的 `FIRECRAWL_API_KEY`。

**Q：安装时提示 permission denied？**
A：`chmod +x install.sh` 后重试。

**Q：想装到 Claude Code 而不是 Codex？**
A：`TARGET_DIR=~/.claude/skills bash install.sh`

## 支持的调研场景（示例）

- **财报快评**："帮我快速看看百度 2026Q2 财报"
- **投资判断**："宁德时代值不值得投"
- **竞品对比**："对比拼多多和淘宝的下沉市场"
- **行业调研**："AI 编程助手赛道 2026 年格局"
- **营销策略**："SaaS 定价怎么设计"
- **估值判断**："英伟达当前估值合理吗"
- **风险评估**："某某公司有没有暴雷风险"
- **单一数字快查**："英伟达最新市值"（会直接调 finance/yfinance-data 短路返回）

## 项目结构

```
search-agent-skill3.0/
├── SKILL.md                        # Codex 主入口 prompt
├── README.md                       # 本文件
├── install.sh                      # 一键安装脚本
├── uninstall.sh
├── .env.example                    # 环境变量示例
├── CHANGELOG.md
├── CLAUDE.md                       # 原始 Claude 版（参考）
├── requirements.txt
├── references/
│   ├── frameworks.md               # 31 分析框架
│   ├── external-skills.md          # 外部 skill 挂载矩阵
│   └── workflow.md                 # Mermaid 流程图
├── scripts/
│   └── firecrawl_search.py         # Firecrawl 深度搜索 CLI
├── lib/
│   ├── frameworks.py               # 9 核心框架配置（Python）
│   ├── intent_classifier.py        # 意图识别（Python 后端）
│   ├── framework_combinator.py     # 框架组合推荐
│   ├── search_engine.py            # 多层搜索调度
│   ├── report_generator.py         # 报告生成
│   └── finance-rss-reader/         # 内嵌 65+ 财经/产业/AI 媒体源
├── bin/
│   └── search_agent.py             # Python CLI 编排入口
└── config/
    └── settings.json
```
