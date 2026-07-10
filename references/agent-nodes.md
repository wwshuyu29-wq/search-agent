# Agent Nodes and Decision Contracts

This document defines how search-agent should think and delegate work. It is the contract future Codex runs must follow when a research request moves from Step 0 to the final report.

The executable version of this contract lives in `lib/workflow_contracts.py`.
Future code and tests should treat that module as the source of truth for node
ordering, specialist skill chains, RSS relevance threshold meaning, and report
family selection.

The lightweight gate checker lives in `lib/workflow_orchestrator.py`. It uses
the artifact contracts to validate required handoff fields and route from one
completed gate to the next workflow phase.

Use these executable helpers when implementing or inspecting the workflow:

- `get_node_contracts()`: ordered sub-agent contracts, including `Media Source Hunter`.
- `get_artifact_contracts()`: typed handoff artifacts and required fields.
- `get_orchestration_plan()`: Step 0-3 execution order, parallel groups, and gates.
- `build_agent_prompt(node_id)`: concrete prompt for a single sub-agent, including schema and hard constraints.
- `get_skill_chain(domain)`: finance, marketing, and mixed finance x marketing skill chains.

金字塔结构在这里是内部组织原则：先回答决策，再给证据支撑、分析展开、风险和参考文献；它不是要求所有报告都长成同一个可见模板。

Every node contract must expose these fields:

- `input_artifact`: what the node receives from the previous node.
- `llm_judgment`: what the LLM is responsible for understanding or deciding.
- `tool_or_skill_use`: which tool or skill is used, how, and why.
- `output_artifact`: what structured artifact is handed to the next node.
- `quality_gate`: what must be true before the pipeline can move on.
- `hard_constraints`: what the node must not do.

## Core Principle

`lib/intent_classifier.py` and `lib/framework_combinator.py` are not the brain. They are deterministic guardrails. The actual Step 0 decision stack is:

1. **LLM 语义理解层**: understand the user's business decision, audience, object, time horizon, ambiguity, and desired output.
2. **专家 skill 前置探针**: call or prepare the relevant expert skill when the request is fuzzy, specialized, or better answered by a vertical model/tool.
3. **规则/关键词分类器**: use keyword scoring as a checklist, regression guard, and CLI fallback.
4. **框架组合器**: assemble the smallest framework set that can answer the decision without bloating the workflow.
5. **人工审核卡片**: present the proposed topic, purpose, framework, dimensions, keywords, source range, and skill usage. Stop until the user confirms.

The rule classifier can never override an obvious LLM semantic read. If the LLM and keyword route disagree, the audit card must say so and explain the final recommendation.

## Step 0 Decision Logic

### Semantic Signals Are Not Keyword Lists

增长类问题、单一金融数字、竞品问题、营销方案问题都不能只靠关键词判断。关键词只是**语义信号**，不是封闭枚举。LLM must judge the user's intent from the whole utterance, including verbs, implied audience, object type, expected output, and evidence need.

Examples:

| Surface words | LLM interpretation | Route |
|---|---|---|
| "暑期怎么做", "从哪些方向入手", "拉新", "提升活跃" | User wants growth levers or campaign directions | Marketing/growth route; use `marketing-ideas` if framing is fuzzy |
| "最新市值", "现在股价", "Q1 收入是多少" | User asks for one factual financial number | Use `yfinance-data`/`funda-data`; short-circuit full report unless interpretation is requested |
| "高德上新了什么功能，给市场组方案" | User wants competitor monitoring plus response plan | Competitor/JTBD/3C route, not generic marketing-plan only |
| "品牌力对股价影响" | User asks for a finance x marketing causal chain | Ask for investor/operating/new-business lens |

If a user avoids these exact words but clearly implies the same decision, follow the implication. If the words appear but the larger sentence points elsewhere, follow the larger sentence and mention the conflict in the audit card.

### 1. LLM 语义理解层

Extract these fields before choosing a framework:

