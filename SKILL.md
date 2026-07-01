---
name: search-agent
description: 通用商业调研 skill，覆盖财报分析、竞品研究、行业调研、营销策略、宏观/政策分析、风险评估、估值判断等场景。基于 31 个战略/营销/金融分析框架（PEST / Porter 五力 / 3C / SWOT / 4P / STP / AARRR / JTBD / CBBE / 财报快评 / 深度财报 / 杜邦 / DCF / 相对估值 / 护城河 / Altman Z / Beneish M / 风险专项 等）驱动多源分层搜索（Firecrawl + realtime-search + baidu-search + enterprise-search + 财经 RSS），输出带引文可跳转的金字塔结构调研报告。
---

# Search Agent 智能分析系统

一个基于**多源分层搜索**与**结构化分析框架**的通用调研工具。根据用户问题自动识别分析场景，从 31 种商业分析框架（战略 / 营销 / 金融）中推荐 Top 3，经人工审核后执行多源并行搜索、多格式内容处理，最终生成带引文链接的金字塔结构专业报告。

## 核心能力

1. **智能意图识别**：自动识别用户问题类型，从 31 种经典分析框架中推荐 Top 3（含 9 个核心框架 + 12 个战略框架 + 9 个营销框架 + 9 个金融框架，见 `references/frameworks.md`）
2. **人工审核机制**：框架选择需人工确认（审核点 ①），报告输出前可校验引文/结论（审核点 ②），确保分析方向准确
3. **多源分层搜索**：整合 Firecrawl（英文深度）、realtime-search（Brave 官方 + 百度中文）、baidu-search、enterprise-search（内网）、finance-rss-reader（35 个财经 RSS 源），按置信度 5 层分层调用
4. **多格式内容处理**：支持 PDF（OCR）、HTML 正文提取、知识库文档（ku-doc-manage）、URL 全文抓取
5. **结构化报告生成**：按框架维度生成金字塔结构 Markdown 报告，**结论先行 + 每个关键论断附引文链接**，末尾附可跳转的参考文献表
6. **可扩展框架库**：内置 31 种框架，可根据需求轻松扩展；支持 10+ 种预定义框架组合（如"全面战略组合""投资判断组合""风险扫描组合"）

## 支持的分析框架

**框架 = search-agent 的编排大脑；外部专家 skill = 每个节点的垂直加速器。**
完整的外部 skill 挂载矩阵（营销 44 个 + 金融 20+ 个）见 `references/external-skills.md`——它按 Step 0/1/2/3 每个节点列清了何时调用哪个专家 skill 来增强产出。

### 战略与竞争分析

| 框架 | 适用场景 | 模型深度 |
|---|---|---|
| ★ 财报快评 | 快速了解公司季度/年度财报 | Sonnet |
| ★ 深度财报分析 | 投资/经营判断、尽职调查 | Opus |
| ★ 同行竞争对比 | 竞品分析、行业研究 | Opus |
| ★ PEST | 宏观环境分析、行业趋势 | Opus |
| ★ Porter 五力 | 竞争格局、进入壁垒评估 | Opus |
| ★ SWOT | 战略规划、综合评估 | Sonnet |
| ★ 3C 战略三角 | 市场定位、商业模式 | Opus |
| Ansoff 增长矩阵 | 增长战略选择 | Sonnet |
| BCG 波士顿矩阵 | 业务组合/资源分配 | Sonnet |
| GE 麦肯锡矩阵 | 多业务集团精细化管理 | Opus |
| 麦肯锡 7S | 组织与战略匹配诊断 | Opus |
| Porter 价值链 | 识别价值创造与成本源头 | Opus |
| 蓝海战略 ERRC | 差异化 / 品类创新 | Opus |

### 营销与用户分析

| 框架 | 适用场景 | 模型深度 |
|---|---|---|
| ★ 4P 营销 | 营销组合 / GTM 策略 | Sonnet |
| 7P 服务营销 | SaaS / 服务型企业营销 | Sonnet |
| STP 市场定位 | 市场细分 / 目标市场 / 定位 | Opus |
| AIDA 广告漏斗 | 广告转化 / 品牌认知路径 | Sonnet |
| AARRR 海盗指标 | 用户增长 / 留存 / LTV | Opus |
| RFM 客户价值分层 | 会员运营 / CRM | Sonnet |
| JTBD 待完成的任务 | 用户需求本质 / 痛点 | Opus |
| Keller CBBE | 品牌资产评估 | Opus |
| Customer Journey Map | 用户体验旅程 | Sonnet |

### 金融与估值分析

| 框架 | 适用场景 | 模型深度 |
|---|---|---|
| DuPont 杜邦分析 | ROE 结构分解 | Opus |
| 财务比率四维 | 财务健康度全景 | Sonnet |
| DCF 现金流折现 | 内在价值估值 | Opus |
| 相对估值倍数 | P/E / P/B / EV/EBITDA / PEG 横向对比 | Sonnet |
| 巴菲特护城河 | 长期竞争壁垒 | Opus |
| 现金流质量分析 | 识别财务粉饰 | Opus |
| Beneish M + Piotroski F | 舞弊筛查 / 价值股筛选 | Opus |
| Altman Z-Score | 破产预警 | Sonnet |
| 5C 信贷分析 | 授信 / 供应商评估 | Sonnet |
| ★ 风险专项 | 综合风险评估（决策矩阵） | Opus |

★ = 核心 9 框架，与 `lib/frameworks.py` 内置配置对齐；完整定义、维度、搜索关键词模板、质量红线见 `references/frameworks.md`。

## 工作流程（Step 0 → 1 → 2 → 3）

**每次调研必须严格执行，不得跳步**：

