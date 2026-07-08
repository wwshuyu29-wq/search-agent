#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable workflow contracts for the multi-agent research pipeline.

This module keeps the node logic testable. Prompt documents can explain the
workflow, but code should also expose the contracts so CLI runs, tests, and
future orchestrators share the same mental model.
"""

from copy import deepcopy
from typing import Any, Dict, List


NODE_CONTRACTS: List[Dict[str, Any]] = [
    {
        "id": "intent_router",
        "name": "Intent Router Agent",
        "input_artifact": "Raw user query + project context + available skills",
        "llm_judgment": (
            "Read the whole request as a business decision: object, audience, "
            "time scope, output shape, evidence need, ambiguity, and conflicts "
            "with keyword signals."
        ),
        "tool_or_skill_use": [
            "intent_classifier.py as deterministic fallback",
            "framework_combinator.py after semantic routing",
            "marketing-ideas / marketing-plan / startup-analysis / yfinance-data / funda-data as Step 0 probes",
        ],
        "output_artifact": "IntentBrief + AuditCard",
        "quality_gate": "Stop before search until the user confirms or revises the audit card.",
        "hard_constraints": [
            "No web search before confirmation.",
            "Keyword hits cannot override the LLM semantic read.",
            "If a specialist skill is triggered, list why in the audit card.",
        ],
    },
    {
        "id": "search_planner",
        "name": "Search Planner Agent",
        "input_artifact": "Confirmed AuditCard",
        "llm_judgment": (
            "Translate each confirmed framework dimension into evidence needs, "
            "source classes, search language, and expected proof."
        ),
        "tool_or_skill_use": [
            "references/search-platforms.md",
            "framework keyword templates",
            "Chinese/English keyword expansion",
        ],
        "output_artifact": "SearchPlan",
        "quality_gate": "Every dimension has at least one task, one source layer, and expected evidence.",
        "hard_constraints": [
            "Do not search generic keywords without a dimension purpose.",
            "Separate official, media, RSS, UGC, finance data, and marketing data tasks.",
        ],
    },
    {
        "id": "official_source_hunter",
        "name": "Official Source Hunter",
        "input_artifact": "SearchPlan official-source tasks",
        "llm_judgment": "Judge whether a result is the primary source that can prove the claim.",
        "tool_or_skill_use": ["Firecrawl", "realtime-search Brave", "URL full-text fetch"],
        "output_artifact": "SourceList rows with OFF### ids",
        "quality_gate": "Official rows include publisher, date, URL, key facts, and fetched/full-text status.",
        "hard_constraints": [
            "Official announcements and filings outrank media summaries.",
            "Do not use a media article as official evidence when the original source is available.",
        ],
    },
    {
        "id": "media_source_hunter",
        "name": "Media Source Hunter",
        "input_artifact": "SearchPlan media/deep-analysis tasks",
        "llm_judgment": "Judge which media results add verified context, expert interpretation, or independent reporting.",
        "tool_or_skill_use": [
            "Firecrawl",
            "realtime-search Brave",
            "realtime-search Baidu",
            "URL full-text fetch",
        ],
        "output_artifact": "SourceList rows with MED### ids",
        "quality_gate": "Media rows distinguish reported fact, expert interpretation, and opinion.",
        "hard_constraints": [
            "Do not let media framing outrank official evidence for primary facts.",
            "Paywalled or excerpt-only sources must be marked as summary evidence.",
        ],
    },
    {
        "id": "rss_news_hunter",
        "name": "RSS/News Hunter",
        "input_artifact": "SearchPlan news/RSS tasks",
        "llm_judgment": "Use RSS as a recency and signal layer, then semantically filter candidates.",
        "tool_or_skill_use": [
            "finance-rss-reader",
            "news-aggregator-skill",
            "Firecrawl full-text fetch for high-relevance items",
        ],
        "output_artifact": "SourceList rows with RSS### / NEWS### ids",
        "quality_gate": "RSS candidates explain relevance score and confidence; high-impact facts need stronger sources.",
        "hard_constraints": [
            "relevance_score >= 0.6 is a full-text fetch gate, not a truth score.",
            "RSS alone cannot prove official financial results, regulation, or exact launch facts.",
        ],
    },
    {
        "id": "ugc_social_hunter",
        "name": "UGC/Social Hunter",
        "input_artifact": "SearchPlan UGC/social tasks",
        "llm_judgment": "Separate user sentiment, complaints, adoption signals, and anecdotal noise.",
        "tool_or_skill_use": [
            "agent-reach",
            "Bilibili / social search where available",
            "opencli-reader / social readers for finance communities when applicable",
        ],
        "output_artifact": "SourceList rows with UGC### ids",
        "quality_gate": "UGC rows are labeled low confidence unless independently verified.",
        "hard_constraints": [
            "Do not generalize UGC anecdotes into market facts.",
            "Do not expose private personal identifiers.",
        ],
    },
    {
        "id": "finance_data_hunter",
        "name": "Finance Data Hunter",
        "input_artifact": "SearchPlan finance-data tasks",
        "llm_judgment": "Decide which structured finance data can answer the financial part of the question.",
        "tool_or_skill_use": [
            "yfinance-data",
            "funda-data",
            "tradingview-reader",
            "finance-sentiment",
        ],
        "output_artifact": "SourceList rows with FIN### ids",
        "quality_gate": "Every numeric row has period, currency, metric definition, and source.",
        "hard_constraints": [
            "Single-number queries short-circuit the full report unless interpretation is requested.",
            "Market sentiment is not company performance evidence by itself.",
        ],
    },
    {
        "id": "marketing_intelligence_hunter",
        "name": "Marketing Intelligence Hunter",
        "input_artifact": "SearchPlan marketing/source-discovery tasks",
        "llm_judgment": "Decide which market, customer, competitor, channel, or funnel evidence is needed.",
        "tool_or_skill_use": [
            "competitor-profiling",
            "customer-research",
            "directory-submissions",
            "public-relations",
            "analytics",
        ],
        "output_artifact": "SourceList rows with MKT### ids",
        "quality_gate": "Marketing rows identify segment, channel, funnel stage, or behavior signal.",
        "hard_constraints": [
            "Do not convert generic marketing advice into a finding.",
            "Recommendations must tie to audience, channel, funnel stage, or metric.",
        ],
    },
    {
        "id": "source_qa",
        "name": "Source QA Agent",
        "input_artifact": "Raw SourceList",
        "llm_judgment": "Challenge source strength, conflicts, missing evidence, freshness, and source independence.",
        "tool_or_skill_use": [
            "URL normalization",
            "duplicate checks",
            "date parsing",
            "numeric comparison",
        ],
        "output_artifact": "SourceQANotes + CleanSourceList",
        "quality_gate": "High-impact conflicts are resolved, downgraded, or paused for user choice.",
        "hard_constraints": [
            "Do not analyze from stale or duplicate sources without marking the limitation.",
            "Paywalled summaries must be labeled as summaries.",
        ],
    },
    {
        "id": "framework_analyst",
        "name": "Framework Analyst Agent",
        "input_artifact": "CleanSourceList + confirmed framework dimensions",
        "llm_judgment": "Turn evidence into dimension-level facts, calculations, assumptions, and judgments.",
        "tool_or_skill_use": [
            "framework definitions",
            "finance specialist outputs",
            "marketing specialist outputs",
        ],
        "output_artifact": "ClaimGraph",
        "quality_gate": "Every material claim has source_ids and claim_type.",
        "hard_constraints": [
            "Weak evidence must be written as evidence-limited and low confidence.",
            "Do not mix fact, calculation, assumption, and judgment in one unlabeled claim.",
        ],
    },
    {
        "id": "finance_specialist",
        "name": "Financial Specialist Agent",
        "input_artifact": "CleanSourceList + finance questions from ClaimGraph",
        "llm_judgment": "Interpret financial metrics, sustainability, valuation, and risk in the user's decision context.",
        "tool_or_skill_use": [
            "yfinance-data",
            "funda-data",
            "earnings-preview",
            "earnings-recap",
            "estimate-analysis",
            "company-valuation",
            "stock-liquidity",
            "stock-correlation",
        ],
        "output_artifact": "FinanceClaims appended to ClaimGraph",
        "quality_gate": "All numbers carry period, currency, YoY/QoQ or definition, and source_id.",
        "hard_constraints": [
            "Separate research judgment from investment advice.",
            "No valuation conclusion without risk and assumption framing.",
        ],
    },
    {
        "id": "marketing_specialist",
        "name": "Marketing Specialist Agent",
        "input_artifact": "CleanSourceList + marketing/growth questions from ClaimGraph",
        "llm_judgment": "Interpret positioning, customer pain, channel leverage, funnel stage, and actionability.",
        "tool_or_skill_use": [
            "marketing-ideas",
            "marketing-plan",
            "product-marketing",
            "customer-research",
            "pricing",
            "ads",
            "copywriting",
            "analytics",
            "ab-testing",
            "competitor-profiling",
        ],
        "output_artifact": "MarketingClaims appended to ClaimGraph",
        "quality_gate": "Recommendations map to segment, channel, funnel stage, metric, and evidence.",
        "hard_constraints": [
            "No empty advice such as '加强宣传' without a mechanism.",
            "Do not force STP/4P/AARRR when the user's decision needs a competitor memo.",
        ],
    },
    {
        "id": "citation_auditor",
        "name": "Citation Auditor Agent",
        "input_artifact": "ClaimGraph + CleanSourceList",
        "llm_judgment": "Read each claim against cited sources and judge whether support is real, partial, or absent.",
        "tool_or_skill_use": ["source_id existence checks", "reference table checks", "claim-source comparison"],
        "output_artifact": "CitationAudit",
        "quality_gate": "Unsupported claims are removed, rewritten, or downgraded before report writing.",
        "hard_constraints": [
            "No citation, no factual claim.",
            "A source that mentions a topic does not automatically support the sentence.",
        ],
    },
    {
        "id": "report_writer",
        "name": "Report Writer Agent",
        "input_artifact": "CitationAudit + audited ClaimGraph + CleanSourceList",
        "llm_judgment": "Choose a reader-appropriate report family and compress claims into a useful decision document.",
        "tool_or_skill_use": [
            "report family selector",
            "reference table renderer",
            "optional generative-ui for finance/visual analysis",
        ],
        "output_artifact": "ReportDraft",
        "quality_gate": "The draft answers the user decision, preserves citations, and states uncertainty.",
        "hard_constraints": [
            "Do not force a visible rule-of-three or one-size-fits-all pyramid template.",
            "The conclusion-first logic must be supported by the audited claim graph.",
        ],
    },
    {
        "id": "humanizer_editor",
        "name": "Humanizer Editor Agent",
        "input_artifact": "ReportDraft + CleanSourceList + reader profile",
        "llm_judgment": "Remove AI-like phrasing while preserving evidence, numbers, citations, and risk boundaries.",
        "tool_or_skill_use": ["humanizer", "humanizer-zh", "copy-editing"],
        "output_artifact": "FinalReport",
        "quality_gate": "Final text sounds like a professional internal research note, not a prompt template.",
        "hard_constraints": [
            "Do not change facts, numbers, citations, or confidence levels.",
            "Do not add personality or unsupported certainty.",
        ],
    },
]


ARTIFACT_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "IntentBrief": {
        "producer_nodes": ["intent_router"],
        "consumer_nodes": ["intent_router", "search_planner", "report_writer"],
        "required_fields": [
            "research_object",
            "user_decision",
            "audience",
            "time_scope",
            "output_shape",
            "evidence_need",
            "ambiguity",
            "semantic_signals",
            "classifier_check",
            "preflight_skills",
        ],
        "quality_rules": [
            "The business decision is explicit.",
            "Semantic signals explain why the route was chosen.",
            "Keyword classifier conflicts are recorded, not hidden.",
        ],
    },
    "AuditCard": {
        "producer_nodes": ["intent_router"],
        "consumer_nodes": ["search_planner"],
        "required_fields": [
            "topic",
            "purpose",
            "llm_semantic_read",
            "recommended_frameworks",
            "dimensions",
            "keyword_families_zh",
            "keyword_families_en",
            "source_scope",
            "planned_expert_skills",
            "open_assumptions",
        ],
        "quality_rules": [
            "Search cannot start until this artifact is confirmed.",
            "Dimensions are written as concrete questions, not labels only.",
        ],
    },
    "SearchPlan": {
        "producer_nodes": ["search_planner"],
        "consumer_nodes": [
            "official_source_hunter",
            "media_source_hunter",
            "rss_news_hunter",
            "ugc_social_hunter",
            "finance_data_hunter",
            "marketing_intelligence_hunter",
        ],
        "required_fields": [
            "frameworks",
            "tasks",
            "task_id",
            "dimension",
            "query_zh",
            "query_en",
            "source_layers",
            "expected_evidence",
            "source_id_prefix",
        ],
        "quality_rules": [
            "Every framework dimension has a task.",
            "Every task declares what evidence would prove or weaken the claim.",
        ],
    },
    "SourceList": {
        "producer_nodes": [
            "official_source_hunter",
            "media_source_hunter",
            "rss_news_hunter",
            "ugc_social_hunter",
            "finance_data_hunter",
            "marketing_intelligence_hunter",
        ],
        "consumer_nodes": ["source_qa"],
        "required_fields": [
            "source_id",
            "title",
            "publisher",
            "source_type",
            "publish_date",
            "url",
            "confidence",
            "key_facts",
            "full_text_fetched",
            "collected_by",
            "confidence_rationale",
        ],
        "quality_rules": [
            "source_id prefix matches source class.",
            "Key facts are extracted from the source, not inferred by the hunter.",
            "Confidence includes rationale, not only high/medium/low.",
        ],
    },
    "SourceQANotes": {
        "producer_nodes": ["source_qa"],
        "consumer_nodes": ["framework_analyst", "finance_specialist", "marketing_specialist"],
        "required_fields": [
            "deduped_count",
            "removed_duplicates",
            "stale_sources",
            "paywalled_summaries",
            "number_conflicts",
            "missing_evidence",
            "approved_source_ids",
        ],
        "quality_rules": [
            "High-impact conflicts are explicit.",
            "Missing source classes are recorded before analysis begins.",
        ],
    },
    "CleanSourceList": {
        "producer_nodes": ["source_qa"],
        "consumer_nodes": ["framework_analyst", "finance_specialist", "marketing_specialist", "citation_auditor"],
        "required_fields": [
            "sources",
            "approved_source_ids",
            "excluded_source_ids",
            "source_quality_notes",
        ],
        "quality_rules": [
            "Only approved sources can support material claims.",
            "Excluded sources keep a reason for auditability.",
        ],
    },
    "ClaimGraph": {
        "producer_nodes": ["framework_analyst", "finance_specialist", "marketing_specialist"],
        "consumer_nodes": ["citation_auditor", "report_writer"],
        "required_fields": [
            "claim_id",
            "dimension",
            "claim_type",
            "text",
            "source_ids",
            "confidence",
            "reasoning_basis",
        ],
        "quality_rules": [
            "claim_type is one of fact/calculation/assumption/judgment.",
            "Factual and numeric claims carry source_ids.",
            "Judgment claims explain the reasoning basis.",
        ],
    },
    "CitationAudit": {
        "producer_nodes": ["citation_auditor"],
        "consumer_nodes": ["framework_analyst", "report_writer"],
        "required_fields": [
            "status",
            "issues",
            "required_rewrites",
            "approved_claim_ids",
            "blocked_claim_ids",
        ],
        "quality_rules": [
            "status is pass only when every material claim is supported.",
            "Unsupported claims are blocked or downgraded before ReportDraft.",
        ],
    },
    "ReportDraft": {
        "producer_nodes": ["report_writer"],
        "consumer_nodes": ["humanizer_editor"],
        "required_fields": [
            "markdown",
            "report_family",
            "core_judgment",
            "supporting_reasons",
            "risk_section",
            "reference_table",
        ],
        "quality_rules": [
            "The selected report family matches the audience and decision.",
            "Every material claim keeps a citation.",
        ],
    },
    "FinalReport": {
        "producer_nodes": ["humanizer_editor"],
        "consumer_nodes": ["user"],
        "required_fields": [
            "markdown",
            "report_family",
            "source_count",
            "generated_at",
            "humanizer_notes",
        ],
        "quality_rules": [
            "Humanizer changes style only, not facts or citations.",
            "The final report keeps references and uncertainty labels.",
        ],
    },
}


ORCHESTRATION_PLAN: List[Dict[str, Any]] = [
    {
        "id": "step0_intent_and_audit",
        "step": "Step 0",
        "nodes": ["intent_router"],
        "input_artifacts": ["RawUserQuery"],
        "output_artifacts": ["IntentBrief", "AuditCard"],
        "parallel": False,
        "gate": "audit_card_confirmed",
    },
    {
        "id": "step1_search_planning",
        "step": "Step 1",
        "nodes": ["search_planner"],
        "input_artifacts": ["AuditCard"],
        "output_artifacts": ["SearchPlan"],
        "parallel": False,
        "gate": "search_plan_complete",
    },
    {
        "id": "step1_parallel_source_hunting",
        "step": "Step 1",
        "nodes": [
            "official_source_hunter",
            "media_source_hunter",
            "rss_news_hunter",
            "ugc_social_hunter",
            "finance_data_hunter",
            "marketing_intelligence_hunter",
        ],
        "input_artifacts": ["SearchPlan"],
        "output_artifacts": ["SourceList"],
        "parallel": True,
        "gate": "source_list_complete",
    },
    {
        "id": "step1_source_qa",
        "step": "Step 1",
        "nodes": ["source_qa"],
        "input_artifacts": ["SourceList"],
        "output_artifacts": ["SourceQANotes", "CleanSourceList"],
        "parallel": False,
        "gate": "source_qa_passed_or_user_resolved_conflict",
    },
    {
        "id": "step2_analysis_and_specialists",
        "step": "Step 2",
        "nodes": ["framework_analyst", "finance_specialist", "marketing_specialist"],
        "input_artifacts": ["CleanSourceList", "SourceQANotes", "AuditCard"],
        "output_artifacts": ["ClaimGraph"],
        "parallel": True,
        "gate": "claim_graph_complete",
    },
    {
        "id": "step2_citation_audit",
        "step": "Step 2",
        "nodes": ["citation_auditor"],
        "input_artifacts": ["ClaimGraph", "CleanSourceList"],
        "output_artifacts": ["CitationAudit"],
        "parallel": False,
        "gate": "citation_audit_passed",
    },
    {
        "id": "step3_report_draft",
        "step": "Step 3",
        "nodes": ["report_writer"],
        "input_artifacts": ["CitationAudit", "ClaimGraph", "CleanSourceList", "IntentBrief"],
        "output_artifacts": ["ReportDraft"],
        "parallel": False,
        "gate": "report_draft_preserves_citations",
    },
    {
        "id": "step3_humanizer_final",
        "step": "Step 3",
        "nodes": ["humanizer_editor"],
        "input_artifacts": ["ReportDraft", "CleanSourceList"],
        "output_artifacts": ["FinalReport"],
        "parallel": False,
        "gate": "final_report_style_only_changes",
    },
]


SKILL_CHAINS: Dict[str, Dict[str, Any]] = {
    "finance": {
        "step0": ["yfinance-data", "funda-data", "startup-analysis"],
        "step1": ["yfinance-data", "funda-data", "tradingview-reader", "finance-sentiment"],
        "step2": [
            "earnings-preview",
            "earnings-recap",
            "estimate-analysis",
            "company-valuation",
            "stock-liquidity",
            "stock-correlation",
            "options-payoff",
            "etf-premium",
        ],
        "step3": ["generative-ui", "options-payoff"],
        "logic": [
            "LLM frames the finance question",
            "finance data skill retrieves structured data",
            "LLM interprets period/currency/metric definition",
            "ClaimGraph records source-backed financial claims",
        ],
        "hard_constraints": [
            "No investment-style conclusion without assumptions, risks, and evidence limits.",
            "Every number needs period, currency, metric definition, and source_id.",
        ],
    },
    "marketing": {
        "step0": ["marketing-ideas", "marketing-plan"],
        "step1": ["competitor-profiling", "customer-research", "directory-submissions", "public-relations"],
        "step2": [
            "product-marketing",
            "customer-research",
            "pricing",
            "ads",
            "ad-creative",
            "copywriting",
            "copy-editing",
            "seo-audit",
            "analytics",
            "ab-testing",
            "competitor-profiling",
        ],
        "step3": ["marketing-plan", "launch", "emails", "content-strategy", "seo-audit", "pricing"],
        "logic": [
            "LLM clarifies growth, positioning, funnel, or campaign decision",
            "marketing skill supplies domain method or evidence structure",
            "LLM maps findings to segment/channel/funnel/metric",
            "ClaimGraph records actionable marketing claims",
        ],
        "hard_constraints": [
            "No generic marketing action without target segment, channel, mechanism, and metric.",
            "Marketing-plan is not the default for every question containing '方案'.",
        ],
    },
    "finance_marketing_mixed": {
        "step0": ["marketing-ideas", "marketing-plan", "yfinance-data", "funda-data"],
        "step1": ["finance-sentiment", "customer-research", "competitor-profiling", "funda-data"],
        "step2": ["company-valuation", "estimate-analysis", "analytics", "product-marketing"],
        "step3": ["humanizer-zh", "copy-editing"],
        "logic": [
            "marketing signal",
            "user behavior",
            "unit economics",
            "financial metric",
            "valuation or risk implication",
        ],
        "hard_constraints": [
            "no direct jump from buzz to stock price without a causal bridge and evidence",
            "Separate brand perception, operating metric, and market-pricing evidence.",
        ],
    },
}


RSS_RELEVANCE_CONTRACT = {
    "candidate_threshold": 0.4,
    "full_text_threshold": 0.6,
    "meaning": "A deterministic lexical relevance gate, not truth, credibility, or final usefulness.",
    "formula": (
        "score = title base/title extra + summary base/summary extra + "
        "unique keyword coverage; uses title_hits, summary_hits, unique_hits."
    ),
    "next_llm_gate": (
        "LLM Source Hunter must semantically review kept RSS items, judge source confidence, "
        "and decide whether stronger official evidence is required."
    ),
    "limitations": [
        "Exact substring matching, not semantic matching.",
        "Synonyms are missed unless the Search Planner expands keywords.",
        "False positives remain possible and must be filtered by Source Hunter/Source QA.",
    ],
}


REPORT_FAMILIES: List[Dict[str, Any]] = [
    {
        "id": "executive_decision_memo",
        "name": "Executive Decision Memo",
        "use_when": ["market team", "business action", "competitor response", "strategy recommendation"],
        "shape": "lead with decision answer, then evidence-backed actions, risks, and next checks",
    },
    {
        "id": "deep_research_report",
        "name": "Deep Research Report",
        "use_when": ["industry study", "complex multi-source analysis", "background-heavy question"],
        "shape": "short answer first, then framework sections, evidence tables, risks, references",
    },
    {
        "id": "competitive_battlecard",
        "name": "Competitive Battlecard",
        "use_when": ["competitor comparison", "sales/market response", "product positioning"],
        "shape": "comparison table, key gaps, response options, proof points",
    },
    {
        "id": "finance_investment_note",
        "name": "Finance / Investment Note",
        "use_when": ["investment judgment", "valuation", "earnings", "financial risk"],
        "shape": "thesis, key numbers, drivers, valuation/risk, source table",
    },
    {
        "id": "growth_gtm_plan",
        "name": "Growth / GTM Plan",
        "use_when": ["growth plan", "launch plan", "campaign", "funnel optimization"],
        "shape": "objective, audience, levers, experiments, metrics, risks",
    },
    {
        "id": "evidence_brief",
        "name": "Evidence Brief",
        "use_when": ["single fact", "single financial number", "quick verification"],
        "shape": "answer, source, timestamp, caveat; no full report unless requested",
    },
]


CODEX_EXECUTION_MODEL: Dict[str, Any] = {
    "primary_runtime": "Codex skill runtime",
    "llm_invocation": (
        "The LLM is the current Codex session after the search-agent skill is triggered. "
        "Each node is executed by rendering its node prompt, reading/writing artifacts, "
        "and using the available Codex tools or installed skills."
    ),
    "requires_openai_api_key_for_llm": False,
    "api_key_boundary": (
        "OpenAI API keys are not required for node LLM calls inside Codex. External tool "
        "keys such as FIRECRAWL_API_KEY may still be required for retrieval."
    ),
    "node_prompt_source": "build_agent_prompt(node_id)",
    "artifact_contract_source": "get_artifact_contracts()",
    "gate_checker": "WorkflowOrchestrator.validate_artifact(...)",
    "parallelization": {
        "preferred": "Use Codex multi-agent tools when available for independent Source Hunter nodes.",
        "fallback": "Use sequential same-session execution with the same node prompts and artifact gates.",
        "parallel_nodes": [
            "official_source_hunter",
            "media_source_hunter",
            "rss_news_hunter",
            "ugc_social_hunter",
            "finance_data_hunter",
            "marketing_intelligence_hunter",
        ],
    },
    "team_install": {
        "skill_path": "~/.codex/skills/search-agent",
        "install_command": "bash install.sh",
        "post_install_checks": [
            "python scripts/search_agent_doctor.py",
            "python bin/search_agent.py \"高德地图最近三个月上了什么新功能\" --workflow-dry-run",
            "python bin/search_agent.py --workflow-playbook",
        ],
    },
    "codex_run_sequence": [
        "Codex loads SKILL.md when the user asks for search-agent research.",
        "Codex reads references/agent-nodes.md and references/node-playbook.md for node contracts.",
        "Intent Router Agent produces AuditCard and pauses for confirmation.",
        "After confirmation, Codex runs Search Planner Agent and Source Hunter nodes.",
        "Source QA validates evidence before analysis.",
        "Framework and specialist agents produce ClaimGraph.",
        "Citation Auditor blocks unsupported claims.",
        "Report Writer drafts the selected report family.",
        "Humanizer Editor performs style-only cleanup and preserves citations.",
    ],
    "not_supported_as_default": [
        "Embedding hidden OpenAI API calls inside the skill for each node.",
        "Letting CLI keyword logic replace Codex LLM semantic judgment.",
        "Skipping artifact gates because a prompt sounds plausible.",
    ],
}


def get_node_contracts() -> List[Dict[str, Any]]:
    """Return the ordered agent-node contracts."""
    return deepcopy(NODE_CONTRACTS)


def get_artifact_contracts() -> Dict[str, Dict[str, Any]]:
    """Return artifact handoff contracts in workflow order."""
    return deepcopy(ARTIFACT_CONTRACTS)


def get_orchestration_plan() -> List[Dict[str, Any]]:
    """Return the high-level orchestration plan."""
    return deepcopy(ORCHESTRATION_PLAN)


def build_agent_prompt(node_id: str) -> str:
    """Render a concrete execution prompt for one sub-agent node."""
    node = _node_by_id(node_id)
    output_artifacts = _artifact_contracts_for_output(node["output_artifact"])
    lines = [
        f"# {node['name']}",
        "",
        "You are a specialist node in the search-agent multi-agent workflow.",
        "Follow this contract exactly and write your result as the declared output artifact.",
        "",
        "## Input Artifact",
        str(node["input_artifact"]),
        "",
        "## LLM Judgment",
        str(node["llm_judgment"]),
        "",
        "## Tool/Skill Use",
    ]
    for item in _as_list(node["tool_or_skill_use"]):
        lines.append(f"- {item}")

    lines.extend(["", "## Output Artifact", str(node["output_artifact"]), ""])

    if output_artifacts:
        lines.append("## Output Schema")
        for artifact_name, contract in output_artifacts.items():
            lines.append(f"### {artifact_name}")
            lines.append("Required fields:")
            for field in contract["required_fields"]:
                lines.append(f"- {field}")
            lines.append("Quality rules:")
            for rule in contract["quality_rules"]:
                lines.append(f"- {rule}")
            lines.append("")

    lines.extend(["## Quality Gate", str(node["quality_gate"]), "", "## Hard Constraints"])
    for item in _as_list(node["hard_constraints"]):
        lines.append(f"- {item}")

    return "\n".join(lines).rstrip() + "\n"


def get_node_playbook(node_id: str) -> Dict[str, Any]:
    """Return one node in the user-facing progression format."""
    node = _node_by_id(node_id)
    return {
        "node_id": node["id"],
        "node": node["name"],
        "input": node["input_artifact"],
        "llm_judgment": node["llm_judgment"],
        "skill_tool_calls": node["tool_or_skill_use"],
        "output_artifact": node["output_artifact"],
        "next_step_condition": node["quality_gate"],
        "hard_constraints": node["hard_constraints"],
    }


def get_workflow_playbook() -> List[Dict[str, Any]]:
    """Return all nodes in the user-facing progression format."""
    return [get_node_playbook(node["id"]) for node in NODE_CONTRACTS]


def render_workflow_playbook_markdown() -> str:
    """Render the full workflow as 输入 -> LLM判断 -> skill/tool -> artifact -> gate."""
    lines = [
        "# Multi-Agent Workflow Node Playbook",
        "",
        "每个子 agent 都按同一条链路推进：输入 -> LLM判断 -> skill/tool调用 -> 输出artifact -> 进入下一步条件。",
        "",
    ]
    for node in get_workflow_playbook():
        lines.extend(
            [
                f"## {node['node']}",
                "",
                f"**输入**：{node['input']}",
                "",
                f"**LLM判断**：{node['llm_judgment']}",
                "",
                f"**skill/tool调用**：{_format_inline_list(node['skill_tool_calls'])}",
                "",
                f"**输出artifact**：{node['output_artifact']}",
                "",
                f"**进入下一步条件**：{node['next_step_condition']}",
                "",
                f"**硬约束**：{_format_inline_list(node['hard_constraints'])}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def get_skill_chain(domain: str) -> Dict[str, Any]:
    """Return the skill chain for a domain."""
    if domain not in SKILL_CHAINS:
        raise KeyError(f"Unknown skill chain: {domain}")
    return deepcopy(SKILL_CHAINS[domain])


def get_rss_relevance_contract() -> Dict[str, Any]:
    """Return the RSS relevance score contract."""
    return deepcopy(RSS_RELEVANCE_CONTRACT)


def get_report_families() -> List[Dict[str, Any]]:
    """Return all supported report families."""
    return deepcopy(REPORT_FAMILIES)


def get_codex_execution_model() -> Dict[str, Any]:
    """Return the Codex-native LLM execution model."""
    return deepcopy(CODEX_EXECUTION_MODEL)


def render_codex_execution_markdown() -> str:
    """Render the Codex-native execution model for docs and CLI output."""
    model = get_codex_execution_model()
    lines = [
        "# Codex-Native Execution Model",
        "",
        "## LLM 调用方式",
        "",
        "在 Codex 中，节点 LLM 默认由当前 Codex 会话承担。search-agent skill 不在节点内部另行隐藏调用 OpenAI API；Codex 读取节点 prompt、执行判断、调用工具、写入 artifact。",
        "",
        "不需要为节点 LLM 另配 OpenAI API Key。需要配置的是外部检索工具的 key，例如 Firecrawl。",
        "",
        f"- Primary runtime: {model['primary_runtime']}",
        f"- Node prompt source: `{model['node_prompt_source']}`",
        f"- Artifact contract source: `{model['artifact_contract_source']}`",
        f"- Gate checker: `{model['gate_checker']}`",
        "",
        "## 并行策略",
        "",
        f"- Preferred: {model['parallelization']['preferred']}",
        f"- Fallback: {model['parallelization']['fallback']}",
        f"- Parallel source hunters: {', '.join(model['parallelization']['parallel_nodes'])}",
        "",
        "## 团队安装后检查",
        "",
        f"安装到 {model['team_install']['skill_path']} 后，建议依次运行：",
        "",
    ]
    for command in model["team_install"]["post_install_checks"]:
        lines.append(f"```bash\n{command}\n```")
        lines.append("")

    lines.extend(["## Codex 内执行顺序", ""])
    for idx, step in enumerate(model["codex_run_sequence"], 1):
        lines.append(f"{idx}. {step}")

    lines.extend(["", "## 默认不采用", ""])
    for item in model["not_supported_as_default"]:
        lines.append(f"- {item}")

    return "\n".join(lines).rstrip() + "\n"


def recommend_report_family(intent_brief: Dict[str, Any]) -> Dict[str, Any]:
    """Select a report family from semantic intent fields.

    This is a deterministic fallback. In Codex-native runs, the Report Writer
    Agent may override it when the audited claim graph suggests a better shape,
    but the override must be explained.
    """
    user_decision = str(intent_brief.get("user_decision", "")).lower()
    audience = str(intent_brief.get("audience", "")).lower()
    output_shape = str(intent_brief.get("output_shape", "")).lower()

    if any(term in user_decision for term in ["单一金融数字", "single"]) or "快查" in output_shape:
        return deepcopy(_report_family_by_id("evidence_brief"))

    if any(term in user_decision for term in ["投资", "估值", "financial", "finance"]):
        return deepcopy(_report_family_by_id("finance_investment_note"))

    if any(term in user_decision for term in ["业务动作", "策略建议", "response", "action"]) or "市场" in audience:
        return deepcopy(_report_family_by_id("executive_decision_memo"))

    if any(term in output_shape for term in ["对比", "battlecard"]) or any(term in user_decision for term in ["竞品", "竞争"]):
        return deepcopy(_report_family_by_id("competitive_battlecard"))

    if any(term in user_decision for term in ["增长", "营销", "gtm", "launch"]):
        return deepcopy(_report_family_by_id("growth_gtm_plan"))

    return deepcopy(_report_family_by_id("deep_research_report"))


def summarize_node_chain(max_nodes: int = 0) -> List[str]:
    """Return concise user-facing node summaries for CLI Step 0 output."""
    summaries = []
    nodes = NODE_CONTRACTS[:max_nodes] if max_nodes and max_nodes > 0 else NODE_CONTRACTS
    for node in nodes:
        skills = node["tool_or_skill_use"]
        skill_text = skills[0] if isinstance(skills, list) else str(skills)
        summaries.append(
            f"{node['name']}: LLM判断={node['llm_judgment']} | skill/tool={skill_text} | 产物={node['output_artifact']}"
        )
    return summaries


def _node_by_id(node_id: str) -> Dict[str, Any]:
    for node in NODE_CONTRACTS:
        if node["id"] == node_id:
            return deepcopy(node)
    raise KeyError(f"Unknown node: {node_id}")


def _artifact_contracts_for_output(output_artifact: str) -> Dict[str, Dict[str, Any]]:
    matched = {}
    for artifact_name, contract in ARTIFACT_CONTRACTS.items():
        if artifact_name in output_artifact:
            matched[artifact_name] = deepcopy(contract)
    return matched


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else [value]


def _format_inline_list(value: Any) -> str:
    return "；".join(str(item) for item in _as_list(value))


def _report_family_by_id(report_id: str) -> Dict[str, Any]:
    for family in REPORT_FAMILIES:
        if family["id"] == report_id:
            return family
    raise KeyError(f"Unknown report family: {report_id}")
