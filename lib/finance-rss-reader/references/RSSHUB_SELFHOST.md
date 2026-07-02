# 自建 RSSHub 部署指南（可选，用于解锁全部中文深度源）

## 为什么需要自建 RSSHub？

本 skill 内置了 16 个**中文财经深度 RSS 源**（财联社/华尔街见闻/晚点 LatePost/远川研究所/财经十一人/雪球/36 氪/第一财经杂志等），但它们不是官方 RSS——而是通过开源工具 [RSSHub](https://github.com/DIYgod/RSSHub) 从原网站抓取生成的。

公共 RSSHub 节点（如 `rsshub.rssforever.com`）由于反爬和流量限制，经常返回 `HTTP 503 / 403`。**自建 RSSHub 是彻底解决方案**——一次部署，所有中文深度源永久可用。

## 实测数据（2026-07-01）

在不自建 RSSHub 的情况下，公共节点当前可用性：

| 状态 | 数量 | 说明 |
|---|---|---|
| ✅ 稳定可用 | 4 个 | 华尔街见闻·全球 / 华尔街见闻·A股 / 第一财经 / 格隆汇 |
| ⚠️ 公共节点 503 | 11 个 | 财联社 / 36氪 / 晚点 / 远川 / 雪球 / 财经十一人等（需自建） |
| ❓ 微信公众号源 | 3 个 | 财经十一人 / 晚点 / 远川（必须自建 RSSHub） |

**自建后可用率 = 100%。**

## 部署方式（推荐 Docker）

### 方式 1：单机 Docker（最简单，1 分钟）

```bash
# 拉起 RSSHub 无头浏览器版（支持 JS 渲染）
docker run -d --name rsshub -p 1200:1200 diygod/rsshub:chromium-bundled
```

启动后访问 `http://localhost:1200`，看到首页即部署成功。

### 方式 2：Docker Compose（推荐，含 Redis 缓存）

新建 `docker-compose.yml`：

```yaml
version: '3'
services:
  rsshub:
    image: diygod/rsshub:chromium-bundled
    restart: always
    ports:
      - '1200:1200'
    environment:
      NODE_ENV: production
      CACHE_TYPE: redis
      REDIS_URL: 'redis://redis:6379/'
    depends_on:
      - redis
  redis:
    image: redis:alpine
    restart: always
    volumes:
      - redis-data:/data
volumes:
  redis-data:
```

启动：
```bash
docker-compose up -d
```

### 方式 3：云端一键部署

- **Zeabur**：[点击部署](https://zeabur.com/templates/X46PTP)
- **Sealos** / **Fly.io** / **Google App Engine**：见 [官方部署文档](https://docs.rsshub.app/deploy)

## 部署后：切换本 skill 的 RSS 端点

自建 RSSHub 部署好后（假设地址是 `http://your-server:1200`），把 `references/rss_sources.json` 里所有 `rsshub.rssforever.com` 全部替换成你的服务器地址：

```bash
# macOS / Linux
sed -i.bak 's|rsshub.rssforever.com|your-server:1200|g' \
    lib/finance-rss-reader/references/rss_sources.json
```

或者写个环境变量到 rss_fetch.py（可选进阶）。

## 无法自建时的替代方案

如果同事的环境无法运行 Docker，也不想自建：

1. **保留可用的 4 个中文深度源** = 华尔街见闻（全球+A股）+ 第一财经 + 格隆汇。已足够覆盖 A 股 + 港股 + 中概股主流深度报道
2. **配合 realtime-search 百度引擎** = 定向搜 `site:cls.cn` / `site:latepost.com` / `site:yuanchuan.com` / `site:eeo.com.cn` 补齐缺失源
3. **配合 Firecrawl** = 拿到 URL 后深度抓正文
4. **官方 API 订阅**：财新 648 元/年、财联社 VIP、华尔街见闻会员——付费用户可拿正版 API

## 完整源列表

见 `references/rss_sources.json`。

- **国际源**：22 个（Reuters、Bloomberg、FT、WSJ、CNBC、SeekingAlpha、Barron's、Morningstar、TechCrunch、Gartner、McKinsey 等）
- **中文深度源（新增）**：16 个（财联社·电报/深度头条/深度公司、华尔街见闻·全球/A股、36 氪·深度、第一财经杂志、第一财经、经济观察报、财经十一人、晚点 LatePost、远川研究所、格隆汇、雪球、巴伦中文、每经原创）
- **中文媒体源**：9 个（东方财富、36 氪、新浪财经、财新、界面、虎嗅、钛媒体、雷锋网、亿欧网）
- **中文产业研究源**：6 个（艾瑞、易观、清科、CBNData、德勤中国、普华永道中国）

总计 **53 个源**。