```
用户输入调研需求
    ↓
Step 0：意图识别 & 框架路由
        ↓ 推荐 Top 3 框架（或组合）
        ↓ 输出【审核卡片】
        ↓
    【人工审核 ①】⏸ 等待用户确认框架
        ↓ 用户确认后
Step 1：多源分层信息检索（5 层）
        ↓ Layer 1 官方 → Layer 2 业绩会 → Layer 3 深度分析 → Layer 4 中文媒体 → Layer 5 RSS
        ↓ 内容抓取（PDF OCR / HTML / 知识库 / URL fetch）
        ↓ 输出 YAML 信息源清单（source_id + confidence + key_facts + 原文链接）
        ↓
Step 2：结构化分析
        ↓ 按框架子维度组织内容
        ↓ 每条结论标注 source_id，区分事实/计算/假设/判断
        ↓ 关键数字 ≥2 源交叉验证
        ↓
Step 3：金字塔调研报告生成
        ↓ 核心结论先行 + 支撑理由 + 主要风险
        ↓ 按框架维度展开正文
        ↓ 风险与不确定性表格 + 参考文献表（原文可跳转）
        ↓
    【人工审核 ②】⏸ 校验引文和结论
        ↓
输出最终报告（保存到 config.output_dir）
```

---

## Step 0：意图识别 & 框架路由

收到用户 query 后**立即执行**，不跳过，不假设，不提前开始搜索。

### 外部 skill 前置（可选）

在进入内置意图分类前，遇到以下情况**先调外部 skill**：
- 用户说"帮我想想 / 灵感 / 不知道选什么"（营销类）→ 调 `marketing/marketing-ideas` 生成方向列表
- 用户想要"完整营销方案骨架" → 调 `marketing/marketing-plan`
- 用户询问"值不值得加入创业公司 / VC 视角" → 调 `finance-skills/startup-analysis`
- 单一数字快查（"XX 现价"、"XX 最新市值"）→ 直接调 `finance-skills/yfinance-data` 或 `finance-skills/funda-data`，**跳过后续所有 Step**

### 流程

1. **判断复杂度**：命中"全面 / 系统 / 多维度 / 深入 / 综合"或问题长度 > 50 字 → 复杂问题，考虑推荐**框架组合**
2. **查询路由表**（见 `references/frameworks.md` 第一节），根据用户意图选主框架
3. **应用引导性扩框规则**（意图单一时主动建议叠加一个补框架）
4. **输出【审核卡片】并停下**，等用户回复"确认"或修改意见

### 框架路由（速查）

| 意图 | 推荐主框架 |
|---|---|
| 快速财报 | 财报快评 |
| 深度经营分析 / 投资判断 | 深度财报分析 (+ 杜邦 + 护城河 + DCF/相对估值) |
| 竞品对比 | 同行竞争对比 (+ 3C + Porter 五力) |
| 宏观 / 政策 / 行业趋势 | PEST |
| 竞争格局 / 进入壁垒 | Porter 五力 |
| 综合战略研判 | SWOT |
| 市场定位 / 商业模式 | 3C 战略三角 (+ STP) |
| 营销 / GTM | 4P / 7P (+ STP + AIDA) |
| 用户增长 / 留存 | AARRR (+ RFM + JTBD) |
| 品牌力 / 品牌资产 | CBBE (+ Customer Journey) |
| 估值 | DCF + 相对估值 + 护城河 |
| 财务健康 / 破产预警 | 财务比率四维 + Altman Z |
| 舞弊筛查 | Beneish M + Piotroski F + 现金流质量 |
| 授信 / 合作评估 | 5C 信贷分析 |
| 风险专项 | 风险专项（决策矩阵） |
| 单一数字查询 | 直接搜索，无需框架 |

### 引导性扩框规则（意图单一时主动建议）

- 只问竞争 → 叠加 SWOT
- 只问财报 → 叠加 3C + 杜邦
- 只问营销 → 叠加 PEST + STP
- 只问用户增长 → 叠加 JTBD + RFM
- 只问风险 → 叠加 SWOT 决策矩阵 + Altman Z
- 只问估值 → 叠加 护城河 + 杜邦

### 金融 × 营销混合题识别与路由（关键）

很多真实调研既是金融题也是营销题，例如：
- "拼多多海外 Temu 值不值得投" → 金融（估值/护城河/风险）+ 营销（GTM/AARRR/JTBD）
- "SaaS 公司 IPO 前的增长故事" → 金融（估值倍数/SaaS 压缩）+ 营销（AARRR/LTV/CAC）
- "小米汽车品牌力对股价的影响" → 金融（相对估值/情绪）+ 营销（CBBE/Customer Journey）
- "特斯拉 Cybertruck 上市首季表现" → 金融（earnings-recap）+ 营销（launch/PR/竞对）

**混合题识别信号**：
- query 同时出现 财报/估值/投资 + 营销/品牌/用户/增长 类关键词
- query 涉及"公司战略 + 消费者视角"（如：定价决策、产品发布、市场进入）
- query 关注"业务基本面 → 财务表现"的传导链条

**混合题标准组合（3 种模式）**：

1. **投资视角主导**（用户是投资者/分析师）：
   `深度财报分析 → AARRR → CBBE → 护城河 → DCF/相对估值 → 风险专项`
   Step 2 skill 调用：`finance/earnings-recap` + `finance/company-valuation` + `marketing/customer-research` + `marketing/competitor-profiling`

2. **经营视角主导**（用户是 CEO/CMO/产品经理）：
   `3C → JTBD → STP → 4P/7P → 财务比率四维 → 杜邦分析 → 风险专项`
   Step 2 skill 调用：`marketing/product-marketing` + `marketing/pricing` + `marketing/analytics` + `finance/estimate-analysis`

