# RSS 抓取的稳定获取方案（免 Docker）

## 背景：为什么公共 RSSHub 不可靠

公共 RSSHub 节点（`rsshub.app` / `rsshub.rssforever.com` 等镜像）常态返回 503/403，原因是**两头挤压**：

1. **源站反爬** — 微博/知乎/B站/雪球/36氪 等平台对匿名高频请求限流或直接封 IP
2. **共享 IP 被拉黑** — 公共节点几十万用户共用一个出口 IP，你一次请求排在几百人后面

自建 Docker RSSHub 能解决共享 IP 问题，但对同事的运维负担偏大。以下是**不需要 Docker** 的三条落地路径，按推荐度排序。

---

## 方案 A（默认推荐）：Firecrawl + 原生 RSS 混合

**思路**：能拿到原生 RSS/Atom 的媒体（Reuters、FT、SeekingAlpha、华尔街见闻·全球、第一财经、格隆汇、财新、36氪部分栏目等 40+ 个）直接走 `feedparser`；拿不到的（微博、知乎话题、B 站 UP 主动态、小红书、雪球组合、财联社电报等），改用 **Firecrawl `/search` 或 `/scrape`** 直接抓页面正文，跳过 RSSHub 中转。

**优点**
- 同事零运维：只需要一个 `FIRECRAWL_API_KEY`
- 反爬成功率高：Firecrawl 自带 IP 池 + JS 渲染
- 与 Step 1 主链路统一：源清单里 `FC###` 和 `S_RSS###` 混排，去重规则不变

**在 `rss_sources.json` 中的标注方式**

```json
{
  "id": "weibo_finance",
  "name": "微博财经话题",
  "type": "search",
  "fetcher": "firecrawl",
  "query_template": "site:weibo.com {keywords}",
  "confidence": "medium",
  "language": "zh"
}
```

`rss_fetch.py` 里加一个分支：`fetcher == "firecrawl"` 走 `scripts/firecrawl_search.py`，其余仍走 feedparser。相关性打分逻辑（`relevance_score >= 0.6` 才做全文抓取、每次最多 5 篇）保持与 `SKILL.md` 一致。

---

## 方案 B：一键托管部署（Zeabur / Sealos）

需要维持 RSSHub 路由格式（例如已经沉淀了几十条 RSSHub 路径）时，选一键部署平台：

| 平台 | 免费额度 | 一键模板 | 备注 |
|---|---|---|---|
| Zeabur | 每月 $5 免费额度 | ✅ [X46PTP](https://zeabur.com/templates/X46PTP) | 中国团队维护、中文友好 |
| Sealos | 免费额度可跑 RSSHub | ✅ | 国内可访问 |
| Railway | 每月 $5 免费 | ✅ | 国际站点，国内偶尔慢 |
| Vercel | 边缘函数免费 | ⚠️ | RSSHub 有专门的 vercel 分支 |

**部署一次，全公司共用**：把托管好的 URL 写进 `rss_sources.json` 的 `endpoint` 字段或 `.env` 中的 `RSSHUB_ENDPOINT`，同事无需接触 Docker。

## 方案 C：RSSHub Pro（付费）

`rsshub.pro` 官方付费镜像，约 $3/月，稳定性最好，但需要跨境付费。适用于国际团队或对成本不敏感的场景。

---

## 推荐落地方式

本 skill 的默认策略：

1. **首选方案 A** — `rss_sources.json` 里保留 40+ 个原生 RSS，另外通过 Firecrawl 覆盖约 10 个"伪 RSS"（社交/贴吧/话题）
2. **方案 B 作为团队级备选** — 如果调研范围高频依赖社交源，可让运维一次性用 Zeabur 部署一个内部实例，`.env` 中写 `RSSHUB_ENDPOINT=https://xxx.zeabur.app` 即可
3. **方案 C 只作个人可选**

## 部署后：切换本 skill 的 RSS 端点

如果启用方案 B，用一条命令把 `references/rss_sources.json` 里所有公共 RSSHub 域名替换成你的自建/托管地址：

```bash
sed -i.bak 's|rsshub.rssforever.com|your-server:1200|g' \
    lib/finance-rss-reader/references/rss_sources.json
```

或者在 `rss_fetch.py` 中读取 `RSSHUB_ENDPOINT` 环境变量做统一替换。

## 无法启用外部依赖时的兜底

即使 Firecrawl 和 RSSHub 都不可用，本 skill 仍能保证基础覆盖：

1. **原生 RSS 稳定源**（华尔街见闻·全球+A股 / 第一财经 / 格隆汇 / Reuters / FT / SeekingAlpha 等）继续走 feedparser
2. **realtime-search 百度引擎**定向搜 `site:cls.cn` / `site:latepost.com` / `site:yuanchuan.com` / `site:eeo.com.cn` 补齐缺失源
3. **官方付费 API**：财新（648 元/年）、财联社 VIP、华尔街见闻会员对应正版 API

## 完整源列表

见 `references/rss_sources.json`。

- **国际源**：22 个（Reuters、Bloomberg、FT、WSJ、CNBC、SeekingAlpha、Barron's、Morningstar、TechCrunch、Gartner、McKinsey 等）
- **中文深度源**：16 个（财联社·电报/深度头条/深度公司、华尔街见闻·全球/A股、36 氪·深度、第一财经杂志、第一财经、经济观察报、财经十一人、晚点 LatePost、远川研究所、格隆汇、雪球、巴伦中文、每经原创）
- **中文媒体源**：9 个（东方财富、36 氪、新浪财经、财新、界面、虎嗅、钛媒体、雷锋网、亿欧网）
- **中文产业研究源**：6 个（艾瑞、易观、清科、CBNData、德勤中国、普华永道中国）

总计 **53 个源**。
