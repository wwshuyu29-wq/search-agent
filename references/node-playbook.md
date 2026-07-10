# Multi-Agent Workflow Node Playbook

每个子 agent 都按同一条链路推进：输入 -> LLM判断 -> skill/tool调用 -> 输出artifact -> 进入下一步条件。

## Intent Router Agent

**输入**：Raw user query + project context + available skills

**职责边界**：Only frames the user's business decision and proposed workflow route before any search.

**LLM判断**：Read the whole request as a business decision: object, audience, time scope, output shape, evidence need, ambiguity, and conflicts with keyword signals.

**skill/tool调用**：intent_classifier.py as deterministic fallback；framework_combinator.py after semantic routing；marketing-ideas / marketing-plan / startup-analysis / yfinance-data / funda-data as Step 0 probes

**可做**：Extract decision context；recommend frameworks；list expert skills；produce AuditCard

**不可做**：Search sources；write findings；skip user confirmation

**输出artifact**：IntentBrief + AuditCard

**进入下一步条件**：Stop before search until the user confirms or revises the audit card.

**交给下一步**：Search Planner after audit_card_confirmed.

**硬约束**：No web search before confirmation.；Keyword hits cannot override the LLM semantic read.；If a specialist skill is triggered, list why in the audit card.

## Search Planner Agent

**输入**：Confirmed AuditCard

**职责边界**：Only turns the confirmed AuditCard into source-specific search tasks.

**LLM判断**：Translate each confirmed framework dimension into evidence needs, source classes, search language, and expected proof.

**skill/tool调用**：references/search-platforms.md；framework keyword templates；Chinese/English keyword expansion

**可做**：Create query families；assign hunters；define expected evidence；set source_id prefixes

**不可做**：Fetch sources；analyze evidence；change confirmed framework without user input

**输出artifact**：SearchPlan

**进入下一步条件**：Every dimension has at least one task, one source layer, and expected evidence.

**交给下一步**：Parallel Source Hunter nodes.

**硬约束**：Do not search generic keywords without a dimension purpose.；Separate official, media, RSS, UGC, finance data, and marketing data tasks.

## Official Source Hunter

**输入**：SearchPlan official-source tasks

**职责边界**：Only collects primary/original sources for confirmed tasks.

**LLM判断**：Judge whether a result is the primary source that can prove the claim.

**skill/tool调用**：Firecrawl；realtime-search Brave；URL full-text fetch

**可做**：Search official sites；fetch original pages；normalize OFF### rows

**不可做**：Use media as official proof；interpret strategy；invent missing dates

**输出artifact**：SourceListFragment rows with OFF### ids

**进入下一步条件**：Official rows include publisher, date, URL, key facts, and fetched/full-text status.

**交给下一步**：SourceList Merger.

**硬约束**：Official announcements and filings outrank media summaries.；Do not use a media article as official evidence when the original source is available.

## Media Source Hunter

**输入**：SearchPlan media/deep-analysis tasks

**职责边界**：Only collects secondary reporting and separates fact from framing.

**LLM判断**：Judge which media results add verified context, expert interpretation, or independent reporting.

**skill/tool调用**：Firecrawl；realtime-search Brave；realtime-search Baidu；URL full-text fetch

**可做**：Search media；fetch article text；label fact/interpretation/opinion

**不可做**：Let media override official facts；treat commentary as proof；hide paywall limits

**输出artifact**：SourceListFragment rows with MED### ids

**进入下一步条件**：Media rows distinguish reported fact, expert interpretation, and opinion.

**交给下一步**：SourceList Merger.

**硬约束**：Do not let media framing outrank official evidence for primary facts.；Paywalled or excerpt-only sources must be marked as summary evidence.

## RSS/News Hunter

**输入**：SearchPlan news/RSS tasks

**职责边界**：Only collects timely RSS/news signals and relevance-gates them.

**LLM判断**：Use RSS as a recency and signal layer, then semantically filter candidates.

**skill/tool调用**：finance-rss-reader；news-aggregator-skill；Firecrawl full-text fetch for high-relevance items

**可做**：Scan RSS；score relevance；route high-signal items for stronger verification

**不可做**：Treat relevance_score as truth；prove exact launch facts from RSS alone；skip stronger sources

**输出artifact**：SourceListFragment rows with RSS### / NEWS### ids

