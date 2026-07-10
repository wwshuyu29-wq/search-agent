import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))


class WorkflowContractsTest(unittest.TestCase):
    def test_every_agent_node_has_llm_skill_artifact_and_gate_contract(self):
        from workflow_contracts import get_node_contracts

        contracts = get_node_contracts()
        expected_nodes = [
            "intent_router",
            "search_planner",
            "official_source_hunter",
            "media_source_hunter",
            "rss_news_hunter",
            "ugc_social_hunter",
            "finance_data_hunter",
            "marketing_intelligence_hunter",
            "source_list_merger",
            "source_qa",
            "gap_filler",
            "framework_analyst",
            "finance_specialist",
            "marketing_specialist",
            "citation_auditor",
            "report_writer",
            "humanizer_editor",
            "integrity_diff_checker",
        ]

        self.assertEqual([node["id"] for node in contracts], expected_nodes)
        for node in contracts:
            with self.subTest(node=node["id"]):
                self.assertTrue(node["input_artifact"])
                self.assertTrue(node["llm_judgment"])
                self.assertTrue(node["tool_or_skill_use"])
                self.assertTrue(node["output_artifact"])
                self.assertTrue(node["quality_gate"])
                self.assertTrue(node["hard_constraints"])

    def test_specialist_skill_chains_cover_finance_marketing_and_mixed_work(self):
        from workflow_contracts import get_skill_chain

        finance = get_skill_chain("finance")
        marketing = get_skill_chain("marketing")
        mixed = get_skill_chain("finance_marketing_mixed")

        self.assertIn("yfinance-data", finance["step0"])
        self.assertIn("funda-data", finance["step1"])
        self.assertIn("company-valuation", finance["step2"])
        self.assertIn("earnings-recap", finance["step2"])

        self.assertIn("marketing-ideas", marketing["step0"])
        self.assertIn("marketing-plan", marketing["step0"])
        self.assertIn("competitor-profiling", marketing["step1"])
        self.assertIn("customer-research", marketing["step2"])
        self.assertIn("pricing", marketing["step2"])

        self.assertIn("marketing signal", mixed["logic"][0])
        self.assertIn("financial metric", " -> ".join(mixed["logic"]))
        self.assertIn("no direct jump from buzz to stock price", mixed["hard_constraints"][0])

    def test_skill_invocation_registry_covers_nodes_and_evidence_roles(self):
        from workflow_contracts import (
            get_skill_coverage_audit,
            get_node_contracts,
            get_skill_invocation_registry,
            get_skill_invocations_for_node,
            render_skill_invocation_registry_markdown,
        )

        registry = get_skill_invocation_registry()
        node_ids = {node["id"] for node in get_node_contracts()}
        covered_nodes = {entry["node_id"] for entry in registry}

        self.assertTrue(node_ids.issubset(covered_nodes))
        for entry in registry:
            with self.subTest(entry=entry["id"]):
                self.assertIn(entry["node_id"], node_ids)
                self.assertTrue(entry["skill_or_tool"])
                self.assertIn(entry["invocation_type"], {"llm_method", "script_cli", "api_or_mcp", "internal"})
                self.assertIn(
                    entry["evidence_role"],
                    {"routing", "market_evidence", "structured_data", "method_reference", "validator", "style_only"},
                )
                self.assertTrue(entry["input_artifact"])
                self.assertTrue(entry["output_artifact"])
                self.assertTrue(entry["artifact_policy"])

        rss = get_skill_invocations_for_node("rss_news_hunter")
        self.assertTrue(any(item["skill_or_tool"] == "finance-rss-reader" for item in rss))
        self.assertTrue(any(item["invocation_type"] == "script_cli" for item in rss))

        finance = get_skill_invocations_for_node("finance_data_hunter")
        self.assertTrue(any(item["skill_or_tool"] == "yfinance-data" for item in finance))
        self.assertTrue(any(item["evidence_role"] == "structured_data" for item in finance))

        marketing = get_skill_invocations_for_node("marketing_intelligence_hunter")
        method_entries = [item for item in marketing if item["skill_or_tool"] in {"marketing-plan", "marketing-ideas"}]
        self.assertTrue(method_entries)
        self.assertFalse(any(item["can_directly_support_claim"] for item in method_entries))

        humanizer = get_skill_invocations_for_node("humanizer_editor")
        self.assertTrue(any(item["evidence_role"] == "style_only" for item in humanizer))

        markdown = render_skill_invocation_registry_markdown()
        self.assertIn("# Skill Invocation Registry", markdown)
        self.assertIn("marketing_intelligence_hunter", markdown)
        self.assertIn("method_reference", markdown)
        self.assertIn("Can Support Claim", markdown)

        audit = get_skill_coverage_audit(REPO_ROOT)
        categories = {category["category"]: category for category in audit["categories"]}
        self.assertIn("marketing", categories)
        self.assertIn("finance", categories)
        self.assertIn("writing", categories)
        self.assertIn("superpowers", categories)
        self.assertGreaterEqual(categories["marketing"]["discovered_count"], 40)
        self.assertGreaterEqual(categories["finance"]["discovered_count"], 20)
        self.assertIn("marketing-plan", categories["marketing"]["registered_or_referenced"])
        self.assertIn("yfinance-data", categories["finance"]["registered_or_referenced"])
        self.assertIn("humanizer-zh", categories["writing"]["registered_or_referenced"])
        self.assertIn("test-driven-development", categories["superpowers"]["registered_or_referenced"])
        self.assertIn("verification-before-completion", categories["superpowers"]["registered_or_referenced"])
        self.assertTrue(categories["superpowers"]["runtime_scope_note"])

        self.assertIn("onboarding", categories["marketing"]["registered_or_referenced"])
        self.assertIn("referrals", categories["marketing"]["registered_or_referenced"])
        self.assertIn("programmatic-seo", categories["marketing"]["registered_or_referenced"])
        self.assertIn("twitter-reader", categories["finance"]["registered_or_referenced"])
        self.assertIn("saas-valuation-compression", categories["finance"]["registered_or_referenced"])
        self.assertIn("brainstorming", categories["superpowers"]["registered_or_referenced"])

    def test_rss_relevance_threshold_contract_explains_0_6_as_fetch_gate(self):
        from workflow_contracts import get_rss_relevance_contract

        contract = get_rss_relevance_contract()

        self.assertEqual(contract["candidate_threshold"], 0.4)
        self.assertEqual(contract["full_text_threshold"], 0.6)
        self.assertIn("not truth", contract["meaning"])
        self.assertIn("title_hits", contract["formula"])
        self.assertIn("LLM Source Hunter", contract["next_llm_gate"])

    def test_report_families_are_selected_by_reader_and_decision_not_one_template(self):
        from workflow_contracts import recommend_report_family

        self.assertEqual(
            recommend_report_family({"user_decision": "形成业务动作或策略建议", "audience": "市场组"})["id"],
            "executive_decision_memo",
        )
        self.assertEqual(
            recommend_report_family({"user_decision": "形成投资/估值判断", "audience": "投资/研究读者"})["id"],
            "finance_investment_note",
        )
        self.assertEqual(
            recommend_report_family({"user_decision": "获取单一金融数字", "audience": "投资/研究读者"})["id"],
            "evidence_brief",
        )

    def test_artifact_contracts_define_required_handoff_fields(self):
        from workflow_contracts import get_artifact_contracts

        artifacts = get_artifact_contracts()
        expected = [
            "IntentBrief",
            "AuditCard",
            "SearchPlan",
            "SourceListFragment",
            "SourceList",
            "RawSourceList",
            "MergerLog",
            "SourceQANotes",
            "ConflictRegister",
            "GapList",
            "CleanSourceList",
            "SupplementalSourceList",
            "RefetchNotes",
            "ClaimGraph",
            "SpecialistNotes",
            "ClaimGraphPatch",
            "CitationAudit",
            "ApprovedClaimGraph",
            "ReportDraft",
            "HumanizerChangeLog",
            "FinalReport",
            "IntegrityDiff",
        ]

        self.assertEqual(list(artifacts.keys()), expected)
        for name, contract in artifacts.items():
            with self.subTest(artifact=name):
                self.assertTrue(contract["producer_nodes"])
                self.assertTrue(contract["consumer_nodes"])
                self.assertTrue(contract["required_fields"])
                self.assertTrue(contract["quality_rules"])

        self.assertIn("source_id", artifacts["SourceList"]["required_fields"])
        self.assertIn("canonical_url", artifacts["RawSourceList"]["required_fields"])
        self.assertIn("merged_sources", artifacts["MergerLog"]["required_fields"])
        self.assertIn("conflicts", artifacts["ConflictRegister"]["required_fields"])
        self.assertIn("gaps", artifacts["GapList"]["required_fields"])
        self.assertIn("claim_type", artifacts["ClaimGraph"]["required_fields"])
        self.assertIn("required_rewrites", artifacts["CitationAudit"]["required_fields"])
        self.assertIn("approved_claim_ids", artifacts["ApprovedClaimGraph"]["required_fields"])
        self.assertIn("changed_numbers", artifacts["IntegrityDiff"]["required_fields"])

    def test_agent_prompt_builder_renders_each_node_constraints_and_schema(self):
        from workflow_contracts import build_agent_prompt

        prompt = build_agent_prompt("source_qa")

        self.assertIn("Source QA Agent", prompt)
        self.assertIn("Input Artifact", prompt)
        self.assertIn("LLM Judgment", prompt)
        self.assertIn("Tool/Skill Use", prompt)
        self.assertIn("Output Artifact", prompt)
        self.assertIn("Quality Gate", prompt)
        self.assertIn("Hard Constraints", prompt)
        self.assertIn("SourceQANotes", prompt)
        self.assertIn("CleanSourceList", prompt)
        self.assertIn("Do not analyze from stale or duplicate sources", prompt)
        self.assertIn("Skill Invocation Rules", prompt)
        self.assertIn("validator", prompt)

    def test_orchestration_plan_groups_parallel_source_hunters_and_citation_gate(self):
        from workflow_contracts import get_orchestration_plan

        plan = get_orchestration_plan()
        phases = [phase["id"] for phase in plan]

        self.assertEqual(phases[0], "step0_intent_and_audit")
        self.assertIn("step1_parallel_source_hunting", phases)
        self.assertIn("step1_source_merge", phases)
        self.assertIn("step1_gap_fill_or_pause", phases)
        self.assertEqual(phases[-1], "step3_integrity_check")

        source_phase = next(phase for phase in plan if phase["id"] == "step1_parallel_source_hunting")
        self.assertTrue(source_phase["parallel"])
        self.assertEqual(
            source_phase["nodes"],
            [
                "official_source_hunter",
                "media_source_hunter",
                "rss_news_hunter",
                "ugc_social_hunter",
                "finance_data_hunter",
                "marketing_intelligence_hunter",
            ],
        )

        citation_phase = next(phase for phase in plan if phase["id"] == "step2_citation_audit")
        self.assertEqual(citation_phase["gate"], "citation_audit_passed")
        self.assertIn("ApprovedClaimGraph", citation_phase["output_artifacts"])

        merge_phase = next(phase for phase in plan if phase["id"] == "step1_source_merge")
        self.assertEqual(merge_phase["nodes"], ["source_list_merger"])
        self.assertEqual(merge_phase["output_artifacts"], ["RawSourceList", "MergerLog"])

        integrity_phase = next(phase for phase in plan if phase["id"] == "step3_integrity_check")
        self.assertEqual(integrity_phase["nodes"], ["integrity_diff_checker"])
        self.assertEqual(integrity_phase["gate"], "humanizer_integrity_passed")

    def test_orchestration_plan_marks_human_gates_and_automatic_gates(self):
        from workflow_contracts import get_orchestration_plan

        plan = get_orchestration_plan()
        gates = {phase["gate"]: phase for phase in plan}

        self.assertEqual(gates["audit_card_confirmed"]["gate_type"], "human")
        self.assertTrue(gates["audit_card_confirmed"]["halts_for_user"])
        self.assertEqual(gates["search_plan_complete"]["gate_type"], "automatic")
        self.assertFalse(gates["search_plan_complete"]["halts_for_user"])
        self.assertEqual(
            gates["source_qa_passed_or_user_resolved_conflict"]["gate_type"],
            "conditional_human",
        )
        self.assertEqual(gates["gap_fill_complete_or_pause"]["gate_type"], "conditional_human")
        self.assertEqual(gates["humanizer_integrity_passed"]["post_gate"], "final_report_review")

    def test_node_playbook_uses_user_requested_progression_fields(self):
        from workflow_contracts import get_node_playbook

        playbook = get_node_playbook("marketing_specialist")

        self.assertEqual(playbook["node"], "Marketing Specialist Agent")
        self.assertEqual(
            list(playbook.keys()),
            [
                "node_id",
                "node",
                "input",
                "llm_judgment",
                "skill_tool_calls",
                "output_artifact",
                "next_step_condition",
                "hard_constraints",
            ],
        )
        self.assertIn("customer-research", playbook["skill_tool_calls"])
        self.assertIn("MarketingClaims appended to ClaimGraph", playbook["output_artifact"])
        self.assertIn("Recommendations map", playbook["next_step_condition"])

    def test_workflow_playbook_markdown_covers_all_subagents_in_plain_progression(self):
        from workflow_contracts import render_workflow_playbook_markdown

        markdown = render_workflow_playbook_markdown()

        for node_name in [
            "Intent Router Agent",
            "Search Planner Agent",
            "Official Source Hunter",
            "Media Source Hunter",
            "RSS/News Hunter",
            "UGC/Social Hunter",
            "Finance Data Hunter",
            "Marketing Intelligence Hunter",
            "SourceList Merger",
            "Source QA Agent",
            "Gap Filler / Conflict Refetch Agent",
            "Framework Analyst Agent",
            "Financial Specialist Agent",
            "Marketing Specialist Agent",
            "Citation Auditor Agent",
            "Report Writer Agent",
            "Humanizer Editor Agent",
            "Integrity Diff Checker",
        ]:
            self.assertIn(f"## {node_name}", markdown)

        for heading in [
            "**输入**",
            "**LLM判断**",
            "**skill/tool调用**",
            "**输出artifact**",
            "**进入下一步条件**",
        ]:
            self.assertIn(heading, markdown)

    def test_codex_execution_model_explains_llm_invocation_without_api_key(self):
        from workflow_contracts import get_codex_execution_model, render_codex_execution_markdown

        model = get_codex_execution_model()

        self.assertEqual(model["primary_runtime"], "Codex skill runtime")
        self.assertIn("current Codex session", model["llm_invocation"])
        self.assertFalse(model["requires_openai_api_key_for_llm"])
        self.assertIn("build_agent_prompt(node_id)", model["node_prompt_source"])
        self.assertIn("multi-agent tools", model["parallelization"]["preferred"])
        self.assertIn("sequential same-session execution", model["parallelization"]["fallback"])

        markdown = render_codex_execution_markdown()
        self.assertIn("# Codex-Native Execution Model", markdown)
        self.assertIn("LLM 调用方式", markdown)
        self.assertIn("不需要为节点 LLM 另配 OpenAI API Key", markdown)
        self.assertIn("安装到 ~/.codex/skills/search-agent", markdown)


if __name__ == "__main__":
    unittest.main()
