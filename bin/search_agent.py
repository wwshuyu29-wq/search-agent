#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search Agent 智能分析系统 - 主入口
基于财报分析 Workflow v2.0 设计理念,扩展为通用的多场景分析系统

功能:
1. 意图识别: 自动识别用户问题类型,推荐合适的分析框架
2. 框架选择: 支持人工审核,确认分析框架
3. 多源搜索: 并行调用 baidu-search、realtime-search、enterprise-search
4. 内容处理: 支持 PDF、HTML、知识库文档等多种格式
5. 报告生成: 按框架结构化输出,每个关键论断附带引文链接
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict

# 添加 lib 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from frameworks import ANALYSIS_FRAMEWORKS, get_framework_by_name, get_search_keywords
from intent_classifier import build_step0_context, classify_intent
from framework_combinator import FrameworkCombinator, recommend_framework_combination
from search_engine import SearchEngine
from report_generator import ReportGenerator
from source_hunter_executor import HUNTER_CONFIG, SourceHunterExecutor
from workflow_contracts import (
    render_codex_execution_markdown,
    render_skill_adapter_matrix_markdown,
    render_skill_coverage_audit_markdown,
    render_skill_invocation_registry_markdown,
    render_workflow_playbook_markdown,
)
from workflow_orchestrator import WorkflowOrchestrator


