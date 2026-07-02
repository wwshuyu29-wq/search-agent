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

## 全流程逻辑一览（先看这个再往下）

一个调研任务被拆成 6 个阶段，不是随便拆的——每个阶段解决的是一个**独立会犯错的环节**，前一步没到位后面必然翻车。

```
[t1] 需求理解 & 框架审核    → 解决"没想清楚在问什么就开搜"的问题
    ↓
[t2] 多源分层信息检索       → 解决"只搜一处就下结论"的问题
    ↓
[t3] 结构化分析             → 解决"堆资料不出观点"的问题
    ↓
[t4] 金字塔报告生成         → 解决"读者看不到要点"的问题
    ↓
[t5] 人工终审 & 修订        → 解决"AI 幻觉与我方视角错位"的问题
    ↓
[t6] 后续行动衔接（可选）    → 解决"调研做完就烂在文件夹里"的问题
```

**每个阶段的分工原则：**
- 需要"判断价值观 / 领域 know-how"的部分 → 你来
- 需要"重复劳动 / 大量并发 / 格式规整"的部分 → Codex 来
- 存在"如果 AI 决定错了成本很高"的选择 → 强制人工闸门

**为什么 skill 要分这么细：**
- 每个 skill 都是一个**已经封装好的领域打法**（例：`marketing/customer-research` 内置了 JTBD 访谈脚本、`marketing/competitor-profiling` 内置了竞对档案的 12 个必查字段）
- 让通用 LLM 直接推理这些内容会漏项、格式不稳定、且没有"专家该做的动作"（例：LLM 直接写"竞品分析"，它不会主动去查融资和团队变动）
- 走 skill = 强制 Codex 按专家清单动作，结果稳定 + 覆盖度高

---

## t1 — 需求理解 & 框架审核

**这一阶段在做什么：** 把用户的一句话需求，翻译成"用哪个分析框架 + 拆成哪几个维度 + 用哪些关键词 + 从哪些源找"。

**为什么必须先做这一步：** 90% 的调研翻车都发生在"没搞清楚在调研什么"就开始搜。同样一句"调研高德地图"，可能是问"新功能"、"用户口碑"、"财务表现"、"增长打法"——不同意图对应完全不同的信息源和分析框架。这一步就是把模糊需求变成可执行的调研 spec。

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
- 从 31 个框架里推荐 Top 3。**下面表格覆盖全部 31 个框架的触发路由**，前 8 行是产品/竞品调研最常用的（★），后面是完整战略/营销/金融清单：

| 你的问题 | Codex 默认框架 | 归类 |
|---|---|---|
| ★ "XX 上了什么新功能" | 同行竞争对比 + JTBD | 战略+营销 |
| ★ "行业发展到哪一步了" | PEST + Porter 五力 | 战略 |
| ★ "用户为什么用 XX 不用我们" | JTBD + CBBE + Customer Journey | 营销 |
| ★ "XX 是怎么做增长的" | AARRR + 3C | 营销+战略 |
| ★ "新功能立项要看什么" | 3C + STP + JTBD + PEST | 混合 |
| ★ "XX 品牌力/口碑" | CBBE + Customer Journey | 营销 |
| ★ "XX 的商业化 / 变现" | 4P/7P + 商业模式画布 | 营销 |
| ★ "XX 的 GTM / 传播" | STP + 4P + AIDA | 营销 |
| "XX 整体怎么样 / 值不值得合作" | **SWOT**（优势·劣势·机会·威胁） | 战略 |
| "XX 哪些业务值得押注 / 砍掉" | **BCG 波士顿矩阵**（明星·金牛·问号·瘦狗） | 战略 |
| "多业务集团精细化管理" | **GE 麦肯锡矩阵**（吸引力 × 竞争力 3×3） | 战略 |
| "XX 组织能力 / 执行力" | **麦肯锡 7S**（战略·结构·系统·风格·员工·技能·价值观） | 战略 |
| "XX 的价值创造在哪一环" | **Porter 价值链**（主活动 5 + 支持活动 4） | 战略 |
| "XX 如何差异化 / 新品类" | **蓝海战略 ERRC**（剔除·减少·增加·创造） | 战略 |
| "XX 怎么增长 / 扩张" | **Ansoff 增长矩阵**（渗透·开发·产品·多元化） | 战略 |
| "XX 用户分层 / 高价值客户" | **RFM**（Recency·Frequency·Monetary） | 营销 |
| "XX 广告效果 / 认知路径" | **AIDA**（注意·兴趣·渴望·行动） | 营销 |
| "SaaS/服务型企业营销" | **7P**（4P + 人员·流程·环境） | 营销 |
| "快看 XX 的 Q1/Q3 财报" | **财报快评**（KPI 树 + 空-雨-伞） | 金融 |
| "XX 值不值得投 / 经营质量" | **深度财报分析**（KPI 树 + 历史 + 同行 + 风险） | 金融 |
| "XX 的 ROE 从哪来" | **杜邦分析**（净利率 × 周转 × 杠杆） | 金融 |
| "XX 财务健康 / 偿债能力" | **财务比率四维**（盈利·偿债·营运·成长） | 金融 |
| "XX 值多少钱 / 合理估值" | **DCF 现金流折现** | 金融 |
| "XX 贵不贵 / 估值分位" | **相对估值倍数**（P/E·P/B·EV/EBITDA·PEG·PS） | 金融 |
| "XX 有护城河吗" | **巴菲特护城河**（品牌·网络·切换成本·成本·无形资产） | 金融 |
| "XX 利润有水分吗 / 造假嫌疑" | **现金流质量 + Beneish M** | 金融 |
| "XX 会不会暴雷" | **Altman Z-Score**（5 比率加权） | 金融 |
| "XX 值不值得授信 / 供应商合作" | **5C 信贷分析**（Character·Capacity·Capital·Collateral·Conditions） | 金融 |
| "XX 有什么风险 / 隐患" | **风险专项 + SWOT 决策矩阵**（按 impact × likelihood） | 混合 |
| "XX 的 Q1 收入是多少"（单一数字） | 直接搜索，跳过框架流程 | — |

