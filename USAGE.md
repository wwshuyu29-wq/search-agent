# search-agent 使用说明（Codex 版，产品/竞品调研场景）

一个给**百度地图团队**用的商业调研 skill，主要场景是**竞品新功能调研 / 行业趋势追踪 / 用户需求分析 / GTM 与营销策略研究**。基于 31 个战略/营销/金融框架驱动多源分层搜索，输出带引文可跳转的金字塔调研报告。

> 金融/估值能力（DCF、杜邦、Altman Z 等）仍保留在 skill 内部，遇到"投不投得起 XX 上市地图厂"这类金融题也能兜住，但不是主战场。

---

## 你会用它做什么（典型场景）

1. **竞品功能上新追踪** — 高德/谷歌地图/腾讯地图/Waze/Apple Maps 最近上了什么新功能、用户口碑如何
2. **新功能立项前的市场调研** — 立体导航 / AR 步导 / 车道级导航 / 通勤模式，行业进到哪一步了、谁做得好
3. **用户需求与痛点挖掘** — 打车、骑行、公交、货车导航等垂直用户的 JTBD
4. **GTM / 营销策略研究** — 竞品新功能的 PR 稿、社交传播、KOL 打法
5. **行业趋势与政策** — 高精地图资质、智驾、车路协同、鸿蒙生态等宏观变化
6. **B 端商务/合作情报** — 谁跟车企签了、谁拿了 L3 许可、导航 SDK 谁占了

---

## 前置：Codex 是否能直接使用？

**能。** 当前部署方式：软链 `~/.codex/skills/search-agent` → `Documents/search-agent-skill3.0`，Codex 启动即识别（系统 reminder 里已能看到 `search-agent` 和 `news-aggregator-skill`）。