3. **市场进入/产品发布视角**（新业务评估）：
   `PEST → Porter 五力 → STP → 4P → AARRR → DCF 情景估值 → 风险专项`
   Step 2 skill 调用：`marketing/launch` + `marketing/marketing-plan` + `finance/startup-analysis` + `finance/company-valuation`

**在审核卡片中的呈现方式**（混合题的额外字段）：

```
║ ⚠️ 检测到金融 × 营销混合题
║
║ 你的视角是？（决定框架排序）
║   [A] 投资/分析师视角 → 组合 1（金融为主）
║   [B] 经营/CMO 视角  → 组合 2（营销为主）
║   [C] 新业务评估视角 → 组合 3（双线并重）
║
║ 或告诉我你更关心的具体问题，我会调整框架顺序
```

用户选定视角后，Step 1 检索会**双通道并行**——金融数据源（yfinance / funda / RSS）+ 营销数据源（competitor-profiling / customer-research），YAML 源清单里 FIN### 和 MKT### 混排；Step 2 按选定视角的组合顺序推进，每一步显式标注"这一步用的是金融/营销哪个框架"；Step 3 报告分双板块：**"财务基本面"章节 + "市场/用户"章节 + 综合结论章节**，综合结论必须显式做金融数据与营销数据的**因果对齐**（如"NPS 从 60 涨到 75 → 复购率提升 → LTV 增长 20% → 支撑估值上调 15%"）。

### 审核卡片格式（Step 0 的强制输出）

```
╔══════════════════════════════════════════════╗
║         调研框架方案 — 待您确认              ║
╠══════════════════════════════════════════════╣
║ 调研主题：[识别出的对象]
║ 调研目的：[识别出的核心问题]
║
║ 建议分析框架：[框架名 或 框架组合]
║ 拆解维度：
║   1. [子维度1] → 核心问题：[具体问题]
║   2. [子维度2] → 核心问题：[具体问题]
║   3. [子维度3] → ...
║
║ 搜索关键词（可修改）：
║   中文：[列出中文关键词]
║   英文：[列出英文关键词]
║
║ 信息源范围（默认全开，可勾选）：
║   [x] 官方财报/公告（IR 页面、SEC/交易所披露）
║   [x] 业绩会 Transcript
║   [x] 深度分析（Seeking Alpha / FT / Bloomberg，走 Firecrawl）
║   [x] 中文媒体（36氪 / 财新 / 东方财富，走 realtime-search 百度）
║   [x] 财经 RSS 聚合（Reuters / MarketWatch / 财新 等 35 个源）
║   [ ] 企业内部知识（enterprise-search，仅内网）
║   [ ] 知识库文档（ku-doc-manage）
║
║ 建议补充框架（可选）：[意图单一时给出扩框建议]
╠══════════════════════════════════════════════╣
║ ✅ 直接回复"确认"开始搜索
║ ✏️  或告诉我需要调整的地方（框架、维度、关键词、源范围）
╚══════════════════════════════════════════════╝
```

**关键**：卡片输出后必须停下等待用户回复，不得自行开始 Step 1。

---

## Step 1：多源分层信息检索

用户确认审核卡片后执行。**按置信度分层**调用工具，最终产出统一的 YAML 源清单。

### Layer 6：垂直专家 skill（新增）

除内置 5 层通用搜索外，根据调研主题从外部 skill 直接取结构化数据：

**金融数据源**（补 Layer 1-2 官方数据）
- `finance-skills/yfinance-data` — 美股价格/财务/期权/股息/财报日期
- `finance-skills/funda-data` — 分析师研究合成（MCP + REST 60+ 端点）
- `finance-skills/tradingview-reader` — 完整期权链 + Greeks + IV
- `finance-skills/finance-sentiment` — Reddit / X / 新闻 / Polymarket 情绪
- `finance-skills/hormuz-strait` — 中东地缘/航运/油价风险监控

**营销/竞对数据源**（补 Layer 3-4 深度分析）
- `marketing/competitor-profiling` — 完整竞对档案（定位/GTM/团队/融资）
- `marketing/customer-research` — JTBD 访谈 / 用户画像 / 痛点
- `marketing/directory-submissions` — Product Hunt / G2 / Capterra 情报
- `marketing/public-relations` — HARO / Featured / 记者联系人
- `marketing/prospecting` — B2B 决策链 / 联系人挖掘

**source_id 命名扩展**：`FIN###` = finance-skills 数据，`MKT###` = marketingskills 数据。

完整触发规则见 `references/external-skills.md`。

### 工具矩阵

**工具 1：Firecrawl 深度搜索**（英文深度内容 / JS 渲染 / IR / SEC / Seeking Alpha）

```bash
python3 scripts/firecrawl_search.py --query "<英文关键词>" --limit 5 --lang en
```

- 环境变量：`FIRECRAWL_API_KEY`（示例 key：`fc-a5279d633c4f4636b2592bc31a431770`，仅供本地测试，生产请替换）
- 返回 JSON 数组，字段：`source_id / title / url / description / publish_date / source_type / confidence`
- 适用：Seeking Alpha 分析师报告、FT / Bloomberg / WSJ、公司 IR 官网、SEC / EDGAR 文件

**工具 2：realtime-search（Brave 引擎）**——英文通用 / 官方来源

```bash
skill realtime-search "<英文关键词>" --engine brave --count 5
```

- 适用：官方财报 PDF（配合 `site:ir.company.com filetype:pdf`）、10-K、业绩会 transcript

**工具 3：realtime-search（百度引擎）**——中文内容

```bash
skill realtime-search "<中文关键词>" --engine baidu --count 5 --freshness month
```

