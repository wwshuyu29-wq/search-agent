# Multi-Agent Workflow Node Playbook

每个子 agent 都按同一条链路推进：输入 -> LLM判断 -> skill/tool调用 -> 输出artifact -> 进入下一步条件。

这份文档是给人看的执行手册；可执行版本在 `lib/workflow_contracts.py`，用 `render_workflow_playbook_markdown()` 可以生成同结构内容。

## Intent Router Agent

**输入**：Raw user query + project context + available skills

**LLM判断**：理解整句需求背后的业务决策，抽取对象、读者、时间范围、输出形态、证据需求、不确定项，并判断关键词分类器是否和语义判断冲突。

**skill/tool调用**：`intent_classifier.py` 做规则兜底；`framework_combinator.py` 做框架组合；`marketing-ideas`、`marketing-plan`、`startup-analysis`、`yfinance-data`、`funda-data` 做 Step 0 专家探针。

**输出artifact**：`IntentBrief + AuditCard`

**进入下一步条件**：审核卡片已输出，用户确认或修改后才能进入搜索规划。

## Search Planner Agent

**输入**：Confirmed AuditCard

**LLM判断**：把确认后的框架维度翻译成证据需求，判断每个维度需要什么来源才能证明或反驳。

**skill/tool调用**：`references/search-platforms.md`、框架关键词模板、中英文关键词扩展。

**输出artifact**：`SearchPlan`

**进入下一步条件**：每个框架维度都有搜索任务、来源层级、期望证据和 source_id 前缀。

## Official Source Hunter

**输入**：SearchPlan official-source tasks

**LLM判断**：判断结果是否是能证明事实的一手来源，例如公司官网、IR、交易所、监管文件、应用商店官方更新。

**skill/tool调用**：Firecrawl、realtime-search Brave、URL full-text fetch。

**输出artifact**：`SourceListFragment rows with OFF### ids`

**进入下一步条件**：官方来源条目包含发布方、日期、URL、key facts、全文抓取状态和可信度理由。

## Media Source Hunter

**输入**：SearchPlan media/deep-analysis tasks

**LLM判断**：判断媒体和深度报道是否提供独立事实、专家解读或市场叙事，并区分事实、解释和观点。

**skill/tool调用**：Firecrawl、realtime-search Brave、realtime-search Baidu、URL full-text fetch。

**输出artifact**：`SourceListFragment rows with MED### ids`

**进入下一步条件**：媒体来源标明报道事实、专家解释或观点属性；付费墙/摘要来源必须降级标注。

## RSS/News Hunter

**输入**：SearchPlan news/RSS tasks

**LLM判断**：把 RSS 当作时效信号层，先看 relevance_score，再语义判断是否值得进入证据池。

**skill/tool调用**：`finance-rss-reader`、`news-aggregator-skill`、高相关条目的 Firecrawl 全文抓取。

**输出artifact**：`SourceListFragment rows with RSS### / NEWS### ids`

**进入下一步条件**：RSS 条目解释 relevance_score 和 confidence；高影响事实必须继续找官方或强来源验证。

## UGC/Social Hunter

**输入**：SearchPlan UGC/social tasks

**LLM判断**：区分用户情绪、抱怨、采用迹象和零散噪音，不把个案直接推成市场事实。

**skill/tool调用**：`agent-reach`、B 站/社交搜索、适用时用 opencli/social readers。

**输出artifact**：`SourceListFragment rows with UGC### ids`

**进入下一步条件**：UGC 条目默认低置信度，除非被官方、数据或多源证据独立验证。

## Finance Data Hunter

**输入**：SearchPlan finance-data tasks

**LLM判断**：判断需要哪类结构化金融数据回答问题，区分单一数字、财报指标、估值、市场情绪和风险数据。

**skill/tool调用**：`yfinance-data`、`yc-reader`、`funda-data`、`twitter-reader`、`opencli-reader`、`tradingview-reader`、`finance-sentiment`。

**输出artifact**：`SourceListFragment rows with FIN### ids`

**进入下一步条件**：每个数字都有期间、币种、指标定义、来源和口径说明。

## Marketing Intelligence Hunter

**输入**：SearchPlan marketing/source-discovery tasks

**LLM判断**：判断市场、客户、竞品、渠道、漏斗或品牌证据分别需要什么来源。

**skill/tool调用**：`competitor-profiling`、`customer-research`、`directory-submissions`、`public-relations`、`analytics`。

**输出artifact**：`SourceListFragment rows with MKT### ids`

**进入下一步条件**：营销证据必须绑定用户分群、渠道、漏斗阶段、行为信号或指标，不能只是泛泛建议。

## SourceList Merger

**输入**：SourceListFragment rows from all Source Hunter nodes

**LLM判断**：不做新搜索、不写分析；只判断哪些来源是重复、转载、同源摘要或原始出处，并保留渠道来源关系。

**skill/tool调用**：URL canonicalizer、schema validator、content hash / duplicate checks。

