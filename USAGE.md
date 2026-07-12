# 搜索调研 Agent 使用指南

Search Agent installs as a **single top-level Skill**. Its 16 **internal specialists** resolve from `specialists/catalog.json`; upstream provenance is pinned in `specialists/vendor.lock.json`. Update manually with `git pull origin main` then `bash install.sh`. Specialist output still passes Citation Audit and every T1-T9 gate.

**适用场景**：竞品新功能调研 / 行业趋势追踪 / 用户需求分析 / GTM 与营销策略研究
**适用团队**：百度地图团队

---

## 一、概览

本文档帮助你上手 `search-agent`，掌握从提需求到交付报告的全流程。

整个流程共 **9 个阶段**，你负责判断与确认，Codex 负责重复性执行，关键节点有**确认闸门**保证质量。

```
T1  需求理解 & 框架审核
     ↓  ⛳ 你确认框架 / 视角 / 关键词
T2  多源分层信息检索
     ↓  ⛳ 数字冲突时你选口径
T3  结构化分析与引文审计
     ↓
T4  生成 3 套候选大纲 + Codex 推荐 1 套
     ↓
T5  你选择、组合或修改大纲
     ↓  ⛳ 你明确确认最终大纲
T6  严格按 ApprovedOutline 扩写深度正文
     ↓
T7  大纲一致性审核 + 引文审核 + 去 AI 味
     ↓
T8  人工终审 & 修订（最多 3 轮）
     ↓  ⛳ 修订涉及结构或新事实时你确认
T9  终稿确认 & 后续行动（可选）
```

---

## 二、快速开始

### 部署（一次性）

Codex 已经识别到 skill：`~/.codex/skills/search-agent`（软链到本地开发目录）。同事第一次用只需：

```bash
git clone git@github.com:wwshuyu29-wq/search-agent.git ~/.codex/skills/search-agent
cd ~/.codex/skills/search-agent
export FIRECRAWL_API_KEY="你的 Firecrawl API Key"   # 写进 ~/.zshrc，不要提交到 GitHub
scripts/bootstrap_python311.sh
source .venv/bin/activate
```

不要直接用系统 `python3` 创建环境。macOS 自带的 `python3` 常见是 3.9.x，网络库会出现 LibreSSL 兼容警告；生产调研统一用 Python 3.11+。

### 跑前检查（每台机器先跑一次）

正式调研前先执行 doctor，确认 Firecrawl、RSS、news-aggregator、agent-reach / opencli 等多平台工具是否可用：

```bash
cd ~/.codex/skills/search-agent
python3 scripts/search_agent_doctor.py
```

典型输出解释：

| 状态 | 含义 | 处理 |
|---|---|---|
| `[OK] news-aggregator script` | 8 大热榜扫描脚本可用 | 可跑 Layer 5 热榜 |
| `[WARN] Python runtime` | 当前运行 doctor 的 Python 低于 3.11 | 执行 `scripts/bootstrap_python311.sh` 后 `source .venv/bin/activate` |
| `[OK] Python 3.11 command` | 机器上能找到 Python 3.11 | 用它创建项目 `.venv` |
| `[WARN] FIRECRAWL_API_KEY` | Firecrawl 脚本在，但缺 API key | 写入 `~/.zshrc` 后 `source ~/.zshrc` |
| `[WARN] agent-reach command` | 小红书 / B站 / Reddit 等平台路由器不在 PATH | 安装或改用 `site:` 搜索兜底 |
| `[WARN] opencli browser bridge` | `opencli` 命令已装，但 Chrome 扩展未连接 | 安装/启用 OpenCLI Chrome 扩展，保持 Chrome 打开后重跑 `opencli doctor` |
| `[OK] RSS Firecrawl path` | RSS 内部调用 Firecrawl 的路径正确 | 无需处理 |

UGC / 社交平台工具链建议一次性安装：