- 适用：36氪、财新、东方财富、界面新闻、虎嗅等中文财经媒体

**工具 4：baidu-search**——中文通用兜底

```bash
skill baidu-search --query "<中文关键词>" --num 10
```

- 适用：realtime-search 无结果时的补充；中文百科、贴吧、论坛类内容

**工具 5：enterprise-search**（企业内部知识，仅内网可用）

```bash
skill enterprise-search --query "<关键词>"
```

- 环境变量：`BAIDU_INTERNAL_NETWORK=true`
- 适用：内部研究报告、竞对情报、知识库文档

**工具 6：财经 RSS 聚合**（35 个高质量财经源）

```bash
python3 lib/finance-rss-reader/scripts/rss_fetch.py \
    --keywords "百度,BIDU" \
    --ticker BIDU \
    --days 14 \
    --sources-config lib/finance-rss-reader/references/rss_sources.json \
    --min-score 0.4 \
    --max-sources 15
```

- 适用：最新资讯快讯、跨源交叉验证（Reuters / Bloomberg / FT / MarketWatch / 财新 / 36氪 / 艾瑞 / 易观 / Gartner / McKinsey 等）

**工具 7：URL 全文抓取**（拿到具体 URL 后深读）

```bash
skill realtime-search fetch "<URL>" --max-chars 50000
```

**工具 8：多格式内容处理**

- **PDF**：`skill pdf --extract "<URL>"` — OCR 识别扫描版财报
- **知识库文档**：`skill ku-doc-manage query-content --url "<URL>"` — 读取 ku.baidu-int.com 文档
- **HTML**：内嵌正文提取器（`lib/search_engine.py::_extract_html_content`）

### 信息源分层（按置信度）

```
Layer 1（最高置信度 high）：公司 IR 官网、交易所披露、SEC EDGAR、监管文件
   → 工具：Brave 定向 site: + filetype:pdf + Firecrawl

Layer 2（高置信度 high）：业绩会 Transcript、官方公告
   → 工具：Brave 搜索 "earnings call transcript"

Layer 3（中等置信度 medium）：Seeking Alpha / FT / Bloomberg / WSJ 深度报道
   → 工具：Firecrawl 深度搜索（英文优先）

Layer 4（参考价值 medium）：中文财经媒体（36氪 / 财新 / 东方财富 / 界面）
   → 工具：realtime-search 百度 + baidu-search

Layer 5（快讯参考 medium）：财经 RSS 聚合
   → 工具：finance-rss-reader（35 个源）

补充层（内网 high，视配置启用）：enterprise-search + ku-doc-manage
```

### 搜索关键词构建策略

- **财报类**：`公司名 + 时间期间 + "财报 / earnings / annual report / 10-K"` + `公司名 + "IR / investors"`
- **竞品类**：`公司A vs 公司B + 关键指标` + `行业 + "market share / 市占率"`
- **行业类**：`行业名 + "趋势 / outlook / forecast" + 年份` + `行业 + 政策 / 监管关键词`
- **营销类**：`品牌名 + "定位 / positioning / STP"` + `品牌名 + "target / 用户画像 / JTBD"`
- **估值类**：`公司 + "valuation / P/E / DCF / WACC / 护城河"`
- **风险类**：`公司 + "风险 / 违规 / 处罚 / 债务 / 现金流风险 / Altman Z"`

### YAML 源清单（Step 1 的强制输出格式）

搜索完成后，把所有源统一整理成如下 YAML，作为 Step 2 的输入：

```yaml
sources:
  - source_id: FC001
    title: "文章/文件标题"
    publisher: "发布方（域名）"
    source_type: 官方财报 | 业绩会 | 分析师报告 | 新闻媒体 | RSS快讯 | 内部文档
    publish_date: YYYY-MM-DD
    url: "https://..."
    confidence: high | medium | low
    key_facts:
      - "关键信息点 1（含数字/结论）"
      - "关键信息点 2"
    full_text_fetched: true | false
```

**source_id 命名约定**：
- `FC###` = Firecrawl
- `RS###` = realtime-search
- `BD###` = baidu-search
- `RSS###` = finance-rss-reader
- `ES###` = enterprise-search
- `KU###` = ku-doc-manage
全局唯一。

---

## Step 2：结构化分析

### 专家 skill 替换纯 LLM 分析（推荐）

走到金融/营销框架时，**优先调用垂直 skill**（内置了 domain 算法与数据模型）而不是纯 LLM 推理。

**金融框架 → finance-skills 映射**
- DCF / 相对估值 → `company-valuation`（DCF + 相对 + SOTP 三角，牛/基/熊三情景）
- 深度财报（财报前）→ `earnings-preview`（consensus / beat-miss 历史）
- 财报快评（财报后）→ `earnings-recap`（实际 vs 预期 EPS、股价反应）
- 深度财报（预期修正）→ `estimate-analysis`
- 护城河（SaaS）→ `saas-valuation-compression`
- 风险专项（流动性）→ `stock-liquidity`（价差/成交量/Amihud）
- 风险专项（相关性）→ `stock-correlation`（对冲候选）
- 技术面分析 → `sepa-strategy`（Minervini VCP）
- 期权策略 → `options-payoff`
- ETF 特化 → `etf-premium`

