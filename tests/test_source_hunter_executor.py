import sys
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_runner_timeout_degrades_structurally_and_next_query_continues(self):
        import subprocess
        from source_hunter_executor import SourceHunterExecutor

        calls = []
        def runner(query, **kwargs):
            calls.append(query)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired(["tool"], 5)
            return [{"title": "ok", "url": "https://example.com", "description": "fact"}]

        executor = SourceHunterExecutor(search_runner=runner)
        plan = {"tasks": [
            {"task_id": "T1", "assigned_hunter": "official_source_hunter", "query_zh": ["one"], "query_en": []},
            {"task_id": "T2", "assigned_hunter": "official_source_hunter", "query_zh": ["two"], "query_en": []},
        ]}
        fragment = executor.run_hunter("official_source_hunter", plan)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(fragment["sources"]), 1)
        self.assertEqual(fragment["warnings"][0]["error_type"], "timeout")
        self.assertEqual(fragment["execution_status"], "completed_with_warnings")

    def test_normalized_method_source_flag_is_preserved(self):
        from source_hunter_executor import SourceHunterExecutor
        executor = SourceHunterExecutor(search_runner=lambda *a, **k: [{"title": "method", "url": "/skill", "summary": "method", "method_source": True}])
        fragment = executor.run_hunter("marketing_intelligence_hunter", {"tasks": [{"task_id": "T", "assigned_hunter": "marketing_intelligence_hunter", "query_zh": ["x"], "query_en": []}]})
        self.assertTrue(fragment["sources"][0]["method_source"])

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

    def test_rss_news_hunter_uses_finance_rss_reader_without_firecrawl_key(self):
        from source_hunter_executor import SourceHunterExecutor

        class Completed:
            returncode = 0
            stderr = ""
            stdout = """
            [
              {
                "title": "高德地图上线新导航能力",
                "url": "https://news.example.com/amap-update?utm_campaign=x",
                "published": "2026-07-02",
                "summary": "高德地图近期上线车道级导航相关能力。",
                "source": "示例财经新闻",
                "source_type": "媒体",
                "fetcher": "rss",
                "relevance_score": 0.72
              }
            ]
            """

        captured_commands = []

        def fake_run(command, **kwargs):
            captured_commands.append(command)
            return Completed()

        executor = SourceHunterExecutor(env={"SEARCH_AGENT_RSS_MAX_SOURCES": "2"})
        search_plan = {
            "tasks": [
                {
                    "task_id": "RSS-T001",
                    "assigned_hunter": "rss_news_hunter",
                    "dimension": "近期快讯",
                    "query_zh": ["高德地图 新功能"],
                    "query_en": [],
                    "source_layers": ["rss", "news"],
                    "expected_evidence": ["近期媒体/RSS信号"],
                    "source_id_prefix": "RSS",
                }
            ]
        }

        with patch("source_hunter_executor.subprocess.run", side_effect=fake_run):
            fragment = executor.run_hunter("rss_news_hunter", search_plan, limit_per_query=3)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertEqual(fragment["task_ids"], ["RSS-T001"])
        self.assertIn("rss_fetch.py", " ".join(captured_commands[0]))
        self.assertIn("--keywords", captured_commands[0])
        self.assertIn("高德地图,新功能", captured_commands[0])
        self.assertIn("--max-sources", captured_commands[0])
        self.assertIn("2", captured_commands[0])
        self.assertNotIn("FIRECRAWL_API_KEY", " ".join(fragment["warnings"]))

        row = fragment["sources"][0]
        self.assertEqual(row["source_id"], "RSS001")
        self.assertEqual(row["source_type"], "rss_news")
        self.assertEqual(row["publisher"], "示例财经新闻")
        self.assertEqual(row["publish_date"], "2026-07-02")
        self.assertEqual(row["canonical_url"], "https://news.example.com/amap-update")
        self.assertEqual(row["key_facts"], ["高德地图近期上线车道级导航相关能力。"])
        self.assertEqual(row["relevance_score"], 0.72)
        self.assertEqual(row["retrieval_tool"], "finance-rss-reader")
        self.assertIn("fetcher=rss", row["confidence_rationale"])

    def test_finance_data_hunter_uses_yfinance_snapshot_runner(self):
        from source_hunter_executor import SourceHunterExecutor

        class Completed:
            returncode = 0
            stderr = ""
            stdout = """
            [
              {
                "title": "AAPL Yahoo Finance market snapshot",
                "url": "https://finance.yahoo.com/quote/AAPL",
                "description": "AAPL last price 220.5 USD; market cap 3300000000000.",
                "publish_date": "2026-07-10",
                "source": "Yahoo Finance via yfinance",
                "confidence": "high",
                "full_text_fetched": true
              }
            ]
            """

        captured_commands = []

        def fake_run(command, **kwargs):
            captured_commands.append(command)
            return Completed()

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "FIN-T001",
                    "assigned_hunter": "finance_data_hunter",
                    "dimension": "行情快照",
                    "query_en": ["AAPL stock price"],
                    "query_zh": [],
                    "source_layers": ["finance_data"],
                    "expected_evidence": ["股价、市值、币种"],
                    "source_id_prefix": "FIN",
                }
            ]
        }

        with patch("source_hunter_executor.subprocess.run", side_effect=fake_run):
            fragment = executor.run_hunter("finance_data_hunter", search_plan, limit_per_query=1)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertIn("yfinance_snapshot.py", " ".join(captured_commands[0]))
        self.assertIn("--ticker", captured_commands[0])
        self.assertIn("AAPL", captured_commands[0])

        row = fragment["sources"][0]
        self.assertEqual(row["source_id"], "FIN001")
        self.assertEqual(row["source_type"], "finance_data")
        self.assertEqual(row["publisher"], "Yahoo Finance via yfinance")
        self.assertEqual(row["confidence"], "high")
        self.assertEqual(row["retrieval_tool"], "yfinance-data")

    def test_finance_data_hunter_skips_when_yfinance_is_missing(self):
        from source_hunter_executor import SourceHunterExecutor

        class Completed:
            returncode = 3
            stderr = "YFINANCE_NOT_INSTALLED"
            stdout = ""

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "FIN-T001",
                    "assigned_hunter": "finance_data_hunter",
                    "query_en": ["AAPL stock price"],
                    "query_zh": [],
                }
            ]
        }

        with patch("source_hunter_executor.subprocess.run", return_value=Completed()):
            fragment = executor.run_hunter("finance_data_hunter", search_plan, limit_per_query=1)

        self.assertEqual(fragment["execution_status"], "skipped_missing_tool_config")
        self.assertEqual(fragment["sources"], [])
        self.assertIn("yfinance", fragment["warnings"][0])

    def test_finance_data_hunter_uses_yc_reader_public_api(self):
        from source_hunter_executor import SourceHunterExecutor

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"""
                [
                  {
                    "name": "Stripe",
                    "one_liner": "Economic infrastructure for the internet.",
                    "batch": "Summer 2009",
                    "team_size": 7000,
                    "isHiring": true,
                    "website": "https://stripe.com",
                    "slug": "stripe"
                  }
                ]
                """

        captured_urls = []

        def fake_urlopen(url, timeout=0):
            captured_urls.append(url)
            return FakeResponse()

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "FIN-T002",
                    "assigned_hunter": "finance_data_hunter",
                    "dimension": "创业公司生态",
                    "query_en": ["YC fintech companies hiring"],
                    "query_zh": [],
                    "source_layers": ["finance_data"],
                    "expected_evidence": ["YC company public data"],
                    "source_id_prefix": "FIN",
                }
            ]
        }

        with patch("source_hunter_executor.urlopen", side_effect=fake_urlopen):
            fragment = executor.run_hunter("finance_data_hunter", search_plan, limit_per_query=3)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertIn("industries/fintech.json", captured_urls[0])
        self.assertEqual(fragment["sources"][0]["retrieval_tool"], "yc-reader")
        self.assertEqual(fragment["sources"][0]["publisher"], "yc-oss/api")
        self.assertIn("Stripe", fragment["sources"][0]["title"])
        self.assertIn("team_size: 7000", fragment["sources"][0]["key_facts"][0])

    def test_finance_data_hunter_routes_funda_without_key_as_setup_required(self):
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "FIN-T003",
                    "assigned_hunter": "finance_data_hunter",
                    "dimension": "分析师研究",
                    "query_en": ["funda DCF comps transcript supply chain"],
                    "query_zh": [],
                    "source_layers": ["finance_data"],
                    "expected_evidence": ["Funda setup status"],
                    "source_id_prefix": "FIN",
                }
            ]
        }

        fragment = executor.run_hunter("finance_data_hunter", search_plan, limit_per_query=3)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertTrue(any("funda-data" in source["title"] for source in fragment["sources"]))
        funda = next(source for source in fragment["sources"] if "funda-data" in source["title"])
        self.assertEqual(funda["retrieval_tool"], "funda-data")
        self.assertEqual(funda["confidence"], "low")
        self.assertIn("FUNDA_API_KEY", funda["key_facts"][0])
        self.assertIn("method source", funda["confidence_rationale"])

    def test_finance_data_hunter_routes_twitter_opencli_missing_setup(self):
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "FIN-T004",
                    "assigned_hunter": "finance_data_hunter",
                    "dimension": "金融舆情",
                    "query_en": ["Twitter sentiment on AAPL stock buzz"],
                    "query_zh": [],
                    "source_layers": ["finance_data"],
                    "expected_evidence": ["Twitter setup status"],
                    "source_id_prefix": "FIN",
                }
            ]
        }

        with patch("source_hunter_executor.shutil.which", return_value=None):
            fragment = executor.run_hunter("finance_data_hunter", search_plan, limit_per_query=3)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertTrue(any("twitter-reader" in source["title"] for source in fragment["sources"]))
        twitter = next(source for source in fragment["sources"] if "twitter-reader" in source["title"])
        self.assertEqual(twitter["retrieval_tool"], "twitter-reader")
        self.assertEqual(twitter["confidence"], "low")
        self.assertIn("opencli", twitter["key_facts"][0])
        self.assertIn("read-only", twitter["key_facts"][0])

    def test_twitter_opencli_timeout_uses_configured_timeout_and_degrades(self):
        import subprocess
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(env={"SEARCH_AGENT_SUBPROCESS_TIMEOUT": "7"})
        spec = {"why_use": "sentiment", "output_artifact": "sources", "use_well": "read only"}
        with patch("source_hunter_executor.shutil.which", return_value="/usr/bin/opencli"), patch(
            "source_hunter_executor.subprocess.run", side_effect=subprocess.TimeoutExpired(["opencli"], 7)
        ) as run:
            rows = executor._twitter_reader_runner("AAPL", limit=2, spec=spec)
        self.assertEqual(run.call_args.kwargs["timeout"], 7.0)
        self.assertIn("timed out", rows[0]["summary"])
        self.assertEqual(rows[0]["confidence"], "low")

    def test_finance_data_hunter_routes_generic_opencli_missing_setup(self):
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "FIN-T005",
                    "assigned_hunter": "finance_data_hunter",
                    "dimension": "外部金融社区",
                    "query_en": ["read reddit r/wallstreetbets using opencli"],
                    "query_zh": [],
                    "source_layers": ["finance_data"],
                    "expected_evidence": ["opencli setup status"],
                    "source_id_prefix": "FIN",
                }
            ]
        }

        with patch("source_hunter_executor.shutil.which", return_value=None):
            fragment = executor.run_hunter("finance_data_hunter", search_plan, limit_per_query=3)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertTrue(any("opencli-reader" in source["title"] for source in fragment["sources"]))
        opencli = next(source for source in fragment["sources"] if "opencli-reader" in source["title"])
        self.assertEqual(opencli["retrieval_tool"], "opencli-reader")
        self.assertEqual(opencli["confidence"], "low")
        self.assertIn("not installed", opencli["key_facts"][0])

    def test_ugc_social_hunter_uses_bilibili_cli_when_available(self):
        from source_hunter_executor import SourceHunterExecutor

        class Completed:
            returncode = 0
            stderr = ""
            stdout = """
            {
              "ok": true,
              "schema_version": "1",
              "data": [
                {
                  "id": "BV123",
                  "bvid": "BV123",
                  "title": "高德地图用户体验讨论",
                  "author": "地图观察员",
                  "play": 1200,
                  "duration": "5:20"
                }
              ]
            }
            """

        captured_commands = []

        def fake_run(command, **kwargs):
            captured_commands.append(command)
            return Completed()

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "UGC-T001",
                    "assigned_hunter": "ugc_social_hunter",
                    "dimension": "用户讨论",
                    "query_zh": ["高德地图 用户体验"],
                    "query_en": [],
                    "source_layers": ["ugc", "social"],
                    "expected_evidence": ["用户讨论信号"],
                    "source_id_prefix": "UGC",
                }
            ]
        }

        with patch("source_hunter_executor.shutil.which", return_value="/usr/local/bin/bili"):
            with patch("source_hunter_executor.subprocess.run", side_effect=fake_run):
                fragment = executor.run_hunter("ugc_social_hunter", search_plan, limit_per_query=2)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertIn("bili", captured_commands[0][0])
        self.assertIn("--json", captured_commands[0])

        row = fragment["sources"][0]
        self.assertEqual(row["source_id"], "UGC001")
        self.assertEqual(row["source_type"], "ugc_social")
        self.assertEqual(row["publisher"], "Bilibili")
        self.assertEqual(row["url"], "https://www.bilibili.com/video/BV123")
        self.assertEqual(row["retrieval_tool"], "bili-cli")
        self.assertIn("地图观察员", row["key_facts"][0])

    def test_ugc_social_hunter_skips_when_bilibili_cli_is_missing(self):
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "UGC-T001",
                    "assigned_hunter": "ugc_social_hunter",
                    "query_zh": ["高德地图 用户体验"],
                    "query_en": [],
                }
            ]
        }

        with patch("source_hunter_executor.shutil.which", return_value=None):
            fragment = executor.run_hunter("ugc_social_hunter", search_plan, limit_per_query=2)

        self.assertEqual(fragment["execution_status"], "skipped_missing_tool_config")
        self.assertEqual(fragment["sources"], [])
        self.assertIn("bili", fragment["warnings"][0])

    def test_marketing_intelligence_hunter_routes_to_local_marketing_skills(self):
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "MKT-T001",
                    "assigned_hunter": "marketing_intelligence_hunter",
                    "dimension": "增长方案",
                    "query_zh": ["百度地图 暑期 增长 营销方案"],
                    "query_en": [],
                    "source_layers": ["marketing_intelligence"],
                    "expected_evidence": ["营销方法和竞品情报入口"],
                    "source_id_prefix": "MKT",
                }
            ]
        }

        fragment = executor.run_hunter("marketing_intelligence_hunter", search_plan, limit_per_query=3)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertEqual(fragment["task_ids"], ["MKT-T001"])
        self.assertGreaterEqual(len(fragment["sources"]), 2)

        first = fragment["sources"][0]
        self.assertEqual(first["source_id"], "MKT001")
        self.assertEqual(first["source_type"], "marketing_intelligence")
        self.assertEqual(first["publisher"], "local marketing skill")
        self.assertEqual(first["retrieval_tool"], "marketing-skills-catalog")
        self.assertIn("specialists/marketing", first["url"])
        self.assertTrue(first["url"].endswith("prompt.md"))
        self.assertIn("method source", first["confidence_rationale"])
        self.assertIn("why_use:", first["key_facts"][0])
        self.assertIn("output_artifact:", first["key_facts"][0])
        self.assertTrue(any("marketing-plan" in source["title"] for source in fragment["sources"]))
        self.assertTrue(any("marketing-ideas" in source["title"] for source in fragment["sources"]))

    def test_marketing_intelligence_hunter_selects_fine_grained_skill(self):
        from source_hunter_executor import SourceHunterExecutor

        executor = SourceHunterExecutor(env={})
        search_plan = {
            "tasks": [
                {
                    "task_id": "MKT-T002",
                    "assigned_hunter": "marketing_intelligence_hunter",
                    "dimension": "用户激活",
                    "query_zh": ["百度地图 新用户 激活 analytics 指标 ab test 实验"],
                    "query_en": [],
                    "source_layers": ["marketing_intelligence"],
                    "expected_evidence": ["激活方法和指标"],
                    "source_id_prefix": "MKT",
                }
            ]
        }

        fragment = executor.run_hunter("marketing_intelligence_hunter", search_plan, limit_per_query=4)

        self.assertEqual(fragment["execution_status"], "completed")
        self.assertTrue(any("analytics" in source["title"] for source in fragment["sources"]))
        analytics = next(source for source in fragment["sources"] if "analytics" in source["title"])
        self.assertIn("Internal curated analytics", analytics["key_facts"][0])
        self.assertIn("method source", analytics["confidence_rationale"])


if __name__ == "__main__":
    unittest.main()
