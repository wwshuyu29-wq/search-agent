#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executable Source Hunter adapter for the R0 retrieval vertical slice.

The executor turns SearchPlan tasks into SourceListFragment rows. It is small on
purpose: tools are injectable for tests and Codex packet execution, while the
default runner uses the local Firecrawl wrapper only when its key is configured.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


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

        runner = self.search_runner or self._firecrawl_runner
        source_index = 1
        for task in tasks:
            for query, lang in self._queries_for_task(task, config):
                try:
                    results = runner(query, limit=limit_per_query, lang=lang, hunter_id=hunter_id)
                except MissingToolConfig as exc:
                    fragment["execution_status"] = "skipped_missing_tool_config"
                    fragment["warnings"].append(str(exc))
                    return fragment
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
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "firecrawl_search.py failed")
        return json.loads(completed.stdout or "[]")

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
        description = result.get("description") or result.get("snippet") or ""
        return {
            "source_id": f"{config['prefix']}{index:03d}",
            "title": result.get("title", ""),
            "publisher": self._publisher_from_url(url),
            "source_type": config["source_type"],
            "publish_date": result.get("publish_date") or result.get("publishedDate") or "",
            "url": url,
            "canonical_url": self._canonical_url(url),
            "confidence": result.get("confidence") or "medium",
            "key_facts": [description] if description else [],
            "full_text_fetched": bool(result.get("full_text_fetched", False)),
            "collected_by": config["collector"],
            "confidence_rationale": (
                f"Search runner result for task {task.get('task_id', '')}; "
                f"requires Source QA before analysis."
            ),
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

    def _config_for(self, hunter_id: str) -> Dict[str, Any]:
        if hunter_id not in HUNTER_CONFIG:
            raise KeyError(f"Unknown source hunter: {hunter_id}")
        return HUNTER_CONFIG[hunter_id]


class MissingToolConfig(RuntimeError):
    """Raised when a real retrieval tool is unavailable or not configured."""