| Field | Question | Example |
|---|---|---|
| research_object | What exact company/product/industry/event is being studied? | 高德地图新功能 |
| user_decision | What decision will this support? | 百度地图是否要跟进或反制 |
| audience | Who will read or act on the result? | 市场组/产品策略 |
| time_scope | What period matters? | 最近三个月 |
| output_shape | What deliverable is implied? | 竞品简报/方案/报告 |
| evidence_need | What proof is required? | 官方更新、媒体报道、UGC、应用商店记录 |
| ambiguity | What is unclear enough to ask or expose in the card? | 功能范围、竞品名单、是否需要内网源 |

The LLM must translate vague user wording into a business question. For example, "高德地图上新了什么功能，汇总成方案" is not just a news search. It is a competitor tracking and response-planning task, so the default route is `同行竞争对比 + JTBD/3C` with optional `SWOT` or `4P` depending on whether the user wants actions.

### 2. 专家 skill 前置探针

Use expert skills in Step 0 when they improve the framing before search:

| Trigger | Skill | Step 0 use |
|---|---|---|
| User says "帮我想想", "不知道从哪看", "给我一些方向" in a marketing/growth context | `marketing-ideas` | Generate candidate angles, then ask the user to choose or use the best 2-3 as card dimensions. |
| User asks for a full marketing plan, GTM plan, launch plan, or campaign skeleton | `marketing-plan` | Use the plan skeleton to choose STP/4P/AIDA/AARRR ordering and deliverable shape. |
| Startup, VC, founder, joining a startup, fundraising, or venture-quality question | `startup-analysis` | Route by VC/founder/candidate lens before choosing financial and strategic frameworks. |
| Single numeric finance query: price, market cap, revenue, EPS, next earnings date | `yfinance-data` or `funda-data` | Short-circuit the full workflow unless the user asks for interpretation. |
| Public company investment question with both market data and narrative | `funda-data` plus financial framework | Add FIN sources to Step 1 and use financial specialist analysis in Step 2. |

These skills are not decorative. The audit card must list which expert skills will be used and why. If a trigger matches but the skill is unavailable, state the fallback.

### 3. 规则/关键词分类器

Use `lib/intent_classifier.py` after the semantic pass:

- Confirm obvious routes and expose a reproducible score.
- Catch simple CLI cases where no LLM is available.
- Provide regression tests for common prompts.

Do not treat keyword hits as the final answer. For example, the word "方案" does not always mean marketing-plan; it may mean an internal response plan after competitor monitoring.

### 4. 框架组合器

Use `lib/framework_combinator.py` only after deciding the core decision. The preferred combination is the smallest one that answers the question:

- Competitor movement -> `同行竞争对比 + 3C/JTBD`
- Industry entry -> `PEST + Porter 五力 + STP`
- Investment judgment -> `深度财报 + 杜邦 + 护城河 + 估值 + 风险`
- Marketing execution -> `STP + 4P + AIDA/AARRR`
- Risk scan -> `风险专项 + SWOT 决策矩阵`

If more than four frameworks are needed, the audit card must explain why; otherwise the run becomes broad but shallow.

## Node Contracts

### R0 execution-layer update

The executable contract has moved from a direct `SourceList -> Source QA -> ClaimGraph`
path to a stricter evidence chain:

```text
SourceListFragment
  -> SourceList Merger
  -> RawSourceList + MergerLog
  -> Source QA
  -> SourceQANotes + ConflictRegister + GapList + CleanSourceList
  -> optional Gap Filler / Conflict Refetch
  -> ClaimGraph + SpecialistNotes + ClaimGraphPatch
  -> CitationAudit + ApprovedClaimGraph
  -> ReportDraft
  -> FinalReport + HumanizerChangeLog
  -> IntegrityDiff
```

When this document and `lib/workflow_contracts.py` differ, treat
`lib/workflow_contracts.py` as the source of truth. Source Hunter nodes now
produce `SourceListFragment` rows, not final analysis-ready sources. The
`SourceList Merger` performs deterministic dedupe/canonicalization before
Source QA. `Integrity Diff Checker` must pass before final review.

### Intent Router Agent

**Role**: Convert the user's message into a business decision and propose the framework path.

**Input**: Raw user query, project context, available skills.

**Output**: Audit card with topic, purpose, LLM semantic read, recommended framework, dimensions, keywords, source scope, expert skills, and open assumptions.

**Must do**:
- Use LLM 语义理解 before keyword scoring.
- Run 专家 skill 前置 when a trigger matches.
- Mention conflicts between LLM judgment and keyword classifier.
- Stop after the audit card.

