# search-agent 使用说明（Codex 版）

一个基于 31 个战略/营销/金融框架、多源分层搜索的商业调研 skill。以下按 t1 → t6 的流程讲清每一步「你」和「Codex」各做什么，以及触发的 skill 和确认闸门。

---

## 前置：Codex 是否能直接使用？

**能。** 当前部署方式：软链 `~/.codex/skills/search-agent` → `Documents/search-agent-skill3.0`，Codex 启动即识别（系统 reminder 里已能看到 `search-agent` 和 `news-aggregator-skill` 两个 skill）。

**你只需一次性做的准备：**

```bash
# 环境变量（写进 ~/.zshrc）
export FIRECRAWL_API_KEY="fc-a5279d633c4f4636b2592bc31a431770"

# Python 依赖
pip3 install -r ~/.codex/skills/search-agent/requirements.txt
pip3 install -r ~/.codex/skills/news-aggregator-skill/requirements.txt
```

**同事拿到代码怎么跑：**

```bash
git clone git@github.com:wwshuyu29-wq/search-agent.git ~/.codex/skills/search-agent
git clone https://github.com/coreyhaines31/marketingskills.git ~/.codex/skills/marketing   # 或用 vendor/
git clone https://github.com/himself65/finance-skills.git ~/.codex/skills/finance
# news-aggregator-skill 可从 cocoloop 装或直接下载
```

---

## t1 — 意图识别 & 框架审核

**你来做：**
- 告诉 Codex 调研需求（对象 + 目的），例如：「帮我调研拼多多 Temu 值不值得投」
- 查看 Codex 输出的【审核卡片】，确认或修改：
  - 主框架 / 框架组合是否合适（例：投资题默认「深度财报 + 杜邦 + 护城河 + DCF/相对估值 + 风险专项」）
  - 拆解维度是否覆盖你的关注点
  - 关键词（中文 / 英文 / 扩展词族）
  - 信息源勾选（官方 / 业绩会 / 深度分析 / 中文媒体 / RSS / 社交热榜）
- 混合题（金融 × 营销）需选视角：[A] 投资视角 / [B] 经营视角 / [C] 新业务评估
- 回复「确认」或「调整为 XX」

**Codex 来做：**
- 从 31 个框架里推荐 Top 3（或预定义组合）
- 复杂题（"全面 / 系统 / 综合" 或 >50 字）自动升级为框架组合
- 单一意图给出「引导性扩框建议」（例：只问竞争 → 建议叠加 SWOT）
- 自动扩展关键词族（例：AI → LLM/GPT/Claude/Agent/RAG/大模型）
- 识别金融×营销混合题并给出 3 种视角组合

**调用的 Skill：**
- **search-agent** 内置意图分类器 → 框架推荐
- **brainstorming** — 需求模糊时追问澄清
- **finance-skills/skill-creator** — 遇到未覆盖场景时动态生成分析 skill

**⛳ 闸门①：你必须回复"确认"或修改意见，Codex 才会开始检索。不确认它会一直等。**

---

## t2 — 多源分层信息检索

**你来做：**
- （通常无需操作）等待 Codex 完成 5 层检索
- 存在数字冲突或关键源缺失时，Codex 会暂停并让你选采信哪个口径

**Codex 来做：**
- Layer 1 官方（IR / SEC EDGAR / 交易所披露）→ Brave `site:` + `filetype:pdf`
- Layer 2 业绩会 Transcript → `earnings call transcript`
- Layer 3 英文深度（Seeking Alpha / FT / Bloomberg）→ Firecrawl
- Layer 4 中文媒体（36氪 / 财新 / 东方财富）→ realtime-search 百度
- Layer 5 财经 RSS 聚合（51 个源，含 16 中文深度源）→ `lib/finance-rss-reader`
- Layer 5b 社交/热榜（HN / 微博 / V2EX / 华尔街见闻 / 36氪）→ `news-aggregator-skill`
- Layer 6 垂直数据 → `yfinance-data` / `funda-data` / `competitor-profiling` 等
- 抓取规则：`relevance_score >= 0.6` 才做全文，每次最多 5 篇
- 统一整理成 YAML 源清单，每条含 `source_id / title / publisher / publish_date / url / confidence / key_facts`

**调用的 Skill：**
- **firecrawl_search.py** — 英文深度、JS 渲染、SEC / Seeking Alpha
- **realtime-search** — Brave 官方 / 百度中文
- **baidu-search** — 中文兜底
- **finance-rss-reader**（Mode B workflow）— 51 个财经 RSS 源
- **news-aggregator-skill** — 8 大热榜实时源（HN / 微博 / V2EX / GitHub Trending / PH / 36氪 / 华尔街见闻 / 腾讯）
- **finance-skills/yfinance-data / funda-data** — 结构化金融数据
- **marketing/competitor-profiling / customer-research** — 竞对与用户情报

