import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class FirecrawlSearchTest(unittest.TestCase):
    def test_firecrawl_search_retries_transient_timeout(self):
        firecrawl = load_module(
            "firecrawl_search_for_retry_test",
            REPO_ROOT / "scripts" / "firecrawl_search.py",
        )

        fake_requests = mock.Mock()
        fake_requests.exceptions.Timeout = TimeoutError
        response = mock.Mock()
        response.json.return_value = {
            "data": [
                {
                    "title": "豆包导航",
                    "url": "https://example.com/doubao",
                    "description": "测试结果",
                }
            ]
        }
        response.raise_for_status.return_value = None
        fake_requests.post.side_effect = [TimeoutError("connect timeout"), response]

        with mock.patch.object(firecrawl, "_require_requests", return_value=fake_requests):
            results = firecrawl.firecrawl_search(
                "豆包导航",
                limit=1,
                lang="zh",
                api_key="test",
                timeout=10,
                retries=1,
                backoff_seconds=0,
            )

        self.assertEqual(fake_requests.post.call_count, 2)
        self.assertEqual(results[0]["source_id"], "FC001")
        self.assertEqual(results[0]["title"], "豆包导航")


if __name__ == "__main__":
    unittest.main()