```bash
# Agent Reach 本体（需要 Python 3.10+）
python3.11 -m venv ~/.agent-reach-venv
~/.agent-reach-venv/bin/python -m pip install "https://github.com/Panniantong/agent-reach/archive/main.zip"
ln -sf ~/.agent-reach-venv/bin/agent-reach ~/.local/bin/agent-reach

# 全网语义搜索 + 浏览器登录态渠道 + B站 CLI
npm install -g mcporter @jackwener/opencli
ln -sf ~/.hermes/node/bin/mcporter ~/.local/bin/mcporter
ln -sf ~/.hermes/node/bin/opencli ~/.local/bin/opencli
~/.agent-reach-venv/bin/python -m pip install bilibili-cli yt-dlp
ln -sf ~/.agent-reach-venv/bin/bili ~/.local/bin/bili
ln -sf ~/.agent-reach-venv/bin/yt-dlp ~/.local/bin/yt-dlp

# Exa 搜索后端
mcporter config add exa https://mcp.exa.ai/mcp

# OpenCLI 还需要手动安装/启用 Chrome 扩展，再验证
opencli doctor
agent-reach doctor --json
```

需要真实探测热榜接口时加 `--live`：

```bash
python scripts/search_agent_doctor.py --live
```

### 多 agent workflow 自检

doctor 检查的是工具环境；workflow dry-run 检查的是多 agent 编排本身是否能跑通。它不联网、不产出真实业务结论，只验证每个子 agent 的 artifact、schema 和 gate 是否能从 Step 0 一路走到 FinalReport。

```bash
python bin/search_agent.py "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示" --workflow-dry-run
```

看到 `Multi-Agent Workflow Dry Run`、`status: complete`、所有 artifact validations 都是 `ok`，说明本地多 agent 骨架是自洽的。

正式状态机由 SourceList Merger 合并并验证：`SourceListFragment → RawSourceList/MergerLog → Source QA → ClaimGraph → CitationAudit/ApprovedClaimGraph → OutlinePlan → 用户批准的 ApprovedOutline → ReportDraft → OutlineComplianceReview(passed) → HumanizerChangeLog/FinalReport → IntegrityDiff(passed) → final_report_review`。普通 CLI 不得把原搜索内容直接标成 audit passed；方法型来源不能支撑市场事实。也就是说，Source Hunter 结果不会直接进分析，必须先经过合并、去重、QA、引用审计和 Humanizer 完整性检查。

### 什么叫"真实检索竖切"

`dry-run` 只证明流程骨架能跑通，里面的来源是占位样例；它像是在检查"流水线每个工位有没有接上电"。

`真实检索竖切` 是先选一条最短但完整的真实链路跑通：从 `SearchPlan` 里拿一个子 agent 的检索任务，调用真实检索工具，拿到网页/文章结果，再标准化成 `SourceListFragment` 写回状态文件。它暂时不要求六个检索子 agent 全部完美，但要求其中一条真的能拿资料、能落 artifact、能被下一步合并和 QA 使用。

现在已经接入两条竖切：

1. `SearchPlan → Official/Media/... Source Hunter → Firecrawl 检索适配器 → SourceListFragment`
2. `SearchPlan → RSS/News Hunter → finance-rss-reader → SourceListFragment`

第一条需要 `FIRECRAWL_API_KEY`；如果没配置，命令会明确标记 `skipped_missing_tool_config`，不会伪造来源。第二条走项目内置 `finance-rss-reader` 脚本，不依赖 Firecrawl key，适合验证“不是所有 Source Hunter 都走同一个通用网页搜索”。

在正式状态机生成 `SearchPlan` 后，可以执行某个检索子 agent：

```bash
python bin/search_agent.py --execute-source-hunter official_source_hunter --state-file search_agent_state.json --limit-per-query 5
```

执行 RSS/News Hunter：

```bash
SEARCH_AGENT_RSS_MAX_SOURCES=5 python bin/search_agent.py --execute-source-hunter rss_news_hunter --state-file search_agent_state.json --limit-per-query 5
```

`SEARCH_AGENT_RSS_MAX_SOURCES` 是本地调试限速用的；正式跑可以不设置，让 RSS 脚本扫描完整来源池。

