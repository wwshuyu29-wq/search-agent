import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))
sys.path.insert(0, str(REPO_ROOT / "bin"))

from intent_classifier import classify_intent  # noqa: E402
from search_agent import SearchAgentSkill  # noqa: E402


class CliBehaviorTest(unittest.TestCase):
    def test_classify_intent_accepts_return_complexity(self):
        recommendations = classify_intent(
            "高德地图最近三个月上了什么新功能，对百度地图有什么启示",
            top_k=3,
            return_complexity=True,
        )

        self.assertTrue(recommendations)
        self.assertIn("is_complex_problem", recommendations[0])

    def test_new_feature_map_research_prefers_competitor_comparison(self):
        recommendations = classify_intent(
            "高德地图最近三个月上了什么新功能，对百度地图有什么启示",
            top_k=3,
            return_complexity=True,
        )

        self.assertEqual(recommendations[0]["framework"], "同行竞争对比")

    def test_extracts_map_competitors_from_query(self):
        agent = SearchAgentSkill()

        params = agent._extract_params_from_query(
            "高德地图最近三个月上了什么新功能，对百度地图有什么启示"
        )

        self.assertEqual(params["主题"], "高德地图")
        self.assertEqual(params["公司名"], "高德地图")
        self.assertEqual(params["公司A"], "高德地图")
        self.assertEqual(params["公司B"], "百度地图")
        self.assertIn("百度地图", params["竞争对手"])
        self.assertEqual(params["行业"], "地图导航")

    def test_output_dir_uses_environment_override(self):
        agent = SearchAgentSkill()

        with tempfile.TemporaryDirectory() as temp_dir:
            previous = os.environ.get("SEARCH_AGENT_OUTPUT_DIR")
            os.environ["SEARCH_AGENT_OUTPUT_DIR"] = temp_dir
            try:
                self.assertEqual(agent._get_output_dir(), temp_dir)
            finally:
                if previous is None:
                    os.environ.pop("SEARCH_AGENT_OUTPUT_DIR", None)
                else:
                    os.environ["SEARCH_AGENT_OUTPUT_DIR"] = previous


if __name__ == "__main__":
    unittest.main()
