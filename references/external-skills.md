# 外部 Skill 增强矩阵

本 skill 通过挂载两个外部 skill 仓库，在 **Step 0 → Step 1 → Step 2 → Step 3** 每个节点补齐垂直能力。核心 search-agent skill 仍是编排大脑，外部 skill 作为**可调用的专家模块**。

## 上游仓库

| 仓库 | 覆盖领域 | 安装位置建议 |
|---|---|---|
| [`coreyhaines31/marketingskills`](https://github.com/coreyhaines31/marketingskills) | 44 个营销/增长/SEO/内容/CRO 技能 | `~/.codex/skills/marketing/` 或 `~/.claude/skills/` |
| [`himself65/finance-skills`](https://github.com/himself65/finance-skills) | 20+ 金融/估值/情绪/市场数据技能（6 大 plugin 分组） | `~/.codex/skills/finance/` 或 `~/.claude/skills/` |

安装方式（Codex）：

```bash
mkdir -p ~/.codex/skills && cd ~/.codex/skills
git clone https://github.com/coreyhaines31/marketingskills.git marketing
git clone https://github.com/himself65/finance-skills.git finance
```

Codex 启动时会自动扫描并注册这些 skill；search-agent skill 在下述节点会**通过 skill 调用**它们。

---

## Step 0：意图识别 & 框架路由（增强）

### 上游 skill 补位：意图分类前置

在 search-agent 内置的 `intent_classifier.py` 无法准确路由时，可**先调这些 skill 二次确认**再进入审核卡片。

| 场景 | 优先调用外部 skill | 用途 |
|---|---|---|
| 营销/增长类调研 | `marketing-ideas` | 生成候选调研方向 / 灵感发散，帮助补全用户模糊需求 |
| 需要跨营销框架决策 | `marketing-plan` | 生成完整营销方案骨架，再从中选主框架 |
| 创业/投资意图 | `finance-skills/startup-analysis` | 提供 VC 视角 / 求职视角 / 创始人视角三重维度 |
| 单一数字快查 | `finance-skills/yfinance-data` 或 `funda-data` | 直接返回股价/财报数据，跳过完整框架流程 |

### 触发规则

```
if "灵感 / 不知道 / 帮我想想" in query and 营销意图:
    先调 marketing-ideas → 输出方向列表 → 用户选定 → 再走 Step 0 框架路由
elif "股价 / 现价 / 最新市值" 单一数字:
    直接调 yfinance-data / funda-data → 结束，跳过 Step 1-3
elif "创业公司 / VC / 值不值得加入":
    优先推荐 startup-analysis 而非通用 3C
```

---

## Step 1：多源分层信息检索（数据源大幅扩容）

外部 skill 在此节点**新增第 6 层"垂直数据源"**，作为传统搜索的补充。

### 金融数据源（补 Layer 1-2 官方数据）

| 场景 | 外部 skill | 数据类型 |
|---|---|---|
| 美股实时价格/财务 | `finance-skills/yfinance-data` | 价格、财务、期权、股息、财报日期 |
| 分析师研究合成 | `finance-skills/funda-data` | 60+ 端点，MCP 服务 + REST 兜底 |
| 完整期权链 | `finance-skills/tradingview-reader` | 期权链 + Greeks + IV + 图表状态 |
| 中东地缘风险监控 | `finance-skills/hormuz-strait` | 航运、油价、保险风险时间线 |
| 股票情绪 | `finance-skills/finance-sentiment` | Reddit / X / 新闻 / Polymarket |

### 营销/竞对数据源（补 Layer 3-4 深度分析）

| 场景 | 外部 skill | 用途 |
|---|---|---|
| 深度竞对情报 | `marketing/competitor-profiling` | 完整竞对档案（定位/GTM/团队/融资） |
| 客户/用户调研 | `marketing/customer-research` | JTBD 访谈 / 用户画像 / 痛点挖掘 |
| 目录站/软件榜单 | `marketing/directory-submissions` | Product Hunt / G2 / Capterra 情报 |
| PR/媒体池 | `marketing/public-relations` | HARO / Featured / 记者联系人 |
| 潜在客户勘察 | `marketing/prospecting` | B2B 决策链 / 联系人挖掘 |

### 调用规范

在 Step 1 的 YAML 源清单里，外部 skill 数据统一命名：
- `FIN###` = finance-skills 数据源
- `MKT###` = marketingskills 数据源

保留 `confidence` 字段——垂直 skill 数据一般标 `high`（结构化 API）或 `medium`（AI 合成）。

---

## Step 2：结构化分析（专家级方法论注入）

### 金融框架的"专家 skill" 替换

当 search-agent 走到金融分析框架时，**优先调用垂直 skill 而不是纯 LLM 分析**，因为它们内置了 domain-specific 的算法与数据模型。

| 内置框架 | 优先调外部 skill | 增强点 |
|---|---|---|
| **DCF / 相对估值** | `finance-skills/company-valuation` | DCF + 相对估值 + SOTP 三角化，隐含股价、WACC×g 敏感性、牛/基/熊三情景 |
| **深度财报分析（财报前）** | `finance-skills/earnings-preview` | Consensus 预期、beat/miss 历史、分析师情绪 |
| **财报快评（财报后）** | `finance-skills/earnings-recap` | 实际 vs 预期 EPS、股价反应、利润率趋势 |
| **深度财报分析（预期修正）** | `finance-skills/estimate-analysis` | 修正趋势 / 增长预期 / 历史准确度 |
| **护城河（SaaS 特化）** | `finance-skills/saas-valuation-compression` | ARR 倍数、原因归因、同行对比 |
| **风险专项（流动性）** | `finance-skills/stock-liquidity` | 价差 / 成交量分布 / Amihud 比率 |
| **风险专项（相关性）** | `finance-skills/stock-correlation` | 行业同行、共同运动、对冲候选 |
| **技术面（新增框架）** | `finance-skills/sepa-strategy` | Minervini 趋势模板 + VCP 形态 + 仓位管理 |
| **期权策略（新增）** | `finance-skills/options-payoff` | 交互式期权盈亏图 + 动态控制 |
| **ETF 特化（新增）** | `finance-skills/etf-premium` | 溢价/折价 vs NAV、同类筛选 |

### 营销框架的"专家 skill" 替换

| 内置框架 | 优先调外部 skill | 增强点 |
|---|---|---|
| **4P / 7P（Product）** | `marketing/product-marketing` | 产品定位 / messaging / launch 打法 |
| **4P（Price）** | `marketing/pricing` | 定价策略 / 价格锚定 / 分层设计 |
| **STP / JTBD** | `marketing/customer-research` | 深度用户研究 / JTBD 访谈脚本 |
| **AIDA（Attention）** | `marketing/ads` + `marketing/ad-creative` | 付费广告 + 创意 brief |
| **AIDA（Interest → Desire）** | `marketing/copywriting` + `marketing/copy-editing` | 高转化文案生成/审校 |
| **AARRR（Acquisition）** | `marketing/seo-audit` / `marketing/ai-seo` / `marketing/programmatic-seo` / `marketing/schema` / `marketing/site-architecture` | SEO 全栈 |
| **AARRR（Activation）** | `marketing/signup` + `marketing/onboarding` | 注册漏斗 + onboarding CRO |
| **AARRR（Retention）** | `marketing/churn-prevention` + `marketing/emails` + `marketing/sms` | 留存 + 生命周期营销 |
| **AARRR（Revenue）** | `marketing/paywalls` + `marketing/pricing` + `marketing/offers` | 变现设计 |
| **AARRR（Referral）** | `marketing/referrals` + `marketing/community-marketing` + `marketing/co-marketing` | 分享/社区/联合营销 |
| **CBBE 品牌** | `marketing/public-relations` + `marketing/social` | 品牌资产建设 |
| **Customer Journey** | `marketing/analytics` + `marketing/ab-testing` | 埋点 + A/B 测试 |
| **风险专项（营销侧）** | `marketing/competitors` + `marketing/competitor-profiling` | 竞对威胁监控 |

### 分析师 skill：finance-skill-creator / marketingskills 的元 skill

- `finance-skills/skill-creator`：当发现某个分析场景反复出现且无现成 skill，**动态生成新分析 skill**
- marketingskills 无对应元 skill，但可通过 search-agent 自身的 `frameworks.md` 扩展

---

## Step 3：金字塔调研报告生成（可视化 + 内容产出）

### 报告可视化增强

- `finance-skills/generative-ui`：把估值模型 / 财务比率 / 用户旅程等**输出为交互式 HTML/SVG widget**，嵌入报告（适用于 web 交付场景）
- `finance-skills/options-payoff`：期权策略报告的必备可视化组件

### 报告后续行动方案

Step 3 报告输出后，若用户问"接下来怎么做"，可衔接以下 skill：

| 用户后续问题 | 衔接 skill |
|---|---|
| "帮我写一份营销方案" | `marketing/marketing-plan` |
| "帮我写产品发布话术" | `marketing/launch` + `marketing/copywriting` |
| "生成落地页" | `marketing/cro` + `marketing/copywriting` |
| "写 5 封邮件序列" | `marketing/emails` |
| "内容日历" | `marketing/content-strategy` + `marketing/social` |
| "冷启动获客" | `marketing/cold-email` + `marketing/directory-submissions` |
| "PR 稿" | `marketing/public-relations` |
| "SEO 修复清单" | `marketing/seo-audit` |
| "定价建议" | `marketing/pricing` + `marketing/offers` |
| "配套广告创意" | `marketing/ad-creative` + `marketing/ads` |
| "免费工具增长" | `marketing/free-tools` + `marketing/lead-magnets` |
| "融资 pitch" | `finance-skills/startup-analysis` + `finance-skills/company-valuation` |
| "交易信号" | `finance-skills/sepa-strategy` + `finance-skills/stock-correlation` |

---

## 全景映射表

```
┌─────────────────── Step 0 ───────────────────┐
│ 意图识别 │ marketing-ideas / marketing-plan (营销灵感/方案骨架)      │
│          │ startup-analysis (创业/投资视角)                          │
│          │ yfinance-data / funda-data (单一数字快查)                 │
└──────────────────────────────────────────────┘
                       ↓
┌─────────────────── Step 1 ───────────────────┐
│ 金融数据 │ yfinance-data · funda-data · tradingview-reader          │
│          │ hormuz-strait · finance-sentiment                        │
│ 营销数据 │ competitor-profiling · customer-research                 │
│          │ directory-submissions · public-relations · prospecting   │
│ 通用搜索 │ [内置] Firecrawl + realtime-search + baidu-search + RSS  │
└──────────────────────────────────────────────┘
                       ↓
┌─────────────────── Step 2 ───────────────────┐
│ 金融分析 │ company-valuation (DCF+相对+SOTP)                        │
│          │ earnings-preview · earnings-recap · estimate-analysis    │
│          │ saas-valuation-compression · stock-liquidity             │
│          │ stock-correlation · sepa-strategy · options-payoff       │
│          │ etf-premium                                              │
│ 营销分析 │ product-marketing · pricing · customer-research          │
│          │ ads · ad-creative · copywriting · copy-editing           │
│          │ seo-audit · ai-seo · programmatic-seo · schema           │
│          │ site-architecture · signup · onboarding                  │
│          │ churn-prevention · emails · sms · paywalls · offers      │
│          │ referrals · community-marketing · co-marketing           │
│          │ social · analytics · ab-testing · competitors            │
│ 元分析   │ skill-creator (动态生成新分析 skill)                     │
└──────────────────────────────────────────────┘
                       ↓
┌─────────────────── Step 3 ───────────────────┐
│ 报告可视化 │ generative-ui (交互 widget)                             │
│            │ options-payoff (期权盈亏图)                             │
│ 后续行动   │ marketing-plan · launch · cro · emails ·                │
│            │ content-strategy · cold-email · seo-audit ·             │
│            │ pricing · public-relations · lead-magnets ·             │
│            │ free-tools · directory-submissions · sales-enablement   │
│            │ revops · product-marketing · marketing-psychology       │
└──────────────────────────────────────────────┘
```

---

## 完整外部 skill 清单

### `himself65/finance-skills` （6 plugins / 20+ skills）

**data-providers**：yfinance-data · funda-data
**market-analysis**：company-valuation · earnings-preview · earnings-recap · estimate-analysis · etf-premium · options-payoff · saas-valuation-compression · sepa-strategy · stock-correlation · stock-liquidity
**social-readers**：finance-sentiment · hormuz-strait · tradingview-reader
**startup-tools**：startup-analysis
**ui-tools**：generative-ui
**skill-creator**：finance-skill-creator（元 skill）

### `coreyhaines31/marketingskills` （44 skills）

**转化优化 CRO**：cro · signup · onboarding · popups · paywalls
**内容与文案**：copywriting · copy-editing · cold-email · emails · social · image · video · sms
**SEO 与发现**：seo-audit · ai-seo · programmatic-seo · site-architecture · schema · aso
**付费与分发**：ads · ad-creative
**测量与实验**：analytics · ab-testing
**留存**：churn-prevention
**增长工程**：referrals · community-marketing · co-marketing · lead-magnets · free-tools
**PR 与 launch**：public-relations · launch · pricing · competitors · competitor-profiling · directory-submissions
**销售赋能**：prospecting · revops · sales-enablement
**规划与研究**：marketing-plan · marketing-ideas · marketing-psychology · content-strategy · customer-research · product-marketing · offers

---

## 触发决策树（供 Codex 使用）

```
用户 query 类型？
├── 营销/增长/内容/SEO/CRO
│    → search-agent 用相应营销框架（4P/STP/AARRR/CBBE 等）
│    → Step 2 自动调用 marketing/* skill 增强
│    → Step 3 后续行动衔接对应 marketing skill
│
├── 财报/估值/投资/股价
│    → search-agent 用金融框架（深度财报/杜邦/DCF/护城河）
│    → Step 1 自动调用 finance-skills/data-providers
│    → Step 2 自动调用 finance-skills/market-analysis
│    → Step 3 可选调用 generative-ui 生成交互图表
│
├── 综合调研（战略/竞品/行业）
│    → search-agent 用战略框架（PEST/Porter/SWOT/3C 等）
│    → Step 1 混合调用 competitor-profiling + customer-research
│    → Step 2/3 走内置流程
│
└── 单一数字/最新价格
     → 跳过完整流程，直接调 yfinance-data / funda-data
```