**说明：** 全部 31 个框架都在 `references/frameworks.md` 有完整定义（视角、维度、搜索关键词模板、质量红线）。Codex 会根据 query 自动路由；你也可以在审核卡片阶段手动指定要用的框架。混合题（例：金融 × 营销）会请你选视角（投资/经营/新业务）。

**关键词自动扩展举例（地图领域）：**

- "AR 导航" → AR Navigation, AR walking, LiveView, 实景导航, 步行 AR
- "车道级" → Lane-level, HD Map, 高精地图, 车道级导航, HDLive
- "打车" → Ride-hailing, 网约车, 滴滴, T3, 打车聚合, 一键打车
- "车机" → IVI, HUD, CarPlay, Android Auto, 鸿蒙座舱, 车联网

遇到"金融×营销混合题"（如"高德 IPO 前值不值得买"）会请你选视角。

**调用的 Skill 及作用：**

| Skill | 它做什么 | 为什么这一步要用它 |
|---|---|---|
| **search-agent 内核**（`lib/intent_classifier.py` + `frameworks.py`）| 关键词打分 + 优先级加权 → 从 31 个框架里选 Top 3 | 通用 LLM 会"什么都推荐一点"，内核有硬编码的打分逻辑，稳定输出可复现 |
| **brainstorming** | 强制 Codex 在动手前先追问澄清（用户目标 / 输出形式 / 边界） | 防止 LLM 一上来就闷头做，Brief 不清晰的调研必然翻车 |
| **marketing/marketing-ideas** | 生成 5-10 个调研角度 | 你说"帮我想想怎么调研"时用，比 LLM 自由发挥更成体系 |
| **marketing/customer-research** | 预挂载 JTBD 访谈框架 | 命中"用户为什么用 XX"类问题时，提前把 JTBD 模板准备好 |

**⛳ 闸门①：你必须回复"确认"或修改意见，Codex 才会开始搜索。**

---

## t2 — 多源分层信息检索（这一步是重点）

**这一阶段在做什么：** 按"官方 → 深度媒体 → UGC → 应用商店 → 热榜/RSS → 内网"六层顺序并行抓取，去重后整理成统一 YAML 源清单。

**为什么必须分层：** 同一个事实在不同源出现，可信度差距很大。例：`高德日活 X 亿`这句话，出自高德官方财报 vs 极客公园文章 vs 微博评论——如果不分层，LLM 会把三者混着用，报告的置信度就崩了。分层的核心目的是**让"官方数字"永远压过"UGC 情绪"**，且冲突时能追溯到源头。

**为什么并发抓取：** 51 个 RSS 源顺序抓要 3-5 分钟，用 `ThreadPoolExecutor(8)` 并发降到 30 秒左右。这不是优化，是可用性——LLM 会话上下文有超时限制，必须快。

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