**一次性准备：**

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
```

（营销/金融外部 skill 已 vendor 在 `vendor/` 目录，无需额外 clone；有代理可选装 `~/.codex/skills/news-aggregator-skill`。）

---

## t1 — 需求理解 & 框架审核

**你来做：**
- 告诉 Codex 调研需求。示例：
  - "帮我查一下高德地图最近半年上了什么新功能，重点看车道级导航和 AR 步导"
  - "调研一下 Waze 的用户社群运营方法，我们百度地图想学"
  - "全网找找 iOS 26 上苹果地图的更新，对我们有什么威胁"
- 查看 Codex 输出的【审核卡片】，确认或修改：
  - **主框架 / 框架组合**（例："竞品对比 → 同行竞争对比 + 3C + Porter 五力"）
  - **拆解维度**是否覆盖你关心的点（例：功能矩阵 / 用户口碑 / 传播打法 / 商业化路径）
  - **搜索关键词**（Codex 会自动扩展词族，你可增删）
  - **信息源勾选**（应用商店 / 官方 blog / 中文媒体 / 微博/小红书/B站 UGC / GitHub / 内网知识库）
- 回复"确认"或"改成 XX"

**Codex 来做：**
- 从 31 个框架里推荐 Top 3。**产品/竞品场景的默认路由：**

| 你的问题 | Codex 默认框架 |
|---|---|
| "XX 上了什么新功能" | 竞品对比 + JTBD |
| "行业发展到哪一步了" | PEST + Porter 五力 |
| "用户为什么用 XX 不用我们" | JTBD + CBBE + Customer Journey |
| "XX 是怎么做增长的" | AARRR + 3C |
| "新功能立项要看什么" | 3C + STP + JTBD + PEST |
| "XX 品牌力/口碑" | CBBE + Customer Journey |
| "XX 的商业化 / 变现" | 4P/7P + 商业模式画布 |
| "XX 的 GTM / 传播" | STP + 4P + AIDA |

- 自动扩展关键词族。**地图领域的自动扩展举例：**
  - "AR 导航" → AR Navigation, AR walking, LiveView, 实景导航, 步行 AR
  - "车道级" → Lane-level, HD Map, 高精地图, 车道级导航, HDLive
  - "打车" → Ride-hailing, 网约车, 滴滴, T3, 打车聚合, 一键打车
  - "车机" → IVI, HUD, CarPlay, Android Auto, 鸿蒙座舱, 车联网
- 遇到"金融×营销混合题"（如"高德 IPO 前值不值得买"）会请你选视角

**调用的 Skill：**
- **search-agent** 内核 — 意图识别 + 框架推荐
- **brainstorming** — 需求模糊时追问
- **marketing/marketing-ideas** — 你说"帮我想想调研角度"时先发散
- **marketing/customer-research** — JTBD / 用户画像相关时挂载

**⛳ 闸门①：你必须回复"确认"或修改意见，Codex 才会开始搜索。**

---

## t2 — 多源分层信息检索（这一步是重点）

**你来做：**
- 通常无需操作，等 Codex 汇总
- 出现"两个源数字对不上"或"缺关键证据"时，Codex 会停下让你选口径

**Codex 来做（按产品调研场景重排的信息源分层）：**

- **Layer 1 官方源**（最高置信度）
  - 竞品官网 / 产品 blog / release notes（例：`site:mobile.gaode.com`、`site:blog.google/products/maps`）
  - App Store / Google Play / 华为应用商店的版本更新历史 + 用户评论
  - 官方微信公众号（走 Firecrawl + Sogou 微信搜索）
- **Layer 2 深度媒体**
  - 36氪 / 晚点 LatePost / 财经十一人 / 远川研究所 / 极客公园 / 雷锋网 / 钛媒体
  - 英文侧：TechCrunch / The Verge / Ars Technica
- **Layer 3 UGC 与社交口碑**
  - 微博 / 小红书（消费者视角）/ B 站（评测视频）/ 知乎（深度讨论）/ 虎扑
  - Reddit r/GoogleMaps r/waze r/iOS / HN / V2EX
- **Layer 4 应用商店与社群**
  - App Annie / 七麦数据 / SensorTower 类替代（走 Firecrawl 抓页面）
  - 微信群/官方社群公告（用户主动补充）
- **Layer 5 财经 RSS 聚合**（51 个源）— 拿资本市场对该功能的解读
- **Layer 5b 实时热榜**（news-aggregator-skill）— HN / 微博热搜 / GitHub Trending / Product Hunt
- **Layer 6 内网**（可选）— enterprise-search + ku-doc-manage 的百度地图内部研究报告

**产品/竞品调研的搜索关键词构建策略：**
- **竞品功能类**：`竞品名 + 功能关键词 + "上线 / 更新 / 发布 / release"` + 时间词
- **用户口碑类**：`竞品名 + "评测 / 使用体验 / 好用吗 / 吐槽 / bug"`
- **技术趋势类**：`技术名 + "白皮书 / 技术架构 / 实现原理"` + 学术源
- **商业化类**：`竞品名 + "定价 / 收费 / 会员 / 商户 / 合作"`

**抓取规则：** `relevance_score >= 0.6` 才做全文，每次最多 5 篇。

**调用的 Skill：**
- **firecrawl_search.py** — 英文深度、JS 渲染、官方 blog、Reddit
- **realtime-search** — Brave 官方 + 百度中文
- **baidu-search** — 中文兜底
- **finance-rss-reader** — 51 个 RSS 源 + Firecrawl 补齐社交源（微博/知乎/雪球/B站/小红书）
- **news-aggregator-skill** — 8 大热榜（HN / 微博 / V2EX / GitHub / PH / 36氪 / 华尔街见闻 / 腾讯）
- **agent-reach** — 小红书 / B站 / Reddit / LinkedIn 定向抓取
- **marketing/competitor-profiling** — 竞对完整档案（定位 / GTM / 团队 / 融资）
- **marketing/customer-research** — 用户访谈 / JTBD
- **marketing/directory-submissions** — Product Hunt / G2 / Capterra 情报
- **enterprise-search + ku-doc-manage** — 内网研究报告（仅内网）

**产出：** 统一的 YAML 源清单，每条含 `source_id / title / publisher / publish_date / url / confidence / key_facts / full_text_fetched`

**source_id 前缀：** FC (Firecrawl) / RS (realtime-search) / BD (baidu) / RSS / SOC (社交/热榜) / MKT (marketing skill) / ES (内网) / KU (知识库)

**⛳ 闸门：数字冲突或缺关键源时暂停请你选口径。**

---

## t3 — 结构化分析（按框架维度）

**你来做：**
- 等待分析产出（无需操作）
- Codex 提示"证据不足"时决定是否补检索

**Codex 来做：**
- 按选定框架的子维度组织内容，例：
  - **竞品对比** — 三栏对比表（我方 / 竞品 A / 竞品 B）× 功能 / 用户口碑 / 商业化 / 迭代节奏
  - **JTBD** — 每个用户任务的"当 [情境] 时，我想 [动机]，以便 [预期结果]"
  - **AARRR** — 5 环节转化率 + LTV/CAC 健康度
  - **CBBE** — 4 层品牌资产金字塔 + 每层量化指标
  - **PEST** — 政治/经济/社会/技术四维，每维 200-300 字 + ≥1 条数据
  - **Porter 五力** — 每一力给强度评级 + ≥2 条依据
- 每条结论标 `source_id + URL`
- 区分**事实 / 计算 / 假设 / 判断**
- 关键数字 ≥2 源交叉验证

**调用的 Skill（产品/竞品场景常用）：**
- **marketing/customer-research** — JTBD 陈述、用户画像
- **marketing/competitor-profiling** — 竞对档案深度写入
- **marketing/analytics + ab-testing** — Customer Journey 转化
- **marketing/product-marketing** — 4P Product 维度
- **marketing/pricing** — 4P Price 维度
- **marketing/social + public-relations** — CBBE / 传播层
- **marketing/seo-audit + programmatic-seo** — AARRR/Acquisition 检查

---

## t4 — 金字塔调研报告生成

**你来做：**
- 等待报告生成

**Codex 来做：**
- **结论先行**：一句话总判断 + 3 条支撑理由（附置信度和 source_id）+ 主要风险
- 按框架维度展开正文，每段 ≤150 字，重要数字**加粗**，趋势用 ↑↓→
- 竞品对比场景强制加**三栏对比表**
- 末尾附**风险与不确定性表格**（触发条件 / 影响 / 概率 / 来源）
- 末尾附**参考文献表**：编号 / 标题 / 发布方 / 日期 / 置信度 / 可跳转链接

**调用的 Skill：**
- **finance-skills/generative-ui** — 竞品矩阵/功能雷达图转 HTML/SVG（Web 交付时）
- **humanizer-zh** — 去 AI 味终检

**产出：** `output/[主题]_report_YYYYMMDD.md`

**⛳ 闸门②：报告输出后，让你校验引文和结论，回复"通过"或"改 XX"。**

---

## t5 — 你终审 & 修订

**你来做：**
- 查看报告 + 引文表
- 提出意见，例如：
  - "竞品对比表少了 Waze 的语音社交功能"
  - "把'用户不满意导航语音'这条改成'待验证'，只有一个源"
  - "加一段：如果我们跟进这个功能，需要哪些前置资源"
- 最多 3 轮修订

**Codex 来做：**
- 把你的意见结构化（位置 / 问题 / 所需改动 / 来源支撑）
- 只按修订计划执行，不擅自改动其他部分
- 需要补数据时回到 t2 补检索

**⛳ 闸门：修订计划里若需要"新事实"或存在冲突，Codex 暂停请你确认。**

---

## t6 — 后续行动衔接（可选）

调研完成后，Codex 可直接衔接下游动作：

| 你说 | Codex 调 | 场景 |
|---|---|---|
| "写个新功能立项 brief" | brainstorming + writing-plans | 立项文档 |
| "起一个 PR 稿" | marketing/launch + copywriting + public-relations | 新功能发布 |
| "帮我起社交传播文案" | marketing/social + copywriting | 微博/小红书 |
| "做落地页文案" | marketing/copywriting + cro | 落地页 |
| "写 KOL 投放脚本" | marketing/social + ad-creative | 抖音/B站 |
| "做用户访谈提纲" | marketing/customer-research | 用户研究 |
| "起竞品监控周报模板" | content-strategy + writing-plans | 长期监控 |
| "输出对外分享稿" | copywriting + copy-editing + humanizer-zh | 内部分享 |

---

## 所有确认闸门汇总

| 闸门 | 触发条件 | 你需要做什么 |
|---|---|---|
| **框架确认（t1）** | Codex 输出审核卡片 | 回复"确认"或修改框架/维度/关键词/信息源 |
| **视角选择（t1）** | 命中金融×营销混合题 | 选投资/经营/新业务视角 |
| **来源冲突（t2）** | 数字或事实两源对不上 | 指定采信口径 |
| **引文校验（t4）** | 报告输出后 | 通过或提出修订意见 |
| **修订计划冲突（t5）** | 需要新事实或意见冲突 | 确认是否继续 / 补哪份资料 |

---

## Skill 快速参考

| Skill | 中文说明 | 在产品调研里的调用时机 |
|---|---|---|
| **search-agent 内核** | 意图识别 + 框架推荐 + 5 层检索调度 + 金字塔生成 | 全流程 |
| brainstorming | 头脑风暴 | 立项前想调研角度、Brief 模糊追问（t1） |
| firecrawl_search.py | 英文深度抓取 | 竞品官方 blog、Reddit、TechCrunch（t2） |
| realtime-search | Brave + 百度双引擎 | 官方源 + 中文媒体（t2） |
| baidu-search | 中文兜底 | 中文长尾内容（t2） |
| finance-rss-reader | 51 个财经/科技 RSS + Firecrawl 补齐 | 36氪/晚点/远川/华尔街见闻等（t2） |
| **news-aggregator-skill** | 8 大热榜实时 | 竞品发布首日的社交扩散量、GitHub 相关项目热度（t2） |
| **agent-reach** | 小红书/B站/Reddit/LinkedIn 定向 | UGC 口碑、评测视频、职位变动信号（t2） |
| **marketing/competitor-profiling** | 完整竞对档案 | 竞品维度必调（t2/t3） |
| **marketing/customer-research** | JTBD / 用户访谈 | 用户视角调研（t2/t3） |
| marketing/directory-submissions | Product Hunt / G2 情报 | 海外竞品调研（t2） |
| marketing/product-marketing | 4P Product | 竞品功能定位（t3） |
| marketing/pricing | 4P Price | 竞品定价/会员/商户体系（t3） |
| marketing/analytics + ab-testing | Customer Journey | 用户路径分析（t3） |
| marketing/social | 社交策略 | CBBE 传播层 + t6 后续文案 |
| marketing/launch + public-relations | 发布 & PR | t6 新功能上线 |
| marketing/copywriting / copy-editing | 文案 & 编辑 | t6 对外产出 |
| finance-skills/generative-ui | 交互式图表 | t4 Web 交付时的竞品雷达图 |
| humanizer-zh | 去 AI 味终检 | t4 报告收尾、t6 文案收尾 |
| enterprise-search + ku-doc-manage | 内网研究报告 | 若百度内网有既往调研，先查内网（t2） |

---

## 核心硬性规则

1. **框架先于搜索** — 未确认框架前不启动检索
2. **官方源优先** — 竞品官网 / release note / 应用商店更新 > 深度媒体 > UGC 口碑
3. **引文透明** — 每条结论绑 source_id + 可跳转 URL；末尾必须有参考文献表
4. **区分事实 / 计算 / 假设 / 判断**
5. **≥2 源交叉验证** — 单源关键结论标"待验证"
6. **UGC 只作情绪信号** — 小红书/微博/B站 弹幕的评价可以进"用户口碑"章节但 `confidence=low`，不作事实断言
7. **数字规范** — DAU/MAU/月活/覆盖率等必附口径、时点、来源
8. **两个闸门不可省** — 框架审核 + 引文校验
9. **UGC 不代表全体用户** — 报告结论必须结合样本量与代表性描述
10. **人工确认才可归档**

---

## 一张图看懂全流程

```
你提竞品/功能调研需求
    ↓
