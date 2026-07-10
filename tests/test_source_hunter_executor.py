import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))


class SourceHunterExecutorTest(unittest.TestCase):
    def test_official_hunter_executes_matching_search_plan_task_and_normalizes_rows(self):
        from source_hunter_executor import SourceHunterExecutor

        calls = []

        def fake_runner(query, *, limit, lang, hunter_id):
            calls.append({"query": query, "limit": limit, "lang": lang, "hunter_id": hunter_id})
            return [
                {
                    "title": "高德地图官方发布新功能",
                    "url": "https://amap.example.com/update?utm_source=test",
                    "description": "高德地图发布车道级导航能力。",
                    "publish_date": "2026-07-01",
                    "source_type": "firecrawl",
                    "confidence": "medium",
                }
            ]

        executor = SourceHunterExecutor(search_runner=fake_runner)
        search_plan = {
            "tasks": [
                {
                    "task_id": "OFF-T001",
                    "assigned_hunter": "official_source_hunter",
                    "dimension": "产品功能变化",
                    "query_zh": ["高德地图 官方 新功能"],
                    "query_en": ["Amap official new features"],
                    "source_layers": ["official"],
                    "expected_evidence": ["官方发布的新功能事实"],
                    "source_id_prefix": "OFF",
                },
                {
                    "task_id": "MED-T001",
                    "assigned_hunter": "media_source_hunter",
                    "dimension": "媒体报道",
                    "query_zh": ["高德地图 媒体 报道"],
                    "query_en": [],
                    "source_layers": ["media"],
                    "expected_evidence": ["媒体解读"],
                    "source_id_prefix": "MED",
                },
            ]
        }

        fragment = executor.run_hunter("official_source_hunter", search_plan, limit_per_query=2)

        self.assertEqual(fragment["node_id"], "official_source_hunter")
        self.assertEqual(fragment["execution_status"], "completed")
        self.assertEqual(fragment["task_ids"], ["OFF-T001"])
        self.assertEqual(calls[0]["query"], "高德地图 官方 新功能")
        self.assertEqual(calls[0]["hunter_id"], "official_source_hunter")
        self.assertEqual(len(fragment["sources"]), 1)

        row = fragment["sources"][0]
        self.assertEqual(row["source_id"], "OFF001")
        self.assertEqual(row["source_type"], "official")
        self.assertEqual(row["canonical_url"], "https://amap.example.com/update")
        self.assertEqual(row["publisher"], "amap.example.com")
        self.assertEqual(row["publish_date"], "2026-07-01")
        self.assertEqual(row["key_facts"], ["高德地图发布车道级导航能力。"])
        self.assertEqual(row["full_text_fetched"], False)
        self.assertEqual(row["collected_by"], "Official Source Hunter")
        self.assertIn("Search runner", row["confidence_rationale"])

    def test_executor_returns_skipped_fragment_when_no_matching_tasks(self):
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(search_runner=lambda *args, **kwargs: [])

        fragment = executor.run_hunter(
            "finance_data_hunter",
            {"tasks": [{"task_id": "OFF-T001", "assigned_hunter": "official_source_hunter"}]},
        )

        self.assertEqual(fragment["node_id"], "finance_data_hunter")
        self.assertEqual(fragment["execution_status"], "skipped_no_matching_tasks")
        self.assertEqual(fragment["sources"], [])

    def test_default_runner_skips_without_firecrawl_key_instead_of_faking_results(self):
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(env={})

        fragment = executor.run_hunter(
            "media_source_hunter",
            {
                "tasks": [
                    {
                        "task_id": "MED-T001",
                        "assigned_hunter": "media_source_hunter",
                        "query_zh": ["高德地图 媒体 报道"],
                        "query_en": [],
                    }
                ]
            },
        )

        self.assertEqual(fragment["execution_status"], "skipped_missing_tool_config")
        self.assertEqual(fragment["sources"], [])
        self.assertIn("FIRECRAWL_API_KEY", fragment["warnings"][0])


if __name__ == "__main__":
    unittest.main()