一次执行全部 Source Hunter：

```bash
SEARCH_AGENT_RSS_MAX_SOURCES=5 python bin/search_agent.py --execute-source-hunters --state-file search_agent_state.json --limit-per-query 5
```

Source Hunter 写回真实 `SourceListFragment` 后，继续进入合并、QA、分析和报告：

```bash
python bin/search_agent.py --workflow-continue-from-sources --state-file search_agent_state.json
```

当前真实工具路由：

| Source Hunter | 真实执行入口 | 配置要求 |
|---|---|---|
| `official_source_hunter` | Firecrawl 搜索/抓取 | `FIRECRAWL_API_KEY` |
| `media_source_hunter` | Firecrawl 搜索/抓取 | `FIRECRAWL_API_KEY` |
| `rss_news_hunter` | `finance-rss-reader/scripts/rss_fetch.py` | 无必需 key；可选 `SEARCH_AGENT_RSS_MAX_SOURCES` |
| `ugc_social_hunter` | `bili search ... --json` | 安装 `bili`；其他平台后续通过 agent-reach/opencli 扩展 |
| `finance_data_hunter` | `scripts/yfinance_snapshot.py` + `yc-reader` + Funda/opencli setup adapters | `pip install -r requirements.txt`；Funda/opencli 按需配置 |
| `marketing_intelligence_hunter` | 本地 marketing skill catalog | 无必需 key；输出 method source，不当作市场事实 |

常用 hunter id：

| hunter_id | 负责内容 |
|---|---|
| `official_source_hunter` | 官网、公告、IR、监管披露等一手来源 |
| `media_source_hunter` | 媒体报道、深度分析、行业文章 |
| `rss_news_hunter` | RSS/快讯/新闻聚合信号 |
| `ugc_social_hunter` | 社交平台、社区、B 站、小红书等用户声音 |
| `finance_data_hunter` | 财务、行情、估值、结构化金融数据 |
| `marketing_intelligence_hunter` | 营销、渠道、用户、竞品投放和市场信号 |

想查看每个子 agent 的推进逻辑：

```bash
python bin/search_agent.py --workflow-playbook
```

如果要讨论子 Agent 边界、B站/社媒卡点或报告模板，优先看：

- `references/team-workflow-guide.md`
- `references/node-playbook.md`
- `references/social-ugc-policy.md`
- `references/report-templates.md`

想查看每个节点能调用哪些 skill/tool、怎么调用、产物能不能当证据：

```bash
python bin/search_agent.py --skill-registry
```

想盘点本地营销、金融、写作、Superpowers skill 哪些已接入 workflow、哪些还只是库存：

```bash
python bin/search_agent.py --skill-coverage
```

想看每个细分营销/金融 skill 为什么被拿来用、适配哪个节点、怎么用、产出什么 artifact：

```bash
python bin/search_agent.py --skill-adapter-matrix marketing
python bin/search_agent.py --skill-adapter-matrix finance
```

想确认 Codex 里 LLM 到底怎么被调用：

```bash
python bin/search_agent.py --codex-execution
```

Codex 里不需要为节点 LLM 另配 OpenAI API Key；Codex 当前会话就是节点 LLM 执行环境。每个子 agent 都会被渲染成一份节点 prompt、artifact schema 和质量 gate，由 Codex 按顺序执行判断；Firecrawl、RSS、agent-reach、opencli 等外部检索工具才需要各自的环境配置。

正式 gate-driven workflow 和 dry-run 不一样：dry-run 用来验证骨架，会一路跑到 FinalReport；正式流程必须先输出审核卡，等你确认后再继续。

```bash
python bin/search_agent.py "高德地图最近三个月上新，对百度地图市场组有什么启示" --workflow-start --state-file search_agent_state.json
python bin/search_agent.py --workflow-resume 确认 --state-file search_agent_state.json
python bin/search_agent.py --workflow-resume 通过 --state-file search_agent_state.json
```

如果需要查看某个阶段实际会创建哪些子 Agent、每个子 Agent 的 prompt、工具约束和输出 artifact，可以导出 node packets：

