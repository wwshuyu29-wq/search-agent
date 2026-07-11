import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ReportGeneratorTest(unittest.TestCase):
    def test_generate_from_approved_outline_preserves_exact_section_order(self):
        report_module = load_module(
            "report_generator_for_outline_test",
            REPO_ROOT / "lib" / "report_generator.py",
        )
        generator = report_module.ReportGenerator()
        approved_outline = {
            "selected_outline_id": "causal_deep_dive",
            "approved_by_user": True,
            "report_family": "deep_research_report",
            "title": "高德地图新功能深度研究",
            "target_reader": "百度地图产品团队",
            "writing_logic": "现象 → 成因 → 机制 → 影响 → 战略含义",
            "sections": [
                {
                    "section_id": "S1",
                    "heading": "现象与关键问题",
                    "purpose": "定义变化",
                    "required_claim_ids": ["C001"],
                    "word_budget": 190,
                },
                {
                    "section_id": "S2",
                    "heading": "战略含义与优先议题",
                    "purpose": "形成建议",
                    "required_claim_ids": ["C002"],
                    "word_budget": 170,
                },
            ],
        }
        claims = [
            {"claim_id": "C001", "claim_type": "fact", "content": "高德发布新功能。", "source_ids": ["OFF001"], "audit_status": "passed", "evidence_text": "高德发布新功能。", "evidence_boundary": "仅覆盖本次官方更新"},
            {"claim_id": "C002", "claim_type": "judgment", "content": "百度地图应验证用户价值。", "source_ids": ["MED001"], "audit_status": "passed", "reasoning_basis": "媒体分析支持验证用户价值", "evidence_boundary": "仅覆盖本次媒体分析"},
        ]
        sources = [
            {"source_id": "OFF001", "title": "官方更新", "url": "https://example.com/official"},
            {"source_id": "MED001", "title": "媒体分析", "url": "https://example.com/media"},
        ]

        report = generator.generate_from_approved_outline(
            approved_outline=approved_outline,
            approved_claims=claims,
            sources=sources,
            subject="高德地图",
            decision="是否跟进",
        )

        self.assertEqual("causal_deep_dive", report["approved_outline_id"])
        self.assertEqual(
            ["现象与关键问题", "战略含义与优先议题"],
            [section["heading"] for section in report["sections"]],
        )
        self.assertNotIn("核心结论", [section["heading"] for section in report["sections"]])
        self.assertIn("# 现象与关键问题", report["markdown"])
        self.assertLess(report["markdown"].index("# 现象与关键问题"), report["markdown"].index("# 战略含义与优先议题"))

    def test_generate_from_approved_outline_enforces_symmetric_word_budget(self):
        report_module = load_module("report_generator_budget_test", REPO_ROOT / "lib" / "report_generator.py")
        generator = report_module.ReportGenerator()
        claim = {"claim_id": "C1", "claim_type": "fact", "text": "用户需求增长", "source_ids": ["S1"], "audit_status": "passed", "evidence_text": "用户需求增长", "evidence_boundary": "仅覆盖当前样本"}
        source = {"source_id": "S1", "title": "来源", "url": "https://example.com", "key_facts": ["用户需求增长"]}

        def outline(budget):
            return {"selected_outline_id": "A", "approved_by_user": True, "title": "报告", "target_reader": "业务团队", "writing_logic": "证据到决策", "sections": [{"section_id": "S1", "heading": "结论", "purpose": "判断是否投入", "required_claim_ids": ["C1"], "word_budget": budget}]}

        report = generator.generate_from_approved_outline(outline(180), [claim], [source], "主题", "是否投入")
        self.assertGreaterEqual(report["sections"][0]["actual_word_count"], 162)
        self.assertLessEqual(report["sections"][0]["actual_word_count"], 198)
        with self.assertRaisesRegex(ValueError, "needs_expansion"):
            generator.generate_from_approved_outline(outline(600), [claim], [source], "主题", "是否投入")
        with self.assertRaisesRegex(ValueError, "over_budget"):
            generator.generate_from_approved_outline(outline(40), [claim], [source], "主题", "是否投入")

    def test_generate_from_approved_outline_consumes_only_passed_claims(self):
        report_module = load_module("report_generator_passed_claims_test", REPO_ROOT / "lib" / "report_generator.py")
        outline = {"selected_outline_id": "A", "approved_by_user": True, "title": "报告", "target_reader": "团队", "writing_logic": "证据", "sections": [{"section_id": "S1", "heading": "结论", "purpose": "决策", "required_claim_ids": ["C1"], "word_budget": 100}]}
        with self.assertRaisesRegex(ValueError, "missing claims"):
            report_module.ReportGenerator().generate_from_approved_outline(outline, [{"claim_id": "C1", "text": "未审核", "source_ids": ["S1"]}], [{"source_id": "S1"}], "主题", "决策")

    def test_generate_from_approved_outline_blocks_unapproved_outline(self):
        report_module = load_module(
            "report_generator_for_unapproved_outline_test",
            REPO_ROOT / "lib" / "report_generator.py",
        )
        with self.assertRaises(ValueError):
            report_module.ReportGenerator().generate_from_approved_outline(
                approved_outline={"approved_by_user": False, "sections": []},
                approved_claims=[],
                sources=[],
                subject="测试",
                decision="测试",
            )
    def test_structured_report_renders_citations_and_references_without_placeholders(self):
        report_module = load_module(
            "report_generator_for_structured_test",
            REPO_ROOT / "lib" / "report_generator.py",
        )
        generator = report_module.ReportGenerator()

        sources = [
            {
                "source_id": "OFF001",
                "title": "豆包 App Store 页面",
                "publisher": "Apple App Store",
                "source_type": "官方应用商店",
                "publish_date": "2026-07-03",
                "url": "https://apps.apple.com/cn/app/doubao",
                "confidence": "high",
                "key_facts": ["官方介绍包含规划出行、安排生活等能力。"],
            },
            {
                "source_id": "MED001",
                "title": "豆包灰测一键打车",
                "publisher": "中文科技媒体",
                "source_type": "新闻媒体",
                "publish_date": "2026-06-23",
                "url": "https://example.com/doubao-ride-hailing",
                "confidence": "medium",
                "key_facts": ["报道称豆包在北京、杭州灰测一键打车。"],
            },
        ]
        analysis = {
            "core_judgment": "豆包导航更像 AI 助手向出行入口延伸，而不是完整地图产品。",
            "supporting_reasons": [
                {
                    "claim": "官方应用页已经把规划出行纳入豆包能力描述。",
                    "source_ids": ["OFF001"],
                    "confidence": "high",
                },
                {
                    "claim": "打车灰测显示豆包在尝试把本地生活交易放进助手链路。",
                    "source_ids": ["MED001"],
                    "confidence": "medium",
                },
            ],
            "sections": [
                {
                    "heading": "豆包导航/出行能力定义",
                    "paragraphs": [
                        {
                            "text": "当前证据支持把它定义为轻量出行助手：用户用自然语言发起路线、步行或骑行等任务，再由底层地图或出行服务承接。",
                            "source_ids": ["OFF001", "MED001"],
                            "confidence": "medium",
                        }
                    ],
                },
                {
                    "heading": "对百度地图的威胁与机会",
                    "paragraphs": [
                        {
                            "text": "威胁在于高频问答入口可能截留一部分出行前查询；机会在于地图能力可以成为 AI 助手的履约底座。",
                            "source_ids": ["OFF001"],
                            "confidence": "medium",
                        }
                    ],
                },
            ],
            "competitor_matrix": {
                "columns": ["产品", "入口", "出行能力", "地图底座", "判断"],
                "rows": [
                    ["豆包", "AI 助手", "轻导航/打车灰测", "外部地图/服务承接", "入口威胁"],
                    ["百度地图", "地图 App", "导航/公交/打车/本地生活", "自有地图", "履约底座"],
                ],
            },
            "actions": [
                {
                    "text": "把“自然语言规划出行”升级为地图首页核心入口。",
                    "source_ids": ["OFF001"],
                    "owner": "产品",
                    "priority": "P0",
                }
            ],
            "risks": [
                {
                    "item": "豆包导航仍处于灰测或媒体报道阶段",
                    "trigger": "官方未发布完整产品说明",
                    "impact": "中",
                    "likelihood": "中",
                    "source_ids": ["MED001"],
                }
            ],
        }

        report = generator.generate_structured_report(
            subject="豆包导航市场调研",
            framework_name="同行竞争对比 + 3C + JTBD",
            sources=sources,
            analysis=analysis,
            generated_at="2026-07-03 16:30:00",
        )

        self.assertIn("# 豆包导航市场调研", report)
        self.assertIn("## 核心结论", report)
        self.assertIn("## 信息源覆盖与可信度说明", report)
        self.assertIn("## 豆包导航/出行能力定义", report)
        self.assertIn("## 对百度地图的威胁与机会", report)
        self.assertIn("## 竞品对比表", report)
        self.assertIn("## 可行动建议", report)
        self.assertIn("## 风险与未验证事项", report)
        self.assertIn("## 参考文献", report)
        self.assertIn("[OFF001](https://apps.apple.com/cn/app/doubao)", report)
        self.assertIn("| OFF001 | 豆包 App Store 页面 | Apple App Store | 2026-07-03 | high | [查看原文](https://apps.apple.com/cn/app/doubao) |", report)
        self.assertNotIn("待填充", report)
        self.assertNotIn("来源1", report)

    def test_structured_report_humanizer_removes_empty_ai_transitions_but_keeps_citations(self):
        report_module = load_module(
            "report_generator_for_humanizer_test",
            REPO_ROOT / "lib" / "report_generator.py",
        )
        generator = report_module.ReportGenerator()

        sources = [
            {
                "source_id": "SRC001",
                "title": "官方更新",
                "publisher": "Official",
                "source_type": "官方",
                "publish_date": "2026-07-01",
                "url": "https://example.com/source",
                "confidence": "high",
            }
        ]
        analysis = {
            "core_judgment": "值得注意的是，百度地图应优先验证暑期出行场景。",
            "supporting_reasons": [
                {
                    "claim": "从多个维度来看，暑期出行需求集中在旅游和亲子场景。",
                    "source_ids": ["SRC001"],
                    "confidence": "medium",
                }
            ],
            "sections": [],
        }

        report = generator.generate_structured_report(
            subject="百度地图暑期增长",
            framework_name="4P + AARRR",
            sources=sources,
            analysis=analysis,
            generated_at="2026-07-08 10:00:00",
        )

        self.assertNotIn("值得注意的是，", report)
        self.assertNotIn("从多个维度来看，", report)
        self.assertIn("[SRC001](https://example.com/source)", report)

    def test_structured_report_records_report_family_and_allows_two_reasons(self):
        report_module = load_module(
            "report_generator_for_family_test",
            REPO_ROOT / "lib" / "report_generator.py",
        )
        generator = report_module.ReportGenerator()

        sources = [
            {
                "source_id": "SRC001",
                "title": "官方来源",
                "publisher": "Official",
                "source_type": "官方",
                "publish_date": "2026-07-01",
                "url": "https://example.com/official",
                "confidence": "high",
            },
            {
                "source_id": "SRC002",
                "title": "用户反馈",
                "publisher": "UGC",
                "source_type": "UGC",
                "publish_date": "2026-07-02",
                "url": "https://example.com/ugc",
                "confidence": "low",
            },
        ]
        analysis = {
            "user_decision": "形成业务动作或策略建议",
            "audience": "市场组",
            "core_judgment": "百度地图应优先验证暑期亲子出行入口，而不是铺开泛旅游投放。",
            "supporting_reasons": [
                {"claim": "官方来源显示暑期功能入口已上线。", "source_ids": ["SRC001"], "confidence": "high"},
                {"claim": "UGC 反馈集中在亲子和跨城出行。", "source_ids": ["SRC002"], "confidence": "low"},
            ],
            "sections": [],
        }

        report = generator.generate_structured_report(
            subject="百度地图暑期增长",
            framework_name="4P + AARRR",
            sources=sources,
            analysis=analysis,
            generated_at="2026-07-08 11:00:00",
        )

        self.assertIn("**报告形态**：Executive Decision Memo", report)
        self.assertIn("1. 官方来源显示暑期功能入口已上线。", report)
        self.assertIn("2. UGC 反馈集中在亲子和跨城出行。", report)
        self.assertNotIn("3. ", report)
        self.assertNotIn("三个关键发现", report)


    def test_evidence_synthesis_requires_all_claims_and_respects_budget(self):
        from report_generator import ReportGenerator
        generator = ReportGenerator()
        outline = {
            "selected_outline_id": "outline_a", "approved_by_user": True,
            "report_family": "deep_research_report", "title": "测试", "target_reader": "管理层",
            "writing_logic": "证据到决策", "sections": [{"section_id": "S1", "heading": "判断", "purpose": "综合事实形成决策判断", "required_claim_ids": ["C1", "C2"], "word_budget": 260}],
        }
        claims = [
            {"claim_id": "C1", "claim_type": "fact", "text": "收入增长。", "source_ids": ["OFF001"], "audit_status": "passed", "evidence_boundary": "仅覆盖本期公告"},
            {"claim_id": "C2", "claim_type": "judgment", "text": "应优先投入。", "source_ids": ["OFF001"], "audit_status": "passed", "reasoning_basis": "增长支持投入", "evidence_boundary": "仅覆盖本期公告"},
        ]
        report = generator.generate_from_approved_outline(outline, claims, [{"source_id": "OFF001", "title": "公告", "url": "https://example.com"}], "主题", "是否投入")
        section = report["sections"][0]
        self.assertEqual(section["claim_ids"], ["C1", "C2"])
        self.assertIn("事实依据：", section["content"])
        self.assertIn("判断依据：", section["content"])
        self.assertIn("综合事实形成决策判断", section["content"])
        self.assertGreaterEqual(section["actual_word_count"], 234)
        self.assertLessEqual(section["actual_word_count"], 286)

    def test_evidence_synthesis_blocks_missing_required_claim(self):
        from report_generator import ReportGenerator
        generator = ReportGenerator()
        outline = {"selected_outline_id": "a", "approved_by_user": True, "report_family": "x", "title": "x", "target_reader": "x", "writing_logic": "x", "sections": [{"section_id": "S1", "heading": "x", "purpose": "x", "required_claim_ids": ["MISSING"], "word_budget": 100}]}
        with self.assertRaisesRegex(ValueError, "MISSING"):
            generator.generate_from_approved_outline(outline, [], [], "x", "x")

    def test_repeated_template_text_cannot_satisfy_word_budget(self):
        from report_generator import ReportGenerator
        outline = {"selected_outline_id": "a", "approved_by_user": True, "title": "报告", "target_reader": "团队", "writing_logic": "证据", "sections": [{"section_id": "S1", "heading": "结论", "purpose": "判断投入", "required_claim_ids": ["C1", "C2"], "word_budget": 300}]}
        claims = [
            {"claim_id": "C1", "claim_type": "fact", "text": "用户增长", "source_ids": ["S1"], "audit_status": "passed", "evidence_text": "用户增长", "evidence_boundary": "2026年样本"},
            {"claim_id": "C2", "claim_type": "fact", "text": "用户增长", "source_ids": ["S1"], "audit_status": "passed", "evidence_text": "用户增长", "evidence_boundary": "2026年样本"},
        ]
        with self.assertRaisesRegex(ValueError, "needs_expansion"):
            ReportGenerator().generate_from_approved_outline(outline, claims, [{"source_id": "S1", "key_facts": ["用户增长"]}], "主题", "是否投入")

    def test_missing_real_evidence_boundary_blocks_writer(self):
        from report_generator import ReportGenerator
        outline = {"selected_outline_id": "a", "approved_by_user": True, "title": "报告", "target_reader": "团队", "writing_logic": "证据", "sections": [{"section_id": "S1", "heading": "结论", "purpose": "判断投入", "required_claim_ids": ["C1"], "word_budget": 100}]}
        claim = {"claim_id": "C1", "claim_type": "fact", "text": "用户增长", "source_ids": ["S1"], "audit_status": "passed", "evidence_text": "用户增长"}
        with self.assertRaisesRegex(ValueError, "未提供证据边界"):
            ReportGenerator().generate_from_approved_outline(outline, [claim], [{"source_id": "S1", "key_facts": ["用户增长"]}], "主题", "是否投入")


if __name__ == "__main__":
    unittest.main()
