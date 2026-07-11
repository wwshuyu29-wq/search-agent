#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable workflow contracts for the multi-agent research pipeline.

This module keeps the node logic testable. Prompt documents can explain the
workflow, but code should also expose the contracts so CLI runs, tests, and
future orchestrators share the same mental model.
"""

from copy import deepcopy
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


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
        "output_artifact": "SourceListFragment rows with OFF### ids",
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
        "output_artifact": "SourceListFragment rows with MED### ids",
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
        "output_artifact": "SourceListFragment rows with RSS### / NEWS### ids",
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
        "output_artifact": "SourceListFragment rows with UGC### ids",
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
        "output_artifact": "SourceListFragment rows with FIN### ids",
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
        "output_artifact": "SourceListFragment rows with MKT### ids",
        "quality_gate": "Marketing rows identify segment, channel, funnel stage, or behavior signal.",
        "hard_constraints": [
            "Do not convert generic marketing advice into a finding.",
            "Recommendations must tie to audience, channel, funnel stage, or metric.",
        ],
    },
    {
        "id": "source_list_merger",
        "name": "SourceList Merger",
        "input_artifact": "SourceListFragment rows from all Source Hunter nodes",
        "llm_judgment": (
            "Do not search or analyze; deterministically merge hunter fragments, "
            "dedupe canonical URLs, preserve channel provenance, and keep original-source priority."
        ),
        "tool_or_skill_use": [
            "URL canonicalizer",
            "schema validator",
            "content hash / duplicate checks",
        ],
        "output_artifact": "RawSourceList + MergerLog",
        "quality_gate": "source_id values are unique, duplicate URLs are merged, and MergerLog records what changed.",
        "hard_constraints": [
            "Do not create new facts while merging.",
            "Do not drop channel provenance when deduplicating.",
            "Official/original sources outrank reposts and media summaries.",
        ],
    },
    {
        "id": "source_qa",
        "name": "Source QA Agent",
        "input_artifact": "RawSourceList + SearchPlan",
        "llm_judgment": "Challenge source strength, conflicts, missing evidence, freshness, and source independence.",
        "tool_or_skill_use": [
            "URL normalization",
            "duplicate checks",
            "date parsing",
            "numeric comparison",
        ],
        "output_artifact": "SourceQANotes + ConflictRegister + GapList + CleanSourceList",
        "quality_gate": "High-impact conflicts are resolved, downgraded, or paused for user choice.",
        "hard_constraints": [
            "Do not analyze from stale or duplicate sources without marking the limitation.",
            "Paywalled summaries must be labeled as summaries.",
        ],
    },
    {
        "id": "gap_filler",
        "name": "Gap Filler / Conflict Refetch Agent",
        "input_artifact": "GapList + ConflictRegister",
        "llm_judgment": (
            "Only address gaps or conflicts explicitly raised by Source QA; "
            "find original sources, resolve numeric口径, or mark unresolved conflict."
        ),
        "tool_or_skill_use": [
            "Firecrawl",
            "realtime-search Brave",
            "URL full-text fetch",
            "official / regulatory / IR search",
            "finance skill when the conflict is financial",
        ],
        "output_artifact": "SupplementalSourceList + RefetchNotes",
        "quality_gate": "Resolved gaps are tied back to gap_id/conflict_id; unresolved items remain paused for user choice.",
        "hard_constraints": [
            "Do not expand beyond Source QA's listed gaps or conflicts.",
            "Do not introduce new research directions without user confirmation.",
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
        "input_artifact": "ClaimGraph + CleanSourceList + SpecialistNotes",
        "llm_judgment": "Read each claim against cited sources and judge whether support is real, partial, or absent.",
        "tool_or_skill_use": ["source_id existence checks", "reference table checks", "claim-source comparison"],
        "output_artifact": "CitationAudit + ApprovedClaimGraph",
        "quality_gate": "Unsupported claims are removed, rewritten, or downgraded before report writing.",
        "hard_constraints": [
            "No citation, no factual claim.",
            "A source that mentions a topic does not automatically support the sentence.",
        ],
    },

    {
        "id": "outline_architect",
        "name": "Outline Architect Agent",
        "input_artifact": "ApprovedClaimGraph + confirmed reader/decision/output context",
        "llm_judgment": "Design three materially different outline logics, recommend one with reasons, and map every section to evidence claims and a word budget.",
        "tool_or_skill_use": ["brainstorming", "writing-plans", "content-strategy"],
        "output_artifact": "OutlinePlan",
        "quality_gate": "Exactly three distinct candidates are usable, evidence-backed, reader-fit, and explicit about tradeoffs.",
        "hard_constraints": [
            "Do not generate three cosmetic variants of the same outline.",
            "Recommend but never approve on the user's behalf.",
            "No candidate section may lack a purpose or evidence claim slot.",
        ],
    },
    {
        "id": "human_outline_gate",
        "name": "Human Outline Approval Gate",
        "input_artifact": "OutlinePlan",
        "llm_judgment": "Present three candidates, mark the recommendation and tradeoffs, then faithfully capture the user's selection, combination, or edits without approving for them.",
        "tool_or_skill_use": ["structured user choice capture"],
        "output_artifact": "ApprovedOutline",
        "quality_gate": "The user explicitly confirms one final outline structure.",
        "hard_constraints": [
            "Never infer approval from silence.",
            "Allow selecting the recommendation, another candidate, or a user-edited combination.",
            "Do not proceed to Report Writer until approved_by_user=true.",
        ],
    },
    {
        "id": "report_writer",
        "name": "Report Writer Agent",
        "input_artifact": "ApprovedOutline + ApprovedClaimGraph + confirmed reader/decision context",
        "llm_judgment": "Develop deep prose within the user-approved section sequence, purpose, evidence slots, and word budgets.",
        "tool_or_skill_use": ["writing-plans", "copywriting", "content-strategy"],
        "output_artifact": "ReportDraft",
        "quality_gate": "Every approved section is developed in order, evidence-linked, reader-fit, and uncertainty explicit.",
        "hard_constraints": [
            "Do not write before ApprovedOutline exists.",
            "Do not add, remove, rename, or reorder top-level sections without user re-approval.",
            "Do not introduce claims outside ApprovedClaimGraph.",
            "Reference appendix remains mandatory.",
        ],
    },
    {
        "id": "outline_compliance_auditor",
        "name": "Outline Compliance Auditor Agent",
        "input_artifact": "ApprovedOutline + ReportDraft",
        "llm_judgment": "Check section order, purpose completion, evidence-slot use, word-budget balance, and unauthorized structural drift.",
        "tool_or_skill_use": ["copy-editing", "verification-before-completion"],
        "output_artifact": "OutlineComplianceReview",
        "quality_gate": "All approved sections are present in order and no unapproved top-level section exists.",
        "hard_constraints": [
            "Block completion on structural drift.",
            "Do not rewrite the report; return actionable findings to Report Writer.",
        ],
    },
    {
        "id": "humanizer_editor",
        "name": "Humanizer Editor Agent",
        "input_artifact": "ReportDraft + ApprovedOutline + OutlineComplianceReview + ApprovedClaimGraph",
        "llm_judgment": "Remove AI-like phrasing while preserving the approved structure, evidence, numbers, citations, and risk boundaries.",
        "tool_or_skill_use": ["humanizer", "humanizer-zh", "copy-editing"],
        "output_artifact": "HumanizerChangeLog + FinalReport",
        "quality_gate": "Expression improves without structural or evidentiary drift.",
        "hard_constraints": [
            "Do not add, remove, rename, or reorder approved top-level sections.",
            "Do not change facts, numbers, citations, assumptions, or risk levels.",
        ],
    },
    {
        "id": "integrity_diff_checker",
        "name": "Integrity Diff Checker",
        "input_artifact": "ReportDraft + FinalReport + HumanizerChangeLog",
        "llm_judgment": (
            "Check whether the Humanizer changed facts, numbers, dates, source_ids, claim_ids, "
            "confidence labels, risk boundaries, or conclusion strength."
        ),
        "tool_or_skill_use": [
            "local diff",
            "regex extraction for numbers/dates/source_id/claim_id",
            "schema validator",
        ],
        "output_artifact": "IntegrityDiff",
        "quality_gate": "No factual, numeric, citation, confidence, or risk-boundary changes before final review.",
        "hard_constraints": [
            "If integrity fails, return to Humanizer; do not send to final review.",
            "Style edits are allowed; evidence changes are not.",
        ],
    },
]


NODE_BOUNDARIES: Dict[str, Dict[str, Any]] = {
    "intent_router": {
        "responsibility_boundary": "Only frames the user's business decision and proposed workflow route before any search.",
        "may_do": ["Extract decision context", "recommend frameworks", "list expert skills", "produce AuditCard"],
        "must_not_do": ["Search sources", "write findings", "skip user confirmation"],
        "handoff_to": "Search Planner after audit_card_confirmed.",
    },
    "search_planner": {
        "responsibility_boundary": "Only turns the confirmed AuditCard into source-specific search tasks.",
        "may_do": ["Create query families", "assign hunters", "define expected evidence", "set source_id prefixes"],
        "must_not_do": ["Fetch sources", "analyze evidence", "change confirmed framework without user input"],
        "handoff_to": "Parallel Source Hunter nodes.",
    },
    "official_source_hunter": {
        "responsibility_boundary": "Only collects primary/original sources for confirmed tasks.",
        "may_do": ["Search official sites", "fetch original pages", "normalize OFF### rows"],
        "must_not_do": ["Use media as official proof", "interpret strategy", "invent missing dates"],
        "handoff_to": "SourceList Merger.",
    },
    "media_source_hunter": {
        "responsibility_boundary": "Only collects secondary reporting and separates fact from framing.",
        "may_do": ["Search media", "fetch article text", "label fact/interpretation/opinion"],
        "must_not_do": ["Let media override official facts", "treat commentary as proof", "hide paywall limits"],
        "handoff_to": "SourceList Merger.",
    },
    "rss_news_hunter": {
        "responsibility_boundary": "Only collects timely RSS/news signals and relevance-gates them.",
        "may_do": ["Scan RSS", "score relevance", "route high-signal items for stronger verification"],
        "must_not_do": ["Treat relevance_score as truth", "prove exact launch facts from RSS alone", "skip stronger sources"],
        "handoff_to": "SourceList Merger.",
    },
    "ugc_social_hunter": {
        "responsibility_boundary": "Only collects public UGC/social signals as sentiment or adoption evidence.",
        "may_do": ["Search B站/social platforms", "record public URLs", "summarize sentiment patterns"],
        "must_not_do": ["Generalize anecdotes into market facts", "collect private identifiers", "treat UGC as official evidence"],
        "handoff_to": "SourceList Merger and Source QA for confidence downgrading.",
    },
    "finance_data_hunter": {
        "responsibility_boundary": "Only collects structured finance/data rows when the task truly needs them.",
        "may_do": ["Fetch yfinance snapshots", "route setup-aware finance adapters", "emit FIN### rows"],
        "must_not_do": ["Run finance tools for non-finance map marketing tasks", "give investment advice", "treat sentiment as performance"],
        "handoff_to": "SourceList Merger.",
    },
    "marketing_intelligence_hunter": {
        "responsibility_boundary": "Only routes marketing method skills and source-discovery hints; it is not market proof by itself.",
        "may_do": ["Select fine-grained marketing skills", "emit method-source rows", "identify source needs"],
        "must_not_do": ["Convert generic marketing advice into findings", "add unsupported recommendations", "replace external evidence"],
        "handoff_to": "SourceList Merger and Marketing Specialist.",
    },
    "source_list_merger": {
        "responsibility_boundary": "Only merges and dedupes source fragments without adding meaning.",
        "may_do": ["Canonicalize URLs", "merge duplicates", "preserve provenance", "write MergerLog"],
        "must_not_do": ["Create facts", "drop provenance", "rank claims"],
        "handoff_to": "Source QA.",
    },
    "source_qa": {
        "responsibility_boundary": "Only approves, downgrades, excludes, or flags sources before analysis.",
        "may_do": ["Check freshness", "detect conflicts", "produce GapList", "approve CleanSourceList"],
        "must_not_do": ["Write analysis", "resolve conflicts by guessing", "bury weak-source caveats"],
        "handoff_to": "Gap Filler when blocked, otherwise Framework/Specialist analysis.",
    },
    "gap_filler": {
        "responsibility_boundary": "Only fills Source QA-listed gaps or conflicts.",
        "may_do": ["Refetch official sources", "target exact conflicts", "write RefetchNotes"],
        "must_not_do": ["Expand scope", "start new research threads", "force unresolved conflicts through"],
        "handoff_to": "Source QA or Framework Analyst after gap/conflict closure.",
    },
    "framework_analyst": {
        "responsibility_boundary": "Only converts approved evidence into framework-structured claims.",
        "may_do": ["Label claim types", "group by dimension", "state reasoning basis"],
        "must_not_do": ["Use unapproved sources", "mix facts and judgments", "overclaim weak evidence"],
        "handoff_to": "Finance/Marketing Specialists and Citation Auditor.",
    },
    "finance_specialist": {
        "responsibility_boundary": "Only handles finance-specific interpretation when the confirmed task requires it.",
        "may_do": ["Add metric interpretation", "state assumptions", "patch ClaimGraph with sourced finance claims"],
        "must_not_do": ["Make trade recommendations", "omit period/currency/口径", "force finance into map marketing tasks"],
        "handoff_to": "Citation Auditor.",
    },
    "marketing_specialist": {
        "responsibility_boundary": "Only turns approved evidence into marketing, positioning, growth, and action logic.",
        "may_do": ["Map segment/channel/funnel/metric", "use marketing skills as methods", "patch ClaimGraph"],
        "must_not_do": ["Give generic advice", "invent user insights", "ignore evidence gaps"],
        "handoff_to": "Citation Auditor.",
    },
    "citation_auditor": {
        "responsibility_boundary": "Only checks claim-source support before report writing.",
        "may_do": ["Verify source_ids", "downgrade claims", "block unsupported statements"],
        "must_not_do": ["Add new claims", "rewrite strategy beyond support", "accept topic-only citations"],
        "handoff_to": "Outline Architect after CitationAudit passes.",
    },
    "outline_architect": {
        "responsibility_boundary": "Only designs three distinct evidence-backed outline candidates and recommends one.",
        "may_do": ["Design outline logic", "map claim slots", "allocate word budgets", "explain tradeoffs"],
        "must_not_do": ["Write report prose", "approve for the user", "offer cosmetic variants"],
        "handoff_to": "Human Outline Approval Gate.",
    },
    "human_outline_gate": {
        "responsibility_boundary": "Only captures the user's explicit outline selection, combination, or edits.",
        "may_do": ["Present candidates", "record edits", "create ApprovedOutline after explicit approval"],
        "must_not_do": ["Infer approval", "change the user's structure", "start report prose"],
        "handoff_to": "Report Writer after approved_by_user=true.",
    },
    "report_writer": {
        "responsibility_boundary": "Only develops prose inside the exact ApprovedOutline structure.",
        "may_do": ["Develop sections", "use approved claims", "render references", "state evidence gaps"],
        "must_not_do": ["Add uncited claims", "change top-level structure", "force conclusion-first logic"],
        "handoff_to": "Outline Compliance Auditor.",
    },
    "outline_compliance_auditor": {
        "responsibility_boundary": "Only checks ReportDraft against ApprovedOutline before Humanizer.",
        "may_do": ["Check section order", "check purposes", "check evidence slots", "block drift"],
        "must_not_do": ["Rewrite prose", "approve structural drift", "alter the outline"],
        "handoff_to": "Humanizer Editor after status=passed.",
    },
    "humanizer_editor": {
        "responsibility_boundary": "Only edits expression and removes AI-like phrasing.",
        "may_do": ["Tighten wording", "remove filler", "adapt tone to market team reader"],
        "must_not_do": ["Change facts", "change citations", "increase certainty", "delete caveats"],
        "handoff_to": "Integrity Diff Checker.",
    },
    "integrity_diff_checker": {
        "responsibility_boundary": "Only verifies the Humanizer preserved evidence-bearing content.",
        "may_do": ["Compare numbers/dates/source_ids", "flag changed risk labels", "block final review"],
        "must_not_do": ["Rewrite the report", "approve changed facts", "skip failed diff"],
        "handoff_to": "Final report review or back to Humanizer.",
    },
}


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
    "SourceListFragment": {
        "producer_nodes": [
            "official_source_hunter",
            "media_source_hunter",
            "rss_news_hunter",
            "ugc_social_hunter",
            "finance_data_hunter",
            "marketing_intelligence_hunter",
        ],
        "consumer_nodes": ["source_list_merger"],
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
            "Each fragment keeps the hunter prefix and provenance.",
            "Rows are evidence candidates only; no analysis conclusions are allowed.",
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
    "RawSourceList": {
        "producer_nodes": ["source_list_merger"],
        "consumer_nodes": ["source_qa"],
        "required_fields": [
            "sources",
            "source_count",
            "canonical_url",
            "merged_duplicate_count",
        ],
        "quality_rules": [
            "All source_id values are unique after merge.",
            "Canonical URL or normalized URL is present for dedupe audit.",
            "Channel provenance is retained for every kept source.",
        ],
    },
    "MergerLog": {
        "producer_nodes": ["source_list_merger"],
        "consumer_nodes": ["source_qa"],
        "required_fields": [
            "input_count",
            "output_count",
            "deduped_count",
            "merged_sources",
            "id_rewrites",
            "warnings",
        ],
        "quality_rules": [
            "Every dropped or merged source is traceable to a kept source.",
            "source_id rewrites are explicit.",
        ],
    },
    "SourceQANotes": {
        "producer_nodes": ["source_qa"],
        "consumer_nodes": ["gap_filler", "framework_analyst", "finance_specialist", "marketing_specialist"],
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
    "ConflictRegister": {
        "producer_nodes": ["source_qa", "gap_filler"],
        "consumer_nodes": ["gap_filler", "framework_analyst"],
        "required_fields": [
            "conflicts",
            "requires_user_decision",
            "recommended_resolution",
        ],
        "quality_rules": [
            "High-severity conflicts explain why they matter.",
            "User-facing options are explicit when a decision is needed.",
        ],
    },
    "GapList": {
        "producer_nodes": ["source_qa"],
        "consumer_nodes": ["gap_filler", "framework_analyst"],
        "required_fields": [
            "gaps",
            "requires_refetch",
            "blocking_gap_count",
        ],
        "quality_rules": [
            "Every gap maps to a SearchPlan task or framework dimension.",
            "Blocking gaps stop analysis until filled or accepted by the user.",
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
    "SupplementalSourceList": {
        "producer_nodes": ["gap_filler"],
        "consumer_nodes": ["source_list_merger", "source_qa"],
        "required_fields": [
            "sources",
            "resolved_gap_ids",
            "resolved_conflict_ids",
        ],
        "quality_rules": [
            "Supplemental sources only address Source QA gaps/conflicts.",
            "New sources must be re-merged and re-QA'd before analysis.",
        ],
    },
    "RefetchNotes": {
        "producer_nodes": ["gap_filler"],
        "consumer_nodes": ["source_qa"],
        "required_fields": [
            "attempted_gap_ids",
            "attempted_conflict_ids",
            "resolved_items",
            "unresolved_items",
        ],
        "quality_rules": [
            "Unresolved conflicts remain visible for user choice.",
            "No new research direction is introduced by refetch.",
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
    "SpecialistNotes": {
        "producer_nodes": ["finance_specialist", "marketing_specialist"],
        "consumer_nodes": ["citation_auditor", "report_writer"],
        "required_fields": [
            "specialist",
            "notes",
            "source_ids",
            "risk_boundaries",
        ],
        "quality_rules": [
            "Specialist notes distinguish fact, observation, inference, and recommendation.",
            "Finance/marketing patches keep source_ids and metric/segment context.",
        ],
    },
    "ClaimGraphPatch": {
        "producer_nodes": ["finance_specialist", "marketing_specialist"],
        "consumer_nodes": ["framework_analyst", "citation_auditor"],
        "required_fields": [
            "patch_id",
            "target_claim_ids",
            "new_claims",
            "source_ids",
            "patch_reason",
        ],
        "quality_rules": [
            "Patches cannot introduce unsupported claims.",
            "Patches preserve claim_type and confidence semantics.",
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
    "ApprovedClaimGraph": {
        "producer_nodes": ["citation_auditor"],
        "consumer_nodes": ["outline_architect", "report_writer"],
        "required_fields": ["approved_claim_ids", "claims"],
        "quality_rules": ["Only audit_status=passed claims are report-ready", "At least one explicit source_id per factual claim"],
    },
    "OutlinePlan": {
        "producer_nodes": ["outline_architect"],
        "consumer_nodes": ["human_outline_gate"],
        "required_fields": ["candidates", "recommended_outline_id", "recommendation_reason"],
        "quality_rules": ["Exactly three materially distinct candidates", "Each candidate declares reader, writing_logic, sections, evidence slots, and word budgets"],
    },
    "ApprovedOutline": {
        "producer_nodes": ["human_outline_gate"],
        "consumer_nodes": ["report_writer", "outline_compliance_auditor"],
        "required_fields": ["selected_outline_id", "approved_by_user", "report_family", "title", "target_reader", "writing_logic", "sections"],
        "quality_rules": ["approved_by_user must be true", "Section order and headings become immutable until re-approved", "Every section has purpose and required_claim_ids"],
    },
    "ReportDraft": {
        "producer_nodes": ["report_writer"],
        "consumer_nodes": ["outline_compliance_auditor", "humanizer_editor"],
        "required_fields": ["report_family", "approved_outline_id", "reader", "decision", "sections", "references"],
        "quality_rules": ["Reader-fit structure", "Top-level sections exactly inherit ApprovedOutline", "Every factual section maps back to ApprovedClaimGraph", "References remain clickable"],
    },
    "OutlineComplianceReview": {
        "producer_nodes": ["outline_compliance_auditor"],
        "consumer_nodes": ["report_writer", "humanizer_editor"],
        "required_fields": ["status", "missing_sections", "unexpected_sections", "order_matches", "purpose_gaps", "evidence_gaps"],
        "quality_rules": ["status=passed before Humanizer", "Structural drift blocks completion"],
    },
    "HumanizerChangeLog": {
        "producer_nodes": ["humanizer_editor"],
        "consumer_nodes": ["integrity_diff_checker"],
        "required_fields": [
            "changed_sections",
            "style_only",
            "unchanged_fact_confirmation",
        ],
        "quality_rules": [
            "Humanizer explicitly confirms facts, numbers, citations, and confidence were preserved.",
            "Any non-style change must be flagged before integrity check.",
        ],
    },
    "FinalReport": {
        "producer_nodes": ["humanizer_editor"],
        "consumer_nodes": ["integrity_diff_checker", "user"],
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
    "IntegrityDiff": {
        "producer_nodes": ["integrity_diff_checker"],
        "consumer_nodes": ["humanizer_editor", "user"],
        "required_fields": [
            "status",
            "changed_numbers",
            "changed_dates",
            "changed_source_ids",
            "changed_claim_ids",
            "changed_confidence",
            "risk_boundary_changes",
            "new_factual_sentences",
        ],
        "quality_rules": [
            "status is passed only when evidence-bearing content is unchanged.",
            "Failures return to Humanizer before final review.",
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
        "gate_type": "human",
        "halts_for_user": True,
        "user_prompt": "Review AuditCard; reply 确认 to continue or provide revisions.",
    },
    {
        "id": "step1_search_planning",
        "step": "Step 1",
        "nodes": ["search_planner"],
        "input_artifacts": ["AuditCard"],
        "output_artifacts": ["SearchPlan"],
        "parallel": False,
        "gate": "search_plan_complete",
        "gate_type": "automatic",
        "halts_for_user": False,
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
        "output_artifacts": ["SourceListFragment"],
        "parallel": True,
        "gate": "source_list_fragment_valid",
        "gate_type": "automatic",
        "halts_for_user": False,
    },
    {
        "id": "step1_source_merge",
        "step": "Step 1",
        "nodes": ["source_list_merger"],
        "input_artifacts": ["SourceListFragment"],
        "output_artifacts": ["RawSourceList", "MergerLog"],
        "parallel": False,
        "gate": "source_merge_complete",
        "gate_type": "automatic",
        "halts_for_user": False,
    },
    {
        "id": "step1_source_qa",
        "step": "Step 1",
        "nodes": ["source_qa"],
        "input_artifacts": ["RawSourceList", "MergerLog", "SearchPlan"],
        "output_artifacts": ["SourceQANotes", "ConflictRegister", "GapList", "CleanSourceList"],
        "parallel": False,
        "gate": "source_qa_passed_or_user_resolved_conflict",
        "gate_type": "conditional_human",
        "halts_for_user": "only_when_conflict_or_missing_key_source",
        "user_prompt": "Resolve numeric conflicts or key source gaps before analysis.",
    },
    {
        "id": "step1_gap_fill_or_pause",
        "step": "Step 1",
        "nodes": ["gap_filler"],
        "input_artifacts": ["ConflictRegister", "GapList"],
        "output_artifacts": ["SupplementalSourceList", "RefetchNotes"],
        "parallel": False,
        "gate": "gap_fill_complete_or_pause",
        "gate_type": "conditional_human",
        "halts_for_user": "only_when_refetch_cannot_resolve_blocking_gap",
        "user_prompt": "If gaps remain blocking after one refetch pass, ask user to choose scope or evidence standard.",
    },
    {
        "id": "step2_analysis_and_specialists",
        "step": "Step 2",
        "nodes": ["framework_analyst", "finance_specialist", "marketing_specialist"],
        "input_artifacts": ["CleanSourceList", "SourceQANotes", "ConflictRegister", "GapList", "AuditCard"],
        "output_artifacts": ["ClaimGraph", "SpecialistNotes", "ClaimGraphPatch"],
        "parallel": True,
        "gate": "claim_graph_complete",
        "gate_type": "automatic",
        "halts_for_user": False,
    },
    {
        "id": "step2_citation_audit",
        "step": "Step 2",
        "nodes": ["citation_auditor"],
        "input_artifacts": ["ClaimGraph", "ClaimGraphPatch", "SpecialistNotes", "CleanSourceList"],
        "output_artifacts": ["CitationAudit", "ApprovedClaimGraph"],
        "parallel": False,
        "gate": "citation_audit_passed",
        "gate_type": "automatic_hard_block",
        "halts_for_user": False,
    },
    {
        "id": "step3_outline_candidates",
        "step": "T4",
        "nodes": ["outline_architect"],
        "input_artifacts": ["ApprovedClaimGraph", "IntentBrief"],
        "output_artifacts": ["OutlinePlan"],
        "parallel": False,
        "gate": "three_outline_candidates_ready",
        "gate_type": "automatic",
        "halts_for_user": False,
    },
    {
        "id": "step3_outline_approval",
        "step": "T5",
        "nodes": ["human_outline_gate"],
        "input_artifacts": ["OutlinePlan"],
        "output_artifacts": ["ApprovedOutline"],
        "parallel": False,
        "gate": "outline_approved_by_user",
        "gate_type": "human_hard_block",
        "halts_for_user": True,
    },
    {
        "id": "step3_report_draft",
        "step": "T6",
        "nodes": ["report_writer"],
        "input_artifacts": ["ApprovedOutline", "ApprovedClaimGraph", "IntentBrief"],
        "output_artifacts": ["ReportDraft"],
        "parallel": False,
        "gate": "report_draft_complete",
        "gate_type": "automatic",
        "halts_for_user": False,
    },
    {
        "id": "step3_outline_compliance",
        "step": "T7",
        "nodes": ["outline_compliance_auditor"],
        "input_artifacts": ["ApprovedOutline", "ReportDraft"],
        "output_artifacts": ["OutlineComplianceReview"],
        "parallel": False,
        "gate": "outline_compliance_passed",
        "gate_type": "automatic_hard_block",
        "halts_for_user": False,
    },
    {
        "id": "step3_humanizer",
        "step": "T7",
        "nodes": ["humanizer_editor"],
        "input_artifacts": ["ReportDraft", "ApprovedOutline", "OutlineComplianceReview", "ApprovedClaimGraph"],
        "output_artifacts": ["HumanizerChangeLog", "FinalReport"],
        "parallel": False,
        "gate": "humanizer_integrity_passed",
        "gate_type": "automatic_hard_block",
        "halts_for_user": False,
    },
    {
        "id": "step3_integrity_check",
        "step": "Step 3",
        "nodes": ["integrity_diff_checker"],
        "input_artifacts": ["ReportDraft", "FinalReport", "HumanizerChangeLog"],
        "output_artifacts": ["IntegrityDiff"],
        "parallel": False,
        "gate": "humanizer_integrity_passed",
        "gate_type": "automatic_then_human",
        "halts_for_user": True,
        "post_gate": "final_report_review",
        "user_prompt": "Review FinalReport only after IntegrityDiff passes; reply 通过 or provide revision notes.",
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
        "conditional_extensions": [
            "discord-reader",
            "hormuz-strait",
            "hyperliquid-reader",
            "linkedin-reader",
            "saas-valuation-compression",
            "sepa-strategy",
            "skill-creator",
            "telegram-reader",
            "twitter-reader",
            "yc-reader",
        ],
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
        "conditional_extensions": [
            "ai-seo",
            "aso",
            "churn-prevention",
            "co-marketing",
            "cold-email",
            "community-marketing",
            "competitors",
            "cro",
            "free-tools",
            "image",
            "lead-magnets",
            "marketing-psychology",
            "offers",
            "onboarding",
            "paywalls",
            "popups",
            "programmatic-seo",
            "prospecting",
            "referrals",
            "revops",
            "sales-enablement",
            "signup",
            "site-architecture",
            "sms",
            "video",
        ],
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


PROCESS_SKILL_REFERENCES = {
    "superpowers": [
        "using-superpowers",
        "brainstorming",
        "test-driven-development",
        "verification-before-completion",
        "executing-plans",
        "writing-plans",
        "dispatching-parallel-agents",
        "subagent-driven-development",
        "systematic-debugging",
        "finishing-a-development-branch",
        "requesting-code-review",
        "receiving-code-review",
        "using-git-worktrees",
        "writing-skills",
    ],
    "writing": [
        "humanizer",
        "humanizer-zh",
        "copy-editing",
        "copywriting",
        "content-strategy",
        "build-report",
    ],
}


SKILL_ADAPTER_MATRIX: Dict[str, List[Dict[str, Any]]] = {
    "marketing": [
        {
            "skill": "marketing-plan",
            "nodes": ["intent_router", "marketing_intelligence_hunter", "marketing_specialist", "report_writer"],
            "trigger_terms": ["营销方案", "增长计划", "gtm", "go-to-market", "aarrr", "路线图", "90天"],
            "why_use": "把模糊的增长/营销问题拆成获客、激活、留存、收入、传播和资源排期。",
            "how_to_use": "先让 LLM 读取 skill 方法，抽取适合当前行业和团队阶段的计划骨架，再落到 SearchPlan 任务或 SpecialistNotes。",
            "output_artifact": "AuditCard.planned_expert_skills / MarketingIntelFragment / SpecialistNotes",
            "evidence_role": "method_reference",
            "use_well": "必须绑定目标人群、渠道、预算、周期和衡量指标；不能把通用建议写成事实结论。",
        },
        {
            "skill": "marketing-ideas",
            "nodes": ["intent_router", "marketing_intelligence_hunter", "marketing_specialist"],
            "trigger_terms": ["想法", "创意", "增长点", "拉新", "促活", "推广", "不知道怎么做"],
            "why_use": "在用户需求还发散时生成候选方向，帮助 Step 0 把问题变成可检索、可分析的框架。",
            "how_to_use": "用于 Step 0 前置探针或营销节点的方向池，筛出 2-3 个和证据最相关的方向。",
            "output_artifact": "AuditCard.dimensions / MarketingIntelFragment",
            "evidence_role": "method_reference",
            "use_well": "只保留能被后续数据验证的方向，并标注需要哪些来源证明。",
        },
        {
            "skill": "product-marketing",
            "nodes": ["intent_router", "marketing_specialist", "report_writer"],
            "trigger_terms": ["定位", "stp", "icp", "人群", "卖点", "messaging", "产品营销"],
            "why_use": "帮助地图/本地生活类竞品分析落到定位、人群、场景和主张，而不是泛泛评价功能。",
            "how_to_use": "把来源中的功能、用户评价、渠道信息整理成定位差异和 messaging 假设。",
            "output_artifact": "SpecialistNotes / ClaimGraphPatch",
            "evidence_role": "method_reference",
            "use_well": "每个定位判断都要回连用户证据、竞品动作或渠道素材。",
        },
        {
            "skill": "customer-research",
            "nodes": ["search_planner", "marketing_intelligence_hunter", "marketing_specialist"],
            "trigger_terms": ["用户", "客户", "痛点", "需求", "jtbd", "voc", "评价", "评论"],
            "why_use": "把用户反馈、UGC、评论和访谈类材料整理成需求、阻力和决策触发点。",
            "how_to_use": "指导 Search Planner 添加 UGC/评论/社媒来源，并在 SpecialistNotes 中做 JTBD/VOC 归纳。",
            "output_artifact": "SearchPlan.tasks / SpecialistNotes",
            "evidence_role": "method_reference",
            "use_well": "不能凭空造用户洞察；必须引用评论、调研、客服记录或公开讨论。",
        },
        {
            "skill": "competitor-profiling",
            "nodes": ["search_planner", "marketing_intelligence_hunter", "framework_analyst"],
            "trigger_terms": ["竞品", "竞争", "对手", "竞对", "competitive", "profile", "对比"],
            "why_use": "适配百度地图市场组最常见的竞品监测任务，补齐定位、渠道、价格、SEO、用户评价等维度。",
            "how_to_use": "用作竞品档案模板，驱动 Official/Media/UGC/Marketing Source Hunter 的查询维度。",
            "output_artifact": "SearchPlan.tasks / ClaimGraph",
            "evidence_role": "method_reference",
            "use_well": "竞品结论必须来自外部来源；skill 只规定该查哪些栏位。",
        },
        {
            "skill": "competitors",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["vs", "替代", "对比页", "battle card", "竞品页"],
            "why_use": "把竞品分析转成可执行的对比表达、battle card 或销售/市场话术。",
            "how_to_use": "在报告建议部分生成差异化表达框架，不用于新增事实。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "必须继承 Citation Auditor 通过的差异点，不能新编竞品弱点。",
        },
        {
            "skill": "pricing",
            "nodes": ["marketing_specialist", "finance_specialist"],
            "trigger_terms": ["定价", "价格", "套餐", "变现", "freemium", "付费"],
            "why_use": "当调研涉及商业模式、会员、广告或增值服务时，用来分析价格结构和价值指标。",
            "how_to_use": "结合竞品价格页、财报 ARPU/变现数据和用户阻力，形成价格/包装假设。",
            "output_artifact": "SpecialistNotes / ClaimGraphPatch",
            "evidence_role": "method_reference",
            "use_well": "价格建议必须标明用户段、价值指标和证据来源。",
        },
        {
            "skill": "analytics",
            "nodes": ["marketing_specialist", "source_qa"],
            "trigger_terms": ["指标", "埋点", "衡量", "归因", "ga4", "转化率", "utm"],
            "why_use": "把营销建议落到可测量指标，避免报告只给动作不给验证方式。",
            "how_to_use": "为每条行动建议补充北极星指标、过程指标、口径和数据获取路径。",
            "output_artifact": "SpecialistNotes.metrics",
            "evidence_role": "validator",
            "use_well": "指标必须有定义、时间窗、分母和触发事件。",
        },
        {
            "skill": "ab-testing",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["ab测试", "a/b", "实验", "假设", "variant", "测试"],
            "why_use": "把争议性营销建议转成可验证实验，而不是一次性拍脑袋决策。",
            "how_to_use": "为关键建议生成实验假设、受众、成功指标、样本和停止条件。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "实验不能替代事实证据，只能验证后续动作。",
        },
        {
            "skill": "aso",
            "nodes": ["search_planner", "marketing_intelligence_hunter", "marketing_specialist"],
            "trigger_terms": ["app store", "应用商店", "aso", "下载", "榜单", "评分", "关键词"],
            "why_use": "地图 App 调研经常需要看应用商店标题、截图、评分、评论和关键词排名。",
            "how_to_use": "驱动 SearchPlan 加入 App Store/应用市场来源，并分析下载转化素材。",
            "output_artifact": "SearchPlan.tasks / SpecialistNotes",
            "evidence_role": "method_reference",
            "use_well": "必须抓取真实商店页面、版本记录或评论；skill 不直接证明排名变化。",
        },
        {
            "skill": "social",
            "nodes": ["ugc_social_hunter", "marketing_specialist", "report_writer"],
            "trigger_terms": ["社媒", "小红书", "微博", "抖音", "b站", "twitter", "social", "声量"],
            "why_use": "把社媒内容、品牌声量和用户讨论纳入竞品监测。",
            "how_to_use": "用于规划社媒搜索词、内容类型和互动指标，并把 UGC 信号转成低置信度证据。",
            "output_artifact": "SourceListFragment / SpecialistNotes",
            "evidence_role": "method_reference",
            "use_well": "社媒信号必须和官方/媒体/数据源交叉验证。",
        },
        {
            "skill": "public-relations",
            "nodes": ["media_source_hunter", "marketing_specialist", "report_writer"],
            "trigger_terms": ["公关", "媒体", "pr", "新闻稿", "传播", "报道", "声量"],
            "why_use": "适合分析竞品如何通过媒体叙事放大产品动作或品牌主张。",
            "how_to_use": "指导媒体来源筛选、新闻角度拆解和传播建议。",
            "output_artifact": "SearchPlan.tasks / ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "不要把 PR 建议冒充成已发生的市场反馈。",
        },
        {
            "skill": "launch",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["发布", "上线", "上新", "launch", "新功能", "发布节奏"],
            "why_use": "竞品上新调研后，市场组通常需要反推发布节奏、传播窗口和响应动作。",
            "how_to_use": "把产品更新证据转成发布复盘和我方响应清单。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "动作建议要区分立即响应、观察、长期布局。",
        },
        {
            "skill": "content-strategy",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["内容", "选题", "栏目", "内容策略", "editorial", "日历"],
            "why_use": "把行业/竞品洞察转成内容选题、栏目和传播节奏。",
            "how_to_use": "根据已验证 claim 生成内容主题池和优先级。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "内容主题必须服务一个明确人群和业务目标。",
        },
        {
            "skill": "seo-audit",
            "nodes": ["marketing_intelligence_hunter", "marketing_specialist"],
            "trigger_terms": ["seo", "搜索流量", "排名", "自然流量", "技术seo"],
            "why_use": "用于分析竞品官网、落地页、帮助中心等搜索入口表现。",
            "how_to_use": "提出要抓取的页面和 SEO 检查维度，输出改进假设。",
            "output_artifact": "MarketingIntelFragment / SpecialistNotes",
            "evidence_role": "method_reference",
            "use_well": "SEO 判断需要页面、排名或流量工具证据支撑。",
        },
        {
            "skill": "ai-seo",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["ai搜索", "llm", "chatgpt", "perplexity", "ai citation", "geo", "aeo"],
            "why_use": "当用户关心 AI 搜索/助手推荐里的品牌可见性时，用来设计可被引用的内容结构。",
            "how_to_use": "把报告行动建议转成 AI 可读知识资产、FAQ 和结构化页面。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "只作为内容分发建议，不证明当前 AI 可见度。",
        },
        {
            "skill": "programmatic-seo",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["programmatic seo", "pseo", "规模化页面", "城市页", "模板页"],
            "why_use": "地图业务适合地点、路线、城市、场景类页面的规模化 SEO 机会判断。",
            "how_to_use": "在行动建议里设计页面模板、数据字段和质量门槛。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "必须先确认页面需求真实、数据可维护、无低质批量风险。",
        },
        {
            "skill": "schema",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["schema", "结构化数据", "json-ld", "rich snippets", "知识面板"],
            "why_use": "用于把地点/产品/FAQ/评论等内容变成搜索引擎更容易理解的结构。",
            "how_to_use": "作为 SEO 或 AI-SEO 建议的技术补充。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "只建议适配业务真实页面类型的 schema。",
        },
        {
            "skill": "site-architecture",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["网站结构", "导航", "sitemap", "栏目", "信息架构", "页面层级"],
            "why_use": "当报告要给官网、专题页或内容阵地建议时，补齐页面层级和内链结构。",
            "how_to_use": "把内容/SEO建议组织成页面地图和优先级。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "避免为一次活动设计过重的信息架构。",
        },
        {
            "skill": "cro",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["转化", "落地页", "表单", "conversion", "cro", "转化率"],
            "why_use": "把调研结论转成落地页、活动页或下载页的转化优化建议。",
            "how_to_use": "输出页面问题、假设、优先级和对应实验。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "必须结合流量来源、用户意图和页面目标。",
        },
        {
            "skill": "signup",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["注册", "开户", "试用", "signup", "注册转化"],
            "why_use": "适合 SaaS/会员/开发者平台，不是普通地图用户必用节点。",
            "how_to_use": "仅当产品有注册/试用漏斗时，分析摩擦点和转化假设。",
            "output_artifact": "SpecialistNotes / ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "不要把所有增长问题都误判为注册问题。",
        },
        {
            "skill": "onboarding",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["激活", "新用户", "首次使用", "onboarding", "aha", "留存"],
            "why_use": "适合分析新功能上线后如何让用户第一次用起来、形成习惯。",
            "how_to_use": "把功能证据和用户反馈转成首访路径、空状态、引导任务和激活指标。",
            "output_artifact": "SpecialistNotes / ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "必须定义激活事件和 time-to-value。",
        },
        {
            "skill": "churn-prevention",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["流失", "留存", "取消", "churn", "召回", "沉默用户"],
            "why_use": "当调研目标是留住用户或挽回沉默用户时，补齐流失原因和干预机制。",
            "how_to_use": "把用户反馈和行为指标转成流失风险分层和触达策略。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "要区分自愿流失、低频自然流失和产品不可控流失。",
        },
        {
            "skill": "emails",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["邮件", "email", "生命周期", "召回", "欢迎序列"],
            "why_use": "适合 B2B、会员、开发者或活动运营场景的生命周期触达。",
            "how_to_use": "把行动建议细化成触发条件、频次、内容和衡量指标。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "地图大众用户场景要谨慎，优先考虑 App 内触达或 push。",
        },
        {
            "skill": "sms",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["短信", "sms", "mms", "短消息", "触达"],
            "why_use": "仅适合高意图、高价值或服务通知型触达，不应默认用于普通营销。",
            "how_to_use": "作为触达渠道建议，补合规、频控、退订和人群条件。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "必须标注合规和用户打扰风险。",
        },
        {
            "skill": "referrals",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["裂变", "推荐", "转介绍", "referral", "邀请", "分享"],
            "why_use": "适合地图场景里的组队、出行、收藏路线、地点分享等传播机制设计。",
            "how_to_use": "把用户场景转成分享动机、奖励、闭环和反作弊设计。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "不要为了裂变牺牲用户信任；必须说明分享理由和触发时机。",
        },
        {
            "skill": "community-marketing",
            "nodes": ["ugc_social_hunter", "marketing_specialist"],
            "trigger_terms": ["社区", "社群", "口碑", "粉丝", "ambassador", "discord", "论坛"],
            "why_use": "适合长期用户口碑、车主/骑行/旅游/本地生活圈层研究。",
            "how_to_use": "指导 UGC 来源选择和社区飞轮建议。",
            "output_artifact": "SourceListFragment / SpecialistNotes",
            "evidence_role": "method_reference",
            "use_well": "要区分真实社区需求和短期活动噪音。",
        },
        {
            "skill": "co-marketing",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["联名", "合作", "伙伴", "co-marketing", "联合营销", "生态"],
            "why_use": "地图业务常涉及车企、酒旅、本地生活、文旅、出行伙伴联合增长。",
            "how_to_use": "把行业/竞品信号转成伙伴候选、联合场景和价值交换。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "必须说明双方收益和执行资源，不只列合作名单。",
        },
        {
            "skill": "ads",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["广告", "投放", "paid", "roas", "cpa", "预算", "买量"],
            "why_use": "把传播建议落到付费渠道、目标人群、预算和优化指标。",
            "how_to_use": "在行动方案里设计投放假设和渠道测试。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "没有受众、预算和转化目标时不要给投放方案。",
        },
        {
            "skill": "ad-creative",
            "nodes": ["report_writer"],
            "trigger_terms": ["广告创意", "素材", "headline", "creative", "文案变体"],
            "why_use": "当报告后续要产出广告素材或创意方向时使用。",
            "how_to_use": "基于已通过引用的卖点生成创意方向，不新增事实。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "style_only",
            "use_well": "创意必须继承报告证据和品牌边界。",
        },
        {
            "skill": "copywriting",
            "nodes": ["report_writer", "humanizer_editor"],
            "trigger_terms": ["文案", "标题", "落地页", "cta", "改写", "价值主张"],
            "why_use": "把调研结论转成可用于页面、活动、发布的表达。",
            "how_to_use": "只在报告建议或附录产出文案，不改事实和引用。",
            "output_artifact": "ReportDraft.copy_assets",
            "evidence_role": "style_only",
            "use_well": "必须保留事实边界、来源和不确定性。",
        },
        {
            "skill": "copy-editing",
            "nodes": ["humanizer_editor", "report_writer"],
            "trigger_terms": ["润色", "编辑", "去ai味", "polish", "精简"],
            "why_use": "让报告读起来更像业务同事写的，而不是模板化 AI 文。",
            "how_to_use": "对 ReportDraft 做表达层编辑，产出 HumanizerChangeLog。",
            "output_artifact": "FinalReport / HumanizerChangeLog",
            "evidence_role": "style_only",
            "use_well": "不得改变数字、引用、风险级别和结论强度。",
        },
        {
            "skill": "marketing-psychology",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["心理", "行为", "说服", "动机", "认知", "决策"],
            "why_use": "帮助解释用户为什么会被某种功能、权益或表达触发。",
            "how_to_use": "把用户洞察转成心理机制假设和可测实验。",
            "output_artifact": "SpecialistNotes",
            "evidence_role": "method_reference",
            "use_well": "心理模型只能解释，不可替代用户证据。",
        },
        {
            "skill": "offers",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["权益", "offer", "优惠", "礼包", "会员", "套餐"],
            "why_use": "当方案需要设计权益、促销或价值包时使用。",
            "how_to_use": "把目标人群和触发场景转成权益结构、风险逆转和转化假设。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "要避免只堆优惠；必须说明价值和成本。",
        },
        {
            "skill": "paywalls",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["付费墙", "升级", "upsell", "试用转付费", "会员弹窗"],
            "why_use": "适合会员、增值服务、订阅类功能的付费转化分析。",
            "how_to_use": "设计升级时机、价值证明、分层和反感风险。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "只在有真实付费路径时使用。",
        },
        {
            "skill": "popups",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["弹窗", "modal", "banner", "浮层", "退出意图"],
            "why_use": "用于活动、订阅、下载、公告等轻量转化组件建议。",
            "how_to_use": "补触发条件、频控、关闭路径和指标。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "必须明确打扰成本和用户场景。",
        },
        {
            "skill": "lead-magnets",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["线索", "资料包", "白皮书", "模板", "lead magnet", "下载"],
            "why_use": "适合 B2B、本地商家、开发者生态等线索获取场景。",
            "how_to_use": "设计内容资产、分发渠道和后续培育路径。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "要说明线索质量和后续承接，不只追求下载量。",
        },
        {
            "skill": "free-tools",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["免费工具", "计算器", "生成器", "grader", "工具获客"],
            "why_use": "适合用地图/位置/路线/商圈数据做工程化获客工具。",
            "how_to_use": "把洞察转成工具概念、输入输出、分发和衡量方式。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "必须评估数据可得性、维护成本和真实使用场景。",
        },
        {
            "skill": "directory-submissions",
            "nodes": ["marketing_intelligence_hunter", "report_writer"],
            "trigger_terms": ["目录", "榜单", "product hunt", "g2", "capterra", "提交"],
            "why_use": "用于软件/工具/AI产品发现渠道，不是地图主链路默认项。",
            "how_to_use": "当对象是工具型产品或海外分发时，补发现渠道和外链机会。",
            "output_artifact": "MarketingIntelFragment / ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "地图业务要谨慎使用，除非研究对象确实依赖目录分发。",
        },
        {
            "skill": "prospecting",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["潜客", "leads", "prospecting", "客户名单", "拓客"],
            "why_use": "适合 B2B 商户、车企、文旅、政企合作等目标账户研究。",
            "how_to_use": "根据 ICP 和行业信号输出账户筛选条件与数据字段。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "不要输出未经授权的个人联系方式；只做账户和公开线索层面。",
        },
        {
            "skill": "cold-email",
            "nodes": ["report_writer"],
            "trigger_terms": ["冷邮件", "cold email", "outbound", "外呼", "触达话术"],
            "why_use": "当报告后续要给 B2B 外联话术时使用。",
            "how_to_use": "基于 approved claims 生成邮件序列或话术。",
            "output_artifact": "ReportDraft.copy_assets",
            "evidence_role": "style_only",
            "use_well": "必须遵守合规和品牌语气，不新增事实。",
        },
        {
            "skill": "sales-enablement",
            "nodes": ["report_writer"],
            "trigger_terms": ["销售材料", "话术", "battlecard", "sales", "异议处理"],
            "why_use": "把调研输出转成销售或BD可用的材料。",
            "how_to_use": "从 ClaimGraph 中抽取差异点、证据和异议处理。",
            "output_artifact": "ReportDraft.enablement_assets",
            "evidence_role": "method_reference",
            "use_well": "只使用通过 Citation Auditor 的事实。",
        },
        {
            "skill": "revops",
            "nodes": ["marketing_specialist", "report_writer"],
            "trigger_terms": ["revops", "mql", "sql", "线索流转", "crm", "销售交接"],
            "why_use": "适合把市场动作和销售/商务承接流程打通。",
            "how_to_use": "设计 lead stage、评分、路由、SLA 和数据口径。",
            "output_artifact": "ReportDraft.action_plan",
            "evidence_role": "method_reference",
            "use_well": "只有涉及线索/销售协同时启用。",
        },
        {
            "skill": "image",
            "nodes": ["report_writer"],
            "trigger_terms": ["图片", "海报", "banner", "视觉", "素材", "mockup"],
            "why_use": "用于报告后续视觉素材方向，不用于调研事实。",
            "how_to_use": "根据已确认主张生成视觉 brief。",
            "output_artifact": "ReportDraft.creative_brief",
            "evidence_role": "style_only",
            "use_well": "先确定信息主张，再做视觉表达。",
        },
        {
            "skill": "video",
            "nodes": ["report_writer"],
            "trigger_terms": ["视频", "短视频", "脚本", "reels", "demo", "video"],
            "why_use": "用于把调研结论转成短视频或发布视频脚本。",
            "how_to_use": "输出视频结构、hook、镜头和 CTA。",
            "output_artifact": "ReportDraft.creative_brief",
            "evidence_role": "style_only",
            "use_well": "视频脚本必须继承已验证卖点。",
        },
    ],
    "finance": [
        {
            "skill": "yfinance-data",
            "nodes": ["intent_router", "finance_data_hunter", "finance_specialist"],
            "trigger_terms": ["股价", "市值", "ticker", "price", "financials", "收入", "eps", "财报"],
            "why_use": "提供最基础的行情、财务、分红、期权和分析师数据，是金融链路的默认结构化数据入口。",
            "how_to_use": "由 finance_data_hunter 或 Finance Specialist 调用，输出 FIN### 或结构化补丁。",
            "output_artifact": "SourceListFragment / SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "必须标明数据日期、币种、期间和 Yahoo/yfinance 口径。",
        },
        {
            "skill": "funda-data",
            "nodes": ["intent_router", "finance_data_hunter", "finance_specialist", "gap_filler"],
            "trigger_terms": ["funda", "dcf", "comps", "sec", "transcript", "分析师", "供应链", "fred"],
            "why_use": "适合分析师级研究、SEC/电话会/供应链/宏观数据补缺。",
            "how_to_use": "优先 MCP 做综合研究，REST 做原始结构化数据兜底。",
            "output_artifact": "SourceListFragment / SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "需要 FUNDA_API_KEY 或 MCP；所有合成内容仍要 Citation Auditor 审核。",
        },
        {
            "skill": "finance-sentiment",
            "nodes": ["finance_data_hunter", "ugc_social_hunter", "finance_specialist"],
            "trigger_terms": ["情绪", "buzz", "reddit", "x", "polymarket", "bullish", "热度"],
            "why_use": "把分散社媒/新闻/预测市场信号变成结构化情绪指标。",
            "how_to_use": "作为金融 UGC 信号源，和价格/新闻/财报交叉验证。",
            "output_artifact": "SourceListFragment / SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "情绪不能单独支撑投资结论，只能描述市场关注和分歧。",
        },
        {
            "skill": "company-valuation",
            "nodes": ["finance_specialist", "report_writer"],
            "trigger_terms": ["估值", "DCF", "fair value", "intrinsic", "目标价", "sotp", "pe"],
            "why_use": "当问题是值不值得投、贵不贵、合理价格时，需要估值框架而不是普通 SWOT。",
            "how_to_use": "基于 CleanSourceList 和结构化财务数据输出 DCF/相对/SOTP 估值笔记。",
            "output_artifact": "SpecialistNotes / ClaimGraphPatch",
            "evidence_role": "method_reference",
            "use_well": "必须展示关键假设、敏感性和不构成投资建议边界。",
        },
        {
            "skill": "earnings-preview",
            "nodes": ["finance_specialist", "report_writer"],
            "trigger_terms": ["财报前", "preview", "预期", "下周财报", "consensus", "street expecting"],
            "why_use": "适合财报前判断市场预期、beat/miss 历史和关键关注点。",
            "how_to_use": "生成财报前 Checklist 和预期差风险。",
            "output_artifact": "SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "区分一致预期、历史表现和个人判断。",
        },
        {
            "skill": "earnings-recap",
            "nodes": ["finance_specialist", "report_writer"],
            "trigger_terms": ["财报后", "recap", "reported", "beat", "miss", "业绩反应"],
            "why_use": "适合财报快评和业绩复盘，拆 actual vs estimate 与股价反应。",
            "how_to_use": "补充 KPI 树和空-雨-伞报告的财务事实。",
            "output_artifact": "SpecialistNotes / ClaimGraphPatch",
            "evidence_role": "structured_data",
            "use_well": "必须明确季度、口径、同比/环比和预期来源。",
        },
        {
            "skill": "estimate-analysis",
            "nodes": ["finance_specialist"],
            "trigger_terms": ["预期修正", "estimate", "revision", "eps趋势", "一致预期"],
            "why_use": "用于判断市场预期上修/下修以及增长质量。",
            "how_to_use": "分析 EPS/收入预期分布、修正方向和不确定性。",
            "output_artifact": "SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "不能把分析师预期当成公司实际业绩。",
        },
        {
            "skill": "startup-analysis",
            "nodes": ["intent_router", "framework_analyst", "finance_specialist"],
            "trigger_terms": ["创业公司", "startup", "vc", "融资", "加入", "尽调", "投资"],
            "why_use": "把创业公司问题分成投资人、求职者、创始人三个视角，避免只看融资新闻。",
            "how_to_use": "Step 0 用于框架路由，Step 2 用于多视角 ClaimGraph。",
            "output_artifact": "AuditCard / ClaimGraphPatch",
            "evidence_role": "method_reference",
            "use_well": "必须补融资、团队、产品、客户、竞争和风险证据。",
        },
        {
            "skill": "yc-reader",
            "nodes": ["official_source_hunter", "finance_data_hunter", "framework_analyst"],
            "trigger_terms": ["yc", "y combinator", "batch", "创业生态", "初创公司"],
            "why_use": "适合 YC 公司、批次、赛道和创业趋势研究。",
            "how_to_use": "作为公开静态数据源补充公司列表、标签、批次和招聘状态。",
            "output_artifact": "SourceListFragment",
            "evidence_role": "structured_data",
            "use_well": "只用于 YC 覆盖范围内，不要泛化到所有创业公司。",
        },
        {
            "skill": "twitter-reader",
            "nodes": ["finance_data_hunter", "ugc_social_hunter", "finance_specialist"],
            "trigger_terms": ["twitter", "x.com", "fintwit", "推特", "tweets", "市场情绪"],
            "why_use": "适合金融实时舆论、分析师观点和突发事件跟踪。",
            "how_to_use": "通过 opencli 只读搜索或读取 feed，输出低/中置信度 UGC 来源。",
            "output_artifact": "SourceListFragment",
            "evidence_role": "market_evidence",
            "use_well": "需要登录态；必须标记为 UGC，不能单独证明事实。",
        },
        {
            "skill": "linkedin-reader",
            "nodes": ["ugc_social_hunter", "finance_specialist"],
            "trigger_terms": ["linkedin", "领英", "专业观点", "招聘", "分析师帖子"],
            "why_use": "用于专业网络、招聘和行业人士观点信号。",
            "how_to_use": "通过 opencli 只读抓取公开/登录可见内容。",
            "output_artifact": "SourceListFragment",
            "evidence_role": "market_evidence",
            "use_well": "不要抓取或输出隐私敏感个人信息。",
        },
        {
            "skill": "discord-reader",
            "nodes": ["ugc_social_hunter", "finance_specialist"],
            "trigger_terms": ["discord", "交易群", "社群", "crypto discord"],
            "why_use": "适合 crypto/交易社群讨论监测。",
            "how_to_use": "通过 opencli 只读读取已登录 Discord 桌面端。",
            "output_artifact": "SourceListFragment",
            "evidence_role": "market_evidence",
            "use_well": "只读；不发送、不反应、不导出敏感内容。",
        },
        {
            "skill": "telegram-reader",
            "nodes": ["ugc_social_hunter", "finance_specialist"],
            "trigger_terms": ["telegram", "电报", "tg", "频道", "crypto news"],
            "why_use": "适合 crypto/金融频道新闻和市场讨论。",
            "how_to_use": "通过 tdl 只读导出或搜索消息。",
            "output_artifact": "SourceListFragment",
            "evidence_role": "market_evidence",
            "use_well": "需要本地 tdl 和账号环境；只读且注明来源频道。",
        },
        {
            "skill": "opencli-reader",
            "nodes": ["finance_data_hunter", "official_source_hunter", "media_source_hunter", "ugc_social_hunter"],
            "trigger_terms": ["opencli", "reddit", "xueqiu", "雪球", "微博", "知乎", "substack", "youtube"],
            "why_use": "作为没有专门 reader 时的只读兜底，覆盖财经和中文平台。",
            "how_to_use": "优先专用 reader；无专用 reader 时用 opencli 读取页面/搜索结果。",
            "output_artifact": "SourceListFragment",
            "evidence_role": "market_evidence",
            "use_well": "永远只读，不能调用点赞、评论、发送、关注等写操作。",
        },
        {
            "skill": "tradingview-reader",
            "nodes": ["finance_data_hunter", "finance_specialist"],
            "trigger_terms": ["tradingview", "期权链", "iv", "chart", "screener", "技术图"],
            "why_use": "适合期权链、图表状态、筛选器和市场技术数据。",
            "how_to_use": "通过本地 TradingView.app 和 opencli 只读获取数据。",
            "output_artifact": "SourceListFragment / SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "需要本地 app 登录态；不修改 watchlist 或图表。",
        },
        {
            "skill": "stock-correlation",
            "nodes": ["finance_specialist"],
            "trigger_terms": ["相关性", "correlation", "同行", "pair", "hedge", "beta", "联动"],
            "why_use": "用于同行联动、供应链相关、对冲和相关股票分析。",
            "how_to_use": "基于历史价格生成相关矩阵和解释。",
            "output_artifact": "SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "相关性不是因果；必须标时间窗。",
        },
        {
            "skill": "stock-liquidity",
            "nodes": ["finance_specialist"],
            "trigger_terms": ["流动性", "成交量", "spread", "slippage", "market impact", "换手"],
            "why_use": "用于风险专项和交易可执行性分析。",
            "how_to_use": "分析成交量、价差、冲击成本和流动性分层。",
            "output_artifact": "SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "必须标样本期和交易规模假设。",
        },
        {
            "skill": "saas-valuation-compression",
            "nodes": ["finance_specialist", "framework_analyst"],
            "trigger_terms": ["saas", "arr", "multiple", "估值压缩", "融资轮", "valuation compression"],
            "why_use": "适合 VC-backed SaaS 的融资轮估值变化分析。",
            "how_to_use": "研究融资历史和 ARR 倍数，解释压缩/扩张原因。",
            "output_artifact": "SpecialistNotes / ClaimGraphPatch",
            "evidence_role": "method_reference",
            "use_well": "ARR、估值和轮次必须有来源；缺失时标不确定。",
        },
        {
            "skill": "sepa-strategy",
            "nodes": ["finance_specialist"],
            "trigger_terms": ["sepa", "minervini", "vcp", "突破", "趋势模板", "swing"],
            "why_use": "适合交易技术面问题，不适合普通商业调研默认启用。",
            "how_to_use": "用作技术面专项补充，输出教育性分析。",
            "output_artifact": "SpecialistNotes",
            "evidence_role": "method_reference",
            "use_well": "必须加非投资建议边界，不能给交易指令。",
        },
        {
            "skill": "options-payoff",
            "nodes": ["finance_specialist", "report_writer"],
            "trigger_terms": ["期权", "payoff", "spread", "straddle", "condor", "盈亏图"],
            "why_use": "当用户给出期权策略时生成盈亏结构和可视化。",
            "how_to_use": "抽取腿、行权价、权利金、到期日，生成策略说明或图表。",
            "output_artifact": "SpecialistNotes / ReportDraft.visual",
            "evidence_role": "method_reference",
            "use_well": "默认参数必须显式标注；不构成交易建议。",
        },
        {
            "skill": "etf-premium",
            "nodes": ["finance_specialist"],
            "trigger_terms": ["etf", "nav", "溢价", "折价", "premium", "discount"],
            "why_use": "用于 ETF 价格与 NAV 偏离、套利阻塞和结构性风险。",
            "how_to_use": "计算 premium/discount，并拆分 NAV 与结构因素。",
            "output_artifact": "SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "特别标注 ETF 类型、交易日和 NAV 来源。",
        },
        {
            "skill": "hormuz-strait",
            "nodes": ["finance_data_hunter", "framework_analyst"],
            "trigger_terms": ["霍尔木兹", "hormuz", "油价", "航运", "地缘", "中东"],
            "why_use": "用于能源、航运和地缘风险专项。",
            "how_to_use": "读取 dashboard 数据，补 PEST/风险矩阵。",
            "output_artifact": "SourceListFragment / ClaimGraphPatch",
            "evidence_role": "structured_data",
            "use_well": "只在相关行业/事件触发时启用。",
        },
        {
            "skill": "hyperliquid-reader",
            "nodes": ["finance_data_hunter", "finance_specialist"],
            "trigger_terms": ["hyperliquid", "hl", "perp", "funding", "open interest", "dex"],
            "why_use": "用于链上永续、资金费率、盘口和 OI 数据。",
            "how_to_use": "调用公开 info API，只读抓取市场数据。",
            "output_artifact": "SourceListFragment / SpecialistNotes",
            "evidence_role": "structured_data",
            "use_well": "只读市场数据；不涉及账户和交易。",
        },
        {
            "skill": "skill-creator",
            "nodes": ["human_review_gate"],
            "trigger_terms": ["创建skill", "新技能", "自动化", "反复做", "skill creator"],
            "why_use": "当现有节点反复遇到无法覆盖的新工作流时，用来设计新 skill。",
            "how_to_use": "作为人工评审后的扩展动作，不在普通调研中自动执行。",
            "output_artifact": "WorkflowImprovementProposal",
            "evidence_role": "validator",
            "use_well": "必须先证明现有 skill 不足，再创建新 skill。",
        },
        {
            "skill": "generative-ui",
            "nodes": ["report_writer"],
            "trigger_terms": ["可视化", "图表", "dashboard", "widget", "交互", "diagram"],
            "why_use": "把财务、竞品或营销结论做成更容易读的可视化组件。",
            "how_to_use": "在报告需要图表/交互说明时生成可视化 brief 或 widget 规格。",
            "output_artifact": "ReportDraft.visual",
            "evidence_role": "style_only",
            "use_well": "图表数据必须来自 ApprovedClaimGraph，不允许凭空画数。",
        },
    ],
}


SKILL_INVOCATION_REGISTRY: List[Dict[str, Any]] = [
    {
        "id": "intent_router.marketing_preflight",
        "node_id": "intent_router",
        "skill_or_tool": "marketing-ideas / marketing-plan / yfinance-data / funda-data",
        "invocation_type": "llm_method",
        "trigger": "The user intent touches growth, marketing planning, finance, startup, or a single financial number.",
        "input_artifact": "RawUserQuery + available skills",
        "output_artifact": "IntentBrief + AuditCard",
        "evidence_role": "routing",
        "can_directly_support_claim": False,
        "required_setup": "Installed skill files; data skills may also require Python package/API setup later.",
        "artifact_policy": "List triggered expert skills and why in AuditCard; do not treat Step 0 probes as final evidence.",
    },
    {
        "id": "search_planner.framework_keywords",
        "node_id": "search_planner",
        "skill_or_tool": "framework templates + competitor-profiling/customer-research methods",
        "invocation_type": "llm_method",
        "trigger": "After AuditCard is confirmed and dimensions must become evidence tasks.",
        "input_artifact": "AuditCard",
        "output_artifact": "SearchPlan",
        "evidence_role": "routing",
        "can_directly_support_claim": False,
        "required_setup": "Local framework and marketing skill documents.",
        "artifact_policy": "Output task-level source_layers, expected_evidence, language, and assigned_hunter.",
    },
    {
        "id": "official_source_hunter.firecrawl",
        "node_id": "official_source_hunter",
        "skill_or_tool": "Firecrawl",
        "invocation_type": "script_cli",
        "trigger": "SearchPlan task assigned to official_source_hunter or source_layers contains official.",
        "input_artifact": "SearchPlan",
        "output_artifact": "SourceListFragment",
        "evidence_role": "market_evidence",
        "can_directly_support_claim": True,
        "required_setup": "FIRECRAWL_API_KEY.",
        "artifact_policy": "OFF### rows must preserve URL, publisher, date, key_facts, and confidence_rationale.",
    },
    {
        "id": "media_source_hunter.firecrawl",
        "node_id": "media_source_hunter",
        "skill_or_tool": "Firecrawl",
        "invocation_type": "script_cli",
        "trigger": "SearchPlan task assigned to media_source_hunter or source_layers contains media/deep_analysis.",
        "input_artifact": "SearchPlan",
        "output_artifact": "SourceListFragment",
        "evidence_role": "market_evidence",
        "can_directly_support_claim": True,
        "required_setup": "FIRECRAWL_API_KEY.",
        "artifact_policy": "MED### rows must distinguish reported fact from interpretation and paywall summaries.",
    },
    {
        "id": "rss_news_hunter.finance_rss_reader",
        "node_id": "rss_news_hunter",
        "skill_or_tool": "finance-rss-reader",
        "invocation_type": "script_cli",
        "trigger": "SearchPlan task assigned to rss_news_hunter or source_layers contains rss/news.",
        "input_artifact": "SearchPlan",
        "output_artifact": "SourceListFragment",
        "evidence_role": "market_evidence",
        "can_directly_support_claim": True,
        "required_setup": "Local finance-rss-reader script; optional SEARCH_AGENT_RSS_* env vars.",
        "artifact_policy": "RSS### rows must carry relevance_score; RSS is a signal layer and may need stronger corroboration.",
    },
    {
        "id": "ugc_social_hunter.bili_cli",
        "node_id": "ugc_social_hunter",
        "skill_or_tool": "agent-reach / bili CLI",
        "invocation_type": "script_cli",
        "trigger": "SearchPlan task assigned to ugc_social_hunter or source_layers contains ugc/social/video.",
        "input_artifact": "SearchPlan",
        "output_artifact": "SourceListFragment",
        "evidence_role": "market_evidence",
        "can_directly_support_claim": True,
        "required_setup": "bili CLI for current vertical slice; agent-reach/opencli for expanded platforms.",
        "artifact_policy": "UGC### rows default to low confidence and cannot be generalized without corroboration.",
    },
    {
        "id": "finance_data_hunter.yfinance",
        "node_id": "finance_data_hunter",
        "skill_or_tool": "yfinance-data",
        "invocation_type": "script_cli",
        "trigger": "SearchPlan task assigned to finance_data_hunter, ticker query, or source_layers contains finance_data.",
        "input_artifact": "SearchPlan",
        "output_artifact": "SourceListFragment",
        "evidence_role": "structured_data",
        "can_directly_support_claim": True,
        "required_setup": "pip install -r requirements.txt; yfinance network access.",
        "artifact_policy": "FIN### rows must include metric period/currency when available; missing metrics go to Source QA.",
    },
    {
        "id": "marketing_intelligence_hunter.skill_catalog",
        "node_id": "marketing_intelligence_hunter",
        "skill_or_tool": "marketing-skills-catalog",
        "invocation_type": "llm_method",
        "trigger": "SearchPlan task assigned to marketing_intelligence_hunter or source_layers contains marketing_intelligence.",
        "input_artifact": "SearchPlan",
        "output_artifact": "SourceListFragment",
        "evidence_role": "method_reference",
        "can_directly_support_claim": False,
        "required_setup": "Local vendor/marketing skill files.",
        "artifact_policy": "MKT### rows are method sources, not market facts; later claims still need evidence source_ids.",
    },
    {
        "id": "marketing_intelligence_hunter.marketing_plan",
        "node_id": "marketing_intelligence_hunter",
        "skill_or_tool": "marketing-plan",
        "invocation_type": "llm_method",
        "trigger": "The task asks for GTM, growth plan, campaign roadmap, AARRR, or marketing operating plan.",
        "input_artifact": "SearchPlan",
        "output_artifact": "SourceListFragment",
        "evidence_role": "method_reference",
        "can_directly_support_claim": False,
        "required_setup": "vendor/marketing/skills/marketing-plan/SKILL.md.",
        "artifact_policy": "Use as planning method and structure only; do not cite as evidence that a market fact is true.",
    },
    {
        "id": "marketing_intelligence_hunter.marketing_ideas",
        "node_id": "marketing_intelligence_hunter",
        "skill_or_tool": "marketing-ideas",
        "invocation_type": "llm_method",
        "trigger": "The task asks for marketing ideas, growth directions, creative options, acquisition, retention, or referral tactics.",
        "input_artifact": "SearchPlan",
        "output_artifact": "SourceListFragment",
        "evidence_role": "method_reference",
        "can_directly_support_claim": False,
        "required_setup": "vendor/marketing/skills/marketing-ideas/SKILL.md.",
        "artifact_policy": "Use to generate/organize options; every recommended action still needs segment/channel/metric logic and evidence.",
    },
    {
        "id": "source_list_merger.internal_dedupe",
        "node_id": "source_list_merger",
        "skill_or_tool": "URL canonicalizer + schema validator",
        "invocation_type": "internal",
        "trigger": "All available SourceListFragment rows are ready or explicitly skipped.",
        "input_artifact": "SourceListFragment",
        "output_artifact": "RawSourceList + MergerLog",
        "evidence_role": "validator",
        "can_directly_support_claim": False,
        "required_setup": "None.",
        "artifact_policy": "Do not create facts; preserve channel provenance and duplicate decisions.",
    },
    {
        "id": "source_qa.internal_quality",
        "node_id": "source_qa",
        "skill_or_tool": "URL normalization + duplicate/date/numeric checks",
        "invocation_type": "internal",
        "trigger": "RawSourceList is produced.",
        "input_artifact": "RawSourceList + SearchPlan",
        "output_artifact": "SourceQANotes + ConflictRegister + GapList + CleanSourceList",
        "evidence_role": "validator",
        "can_directly_support_claim": False,
        "required_setup": "None.",
        "artifact_policy": "Approve, downgrade, exclude, or pause; do not analyze unsupported sources.",
    },
    {
        "id": "gap_filler.refetch",
        "node_id": "gap_filler",
        "skill_or_tool": "Firecrawl / finance skill / official search",
        "invocation_type": "script_cli",
        "trigger": "Source QA produces blocking GapList or ConflictRegister.",
        "input_artifact": "GapList + ConflictRegister",
        "output_artifact": "SupplementalSourceList + RefetchNotes",
        "evidence_role": "market_evidence",
        "can_directly_support_claim": True,
        "required_setup": "Depends on the gap: Firecrawl key, finance dependencies, or platform CLI.",
        "artifact_policy": "Only fill listed gaps/conflicts; tie every new source to gap_id or conflict_id.",
    },
    {
        "id": "framework_analyst.frameworks",
        "node_id": "framework_analyst",
        "skill_or_tool": "framework definitions + finance/marketing specialist notes",
        "invocation_type": "llm_method",
        "trigger": "CleanSourceList is available and framework dimensions are confirmed.",
        "input_artifact": "CleanSourceList + confirmed framework dimensions",
        "output_artifact": "ClaimGraph",
        "evidence_role": "method_reference",
        "can_directly_support_claim": False,
        "required_setup": "Local framework definitions.",
        "artifact_policy": "Every claim must cite approved source_ids and label fact/calculation/assumption/judgment.",
    },
    {
        "id": "finance_specialist.finance_skills",
        "node_id": "finance_specialist",
        "skill_or_tool": "yfinance-data / funda-data / earnings-recap / company-valuation",
        "invocation_type": "api_or_mcp",
        "trigger": "ClaimGraph or user question contains financial metrics, filings, valuation, or market data.",
        "input_artifact": "CleanSourceList + finance questions from ClaimGraph",
        "output_artifact": "SpecialistNotes + ClaimGraphPatch",
        "evidence_role": "structured_data",
        "can_directly_support_claim": True,
        "required_setup": "yfinance dependencies and optional FUNDA_API_KEY/Funda MCP.",
        "artifact_policy": "Append only sourced finance claims with period, currency, metric definition, and assumptions.",
    },
    {
        "id": "marketing_specialist.marketing_skills",
        "node_id": "marketing_specialist",
        "skill_or_tool": "marketing-ideas / marketing-plan / product-marketing / customer-research",
        "invocation_type": "llm_method",
        "trigger": "ClaimGraph needs positioning, funnel, channel, customer, or growth interpretation.",
        "input_artifact": "CleanSourceList + marketing/growth questions from ClaimGraph",
        "output_artifact": "SpecialistNotes + ClaimGraphPatch",
        "evidence_role": "method_reference",
        "can_directly_support_claim": False,
        "required_setup": "Local marketing skill files.",
        "artifact_policy": "Marketing methods shape recommendations; factual market claims still need CleanSourceList source_ids.",
    },
    {
        "id": "citation_auditor.internal_citations",
        "node_id": "citation_auditor",
        "skill_or_tool": "source_id existence checks + claim-source comparison",
        "invocation_type": "internal",
        "trigger": "ClaimGraph and specialist patches are ready.",
        "input_artifact": "ClaimGraph + ClaimGraphPatch + SpecialistNotes + CleanSourceList",
        "output_artifact": "CitationAudit + ApprovedClaimGraph",
        "evidence_role": "validator",
        "can_directly_support_claim": False,
        "required_setup": "None.",
        "artifact_policy": "Block unsupported claims; rewrite or remove claims whose citations do not prove them.",
    },
    {
        "id": "outline_architect.outline_methods",
        "node_id": "outline_architect",
        "skill_or_tool": "brainstorming / writing-plans / content-strategy",
        "invocation_type": "llm_method",
        "trigger": "ApprovedClaimGraph and reader/decision context are ready.",
        "input_artifact": "ApprovedClaimGraph + IntentBrief",
        "output_artifact": "OutlinePlan",
        "evidence_role": "method_reference",
        "can_directly_support_claim": False,
        "required_setup": "Local outline archetypes and planning skills.",
        "artifact_policy": "Methods shape three candidate outlines but cannot approve one for the user.",
    },
    {
        "id": "human_outline_gate.user_choice",
        "node_id": "human_outline_gate",
        "skill_or_tool": "structured user choice capture",
        "invocation_type": "internal",
        "trigger": "OutlinePlan is ready and explicit user input is required.",
        "input_artifact": "OutlinePlan",
        "output_artifact": "ApprovedOutline",
        "evidence_role": "validator",
        "can_directly_support_claim": False,
        "required_setup": "Explicit user response.",
        "artifact_policy": "No report prose before approved_by_user=true.",
    },
    {
        "id": "report_writer.report_family",
        "node_id": "report_writer",
        "skill_or_tool": "report family selector + build-report/marketing-plan where applicable",
        "invocation_type": "llm_method",
        "trigger": "ApprovedClaimGraph and CitationAudit pass.",
        "input_artifact": "ApprovedClaimGraph + CitationAudit + CleanSourceList + IntentBrief",
        "output_artifact": "ReportDraft",
        "evidence_role": "method_reference",
        "can_directly_support_claim": False,
        "required_setup": "Local report family definitions and optional data analytics/reporting skills.",
        "artifact_policy": "Report structure can change; facts, source_ids, confidence, and risk boundaries cannot be invented.",
    },
    {
        "id": "outline_compliance_auditor.structure_check",
        "node_id": "outline_compliance_auditor",
        "skill_or_tool": "copy-editing / verification-before-completion",
        "invocation_type": "llm_method",
        "trigger": "ReportDraft is ready.",
        "input_artifact": "ApprovedOutline + ReportDraft",
        "output_artifact": "OutlineComplianceReview",
        "evidence_role": "validator",
        "can_directly_support_claim": False,
        "required_setup": "ApprovedOutline and structured ReportDraft.",
        "artifact_policy": "Block any missing, unexpected, or reordered top-level section.",
    },
    {
        "id": "humanizer_editor.humanizer_zh",
        "node_id": "humanizer_editor",
        "skill_or_tool": "humanizer-zh / copy-editing",
        "invocation_type": "llm_method",
        "trigger": "ReportDraft exists and citations are preserved.",
        "input_artifact": "ReportDraft + CleanSourceList",
        "output_artifact": "FinalReport + HumanizerChangeLog",
        "evidence_role": "style_only",
        "can_directly_support_claim": False,
        "required_setup": "Installed humanizer/copy-editing skills.",
        "artifact_policy": "Style-only edits; do not change numbers, source_ids, dates, confidence, or factual meaning.",
    },
    {
        "id": "integrity_diff_checker.internal_diff",
        "node_id": "integrity_diff_checker",
        "skill_or_tool": "local diff + regex extraction + schema validator",
        "invocation_type": "internal",
        "trigger": "FinalReport and HumanizerChangeLog are produced.",
        "input_artifact": "ReportDraft + FinalReport + HumanizerChangeLog",
        "output_artifact": "IntegrityDiff",
        "evidence_role": "validator",
        "can_directly_support_claim": False,
        "required_setup": "None.",
        "artifact_policy": "Block final review if evidence-bearing tokens changed after humanizer.",
    },
]


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


OUTLINE_ARCHETYPES: List[Dict[str, Any]] = [
    {
        "id": "panoramic_comparison",
        "name": "全景对比型",
        "report_family": "competitive_battlecard",
        "writing_logic": "事实全景 → 维度对比 → 用户反馈 → 差距判断 → 我方行动",
        "sections": [
            ("竞品变化全景", "建立时间线和功能事实底座"),
            ("核心功能与用户任务", "解释功能解决的用户任务和价值"),
            ("我方与竞品对比", "按统一维度比较能力、体验与节奏"),
            ("用户反馈与证据分歧", "区分事实、UGC 情绪和证据限制"),
            ("对我方的启示与行动", "提出有优先级和验证指标的建议"),
        ],
    },
    {
        "id": "causal_deep_dive",
        "name": "因果深挖型",
        "report_family": "deep_research_report",
        "writing_logic": "现象 → 成因 → 机制 → 影响 → 战略含义",
        "sections": [
            ("现象与关键问题", "定义真正需要解释的变化和边界"),
            ("变化背后的驱动因素", "分析市场、技术、用户和组织成因"),
            ("核心机制与产品逻辑", "解释功能或策略如何产生价值"),
            ("影响、限制与不确定性", "分析影响范围、反证和边界条件"),
            ("战略含义与优先议题", "把因果判断转成我方重点议题"),
        ],
    },
    {
        "id": "action_decision",
        "name": "行动决策型",
        "report_family": "executive_decision_memo",
        "writing_logic": "决策问题 → 选项 → 取舍 → 行动 → 验证",
        "sections": [
            ("需要做出的决策", "明确决策对象、时限和成功标准"),
            ("可选方案与证据", "列出可行选项及各自证据"),
            ("推荐方案与取舍", "说明选择、放弃和关键假设"),
            ("实施条件与风险", "识别资源、依赖、风险和触发条件"),
            ("下一步行动与验证指标", "给出责任动作、顺序和验证指标"),
        ],
    },
]


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
    return [_enrich_node_contract(node) for node in NODE_CONTRACTS]


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
        "## Responsibility Boundary",
        str(node["responsibility_boundary"]),
        "",
        "## LLM Judgment",
        str(node["llm_judgment"]),
        "",
        "## Tool/Skill Use",
    ]
    for item in _as_list(node["tool_or_skill_use"]):
        lines.append(f"- {item}")

    skill_rules = get_skill_invocations_for_node(node_id)
    if skill_rules:
        lines.extend(["", "## Skill Invocation Rules"])
        for rule in skill_rules:
            lines.append(
                "- {skill} ({kind}, {role}): trigger={trigger}; output={output}; can_support_claim={claim}; policy={policy}".format(
                    skill=rule["skill_or_tool"],
                    kind=rule["invocation_type"],
                    role=rule["evidence_role"],
                    trigger=rule["trigger"],
                    output=rule["output_artifact"],
                    claim=rule["can_directly_support_claim"],
                    policy=rule["artifact_policy"],
                )
            )

    lines.extend(["", "## May Do"])
    for item in _as_list(node["may_do"]):
        lines.append(f"- {item}")

    lines.extend(["", "## Must Not Do"])
    for item in _as_list(node["must_not_do"]):
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
    lines.extend(["", "## Handoff", str(node["handoff_to"])])

    return "\n".join(lines).rstrip() + "\n"


def get_node_playbook(node_id: str) -> Dict[str, Any]:
    """Return one node in the user-facing progression format."""
    node = _node_by_id(node_id)
    return {
        "node_id": node["id"],
        "node": node["name"],
        "input": node["input_artifact"],
        "responsibility_boundary": node["responsibility_boundary"],
        "llm_judgment": node["llm_judgment"],
        "skill_tool_calls": node["tool_or_skill_use"],
        "may_do": node["may_do"],
        "must_not_do": node["must_not_do"],
        "output_artifact": node["output_artifact"],
        "next_step_condition": node["quality_gate"],
        "hard_constraints": node["hard_constraints"],
        "handoff_to": node["handoff_to"],
    }


def get_workflow_playbook() -> List[Dict[str, Any]]:
    """Return all nodes in the user-facing progression format."""
    return [get_node_playbook(node["id"]) for node in get_node_contracts()]


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
                f"**职责边界**：{node['responsibility_boundary']}",
                "",
                f"**LLM判断**：{node['llm_judgment']}",
                "",
                f"**skill/tool调用**：{_format_inline_list(node['skill_tool_calls'])}",
                "",
                f"**可做**：{_format_inline_list(node['may_do'])}",
                "",
                f"**不可做**：{_format_inline_list(node['must_not_do'])}",
                "",
                f"**输出artifact**：{node['output_artifact']}",
                "",
                f"**进入下一步条件**：{node['next_step_condition']}",
                "",
                f"**交给下一步**：{node['handoff_to']}",
                "",
                f"**硬约束**：{_format_inline_list(node['hard_constraints'])}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_skill_invocation_registry_markdown() -> str:
    """Render the node-by-node skill invocation registry."""
    lines = [
        "# Skill Invocation Registry",
        "",
        "这张表说明每个节点可以调用哪些 skill/tool、怎么调用、产出什么 artifact，以及产物能不能直接支撑事实结论。",
        "",
        "| Node | Skill/Tool | Type | Evidence Role | Can Support Claim | Output | Policy |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in SKILL_INVOCATION_REGISTRY:
        lines.append(
            "| {node} | `{skill}` | {kind} | {role} | {claim} | {output} | {policy} |".format(
                node=entry["node_id"],
                skill=entry["skill_or_tool"],
                kind=entry["invocation_type"],
                role=entry["evidence_role"],
                claim="yes" if entry["can_directly_support_claim"] else "no",
                output=entry["output_artifact"],
                policy=entry["artifact_policy"].replace("|", "/"),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def get_skill_chain(domain: str) -> Dict[str, Any]:
    """Return the skill chain for a domain."""
    if domain not in SKILL_CHAINS:
        raise KeyError(f"Unknown skill chain: {domain}")
    return deepcopy(SKILL_CHAINS[domain])


def get_skill_invocation_registry() -> List[Dict[str, Any]]:
    """Return the executable skill/tool invocation registry."""
    return deepcopy(SKILL_INVOCATION_REGISTRY)


def get_skill_invocations_for_node(node_id: str) -> List[Dict[str, Any]]:
    """Return invocation rules for one workflow node."""
    return [
        deepcopy(entry)
        for entry in SKILL_INVOCATION_REGISTRY
        if entry["node_id"] == node_id
    ]


def get_skill_adapter_matrix(domain: str = "") -> Dict[str, List[Dict[str, Any]]]:
    """Return the fine-grained skill adapter matrix."""
    if domain:
        return {domain: deepcopy(SKILL_ADAPTER_MATRIX.get(domain, []))}
    return deepcopy(SKILL_ADAPTER_MATRIX)


def select_skill_adapters(
    query: str,
    *,
    domain: str = "",
    node_id: str = "",
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Select fine-grained skill adapters for a query and optional node."""
    query_l = (query or "").lower()
    candidates: List[Dict[str, Any]] = []
    domains = [domain] if domain else list(SKILL_ADAPTER_MATRIX.keys())
    for current_domain in domains:
        for adapter in SKILL_ADAPTER_MATRIX.get(current_domain, []):
            trigger_score = 0
            for term in adapter.get("trigger_terms", []):
                term_l = str(term).lower()
                if term_l and term_l in query_l:
                    trigger_score += 3
            is_default = adapter["skill"] in {"marketing-plan", "marketing-ideas", "yfinance-data"}
            if not trigger_score and not is_default:
                continue
            score = trigger_score
            if node_id and node_id in adapter.get("nodes", []):
                score += 2
            if is_default:
                score += 1
            if score:
                selected = deepcopy(adapter)
                selected["domain"] = current_domain
                selected["selection_score"] = score
                candidates.append(selected)
    candidates.sort(key=lambda item: (-item["selection_score"], item["skill"]))
    return candidates[:limit]


