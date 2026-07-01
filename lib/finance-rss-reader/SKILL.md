---
name: finance-rss-reader
description: 财经 RSS 深度阅读与分析工具。给定公司名、股票代码或行业关键词，从预设高质量财经 RSS 源（Reuters、SeekingAlpha、FT、Bloomberg、东方财富、36氪等）拉取最近 N 天相关文章，过滤高相关条目并抓取全文，输出兼容财报分析 workflow Step 2 的 source_id YAML 格式摘要。支持两种模式：(1) 独立手动调用——用户说"帮我搜一下携程最近的行业动态/分析师观点/监管动态"时触发；(2) 被财报分析工作流 Step 2 静默集成调用，补充搜索引擎覆盖不到的聚合信息流。
---

# 财经 RSS 深度阅读与分析

从预设高质量财经 RSS 源按需拉取、过滤、全文抓取并结构化输出，服务于财报分析 Step 2 信息收集。

## 调用方式

### 模式 A：独立手动调用

用户提供公司名/ticker/行业关键词，直接触发本 skill：

```
帮我看看 [公司名] 最近的行业动态
搜一下 [TICKER] 的分析师观点
[行业] 最近有什么监管动态
```

### 模式 B：被工作流静默集成（Step 2 调用）

财报分析 Step 2 在完成官方财报收集后，用以下格式调用本 skill：

```
调用 finance-rss-reader，关键词=[公司名]，ticker=[TICKER]，days=14，模式=workflow
```

输出直接追加到 Step 2 资料清单 YAML，source_id 从 S_RSS001 开始编号。

## 执行流程

### Step 1：解析输入参数

从用户输入或调用参数中提取：
- `keywords`：公司名、中英文别名
- `ticker`：股票代码（如有，用于 SeekingAlpha RSS）
- `days`：拉取时间范围，默认 14 天
- `mode`：`manual`（默认）或 `workflow`

### Step 2：拉取 RSS 条目

执行脚本拉取各源最新条目：

```bash
python3 $SKILL_DIR/scripts/rss_fetch.py \
  --keywords "[关键词]" \
  --ticker "[TICKER]" \
  --days [N] \
  --sources-config $SKILL_DIR/references/rss_sources.json
```

脚本返回过滤后的相关条目列表（JSON），每条包含：title、url、published、source、relevance_score、summary。

### Step 3：全文抓取高相关条目

对 `relevance_score >= 0.6` 的条目，用 realtime-search 的 fetch 工具抓全文：

```bash
FETCH_SCRIPT=/home/gem/workspace/.claude/skills/realtime-search/scripts/fetch.py
python3 $FETCH_SCRIPT "[article_url]" --max-chars 8000
```

每篇全文抓取后提炼 3-5 条关键信息点（facts/数字/判断）。

**抓取限制**：每次最多抓取 5 篇全文，避免上下文溢出。优先级：relevance_score 从高到低。

### Step 4：输出结构化结果

#### 模式 A（manual）输出格式

```markdown
## 财经资讯摘要 — [关键词] — [日期范围]

### 高相关文章（全文已读）

**[标题]** | [来源] | [日期]
- 要点1
- 要点2
- 要点3
- 来源：[URL]

...

### 相关文章（摘要）

| 标题 | 来源 | 日期 | 摘要 |
|---|---|---|---|
```

#### 模式 B（workflow）输出格式

直接追加到 Step 2 资料清单，使用 source_id YAML 格式：

```yaml
- source_id: S_RSS001
  title: "[文章标题]"
  publisher: Reuters
  source_type: 媒体
  publish_date: 2026-06-28
  data_period: "[文章涉及期间]"
  url_or_path: "[URL]"
  confidence: medium
  key_facts:
    - 要点1
    - 要点2
  notes: 全文已读取

- source_id: S_RSS002
  ...
```

## 详细规范

见 `references/rss_sources.json`（RSS 源配置）和 `references/fetch_rules.md`（全文抓取规则）。