[t1] 意图识别 & 框架审核 ← ⛳ 你确认框架 / 视角 / 关键词
    ↓
[t2] 5 层检索（官方 → 媒体 → UGC → 应用商店 → 热榜/RSS）
    ↓（数字冲突⛳ 你选口径）
[t3] 按框架结构化分析（事实/计算/假设/判断）
    ↓
[t4] 金字塔报告生成（三栏对比表 + 引文表） ← ⛳ 你校验
    ↓
[t5] 修订（最多 3 轮）← ⛳ 修订计划冲突时你确认
    ↓
[t6] 后续行动（PR 稿 / 社交文案 / 立项 brief / 监控周报，可选）
```

---

## 快速触发模板（百度地图团队日常场景）

```
# 竞品新功能追踪
用 search-agent 帮我查一下高德地图最近三个月上了什么新功能，重点看车道级导航、
   AR 步导、通勤模式，输出对比表。

# 单一功能深挖
调 search-agent 深入调研一下谷歌地图的 Immersive View，覆盖：技术实现、用户口碑、
   商业化路径，用 JTBD + Porter 五力 组合。

# 用户需求挖掘
用 search-agent 从 JTBD 视角挖一下打车用户在地图里的核心任务和痛点，UGC 优先。

# 品牌力对比
调 search-agent 对比百度地图 vs 高德地图 vs 腾讯地图的品牌力，用 CBBE + Customer Journey。

