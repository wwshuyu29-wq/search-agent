# 搜索平台矩阵（Step 1 扩展）

本文件把 SKILL.md Step 1 的工具矩阵**按场景 × 平台**展开，覆盖英文/中文/垂直财经/社交/学术/政府数据/数据 API 共 40+ 个渠道。所有平台的产出必须归一化到 SKILL.md 的 **source_id YAML 格式**（见 Step 1 末尾），source_id 前缀按下表分配。

> 设计原则参考 `lib/finance-rss-reader/SKILL.md`：
> - 两种调用模式：Mode A 手动 / Mode B workflow 静默集成
> - `relevance_score >= 0.6` 才做全文抓取，每次最多 5 篇
> - 输出 YAML 字段固定：source_id / title / publisher / source_type / publish_date / data_period / url_or_path / confidence / key_facts / notes

## source_id 前缀速查

| 前缀 | 来源类别 | 主要工具 |
|---|---|---|
| FC### | Firecrawl 深度抓取 | `scripts/firecrawl_search.py` |
| RS### | realtime-search（Brave/百度） | `skill realtime-search` |
| BD### | baidu-search（中文兜底） | `skill baidu-search` |
| RSS### / S_RSS### | 财经 RSS 聚合 | `lib/finance-rss-reader` |
| ES### | 企业内网 | `skill enterprise-search` |
| KU### | 知识库文档 | `skill ku-doc-manage` |
| FIN### | finance-skills 结构化数据 | vendor/finance/* |
| MKT### | marketing-skills 结构化情报 | vendor/marketing/* |
| SOC### | 社交/热榜内容 | news-aggregator-skill / agent-reach |
| ACA### | 学术/论文 | arXiv / CNKI / Scholar |
| DAT### | 政府/统计/API 数据 | AKShare / yfinance / EDGAR |

---

## 0. news-aggregator-skill 集成（Layer 5b 热榜扫描）

news-aggregator-skill 直连 8 大热榜源的内部 JSON/HTML 端点，比走 RSS/Firecrawl 快 5x。已在 `~/.comate/skills/news-aggregator-skill/scripts/fetch_news.py` 安装。

**两种调用方式：**

1. **独立调用**（追加 Layer 5b 的 SOC### 源）：

```bash
python3 ~/.comate/skills/news-aggregator-skill/scripts/fetch_news.py \
    --source hackernews,weibo,v2ex,36kr,wallstreetcn,tencent,github,producthunt \
    --limit 15 \
    --keyword "<扩展词族逗号连接>" \
    --deep
```

2. **通过 finance-rss-reader 融合**（推荐，与其他 67 个源统一 YAML 输出）：
   `rss_sources.json` 里将部分源标为 `fetcher: newsagg`，`rss_fetch.py` 会自动 subprocess 调用 news-aggregator 拿数据并归一化。当前已迁移：**华尔街见闻·全球 / 36 氪·深度**（从 firecrawl 降级为直连 API）。

**为什么用它替代部分 Firecrawl 源**：
- 华尔街见闻内部 API `api-one.wallstcn.com` 直返 JSON，200 状态
- 36 氪 `newsflashes` 页面 HTML 稳定，直接 BeautifulSoup
- 微博走 `weibo.com/ajax/side/hotSearch` Ajax
- V2EX 走官方 `topics/hot.json`
- 腾讯新闻走 `getTagInfo` 内部 API

每个源都有自己"最省事的入口"（隐藏 API > RSS > HTML > Firecrawl > 浏览器渲染）。

---



## 1. 通用搜索引擎（Layer 1-2 官方入口 / Layer 3 深度）

