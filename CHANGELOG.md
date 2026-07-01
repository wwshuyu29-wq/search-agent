# Search Agent 智能分析系统 - 更新日志

## v2.3 (2026-07-01)

### ✨ 新增功能

#### 1. **RSS 源大幅扩充 (17 → 35 个源)**

新增 18 个高质量财经/产业研究 RSS 源:

**国际分析与投资机构**:
- The Motley Fool: 个人投资者股票分析
- Barron's: 高端投资杂志
- Morningstar: 投资研究和基金分析
- Benzinga: 实时股票新闻
- TechCrunch: 科技创业融资动态
- VentureBeat: 科技商业新闻

**国际产业研究**:
- Gartner Press Releases: IT 市场研究
- McKinsey Insights: 战略咨询洞察
- (IDC/德勤/普华永道需手动抓取)

**中文财经媒体**:
- 钛媒体: 科技商业深度报道
- 雷锋网: AI/智能硬件
- 亿欧网: 产业互联网

**中文产业研究**:
- 艾瑞网: 互联网行业数据
- 易观分析: 数字经济分析
- 清科研究: 私募股权/创投
- CBNData: 消费大数据
- 普华永道中国: 行业洞察

完整 RSS 源配置见 `lib/finance-rss-reader/references/rss_sources.json`

#### 2. **RSS 拉取脚本重构与 Bug 修复**

**核心改进**:
- **SSL 证书处理**: 支持自签名证书的 RSS 源
- **编码自动检测**: 从 Content-Type 提取正确编码
- **更健壮的解析**: 支持更多日期格式和 HTML 实体
- **改进的相关性算法**: 标题匹配权重 2x
- **详细错误日志**: HTTP 错误、URL 错误分类记录
- **源数量限制**: 新增 `--max-sources` 参数避免超时
- **超时时间延长**: 从 30 秒延长到 60 秒

**Bug 修复**:
- 修复 URL 提取失败问题 (支持 href 属性)
- 修复日期解析异常 (支持 6 种日期格式)
- 修复 HTML 实体未清理问题
- 修复时区处理错误

**新增功能**:
```python
# 支持限制源数量
--max-sources 15  # 只拉取前 15 个源

# 更详细的进度日志
[1/35] Fetching Reuters Business...
  -> Parsed 50 items
[INFO] Fetched from 15/35 sources, 23 relevant items
```

### 🎯 核心改进

#### RSS 源分类统计

**v2.2**: 17 个源
- 媒体: 14 个
- 分析: 3 个

**v2.3**: 35 个源
- 媒体: 20 个 (+6)
- 分析: 9 个 (+6)
- 产业研究: 6 个 (新增)

#### 搜索引擎性能优化

- RSS 超时从 30s → 60s
- 默认限制 15 个源 (可配置)
- 错误降级机制: 单源失败不影响其他源

### 📚 文档更新

- 更新 `rss_sources.json` 包含 35 个源
- 更新 `rss_fetch.py` 增加错误处理文档
- 新增 `--max-sources` 参数说明

### 🐛 Bug修复

- **Critical**: 修复 SSL 证书验证失败导致的拉取失败
- **Critical**: 修复日期解析错误导致的时间过滤失效
- 修复 URL 提取不完整问题
- 修复编码错误导致的乱码
- 修复相关性评分算法权重不合理

### 📦 下载

**v2.3 完整包**: (待上传)

### 🔄 升级说明

从 v2.2 升级到 v2.3:

1. **完全替换**: 下载 v2.3 覆盖原目录 (推荐)
2. **增量升级**:
   - 替换 `lib/finance-rss-reader/scripts/rss_fetch.py`
   - 替换 `lib/finance-rss-reader/references/rss_sources.json`
   - 替换 `lib/search_engine.py` (超时参数调整)

**重要**: v2.3 完全兼容 v2.2 API，无需修改调用代码

### 💡 RSS 源使用建议

**默认配置** (推荐):
```python
# 自动限制前 15 个源，平衡速度与覆盖面
--max-sources 15
```

**快速模式** (30 秒内完成):
```python
--max-sources 5  # 只拉取前 5 个源
```

**完整模式** (获取最全面信息):
```python
--max-sources 0  # 拉取所有 35 个源 (可能需要 2-3 分钟)
```

**中文优先**:
手动编辑 `rss_sources.json`，将中文源移到前面

### 🎯 新增产业研究源价值

**Gartner / McKinsey / 艾瑞 / 易观**:
- 提供宏观行业趋势
- 竞争格局分析
- 市场规模预测
- 适合深度行业分析和战略规划