**营销框架 → marketingskills 映射**（节选，完整表见 `references/external-skills.md`）
- 4P/Product → `product-marketing`
- 4P/Price → `pricing`
- STP / JTBD → `customer-research`
- AIDA/Attention → `ads` + `ad-creative`
- AIDA/Interest-Desire → `copywriting` + `copy-editing`
- AARRR/Acquisition → `seo-audit` + `ai-seo` + `programmatic-seo` + `schema`
- AARRR/Activation → `signup` + `onboarding`
- AARRR/Retention → `churn-prevention` + `emails` + `sms`
- AARRR/Revenue → `paywalls` + `offers`
- AARRR/Referral → `referrals` + `community-marketing` + `co-marketing`
- CBBE 品牌 → `public-relations` + `social`
- Customer Journey → `analytics` + `ab-testing`

**元 skill**：反复遇到未覆盖的分析场景 → 调 `finance-skills/skill-creator` 动态生成新分析 skill。

### 强制原则（不遵守即视为不合格产出）

1. **每条结论必须标注 source_id**，内联格式：`[结论内容]（来源：[FC001](URL), [RS003](URL)）`
2. **区分事实 / 计算 / 假设 / 判断**，四类分别标注
3. **不确定项**：标注"证据有限，推测如下（置信度：低）"，禁止以肯定语气断言
4. **数字规范**：所有数字附带**期间 + 币种 + 同比/环比口径**，缺一不可
5. **同源交叉**：关键数字至少 2 个独立来源交叉验证；单源数字标注"待验证"

### 按框架分析质量红线（摘录，完整见 `references/frameworks.md`）

- **PEST**：每维度 200-300 字，含 ≥1 条数据支撑；禁"可能影响 / 或许会"等模糊词
- **Porter 五力**：每一力给出高/中/低强度评估 + ≥2 条依据
- **SWOT**：2×2 矩阵，每象限 ≥3 条具体条目 + SO/WO/ST/WT 四条战略
- **3C**：三方分析必须闭环（公司能力 vs 客户需求 vs 竞对差距）
- **4P / 7P**：4P 之间要有一致性论证
- **STP**：细分必须 MECE，定位遵循"对 [目标客户]，[品牌] 是 [品类] 中 [差异点]"句式
- **AARRR**：每环节给出关键指标 + 漏斗转化率；LTV/CAC > 3 视为健康
- **JTBD**：任务陈述遵循"当 [情境] 时，我想 [动机]，以便 [预期结果]"
- **CBBE**：每一层必须有量化指标或访谈证据
- **财报/KPI 树**：思维链——拆解 KPI → 历史对比 → 同行对比 → 识别驱动因子 → 判断可持续性
- **杜邦分析**：识别 ROE 是盈利驱动 / 效率驱动 / 杠杆驱动 中的哪一类
- **DCF**：给出基准/乐观/悲观三情景估值；WACC 各参数分别标注来源
- **相对估值**：至少 5 家同行同期可比 + 说明为何该行业适用该倍数
- **护城河**：给出数据证据 + 判断护城河是加宽还是变窄
- **Altman Z / Beneish M / Piotroski F**：列出每项指标计算结果 + 得分 + 使用的模型版本
- **风险专项**：决策矩阵（impact × likelihood）+ 触发条件 + 预警指标

---

## Step 3：金字塔调研报告生成

### 可视化增强

- `finance-skills/generative-ui`：把估值模型 / 财务比率 / 用户旅程等**输出为交互式 HTML/SVG widget**，嵌入报告（Web 交付场景）
- `finance-skills/options-payoff`：期权策略盈亏图必备

### 报告后续行动衔接

Step 3 报告输出后若用户问"接下来怎么做"，自动衔接以下 skill：

| 用户后续问题 | 衔接 skill |
|---|---|
| 写营销方案 | `marketing/marketing-plan` |
| 产品发布 | `marketing/launch` + `marketing/copywriting` |
| 落地页 | `marketing/cro` + `marketing/copywriting` |
| 邮件序列 | `marketing/emails` |
| 内容日历 | `marketing/content-strategy` + `marketing/social` |
| 冷启动获客 | `marketing/cold-email` + `marketing/directory-submissions` |
| PR 稿 | `marketing/public-relations` |
| SEO 修复 | `marketing/seo-audit` |
| 定价建议 | `marketing/pricing` + `marketing/offers` |
| 广告创意 | `marketing/ad-creative` + `marketing/ads` |
| 免费工具增长 | `marketing/free-tools` + `marketing/lead-magnets` |
| 融资 pitch | `finance-skills/startup-analysis` + `finance-skills/company-valuation` |
| 交易信号 | `finance-skills/sepa-strategy` + `finance-skills/stock-correlation` |

完整衔接矩阵见 `references/external-skills.md`。

### 报告模板（严格遵守）

```markdown
# [调研主题] 调研报告

**生成时间**：YYYY-MM-DD
**分析框架**：[所用框架 / 组合]
**信息源数量**：[N] 条（Firecrawl [X] / realtime-search [Y] / baidu [Z] / RSS [W] / 内网 [V]）

---

## 核心结论

> **总判断**：[一句话核心结论]

支撑理由：
1. [理由 1]（置信度：高）（来源：[FC001](URL)）
2. [理由 2]（置信度：中）（来源：[FC002](URL), [RS003](URL)）
3. [理由 3]（置信度：高）（来源：[FC003](URL)）

主要风险：[1-2 个关键风险]

---

## [框架维度 1]

[分析内容，每条结论后标注 source_id 与链接]

## [框架维度 2]

...

---

## 风险与不确定性

| 风险事项 | 触发条件 | 影响程度 | 发生概率 | 来源 |
|---|---|---|---|---|
| [风险 1] | [条件] | 高/中/低 | 高/中/低 | [FC00X](URL) |

---

## 参考文献

| 编号 | 标题 | 发布方 | 日期 | 置信度 | 原文链接 |
|---|---|---|---|---|---|
| FC001 | [标题] | [发布方] | [日期] | 高 | [查看原文](URL) |
| RS002 | ... | ... | ... | 中 | ... |
```