class SearchAgentSkill:
    """Search Agent 智能分析系统"""

    def __init__(self):
        self.search_engine = SearchEngine()
        self.report_generator = ReportGenerator()
        self.framework_combinator = FrameworkCombinator()

    def run(self, user_query: str, auto_confirm: bool = False):
        """
        主流程

        Args:
            user_query: 用户问题
            auto_confirm: 是否自动确认框架(默认False,需要人工审核)
        """
        print(f"\n{'='*60}")
        print(f"Search Agent 智能分析系统")
        print(f"{'='*60}\n")

        print(f"【用户问题】: {user_query}\n")

        # Step 1: 意图识别,推荐分析框架
        print("Step 0: LLM 语义理解 + 专家 skill 前置 + 规则分类校验...\n")
        step0_context = build_step0_context(user_query)
        self._print_step0_audit_context(step0_context)

        if step0_context.get("short_circuit"):
            print("检测到单一数字/结构化数据查询，建议直接调用专家数据 skill 后结束。")
            print("如仍需完整调研报告，请重新运行并明确说明需要分析。\n")
            print("已停止完整调研流程。")
            return

        print("规则/关键词分类器校验框架推荐...\n")
        recommendations = classify_intent(user_query, top_k=3, return_complexity=True)

        if not recommendations:
            print("❌ 无法识别用户意图,请提供更具体的问题描述")
            return

        # 检查问题复杂度
        is_complex = recommendations[0].get("is_complex_problem", False)

        if is_complex:
            print("⚠️  检测到这是一个复杂问题,可能需要组合多个分析框架")
            print("正在为您推荐框架组合...\n")

            # 推荐框架组合
            combination_recommendations = self.framework_combinator.recommend_combination(
                user_query, recommendations
            )

            if combination_recommendations:
                print("推荐的框架组合:\n")
                for idx, combo in enumerate(combination_recommendations, 1):
                    print(f"{idx}. **{combo['combination_name']}**")
                    print(f"   包含框架: {' → '.join(combo['execution_order'])}")
                    print(f"   描述: {combo['description']}")
                    print(f"   说明: {combo['说明']}")
                    print()

                print("也可以选择单个框架:\n")

        print("推荐的单个分析框架:\n")
        for idx, rec in enumerate(recommendations, 1):
            fw_name = rec["framework"]
            fw_info = get_framework_by_name(fw_name)
            print(f"{idx}. **{fw_name}**")
            print(f"   描述: {fw_info['description']}")
            print(f"   匹配理由: {rec['reason']}")
            print(f"   适用场景: {', '.join(fw_info['适用场景'])}")
            print()

        # Step 2: 人工审核点① - 确认框架
        if not auto_confirm:
            print("\n【人工审核点①】请选择分析方式:")

            if is_complex and combination_recommendations:
                print("输入 'C1', 'C2', 'C3'... 选择框架组合")

            print("或输入 '1', '2', '3'... 选择单个框架")
            print("输入 'q' 退出")

            selected = input("\n请选择: ").strip()

            if selected.lower() == 'q':
                print("已取消分析")
                return

            # 解析用户选择
            if selected.startswith('C') or selected.startswith('c'):
                # 选择了框架组合
                try:
                    combo_idx = int(selected[1:])
                    if combo_idx < 1 or combo_idx > len(combination_recommendations):
                        print("❌ 无效的选择")
                        return

                    selected_combo = combination_recommendations[combo_idx - 1]
                    selected_frameworks = selected_combo["execution_order"]
                    is_combination = True
                    combination_name = selected_combo["combination_name"]

                except ValueError:
                    print("❌ 无效的输入")
                    return
            else:
                # 选择了单个框架
                try:
                    fw_idx = int(selected)
                    if fw_idx < 1 or fw_idx > len(recommendations):
                        print("❌ 无效的选择")
                        return

                    selected_frameworks = [recommendations[fw_idx - 1]["framework"]]
                    is_combination = False
                    combination_name = None

                except ValueError:
                    print("❌ 无效的输入")
                    return
        else:
            # 自动选择
            if is_complex and combination_recommendations:
                # 复杂问题自动选择第一个组合
                selected_frameworks = combination_recommendations[0]["execution_order"]
                is_combination = True
                combination_name = combination_recommendations[0]["combination_name"]
            else:
                # 简单问题自动选择第一个单框架
                selected_frameworks = [recommendations[0]["framework"]]
                is_combination = False
                combination_name = None

        if is_combination:
            print(f"\n✅ 已确认使用框架组合: **{combination_name}**")
            print(f"   执行顺序: {' → '.join(selected_frameworks)}\n")
        else:
            print(f"\n✅ 已确认使用框架: **{selected_frameworks[0]}**\n")

        # Step 3: 按顺序执行框架分析
        print("Step 2: 执行分析...\n")

        all_content_pools = []
        all_citations = {}

        for framework_name in selected_frameworks:
            print(f"\n--- 执行框架: {framework_name} ---\n")

            # 拆解搜索任务
            print(f"[{framework_name}] 拆解搜索任务...\n")
            framework_info = get_framework_by_name(framework_name)

            # 解析用户问题,提取参数 (简化版)
            params = self._extract_params_from_query(user_query)
            print(f"提取的参数: {json.dumps(params, ensure_ascii=False, indent=2)}\n")

            # 生成搜索关键词
            search_keywords_by_dimension = get_search_keywords(framework_name, **params)

            print("各维度的搜索关键词:\n")
            for dimension, keywords in search_keywords_by_dimension.items():
                print(f"  [{dimension}]")
                for kw in keywords[:3]:  # 只显示前3个
                    print(f"    - {kw}")
            print()

            # 多源搜索
            print(f"[{framework_name}] 执行多源搜索...\n")
            all_keywords = []
            for keywords in search_keywords_by_dimension.values():
                all_keywords.extend(keywords[:2])  # 每个维度取前2个关键词

            # 调用更新后的搜索引擎 (返回 tuple)
            fw_content_pool, fw_citations = self.search_engine.multi_source_search(
                keywords=all_keywords,
                framework_name=framework_name,
                params=params,
                max_results_per_keyword=5,
                enable_layered_search=True  # 启用分层搜索
            )
            print(f"✅ 搜索完成,共找到 {len(fw_content_pool)} 条结果\n")

            # 内容抓取
            print(f"[{framework_name}] 抓取内容并处理...\n")

            for idx, item in enumerate(fw_content_pool[:10], 1):  # 限制处理前10条
                url = item.get("url")
                content_type = self._detect_content_type(url)

                print(f"  [{idx}] 处理 {content_type}: {item['title'][:50]}...")

                # 提取内容
                content_data = self.search_engine.extract_content_from_url(url, content_type)

                # 更新 item 的 content 字段
                item["content"] = content_data.get("content", "")

            print(f"\n✅ [{framework_name}] 内容处理完成,共处理 {len(fw_content_pool[:10])} 条内容\n")

            all_content_pools.extend(fw_content_pool[:10])
            all_citations.update(fw_citations)

        # Step 4: 生成综合报告
        print("Step 3: 生成分析报告...\n")

        subject = params.get("主题", "未知主题")

        if is_combination:
            # 组合分析报告
            report_content = self._generate_combination_report(
                combination_name=combination_name,
                frameworks=selected_frameworks,
                subject=subject,
                content_pool=all_content_pools,
                citations=all_citations,
                params=params
            )
        else:
            # 单框架报告
            report_content = self.report_generator.generate_report(
                framework_name=selected_frameworks[0],
                subject=subject,
                content_pool=all_content_pools,
                citations=all_citations,
                period=params.get("期间", "N/A")
            )

        # Step 7: 输出报告
        output_dir = self._get_output_dir()
        os.makedirs(output_dir, exist_ok=True)

        if is_combination:
            report_filename = f"{subject}_{combination_name.replace(' ', '_')}_{params.get('期间', 'latest')}.md"
        else:
            report_filename = f"{subject}_{selected_frameworks[0]}_{params.get('期间', 'latest')}.md"

        report_path = os.path.join(output_dir, report_filename)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"✅ 报告已生成: {report_path}\n")

        # Step 8: 人工审核点② (此处简化,实际应等待用户反馈)
        print("【人工审核点②】请校验报告的引文和结论")
        print(f"报告路径: {report_path}\n")

        # 可选: 导出为 Word
        # word_path = report_path.replace(".md", ".docx")
        # self.report_generator.export_to_word(report_content, word_path)

        print(f"{'='*60}")
        print("分析完成!")
        print(f"{'='*60}\n")

    def print_workflow_playbook(self):
        """Print the full multi-agent node playbook."""
        print(render_workflow_playbook_markdown())

    def print_codex_execution_model(self):
        """Print how the workflow runs inside Codex."""
        print(render_codex_execution_markdown())

    def print_skill_invocation_registry(self):
        """Print the node-by-node skill invocation registry."""
        print(render_skill_invocation_registry_markdown())

    def print_skill_coverage_audit(self):
        """Print the discovered-vs-registered skill coverage audit."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        print(render_skill_coverage_audit_markdown(repo_root))

    def print_skill_adapter_matrix(self, domain: str = ""):
        """Print fine-grained skill adapter logic."""
        print(render_skill_adapter_matrix_markdown(domain))

    def run_workflow_dry_run(self, user_query: str):
        """Run the artifact-only multi-agent workflow for validation."""
        orchestrator = WorkflowOrchestrator()
        result = orchestrator.run_dry_workflow(user_query)

        print("Multi-Agent Workflow Dry Run")
        print(f"status: {result['status']}")
        print(f"valid: {result['valid']}")
        print("\nPhases:")
        for phase in result["phase_results"]:
            print(
                "- {id} | nodes={nodes} | gate={gate} | outputs={outputs}".format(
                    id=phase["id"],
                    nodes=", ".join(phase["nodes"]),
                    gate=phase["gate"],
                    outputs=", ".join(phase["output_artifacts"]),
                )
            )

        print("\nArtifact validations:")
        for validation in result["validations"]:
            status = "ok" if validation["valid"] else "blocked"
            print(f"- {validation['artifact']}: {status}")
            if validation["missing_fields"]:
                print(f"  missing: {', '.join(validation['missing_fields'])}")

        final_report = result["artifacts"].get("FinalReport")
        if final_report:
            print("\nFinalReport:")
            print(final_report["markdown"])

    def start_gate_workflow(self, user_query: str, state_file: str = "search_agent_state.json") -> Dict:
        """Start the formal gate-driven workflow and persist the pending audit state."""
        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(user_query)
        self._write_workflow_state(state, state_file)

        audit_card = state["artifacts"]["AuditCard"]
        print("Gate-Driven Workflow Started")
        print("status: 等待用户确认")
        print(f"pending_gate: {state['pending_gate']}")
        print(f"state_file: {state_file}")
        print("\nAuditCard:")
        print(json.dumps(audit_card, ensure_ascii=False, indent=2))
        print(f"\n下一步: {state['next_action']}")
        return state

    def resume_gate_workflow(self, user_decision: str, state_file: str = "search_agent_state.json") -> Dict:
        """Resume a persisted gate-driven workflow from a user decision."""
        orchestrator = WorkflowOrchestrator()
        previous_state = self._read_workflow_state(state_file)
        state = orchestrator.resume_gate_workflow(previous_state, user_decision)
        self._write_workflow_state(state, state_file)

        print("Gate-Driven Workflow Resumed")
        print(f"status: {state['status']}")
        print(f"pending_gate: {state['pending_gate']}")
        print(f"state_file: {state_file}")

        if state["pending_gate"] == "final_report_review":
            print("status_label: 等待终稿审核")
            final_report = state["artifacts"].get("FinalReport", {})
            if final_report.get("markdown"):
                print("\nFinalReport:")
                print(final_report["markdown"])
        elif state["status"] == "complete":
            print("status_label: 已完成")
        elif state["status"] == "revision_requested":
            print("status_label: 等待修订")

        print(f"\n下一步: {state['next_action']}")
        return state

    def print_node_packets(self, phase_id: str, state_file: str = "search_agent_state.json") -> List[Dict]:
        """Print constrained sub-agent execution packets for a workflow phase."""
        orchestrator = WorkflowOrchestrator()
        state = self._read_workflow_state(state_file)
        packets = orchestrator.build_node_packets(phase_id, state.get("artifacts", {}))

        print("Sub-Agent Node Packets")
        print(f"phase_id: {phase_id}")
        print(f"state_file: {state_file}")
        for packet in packets:
            print("\n" + "=" * 60)
            print(f"node_id: {packet['node_id']}")
            print(f"node_name: {packet['node_name']}")
            print(f"parallel: {packet['parallel']}")
            print(f"output_artifact: {packet['output_artifact']}")
            print(f"allowed_tools_or_skills: {packet['allowed_tools_or_skills']}")
            print("skill_invocation_rules:")
            for rule in packet.get("skill_invocation_rules", []):
                print(
                    "  - {skill} | type={kind} | evidence_role={role} | can_support_claim={claim}".format(
                        skill=rule["skill_or_tool"],
                        kind=rule["invocation_type"],
                        role=rule["evidence_role"],
                        claim=rule["can_directly_support_claim"],
                    )
                )
            print("\nPrompt:")
            print(packet["prompt"])
        return packets

    def execute_source_hunter(
        self,
        hunter_id: str,
        state_file: str = "search_agent_state.json",
        limit_per_query: int = 5,
    ) -> Dict:
        """Execute one real Source Hunter vertical slice and persist its fragment."""
        state = self._read_workflow_state(state_file)
        artifacts = state.setdefault("artifacts", {})
        search_plan = artifacts.get("SearchPlan")
        if not search_plan:
            raise ValueError("SearchPlan artifact is required before executing a Source Hunter")

        executor = SourceHunterExecutor()
        fragment = executor.run_hunter(
            hunter_id,
            search_plan,
            limit_per_query=limit_per_query,
        )

        existing_fragments = artifacts.get("SourceListFragment", [])
        if isinstance(existing_fragments, dict):
            existing_fragments = [existing_fragments]
        existing_fragments = [
            item for item in existing_fragments
            if item.get("node_id") != hunter_id
        ]
        existing_fragments.append(fragment)
        artifacts["SourceListFragment"] = existing_fragments
        state["current_phase"] = "step1_parallel_source_hunting"
        state["updated_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        self._write_workflow_state(state, state_file)

        print("Source Hunter Executed")
        print(f"node_id: {hunter_id}")
        print(f"status: {fragment['execution_status']}")
        print(f"sources: {len(fragment.get('sources', []))}")
        print(f"state_file: {state_file}")
        if fragment.get("warnings"):
            print("warnings:")
            for warning in fragment["warnings"]:
                print(f"- {warning}")
        return fragment

    def execute_all_source_hunters(
        self,
        state_file: str = "search_agent_state.json",
        limit_per_query: int = 5,
    ) -> List[Dict]:
        """Execute every Source Hunter node and persist all fragments."""
        state = self._read_workflow_state(state_file)
        artifacts = state.setdefault("artifacts", {})
        search_plan = artifacts.get("SearchPlan")
        if not search_plan:
            raise ValueError("SearchPlan artifact is required before executing Source Hunters")

        executor = SourceHunterExecutor()
        fragments = []
        for hunter_id in HUNTER_CONFIG:
            fragments.append(
                executor.run_hunter(
                    hunter_id,
                    search_plan,
                    limit_per_query=limit_per_query,
                )
            )

        artifacts["SourceListFragment"] = fragments
        state["current_phase"] = "step1_parallel_source_hunting"
        state["updated_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        self._write_workflow_state(state, state_file)

        print("All Source Hunters Executed")
        print(f"state_file: {state_file}")
        for fragment in fragments:
            print(
                "- {node_id}: {status}, sources={source_count}, warnings={warning_count}".format(
                    node_id=fragment["node_id"],
                    status=fragment["execution_status"],
                    source_count=len(fragment.get("sources", [])),
                    warning_count=len(fragment.get("warnings", [])),
                )
            )
        return fragments

    def continue_workflow_from_sources(self, state_file: str = "search_agent_state.json") -> Dict:
        """Continue the workflow after real Source Hunter fragments are written."""
        orchestrator = WorkflowOrchestrator()
        previous_state = self._read_workflow_state(state_file)
        state = orchestrator.continue_from_source_fragments(previous_state)
        self._write_workflow_state(state, state_file)

        print("Workflow Continued From Source Fragments")
        print(f"status: {state['status']}")
        print(f"pending_gate: {state['pending_gate']}")
        print(f"state_file: {state_file}")
        raw_source_list = state["artifacts"].get("RawSourceList", {})
        print(f"raw_sources: {raw_source_list.get('source_count', 0)}")
        final_report = state["artifacts"].get("FinalReport", {})
        if final_report.get("markdown"):
            print("\nFinalReport:")
            print(final_report["markdown"])
        print(f"\n下一步: {state['next_action']}")
        return state

    def _write_workflow_state(self, state: Dict, state_file: str):
        with open(state_file, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)

    def _read_workflow_state(self, state_file: str) -> Dict:
        with open(state_file, "r", encoding="utf-8") as file:
            return json.load(file)

    def _print_step0_audit_context(self, step0_context: Dict):
        """Print Step 0 semantic fields and expert skill probes for CLI users."""
        fields = step0_context.get("semantic_fields", {})
        print("Step 0 决策栈:")
        for idx, item in enumerate(step0_context.get("decision_stack", []), 1):
            print(f"  {idx}. {item}")
        print("\nLLM 语义理解字段（CLI 为启发式兜底，Codex 原生需用 LLM 判断）:")
        for key in [
            "research_object",
            "user_decision",
            "audience",
            "time_scope",
            "output_shape",
            "evidence_need",
            "ambiguity",
        ]:
            print(f"  - {key}: {fields.get(key)}")

        preflight_skills = step0_context.get("preflight_skills", [])
        print("\n专家 skill 前置建议:")
        if not preflight_skills:
            print("  - 无强制前置 skill；进入框架路由")
        else:
            for skill in preflight_skills:
                print(f"  - {skill['skill']} ({skill['step']}): {skill['reason']}")

        report_family = step0_context.get("report_family") or {}
        if report_family:
            print("\n建议报告形态:")
            print(f"  - {report_family.get('name')} ({report_family.get('id')})")
            print(f"  - 结构逻辑: {report_family.get('shape')}")

        node_chain_preview = step0_context.get("node_chain_preview") or []
        if node_chain_preview:
            print("\n后续子 agent 链（确认后按此推进）:")
            for idx, node_summary in enumerate(node_chain_preview, 1):
                print(f"  {idx}. {node_summary}")
        print("\n分类说明:")
        print("  - CLI 只输出语义字段和规则信号；Codex 原生执行时必须用 LLM 复核整句意图。")
        print("  - 增长类、单一金融数字、竞品、营销方案等不是靠固定关键词封闭判断。")
        print()

    def _generate_combination_report(
        self,
        combination_name: str,
        frameworks: List[str],
        subject: str,
        content_pool: List[Dict],
        citations: Dict[str, str],
        params: dict
    ) -> str:
        """
        生成框架组合分析报告

        将多个框架的分析结果整合到一个报告中
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# {subject} - {combination_name}分析报告