**进入下一步条件**：RSS candidates explain relevance score and confidence; high-impact facts need stronger sources.

**交给下一步**：SourceList Merger.

**硬约束**：relevance_score >= 0.6 is a full-text fetch gate, not a truth score.；RSS alone cannot prove official financial results, regulation, or exact launch facts.

## UGC/Social Hunter

**输入**：SearchPlan UGC/social tasks

**职责边界**：Only collects public UGC/social signals as sentiment or adoption evidence.

**LLM判断**：Separate user sentiment, complaints, adoption signals, and anecdotal noise.

**skill/tool调用**：agent-reach；Bilibili / social search where available；opencli-reader / social readers for finance communities when applicable

**可做**：Search B站/social platforms；record public URLs；summarize sentiment patterns

**不可做**：Generalize anecdotes into market facts；collect private identifiers；treat UGC as official evidence

**输出artifact**：SourceListFragment rows with UGC### ids

**进入下一步条件**：UGC rows are labeled low confidence unless independently verified.

**交给下一步**：SourceList Merger and Source QA for confidence downgrading.

**硬约束**：Do not generalize UGC anecdotes into market facts.；Do not expose private personal identifiers.

## Finance Data Hunter

**输入**：SearchPlan finance-data tasks

**职责边界**：Only collects structured finance/data rows when the task truly needs them.

**LLM判断**：Decide which structured finance data can answer the financial part of the question.

**skill/tool调用**：yfinance-data；funda-data；tradingview-reader；finance-sentiment

**可做**：Fetch yfinance snapshots；route setup-aware finance adapters；emit FIN### rows

**不可做**：Run finance tools for non-finance map marketing tasks；give investment advice；treat sentiment as performance

**输出artifact**：SourceListFragment rows with FIN### ids

**进入下一步条件**：Every numeric row has period, currency, metric definition, and source.

**交给下一步**：SourceList Merger.

**硬约束**：Single-number queries short-circuit the full report unless interpretation is requested.；Market sentiment is not company performance evidence by itself.

## Marketing Intelligence Hunter

**输入**：SearchPlan marketing/source-discovery tasks

**职责边界**：Only routes marketing method skills and source-discovery hints; it is not market proof by itself.

**LLM判断**：Decide which market, customer, competitor, channel, or funnel evidence is needed.

**skill/tool调用**：competitor-profiling；customer-research；directory-submissions；public-relations；analytics

**可做**：Select fine-grained marketing skills；emit method-source rows；identify source needs

**不可做**：Convert generic marketing advice into findings；add unsupported recommendations；replace external evidence

**输出artifact**：SourceListFragment rows with MKT### ids

**进入下一步条件**：Marketing rows identify segment, channel, funnel stage, or behavior signal.

**交给下一步**：SourceList Merger and Marketing Specialist.

**硬约束**：Do not convert generic marketing advice into a finding.；Recommendations must tie to audience, channel, funnel stage, or metric.

## SourceList Merger

**输入**：SourceListFragment rows from all Source Hunter nodes

**职责边界**：Only merges and dedupes source fragments without adding meaning.

**LLM判断**：Do not search or analyze; deterministically merge hunter fragments, dedupe canonical URLs, preserve channel provenance, and keep original-source priority.

**skill/tool调用**：URL canonicalizer；schema validator；content hash / duplicate checks

**可做**：Canonicalize URLs；merge duplicates；preserve provenance；write MergerLog

**不可做**：Create facts；drop provenance；rank claims

**输出artifact**：RawSourceList + MergerLog

**进入下一步条件**：source_id values are unique, duplicate URLs are merged, and MergerLog records what changed.

**交给下一步**：Source QA.

**硬约束**：Do not create new facts while merging.；Do not drop channel provenance when deduplicating.；Official/original sources outrank reposts and media summaries.

## Source QA Agent

**输入**：RawSourceList + SearchPlan

**职责边界**：Only approves, downgrades, excludes, or flags sources before analysis.

**LLM判断**：Challenge source strength, conflicts, missing evidence, freshness, and source independence.

**skill/tool调用**：URL normalization；duplicate checks；date parsing；numeric comparison

**可做**：Check freshness；detect conflicts；produce GapList；approve CleanSourceList

**不可做**：Write analysis；resolve conflicts by guessing；bury weak-source caveats

