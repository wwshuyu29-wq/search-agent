#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable Source Hunter adapter for the R0 retrieval vertical slice.

The executor turns SearchPlan tasks into SourceListFragment rows. It is small on
purpose: tools are injectable for tests and Codex packet execution, while the
default runner uses the local Firecrawl wrapper only when its key is configured.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import urlopen

from workflow_contracts import select_skill_adapters


SearchRunner = Callable[..., List[Dict[str, Any]]]


HUNTER_CONFIG = {
    "official_source_hunter": {
        "prefix": "OFF",
        "source_type": "official",
        "collector": "Official Source Hunter",
        "layers": {"official"},
        "lang_order": ("zh", "en"),
    },
    "media_source_hunter": {
        "prefix": "MED",
        "source_type": "media",
        "collector": "Media Source Hunter",
        "layers": {"media", "deep_analysis"},
        "lang_order": ("zh", "en"),
    },
    "rss_news_hunter": {
        "prefix": "RSS",
        "source_type": "rss_news",
        "collector": "RSS/News Hunter",
        "layers": {"rss", "news", "rss_news"},
        "lang_order": ("zh", "en"),
    },
    "ugc_social_hunter": {
        "prefix": "UGC",
        "source_type": "ugc_social",
        "collector": "UGC/Social Hunter",
        "layers": {"ugc", "social", "ugc_social"},
        "lang_order": ("zh", "en"),
    },
    "finance_data_hunter": {
        "prefix": "FIN",
        "source_type": "finance_data",
        "collector": "Finance Data Hunter",
        "layers": {"finance", "finance_data"},
        "lang_order": ("en", "zh"),
    },
    "marketing_intelligence_hunter": {
        "prefix": "MKT",
        "source_type": "marketing_intelligence",
        "collector": "Marketing Intelligence Hunter",
        "layers": {"marketing", "marketing_intelligence"},
        "lang_order": ("zh", "en"),
    },
}