**调用的 Skill 及作用：**

| Skill | 它做什么 | 为什么这一步要用它 |
|---|---|---|
| **firecrawl_search.py** | 走 Firecrawl API，做**英文深度 + JS 渲染 + 反爬 IP 池**的搜索 | Seeking Alpha / Reddit / TechCrunch / 竞品官方 blog 大多是 JS 渲染或有反爬，普通 requests 拿不到，Firecrawl 是目前最省事的方案 |
| **realtime-search** | Brave 引擎（英文）+ 百度引擎（中文），支持 `site:` / `filetype:pdf` 定向 | 官方一手信息（IR PDF / release notes / 白皮书）用它最快，百度引擎对中文长尾内容覆盖最好 |
| **baidu-search** | Baidu AI 搜索的原生结果 | realtime-search 空结果时的兜底，对贴吧/百科/中文冷门内容有优势 |
| **finance-rss-reader**（`lib/finance-rss-reader`）| 51 个财经/科技/深度 RSS 源并发抓取 + 关键词打分过滤 + 相关度 ≥0.6 才做全文 | 竞品新闻和行业动态**每天都在变**，搜索引擎收录慢；RSS 是被动订阅式，能拿到当天甚至当小时的更新。且 51 个源覆盖了我们内部很难人肉盯完的深度媒体 |
| **news-aggregator-skill**（8 大热榜）| 直连 HN / 微博 / V2EX / GitHub Trending / Product Hunt / 36氪 / 华尔街见闻 / 腾讯 的**内部 API** | 这些平台没有原生 RSS 或 RSSHub 常态 503，直连 API 比 Firecrawl 快 5x，且不消耗 Firecrawl 额度。**竞品发布首日**用它扫社交扩散量最有效 |
| **agent-reach** | 小红书 / B站 / Reddit / LinkedIn / 知乎 / 雪球等 13 个平台的定向抓取 | 消费者视角/UGC 口碑/招聘信号只有这些平台有，通用搜索引擎抓不到。**评测视频（B站）+ 使用体验（小红书）+ 招聘变动（LinkedIn）** 是竞品情报三金刚 |
| **marketing/competitor-profiling** | 内置了竞对档案的 12 个必查字段（定位 / 团队 / 融资 / GTM / 定价 / 产品线 / 客户 / 合作 / 官方渠道 / 招聘 / 舆情 / 迭代节奏） | 让 LLM 自由做"竞品分析"会漏项。这个 skill 强制走清单，输出稳定 |
| **marketing/customer-research** | 内置了 JTBD 访谈脚本 + 用户画像模板 | 命中"用户为什么用 XX"类问题时挂载，比 LLM 自由发散更成体系 |
| **marketing/directory-submissions** | Product Hunt / G2 / Capterra / AlternativeTo 的情报接口 | 海外竞品调研必调，这些平台是海外 SaaS/工具类产品最集中的评价与发现地 |
| **enterprise-search + ku-doc-manage** | 百度内网研究报告 + 如流知识库 | 如果既往调研已经做过，先查内网再联网可省一半时间；且内网数据 `confidence=high` |

**产出：** 统一的 YAML 源清单，每条含 `source_id / title / publisher / publish_date / url / confidence / key_facts / full_text_fetched`

**source_id 前缀（用于报告引文追溯）：** FC (Firecrawl) / RS (realtime-search) / BD (baidu) / RSS / SOC (社交/热榜) / MKT (marketing skill) / ES (内网) / KU (知识库)

**⛳ 闸门：数字冲突或缺关键源时暂停请你选口径。**

---

## t3 — 结构化分析（按框架维度）

**这一阶段在做什么：** 把 t2 拿到的一堆资料，按 t1 选定的框架维度重新组织，每条结论必须挂 source_id，并区分事实/计算/假设/判断。

**为什么必须做这一步：** t2 结束时你手里是"51 篇原始资料"，直接扔给 LLM 让它写报告，产出会变成"堆资料"——把资料原文换了个说法罗列一遍，没有观点、没有比较、没有洞察。t3 存在的意义是**强制按框架的子维度提炼**，让 LLM 从"总结员"变成"分析师"。

