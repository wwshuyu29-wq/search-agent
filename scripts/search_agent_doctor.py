#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search Agent workflow preflight checks.

This script is intentionally network-light by default. Use --live when you
want to verify real endpoint access in addition to local setup.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _check(name, status, detail, required=False):
    return {
        "name": name,
        "status": status,
        "required": required,
        "detail": detail,
    }


def _file_check(name, path, required=True):
    path = Path(path)
    if path.exists():
        return _check(name, "ok", str(path), required)
    status = "error" if required else "warn"
    return _check(name, status, f"missing: {path}", required)


def _command_check(name, command, required=False):
    found = shutil.which(command)
    if found:
        return _check(name, "ok", found, required)
    status = "error" if required else "warn"
    return _check(name, status, f"{command} not found in PATH", required)


def _python_runtime_check(required=True):
    version = sys.version_info
    detail = f"{sys.executable} ({version.major}.{version.minor}.{version.micro})"
    if version >= (3, 11):
        return _check("Python runtime", "ok", detail, required)
    return _check(
        "Python runtime",
        "warn",
        f"{detail}; recommended Python 3.11+ for network tooling stability",
        required,
    )


def _python311_command_check(required=False):
    candidates = ["python3.11", str(Path.home() / ".local" / "bin" / "python3.11")]
    for candidate in candidates:
        path = shutil.which(candidate) if os.path.basename(candidate) == candidate else candidate
        if not path or not Path(path).exists():
            continue
        try:
            proc = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            continue
        if proc.returncode == 0:
            return _check("Python 3.11 command", "ok", f"{path} {proc.stdout.strip() or proc.stderr.strip()}", required)
    status = "error" if required else "warn"
    return _check("Python 3.11 command", status, "python3.11 not found; install Python 3.11+ or use bundled runtime", required)


def _run_help_check(name, command, required=False):
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=15)
    except Exception as exc:
        status = "error" if required else "warn"
        return _check(name, status, str(exc), required)

    if proc.returncode == 0:
        return _check(name, "ok", "command passed", required)

    status = "error" if required else "warn"
    detail = (proc.stderr or proc.stdout or "").strip()[-300:]
    return _check(name, status, detail or f"exit {proc.returncode}", required)