```bash
python bin/search_agent.py --workflow-packets step1_parallel_source_hunting --state-file search_agent_state.json
```

Source QA 发现数字冲突、关键证据缺口或来源口径不一致时，会把状态停在 `source_qa_conflict_resolution`，不会继续进入 Framework Analyst。你需要回复采用哪个口径，或要求补充哪个来源后再继续。

### 提示词怎么写

在 Codex 里使用时，不需要在提示词里手动写"请使用 sub agent"。只要明确写 `用 search-agent`，Codex 就应该按 `SKILL.md` 读取多 agent workflow、先输出审核卡、确认后再继续。

推荐写法：

```
用 search-agent 帮我调研高德地图最近三个月上了什么新功能，
面向百度地图市场组，先输出审核卡，等我确认后再继续。
```

如果你想强制 Codex 不要偷懒，可以加一句：

```
严格按多 agent workflow 执行：Intent Router 先判断意图，
确认后再进入 Search Planner 和各 Source Hunter。
```

### 常用触发模板

直接复制发给 Codex，替换括号内容即可启动：

```
# 竞品新功能追踪
用 search-agent 帮我查一下【竞品名】最近三个月上了什么新功能，
重点看【功能 A】、【功能 B】，输出对比表。

# 用户需求挖掘
用 search-agent 从 JTBD 视角挖一下【用户群体】在地图里的核心任务和痛点，UGC 优先。

# 立项前市场调研
用 search-agent 帮我调研【功能方向】这个方向，全球做得好的有哪些，
用 PEST + 3C + STP 组合，重点看技术成熟度和用户接受度。

# 品牌力对比
用 search-agent 对比【我方】vs【竞品 A】vs【竞品 B】的品牌力，
用 CBBE + Customer Journey 组合。

# 实时热点扫描
用 search-agent 扫一下最近 48 小时【领域】相关的社交讨论和媒体报道。
```

---

## 三、各阶段详细说明

### T1 · 需求理解 & 框架审核

**目标**：把你的一句话需求，转化成"用哪个框架 + 拆哪些维度 + 搜哪些关键词 + 从哪些源找"。

底层执行遵守 `references/agent-nodes.md`：先由 LLM 语义理解层判断真实业务决策，再触发专家 skill 前置探针，最后才用规则/关键词分类器和框架组合器做校验。`marketing-ideas`、`marketing-plan`、`startup-analysis`、`yfinance-data/funda-data` 在命中场景时会先参与 Step 0，而不是等到报告后才使用。

#### 你需要做什么

1. 告诉 Codex 你的调研需求（一句话即可）
2. 查看 Codex 输出的**审核卡片**，确认或修改：
   - 分析框架（如"竞品对比 + JTBD + Porter 五力"）
   - 拆解维度（如功能矩阵 / 用户口碑 / 商业化路径）
   - 搜索关键词（Codex 会自动扩展词族）
   - 信息源（应用商店 / 官方 Blog / 中文媒体 / UGC 等）
3. 回复"确认"或"改成 XX"

> ⚠️ **闸门①（必须完成）**：未回复确认前，Codex 不会启动检索。

#### 框架自动路由规则

skill 内置 **31 个框架**（战略 12 + 营销 9 + 金融 10），Codex 会根据你的问题自动路由。

**产品/竞品调研常用（默认场景）：**

| 你的问题 | 默认框架 |
|---|---|
| XX 上了什么新功能 | 竞品对比 + JTBD |
| 行业发展到哪一步 | PEST + Porter 五力 |
| 用户为什么用 XX 不用我们 | JTBD + CBBE + Customer Journey |
| XX 是怎么做增长的 | AARRR + 3C |
| 新功能立项要看什么 | 3C + STP + JTBD + PEST |
| XX 品牌力 / 口碑 | CBBE + Customer Journey |
| XX 的商业化 / 变现 | 4P/7P + 商业模式画布 |
| XX 的 GTM / 传播 | STP + 4P + AIDA |