# 立项前市场调研
用 search-agent 帮我调研 AR 步导这个方向，全球做得好的有哪些，
   用 PEST + 3C + STP 组合，重点看技术成熟度和用户接受度。

# 竞品营销打法
调 search-agent 分析 Waze 的社群运营和 UGC 激励机制，我们地图团队想学。

# 政策与资质
用 search-agent 查一下高精地图资质在国内 2026 的最新政策，谁拿到牌照、
   对导航行业影响是什么。

# 车厂合作情报
调 search-agent 帮我盘一下 2026 年地图厂商和车企的合作动态，重点看鸿蒙座舱。

# 实时热点
用 search-agent 扫一下最近 48 小时地图/导航相关的社交讨论和媒体报道。
```

---

## CLI 备用（脚本党）

Codex prompt 走不通时可以纯 CLI：

```bash
cd ~/.codex/skills/search-agent
python3 bin/search_agent.py "高德地图 2026 上半年新功能盘点"           # 交互式（有审核点）
python3 bin/search_agent.py "高德地图 2026 上半年新功能盘点" --auto    # 自动模式（跳过审核点①）
```

CLI 模式不推荐生产使用——跳过了框架审核这个人工闸门。

---

## 与金融投资场景的区别

skill 内部仍保留 10 个金融框架（DCF / 杜邦 / 护城河 / Altman Z / Beneish M 等）和全套 finance-skills 挂载，遇到"高德要 IPO 值不值得关注"、"Waze 被谷歌收购的价格逻辑"这类混合题也能兜住。但**默认路由已经调整**：产品/竞品调研问题不会强推金融框架，只在明确出现"估值 / 值不值得投 / 财报"等信号词时才启用。
