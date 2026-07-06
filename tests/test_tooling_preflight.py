import importlib.util
import os
import subprocess
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


class ToolingPreflightTest(unittest.TestCase):
    def test_rss_firecrawl_default_path_points_to_repo_script(self):
        rss_fetch = load_module(
            "rss_fetch_for_test",
            REPO_ROOT / "lib" / "finance-rss-reader" / "scripts" / "rss_fetch.py",
        )

        self.assertEqual(
            Path(rss_fetch.FIRECRAWL_SCRIPT),
            REPO_ROOT / "scripts" / "firecrawl_search.py",
        )

    def test_doctor_reports_core_tooling_without_network(self):
        doctor = load_module(
            "search_agent_doctor_for_test",
            REPO_ROOT / "scripts" / "search_agent_doctor.py",
        )

        checks = doctor.collect_checks(run_live=False)
        by_name = {check["name"]: check for check in checks}

        self.assertEqual(by_name["search-agent skill"]["status"], "ok")
        self.assertEqual(by_name["Firecrawl script"]["status"], "ok")
        self.assertEqual(by_name["RSS Firecrawl path"]["status"], "ok")
        self.assertIn(by_name["FIRECRAWL_API_KEY"]["status"], {"ok", "warn"})
        self.assertIn(by_name["agent-reach command"]["status"], {"ok", "warn"})

    def test_doctor_live_mode_reports_firecrawl_without_key(self):
        doctor = load_module(
            "search_agent_doctor_live_for_test",
            REPO_ROOT / "scripts" / "search_agent_doctor.py",
        )

        previous = os.environ.get("FIRECRAWL_API_KEY")
        os.environ.pop("FIRECRAWL_API_KEY", None)
        try:
            checks = doctor.collect_checks(run_live=True)
        finally:
            if previous is not None:
                os.environ["FIRECRAWL_API_KEY"] = previous

        by_name = {check["name"]: check for check in checks}
        self.assertEqual(by_name["Firecrawl live smoke"]["status"], "warn")
        self.assertIn("missing", by_name["Firecrawl live smoke"]["detail"])

    def test_opencli_bridge_check_warns_when_extension_is_missing(self):
        doctor = load_module(
            "search_agent_doctor_opencli_for_test",
            REPO_ROOT / "scripts" / "search_agent_doctor.py",
        )

        proc = subprocess.CompletedProcess(
            args=["opencli", "doctor"],
            returncode=1,
            stdout="[MISSING] Extension: not connected\n[FAIL] Connectivity: failed",
            stderr="",
        )
        with mock.patch.object(doctor.shutil, "which", return_value="/tmp/opencli"):
            with mock.patch.object(doctor.subprocess, "run", return_value=proc):
                check = doctor._opencli_bridge_check(required=False)

        self.assertEqual(check["status"], "warn")
        self.assertIn("extension not connected", check["detail"])


if __name__ == "__main__":
    unittest.main()
