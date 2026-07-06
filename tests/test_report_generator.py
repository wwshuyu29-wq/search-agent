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


if __name__ == "__main__":
    unittest.main()