def _opencli_bridge_check(required=False):
    if not shutil.which("opencli"):
        return _check("opencli browser bridge", "warn", "opencli not found in PATH", required)

    try:
        proc = subprocess.run(
            ["opencli", "doctor"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as exc:
        status = "error" if required else "warn"
        return _check("opencli browser bridge", status, str(exc), required)

    output = f"{proc.stdout}\n{proc.stderr}".strip()
    if proc.returncode == 0 and "[OK] Connectivity" in output:
        return _check("opencli browser bridge", "ok", "Chrome Browser Bridge connected", required)

    status = "error" if required else "warn"
    if "Extension" in output and "not connected" in output:
        detail = "Chrome Browser Bridge extension not connected; install/enable OpenCLI extension, keep Chrome open, then rerun opencli doctor"
    else:
        detail = output[-300:] or f"exit {proc.returncode}"
    return _check("opencli browser bridge", status, detail, required)


def _firecrawl_live_check(required=False):
    if not os.environ.get("FIRECRAWL_API_KEY"):
        return _check(
            "Firecrawl live smoke",
            "warn",
            "missing FIRECRAWL_API_KEY; cannot test api.firecrawl.dev",
            required,
        )

    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "firecrawl_search.py"),
        "--query",
        "search-agent doctor smoke test",
        "--limit",
        "1",
        "--lang",
        "en",
        "--timeout",
        "20",
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        return _check("Firecrawl live smoke", "warn", str(exc), required)

    if proc.returncode == 0:
        return _check("Firecrawl live smoke", "ok", "api.firecrawl.dev search succeeded", required)

    detail = (proc.stderr or proc.stdout or "").strip()[-300:]
    return _check("Firecrawl live smoke", "warn", detail or f"exit {proc.returncode}", required)


def _load_rss_fetch_module():
    module_path = REPO_ROOT / "lib" / "finance-rss-reader" / "scripts" / "rss_fetch.py"
    spec = importlib.util.spec_from_file_location("search_agent_doctor_rss_fetch", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_checks(run_live=False):
    """Collect local workflow readiness checks."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from lib.specialist_registry import SpecialistRegistry
        registry = SpecialistRegistry(REPO_ROOT)
        registry_status = _check("internal specialist catalog", "ok", f"{len(registry.list_specialists())} curated specialists ready", True)
    except Exception as exc:
        registry_status = _check("internal specialist catalog", "error", str(exc), True)
    checks = [
        registry_status,
        _python_runtime_check(required=False),
        _python311_command_check(required=False),
        _file_check("search-agent skill", REPO_ROOT / "SKILL.md"),
        _file_check("USAGE guide", REPO_ROOT / "USAGE.md"),
        _file_check("Firecrawl script", REPO_ROOT / "scripts" / "firecrawl_search.py"),
        _file_check(
            "RSS fetch script",
            REPO_ROOT / "lib" / "finance-rss-reader" / "scripts" / "rss_fetch.py",
        ),
        _file_check(
            "RSS sources config",
            REPO_ROOT / "lib" / "finance-rss-reader" / "references" / "rss_sources.json",
        ),
        _file_check(
            "news-aggregator script",
            Path.home() / ".comate" / "skills" / "news-aggregator-skill" / "scripts" / "fetch_news.py",
            required=False,
        ),
    ]

    checks.append(
        _check(
            "FIRECRAWL_API_KEY",
            "ok" if os.environ.get("FIRECRAWL_API_KEY") else "warn",
            "set" if os.environ.get("FIRECRAWL_API_KEY") else "missing; Firecrawl searches will be skipped/fail",
            required=False,
        )
    )

    checks.extend(
        [
            _command_check("agent-reach command", "agent-reach", required=False),
            _command_check("opencli command", "opencli", required=False),
            _command_check("mcporter command", "mcporter", required=False),
            _command_check("bili command", "bili", required=False),
        ]
    )
    checks.append(_opencli_bridge_check(required=False))
    skills_root = REPO_ROOT.parent
    for name in ("marketing", "finance"):
        stale = skills_root / name
        checks.append(_check(
            f"optional stale top-level {name}", "warn" if stale.exists() else "ok",
            f"optional old installation found: {stale}; safe to remove manually" if stale.exists() else "not installed",
            required=False,
        ))

    try:
        rss_fetch = _load_rss_fetch_module()
        firecrawl_path = Path(rss_fetch.FIRECRAWL_SCRIPT)
        expected_path = REPO_ROOT / "scripts" / "firecrawl_search.py"
        if firecrawl_path == expected_path and firecrawl_path.exists():
            checks.append(_check("RSS Firecrawl path", "ok", str(firecrawl_path), required=True))
        else:
            checks.append(
                _check(
                    "RSS Firecrawl path",
                    "error",
                    f"got {firecrawl_path}; expected {expected_path}",
                    required=True,
                )
            )
    except Exception as exc:
        checks.append(_check("RSS Firecrawl path", "error", str(exc), required=True))

    checks.append(
        _run_help_check(
            "Firecrawl CLI help",
            [sys.executable, str(REPO_ROOT / "scripts" / "firecrawl_search.py"), "--help"],
            required=True,
        )
    )

    newsagg_script = Path.home() / ".comate" / "skills" / "news-aggregator-skill" / "scripts" / "fetch_news.py"
    if newsagg_script.exists():
        checks.append(
            _run_help_check(
                "news-aggregator CLI help",
                [sys.executable, str(newsagg_script), "--help"],
                required=False,
            )
        )

    if run_live and newsagg_script.exists():
        checks.append(_firecrawl_live_check(required=False))
        checks.append(
            _run_help_check(
                "news-aggregator live smoke",
                [sys.executable, str(newsagg_script), "--source", "weibo", "--limit", "1"],
                required=False,
            )
        )

    return checks


def print_text(checks):
    for check in checks:
        marker = {"ok": "OK", "warn": "WARN", "error": "ERROR"}.get(check["status"], check["status"])
        print(f"[{marker}] {check['name']}: {check['detail']}")


def main():
    parser = argparse.ArgumentParser(description="Check Search Agent workflow tool readiness")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--live", action="store_true", help="Run lightweight live endpoint checks")
    args = parser.parse_args()

    checks = collect_checks(run_live=args.live)
    if args.json:
        json.dump(checks, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print_text(checks)

    if any(check["status"] == "error" for check in checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