**为什么区分事实/计算/假设/判断：** 这是给报告读者的可信度信号。同样是"高德 MAU 4.5 亿"这句话——
- 官方财报 → 事实（可直接引用）
- 财报数字 × 增长率 → 计算（可复算）
- 参考市场规模反推 → 假设（可能错，需注明）
- "领先百度地图 20%" → 判断（主观，需支撑）

不区分这四类的报告读起来"看起来都很确定"，但里面 30% 是 LLM 拍脑袋，这是最危险的。

**调用的 Skill 及作用：**

| Skill | 它做什么 | 为什么这一步要用它 |
|---|---|---|
| **marketing/customer-research** | 强制 JTBD 陈述遵循"当[情境]时，我想[动机]，以便[结果]"句式 + 用户画像 6 字段模板 | LLM 自由写用户需求会写成"用户想要更方便"这种废话，走 skill 输出的每条 JTBD 都是可执行洞察 |
| **marketing/competitor-profiling** | 竞对档案 12 字段清单（见 t2 说明） | 让 t3 竞品对比表的每一列都有确定字段，不会漏 |
| **marketing/analytics + ab-testing** | Customer Journey 五阶段模板 + AARRR 漏斗计算 | 用户路径类分析需要转化率、留存率等标准指标，skill 有内置公式 |
| **marketing/product-marketing** | 4P 中 Product 维度的分析清单（USP / positioning / feature-benefit） | 竞品功能定位分析强制走清单，避免遗漏关键差异化点 |
| **marketing/pricing** | 4P 中 Price 维度（定价模型 / 会员体系 / 折扣策略 / anchor） | 竞品商业化分析必用，尤其地图厂商的会员/商户/API 收费三条线 |
| **marketing/social + public-relations** | CBBE 品牌传播层 + 媒体口径识别 | 品牌力分析用 |
| **marketing/seo-audit + programmatic-seo** | AARRR/Acquisition 层的搜索获客检查 | 竞品增长打法分析用 |
| **finance-skills/*** | 遇到估值/财报/护城河题时挂载（本项目不主用） | 混合题兜底，一般不触发 |

**产出：** 按框架的结构化中间稿（每维度一节，每条结论带 source_id 与置信度）

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

**你来做：**
- 等待分析产出（无需操作）
- Codex 提示"证据不足"时决定是否补检索

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

**这一阶段在做什么：** 把 t3 的结构化分析转成读者能 5 分钟读懂的报告——结论先行、每段 ≤150 字、关键数据加粗、附三栏对比表和参考文献表。

**为什么必须做这一步：** t3 的产出是"分析中间态"，按框架维度组织，但对报告读者不友好（他们不关心 PEST 四维，他们想 30 秒知道结论）。t4 存在的意义是**把分析结论金字塔化**——最上面是一句话结论，往下拆成 3 条支撑理由，再往下是各维度详细分析。读者可以随时停在任一层级。

**为什么强制附参考文献表：** 报告结论如果只写"根据某研究"没有链接，读者无法验证；如果每条都嵌大段引用又难读。金字塔尾部的参考文献表 + 正文内联 source_id 是妥协方案——正文轻，读者想验证时能一键跳原文。

**你来做：**
- 等待报告生成

**Codex 来做：**
- **结论先行**：一句话总判断 + 3 条支撑理由（附置信度和 source_id）+ 主要风险
- 按框架维度展开正文，每段 ≤150 字，重要数字**加粗**，趋势用 ↑↓→
- 竞品对比场景强制加**三栏对比表**
- 末尾附**风险与不确定性表格**（触发条件 / 影响 / 概率 / 来源）
- 末尾附**参考文献表**：编号 / 标题 / 发布方 / 日期 / 置信度 / 可跳转链接

**调用的 Skill 及作用：**

| Skill | 它做什么 | 为什么这一步要用它 |
|---|---|---|
| **search-agent 内核**（`lib/report_generator.py`）| 按框架模板生成金字塔结构 + 自动插入 source_id + 生成参考文献表 | 报告结构和引文格式必须完全一致，走内核模板比让 LLM 每次自由发挥更稳定 |
| **finance-skills/generative-ui** | 把竞品对比表、功能矩阵、雷达图转成交互式 HTML/SVG widget | Web 交付时用（例：需要在飞书文档或内部站点嵌入可点击的对比图），比静态截图直观 10 倍 |
| **humanizer-zh** | 检测并修复 AI 写作特征（破折号过度、三段式、"值得注意的是"等 AI 味词） | 报告如果一眼看出是 AI 写的，读者会先入为主打折扣；这个 skill 是发布前的最后一道净化 |

**产出：** `output/[主题]_report_YYYYMMDD.md`

**⛳ 闸门②：报告输出后，让你校验引文和结论，回复"通过"或"改 XX"。**

---

## t5 — 你终审 & 修订

**这一阶段在做什么：** 你把报告过一遍，提出具体修订意见（不是"改得更好"这种模糊指令，而是"位置 X 的结论过强 / 表格缺一列 / 这个 source 不可信"），Codex 只按修订清单执行。

**为什么必须有这一步：** LLM 存在两类无法自查的问题——
1. **幻觉**：编造出没出现在源里的数字或"某某报告显示"，越自信越可疑
2. **视角错位**：LLM 从中立视角写"高德 vs 百度地图"，但你想要的是"百度地图团队视角的启示"

第 1 类问题需要人工对着参考文献表逐条抽查；第 2 类问题只有你能判断"对我们团队有没有用"。这一步不是走过场，是最后的质量闸门。

**为什么限制 3 轮：** 修订循环没有上限就会陷入"每轮都改一点点"的低效循环。3 轮足够处理绝大多数正当修订；超过 3 轮说明 t1 或 t2 有本质问题（比如框架选错了或者源太少），应该往回退而不是继续改。

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

**调用的 Skill 及作用：**

| Skill | 它做什么 | 为什么这一步要用它 |
|---|---|---|
| **verification-before-completion** | 声称"改完了"之前强制跑一次核查：所有 must_fix 是否都改了、是否引入新的无源事实、Key Message 是否仍一致 | LLM 有"过度乐观地宣布完成"的倾向，这个 skill 是防止假交付 |
| **copy-editing** | 结构化编辑审查（Key Message 一致性、事实可追溯性、调性合规） | 修订过程中容易改坏其他段落，让这个 skill 每轮修订后再过一遍 |
| **humanizer-zh** | 去 AI 味 | 修订会引入新的 AI 味语言，每轮结束前重新净化 |

**⛳ 闸门：修订计划里若需要"新事实"或存在冲突，Codex 暂停请你确认。**

---

## t6 — 后续行动衔接（可选）

**这一阶段在做什么：** 调研做完不能只停在报告——报告的价值 = 后续动作的价值。t6 是把报告变成"立项 brief / PR 稿 / 社交传播 / KOL 脚本 / 用户访谈提纲 / 竞品监控周报"等可执行产物的桥梁。

**为什么单独作为一个阶段：** 大部分调研做完就烂在文件夹里，因为"从调研结论 → 可执行产物"这一步需要**换一批 skill**（copywriting / launch / cro / emails 等），不再是搜索和分析类工具。把它独立出来是提醒你：报告不是终点。

**为什么衔接的 skill 都是 marketing/*：** 因为我们是产品/竞品调研场景，下游动作大概率是"根据调研写文案 / 起立项 / 定 GTM"，这些都是营销与增长范畴。skill 之间的衔接不是随机组合，是走"调研→立项→执行"的产品经典流水线。

调研完成后，Codex 可直接衔接下游动作。**每个后续 skill 都是一个"专家动作打包"**——你不需要自己拼组件：

| 你说 | Codex 调 | 场景 | 这个 skill 内置了什么 |
|---|---|---|---|
| "写个新功能立项 brief" | brainstorming + writing-plans | 立项文档 | 立项模板（目标 / 用户 / 竞品 / 关键指标 / 资源 / 时间线）|
| "起一个 PR 稿" | marketing/launch + copywriting + public-relations | 新功能发布 | PR 三段结构（hook / 事实 / 引语）+ 记者语气模板 |
| "帮我起社交传播文案" | marketing/social + copywriting | 微博/小红书 | 各平台字数上限、hashtag 规范、cover 图规格 |
| "做落地页文案" | marketing/copywriting + cro | 落地页 | AIDA 结构 + 转化率优化 checklist |
| "写 KOL 投放脚本" | marketing/social + ad-creative | 抖音/B站 | 短视频 hook 3 秒黄金法则 + 脚本节奏 |
| "做用户访谈提纲" | marketing/customer-research | 用户研究 | JTBD 5 问 + 追问模板 |
| "起竞品监控周报模板" | content-strategy + writing-plans | 长期监控 | 每周 checklist + 变更对比表 |
| "输出对外分享稿" | copywriting + copy-editing + humanizer-zh | 内部分享 | 润色 + 去 AI 味 |

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