**清科研究 / CBNData**:
- 融资数据和创投趋势
- 消费行为洞察
- 适合投资分析和市场研究

---

## v2.2 (2026-07-01)

### ✨ 新增功能

#### 1. **RSS 聚合信息流集成 (Layer RSS)**

基于 finance-rss-reader Skill，新增第五层 RSS 聚合搜索:

**特性**:
- 自动从 17+ 高质量财经 RSS 源聚合信息
- 支持中英文财经媒体 (Reuters、Bloomberg、FT、36氪、财新、东方财富等)
- 关键词相关性自动过滤 (min_score: 0.4)
- 时间范围: 最近 14 天
- 自动限制结果数量 (Top 10)，避免上下文溢出

**支持的 RSS 源**:
- **国际**: Reuters、Bloomberg、FT、WSJ、CNBC、Yahoo Finance、MarketWatch
- **中文**: 36氪、财新、东方财富、第一财经、界面新闻、虎嗅、新浪财经
- **分析**: Investopedia、SeekingAlpha (动态根据 ticker 添加)

**数据结构增强**:
```python
{
    "source_type": "rss_feed",
    "confidence": "medium",
    "notes": "来自 RSS: 36氪, 相关性: 1.0",
    "rss_metadata": {
        "source_name": "36氪",
        "relevance_score": 1.0,
        "region": "zh",
        "source_type_rss": "媒体"
    }
}
```

#### 2. **内嵌 finance-rss-reader 组件**

- 将完整的 finance-rss-reader Skill 内嵌到 `lib/finance-rss-reader/` 目录
- 无需用户单独安装，开箱即用
- 自动路径查找: 优先使用内嵌版本，其次查找系统 skill 路径

**目录结构**:
```
lib/
├── finance-rss-reader/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── rss_fetch.py
│   └── references/
│       └── rss_sources.json
├── search_engine.py
├── frameworks.py
...
```

### 🎯 核心改进

#### 搜索层级扩展

**v2.1** (4层):
1. Layer 1: 官方原始来源
2. Layer 2: 业绩会 Transcript
3. Layer 3: 深度分析文章
4. Layer 4: 同行交叉验证

**v2.2** (5层):
1-4 层保持不变
5. **Layer RSS**: RSS 聚合信息流 (新增)

#### API 变更

**search_engine.py**:
```python
# 新增方法
def _find_finance_rss_reader() -> str
def _search_rss_feeds(params: dict, framework: str) -> List[Dict]

# multi_source_search() 自动集成 RSS 层
# 当 enable_layered_search=True 时自动调用
```

#### 超时处理优化

- RSS 拉取设置 30 秒超时
- 超时时优雅降级，不阻塞其他层搜索
- 错误日志清晰标注失败原因

### 📚 文档更新

- 更新 `lib/search_engine.py` 注释说明 RSS 集成
- 内嵌 `lib/finance-rss-reader/SKILL.md` 完整文档
- RSS 源配置文件 `lib/finance-rss-reader/references/rss_sources.json`

### 🐛 Bug修复

- 修复 RSS 拉取超时导致整体搜索失败的问题
- 优化 RSS 脚本路径查找逻辑

### 📦 下载

**v2.2 完整包**: https://dwz.cn/QB3L0m9m (50.85 KB)

### 🔄 升级说明

从 v2.1 升级到 v2.2:

1. **完全替换**: 下载 v2.2 覆盖原目录 (推荐)
2. **增量升级**:
   - 替换 `lib/search_engine.py`
   - 新增 `lib/finance-rss-reader/` 整个目录

**重要**: v2.2 兼容 v2.1 API，无需修改调用代码

### 💡 使用示例

**自动启用 RSS 聚合**:
```python
content_pool, citations = search_engine.multi_source_search(
    keywords=["百度 AI"],
    framework_name="深度财报分析",
    params={"公司名": "百度", "股票代码": "BIDU", "期间": "2026Q1"},
    enable_layered_search=True
)
```

系统会自动执行 5 层搜索:
1. Layer 1: 官方财报 PDF (Brave Search)
2. Layer 2: 业绩会 transcript
3. Layer 3: 深度分析 (seekingalpha/ft/reuters)
4. Layer 4: 竞争对手数据
5. **Layer RSS**: 从 17+ RSS 源聚合最新资讯

**RSS 层输出示例**:
```
[Layer RSS] 从财经 RSS 源聚合信息...
[Layer RSS] 找到 2 条 RSS 条目
[Layer RSS] 转换完成，返回 2 条结果
```

**禁用 RSS 聚合**:
```python
# 如果不需要 RSS，可以手动移除 lib/finance-rss-reader/ 目录
# 或者使用传统搜索模式 (enable_layered_search=False)
```