**战略与竞争分析：**

| 你的问题 | 默认框架 |
|---|---|
| XX 整体怎么样 / 值不值得合作 | SWOT |
| XX 哪些业务值得押注 / 砍掉 | BCG 波士顿矩阵 |
| 多业务集团精细化管理 | GE 麦肯锡矩阵 |
| XX 组织能力 / 执行力 | 麦肯锡 7S |
| XX 的价值创造在哪一环 | Porter 价值链 |
| XX 如何差异化 / 新品类 | 蓝海战略 ERRC |
| XX 怎么增长 / 扩张 | Ansoff 增长矩阵 |

**营销与用户分析（其他）：**

| 你的问题 | 默认框架 |
|---|---|
| XX 用户分层 / 高价值客户 | RFM |
| XX 广告效果 / 认知路径 | AIDA |
| SaaS / 服务型企业营销 | 7P |

**金融与估值分析：**

| 你的问题 | 默认框架 |
|---|---|
| 快看 XX 的 Q1/Q3 财报 | 财报快评（KPI 树 + 空-雨-伞）|
| XX 值不值得投 / 经营质量 | 深度财报分析 |
| XX 的 ROE 从哪来 | 杜邦分析 |
| XX 财务健康 / 偿债能力 | 财务比率四维 |
| XX 值多少钱 / 合理估值 | DCF 现金流折现 |
| XX 贵不贵 / 估值分位 | 相对估值倍数（P/E·P/B·PEG）|
| XX 有护城河吗 | 巴菲特护城河 |
| XX 利润有水分吗 | 现金流质量 + Beneish M |
| XX 会不会暴雷 | Altman Z-Score |
| XX 值不值得授信 / 供应商合作 | 5C 信贷分析 |
| XX 有什么风险 / 隐患 | 风险专项 + SWOT 决策矩阵 |
| XX 的 Q1 收入是多少（单一数字）| 直接搜索，跳过框架流程 |

> 完整框架定义（视角、维度、搜索关键词模板、质量红线）见 `references/frameworks.md`。混合题（金融 × 营销）会请你选视角（投资 / 经营 / 新业务）。

#### 关键词自动扩展（地图领域）

- "AR 导航" → AR Navigation, LiveView, 实景导航, 步行 AR
- "车道级" → Lane-level, HD Map, 高精地图, HDLive
- "打车" → Ride-hailing, 网约车, 滴滴, T3, 一键打车
- "车机" → IVI, HUD, CarPlay, Android Auto, 鸿蒙座舱

---

### T2 · 多源分层信息检索

**目标**：按"官方 → 深度媒体 → UGC → 应用商店 → 热榜/RSS → 内网"六层并行抓取，确保信息置信度有据可查。

#### 六层信息源说明

| 层级 | 信息源 | 置信度 | 说明 |
|---|---|---|---|
| Layer 1 | 竞品官网 / 官方 Blog / App Store 更新历史 | 最高 | 第一手信息 |
| Layer 2 | 36氪 / 晚点 / 极客公园 / TechCrunch | 高 | 深度媒体报道 |
| Layer 3 | 微博 / 小红书 / B站 / 知乎 / Reddit | 低（情绪参考）| UGC 用户口碑 |
| Layer 4 | App Annie / 七麦数据 / 应用商店评分 | 中 | 市场数据 |
| Layer 5 | 51 个财经 RSS 源 + 8 大热榜 | 中 | 行业动态实时 |
| Layer 6 | 百度内网研究报告 | 高（内部资产）| 优先查阅 |

#### 每层用什么工具抓

| 层级 | 主要工具 | 为什么用它 |
|---|---|---|
| Layer 1 | firecrawl_search.py + realtime-search | 官方页面多是 JS 渲染 + 反爬，Firecrawl 有 IP 池能穿过 |
| Layer 2 | firecrawl_search.py + realtime-search（百度）| 中英文深度媒体都能覆盖 |
| Layer 3 | agent-reach（小红书 / B站 / Reddit / 知乎）| 这些平台没有原生 RSS，只有 agent-reach 能定向抓 |
| Layer 4 | firecrawl_search.py | 应用商店页面动态渲染 |
| Layer 5 | finance-rss-reader（51 源）+ news-aggregator-skill（8 热榜）| RSS 并发抓取 + 热榜直连内部 API，比 RSSHub 快 5× |
| Layer 6 | enterprise-search + ku-doc-manage | 内网数据 confidence=high，能省一半调研时间 |

