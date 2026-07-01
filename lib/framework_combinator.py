#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
框架组合器 - 支持多框架组合分析
基于财报分析 Workflow v2.0 的"默认组合"思路
"""

from typing import List, Dict


class FrameworkCombinator:
    """分析框架组合推荐器"""

    # 预定义的框架组合模板 (参考文档中的默认组合)
    FRAMEWORK_COMBINATIONS = {
        "财报快评组合": {
            "name": "财报快评组合",
            "frameworks": ["财报快评"],
            "core_methods": ["KPI 树", "空-雨-伞"],
            "description": "单家公司财报快速分析",
            "适用场景": ["快速了解公司业绩", "季报速览", "时间紧迫的决策"],
            "execution_order": ["财报快评"],
            "说明": "KPI树拆解指标 + 空-雨-伞从事实到判断"
        },

        "深度财报分析组合": {
            "name": "深度财报分析组合",
            "frameworks": ["深度财报分析", "3C战略三角"],
            "core_methods": ["KPI 树", "3C", "空-雨-伞"],
            "description": "完整的公司经营质量与竞争力分析",
            "适用场景": ["投资决策", "深度研究", "经营质量评估"],
            "execution_order": ["深度财报分析", "3C战略三角"],
            "说明": "先用KPI树+3C做深度财报分析,再用3C分析公司-客户-竞争对手三角"
        },

        "同行对比分析组合": {
            "name": "同行对比分析组合",
            "frameworks": ["同行竞争对比", "3C战略三角", "Porter五力"],
            "core_methods": ["3C", "核心竞争力分析", "Porter五力"],
            "description": "横向对比多家公司的竞争力",
            "适用场景": ["竞品分析", "市场定位", "投资组合对比"],
            "execution_order": ["同行竞争对比", "3C战略三角", "Porter五力"],
            "说明": "先做同行对比,再用3C分析各家定位,最后用五力看行业格局"
        },

        "风险复盘分析组合": {
            "name": "风险复盘分析组合",
            "frameworks": ["风险专项", "SWOT"],
            "core_methods": ["SWOT", "决策矩阵"],
            "description": "全面识别风险并制定应对策略",
            "适用场景": ["风险评估", "危机预警", "战略调整"],
            "execution_order": ["风险专项", "SWOT"],
            "说明": "先识别具体风险,再用SWOT做综合评估和决策"
        },

        "新市场进入组合": {
            "name": "新市场进入组合",
            "frameworks": ["PEST分析", "Porter五力", "SWOT"],
            "core_methods": ["PEST", "Porter五力", "SWOT"],
            "description": "进入新市场前的全面环境与竞争分析",
            "适用场景": ["市场拓展", "战略规划", "新业务评估"],
            "execution_order": ["PEST分析", "Porter五力", "SWOT"],
            "说明": "先看宏观环境(PEST),再看行业竞争(五力),最后综合评估(SWOT)"
        },

        "产品策略组合": {
            "name": "产品策略组合",
            "frameworks": ["3C战略三角", "4P营销", "SWOT"],
            "core_methods": ["3C", "4P", "SWOT"],
            "description": "产品定位与营销策略制定",
            "适用场景": ["产品上市", "营销策划", "市场定位"],
            "execution_order": ["3C战略三角", "4P营销", "SWOT"],
            "说明": "先用3C明确定位(公司-客户-竞争),再用4P设计营销组合,最后SWOT评估"
        },

        "全面战略分析组合": {
            "name": "全面战略分析组合",
            "frameworks": ["PEST分析", "Porter五力", "3C战略三角", "SWOT"],
            "core_methods": ["PEST", "Porter五力", "3C", "SWOT"],
            "description": "从宏观到微观的完整战略分析",
            "适用场景": ["战略规划", "年度复盘", "重大决策"],
            "execution_order": ["PEST分析", "Porter五力", "3C战略三角", "SWOT"],
            "说明": "宏观环境→行业竞争→公司定位→综合评估,层层递进"
        }
    }

    def __init__(self):
        pass

    def recommend_combination(self, user_query: str, single_framework_recommendations: List[Dict]) -> List[Dict]:
        """
        根据用户问题和单框架推荐结果,推荐合适的框架组合

        Args:
            user_query: 用户问题
            single_framework_recommendations: 单框架推荐结果 (来自 IntentClassifier)

        Returns:
            List[Dict]: 推荐的框架组合列表
        """
        recommendations = []
        query_lower = user_query.lower()

        # 规则1: 如果单框架推荐中有财报分析,优先推荐财报组合
        framework_names = [rec["framework"] for rec in single_framework_recommendations]

        if "财报快评" in framework_names:
            recommendations.append(self._build_recommendation("财报快评组合", score=10))

        if "深度财报分析" in framework_names:
            recommendations.append(self._build_recommendation("深度财报分析组合", score=10))

        if "同行竞争对比" in framework_names:
            recommendations.append(self._build_recommendation("同行对比分析组合", score=9))

        # 规则2: 检测关键词
        if any(kw in query_lower for kw in ["风险", "危机", "预警", "隐患"]):
            recommendations.append(self._build_recommendation("风险复盘分析组合", score=8))

        if any(kw in query_lower for kw in ["新市场", "进入", "拓展", "扩张", "开拓"]):
            recommendations.append(self._build_recommendation("新市场进入组合", score=8))

        if any(kw in query_lower for kw in ["产品", "营销", "推广", "上市", "定位"]):
            recommendations.append(self._build_recommendation("产品策略组合", score=7))

        if any(kw in query_lower for kw in ["战略", "规划", "全面", "完整", "系统"]):
            recommendations.append(self._build_recommendation("全面战略分析组合", score=7))

        # 规则3: 如果没有匹配到组合,根据单框架数量决定
        if not recommendations:
            if len(framework_names) >= 2:
                # 如果单框架推荐有多个,尝试自动组合
                auto_combo = self._create_auto_combination(framework_names)
                if auto_combo:
                    recommendations.append(auto_combo)

        # 去重并排序
        seen = set()
        unique_recommendations = []
        for rec in sorted(recommendations, key=lambda x: x["score"], reverse=True):
            if rec["combination_name"] not in seen:
                seen.add(rec["combination_name"])
                unique_recommendations.append(rec)

        return unique_recommendations[:3]  # 最多返回3个组合

    def _build_recommendation(self, combination_name: str, score: int) -> Dict:
        """构建推荐结果"""
        combo = self.FRAMEWORK_COMBINATIONS.get(combination_name)
        if not combo:
            return None

        return {
            "combination_name": combo["name"],
            "frameworks": combo["frameworks"],
            "core_methods": combo["core_methods"],
            "description": combo["description"],
            "execution_order": combo["execution_order"],
            "说明": combo["说明"],
            "score": score,
            "is_combination": True
        }

    def _create_auto_combination(self, framework_names: List[str]) -> Dict:
        """根据单框架列表自动创建组合"""
        if len(framework_names) < 2:
            return None

        # 简单组合: 取前2个框架
        auto_combo = {
            "combination_name": f"{framework_names[0]} + {framework_names[1]}",
            "frameworks": framework_names[:2],
            "core_methods": framework_names[:2],
            "description": "自动组合推荐",
            "execution_order": framework_names[:2],
            "说明": f"先执行{framework_names[0]},再执行{framework_names[1]}",
            "score": 5,
            "is_combination": True
        }

        return auto_combo

    def get_combination_details(self, combination_name: str) -> Dict:
        """获取组合详情"""
        return self.FRAMEWORK_COMBINATIONS.get(combination_name)

    def list_all_combinations(self) -> List[Dict]:
        """列出所有预定义的框架组合"""
        return [
            {
                "name": combo["name"],
                "frameworks": combo["frameworks"],
                "description": combo["description"],
                "适用场景": combo["适用场景"]
            }
            for combo in self.FRAMEWORK_COMBINATIONS.values()
        ]


# 便捷函数
def recommend_framework_combination(user_query: str, single_recommendations: List[Dict]) -> List[Dict]:
    """便捷函数: 推荐框架组合"""
    combinator = FrameworkCombinator()
    return combinator.recommend_combination(user_query, single_recommendations)


if __name__ == "__main__":
    # 测试用例
    combinator = FrameworkCombinator()

    print("=" * 60)
    print("预定义的框架组合:")
    print("=" * 60)
    for combo in combinator.list_all_combinations():
        print(f"\n【{combo['name']}】")
        print(f"  框架: {' + '.join(combo['frameworks'])}")
        print(f"  描述: {combo['description']}")
        print(f"  适用场景: {', '.join(combo['适用场景'])}")

    print("\n" + "=" * 60)
    print("测试推荐:")
    print("=" * 60)

    test_query = "帮我深度分析一下百度的经营质量和竞争力"
    single_recs = [
        {"framework": "深度财报分析", "score": 10},
        {"framework": "3C战略三角", "score": 8}
    ]

    combo_recs = combinator.recommend_combination(test_query, single_recs)
    for rec in combo_recs:
        print(f"\n推荐: {rec['combination_name']}")
        print(f"  框架: {' → '.join(rec['execution_order'])}")
        print(f"  说明: {rec['说明']}")