def render_skill_adapter_matrix_markdown(domain: str = "") -> str:
    """Render fine-grained skill adapters with trigger and artifact logic."""
    matrix = get_skill_adapter_matrix(domain)
    lines = [
        "# Skill Adapter Matrix",
        "",
        "这张矩阵说明每个细分 skill 为什么接入、在哪个节点用、怎么用、产出什么 artifact，以及证据边界。",
        "",
    ]
    for current_domain, adapters in matrix.items():
        lines.extend([f"## {current_domain}", ""])
        for adapter in adapters:
            lines.extend(
                [
                    f"### {adapter['skill']}",
                    f"- nodes: {', '.join(adapter['nodes'])}",
                    f"- trigger_terms: {', '.join(adapter['trigger_terms'][:8])}",
                    f"- why_use: {adapter['why_use']}",
                    f"- how_to_use: {adapter['how_to_use']}",
                    f"- output_artifact: {adapter['output_artifact']}",
                    f"- evidence_role: {adapter['evidence_role']}",
                    f"- use_well: {adapter['use_well']}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def get_skill_coverage_audit(repo_root: Any = None) -> Dict[str, Any]:
    """Audit discovered local skills against workflow registry references."""
    root = Path(repo_root or Path(__file__).resolve().parents[1])
    referenced = _referenced_skill_names()

    category_specs = [
        {
            "category": "marketing",
            "discovered": _discover_skill_names(root / "vendor" / "marketing" / "skills"),
            "runtime_scope_note": "Runtime marketing skills are used as method references unless backed by external evidence.",
        },
        {
            "category": "finance",
            "discovered": _discover_finance_skill_names(root / "vendor" / "finance" / "plugins"),
            "runtime_scope_note": "Finance data skills may directly support structured data claims when dependencies/API keys are configured.",
        },
        {
            "category": "writing",
            "discovered": _discover_writing_skill_names(root),
            "runtime_scope_note": "Writing skills are style/structure helpers; they cannot change facts, source_ids, or risk boundaries.",
        },
        {
            "category": "superpowers",
            "discovered": _discover_superpowers_skill_names(),
            "runtime_scope_note": "Superpowers are development/process guardrails for building and verifying the skill, not report evidence.",
        },
    ]

    categories = []
    for spec in category_specs:
        discovered = sorted(set(spec["discovered"]))
        registered_or_referenced = sorted(name for name in discovered if name in referenced)
        inventory_only = sorted(name for name in discovered if name not in referenced)
        categories.append(
            {
                "category": spec["category"],
                "discovered_count": len(discovered),
                "discovered": discovered,
                "registered_or_referenced": registered_or_referenced,
                "inventory_only": inventory_only,
                "runtime_scope_note": spec["runtime_scope_note"],
            }
        )

    return {
        "categories": categories,
        "referenced_skill_names": sorted(referenced),
        "policy": [
            "A local SKILL.md file is inventory, not an executable workflow step.",
            "Runtime use requires a registry entry, node contract reference, or specialist skill chain reference.",
            "Method/reference skills cannot directly support factual claims without CleanSourceList evidence.",
        ],
    }


def render_skill_coverage_audit_markdown(repo_root: Any = None) -> str:
    """Render a readable skill coverage audit."""
    audit = get_skill_coverage_audit(repo_root)
    lines = [
        "# Skill Coverage Audit",
        "",
        "这份审计把本地已发现的 skill 和 workflow 已明确调度的 skill 分开，避免把库存误认为已经接入执行链。",
        "",
    ]
    for category in audit["categories"]:
        lines.extend(
            [
                f"## {category['category']}",
                "",
                f"- discovered: {category['discovered_count']}",
                f"- registered_or_referenced: {len(category['registered_or_referenced'])}",
                f"- inventory_only: {len(category['inventory_only'])}",
                f"- scope: {category['runtime_scope_note']}",
                "",
                "**registered_or_referenced**:",
                ", ".join(f"`{name}`" for name in category["registered_or_referenced"]) or "_none_",
                "",
                "**inventory_only examples**:",
                ", ".join(f"`{name}`" for name in category["inventory_only"][:20]) or "_none_",
                "",
            ]
        )
    lines.extend(["## Policy", ""])
    for policy in audit["policy"]:
        lines.append(f"- {policy}")
    return "\n".join(lines).rstrip() + "\n"


def get_rss_relevance_contract() -> Dict[str, Any]:
    """Return the RSS relevance score contract."""
    return deepcopy(RSS_RELEVANCE_CONTRACT)


def get_report_families() -> List[Dict[str, Any]]:
    """Return all supported report families."""
    return deepcopy(REPORT_FAMILIES)


def build_outline_candidates(intent_brief: Dict[str, Any], claim_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Build three distinct outline candidates and recommend one without approving it.

    The recommendation is advisory. The selected structure becomes executable only
    after :func:`approve_outline` records explicit user approval.
    """
    brief = intent_brief or {}
    claims = list(claim_ids or ["CLAIM_SLOT"])
    subject = brief.get("subject") or brief.get("research_topic") or "调研主题"
    audience = brief.get("audience") or brief.get("target_reader") or "业务决策者"
    decision_text = " ".join(
        str(brief.get(key, ""))
        for key in ("user_decision", "output_shape", "research_goal", "intent")
    ).lower()
    recommended_family = recommend_report_family(brief)["id"]
    preferred_by_family = {
        "competitive_battlecard": "panoramic_comparison",
        "deep_research_report": "causal_deep_dive",
        "executive_decision_memo": "action_decision",
        "growth_gtm_plan": "action_decision",
        "finance_investment_note": "causal_deep_dive",
        "evidence_brief": "panoramic_comparison",
    }
    recommended_id = preferred_by_family.get(recommended_family, "causal_deep_dive")
    if any(token in decision_text for token in ("跟进", "行动", "决策", "方案", "落地")):
        recommended_id = "action_decision"
    elif any(token in decision_text for token in ("对比", "竞品", "差距", "battlecard")):
        recommended_id = "panoramic_comparison"
    elif any(token in decision_text for token in ("为什么", "机制", "深度", "研究")):
        recommended_id = "causal_deep_dive"

    candidates: List[Dict[str, Any]] = []
    for archetype in OUTLINE_ARCHETYPES:
        sections: List[Dict[str, Any]] = []
        for index, (heading, purpose) in enumerate(archetype["sections"], start=1):
            assigned = [claims[(index - 1) % len(claims)]]
            sections.append(
                {
                    "section_id": f"S{index}",
                    "heading": heading,
                    "purpose": purpose,
                    "required_claim_ids": assigned,
                    "word_budget": max(100, 110 * len(assigned)),
                }
            )
        candidates.append(
            {
                "outline_id": archetype["id"],
                "name": archetype["name"],
                "report_family": archetype["report_family"],
                "title": f"{subject}：{archetype['name']}调研报告",
                "target_reader": audience,
                "writing_logic": archetype["writing_logic"],
                "sections": sections,
                "tradeoff": {
                    "panoramic_comparison": "覆盖最全，适合功能盘点，但因果深度相对有限。",
                    "causal_deep_dive": "解释深，适合专题研究，但不适合只要快速决策的读者。",
                    "action_decision": "行动清晰，适合管理层，但会压缩背景与方法论篇幅。",
                }[archetype["id"]],
            }
        )
    recommended_name = next(x["name"] for x in candidates if x["outline_id"] == recommended_id)
    return {
        "candidates": candidates,
        "recommended_outline_id": recommended_id,
        "recommendation_reason": f"根据读者“{audience}”和决策目标，优先推荐{recommended_name}；用户仍可选择、组合或修改任一大纲。",
        "approval_required": True,
    }


def approve_outline(
    outline_plan: Dict[str, Any],
    selected_outline_id: str,
    *,
    approved_by_user: bool,
    revision_notes: Optional[List[str]] = None,
    sections_override: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create the immutable outline contract used by Report Writer."""
    if not approved_by_user:
        raise ValueError("大纲必须由用户明确确认，Codex 不得代替用户批准。")
    candidates = outline_plan.get("candidates", [])
    selected = next((item for item in candidates if item.get("outline_id") == selected_outline_id), None)
    if selected is None:
        raise ValueError(f"未知大纲：{selected_outline_id}")
    approved = deepcopy(selected)
    if sections_override is not None:
        approved["sections"] = deepcopy(sections_override)
    for section in approved.get("sections", []):
        if not section.get("heading") or not section.get("purpose"):
            raise ValueError("每个大纲章节必须包含 heading 和 purpose。")
        section.setdefault("required_claim_ids", ["CLAIM_SLOT"])
        section.setdefault("word_budget", 600)
    approved.update(
        {
            "selected_outline_id": selected_outline_id,
            "approved_by_user": True,
            "revision_notes": list(revision_notes or []),
        }
    )
    return approved


def review_outline_compliance(approved_outline: Dict[str, Any], report_draft: Dict[str, Any]) -> Dict[str, Any]:
    """Verify that a report inherits the approved top-level structure exactly."""
    expected = [section.get("heading") for section in approved_outline.get("sections", [])]
    actual = [section.get("heading") for section in report_draft.get("sections", [])]
    missing = [heading for heading in expected if heading not in actual]
    unexpected = [heading for heading in actual if heading not in expected]
    expected_by_heading = {section.get("heading"): section for section in approved_outline.get("sections", [])}
    purpose_gaps, evidence_gaps, missing_required_claim_ids, needs_expansion, over_budget = [], [], [], [], []
    for section in report_draft.get("sections", []):
        heading = section.get("heading")
        contract = expected_by_heading.get(heading, {})
        content = str(section.get("content", ""))
        purpose = str(contract.get("purpose", ""))
        purpose_terms = [term.lower() for term in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", purpose)]
        purpose_present = bool(purpose_terms) and any(term in content.lower() for term in purpose_terms)
        if not section.get("purpose_addressed", False) or (section.get("writer_added_prose", True) and not purpose_present):
            purpose_gaps.append(heading)
        used_claims = set(section.get("claim_ids", []))
        required_claims = set(contract.get("required_claim_ids", []))
        absent = sorted(required_claims - used_claims)
        missing_required_claim_ids.extend(absent)
        if not used_claims or absent:
            evidence_gaps.append(heading)
        budget = int(contract.get("word_budget", section.get("word_budget", 0)) or 0)
        actual_count = int(section.get("actual_word_count", len(content.replace(" ", ""))) or 0)
        if budget and actual_count < max(1, int(budget * 0.90)):
            needs_expansion.append(heading)
        if budget and actual_count > int(budget * 1.10):
            over_budget.append(heading)
    passed = not missing and not unexpected and actual == expected and not purpose_gaps and not evidence_gaps and not needs_expansion and not over_budget
    return {
        "status": "passed" if passed else "blocked",
        "missing_sections": missing,
        "unexpected_sections": unexpected,
        "order_matches": actual == expected,
        "purpose_gaps": purpose_gaps,
        "evidence_gaps": evidence_gaps,
        "missing_required_claim_ids": missing_required_claim_ids,
        "needs_expansion": needs_expansion,
        "over_budget": over_budget,
    }


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
            return _enrich_node_contract(node)
    raise KeyError(f"Unknown node: {node_id}")


def _enrich_node_contract(node: Dict[str, Any]) -> Dict[str, Any]:
    enriched = deepcopy(node)
    boundary = NODE_BOUNDARIES.get(node["id"], {})
    enriched.update(
        {
            "responsibility_boundary": boundary.get("responsibility_boundary", ""),
            "may_do": boundary.get("may_do", []),
            "must_not_do": boundary.get("must_not_do", []),
            "handoff_to": boundary.get("handoff_to", ""),
        }
    )
    return enriched


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


def _discover_skill_names(skill_root: Path) -> List[str]:
    if not skill_root.exists():
        return []
    return sorted(path.parent.name for path in skill_root.glob("*/SKILL.md"))


def _discover_finance_skill_names(finance_plugins_root: Path) -> List[str]:
    if not finance_plugins_root.exists():
        return []
    return sorted(path.parent.name for path in finance_plugins_root.glob("*/skills/*/SKILL.md"))


def _discover_writing_skill_names(repo_root: Path) -> List[str]:
    names = set(PROCESS_SKILL_REFERENCES["writing"])
    marketing_root = repo_root / "vendor" / "marketing" / "skills"
    for name in ["copy-editing", "copywriting", "content-strategy", "public-relations", "emails"]:
        if (marketing_root / name / "SKILL.md").exists():
            names.add(name)
    for root in [Path.home() / ".codex" / "skills", Path.home() / ".agents" / "skills"]:
        for name in ["humanizer", "humanizer-zh", "copy-editing", "copywriting", "content-strategy"]:
            if (root / name / "SKILL.md").exists():
                names.add(name)
    return sorted(names)


def _discover_superpowers_skill_names() -> List[str]:
    names = set(PROCESS_SKILL_REFERENCES["superpowers"])
    root = Path.home() / ".codex" / "plugins" / "cache" / "openai-curated-remote" / "superpowers" / "6.1.1" / "skills"
    if root.exists():
        names.update(path.parent.name for path in root.glob("*/SKILL.md"))
    return sorted(names)


def _referenced_skill_names() -> set:
    text_parts: List[str] = []
    for entry in SKILL_INVOCATION_REGISTRY:
        text_parts.append(str(entry.get("skill_or_tool", "")))
    for node in NODE_CONTRACTS:
        text_parts.extend(str(item) for item in _as_list(node.get("tool_or_skill_use", [])))
    for chain in SKILL_CHAINS.values():
        for value in chain.values():
            if isinstance(value, list):
                text_parts.extend(str(item) for item in value)
    for values in PROCESS_SKILL_REFERENCES.values():
        text_parts.extend(values)

    text = "\n".join(text_parts)
    names = set()
    for token in text.replace("/", " ").replace(",", " ").replace(";", " ").split():
        cleaned = token.strip("`*：:()[]，。")
        if cleaned:
            names.add(cleaned)
    return names


def _report_family_by_id(report_id: str) -> Dict[str, Any]:
    for family in REPORT_FAMILIES:
        if family["id"] == report_id:
            return family
    raise KeyError(f"Unknown report family: {report_id}")