**补充专家 skill：**
- `marketing/competitor-profiling` — 强制竞对档案 12 字段清单，防漏项
- `marketing/customer-research` — 内置 JTBD 访谈脚本 + 用户画像模板
- `marketing/directory-submissions` — Product Hunt / G2 / Capterra 情报

#### 你需要做什么

- 通常无需操作，等待 Codex 汇总
- 若出现数字冲突（两个源数据对不上），Codex 会暂停并请你选择采信哪个口径

> ⚠️ **闸门（条件触发）**：数字冲突或缺关键源时暂停，请你选口径后继续。

#### 注意事项

- **UGC 内容**（小红书 / 微博等）只作情绪信号，置信度标注为 `low`，不可作为事实断言
- **关键数字**必须附口径、时间点、来源（如"高德 MAU 4.5 亿，来源 2025 年官方财报"）

---

### T3 · 结构化分析

**目标**：把检索到的资料按框架维度重新组织，每条结论挂 source_id，区分事实 / 计算 / 假设 / 判断。

#### 四类结论的区别

| 类型 | 定义 | 示例 |
|---|---|---|
| **事实** | 来自官方文件，可直接引用 | "高德 MAU 4.5 亿（2025 官方财报）" |
| **计算** | 基于数据推算，可复算 | "财报数字 × 增长率估算下季度" |
| **假设** | 参考市场规模反推，可能有偏差 | "参考行业均值估算渗透率" |
| **判断** | 基于综合分析的主观结论，需支撑 | "领先百度地图约 20%（综合多项指标）" |

**为什么要区分？** 不区分的报告让读者无法判断哪些是硬事实、哪些是推断，容易误导决策。

#### 常见框架分析示例

- **竞品对比**：三栏对比表（我方 / 竞品 A / 竞品 B）× 功能 / 口碑 / 商业化 / 迭代节奏
- **JTBD**：每个用户任务写成"当 [情境] 时，我想 [动机]，以便 [预期结果]"
- **AARRR**：5 环节转化率 + LTV / CAC 健康度
- **CBBE**：4 层品牌资产金字塔 + 每层量化指标
- **Porter 五力**：每一力给出强度评级 + ≥2 条依据
- **PEST**：四维各 200-300 字 + ≥1 条量化数据

#### 这一步用到的 skill

| Skill | 强制走什么专家动作 |
|---|---|
| marketing/customer-research | JTBD 陈述必须走"当[情境]时，我想[动机]，以便[结果]"句式 |
| marketing/competitor-profiling | 竞品档案 12 字段清单必查 |
| marketing/product-marketing / pricing | 4P 各维度分析清单 |
| marketing/analytics + ab-testing | Customer Journey / AARRR 转化率公式 |

---

### T4 · 生成 3 套候选大纲

**目标**：在写正文前先决定“这篇报告按什么逻辑讲”，避免所有报告都套倒金字塔。

Codex 默认给出 3 套差异化大纲：

| 大纲类型 | 写作逻辑 | 适合场景 |
|---|---|---|
| **A 全景对比型** | 事实全景 → 维度对比 → 用户反馈 → 差距 → 我方行动 | 竞品功能盘点、横向比较 |
| **B 因果深挖型** | 现象 → 成因 → 机制 → 影响 → 战略含义 | 专题研究、解释“为什么” |
| **C 行动决策型** | 决策问题 → 选项 → 取舍 → 行动 → 验证 | 立项、管理层决策；可用倒金字塔 |

每套大纲都会写明：目标读者、推荐理由、优点与限制、章节顺序、每章分析目的、证据槽位和字数预算。