| 平台 | 适用场景 | 触发方式 | 备注 |
|---|---|---|---|
| Firecrawl | 英文深度、JS 渲染、Seeking Alpha / FT / SEC | `python3 scripts/firecrawl_search.py --query ... --lang en` | 主力英文入口 |
| Brave（realtime-search）| 英文官方来源、`site:` / `filetype:pdf` | `skill realtime-search "..." --engine brave` | IR / 10-K 定位 |
| 百度（realtime-search）| 中文财经/媒体 | `skill realtime-search "..." --engine baidu --freshness month` | 主力中文入口 |
| baidu-search | 中文通用兜底 | `skill baidu-search --query ...` | realtime 空结果时补 |
| Google Scholar | 学术、白皮书、行业研究 | `skill realtime-search "..." --engine brave` + `site:scholar.google.com` | 学术论证 |
| DuckDuckGo | 隐私 / 少见结果 | `multi-search-engine` skill | 交叉验证 |
| Bing | 英文补充 | `multi-search-engine` skill | 英语兜底 |
| Sogou 微信搜索 | 微信公众号原文 | `skill realtime-search` + `site:mp.weixin.qq.com` | 中文自媒体独家 |
| Yandex | 俄语 / 独联体地区 | `multi-search-engine` skill | 地缘/能源题 |

## 2. 中文垂直财经与消费社群

| 平台 | 类型 | 优先场景 | 抓取方式 |
|---|---|---|---|
| 知乎 | UGC 深度长文 / 匿名爆料 | 行业机制解释、内幕、职场信号 | `agent-reach` 或 `realtime-search "..." site:zhihu.com` |
| 雪球 | A/港/美股讨论 + 组合 | 散户情绪、多空辩论、机构 F10 | `agent-reach xueqiu` / `finance-sentiment` |
| 东方财富股吧 | A 股散户情绪 | 情绪面 / 短线扰动 | `realtime-search "..." site:guba.eastmoney.com` |
| 同花顺 iFinD | A 股 F10 / 公告 | 官方公告结构化数据 | 需付费；无 key 时用 `site:10jqka.com.cn` |
| 淘股吧 | A 股游资 / 龙虎榜 | 短线 / 主力资金 | `realtime-search site:taoguba.com.cn` |
| 微博财经 | 突发/情绪/大 V | 传播链、突发事件 | `agent-reach weibo` |
| 小红书 | 消费品 GTM / KOC | 品牌调研、消费者原声 | `agent-reach xhs`（触发关键字 xhs/小红书）|
| B 站 | 深度视频、财报解读、产品评测 | UGC 长视频、教程、评测 | `agent-reach bilibili` |
| 虎扑 | 消费品/男性向讨论 | 运动、汽车、数码调性 | `realtime-search site:hupu.com` |
| 豆瓣 | 文娱 / 内容评级 | 消费品口碑、内容评价 | `realtime-search site:douban.com` |

## 3. 全球社交与情绪源

| 平台 | 主要用途 | 抓取方式 |
|---|---|---|
| Reddit | 英文 UGC 深度、r/wallstreetbets、r/stocks | `agent-reach reddit` 或 `finance-sentiment` |
| X / Twitter | 突发、KOL、金融 Fintwit | `agent-reach twitter` |
| Discord | 私域社群（限公开频道） | 手动或 `agent-reach` |
| Polymarket | 事件预测市场概率 | `finance-skills/finance-sentiment` |
| StockTwits | 美股 tickers 情绪 | `finance-sentiment` 或 `realtime-search site:stocktwits.com` |
| LinkedIn | 招聘信号、团队变动、B2B 决策链 | `agent-reach linkedin`（受限，需人工兜底）|
| YouTube | 财报解读、访谈、纪录片 | `agent-reach youtube` |
| 小宇宙 | 中文财经播客 | `agent-reach xiaoyuzhou` |

## 4. 学术与政策数据

| 平台 | 用途 | 抓取方式 |
|---|---|---|
| arXiv | AI / 量化 / 前沿论文 | `realtime-search site:arxiv.org` |
| CNKI 知网 | 中文学术论文 | `realtime-search site:cnki.net`（正文需机构订阅）|
| SSRN | 金融学术 preprint | `realtime-search site:ssrn.com` |
| 国家统计局 | 中国宏观数据 | `realtime-search site:stats.gov.cn` |
| 人民银行 / 银保监 / 证监会 | 政策原文 | `site:pbc.gov.cn` / `csrc.gov.cn` 等 |
| Trading Economics | 全球宏观指标 | 直接抓取或 API |
| SEC EDGAR | 美股披露原件（10-K/Q/8-K/13F/S-1） | `realtime-search site:sec.gov` 或 `finance-skills/funda-data` |