**Must not do**:
- Search the web before confirmation.
- Hide uncertainty.
- Select a framework only because a keyword matched.

### Search Planner Agent

**Role**: Turn confirmed framework dimensions into search tasks.

**Input**: Confirmed audit card.

**Output**: Search plan with per-dimension Chinese/English queries, source layers, expected evidence, and source_id prefixes.

**Must do**:
- Map every framework dimension to at least one search query.
- Add expanded keyword families.
- Mark official, media, UGC, RSS, data API, and internal sources separately.

### Source Hunter Agent

**Role**: Execute multi-source search and fetch raw evidence.

**Input**: Search plan.

**Output**: SourceListFragment rows.

**Must do**:
- Prioritize Layer 1 official sources before media and social sources.
- Normalize every item into `source_id / title / publisher / source_type / publish_date / url / confidence / key_facts / full_text_fetched`.
- Keep UGC/social sources as low-confidence sentiment unless independently verified.

### SourceList Merger

**Role**: Merge SourceListFragment rows from all Source Hunter nodes without adding facts.

**Input**: SourceListFragment rows.

**Output**: RawSourceList and MergerLog.

**Must do**:
- Canonicalize URLs and merge duplicates.
- Preserve channel provenance.
- Keep original/official sources ahead of reposts or summaries.
- Record merged source IDs and id rewrites.

### Gap Filler / Conflict Refetch Agent

**Role**: Address only Source QA gaps and conflicts.

**Input**: GapList and ConflictRegister.

**Output**: SupplementalSourceList and RefetchNotes.

**Must do**:
- Refetch original official/IR/regulatory sources for listed conflicts.
- Avoid expanding the research scope without user confirmation.
- Leave unresolved conflicts visible for user decision.

### Integrity Diff Checker

**Role**: Verify Humanizer did not change evidence-bearing content.

**Input**: ReportDraft, FinalReport, HumanizerChangeLog.

**Output**: IntegrityDiff.

**Must do**:
- Compare numbers, dates, source_ids, claim_ids, confidence labels, and risk boundaries.
- Block final review if evidence-bearing content changed.

### Media Source Hunter

**Role**: Collect and judge non-official media, deep analysis, and secondary reporting.

**Input**: SearchPlan media/deep-analysis tasks.

**Output**: SourceList rows with `MED###` source IDs.

**Must do**:
- Use Firecrawl, Brave, Baidu, and URL full-text fetch for media and analysis pages.
- Separate reported fact, expert interpretation, and opinion.
- Mark paywalled or excerpt-only articles as summary evidence.

**Must not do**:
- Let media framing outrank official evidence for primary facts.
- Treat a topic mention as proof of a claim.

### Source QA Agent

**Role**: Validate evidence before analysis.

**Input**: YAML source list.

**Output**: Clean source list, conflict notes, missing-source warnings.

**Must do**:
- Deduplicate URLs.
- Flag stale dates and paywalled summaries.
- Cross-check key numbers with at least two independent sources when possible.
- Pause for user choice if two high-impact numbers conflict.

### Framework Analyst Agent

**Role**: Analyze evidence according to the confirmed framework.

**Input**: Clean source list, confirmed framework, dimension questions.

**Output**: Claim graph grouped by framework dimension.

**Must do**:
- Label every claim as fact, calculation, assumption, or judgment.
- Attach source_id to every factual or numeric claim.
- Use expert financial/marketing skills when the framework calls for them.
- State "证据有限，推测如下（置信度：低）" for weakly supported interpretations.

### Financial Specialist Agent

**Role**: Handle finance, valuation, market data, and financial risk.

**Use when**: 财报、估值、投资判断、股价、现金流、ROE、风险预警.

**Must do**:
- Use `yfinance-data`, `funda-data`, `earnings-recap`, `company-valuation`, or related finance skills when applicable.
- Include period, currency, YoY/QoQ basis, and data source for every number.
- Separate research from investment advice.

### Marketing Specialist Agent

**Role**: Handle positioning, customer research, GTM, growth, and brand questions.

**Use when**: STP, 4P, AARRR, JTBD, CBBE, AIDA, launch, pricing, channel, user pain points.