**产出：** YAML 源清单（source_id 前缀：FC / RS / BD / RSS / SOC / FIN / MKT）

**⛳ 闸门：数字冲突或缺关键源时，Codex 暂停请你选口径。**

---

## t3 — 结构化分析（按框架维度）

**你来做：**
- 等待分析产出（无需操作）
- 只在 Codex 提示"证据不足，是否补检索"时回复

**Codex 来做：**
- 按选定框架的子维度组织内容（例：PEST 四维 / 杜邦拆解 / DCF 三情景 / AARRR 五漏斗）
- 每条结论标注 `source_id` 与 URL：`[结论]（来源：[FC001](URL), [RS003](URL)）`
- 区分 **事实 / 计算 / 假设 / 判断** 四类
- 关键数字 ≥2 源交叉验证，单源标"待验证"
- 遵守框架质量红线（如 DCF 必须给三情景 + WACC 各参数来源；SWOT 每象限 ≥3 条条目）

**调用的 Skill（按框架自动选）：**
- **finance-skills/company-valuation** — DCF + 相对 + SOTP 三角
- **finance-skills/earnings-recap / earnings-preview** — 财报快评/预告
- **finance-skills/estimate-analysis** — 预期修正分析
- **marketing/product-marketing / pricing** — 4P 相关维度
- **marketing/customer-research** — JTBD / 用户画像
- **marketing/analytics + ab-testing** — Customer Journey

**产出：** 按框架的结构化分析中间稿

---

## t4 — 金字塔调研报告生成

**你来做：**
- 等待报告生成（无需操作）

**Codex 来做：**
- 结论先行：一句话总判断 + 3 条支撑理由（每条附置信度和 source_id）+ 主要风险
- 按框架维度展开正文，每段 ≤150 字，重要数字加粗，趋势用 ↑↓→
- 组合报告增加"执行摘要 + 分框架章节 + 综合结论"
- 混合题分双板块：财务基本面 + 市场/用户 + 综合因果对齐（例：NPS↑ → 复购↑ → LTV↑ → 估值↑）
- 末尾附**风险与不确定性表格**（触发条件 / 影响 / 概率 / 来源）
- 末尾附**参考文献表**：每篇被引资料列出编号 / 标题 / 发布方 / 日期 / 置信度 / 可跳转原文链接

**调用的 Skill：**
- **finance-skills/generative-ui** — 估值模型/财务比率转 HTML/SVG widget（Web 交付时）
- **finance-skills/options-payoff** — 期权策略盈亏图
- **humanizer / humanizer-zh** — 去 AI 味终检

**产出：** `output/[主题]_report_YYYYMMDD.md`（金字塔结构 + 引文表）

**⛳ 闸门②：报告输出后，Codex 会让你校验引文和结论，等你说"通过"或"改 XX"。**

---

## t5 — 你终审 & 修订

**你来做：**
- 查看报告 + 引文表
- 提出修改意见（结论过强 / 某个 source 不可信 / 缺某维度分析 / 要加视角 X）
- 最多 3 轮修订

**Codex 来做：**
- 把你的意见结构化（位置 / 问题 / 所需改动 / 来源支撑）
- 只按修订计划执行，不擅自改动其他部分
- 需要补数据时回到 t2 补检索

**⛳ 闸门：修订计划里若需要"新事实"或存在冲突，Codex 暂停请你确认。**

---

## t6 — 后续行动衔接（可选）

**你来做：**
- 决定是否让 Codex 基于报告生成后续产物

**Codex 来做：** 根据你的诉求自动衔接 skill：

| 你说 | Codex 调 |
|---|---|
| 写营销方案 | `marketing/marketing-plan` |
| 产品发布稿 | `marketing/launch` + `copywriting` |
| 落地页 | `marketing/cro` + `copywriting` |
| 邮件序列 | `marketing/emails` |
| PR 稿 | `marketing/public-relations` |
| SEO 修复 | `marketing/seo-audit` |
| 定价建议 | `marketing/pricing` + `offers` |
| 融资 pitch | `finance-skills/startup-analysis` + `company-valuation` |
| 交易信号 | `finance-skills/sepa-strategy` + `stock-correlation` |

---

## 所有确认闸门汇总