**Codex 会推荐吗？** 会。Codex 根据读者、决策目标和证据深度标出“推荐大纲”及理由；但推荐只是建议，最终由你选择。

### T5 · 你选择并确认大纲

**你可以这样回复：**

- “选择推荐的 A，大纲确认”
- “我选 B，但把第 4 节移到第 2 节”
- “以 A 为主，合并 B 的‘核心机制’章节”
- “三套都不合适，按以下章节重写……”

> ⚠️ **强制闸门**：只有你明确确认后，系统才生成 `ApprovedOutline`。未确认时 Codex 不能开始正文。

确认后，一级标题、顺序、每章目的和证据槽位成为结构契约。后续如需改结构，必须再次请你确认。

### T6 · 按已确认大纲扩写深度正文

**目标**：用户选择什么结构，最终正文就按什么结构展开。

Report Writer 必须：

1. 严格按 `ApprovedOutline` 的章节顺序写；
2. 每章完成大纲中约定的分析目的；
3. 使用该章绑定的 Claim 与 source_id；
4. 按字数预算展开深度论证；
5. 不擅自增加、删除、改名或调换一级章节；
6. 证据不足时标 `[待补证据]`，不能用套话凑字数。

倒金字塔不再是统一格式。只有当你选择“行动决策型”时才通常结论先行；因果深挖型和全景对比型按各自逻辑展开。

### T7 · 大纲一致性审核 + 去 AI 味

Codex 自动检查：

- 所有章节是否存在且顺序一致；
- 是否出现未经确认的新一级章节；
- 每章是否完成原定目的；
- 必需证据是否进入正文；
- 引文是否真实支持结论；
- 篇幅是否明显失衡。

任一结构项失败，自动退回 Writer 修订。通过后才运行 `humanizer-zh`，且去 AI 味不得改变事实、数字、引文和大纲结构。

### T8 · 人工终审 & 修订

**目标**：修正 AI 幻觉与视角错位，让报告真正服务于你的团队决策。

#### 两类必须人工校验的问题

| 问题类型 | 表现 | 如何发现 |
|---|---|---|
| **AI 幻觉** | 编造了没有出现在源里的数字或"某某报告显示" | 对照参考文献表逐条抽查 |
| **视角错位** | 中立视角写"高德 vs 百度地图"，但你需要"百度地图团队的启示" | 判断"对我们有没有用" |

#### 如何提修订意见

✅ **好的意见（具体可执行）**：
- "竞品对比表少了 Waze 的语音社交功能"
- "把'用户不满意导航语音'改成'待验证'，只有一个源"
- "加一段：如果我们跟进这个功能，需要哪些前置资源"

❌ **不好的意见（太模糊）**：
- "改得更好一点"
- "再详细些"

#### 修订规则

- 最多 **3 轮**修订
- 超过 3 轮说明 T1 框架或 T2 信息源有根本问题，应往回退重做
- Codex 只按修订清单执行，不擅自改动其他部分

#### 这一步用到的 skill

| Skill | 作用 |
|---|---|
| verification-before-completion | 声称"改完了"前强制核查：所有 must_fix 是否都改了、是否引入新的无源事实 |
| copy-editing | 修订后过一遍编辑审查（Key Message 一致性、事实可追溯性）|
| humanizer-zh | 修订后再次去 AI 味 |

> ⚠️ **闸门（条件触发）**：修订计划中若需要新事实或存在冲突，Codex 暂停请你确认。

---

### T9 · 终稿确认 & 后续行动（可选）

**目标**：把调研报告转化为可执行产物，避免"报告做完烂在文件夹里"。

#### 常用后续行动