---

## v2.1 (2026-07-01)

### ✨ 新增功能

#### 1. **多层搜索策略 (Layered Search)**

基于财报分析 Workflow v2.0 Step 2 设计,实现4层渐进式搜索:

**第一层: 官方原始来源 (必须有)**
- 使用 Brave Search 定向查询官方财报PDF、10-K报告
- 查询策略: `site:ir.company.com filetype:pdf`
- 置信度: high

**第二层: 业绩会 Transcript (必须有)**
- 搜索 earnings call transcript、业绩会实录
- 获取管理层对业务的解读和问答
- 置信度: high

**第三层: 深度分析文章**
- 定向搜索高质量分析网站 (seekingalpha.com、ft.com、reuters.com等)
- 查询策略: `keyword site:seekingalpha.com`
- 置信度: medium

**第四层: 同行交叉验证**
- 搜索竞争对手的相关信息
- 用于横向对比和市场格局分析
- 置信度: medium

#### 2. **结构化源元数据 (Source Metadata)**

新增8字段结构化源数据追踪:

```python
{
    "source_id": "source_财报快评_1",
    "title": "百度2026Q1财报",
    "publisher": "baidu.com",
    "source_type": "official_report",  # 来源类型
    "publish_date": "2026-06-30",
    "data_period": "2026Q1",
    "url_or_path": "https://...",
    "confidence": "high",  # 置信度
    "notes": "来自 Brave Search - official"
}
```

**source_type 类型**:
- `official_report`: 官方财报
- `earnings_call`: 业绩会记录
- `analysis_article`: 深度分析文章
- `competitor_data`: 竞争对手数据
- `web_search`: 通用网页搜索

**confidence 置信度**:
- `high`: 官方来源、业绩会记录
- `medium`: 深度分析、竞争对手数据
- `low`: 通用搜索结果

#### 3. **Brave Search 集成**

- 新增 `_call_brave_search()` 方法
- 支持 site: 限定、filetype: 过滤
- 返回结构化源元数据

#### 4. **搜索完整度检测 (规划中)**

计划支持搜索完整度验证:
- 当前期间数据已获取
- 历史对比数据已获取
- 竞争对手数据已获取
- 引文来源已覆盖

### 🎯 核心改进

#### API 签名变更

**search_engine.py**:
```python
# v2.0
multi_source_search(keywords, max_results_per_keyword) -> List[Dict]

# v2.1
multi_source_search(
    keywords,
    framework_name,
    params,
    max_results_per_keyword,
    enable_layered_search=True
) -> Tuple[List[Dict], Dict[str, str]]
```

返回值改为 `(content_pool, citations)` 元组

**search_agent.py**:
```python
# v2.0
search_results = self.search_engine.multi_source_search(...)
# 手动构建 content_pool 和 citations

# v2.1
fw_content_pool, fw_citations = self.search_engine.multi_source_search(
    keywords=all_keywords,
    framework_name=framework_name,
    params=params,
    enable_layered_search=True
)
# 直接获取结构化内容池
```

#### 搜索策略优化

- **分层搜索**: 优先获取高质量官方来源
- **定向搜索**: 使用 site: 限定搜索范围
- **置信度标注**: 自动计算来源置信度
- **兼容模式**: 支持传统并行搜索 (enable_layered_search=False)

### 📚 文档更新

- 更新 `lib/search_engine.py` 代码文档
- 新增多层搜索策略说明
- 新增结构化源元数据字段说明

### 🐛 Bug修复

- 修复 `multi_source_search()` 返回值格式不一致问题
- 修复 `search_agent.py` 中 search_engine 调用方式

### 📦 下载

**v2.1 完整包**: https://dwz.cn/nGblEbNG (39.21 KB)

### 🔄 升级说明

如果你已经下载了 v2.0,可以：

1. **完全替换**: 下载 v2.1 覆盖原目录
2. **增量升级**: 只需替换 `lib/search_engine.py` 和 `bin/search_agent.py`

**重要**: v2.1 改变了 `multi_source_search()` API 签名,如果你有自定义调用需要适配

### 💡 使用示例

**启用分层搜索 (推荐)**:
```python
content_pool, citations = search_engine.multi_source_search(
    keywords=["百度 2026Q1 财报"],
    framework_name="深度财报分析",
    params={"公司名": "百度", "期间": "2026Q1"},
    enable_layered_search=True
)
```

系统会自动执行:
1. Layer 1: 搜索官方财报PDF
2. Layer 2: 搜索业绩会 transcript
3. Layer 3: 搜索深度分析文章 (seekingalpha/ft/reuters)
4. Layer 4: 搜索竞争对手数据 (如有)