| 闸门 | 触发条件 | 你需要做什么 |
|---|---|---|
| **框架确认（t1）** | Codex 输出审核卡片 | 回复"确认"或修改框架/维度/关键词/信息源 |
| **视角选择（t1）** | 命中金融×营销混合题 | 选 A/B/C 视角组合 |
| **来源冲突（t2）** | 数字或事实两源对不上 | 指定采信口径 |
| **引文校验（t4）** | 报告输出后 | 通过或提出修订意见 |
| **修订计划冲突（t5）** | 需要新事实或意见冲突 | 确认是否继续 / 补哪份资料 |

---

## Skill 快速参考

| Skill | 中文说明 | 调用时机 |
|---|---|---|
| **search-agent 内核** | 意图识别 + 框架推荐 + 5 层检索调度 + 金字塔生成 | 全流程 |
| brainstorming | 头脑风暴 | 需求模糊追问（t1） |
| firecrawl_search.py | 英文深度抓取 | 英文深度源（t2） |
| realtime-search | Brave + 百度双引擎 | 官方 + 中文（t2） |
| baidu-search | 中文兜底 | Realtime 空结果时（t2） |
| finance-rss-reader | 51 个财经 RSS + Firecrawl 补齐 | 财经聚合（t2） |
| **news-aggregator-skill** | 8 大热榜实时（HN / 微博 / V2EX 等） | 社交/情绪面（t2） |
| finance-skills/yfinance-data | 美股结构化数据 | 股价/财务/期权（t2） |
| finance-skills/funda-data | 分析师研究合成 | 深度金融数据（t2） |
| finance-skills/company-valuation | DCF + 相对 + SOTP | 估值分析（t3） |
| finance-skills/earnings-recap | 财报快评 | 财报后（t3） |
| marketing/customer-research | JTBD / 用户访谈 | 用户维度（t3） |
| marketing/competitor-profiling | 完整竞对档案 | 竞对维度（t3） |
| finance-skills/generative-ui | 交互式估值 widget | Web 交付（t4） |
| humanizer / humanizer-zh | 去 AI 味终检 | 报告收尾（t4） |
| marketing/copywriting / launch / seo-audit 等 | 后续行动 | 报告后（t6） |

---

## 核心硬性规则（必读）

1. **框架先于搜索** — 未确认框架前不检索
2. **官方来源优先** — Layer 1 > 2 > 3 > 4 > 5，冲突时官方胜出
3. **引文透明** — 每条结论必须绑 source_id + URL，末尾必须有参考文献表
4. **数字规范** — 所有数字必附「期间 + 币种 + 同比/环比口径」
5. **区分事实/计算/假设/判断** — 四类分别标注
6. **≥2 源交叉验证** — 关键数字单源要标"待验证"
7. **不确定项标置信度：低** — 禁用"可能/或许/大概"
8. **两个闸门不可省** — 框架审核 + 引文校验
9. **金融结论加免责声明** — DCF/杜邦结果不构成投资建议
10. **人工确认才可归档** — 终稿必须你回复"通过"

---

## 一张图看懂全流程

```
你提需求
    ↓
[t1] 意图识别 & 框架审核 ← ⛳ 你确认框架 / 视角
    ↓
[t2] 5 层检索 + Source YAML 整理
    ↓（有数字冲突⛳ 你选口径）
[t3] 按框架结构化分析（事实/计算/假设/判断）
    ↓
[t4] 金字塔报告生成 ← ⛳ 你校验引文
    ↓
[t5] 修订（最多 3 轮）← ⛳ 修订计划冲突时你确认
    ↓
[t6] 后续行动（营销方案 / PR 稿 / 融资 pitch 等，可选）
```

---

## 快速触发模板

```
# 财报快评
用 search-agent 帮我做百度 2026Q1 财报快评

# 投资判断
调 search-agent 分析 NVDA 值不值得投

# 竞品对比
用 search-agent 对比高德地图和百度地图，重点看市场份额和用户增长

# 营销策略
调 search-agent 帮我看 Temu 的 GTM 打法，用 4P + AARRR 组合

# 混合题
用 search-agent 从 CMO 视角评估小米汽车的品牌力对股价影响

# 全网热点扫描
用 search-agent 帮我扫一下最近 24 小时的 AI 大新闻
```

---

## CLI 备用（脚本党）

Codex prompt 走不通时可以纯 CLI：

```bash
cd ~/.codex/skills/search-agent
python3 bin/search_agent.py "百度2026Q1财报分析"           # 交互式（有审核点）
python3 bin/search_agent.py "百度2026Q1财报分析" --auto    # 自动模式（跳过审核点①）
```

CLI 模式不推荐生产使用——它跳过了框架审核这个人工闸门。
