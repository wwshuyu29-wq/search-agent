#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图识别模块 - 基于关键词和语义理解推荐合适的分析框架
"""

import re
from typing import List, Dict


class IntentClassifier:
    """意图识别分类器"""

    # 关键词映射表 (框架名 -> 关键词列表)
    KEYWORD_MAP = {
        "财报快评": ["财报", "季报", "年报", "快速看", "Q1", "Q2", "Q3", "Q4", "earnings", "快评"],
        "深度财报分析": ["深度", "投资", "经营判断", "值不值得投", "经营质量", "尽调", "投资决策"],
        "同行竞争对比": ["同行", "竞争", "对比", "竞品", "vs", "PK", "哪个更好", "比较"],
        "PEST分析": ["政策", "监管", "宏观", "环境", "趋势", "社会", "技术变革", "PEST"],
        "Porter五力": ["竞争格局", "供应商", "买方", "进入壁垒", "替代品", "五力", "Porter", "行业格局"],
        "SWOT": ["优劣势", "机会威胁", "战略", "综合评估", "SWOT", "诊断"],
        "3C战略三角": ["市场定位", "客户", "商业模式", "3C", "战略三角"],
        "4P营销": ["营销", "产品推广", "定价", "渠道", "市场营销", "4P", "GTM"],
        "风险专项": ["风险", "监管风险", "财务风险", "危机", "预警", "合规"]
    }

    # 复杂问题指示词 (提示需要多框架组合)
    COMPLEXITY_INDICATORS = [
        "全面", "完整", "系统", "深入", "详细", "多维度",
        "从多个角度", "综合", "整体", "全方位", "多角度"
    ]

    # 优先级权重 (某些关键词出现时,优先推荐对应框架)
    PRIORITY_KEYWORDS = {
        "财报": ["财报快评", "深度财报分析"],
        "快速": ["财报快评"],
        "深度": ["深度财报分析"],
        "竞品": ["同行竞争对比", "3C战略三角"],
        "政策": ["PEST分析"],
        "风险": ["风险专项"]
    }

    def __init__(self):
        pass

    def classify(self, user_query: str, top_k: int = 3, return_complexity: bool = True) -> List[Dict]:
        """
        分析用户问题,推荐合适的分析框架

        Args:
            user_query: 用户输入的问题
            top_k: 返回Top K个推荐框架
            return_complexity: 是否返回问题复杂度判断

        Returns:
            List[Dict]: 推荐框架列表,每个包含 framework, score, reason
                       如果 return_complexity=True, 还会包含 is_complex_problem
        """
        scores = {}
        reasons = {}

        # 预处理用户输入
        query_lower = user_query.lower()

        # 1. 关键词匹配打分
        for framework, keywords in self.KEYWORD_MAP.items():
            score = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 1
                    matched_keywords.append(keyword)

            if score > 0:
                scores[framework] = score
                reasons[framework] = f"问题涉及: {', '.join(matched_keywords)}"

        # 2. 优先级加权
        for priority_kw, priority_frameworks in self.PRIORITY_KEYWORDS.items():
            if priority_kw in query_lower:
                for fw in priority_frameworks:
                    if fw in scores:
                        scores[fw] += 2  # 优先级加权

        # 3. 特殊规则判断
        # 规则1: 如果提到具体公司名+财报相关,优先财报分析
        if self._contains_company_name(user_query) and any(kw in query_lower for kw in ["财报", "季报", "年报", "earnings"]):
            if "快速" in query_lower or "快评" in query_lower:
                scores["财报快评"] = scores.get("财报快评", 0) + 3
            else:
                scores["深度财报分析"] = scores.get("深度财报分析", 0) + 3

        # 规则2: 如果提到多个公司,优先同行对比
        if self._contains_multiple_companies(user_query):
            scores["同行竞争对比"] = scores.get("同行竞争对比", 0) + 3

        # 规则3: 地图/产品新功能调研通常是竞品跟踪，优先竞争对比，再补宏观趋势
        if any(kw in query_lower for kw in ["新功能", "上新", "市场动态", "行业趋势"]):
            scores["同行竞争对比"] = scores.get("同行竞争对比", 0) + 4
            scores["PEST分析"] = scores.get("PEST分析", 0) + 1
            reasons.setdefault("同行竞争对比", "问题涉及: 新功能/市场动态，需要做竞品跟踪")
            reasons.setdefault("PEST分析", "问题涉及: 市场动态，可补充行业趋势")

        # 4. 如果没有匹配到任何框架,返回默认推荐
        if not scores:
            return self._get_default_recommendations()

        # 5. 按分数排序,返回Top K
        sorted_frameworks = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        recommendations = []
        for fw_name, score in sorted_frameworks:
            recommendations.append({
                "framework": fw_name,
                "score": score,
                "reason": reasons.get(fw_name, "通用场景推荐")
            })

        # 6. 判断问题复杂度 (是否需要多框架组合)
        if return_complexity:
            is_complex = self._is_complex_problem(user_query, scores)
            for rec in recommendations:
                rec["is_complex_problem"] = is_complex

        return recommendations

    def _contains_company_name(self, text: str) -> bool:
        """简单判断是否包含公司名 (可扩展为NER)"""
        # 简化版: 检测常见公司后缀
        company_suffixes = ["公司", "集团", "股份", "有限", "科技", "Inc", "Corp", "Ltd"]
        return any(suffix in text for suffix in company_suffixes)

    def _contains_multiple_companies(self, text: str) -> bool:
        """判断是否提到多个公司 (vs/对比/和等)"""
        comparison_keywords = ["vs", "对比", "比较", "和", "与", "PK"]
        return any(kw in text for kw in comparison_keywords)

    def _get_default_recommendations(self) -> List[Dict]:
        """默认推荐"""
        return [
            {"framework": "PEST分析", "score": 0, "reason": "通用环境分析框架", "is_complex_problem": False},
            {"framework": "SWOT", "score": 0, "reason": "通用综合评估框架", "is_complex_problem": False},
            {"framework": "3C战略三角", "score": 0, "reason": "通用市场分析框架", "is_complex_problem": False}
        ]

    def _is_complex_problem(self, user_query: str, scores: Dict) -> bool:
        """
        判断问题是否复杂,需要多框架组合

        判断规则:
        1. 用户明确提到"全面"、"完整"、"系统"等词
        2. 匹配到多个框架且分数差距不大 (说明问题多维度)
        3. 问题长度超过50字 (通常是复杂需求)
        """
        query_lower = user_query.lower()

        # 规则1: 显式复杂度指示词
        if any(indicator in query_lower for indicator in self.COMPLEXITY_INDICATORS):
            return True

        # 规则2: 多个高分框架 (Top 2的分数都>=3且差距<=2)
        if len(scores) >= 2:
            sorted_scores = sorted(scores.values(), reverse=True)
            if sorted_scores[0] >= 3 and sorted_scores[1] >= 3:
                if abs(sorted_scores[0] - sorted_scores[1]) <= 2:
                    return True

        # 规则3: 问题长度
        if len(user_query) > 50:
            return True

        return False


# 便捷函数
def classify_intent(user_query: str, top_k: int = 3, return_complexity: bool = True) -> List[Dict]:
    """便捷函数: 分析用户意图并推荐框架"""
    classifier = IntentClassifier()
    return classifier.classify(user_query, top_k, return_complexity=return_complexity)


if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "帮我快速看看高德地图的Q1财报",
        "百度值不值得投资?做个深度分析",
        "对比一下高德和百度地图的竞争力",
        "小度音箱的政策环境怎么样?",
        "分析一下百度的风险因素"
    ]

    for query in test_cases:
        print(f"\n用户问题: {query}")
        result = classify_intent(query)
        for idx, rec in enumerate(result, 1):
            print(f"  推荐{idx}: {rec['framework']} (得分:{rec['score']}, 理由:{rec['reason']})")