class SourceHunterExecutor:
    """Run one Source Hunter node against a SearchPlan."""

    def __init__(
        self,
        search_runner: Optional[SearchRunner] = None,
        env: Optional[Dict[str, str]] = None,
        repo_root: Optional[Path] = None,
    ):
        self.env = dict(os.environ if env is None else env)
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[1])
        self.search_runner = search_runner

    def run_hunter(
        self,
        hunter_id: str,
        search_plan: Dict[str, Any],
        limit_per_query: int = 5,
    ) -> Dict[str, Any]:
        """Execute tasks assigned to one hunter and return a SourceListFragment."""
        config = self._config_for(hunter_id)
        tasks = self._matching_tasks(hunter_id, search_plan.get("tasks", []), config)
        fragment = {
            "node_id": hunter_id,
            "execution_status": "completed",
            "task_ids": [task.get("task_id", "") for task in tasks],
            "sources": [],
            "warnings": [],
        }

        if not tasks:
            fragment["execution_status"] = "skipped_no_matching_tasks"
            return fragment

        runner = self.search_runner or self._runner_for_hunter(hunter_id)
        source_index = 1
        for task in tasks:
            for query, lang in self._queries_for_task(task, config):
                try:
                    results = runner(query, limit=limit_per_query, lang=lang, hunter_id=hunter_id)
                except MissingToolConfig as exc:
                    fragment["execution_status"] = "skipped_missing_tool_config"
                    fragment["warnings"].append(str(exc))
                    return fragment
                except subprocess.TimeoutExpired as exc:
                    fragment["execution_status"] = "completed_with_warnings"
                    fragment["warnings"].append({"error_type": "timeout", "query": query, "timeout_seconds": exc.timeout, "message": str(exc)})
                    continue
                except Exception as exc:
                    fragment["execution_status"] = "completed_with_warnings"
                    fragment["warnings"].append({"error_type": "provider_failure", "query": query, "message": str(exc)})
                    continue
                for result in results:
                    fragment["sources"].append(
                        self._normalize_result(
                            result=result,
                            task=task,
                            config=config,
                            index=source_index,
                        )
                    )
                    source_index += 1

        return fragment

    def _runner_for_hunter(self, hunter_id: str) -> SearchRunner:
        if hunter_id == "rss_news_hunter":
            return self._rss_runner
        if hunter_id == "finance_data_hunter":
            return self._finance_runner
        if hunter_id == "ugc_social_hunter":
            return self._ugc_runner
        if hunter_id == "marketing_intelligence_hunter":
            return self._marketing_skill_runner
        return self._firecrawl_runner

    def _firecrawl_runner(self, query: str, *, limit: int, lang: str, hunter_id: str):
        if not self.env.get("FIRECRAWL_API_KEY"):
            raise MissingToolConfig("FIRECRAWL_API_KEY is required for default SourceHunterExecutor retrieval")

        script = self.repo_root / "scripts" / "firecrawl_search.py"
        command = [
            sys.executable,
            str(script),
            "--query",
            query,
            "--limit",
            str(limit),
            "--lang",
            lang,
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
            timeout=float(self.env.get("SEARCH_AGENT_SUBPROCESS_TIMEOUT", "60")),
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "firecrawl_search.py failed")
        return json.loads(completed.stdout or "[]")

    def _rss_runner(self, query: str, *, limit: int, lang: str, hunter_id: str):
        script = self.repo_root / "lib" / "finance-rss-reader" / "scripts" / "rss_fetch.py"
        sources_config = (
            self.repo_root
            / "lib"
            / "finance-rss-reader"
            / "references"
            / "rss_sources.json"
        )
        if not script.exists():
            raise MissingToolConfig(f"finance-rss-reader script not found: {script}")
        if not sources_config.exists():
            raise MissingToolConfig(f"RSS sources config not found: {sources_config}")

        command = [
            sys.executable,
            str(script),
            "--keywords",
            self._rss_keywords_arg(query),
            "--ticker",
            "",
            "--days",
            str(self.env.get("SEARCH_AGENT_RSS_DAYS", "14")),
            "--sources-config",
            str(sources_config),
            "--min-score",
            str(self.env.get("SEARCH_AGENT_RSS_MIN_SCORE", "0.4")),
        ]
        if self.env.get("SEARCH_AGENT_RSS_MAX_SOURCES"):
            command.extend(["--max-sources", str(self.env["SEARCH_AGENT_RSS_MAX_SOURCES"])])
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
            timeout=float(self.env.get("SEARCH_AGENT_SUBPROCESS_TIMEOUT", "60")),
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "rss_fetch.py failed")
        results = json.loads(completed.stdout or "[]")
        return results[:limit]

    def _ugc_runner(self, query: str, *, limit: int, lang: str, hunter_id: str):
        bili_path = shutil.which("bili")
        if not bili_path:
            raise MissingToolConfig("bili CLI is required for ugc_social_hunter Bilibili retrieval")

        command = [
            bili_path,
            "search",
            query,
            "--type",
            "video",
            "-n",
            str(limit),
            "--json",
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
            timeout=float(self.env.get("SEARCH_AGENT_SUBPROCESS_TIMEOUT", "60")),
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "bili search failed")
        payload = json.loads(completed.stdout or "{}")
        records = payload.get("data", []) if isinstance(payload, dict) else payload
        results = []
        for record in records[:limit]:
            bvid = record.get("bvid") or record.get("id") or ""
            url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
            metadata = {
                "author": record.get("author") or "unknown author",
                "play": record.get("play"),
                "duration": record.get("duration"),
            }
            results.append(
                {
                    "title": record.get("title", ""),
                    "url": url,
                    "source": "Bilibili",
                    "confidence": "low",
                    "full_text_fetched": False,
                    "metadata": metadata,
                    "fetcher": "bili-cli",
                }
            )
        return results

    def _marketing_skill_runner(self, query: str, *, limit: int, lang: str, hunter_id: str):
        selected = select_skill_adapters(
            query,
            domain="marketing",
            node_id="marketing_intelligence_hunter",
            limit=limit,
        )

        results = []
        for spec in selected[:limit]:
            from specialist_registry import SpecialistRegistry
            path = SpecialistRegistry(self.repo_root).resolve_prompt(spec["skill"])
            summary = (
                f"why_use: {spec['why_use']} "
                f"how_to_use: {spec['how_to_use']} "
                f"output_artifact: {spec['output_artifact']} "
                f"use_well: {spec['use_well']}"
            )
            results.append(
                {
                    "title": f"{spec['skill']} skill routing",
                    "url": str(path),
                    "summary": summary,
                    "source": "local marketing skill",
                    "confidence": "medium",
                    "full_text_fetched": True,
                    "method_source": True,
                    "evidence_role": spec["evidence_role"],
                    "selection_score": spec["selection_score"],
                    "fetcher": "marketing-skills-catalog",
                }
            )
        return results


    def _finance_runner(self, query: str, *, limit: int, lang: str, hunter_id: str):
        selected = select_skill_adapters(
            query,
            domain="finance",
            node_id="finance_data_hunter",
            limit=max(limit, 6),
        )
        selected_skills = {spec["skill"] for spec in selected}
        results = []

        if "funda-data" in selected_skills:
            spec = next(item for item in selected if item["skill"] == "funda-data")
            results.append(self._funda_setup_result(spec))
            if not self.env.get("FUNDA_API_KEY") or len(results) >= limit:
                return results[:limit]

        for spec in selected:
            if spec["skill"] == "yc-reader":
                results.extend(self._yc_reader_runner(query, limit=limit))
            elif spec["skill"] == "funda-data":
                continue
            elif spec["skill"] == "twitter-reader":
                results.extend(self._twitter_reader_runner(query, limit=limit, spec=spec))
            elif spec["skill"] == "opencli-reader":
                results.append(self._opencli_setup_result(spec))
            if len(results) >= limit:
                return results[:limit]

        ticker = self._ticker_from_query(query)
        if not ticker:
            if results:
                return results[:limit]
            raise MissingToolConfig("finance_data_hunter requires a ticker symbol or a configured finance adapter trigger")

        explicit_yfinance = self._adapter_triggered(query, "finance", "yfinance-data")
        if results and "yfinance-data" in selected_skills and not explicit_yfinance:
            return results[:limit]

        script = self.repo_root / "scripts" / "yfinance_snapshot.py"
        if not script.exists():
            raise MissingToolConfig(f"yfinance snapshot script not found: {script}")

        command = [
            sys.executable,
            str(script),
            "--ticker",
            ticker,
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
            timeout=float(self.env.get("SEARCH_AGENT_SUBPROCESS_TIMEOUT", "60")),
        )
        if completed.returncode == 3 or "YFINANCE_NOT_INSTALLED" in completed.stderr:
            raise MissingToolConfig("yfinance is required for finance_data_hunter; install requirements first")
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "yfinance_snapshot.py failed")
        results.extend(json.loads(completed.stdout or "[]"))
        return results[:limit]

    def _yc_reader_runner(self, query: str, *, limit: int) -> List[Dict[str, Any]]:
        endpoint = self._yc_endpoint_for_query(query)
        url = f"https://yc-oss.github.io/api/{endpoint}"
        try:
            with urlopen(url, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            return [
                self._finance_adapter_setup_result(
                    skill="yc-reader",
                    summary=f"yc-reader public API request failed for {endpoint}: {exc}",
                    confidence="low",
                    method_source=False,
                    fetcher="yc-reader",
                )
            ]

        records = payload if isinstance(payload, list) else [payload]
        results = []
        for record in records[:limit]:
            if not isinstance(record, dict):
                continue
            name = record.get("name") or record.get("slug") or "YC company"
            one_liner = record.get("one_liner") or record.get("oneLiner") or ""
            batch = record.get("batch") or ""
            team_size = record.get("team_size") or record.get("teamSize")
            hiring = record.get("isHiring")
            website = record.get("website") or record.get("url") or ""
            summary_parts = []
            if one_liner:
                summary_parts.append(one_liner)
            if batch:
                summary_parts.append(f"batch: {batch}")
            if team_size is not None:
                summary_parts.append(f"team_size: {team_size}")
            if hiring is not None:
                summary_parts.append(f"is_hiring: {hiring}")
            results.append(
                {
                    "title": f"YC company: {name}",
                    "url": website or url,
                    "summary": "; ".join(summary_parts) or f"YC public API record from {endpoint}",
                    "source": "yc-oss/api",
                    "confidence": "medium",
                    "full_text_fetched": True,
                    "fetcher": "yc-reader",
                    "metrics": {"yc_endpoint": endpoint},
                }
            )
        return results or [
            self._finance_adapter_setup_result(
                skill="yc-reader",
                summary=f"yc-reader returned no matching company rows from {endpoint}",
                confidence="low",
                method_source=False,
                fetcher="yc-reader",
            )
        ]

    def _funda_setup_result(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        if self.env.get("FUNDA_API_KEY"):
            summary = (
                "FUNDA_API_KEY detected. Use Funda REST for raw structured data or Funda MCP "
                "for research synthesis; endpoint selection is handled by the finance specialist."
            )
            confidence = "medium"
        else:
            summary = (
                "FUNDA_API_KEY or Funda MCP is required before funda-data can fetch real financial data. "
                "This row is a setup/routing note, not market evidence."
            )
            confidence = "low"
        return self._finance_adapter_setup_result(
            skill="funda-data",
            summary=summary,
            confidence=confidence,
            method_source=True,
            fetcher="funda-data",
            spec=spec,
        )

    def _twitter_reader_runner(self, query: str, *, limit: int, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        opencli_path = shutil.which("opencli")
        if not opencli_path:
            return [
                self._finance_adapter_setup_result(
                    skill="twitter-reader",
                    summary=(
                        "opencli is required for twitter-reader. Install opencli, enable the Browser Bridge, "
                        "and log in to x.com in Chrome. This read-only route never posts, likes, or replies."
                    ),
                    confidence="low",
                    method_source=True,
                    fetcher="twitter-reader",
                    spec=spec,
                )
            ]

        command = [
            opencli_path,
            "twitter",
            "search",
            query,
            "--filter",
            "live",
            "--limit",
            str(limit),
            "-f",
            "json",
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, env=self.env, check=False,
                timeout=float(self.env.get("SEARCH_AGENT_SUBPROCESS_TIMEOUT", "60")),
            )
        except subprocess.TimeoutExpired as exc:
            return [self._finance_adapter_setup_result(
                skill="twitter-reader",
                summary=f"opencli twitter search timed out after {exc.timeout} seconds; retrieval degraded without evidence.",
                confidence="low", method_source=True, fetcher="twitter-reader", spec=spec,
            )]
        if completed.returncode != 0:
            return [
                self._finance_adapter_setup_result(
                    skill="twitter-reader",
                    summary=f"opencli twitter search failed: {completed.stderr.strip() or completed.stdout.strip()}",
                    confidence="low",
                    method_source=True,
                    fetcher="twitter-reader",
                    spec=spec,
                )
            ]
        records = json.loads(completed.stdout or "[]")
        if isinstance(records, dict):
            records = records.get("data") or records.get("items") or []
        results = []
        for record in records[:limit]:
            title = f"Twitter/X: {record.get('author') or record.get('screen_name') or 'post'}"
            text = record.get("text") or record.get("content") or ""
            metrics = {
                key: record.get(key)
                for key in ["likes", "retweets", "replies", "views"]
                if record.get(key) is not None
            }
            results.append(
                {
                    "title": title,
                    "url": record.get("url") or "",
                    "summary": text,
                    "source": "Twitter/X via opencli",
                    "confidence": "low",
                    "full_text_fetched": True,
                    "fetcher": "twitter-reader",
                    "metrics": metrics,
                }
            )
        return results

    def _opencli_setup_result(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        opencli_path = shutil.which("opencli")
        if opencli_path:
            summary = (
                "opencli is installed. Use opencli list -f json to discover the exact read-only site command "
                "before fetching non-specialized finance or research sources."
            )
            confidence = "medium"
        else:
            summary = (
                "opencli is not installed. Install @jackwener/opencli and configure Browser Bridge before using "
                "generic read-only sources such as Reddit, Xueqiu, Eastmoney, Bloomberg, Reuters, or Substack."
            )
            confidence = "low"
        return self._finance_adapter_setup_result(
            skill="opencli-reader",
            summary=summary,
            confidence=confidence,
            method_source=True,
            fetcher="opencli-reader",
            spec=spec,
        )

    def _finance_adapter_setup_result(
        self,
        *,
        skill: str,
        summary: str,
        confidence: str,
        method_source: bool,
        fetcher: str,
        spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        path = self._finance_skill_path(skill)
        if spec:
            summary = (
                f"{summary} why_use: {spec.get('why_use', '')} "
                f"output_artifact: {spec.get('output_artifact', '')} "
                f"use_well: {spec.get('use_well', '')}"
            )
        return {
            "title": f"{skill} setup required" if confidence == "low" else f"{skill} routing",
            "url": str(path) if path else "",
            "summary": summary,
            "source": "local finance skill",
            "confidence": confidence,
            "full_text_fetched": bool(path),
            "method_source": method_source,
            "fetcher": fetcher,
        }

    def _matching_tasks(self, hunter_id: str, tasks: List[Dict[str, Any]], config: Dict[str, Any]):
        matching = []
        for task in tasks:
            assigned = task.get("assigned_hunter")
            if assigned == hunter_id:
                matching.append(task)
                continue
            source_layers = {str(layer) for layer in task.get("source_layers", [])}
            if source_layers.intersection(config["layers"]):
                matching.append(task)
        return matching

    def _queries_for_task(self, task: Dict[str, Any], config: Dict[str, Any]):
        query_buckets = {
            "zh": task.get("query_zh") or task.get("primary_queries") or [],
            "en": task.get("query_en") or [],
        }
        queries = []
        for lang in config["lang_order"]:
            for query in query_buckets.get(lang, []):
                if query:
                    queries.append((query, lang))
        return queries[:1]

    def _normalize_result(
        self,
        result: Dict[str, Any],
        task: Dict[str, Any],
        config: Dict[str, Any],
        index: int,
    ) -> Dict[str, Any]:
        url = result.get("url", "")
        description = result.get("description") or result.get("snippet") or result.get("summary") or ""
        content_excerpt = result.get("content_excerpt") or result.get("support_excerpt") or result.get("evidence_text")
        key_facts = result.get("key_facts")
        if key_facts is None:
            key_facts = [description] if description and config["source_type"] != "ugc_social" else []
        publisher = result.get("source") or result.get("publisher") or self._publisher_from_url(url)
        fetcher = result.get("fetcher")
        retrieval_tool = self._retrieval_tool_for(config["source_type"])
        if fetcher in {
            "bili-cli",
            "marketing-skills-catalog",
            "yc-reader",
            "funda-data",
            "twitter-reader",
            "opencli-reader",
        }:
            retrieval_tool = fetcher
        rationale_bits = [
            f"Search runner result for task {task.get('task_id', '')}",
            "requires Source QA before analysis",
        ]
        if fetcher:
            rationale_bits.append(f"fetcher={fetcher}")
        if result.get("method_source"):
            rationale_bits.append("method source, not market evidence")
        if result.get("relevance_score") is not None:
            rationale_bits.append(f"relevance_score={result['relevance_score']}")
        return {
            "source_id": f"{config['prefix']}{index:03d}",
            "title": result.get("title", ""),
            "publisher": publisher,
            "source_type": config["source_type"],
            "publish_date": result.get("publish_date") or result.get("publishedDate") or result.get("published") or "",
            "url": url,
            "canonical_url": self._canonical_url(url),
            "confidence": result.get("confidence") or "medium",
            "key_facts": list(key_facts),
            **({"content_excerpt": content_excerpt} if content_excerpt else {}),
            "full_text_fetched": bool(result.get("full_text_fetched", False)),
            "collected_by": config["collector"],
            "confidence_rationale": "; ".join(rationale_bits) + ".",
            "retrieval_tool": retrieval_tool,
            "relevance_score": result.get("relevance_score"),
            "metrics": result.get("metrics"),
            "metadata": result.get("metadata", {}),
            "method_source": bool(result.get("method_source", False)),
        }

    def _canonical_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlsplit(url)
        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ]
        return urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/") or parsed.path,
                urlencode(filtered_query),
                "",
            )
        )

    def _publisher_from_url(self, url: str) -> str:
        return urlsplit(url).netloc.lower() or "unknown"

    def _rss_keywords_arg(self, query: str) -> str:
        return ",".join(part for part in query.split() if part)

    def _ticker_from_query(self, query: str) -> str:
        for token in query.replace("(", " ").replace(")", " ").replace(",", " ").split():
            cleaned = "".join(char for char in token if char.isalnum() or char in {".", "-"})
            if cleaned.isupper() and 1 <= len(cleaned) <= 8 and any(char.isalpha() for char in cleaned):
                return cleaned
        return ""

    def _yc_endpoint_for_query(self, query: str) -> str:
        normalized = query.lower().replace("_", "-")
        if "fintech" in normalized:
            return "industries/fintech.json"
        if "healthcare" in normalized or "health care" in normalized:
            return "industries/healthcare.json"
        if "developer tool" in normalized or "devtool" in normalized:
            return "tags/developer-tools.json"
        if "ai" in normalized or "artificial intelligence" in normalized:
            return "tags/ai.json"
        if "hiring" in normalized:
            return "companies/hiring.json"
        if "top" in normalized:
            return "companies/top.json"
        for season in ["winter", "spring", "summer", "fall"]:
            marker = f"{season}-"
            if marker in normalized:
                year = normalized.split(marker, 1)[1][:4]
                if year.isdigit():
                    return f"batches/{season}-{year}.json"
        return "companies/top.json"

    def _adapter_triggered(self, query: str, domain: str, skill: str) -> bool:
        query_l = query.lower()
        from workflow_contracts import get_skill_adapter_matrix

        for adapter in get_skill_adapter_matrix(domain).get(domain, []):
            if adapter["skill"] != skill:
                continue
            return any(str(term).lower() in query_l for term in adapter.get("trigger_terms", []))
        return False

    def _finance_skill_path(self, skill: str) -> Optional[Path]:
        try:
            from specialist_registry import SpecialistRegistry
            return SpecialistRegistry(self.repo_root).resolve_prompt(skill)
        except (KeyError, ValueError):
            return None

    def _retrieval_tool_for(self, source_type: str) -> str:
        return {
            "rss_news": "finance-rss-reader",
            "finance_data": "yfinance-data",
            "ugc_social": "bili-cli",
            "marketing_intelligence": "marketing-skills-catalog",
        }.get(source_type, "firecrawl")

    def _config_for(self, hunter_id: str) -> Dict[str, Any]:
        if hunter_id not in HUNTER_CONFIG:
            raise KeyError(f"Unknown source hunter: {hunter_id}")
        return HUNTER_CONFIG[hunter_id]


class MissingToolConfig(RuntimeError):
    """Raised when a real retrieval tool is unavailable or not configured."""
