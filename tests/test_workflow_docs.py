import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class WorkflowDocsTest(unittest.TestCase):
    def test_agent_nodes_define_llm_and_subagent_contracts(self):
        doc_path = REPO_ROOT / "references" / "agent-nodes.md"
        text = doc_path.read_text(encoding="utf-8")

        required_terms = [
            "LLM 语义理解层",
            "规则/关键词分类器",
            "专家 skill 前置探针",
            "语义信号",
            "不是封闭枚举",
            "Intent Router Agent",
            "Search Planner Agent",
            "Source Hunter Agent",
            "Framework Analyst Agent",
            "Citation Auditor Agent",
            "Outline Architect Agent",
            "Human Outline Approval Gate",
            "Report Writer Agent",
            "Outline Compliance Auditor Agent",
            "Humanizer Editor Agent",
            "ApprovedOutline",
            "去 AI 味",
        ]

        for term in required_terms:
            self.assertIn(term, text)

    def test_primary_skill_and_agents_reference_agent_nodes(self):
        skill_text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        for text in (skill_text, agents_text):
            self.assertIn("references/agent-nodes.md", text)
            self.assertIn("references/node-playbook.md", text)
            self.assertIn("lib/workflow_contracts.py", text)
            self.assertIn("LLM 语义理解", text)
            self.assertIn("专家 skill 前置", text)

    def test_agent_nodes_reference_executable_contract_fields(self):
        text = (REPO_ROOT / "references" / "agent-nodes.md").read_text(encoding="utf-8")

        for term in [
            "lib/workflow_contracts.py",
            "lib/workflow_orchestrator.py",
            "get_artifact_contracts",
            "build_agent_prompt",
            "get_orchestration_plan",
            "Media Source Hunter",
            "input_artifact",
            "llm_judgment",
            "tool_or_skill_use",
            "output_artifact",
            "quality_gate",
            "hard_constraints",
        ]:
            self.assertIn(term, text)

    def test_node_playbook_documents_every_subagent_progression(self):
        text = (REPO_ROOT / "references" / "node-playbook.md").read_text(encoding="utf-8")

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
            self.assertIn(f"## {node_name}", text)

        for label in [
            "**输入**",
            "**职责边界**",
            "**LLM判断**",
            "**skill/tool调用**",
            "**可做**",
            "**不可做**",
            "**输出artifact**",
            "**进入下一步条件**",
        ]:
            self.assertIn(label, text)

    def test_report_templates_and_social_policy_are_documented(self):
        report_text = (REPO_ROOT / "references" / "report-templates.md").read_text(encoding="utf-8")
        social_text = (REPO_ROOT / "references" / "social-ugc-policy.md").read_text(encoding="utf-8")

        for term in [
            "百度地图市场组",
            "竞品动态简报",
            "市场响应建议",
            "报告不是固定模板",
            "source_id",
            "去 AI 味",
        ]:
            self.assertIn(term, report_text)

        for term in [
            "B站",
            "社媒",
            "卡点",
            "低置信度",
            "交叉验证",
            "不抓取隐私",
        ]:
            self.assertIn(term, social_text)

    def test_team_workflow_guide_explains_business_user_flow(self):
        text = (REPO_ROOT / "references" / "team-workflow-guide.md").read_text(encoding="utf-8")

        for term in [
            "Search Agent 团队使用说明",
            "T1",
            "T9",
            "审核卡片",
            "Source Pack",
            "Source QA",
            "Citation Auditor",
            "Humanizer",
            "确认闸门",
            "同事最常用的提示词模板",
            "AI 不能替你批准发布或归档",
        ]:
            self.assertIn(term, text)

    def test_usage_documents_workflow_dry_run_command(self):
        text = (REPO_ROOT / "USAGE.md").read_text(encoding="utf-8")

        self.assertIn("--workflow-dry-run", text)
        self.assertIn("--workflow-playbook", text)
        self.assertIn("--codex-execution", text)
        self.assertIn("--workflow-start", text)
        self.assertIn("--workflow-resume", text)
        self.assertIn("--workflow-packets", text)
        self.assertIn("source_qa_conflict_resolution", text)
        self.assertIn("SourceList Merger", text)
        self.assertIn("IntegrityDiff", text)
        self.assertIn("Multi-Agent Workflow Dry Run", text)
        self.assertIn("Codex 里不需要为节点 LLM 另配 OpenAI API Key", text)

    def test_usage_explains_user_does_not_need_to_name_subagents(self):
        text = (REPO_ROOT / "USAGE.md").read_text(encoding="utf-8")

        self.assertIn("不需要在提示词里手动写", text)
        self.assertIn("sub agent", text)
        self.assertIn("先输出审核卡", text)
        self.assertIn("确认后再继续", text)

    def test_install_script_checks_codex_execution_reference(self):
        text = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn("codex-execution.md", text)

    def test_codex_execution_doc_explains_llm_runtime_and_install(self):
        text = (REPO_ROOT / "references" / "codex-execution.md").read_text(encoding="utf-8")

        self.assertIn("Codex-Native Execution Model", text)
        self.assertIn("LLM 调用方式", text)
        self.assertIn("不需要为节点 LLM 另配 OpenAI API Key", text)
        self.assertIn("~/.codex/skills/search-agent", text)
        self.assertIn("--workflow-dry-run", text)

    def test_primary_docs_reference_codex_execution_model(self):
        skill_text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        for text in (skill_text, agents_text):
            self.assertIn("references/codex-execution.md", text)


if __name__ == "__main__":
    unittest.main()