### 参考文献规范（不可省略）

- **每篇被引用的资料必须在报告末尾列出**
- **原文链接必须可点击跳转**：`[查看原文](URL)`
- **正文内联引用**：`（来源：[FC001](URL)）`
- 付费墙文章：标注"内容来源：摘要 / RSS 快讯"
- 无 URL 的内部文档：标注文件名 + 获取渠道

### 报告语气规范

- **结论先行**，数字后必有解释（不要只堆数据）
- 不确定判断标注**置信度：高 / 中 / 低**
- **禁止**"可能 / 或许 / 也许 / 大概"等无价值模糊词
- 重要数字**加粗**，趋势用 ↑ ↓ → 标注
- 每段控制在 150 字以内

### 组合报告的额外结构

当使用框架组合（如"投资判断组合"= 深度财报 + 杜邦 + 护城河 + DCF）时，报告增加：

- **执行摘要**：列出所有框架及其结论要点
- **分框架章节**：第 1 部分 [框架 A]、第 2 部分 [框架 B]……
- **综合结论**：跨框架总结，识别一致 / 冲突结论

---

## 两种使用方式

### 方式 1：Codex 原生（推荐）

Codex 加载本 SKILL.md 后，按 Step 0→1→2→3 走 prompt 流程，工具调用穿插在对话中，允许用户在每个审核点介入。

### 方式 2：Python CLI（脚本党）

```bash
# 交互式模式（会输出审核卡片提示选择框架）
python3 bin/search_agent.py "高德地图上新了什么功能?"

# 自动模式（跳过审核点 ①，使用推荐的第一个框架/组合）
python3 bin/search_agent.py "百度2026Q1财报分析" --auto
```

## 技术架构

### 目录结构

```
search-agent-skill/
├── SKILL.md                    # Codex 主入口 prompt（本文件）
├── CLAUDE.md                   # 原始 Claude 版调研助手（保留参考）
├── CHANGELOG.md
├── requirements.txt
├── references/
│   ├── frameworks.md           # 31 框架详细定义 + 质量红线 + 组合规则
│   └── workflow.md             # 工作流 mermaid 图
├── scripts/
│   └── firecrawl_search.py     # Firecrawl 深度搜索薄封装
├── lib/
│   ├── frameworks.py           # 9 核心框架配置（Python，脚本后端）
│   ├── intent_classifier.py    # 意图识别器（脚本后端）
│   ├── framework_combinator.py # 框架组合推荐（脚本后端）
│   ├── search_engine.py        # 多层搜索调度（脚本后端）
│   ├── report_generator.py     # 报告生成器（脚本后端）
│   └── finance-rss-reader/     # 内嵌 RSS 拉取组件（35 源）
├── bin/
│   └── search_agent.py         # Python CLI 编排入口
└── config/
    └── settings.json           # 参数配置
```

### 核心模块

#### 1. `references/frameworks.md` + `lib/frameworks.py` — 分析框架库

31 个框架的完整定义，每个框架包含：
- 视角（分析师角色）
- 分析维度列表
- 适用场景
- 搜索关键词模板（按维度分组）
- 推荐模型深度（Sonnet / Opus）
- **质量红线**（禁止模糊词 / 数字口径要求 / 输出格式约束）

markdown 版给 prompt 用，Python dict 版给 CLI 脚本用。新增框架只需在两处同步更新。

#### 2. `lib/intent_classifier.py` — 意图识别

基于关键词匹配 + 优先级加权 + 复杂度判断，推荐 Top K 个框架：
- 关键词打分（`KEYWORD_MAP`）
- 优先级加权（`PRIORITY_KEYWORDS`）
- 复杂度判断（`COMPLEXITY_INDICATORS`：全面 / 系统 / 多维度 / 深入 / 综合，或问题 > 50 字）

#### 3. `lib/framework_combinator.py` — 框架组合推荐

内置 10+ 种预定义组合（战略型 / 营销型 / 金融型），基于单框架推荐结果自动匹配组合。

#### 4. `lib/search_engine.py` — 多源分层搜索引擎

5 层分层策略 + 结构化源元数据（8 字段：source_id / title / publisher / source_type / publish_date / data_period / url_or_path / confidence / notes）。

支持格式：
- PDF → `pdf` skill OCR
- 知识库文档 → `ku-doc-manage` skill
- HTML → 正文提取
- RSS → 内嵌 rss_fetch.py

#### 5. `lib/report_generator.py` — 报告生成器

按框架结构化生成 Markdown 金字塔报告：
- 多种报告模板（财报快评 / 深度分析 / PEST / 通用等）
- 自动插入引文链接
- 生成参考文献表
- 可选导出 Word（调用 `docx` skill）

#### 6. `scripts/firecrawl_search.py` — Firecrawl 深度搜索

Codex 直接调用的 CLI 工具，返回标准化 JSON，填补英文深度内容（Seeking Alpha / FT / SEC）的短板。

## 配置说明

### `config/settings.json`

```json
{
  "search": {
    "max_results_per_keyword": 10,
    "max_parallel_searches": 5,
    "timeout_seconds": 30,
    "enable_enterprise_search": false
  },
  "content_processing": {
    "max_content_length": 50000,
    "enable_pdf_ocr": true,
    "enable_ku_doc": true,
    "max_pdf_pages": 50
  },
  "report": {
    "output_dir": "./output",
    "default_format": "markdown",
    "include_citations": true,
    "export_to_word": false
  },
  "firecrawl": {
    "enabled": true,
    "default_limit": 5,
    "default_lang": "en",
    "timeout_seconds": 60
  },
  "human_review": {
    "require_framework_confirmation": true,
    "require_report_validation": false
  }
}
```

