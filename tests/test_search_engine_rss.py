import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))

from search_engine import SearchEngine  # noqa: E402


class SearchEngineRssTest(unittest.TestCase):
    def test_workflow_rss_search_scans_all_configured_sources_by_default(self):
        engine = SearchEngine()

        completed = mock.Mock()
        completed.returncode = 0
        completed.stdout = "[]"
        completed.stderr = ""

        with mock.patch("search_engine.subprocess.run", return_value=completed) as run_mock:
            engine._search_rss_feeds({"公司名": "豆包", "股票代码": ""}, "同行竞争对比")

        command = run_mock.call_args.args[0]
        self.assertNotIn("--max-sources", command)


if __name__ == "__main__":
    unittest.main()