**输出artifact**：`RawSourceList + MergerLog`

**进入下一步条件**：source_id 唯一，重复 URL 已合并，canonical_url 清楚，MergerLog 记录被合并或重写的来源。

## Source QA Agent

**输入**：RawSourceList + SearchPlan

**LLM判断**：挑战来源质量，检查重复、过期、付费摘要、数字冲突、来源独立性和缺失证据。

**skill/tool调用**：URL normalization、duplicate checks、date parsing、numeric comparison。

**输出artifact**：`SourceQANotes + ConflictRegister + GapList + CleanSourceList`

**进入下一步条件**：高影响冲突已解决、降级或暂停给用户选择；只有 approved sources 可以进入分析。

## Gap Filler / Conflict Refetch Agent

**输入**：GapList + ConflictRegister

**LLM判断**：只处理 Source QA 明确列出的缺口和冲突，判断是否能通过一次定向补搜找到一手来源或权威口径。

**skill/tool调用**：Firecrawl、realtime-search Brave、URL full-text fetch、official/regulatory/IR search、finance skill。

**输出artifact**：`SupplementalSourceList + RefetchNotes`

**进入下一步条件**：补充来源必须回填 gap_id/conflict_id；仍无法解决的冲突必须暂停给用户选口径，不能强行进入分析。

## Framework Analyst Agent

**输入**：CleanSourceList + confirmed framework dimensions

**LLM判断**：把证据变成框架维度下的事实、计算、假设和判断，并说明推理依据。

**skill/tool调用**：framework definitions、finance specialist outputs、marketing specialist outputs。

**输出artifact**：`ClaimGraph`

**进入下一步条件**：每个关键 claim 都有 claim_type、source_ids、confidence 和 reasoning_basis。

## Financial Specialist Agent

**输入**：CleanSourceList + finance questions from ClaimGraph

**LLM判断**：解释财务指标、可持续性、估值和金融风险，并把它们放回用户决策语境。

**skill/tool调用**：`yfinance-data`、`funda-data`、`earnings-preview`、`earnings-recap`、`estimate-analysis`、`company-valuation`、`stock-liquidity`、`stock-correlation`。

**输出artifact**：`FinanceClaims appended to ClaimGraph`

**进入下一步条件**：所有金融数字都有期间、币种、同比/环比或指标定义和 source_id。

## Marketing Specialist Agent

**输入**：CleanSourceList + marketing/growth questions from ClaimGraph

**LLM判断**：解释定位、用户痛点、渠道杠杆、漏斗阶段和行动可行性。

**skill/tool调用**：`marketing-ideas`、`marketing-plan`、`product-marketing`、`customer-research`、`pricing`、`ads`、`copywriting`、`analytics`、`ab-testing`、`competitor-profiling`。

**输出artifact**：`MarketingClaims appended to ClaimGraph`

**进入下一步条件**：建议必须映射到 segment、channel、funnel stage、metric 和 evidence。

## Citation Auditor Agent

**输入**：ClaimGraph + CleanSourceList + SpecialistNotes

**LLM判断**：逐条读 claim 和引用来源，判断来源是否真的支持这句话，是充分、部分还是不支持。

**skill/tool调用**：source_id existence checks、reference table checks、claim-source comparison。

**输出artifact**：`CitationAudit + ApprovedClaimGraph`

**进入下一步条件**：unsupported claims 被删除、改写或降级；CitationAudit 状态为 pass 才能写报告。

## Report Writer Agent

**输入**：ApprovedClaimGraph + CitationAudit + CleanSourceList

**LLM判断**：选择适合读者和决策的报告形态，把 claim graph 压缩成可用的业务文档。

**skill/tool调用**：report family selector、reference table renderer、金融/可视化场景可选 generative-ui。

**输出artifact**：`ReportDraft`

**进入下一步条件**：报告回答用户决策，保留引用，说明风险和不确定性，不硬套三段式模板。

## Humanizer Editor Agent

**输入**：ReportDraft + CleanSourceList + reader profile

**LLM判断**：只做表达层面的去 AI 味，删掉空泛转折、强行三点式、模板腔和泛化形容词。

**skill/tool调用**：`humanizer`、`humanizer-zh`、`copy-editing`。

**输出artifact**：`FinalReport + HumanizerChangeLog`

**进入下一步条件**：事实、数字、引用、置信度和风险边界未被改变，文本像专业内部调研简报。

## Integrity Diff Checker

**输入**：ReportDraft + FinalReport + HumanizerChangeLog

**LLM判断**：检查 Humanizer 是否改坏事实、数字、日期、source_id、claim_id、confidence、风险边界或结论强弱。

**skill/tool调用**：local diff、regex extraction for numbers/dates/source_id/claim_id、schema validator。

**输出artifact**：`IntegrityDiff`

**进入下一步条件**：IntegrityDiff 必须 passed 才能进入 final_report_review；失败则退回 Humanizer，只允许表达层修改。