### 环境变量

```bash
# Firecrawl 深度搜索（必须配置）
export FIRECRAWL_API_KEY="fc-a5279d633c4f4636b2592bc31a431770"  # 仅示例，生产请替换

# 内网搜索（可选，仅百度内网）
export BAIDU_INTERNAL_NETWORK=true
```

## 依赖的 Skills

- `realtime-search`：Brave 官方 + 百度中文 + URL 全文抓取（**必需**）
- `baidu-search`：中文通用兜底（可选）
- `enterprise-search`：企业内部知识（可选，仅内网）
- `pdf`：PDF 文件处理与 OCR（可选，处理财报 PDF 时必需）
- `ku-doc-manage`：知识库文档管理（可选）
- `docx`：Word 文档生成（可选）
- 本地脚本 `scripts/firecrawl_search.py`：Firecrawl 深度检索（**推荐**）
- 本地脚本 `lib/finance-rss-reader/scripts/rss_fetch.py`：35 个财经 RSS 源聚合（内嵌）

### 外部 skill 仓库（强烈推荐挂载）

```bash
mkdir -p ~/.codex/skills && cd ~/.codex/skills
git clone https://github.com/coreyhaines31/marketingskills.git marketing
git clone https://github.com/himself65/finance-skills.git finance
```

- **`marketing/*`** — 44 个营销专家 skill（copywriting / cro / seo-audit / emails / ads / analytics / ab-testing / churn-prevention 等），在 Step 2 营销框架 + Step 3 后续行动节点自动衔接
- **`finance/*`** — 20+ 个金融专家 skill（company-valuation / earnings-preview / yfinance-data / stock-liquidity / options-payoff / generative-ui / startup-analysis 等），在 Step 1 数据层 + Step 2 金融框架 + Step 3 可视化节点自动衔接

完整触发规则和映射矩阵：`references/external-skills.md`

Python 依赖：见 `requirements.txt`（主要为 `requests`）

## 扩展指南

### 添加新的分析框架

**双份同步**：
1. 在 `references/frameworks.md` 中按现有格式添加：视角 / 维度 / 搜索关键词模板 / 质量红线
2. 如需 Python CLI 支持，在 `lib/frameworks.py` 中添加：

```python
ANALYSIS_FRAMEWORKS["新框架名"] = {
    "name": "新框架名",
    "description": "框架描述",
    "dimensions": ["维度1", "维度2"],
    "适用场景": ["场景1", "场景2"],
    "模型深度": "Opus",
    "搜索策略": "搜索策略描述",
    "search_keywords_template": {
        "维度1": ["{主题} 关键词1", "{主题} 关键词2"],
        "维度2": ["{主题} 关键词3"]
    }
}
```

然后在 `lib/intent_classifier.py` 中添加触发关键词：

```python
KEYWORD_MAP["新框架名"] = ["关键词1", "关键词2"]
```

### 添加新的搜索源

1. 在 SKILL.md **Step 1 工具矩阵**中新增工具条目
2. 如需 CLI 支持，在 `lib/search_engine.py` 中添加搜索方法：

```python
def _call_custom_search(self, keyword: str, max_results: int) -> List[Dict]:
    # 调用自定义搜索 API
    ...
```

3. 在 `multi_source_search` 方法中调用

### 添加新的框架组合

在 `lib/framework_combinator.py` 的 `FRAMEWORK_COMBINATIONS` 中新增：

```python
"投资判断组合": {
    "name": "投资判断组合",
    "frameworks": ["深度财报分析", "DuPont杜邦", "巴菲特护城河", "DCF"],
    "execution_order": ["深度财报分析", "DuPont杜邦", "巴菲特护城河", "DCF"],
    "适用场景": ["价值投资", "长期持仓决策"],
    "说明": "先看经营质量，再拆 ROE 结构，再判断护城河，最后估内在价值"
}
```

## 限制与注意事项

1. **搜索结果数量**：每个关键词默认最多返回 10 条结果，可通过配置调整
2. **内容长度限制**：单个内容最大处理长度为 50,000 字符
3. **PDF OCR**：依赖 `pdf` Skill，扫描版 PDF 识别准确度取决于 OCR 质量
4. **Firecrawl 需付费 API Key**：默认示例 key 仅供测试，长期使用请自备
5. **内网依赖**：`enterprise-search` 和 `ku-doc-manage` 仅在百度内网环境可用
6. **人工审核**：框架选择需人工确认，无法完全自动化（`--auto` 模式仅跳过审核点 ①，不推荐生产使用）
7. **金融专业性**：DCF / 杜邦 / 相对估值等金融框架产出的估值结果**不构成投资建议**，仅供研究参考

## 示例场景

### 场景 1：快速财报分析

**用户输入**：`"帮我快速看看高德地图的 2026Q1 财报"`

**流程**：
1. Step 0：意图识别 → 推荐"财报快评"
2. 审核卡片输出，用户确认
3. Step 1：
   - Brave 搜 `高德地图 2026Q1 财报 filetype:pdf`
   - realtime-search 百度搜 `高德地图 2026Q1 业绩`
   - RSS 聚合关键词 `高德,AutoNavi`
4. Step 2：按财报快评维度分析（核心结论 / 三个关键发现 / 财务表现表格 / 现金流 / 主要风险）
5. Step 3：金字塔报告 + 参考文献表

### 场景 2：新功能市场调研

**用户输入**：`"高德地图上新了什么功能，帮我全网搜索相关的稿件，然后把这些信息汇总成一个方案"`

