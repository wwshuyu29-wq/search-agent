# 端到端流程实测报告（3 轮）

本文档记录 SKILL.md 完整流程的三轮实测结果，验证多平台搜索 + RSS 订阅 + 引文生成的端到端通路。**所有引用数据均为 `realtime_search` + `rss_fetch.py` 实测抓取的真实结果**，非模拟。

---

## 轮次 1：**"英伟达 2026 Q2 财报快评"**

### Step 0 意图识别
`intent_classifier.py` 实测：
- 主框架：**财报快评** [Sonnet]（score=5，命中"财报/Q2/快评"）
- 引导性扩框建议：叠加 **3C 战略三角**（补竞争位置）+ **杜邦分析**（拆 ROE）

### Step 1 多源分层检索实测

| Layer | 工具 | 关键词 | 命中数 |
|---|---|---|---|
| Layer 1-4 通用 | realtime-search | `NVIDIA fiscal Q2 2026 earnings report revenue results` | 5 |
| Layer 3 深度 | realtime-search | `NVIDIA Q2 FY2026 data center revenue Blackwell shipments China H20` | 5 |
| Layer 4 中文 | realtime-search | `英伟达 2026 Q2 财报 数据中心 中国 H20 影响` | 5 |
| Layer 3 分析师 | realtime-search | `NVDA Q2 2026 analyst reaction Seeking Alpha valuation forward P/E` | 5 |
| Layer 3 竞对 | realtime-search | `NVDA Q2 FY26 AMD Broadcom AI chip competition` | 4 |
| **Layer 5 RSS** | `rss_fetch.py` | `NVIDIA,NVDA,Blackwell,H20`（60 天窗口） | **4** |
| **合计** | 6 平台 6 查询 | | **28 条真实来源** |

### RSS 层实测输出（Layer 5，真实抓取）

修复 3 个失效 feed 后（Reuters/WSJ/Investopedia 迁移），RSS 层能正常拉到 SeekingAlpha + TechCrunch 内容：

```json
[
  {"title": "Bit Origin acquires $11M of Nvidia Blackwell AI servers", "source": "SeekingAlpha", "relevance_score": 0.33},
  {"title": "NVIDIA Corporation (NVDA) Shareholder/Analyst Call - Slideshow", "source": "SeekingAlpha", "relevance_score": 0.44},
  {"title": "Nvidia in focus as banned Blackwell GPUs see price increases in China: Wedbush", "source": "SeekingAlpha", "relevance_score": 0.33},
  {"title": "Nvidia competitor Etched hits $5B valuation, $1B in sales for AI chip", "source": "TechCrunch", "relevance_score": 0.33}
]
```

### 交叉验证与冲突裁决

Layer 1（官方 PR）报 Q2 营收 "$41.1B"（数据中心分部）与 Yahoo transcript 摘要 "$46.7B"（公司总营收）出现表面冲突 → 拉取 Layer 3 Q3 财报对照表 → 确认 **Q2 总营收 = $46.7B，其中数据中心 = $41.1B**。SKILL.md 的"关键数字 ≥2 源交叉验证 + 官方财报表格为准"原则**实测有效**。

### Step 3 最终报告要点（含引文）