| 你说 | Codex 输出 | 内置什么 |
|---|---|---|
| 写个新功能立项 Brief | 立项模板 | 目标 / 用户 / 竞品 / 关键指标 / 资源 / 时间线 |
| 起一个 PR 稿 | PR 三段结构 | Hook / 事实 / 引语 + 记者语气 |
| 帮我起社交传播文案 | 微博 / 小红书 / B 站适配版本 | 各平台字数上限 + hashtag 规范 |
| 做落地页文案 | 转化型文案 | AIDA 结构 + CRO checklist |
| 写 KOL 投放脚本 | 短视频脚本 | 3 秒 hook 黄金法则 + 脚本节奏 |
| 做用户访谈提纲 | 访谈脚本 | JTBD 5 问 + 追问模板 |
| 起竞品监控周报模板 | 周报模板 | 每周 checklist + 变更对比表 |
| 输出对外分享稿 | 润色版报告 | Copy-editing + 去 AI 味 |

---

## 四、核心规则（必读）

1. **框架先于搜索** — 未确认框架前不启动检索
2. **官方源优先** — 竞品官网 / release note > 深度媒体 > UGC 口碑
3. **引文透明** — 每条结论绑 source_id + 可跳转 URL
4. **区分事实 / 计算 / 假设 / 判断**
5. **≥2 源交叉验证** — 单源关键结论标"待验证"
6. **UGC 只作情绪信号** — 置信度 low，不作事实断言
7. **数字规范** — DAU / MAU 等必附口径、时间点、来源
8. **两个闸门不可省** — 框架审核 + 引文校验
9. **修订上限 3 轮** — 超过退回 T1/T2 重做
10. **终稿必须你确认** — Codex 不自动归档

---

## 五、附录

### 5.1 所有闸门汇总

| 闸门 | 触发条件 | 你需要做什么 |
|---|---|---|
| T1 框架确认 | Codex 输出审核卡片 | 回复"确认"或修改 |
| T1 视角选择 | 金融 × 营销混合题 | 选投资 / 经营 / 新业务视角 |
| T2 来源冲突 | 数字或事实对不上 | 指定采信口径 |
| T5 大纲确认 | 3 套候选大纲输出后 | 选择推荐项、其他候选，或组合/修改后明确确认 |
| T7 结构/引文校验 | 正文输出后 | 查看自动审核结果 |
| T8 修订冲突 | 需要改结构、新事实或意见冲突 | 重新确认大纲或补哪份资料 |
| T9 终稿确认 | 归档前 | 明确回复通过 |

### 5.2 CLI 备用（脚本党）

Codex prompt 走不通时可以纯 CLI：

```bash
cd ~/.codex/skills/search-agent
python3 bin/search_agent.py "高德地图 2026 上半年新功能盘点"           # 交互式（有审核点）
python3 bin/search_agent.py "高德地图 2026 上半年新功能盘点" --auto    # 自动模式（跳过审核点①）
python3 bin/search_agent.py "高德地图 2026 上半年新功能盘点" --workflow-dry-run
python3 bin/search_agent.py "高德地图 2026 上半年新功能盘点" --workflow-start --state-file search_agent_state.json
python3 bin/search_agent.py --workflow-resume 确认 --state-file search_agent_state.json
python3 bin/search_agent.py --workflow-packets step1_parallel_source_hunting --state-file search_agent_state.json
python3 bin/search_agent.py --execute-source-hunters --state-file search_agent_state.json --limit-per-query 5
python3 bin/search_agent.py --workflow-continue-from-sources --state-file search_agent_state.json
python3 bin/search_agent.py --skill-registry
python3 bin/search_agent.py --skill-coverage
python3 bin/search_agent.py --skill-adapter-matrix marketing
python3 bin/search_agent.py --skill-adapter-matrix finance
python3 bin/search_agent.py --workflow-playbook
python3 bin/search_agent.py --codex-execution
```

⚠️ CLI 自动模式不推荐生产使用——它跳过了框架审核这个人工闸门。

### 5.3 与金融投资场景的区别

skill 内部仍保留 10 个金融框架（DCF / 杜邦 / 护城河 / Altman Z / Beneish M 等）和全套 finance-skills 挂载，遇到"高德要 IPO 值不值得关注"这类混合题也能兜住。但**默认路由已调整**：产品/竞品调研问题不会强推金融框架，只在明确出现"估值 / 值不值得投 / 财报"等信号词时才启用。