**流程**：
1. Step 0：识别为"复杂问题" → 推荐组合 **PEST + 3C**
2. 审核卡片，用户可勾选/调整
3. Step 1：
   - PEST 维度：政治 `高德地图 政策`、技术 `高德地图 新功能`、社会 `高德地图 用户需求`
   - 3C 维度：公司 `高德地图 战略`、客户 `高德地图 用户画像`、竞争 `高德 vs 百度地图`
4. Step 2：按 PEST 四维 + 3C 三角组织内容
5. Step 3：组合报告，末尾附来源链接

### 场景 3：竞品对比

**用户输入**：`"对比高德地图和百度地图的功能和市场表现"`

**流程**：
1. Step 0：推荐 **同行对比组合**（同行竞争对比 → 3C → Porter 五力）
2. 审核卡片
3. Step 1：多公司并行搜索 + Firecrawl 搜 `Amap vs Baidu Maps market share`
4. Step 2：三栏对比表 + 相对优劣势 + 战略建议
5. Step 3：金字塔报告

### 场景 4：投资价值判断（新增，融合金融框架）

**用户输入**：`"百度值不值得投"`

**流程**：
1. Step 0：识别为投资判断 → 推荐 **投资判断组合**（深度财报 → 杜邦 → 护城河 → DCF/相对估值 → 风险专项）
2. Step 1：
   - Firecrawl 搜 `Baidu 10-K annual report`、`site:seekingalpha.com BIDU analysis`
   - Brave 搜 `Baidu earnings call transcript 2026Q1`
   - RSS 聚合关键词 `百度,BIDU`
3. Step 2：
   - 深度财报：营收/利润/现金流三张表
   - 杜邦：ROE = 净利率 × 周转 × 杠杆，识别驱动因子
   - 护城河：搜索引擎份额 + AI 云 + 自动驾驶专利，判断加宽/变窄
   - DCF：基准/乐观/悲观三情景，WACC 参数标注来源
   - 相对估值：与 Alphabet / Alibaba / Tencent 同行对比 P/E、PEG
   - 风险专项：监管 / 收入结构单一 / 竞争加剧，决策矩阵排序
4. Step 3：金字塔报告，末尾附投资结论（注明"不构成投资建议"）

## 常见问题

**Q：如何调整搜索结果数量？**
A：修改 `config/settings.json` 中的 `max_results_per_keyword` 参数。

**Q：如何跳过人工审核，直接使用推荐的框架？**
A：使用 `--auto` 参数运行脚本（仅 CLI 模式；Codex prompt 模式建议保留审核点以保证质量）。

**Q：生成的报告保存在哪里？**
A：默认保存在 `config.report.output_dir`（`./output`），可修改。

**Q：如何添加自定义的分析框架？**
A：参考"扩展指南 → 添加新的分析框架"，在 `references/frameworks.md` 和 `lib/frameworks.py` 双份同步添加。

**Q：PDF 文件无法识别怎么办？**
A：检查 `pdf` Skill 是否已安装并正常工作，或手动提取 PDF 内容后作为文本传入。

**Q：Firecrawl 报错怎么办？**
A：检查 `FIRECRAWL_API_KEY` 是否设置且额度未用尽；免费额度较小，长期使用请自备付费 key。

**Q：Codex 里跑不需要 Python CLI？**
A：对，Codex 直接读 SKILL.md 走 prompt 流程即可，Python CLI 只是"脚本党"的备选路径。工具调用（Firecrawl / realtime-search / RSS）依然通过 subprocess 或 skill 调用。

**Q：金融框架的估值结果是投资建议吗？**
A：**不是**。DCF / 相对估值 / 杜邦分析等仅是研究工具，结果仅供参考，不构成投资、财务、法律建议。

## 开发路线图

- [x] v3.0 融合 CLAUDE.md 精华：审核卡片 / YAML 源清单 / 金字塔报告 / 质量红线
- [x] v3.0 扩容至 31 个框架（战略 12 + 营销 9 + 金融 10）
- [x] v3.0 集成 Firecrawl 深度搜索
- [ ] 支持多 Agent 并行分析（Researcher / Analyst / Validator 分工）
- [ ] 集成 finance-rss-reader 定时任务（定期监控特定主题的新闻/公告）
- [ ] 引文质量评分与来源可信度分析（自动识别官方 vs 二手转载）
- [ ] 报告模板可视化编辑器
- [ ] 支持多轮迭代优化（用户反馈 → 重新搜索/分析）
- [ ] 金融框架增强：加入 CAMELS（银行）、VRIO（资源基础观）、PESTLE（+ 法律环境）
- [ ] 营销框架增强：加入 Growth Loops、PMF 度量、North Star Metric

## 设计原则

1. **框架先于搜索**：先决定要支撑什么判断，再决定查什么资料
2. **官方来源优先**：分层搜索把 confidence: high 放前面
3. **引文透明**：每个关键论断绑定 source_id，报告末尾必须列参考文献表
4. **两个人工闸门**：审核点 ①（选框架）+ 审核点 ②（校引文/结论）
5. **可扩展**：新框架 / 新搜索源 / 新组合均可低成本接入
6. **专业视角**：战略题用战略咨询顾问视角，金融题用卖方分析师/投资经理视角，营销题用品牌经理/增长负责人视角

## 许可与贡献

本 Skill 融合了两条设计脉络：
- **v2.3 财报分析 Workflow**：分层搜索 + 结构化源元数据 + RSS 聚合
- **CLAUDE.md 通用调研助手**：审核卡片 + YAML 源清单 + 金字塔报告 + 质量红线

遵循原则：
- 先明确要支持的判断，再决定查什么资料
- 优先使用官方来源
- 所有关键数字必须标明来源
- 结论必须区分事实、计算、假设和判断

欢迎提出改进建议和贡献代码！