**输出artifact**：SourceQANotes + ConflictRegister + GapList + CleanSourceList

**进入下一步条件**：High-impact conflicts are resolved, downgraded, or paused for user choice.

**交给下一步**：Gap Filler when blocked, otherwise Framework/Specialist analysis.

**硬约束**：Do not analyze from stale or duplicate sources without marking the limitation.；Paywalled summaries must be labeled as summaries.

## Gap Filler / Conflict Refetch Agent

**输入**：GapList + ConflictRegister

**职责边界**：Only fills Source QA-listed gaps or conflicts.

**LLM判断**：Only address gaps or conflicts explicitly raised by Source QA; find original sources, resolve numeric口径, or mark unresolved conflict.

**skill/tool调用**：Firecrawl；realtime-search Brave；URL full-text fetch；official / regulatory / IR search；finance skill when the conflict is financial

**可做**：Refetch official sources；target exact conflicts；write RefetchNotes

**不可做**：Expand scope；start new research threads；force unresolved conflicts through

**输出artifact**：SupplementalSourceList + RefetchNotes

**进入下一步条件**：Resolved gaps are tied back to gap_id/conflict_id; unresolved items remain paused for user choice.

**交给下一步**：Source QA or Framework Analyst after gap/conflict closure.

**硬约束**：Do not expand beyond Source QA's listed gaps or conflicts.；Do not introduce new research directions without user confirmation.

## Framework Analyst Agent

**输入**：CleanSourceList + confirmed framework dimensions

**职责边界**：Only converts approved evidence into framework-structured claims.

**LLM判断**：Turn evidence into dimension-level facts, calculations, assumptions, and judgments.

**skill/tool调用**：framework definitions；finance specialist outputs；marketing specialist outputs

**可做**：Label claim types；group by dimension；state reasoning basis

**不可做**：Use unapproved sources；mix facts and judgments；overclaim weak evidence

**输出artifact**：ClaimGraph

**进入下一步条件**：Every material claim has source_ids and claim_type.

**交给下一步**：Finance/Marketing Specialists and Citation Auditor.

**硬约束**：Weak evidence must be written as evidence-limited and low confidence.；Do not mix fact, calculation, assumption, and judgment in one unlabeled claim.

## Financial Specialist Agent

**输入**：CleanSourceList + finance questions from ClaimGraph

**职责边界**：Only handles finance-specific interpretation when the confirmed task requires it.

**LLM判断**：Interpret financial metrics, sustainability, valuation, and risk in the user's decision context.

**skill/tool调用**：yfinance-data；funda-data；earnings-preview；earnings-recap；estimate-analysis；company-valuation；stock-liquidity；stock-correlation

**可做**：Add metric interpretation；state assumptions；patch ClaimGraph with sourced finance claims

**不可做**：Make trade recommendations；omit period/currency/口径；force finance into map marketing tasks

**输出artifact**：FinanceClaims appended to ClaimGraph

**进入下一步条件**：All numbers carry period, currency, YoY/QoQ or definition, and source_id.

**交给下一步**：Citation Auditor.

**硬约束**：Separate research judgment from investment advice.；No valuation conclusion without risk and assumption framing.

## Marketing Specialist Agent

**输入**：CleanSourceList + marketing/growth questions from ClaimGraph

**职责边界**：Only turns approved evidence into marketing, positioning, growth, and action logic.

**LLM判断**：Interpret positioning, customer pain, channel leverage, funnel stage, and actionability.

**skill/tool调用**：marketing-ideas；marketing-plan；product-marketing；customer-research；pricing；ads；copywriting；analytics；ab-testing；competitor-profiling

**可做**：Map segment/channel/funnel/metric；use marketing skills as methods；patch ClaimGraph

**不可做**：Give generic advice；invent user insights；ignore evidence gaps

**输出artifact**：MarketingClaims appended to ClaimGraph

**进入下一步条件**：Recommendations map to segment, channel, funnel stage, metric, and evidence.

**交给下一步**：Citation Auditor.

**硬约束**：No empty advice such as '加强宣传' without a mechanism.；Do not force STP/4P/AARRR when the user's decision needs a competitor memo.

## Citation Auditor Agent

**输入**：ClaimGraph + CleanSourceList + SpecialistNotes

**职责边界**：Only checks claim-source support before report writing.