## 5. 结构化数据 API（不走搜索，直取）

| 数据源 | 覆盖 | 触发 skill / 库 |
|---|---|---|
| yfinance | 美股价格/财务/期权/股息 | `finance-skills/yfinance-data` |
| AKShare | A/港/美/期货/宏观 全面 Python | 本地 `python -c "import akshare as ak; ..."` |
| Tushare | A 股专业金融数据 | 需 token；同 AKShare 用法 |
| baostock | A 股免费数据 | Python 库直接调 |
| Alpha Vantage | 全球股票 / 外汇 / 加密 | API key + REST |
| Financial Modeling Prep | 财报 / 估值倍数 | API key + REST |
| Polygon.io | tick 级美股 | API key + REST |
| Finnhub | 财报日历 / 分析师目标价 / 新闻 | API key + REST |
| TradingView | 期权链 / 技术图 | `finance-skills/tradingview-reader` |
| funda-data MCP | 分析师研究合成 60+ 端点 | `finance-skills/funda-data` |

**规则**：结构化 API 拿到的数字直接进 YAML，`confidence=high`，`source_type=数据API`，`url_or_path` 写 endpoint 或 skill 名。

## 6. 财经 RSS 聚合（Layer 5，兼容 finance-rss-reader 设计）

沿用 `lib/finance-rss-reader` 的两模式设计：

**Mode A（手动）**：用户说"帮我看看 XX 最近的行业动态" → 直接触发。

**Mode B（workflow 静默集成）**：Step 1 结束前，用以下调用格式接入：

```bash
python3 lib/finance-rss-reader/scripts/rss_fetch.py \
    --keywords "<关键词, 别名>" \
    --ticker "<TICKER>" \
    --days 14 \
    --sources-config lib/finance-rss-reader/references/rss_sources.json \
    --min-score 0.4
```

抓取规则：
- `relevance_score >= 0.6` 的条目才做全文抓取
- 每次最多 5 篇全文，按 score 降序
- 全文抓取走 `skill realtime-search fetch <URL> --max-chars 8000`
- 输出直接以 `S_RSS###` 追加到 Step 1 的 YAML 源清单

当前 65+ 个源，其中中文财经、英文财经、AI/科技商业、深度长文源混合覆盖；配置详见 `lib/finance-rss-reader/references/rss_sources.json`。生产调研默认全量扫描，只有调试或演示时才临时加 `--max-sources N`。

## 7. 场景 → 平台组合速查

| 场景 | 建议平台组合 |
|---|---|
| 美股深度财报/估值 | Firecrawl + Brave + SEC EDGAR + yfinance + funda-data + Seeking Alpha（RSS）+ Reddit r/investing |
| A 股上市公司 | 巨潮资讯（site:cninfo.com.cn）+ AKShare + 雪球 + 东方财富股吧 + 财新 RSS |
| 消费品 / 新品牌 | 小红书 + B站 + 微博 + 豆瓣 + 36氪 RSS + Product Hunt（marketing/directory-submissions）|
| SaaS / B2B | G2 + Capterra + LinkedIn + Reddit r/SaaS + FT + Bloomberg + funda-data |
| 宏观 / 政策 | 国家统计局 + 央行 + 证监会 + Trading Economics + 财新 + Reuters（RSS）|
| 事件驱动 / 突发 | X/Twitter + 微博 + Reuters RSS + 华尔街见闻 + Polymarket |
| 学术 / 白皮书 | Google Scholar + arXiv + CNKI + SSRN + 麦肯锡/Gartner（Firecrawl）|

## 8. 抓取顺序与去重规则

1. **官方直取优先**：结构化 API（yfinance / EDGAR / AKShare）> 官方 IR > 搜索引擎
2. **同一新闻多源命中**：优先保留 confidence 更高的（官方 > 大厂媒体 > RSS 快讯 > 论坛 UGC）
3. **社交源单独标注**：`source_type=社交`，`confidence=low`，只作情绪面/信号面证据，不作事实断言
4. **付费墙内容**：抓到摘要即可，`notes: paywalled，摘要仅供参考`
5. **重复 URL 全局去重**：Step 1 结束前对 YAML 做 url 归一化去重
