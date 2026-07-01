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
from intent_classifier import classify_intent
from framework_combinator import FrameworkCombinator, recommend_framework_combination
from search_engine import SearchEngine
from report_generator import ReportGenerator


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
        print("Step 1: 分析用户意图,推荐分析框架...\n")
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
        output_dir = "/home/gem/workspace/.ark/output/search-agent-skill_2026-07-01"
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
        if "高德" in user_query:
            params["主题"] = "高德地图"
            params["公司名"] = "高德地图"
        elif "百度" in user_query:
            params["主题"] = "百度"
            params["公司名"] = "百度"
        else:
            params["主题"] = "未知主题"

        # 提取时间
        if "2026" in user_query:
            if "Q1" in user_query:
                params["期间"] = "2026Q1"
            elif "Q2" in user_query:
                params["期间"] = "2026Q2"
            else:
                params["期间"] = "2026"

        return params

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
    parser.add_argument("query", type=str, help="用户问题")
    parser.add_argument("--auto", action="store_true", help="自动确认框架,跳过人工审核")

    args = parser.parse_args()

    agent = SearchAgentSkill()
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