**LLM判断**：Read each claim against cited sources and judge whether support is real, partial, or absent.

**skill/tool调用**：source_id existence checks；reference table checks；claim-source comparison

**可做**：Verify source_ids；downgrade claims；block unsupported statements

**不可做**：Add new claims；rewrite strategy beyond support；accept topic-only citations

**输出artifact**：CitationAudit + ApprovedClaimGraph

**进入下一步条件**：Unsupported claims are removed, rewritten, or downgraded before report writing.

**交给下一步**：Outline Architect after CitationAudit passes.

**硬约束**：No citation, no factual claim.；A source that mentions a topic does not automatically support the sentence.

## Outline Architect Agent

**输入**：ApprovedClaimGraph + IntentBrief

**职责边界**：只设计大纲，不写正文。

**LLM判断**：生成全景对比、因果深挖、行动决策三套差异化结构，并按读者/决策推荐一套。

**skill/tool调用**：brainstorming；writing-plans；content-strategy

**可做**：推荐；解释取舍；绑定 claim_ids；分配字数

**不可做**：替用户确认；给三个换皮大纲；写正文

**输出artifact**：OutlinePlan

**进入下一步条件**：三套大纲完整且推荐理由明确。

## Human Outline Approval Gate

**输入**：OutlinePlan

**职责边界**：展示推荐，记录用户选择、组合或修改。

**输出artifact**：ApprovedOutline

**进入下一步条件**：approved_by_user=true。

**硬约束**：不得从沉默推断批准；未确认不得写正文。

## Report Writer Agent

**输入**：ApprovedOutline + ApprovedClaimGraph + CleanSourceList

**职责边界**：只在用户确认的结构内扩写深度正文。

**LLM判断**：按章节 purpose、required_claim_ids 和 word_budget 完成论证。

**skill/tool调用**：writing-plans；copywriting；content-strategy

**可做**：扩写论证；保留引文；暴露证据缺口；写参考文献

**不可做**：新增/删除/改名/重排一级章节；添加未审计 claims；强套倒金字塔

**输出artifact**：ReportDraft

**进入下一步条件**：正文严格继承 ApprovedOutline。

**交给下一步**：Outline Compliance Auditor.

## Outline Compliance Auditor Agent

**输入**：ApprovedOutline + ReportDraft

**职责边界**：只审核结构一致性，不改写正文。

**skill/tool调用**：copy-editing；verification-before-completion

**输出artifact**：OutlineComplianceReview

**进入下一步条件**：status=passed 后才能交 Humanizer。

**硬约束**：章节缺失、顺序变化或未经确认的新章节必须阻塞。

## Humanizer Editor Agent

**输入**：ReportDraft + CleanSourceList + reader profile

**职责边界**：Only edits expression and removes AI-like phrasing.

**LLM判断**：Remove AI-like phrasing while preserving evidence, numbers, citations, and risk boundaries.

**skill/tool调用**：humanizer；humanizer-zh；copy-editing

**可做**：Tighten wording；remove filler；adapt tone to market team reader

**不可做**：Change facts；change citations；increase certainty；delete caveats

**输出artifact**：FinalReport + HumanizerChangeLog

**进入下一步条件**：Final text sounds like a professional internal research note, not a prompt template.

**交给下一步**：Integrity Diff Checker.

**硬约束**：Do not change facts, numbers, citations, or confidence levels.；Do not add personality or unsupported certainty.

## Integrity Diff Checker

**输入**：ReportDraft + FinalReport + HumanizerChangeLog

**职责边界**：Only verifies the Humanizer preserved evidence-bearing content.

**LLM判断**：Check whether the Humanizer changed facts, numbers, dates, source_ids, claim_ids, confidence labels, risk boundaries, or conclusion strength.

**skill/tool调用**：local diff；regex extraction for numbers/dates/source_id/claim_id；schema validator

**可做**：Compare numbers/dates/source_ids；flag changed risk labels；block final review

**不可做**：Rewrite the report；approve changed facts；skip failed diff

**输出artifact**：IntegrityDiff

**进入下一步条件**：No factual, numeric, citation, confidence, or risk-boundary changes before final review.

**交给下一步**：Final report review or back to Humanizer.

**硬约束**：If integrity fails, return to Humanizer; do not send to final review.；Style edits are allowed; evidence changes are not.