**分析对象**: {subject}
**分析框架组合**: {' → '.join(frameworks)}
**生成时间**: {timestamp}

---

## 执行摘要

本报告采用 **{combination_name}**,依次执行 {len(frameworks)} 个分析框架:

"""

        for idx, fw in enumerate(frameworks, 1):
            fw_info = get_framework_by_name(fw)
            report += f"{idx}. **{fw}**: {fw_info['description']}\n"

        report += "\n---\n\n"

        # 按框架生成各章节
        for fw_name in frameworks:
            report += f"## 第{frameworks.index(fw_name)+1}部分: {fw_name}分析\n\n"

            # 筛选该框架的内容
            fw_content_pool = [c for c in content_pool if c.get("framework") == fw_name]

            # 生成该框架的报告片段 (简化版)
            report += f"### {fw_name}的分析维度\n\n"
            report += f"待填充: 基于{len(fw_content_pool)}条内容生成分析...\n\n"

        # 生成综合结论
        report += "## 综合结论与建议\n\n"
        report += "待填充: 基于多框架分析的综合结论...\n\n"

        # 生成来源列表
        report += "## 来源\n\n"
        for idx, (source_id, url) in enumerate(citations.items(), 1):
            report += f"- [{idx}] {url}\n"

        return report

    def _extract_params_from_query(self, user_query: str) -> dict:
        """
        从用户问题中提取参数 (简化版NER)

        实际应使用NER或正则提取:
        - 公司名/产品名
        - 时间期间 (2026Q1、2026年等)
        - 竞争对手
        """
        params = {}

        # 简化实现: 使用关键词匹配
        map_products = ["高德地图", "百度地图", "腾讯地图", "Apple Maps", "Google Maps", "Waze"]
        mentioned_map_products = [product for product in map_products if product in user_query]

        if mentioned_map_products:
            primary = mentioned_map_products[0]
            params["主题"] = primary
            params["公司名"] = primary
            params["公司A"] = primary
            params["行业"] = "地图导航"
            competitors = [product for product in mentioned_map_products[1:] if product != primary]
            if competitors:
                params["竞争对手"] = competitors
                params["公司B"] = competitors[0]
        elif "高德" in user_query:
            params["主题"] = "高德地图"
            params["公司名"] = "高德地图"
            params["公司A"] = "高德地图"
            params["行业"] = "地图导航"
        elif "百度" in user_query:
            params["主题"] = "百度"
            params["公司名"] = "百度"
        else:
            params["主题"] = "未知主题"

        # 提取时间
        if "最近三个月" in user_query:
            params["期间"] = "最近三个月"
        elif "2026" in user_query:
            if "Q1" in user_query:
                params["期间"] = "2026Q1"
            elif "Q2" in user_query:
                params["期间"] = "2026Q2"
            else:
                params["期间"] = "2026"

        return params

    def _get_output_dir(self) -> str:
        """获取报告输出目录，优先使用环境变量，其次读取配置文件。"""
        env_output_dir = os.getenv("SEARCH_AGENT_OUTPUT_DIR")
        if env_output_dir:
            return env_output_dir

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        config_path = os.path.join(repo_root, "config", "settings.json")
        default_output_dir = os.path.join(repo_root, "output")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            configured_output_dir = settings.get("report", {}).get("output_dir")
        except (OSError, json.JSONDecodeError):
            configured_output_dir = None

        if not configured_output_dir:
            return default_output_dir

        if os.path.isabs(configured_output_dir):
            return configured_output_dir

        return os.path.abspath(os.path.join(repo_root, configured_output_dir))

    def _detect_content_type(self, url: str) -> str:
        """检测URL对应的内容类型"""
        if ".pdf" in url.lower():
            return "pdf"
        elif "ku.baidu-int.com" in url:
            return "ku_doc"
        else:
            return "html"


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Search Agent 智能分析系统")
    parser.add_argument("query", type=str, nargs="?", help="用户问题")
    parser.add_argument("--auto", action="store_true", help="自动确认框架,跳过人工审核")
    parser.add_argument("--workflow-playbook", action="store_true", help="输出完整子 agent 推进手册")
    parser.add_argument("--skill-registry", action="store_true", help="输出每个节点可调用 skill/tool 的注册表")
    parser.add_argument("--skill-coverage", action="store_true", help="输出本地开源/外部 skill 的覆盖审计")
    parser.add_argument("--skill-adapter-matrix", nargs="?", const="all", choices=["all", "marketing", "finance"], help="输出细分 skill 适配矩阵")
    parser.add_argument("--workflow-dry-run", action="store_true", help="运行 artifact-only 多 agent 工作流自检")
    parser.add_argument("--workflow-start", action="store_true", help="启动正式 gate-driven workflow，输出审核卡后暂停")
    parser.add_argument("--workflow-resume", type=str, help="根据用户确认/修订意见恢复 gate-driven workflow")
    parser.add_argument("--workflow-packets", type=str, help="输出某个 phase 的可派发子 agent packet")
    parser.add_argument("--execute-source-hunter", type=str, help="执行指定 Source Hunter 节点并写回 SourceListFragment")
    parser.add_argument("--execute-source-hunters", action="store_true", help="执行全部 Source Hunter 节点并写回 SourceListFragment")
    parser.add_argument("--workflow-continue-from-sources", action="store_true", help="从真实 SourceListFragment 继续合并、QA、分析和报告")
    parser.add_argument("--limit-per-query", type=int, default=5, help="每个检索任务最多返回多少条结果")
    parser.add_argument("--state-file", default="search_agent_state.json", help="gate-driven workflow 状态文件路径")
    parser.add_argument("--codex-execution", action="store_true", help="输出 Codex 内 LLM 调用与团队安装执行模型")

    args = parser.parse_args()

    agent = SearchAgentSkill()
    if args.workflow_playbook:
        agent.print_workflow_playbook()
        return

    if args.skill_registry:
        agent.print_skill_invocation_registry()
        return

    if args.skill_coverage:
        agent.print_skill_coverage_audit()
        return

    if args.skill_adapter_matrix:
        domain = "" if args.skill_adapter_matrix == "all" else args.skill_adapter_matrix
        agent.print_skill_adapter_matrix(domain)
        return

    if args.codex_execution:
        agent.print_codex_execution_model()
        return

    if args.workflow_dry_run:
        if not args.query:
            parser.error("--workflow-dry-run 需要一个用户问题")
        agent.run_workflow_dry_run(args.query)
        return

    if args.workflow_start:
        if not args.query:
            parser.error("--workflow-start 需要一个用户问题")
        agent.start_gate_workflow(args.query, state_file=args.state_file)
        return

    if args.workflow_resume:
        agent.resume_gate_workflow(args.workflow_resume, state_file=args.state_file)
        return

    if args.workflow_packets:
        agent.print_node_packets(args.workflow_packets, state_file=args.state_file)
        return

    if args.execute_source_hunter:
        agent.execute_source_hunter(
            args.execute_source_hunter,
            state_file=args.state_file,
            limit_per_query=args.limit_per_query,
        )
        return

    if args.execute_source_hunters:
        agent.execute_all_source_hunters(
            state_file=args.state_file,
            limit_per_query=args.limit_per_query,
        )
        return

    if args.workflow_continue_from_sources:
        agent.continue_workflow_from_sources(state_file=args.state_file)
        return

    if not args.query:
        parser.error("缺少用户问题；或使用 --workflow-playbook 查看完整子 agent 推进手册")

    agent.run(args.query, auto_confirm=args.auto)


if __name__ == "__main__":
    # 测试用例
    if len(sys.argv) == 1:
        # 如果没有命令行参数,使用测试用例
        test_query = "高德地图上新了什么功能,帮我全网搜索相关的稿件,然后把这些信息汇总成一个方案"
        agent = SearchAgentSkill()
        agent.run(test_query, auto_confirm=False)
    else:
        main()
