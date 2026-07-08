import os
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

    def test_cli_can_run_workflow_dry_run(self):
        agent = SearchAgentSkill()

        with patch("builtins.print") as mocked_print:
            agent.run_workflow_dry_run("高德地图最近三个月上新，对百度地图市场组有什么启示")

        printed = "\n".join(str(call.args[0]) for call in mocked_print.call_args_list if call.args)
        self.assertIn("Multi-Agent Workflow Dry Run", printed)
        self.assertIn("step0_intent_and_audit", printed)
        self.assertIn("step3_humanizer_final", printed)
        self.assertIn("FinalReport", printed)
        self.assertIn("status: complete", printed)

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