**Must do**:
- Use `marketing-ideas` or `marketing-plan` in Step 0 when framing is unclear or plan-shaped.
- Use `customer-research`, `product-marketing`, `pricing`, `competitor-profiling`, `analytics`, or related skills in Step 2 when analysis needs depth.
- Tie recommendations to user segment, channel, funnel stage, or conversion metric.

### Citation Auditor Agent

**Role**: Check that claims and citations actually match.

**Input**: Draft analysis or report, source list.

**Output**: Citation issue list or approval.

**Must do**:
- Verify every source_id exists in the reference table.
- Verify cited sources support the sentence they are attached to.
- Reject unsupported numbers and vague conclusions.
- Require source replacement or wording downgrade when support is weak.

### Report Writer Agent

**Role**: Convert the audited claim graph into an executive report.

**Input**: Audited claim graph, source list, framework.

**Output**: Markdown report.

**Must do**:
- Use conclusion-first logic: 一句话总判断 -> supporting reasons -> framework sections -> risks -> references, while adapting the visible structure to the selected report family.
- Write a 一句话总判断 only when the evidence supports it.
- Use 2-5 supporting reasons; default to 3 because business readers scan that shape well, but do not force exactly 3 when evidence says otherwise.
- Keep every material claim cited.

**Must not do**:
- Force every report into a visible "三条理由/四个维度/五个建议" pattern when the evidence does not naturally support it.
- Use filler transitions like "综上所述", "值得注意的是", "从多个维度来看" unless they carry meaning.
- Write generic consultant prose that could fit any company.

### Humanizer Editor Agent

**Role**: Remove AI-like writing patterns after citation audit, without weakening evidence or changing the conclusion.

**Input**: Citation-audited report draft, source list, intended reader.

**Output**: Natural final report.

**Must do**:
- 去 AI 味 by removing empty template phrasing, forced rule-of-three, inflated significance, vague attribution, repetitive transitions, and generic "关键/重要/显著" language.
- Preserve source_id citations, numbers, caveats, and framework logic.
- Vary sentence rhythm while keeping business writing concise.
- Prefer concrete nouns and verbs over abstract filler.
- Match the target reader: market team reports can be sharper and action-oriented; financial reports stay neutral and precise.

**Must not do**:
- Delete evidence because it sounds stiff.
- Add personality that conflicts with a professional research report.
- Turn risk language into overconfident recommendations.

## Report Logic

The report is not a template fill. It is a compression of the audited claim graph, then a human editing pass.

1. **Claim graph first**: Framework Analyst produces dimension-level claims with source_ids.
2. **Synthesis second**: Report Writer groups claims by the decision they support.
3. **Pyramid top**: The one-sentence judgment answers the user's decision directly. If a one-sentence judgment would be fake confidence, use a qualified judgment.
4. **Support layer**: The top 2-5 reasons are selected by evidence strength and decision relevance. Three reasons is a default scanning pattern, not a quota.
5. **Framework body**: Sections preserve the analytical trace so the reader can inspect why the judgment was made.
6. **Risk layer**: Risks and uncertainty prevent overclaiming.
7. **Reference layer**: Every cited source appears in the reference table.
8. **Humanizer layer**: Humanizer Editor Agent removes AI-like scaffolding and stiff phrasing while preserving citations and caveats.

If the claim graph is weak, the report must say evidence is insufficient instead of inventing a confident conclusion.

## Pressure Scenarios

Use these scenarios to validate the skill:

1. **Vague marketing prompt**: "帮我想想百度地图暑期怎么做增长" should trigger `marketing-ideas` before framework routing.
2. **Competitor monitoring prompt**: "高德最近上了什么新功能，给市场组一个方案" should route to competitor/JTBD/3C, not generic 4P only.
3. **Single-number prompt**: "英伟达最新市值是多少" should use `yfinance-data` or `funda-data` and skip Step 1-3 report flow.
4. **Investment plus brand prompt**: "小米汽车品牌力对股价有什么影响" should detect financial x marketing mixed framing and ask for investor/operating/new-business lens.
5. **Citation mismatch draft**: Any sentence with a source_id that does not support the claim must be rejected by Citation Auditor Agent.
