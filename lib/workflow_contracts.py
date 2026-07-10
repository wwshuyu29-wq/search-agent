#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable workflow contracts for the multi-agent research pipeline.

This module keeps the node logic testable. Prompt documents can explain the
workflow, but code should also expose the contracts so CLI runs, tests, and
future orchestrators share the same mental model.
"""

from copy import deepcopy
from pathlib import Path
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
        "id": "report_writer",
        "name": "Report Writer Agent",
        "input_artifact": "ApprovedClaimGraph + CitationAudit + CleanSourceList",
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
        "output_artifact": "FinalReport + HumanizerChangeLog",
        "quality_gate": "Final text sounds like a professional internal research note, not a prompt template.",
        "hard_constraints": [
            "Do not change facts, numbers, citations, or confidence levels.",
            "Do not add personality or unsupported certainty.",
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
        "consumer_nodes": ["report_writer"],
        "required_fields": [
            "approved_claim_ids",
            "claims",
            "blocked_claim_ids",
            "citation_audit_status",
        ],
        "quality_rules": [
            "Only supported or explicitly allowed partially supported claims remain.",
            "Blocked claims are unavailable to Report Writer.",
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
        "id": "step3_report_draft",
        "step": "Step 3",
        "nodes": ["report_writer"],
        "input_artifacts": ["ApprovedClaimGraph", "CitationAudit", "CleanSourceList", "IntentBrief"],
        "output_artifacts": ["ReportDraft"],
        "parallel": False,
        "gate": "report_draft_preserves_citations",
        "gate_type": "automatic",
        "halts_for_user": False,
    },
    {
        "id": "step3_humanizer_final",
        "step": "Step 3",
        "nodes": ["humanizer_editor"],
        "input_artifacts": ["ReportDraft", "CleanSourceList"],
        "output_artifacts": ["FinalReport", "HumanizerChangeLog"],
        "parallel": False,
        "gate": "final_report_style_only_changes",
        "gate_type": "automatic",
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