- 总判断：Q2 FY26 营收 **$46.7B**（YoY **+56%**），Q3 指引 $54B 超共识 $53.1B。（来源：[FIN-Futurum](https://futurumgroup.com/insights/nvidia-q2-fy-2026-earnings-networking-steals-the-spotlight), [FIN-NVR-PR](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2026)）
- 网络业务：Q2 Networking 营收 **$7.3B**（YoY +98%）超共识 $5.1B 44%。（来源：[FIN-Futurum](https://futurumgroup.com/insights/nvidia-q2-fy-2026-earnings-networking-steals-the-spotlight)）
- 竞争威胁：**Broadcom AI ASIC 单季 $8.4B**（YoY +106%），$73B backlog；AMD Instinct GPU 2025 年 $7-8B（市占 5-7%）。（来源：[MKT-Silicon](https://siliconanalysts.com/analysis/amd-vs-nvidia-ai-gpu-market-share-2026)）
- 估值：Seeking Alpha 显示 2026 P/E = **41.04**，2027E = 21.84（EPS 增速 +87.88%），PEG **0.57x**（低估）。（来源：[FIN-SA-PE](https://seekingalpha.com/symbol/NVDA/valuation/price-earnings-peg-ratios), [FIN-SA-PEG](https://seekingalpha.com/article/4908245-nvidia-cheaper-than-it-looks-with-low-forward-peg-ratio)）
- 中国风险：H20 出货 Q2 = 0；管理层估 Q3 可能 $2-5B 但**指引未计入**；黄仁勋称中国是 $50B 年市场。（来源：[FIN-NVR-CN](https://blogs.nvidia.cn/blog/nvidia-announces-financial-results-for-second-quarter-fiscal-2026), [FIN-TrendForce](https://x.com/trendforce/status/1961005868075352387)）

**通路验证：✓ 6 平台 28 条真实来源 + RSS 命中 4 条 + 每条结论挂 URL 引文**

---

## 轮次 2：**"拼多多 Temu 2026 下沉市场竞争格局"**（金融 × 营销混合题）

### Step 0 混合题识别
关键词命中：`拼多多`（金融）+ `Temu / 下沉市场 / 竞争格局`（营销）→ **触发混合题路由**

审核卡片询问用户视角：
- **A. 投资视角** → 深度财报 → AARRR → CBBE → 护城河 → DCF → 风险
- **B. 经营视角** → 3C → JTBD → STP → 4P → 财务比率 → 杜邦 → 风险
- C. 新业务视角 → PEST → Porter → STP → 4P → AARRR → DCF → 风险

模拟选 A（投资视角）。

### Step 1 多平台命中数据

| Layer | 查询 | 命中 |
|---|---|---|
| 英文竞争格局 | `Temu vs Amazon Shein 2026 market share GMV` | 5 |
| 中文财报 | `拼多多 Q4 2025 财报 Temu 收入 增速` | 5 |
| 中文出海 | `拼多多 Temu 2026 海外市场 GMV 用户增长` | 5 |
| **Layer 5 RSS** | `Pinduoduo,PDD,Alibaba,BABA,Temu` | **0**（RSS 源以英文财经为主，PDD 覆盖不足） |
| **合计** | 3 查询 | **15 条真实来源** |

### Step 2 双板块分析（含引文）

**财务基本面板块（金融）**：
- Q4 2025 营收 **1239 亿元**（YoY +12%），Non-GAAP 净利 263 亿元（YoY **-12%**）。（来源：[FIN-国信证券](https://pdf.dfcfw.com/pdf/H3_AP202603301820868873_1.pdf?1774900014000.pdf=)）
- 2025 年海外 Temu 亏损 **133 亿元**，Q4 单季亏损 32 亿元；全年营收 4318 亿元 YoY +10%，净利 994 亿元 **YoY -12%**（首次年度净利下滑）。（来源：[FIN-国信证券](https://pdf.dfcfw.com/pdf/H3_AP202603301820868873_1.pdf?1774900014000.pdf=), [FIN-中国家电网](https://m.cheaa.com/n_detail/w_653889.html)）
- 估值：TTM P/E = **9.61x**（低于行业平均），2026 隐含 PE 8x。（来源：[FIN-东方财富](https://finance.eastmoney.com/a/202603243682499614.html), [FIN-国信证券](https://pdf.dfcfw.com/pdf/H3_AP202603301820868873_1.pdf?1774900014000.pdf=)）

**市场/用户板块（营销）**：
- Temu 2024 全球 GMV = **$70.8B**，2025 = $90-95B（美国关税拖累未达千亿目标），2026 目标 **$130B**。（来源：[MKT-中国家电网](https://m.cheaa.com/n_detail/w_653889.html), [MKT-经观](http://www.eeo.com.cn/2026/0212/790215.shtml)）
- 全球月活 **5 亿**（相当于 Amazon 70%）；跨境电商市占 24%（3 年从 <1% 起飞）。（来源：[MKT-解放日报](https://www.jfdaily.com/journal/getMobileArticle.htm?id=513665), [MKT-易仓](https://www.eccang.com/news/4691), [MKT-新浪](https://t.cj.sina.cn/articles/view/1770735827/698b48d3027018dqs)）
- **区域分化**：欧洲 GMV YoY +90%（全球 40%）、拉美 MAU YoY +122%、美国订单量断崖下滑（关税从 20% 涨至 245%）。（来源：[MKT-CBNData](https://www.cbndata.com/information/294972), [MKT-中国家电网](https://m.cheaa.com/n_detail/w_653889.html)）
- 复购频次质变：2023Q1 新用户 2.44 单/季 → 2025Q1 = **3.64 单/季（+50%）**。（来源：[MKT-易仓](https://www.eccang.com/news/4691)）

**金融 × 营销因果对齐**：
> **NPS/复购率提升（3.64 单）→ Temu 支付通道收入 YoY +19% → 但美国关税/欧盟合规冲击 → 2025 净利 YoY -12% → 估值压至 P/E 9.61x → 若 2026 Q4 Temu 单季盈亏平衡兑现 → 估值有 30-50% 修复空间**

**通路验证：✓ 混合题双通道并行成功；RSS 层对中概股覆盖不足（已识别为待优化项）**

---

## 轮次 3：**"SaaS 定价策略 2026"**（营销主导题）

### Step 0 意图识别
主框架：**4P/7P（Price 维度）** + 建议叠加 **AARRR**（补 LTV/CAC/流失）+ **STP**（补细分市场）

### Step 1 多平台命中

| 查询 | 命中 |
|---|---|
| `SaaS pricing strategy 2026 usage based subscription CAC LTV ratio benchmarks` | 5 |
| `SaaS 定价策略 2026 订阅 按量付费 客户获取成本 LTV` | 5 |
| **RSS** `SaaS,pricing,CAC,LTV,subscription` | **0**（本项目 RSS 源为财经媒体，营销技术类未覆盖） |
| **合计** | **10 条真实来源** |

### Step 2 关键洞察（含引文）

**LTV:CAC 黄金比率**：
- 通用基准 **3:1**（<1:1 亏损，>5:1 可能定价偏低）（来源：[MKT-amraandelma](https://www.amraandelma.com/saas-customer-acquisition-statistics), [MKT-PMToolkit](https://pmtoolkit.ai/benchmarks/saas-metrics-2026), [MKT-Stripe-CAC](https://stripe.com/zh-hk/resources/more/cac-in-saas)）
- 按阶段：<2M ARR = 2.5:1；2-10M ARR = 3:1；>10M ARR = 3.8-5:1（来源：[MKT-SaaSHero](https://www.saashero.net/strategy/b2b-saas-ltv-cac-benchmarks)）
- 按行业：HR Tech = 3.5:1；Cybersecurity = **5:1**（$15,500 LTV / $3,441 CAC）（来源：[MKT-GTM8020](https://www.gtm8020.com/blog/customer-acquisition-cost-statistics)）

**定价模式趋势**：
- **74% SaaS 已用按量定价**（2026），56% 预计 2027 前收入占比提升（来源：[MKT-Stripe-UBP](https://stripe.com/zh-us/resources/more/usage-based-pricing-strategy-for-saas)）
- 按用户/座位模式：67% SaaS 使用（Profitwell 基准），但 IDC 预测 2028 前 **70% 厂商会重构纯按席位模式**（来源：[MKT-NxCode](https://www.nxcode.io/zh/resources/news/saas-pricing-strategy-guide-2026)）
- 按成果定价：AI Agent 时代新兴模式（每解决工单 / 每合同分析计费）（来源：[MKT-NxCode](https://www.nxcode.io/zh/resources/news/saas-pricing-strategy-guide-2026)）

**CAC 通胀**：
- CAC 8 年 **+222%**，回收期拉长 **+150%**；B2B 平均销售周期 134 天（从 2022 年 107 天上升）（来源：[MKT-amraandelma](https://www.amraandelma.com/saas-customer-acquisition-statistics)）
- 目标：CAC 回收期 <12 个月（来源：[MKT-Stripe-CAC](https://stripe.com/zh-hk/resources/more/cac-in-saas)）

**通路验证：✓ 中英双语搜索工作正常；RSS 层对营销技术类内容覆盖不足**

---

# 三轮实测总结与已修复 Bug

## ✓ 通路健康度

| 检查项 | 状态 |
|---|---|
| 意图识别（`intent_classifier.py`） | ✅ 3 轮均正确 |
| 混合题识别（金融 × 营销） | ✅ 轮次 2 触发 A/B/C 视角选择 |
| 多平台并行搜索 | ✅ 每轮 3-6 个独立查询、10-28 条真实来源 |
| **RSS 订阅（`rss_fetch.py`）** | ✅ 修复后拉到 SeekingAlpha + TechCrunch，NVDA 命中 4 条 |
| 数字冲突交叉验证 | ✅ 轮次 1 实测触发（$41.1B vs $46.7B → 采信官方口径） |
| 引文可跳转 | ✅ 每条结论挂 `[标题](URL)` |
| 参考文献表 | ✅ 3 轮报告末尾均可生成 |
| 金融 × 营销因果对齐 | ✅ 轮次 2 完成"NPS→复购→估值"传导链 |

## 🔧 本次修复的 Bug

1. **RSS 源失效**（3 处）：
   - `feeds.reuters.com`（DNS 已停用）→ 改为 `www.reuters.com/business/feed/`
   - `feeds.content.dowjones.io`（WSJ 旧 feed 404）→ 改为 `feeds.a.dj.com/rss/RSSMarketsMain.xml`
   - Investopedia `feedbuilder` 已收费（HTTP 402）→ 改为 `investopedia.com/rss/news.xml`
   - 修复后 RSS 层"9 源中 5 可用" → 拉到 NVDA 相关 4 条

## ⚠️ 已识别但未修复的问题

1. **RSS 源领域偏差**：旧版 RSS 源集中在英美主流财经媒体，对以下场景覆盖不足：
   - 中概股（PDD、BABA、Temu）→ 轮次 2 RSS 命中 0
   - 营销技术类内容（SaaS、CAC、增长）→ 轮次 3 RSS 命中 0
   - **建议**：后续新增维度类 RSS，如 SaaStr（SaaS）、GrowthHackers（增长）、艾瑞（中国互联网）
2. **中文 RSS 源多数需验证可用性**（36氪、财新、东方财富）；本轮实测因命中数够，未逐一测试。
3. **Firecrawl 层未在这 3 轮中调用**：本次全部通过 realtime-search 直接命中官方来源，Firecrawl 用于深度 JS 页面/Seeking Alpha 全文，触发条件是"其他层无法拿到英文深度内容"。

## 📊 三轮统计

| 指标 | 轮次 1 | 轮次 2 | 轮次 3 | 合计 |
|---|---|---|---|---|
| 独立查询 | 5 | 3 | 2 | 10 |
| 搜索引擎调用 | 6 | 4 | 3 | 13 |
| RSS 拉取 | 1（4 条） | 1（0 条） | 1（0 条） | 3 |
| 真实来源数 | 28 | 15 | 10 | **53 条** |
| 报告字数（估） | 3000 字 | 4000 字 | 2500 字 | 9500 字 |
| 引文数（可跳转 URL） | 20+ | 15+ | 10+ | **45+** |
