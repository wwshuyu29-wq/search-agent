import os
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))
sys.path.insert(0, str(REPO_ROOT / "bin"))

from intent_classifier import classify_intent  # noqa: E402
from intent_classifier import build_step0_context  # noqa: E402
from search_agent import SearchAgentSkill  # noqa: E402


class CliBehaviorTest(unittest.TestCase):
    def test_classify_intent_accepts_return_complexity(self):
        recommendations = classify_intent(
            "高德地图最近三个月上了什么新功能，对百度地图有什么启示",
            top_k=3,
            return_complexity=True,
        )

        self.assertTrue(recommendations)
        self.assertIn("is_complex_problem", recommendations[0])

    def test_new_feature_map_research_prefers_competitor_comparison(self):
        recommendations = classify_intent(
            "高德地图最近三个月上了什么新功能，对百度地图有什么启示",
            top_k=3,
            return_complexity=True,
        )

        self.assertEqual(recommendations[0]["framework"], "同行竞争对比")

    def test_step0_context_marks_classifier_as_cli_fallback_and_routes_marketing_ideas(self):
        context = build_step0_context("帮我想想百度地图暑期增长可以从哪些方向入手")

        self.assertEqual(context["decision_stack"][0], "LLM 语义理解层")
        self.assertIn("规则/关键词分类器", context["decision_stack"])
        self.assertTrue(context["cli_fallback_only"])
        self.assertIn("Codex prompt mode must use LLM", context["notes"])
        self.assertEqual(context["semantic_fields"]["user_decision"], "形成业务动作或策略建议")
        self.assertEqual(context["semantic_fields"]["time_scope"], "暑期")
        self.assertIn("marketing-ideas", [skill["skill"] for skill in context["preflight_skills"]])
        self.assertEqual(context["report_family"]["id"], "executive_decision_memo")
        self.assertTrue(context["node_chain_preview"])

        recommendations = classify_intent(
            "帮我想想百度地图暑期增长可以从哪些方向入手",
            top_k=3,
            return_complexity=True,
        )
        self.assertEqual(recommendations[0]["framework"], "4P营销")

    def test_step0_context_short_circuits_single_finance_number(self):
        context = build_step0_context("英伟达最新市值是多少")

        self.assertTrue(context["short_circuit"])
        self.assertEqual(context["semantic_fields"]["user_decision"], "获取单一金融数字")
        self.assertEqual(context["semantic_fields"]["time_scope"], "最新可得")
        self.assertIn("yfinance-data", [skill["skill"] for skill in context["preflight_skills"]])

    def test_cli_short_circuit_skips_framework_recommendations(self):
        agent = SearchAgentSkill()

        with patch("builtins.print") as mocked_print:
            agent.run("英伟达最新市值是多少", auto_confirm=False)

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("已停止完整调研流程", printed)
        self.assertNotIn("推荐的单个分析框架", printed)

    def test_cli_prints_report_family_and_node_chain_preview(self):
        agent = SearchAgentSkill()

        context = build_step0_context("帮我调研高德地图最近三个月上新，对百度地图市场组有什么启示")

        with patch("builtins.print") as mocked_print:
            agent._print_step0_audit_context(context)

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("建议报告形态", printed)
        self.assertIn("Executive Decision Memo", printed)
        self.assertIn("后续子 agent 链", printed)
        self.assertIn("Intent Router Agent", printed)
        self.assertIn("Citation Auditor Agent", printed)
        self.assertIn("Humanizer Editor Agent", printed)

    def test_cli_can_print_full_workflow_playbook(self):
        agent = SearchAgentSkill()

        with patch("builtins.print") as mocked_print:
            agent.print_workflow_playbook()

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("# Multi-Agent Workflow Node Playbook", printed)
        self.assertIn("## Intent Router Agent", printed)
        self.assertIn("## Humanizer Editor Agent", printed)
        self.assertIn("**输入**", printed)
        self.assertIn("**进入下一步条件**", printed)

    def test_cli_can_print_skill_invocation_registry(self):
        agent = SearchAgentSkill()

        with patch("builtins.print") as mocked_print:
            agent.print_skill_invocation_registry()

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("# Skill Invocation Registry", printed)
        self.assertIn("finance_data_hunter", printed)
        self.assertIn("yfinance-data", printed)
        self.assertIn("marketing-plan", printed)
        self.assertIn("Can Support Claim", printed)

    def test_cli_can_print_skill_coverage_audit(self):
        agent = SearchAgentSkill()

        with patch("builtins.print") as mocked_print:
            agent.print_skill_coverage_audit()

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("# Skill Coverage Audit", printed)
        self.assertIn("## marketing", printed)
        self.assertIn("## finance", printed)
        self.assertIn("## writing", printed)
        self.assertIn("## superpowers", printed)
        self.assertIn("inventory_only", printed)

    def test_cli_can_print_skill_adapter_matrix(self):
        agent = SearchAgentSkill()

        with patch("builtins.print") as mocked_print:
            agent.print_skill_adapter_matrix("marketing")

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("# Skill Adapter Matrix", printed)
        self.assertIn("## marketing", printed)
        self.assertIn("### onboarding", printed)
        self.assertIn("why_use", printed)
        self.assertIn("output_artifact", printed)

    def test_cli_can_run_workflow_dry_run(self):
        agent = SearchAgentSkill()

        with patch("builtins.print") as mocked_print:
            agent.run_workflow_dry_run("高德地图最近三个月上新，对百度地图市场组有什么启示")

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("Multi-Agent Workflow Dry Run", printed)
        self.assertIn("step0_intent_and_audit", printed)
        self.assertIn("step3_humanizer", printed)
        self.assertIn("FinalReport", printed)
        self.assertIn("status: complete", printed)

    def test_cli_gate_workflow_start_writes_pending_audit_state(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "search_agent_state.json"
            with patch("builtins.print") as mocked_print:
                state = agent.start_gate_workflow(
                    "高德地图最近三个月上新，对百度地图市场组有什么启示",
                    str(state_file),
                )

            saved = json.loads(state_file.read_text(encoding="utf-8"))
            printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)

        self.assertEqual(state["pending_gate"], "audit_card_confirmed")
        self.assertEqual(saved["pending_gate"], "audit_card_confirmed")
        self.assertIn("AuditCard", saved["artifacts"])
        self.assertNotIn("SearchPlan", saved["artifacts"])
        self.assertIn("等待用户确认", printed)

    def test_cli_gate_workflow_resume_confirmation_writes_final_review_state(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "search_agent_state.json"
            agent.start_gate_workflow(
                "高德地图最近三个月上新，对百度地图市场组有什么启示",
                str(state_file),
            )
            with patch("builtins.print") as mocked_print:
                state = agent.resume_gate_workflow("确认", str(state_file))

            saved = json.loads(state_file.read_text(encoding="utf-8"))
            printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)

        self.assertEqual(state["pending_gate"], "outline_approved_by_user")
        self.assertEqual(saved["pending_gate"], "outline_approved_by_user")
        self.assertIn("OutlinePlan", saved["artifacts"])
        self.assertNotIn("ReportDraft", saved["artifacts"])

    def test_cli_can_print_node_packets_from_saved_state(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "search_agent_state.json"
            state = agent.start_gate_workflow(
                "高德地图最近三个月上新，对百度地图市场组有什么启示",
                str(state_file),
            )
            state["artifacts"]["SearchPlan"] = {
                "frameworks": ["同行竞争对比"],
                "tasks": [
                    {
                        "task_id": "SP001",
                        "dimension": "竞品变化",
                        "query_zh": ["高德地图 新功能"],
                        "query_en": ["Amap new features"],
                        "source_layers": ["official", "media"],
                        "expected_evidence": ["发布时间", "关键事实"],
                        "source_id_prefix": "AUTO",
                    }
                ],
            }
            state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

            with patch("builtins.print") as mocked_print:
                packets = agent.print_node_packets(
                    "step1_parallel_source_hunting",
                    str(state_file),
                )

            printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)

        self.assertEqual(len(packets), 6)
        self.assertIn("Sub-Agent Node Packets", printed)
        self.assertIn("official_source_hunter", printed)
        self.assertIn("## Hard Constraints", printed)
        self.assertIn("skill_invocation_rules", printed)
        self.assertIn("can_support_claim", printed)

    def test_cli_can_execute_one_source_hunter_and_persist_fragment(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "search_agent_state.json"
            state = {
                "schema_version": "workflow_state.v1",
                "status": "waiting_for_user",
                "current_phase": "step1_parallel_source_hunting",
                "pending_gate": "source_list_fragment_valid",
                "artifacts": {
                    "SearchPlan": {
                        "frameworks": ["同行竞争对比"],
                        "tasks": [
                            {
                                "task_id": "OFF-T001",
                                "assigned_hunter": "official_source_hunter",
                                "dimension": "官方变化",
                                "query_zh": ["高德地图 官方 新功能"],
                                "query_en": [],
                                "source_layers": ["official"],
                                "expected_evidence": ["官方发布时间"],
                                "source_id_prefix": "OFF",
                            }
                        ],
                    }
                },
            }
            state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

            fake_fragment = {
                "node_id": "official_source_hunter",
                "execution_status": "completed",
                "task_ids": ["OFF-T001"],
                "sources": [{"source_id": "OFF001", "url": "https://example.com"}],
                "warnings": [],
            }
            with patch("search_agent.SourceHunterExecutor") as executor_class:
                executor_class.return_value.run_hunter.return_value = fake_fragment
                with patch("builtins.print") as mocked_print:
                    returned_fragment = agent.execute_source_hunter(
                        "official_source_hunter",
                        str(state_file),
                        limit_per_query=2,
                    )

            saved = json.loads(state_file.read_text(encoding="utf-8"))
            printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)

        self.assertEqual(returned_fragment, fake_fragment)
        executor_class.return_value.run_hunter.assert_called_once()
        _, call_kwargs = executor_class.return_value.run_hunter.call_args
        self.assertEqual(call_kwargs["limit_per_query"], 2)
        self.assertEqual(saved["artifacts"]["SourceListFragment"], [fake_fragment])
        self.assertIn("Source Hunter Executed", printed)
        self.assertIn("sources: 1", printed)

    def test_cli_source_hunter_requires_search_plan(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "search_agent_state.json"
            state_file.write_text(json.dumps({"artifacts": {}}, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(ValueError) as context:
                agent.execute_source_hunter("official_source_hunter", str(state_file))

        self.assertIn("SearchPlan", str(context.exception))

    def test_cli_can_execute_all_source_hunters_and_persist_fragments(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "search_agent_state.json"
            state = {
                "schema_version": "workflow_state.v1",
                "status": "ready_for_execution",
                "current_phase": "step1_parallel_source_hunting",
                "pending_gate": "source_list_fragment_valid",
                "artifacts": {
                    "SearchPlan": {
                        "frameworks": ["同行竞争对比"],
                        "tasks": [
                            {
                                "task_id": "ALL-T001",
                                "assigned_hunter": "official_source_hunter",
                                "dimension": "全量检索",
                                "query_zh": ["高德地图 新功能"],
                                "query_en": ["AAPL stock price"],
                                "source_layers": ["official"],
                                "expected_evidence": ["来源"],
                                "source_id_prefix": "OFF",
                            }
                        ],
                    }
                },
            }
            state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

            def fake_fragment(hunter_id, search_plan, limit_per_query):
                return {
                    "node_id": hunter_id,
                    "execution_status": "completed",
                    "task_ids": [],
                    "sources": [],
                    "warnings": [],
                }

            with patch("search_agent.SourceHunterExecutor") as executor_class:
                executor_class.return_value.run_hunter.side_effect = fake_fragment
                with patch("builtins.print") as mocked_print:
                    fragments = agent.execute_all_source_hunters(
                        str(state_file),
                        limit_per_query=2,
                    )

            saved = json.loads(state_file.read_text(encoding="utf-8"))
            printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)

        self.assertEqual(len(fragments), 6)
        self.assertEqual(executor_class.return_value.run_hunter.call_count, 6)
        self.assertEqual(len(saved["artifacts"]["SourceListFragment"]), 6)
        self.assertIn("All Source Hunters Executed", printed)
        self.assertIn("official_source_hunter", printed)
        self.assertIn("marketing_intelligence_hunter", printed)

    def test_cli_can_continue_workflow_from_source_fragments(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "search_agent_state.json"
            state = agent.start_gate_workflow(
                "高德地图最近三个月上新，对百度地图市场组有什么启示",
                str(state_file),
            )
            state["artifacts"]["SearchPlan"] = {
                "frameworks": ["同行竞争对比"],
                "tasks": [
                    {
                        "task_id": "RSS-T001",
                        "assigned_hunter": "rss_news_hunter",
                        "dimension": "RSS",
                        "query_zh": ["高德地图 新功能"],
                        "query_en": [],
                        "source_layers": ["rss"],
                        "expected_evidence": ["RSS"],
                        "source_id_prefix": "RSS",
                    }
                ],
            }
            state["artifacts"]["SourceListFragment"] = [
                {
                    "node_id": "rss_news_hunter",
                    "execution_status": "completed",
                    "task_ids": ["RSS-T001"],
                    "sources": [
                        {
                            "source_id": "RSS001",
                            "title": "高德地图新功能报道",
                            "publisher": "示例媒体",
                            "source_type": "rss_news",
                            "publish_date": "2026-07-10",
                            "url": "https://example.com/amap",
                            "canonical_url": "https://example.com/amap",
                            "confidence": "medium",
                            "key_facts": ["高德地图上线新功能。"],
                            "full_text_fetched": False,
                            "collected_by": "RSS/News Hunter",
                            "confidence_rationale": "test source",
                        }
                    ],
                    "warnings": [],
                }
            ]
            state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

            with patch("builtins.print") as mocked_print:
                continued = agent.continue_workflow_from_sources(str(state_file))

            saved = json.loads(state_file.read_text(encoding="utf-8"))
            printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)

        self.assertEqual(continued["pending_gate"], "outline_approved_by_user")
        self.assertEqual(saved["artifacts"]["RawSourceList"]["source_count"], 1)
        self.assertIn("Workflow Continued From Source Fragments", printed)
        self.assertIn("raw_sources: 1", printed)

    def test_cli_can_print_codex_execution_model(self):
        agent = SearchAgentSkill()

        with patch("builtins.print") as mocked_print:
            agent.print_codex_execution_model()

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("# Codex-Native Execution Model", printed)
        self.assertIn("LLM 调用方式", printed)
        self.assertIn("不需要为节点 LLM 另配 OpenAI API Key", printed)
        self.assertIn("~/.codex/skills/search-agent", printed)

    def test_extracts_map_competitors_from_query(self):
        agent = SearchAgentSkill()

        params = agent._extract_params_from_query(
            "高德地图最近三个月上了什么新功能，对百度地图有什么启示"
        )

        self.assertEqual(params["主题"], "高德地图")
        self.assertEqual(params["公司名"], "高德地图")
        self.assertEqual(params["公司A"], "高德地图")
        self.assertEqual(params["公司B"], "百度地图")
        self.assertIn("百度地图", params["竞争对手"])
        self.assertEqual(params["行业"], "地图导航")

    def test_output_dir_uses_environment_override(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            previous = os.environ.get("SEARCH_AGENT_OUTPUT_DIR")
            os.environ["SEARCH_AGENT_OUTPUT_DIR"] = temp_dir
            try:
                self.assertEqual(agent._get_output_dir(), temp_dir)
            finally:
                if previous is None:
                    os.environ.pop("SEARCH_AGENT_OUTPUT_DIR", None)
                else:
                    os.environ["SEARCH_AGENT_OUTPUT_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