**传统并行搜索**:
```python
content_pool, citations = search_engine.multi_source_search(
    keywords=["高德地图 新功能"],
    framework_name="PEST分析",
    params={"主题": "高德地图"},
    enable_layered_search=False
)
```

---

## v2.0 (2026-07-01)

### ✨ 新增功能

#### 1. **多框架组合分析能力**

新增 `framework_combinator.py` 模块,支持智能推荐和执行框架组合:

**7种预定义框架组合**:
- 财报快评组合 (财报快评)
- 深度财报分析组合 (深度财报分析 + 3C)
- 同行对比分析组合 (同行对比 + 3C + Porter五力)
- 风险复盘分析组合 (风险专项 + SWOT)
- 新市场进入组合 (PEST + Porter五力 + SWOT)
- 产品策略组合 (3C + 4P + SWOT)
- 全面战略分析组合 (PEST + Porter五力 + 3C + SWOT)

**智能推荐逻辑**:
- 自动检测问题复杂度 (关键词/多维度/长度)
- 复杂问题优先推荐组合框架
- 简单问题推荐单框架
- 支持用户手动选择组合或单框架

#### 2. **问题复杂度识别**

在 `intent_classifier.py` 中新增复杂度判断:

**判断规则**:
1. 显式复杂度指示词: "全面"、"完整"、"系统"、"深入"、"多维度"等
2. 多个高分框架: Top 2分数都>=3且差距<=2
3. 问题长度: 超过50字

**输出示例**:
```python
{
    "framework": "深度财报分析",
    "score": 10,
    "reason": "涉及投资决策",
    "is_complex_problem": True  # 新增字段
}
```

#### 3. **组合执行引擎**

更新 `search_agent.py` 主流程:

**支持按顺序执行多个框架**:
1. 依次执行组合中的每个框架
2. 为每个框架独立搜索和分析
3. 汇总所有内容池
4. 生成综合分析报告

**新增组合报告模板**:
- 执行摘要 (列出所有框架)
- 分框架章节 (第1部分、第2部分...)
- 综合结论 (跨框架总结)

### 🎯 核心改进

#### 用户体验优化

**审核点①增强**:
- 复杂问题先展示组合推荐
- 支持选择 'C1', 'C2' (组合) 或 '1', '2' (单框架)
- 自动模式下,复杂问题自动选组合

**示例交互**:
```
⚠️  检测到这是一个复杂问题,可能需要组合多个分析框架

推荐的框架组合:

1. **深度财报分析组合**
   包含框架: 深度财报分析 → 3C战略三角
   说明: 先用KPI树+3C做深度财报分析,再用3C分析公司-客户-竞争对手三角

也可以选择单个框架:

推荐的单个分析框架:

1. **深度财报分析**
   ...

【人工审核点①】请选择分析方式:
输入 'C1', 'C2'... 选择框架组合
或输入 '1', '2'... 选择单个框架
```

### 📚 文档更新

- 更新 `SKILL.md`,增加框架组合章节
- 新增 `framework_combinator.py` 代码文档
- 更新工作流程图,体现组合分析路径

### 🐛 Bug修复

- 修复 `search_agent.py` 缺少 `typing` 导入
- 修复组合报告生成时的引文索引问题

### 📦 下载

**v2.0 完整包**: https://dwz.cn/1TE6GIJL (34.18 KB)

### 🔄 升级说明

如果你已经下载了 v1.0,可以：

1. **完全替换**: 下载 v2.0 覆盖原目录
2. **增量升级**: 只需添加 `lib/framework_combinator.py` 并更新 `bin/search_agent.py` 和 `lib/intent_classifier.py`

### 💡 使用示例

**复杂问题自动推荐组合**:
```bash
python3 bin/search_agent.py "帮我全面分析百度的经营质量、竞争力和风险因素" --auto
```

系统会自动识别这是复杂问题,推荐"全面战略分析组合",依次执行:
1. PEST分析 (宏观环境)
2. Porter五力 (行业竞争)
3. 3C战略三角 (公司定位)
4. SWOT (综合评估)

**简单问题仍用单框架**:
```bash
python3 bin/search_agent.py "高德地图2026Q1财报快评" --auto
```

系统识别为简单问题,直接使用"财报快评"单框架

---

## v1.0 (2026-07-01)

初始版本,支持:
- 9种单框架分析
- 意图识别
- 多源搜索
- 报告生成

**v1.0 下载**: https://dwz.cn/U9bBwsLt (17.27 KB)
