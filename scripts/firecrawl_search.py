#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firecrawl 深度搜索封装
-----------------------
薄封装 Firecrawl Search API，命令行调用：

    python3 scripts/firecrawl_search.py --query "Meituan vs Eleme market share 2026" --limit 5 --lang en

标准输出为 JSON 数组，每条包含：
    { title, url, description, source_type: "firecrawl", confidence: "medium", publish_date? }

适用场景：Seeking Alpha 分析师报告 / FT / Bloomberg / 公司 IR 官网 / SEC EDGAR 等
JS 渲染或需要深度抓取的英文页面。

环境变量：
    FIRECRAWL_API_KEY   必填。示例 key 见 CLAUDE.md（生产环境请替换为自己的）。

依赖：requests（大多数环境已安装；未安装时会打印安装提示并退出）
"""

import argparse
import json
import os
import sys
import time

FIRECRAWL_ENDPOINT = "https://api.firecrawl.dev/v1/search"


def _require_requests():
    try:
        import requests  # noqa: WPS433 (lazy import by design)
        return requests
    except ImportError:
        print(
            "[firecrawl_search] 缺少依赖 'requests'，请先安装：pip install requests",
            file=sys.stderr,
        )
        sys.exit(2)


def firecrawl_search(
    query: str,
    limit: int,
    lang: str,
    api_key: str,
    timeout: int = 60,
    retries: int = 2,
    backoff_seconds: float = 1.5,
):
    """调用 Firecrawl Search API，返回标准化的结果列表。"""
    requests = _require_requests()
    payload = {
        "query": query,
        "limit": limit,
        "lang": lang,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = None
    last_error = None
    request_timeout = (10, timeout)
    for attempt in range(retries + 1):
        try:
            resp = requests.post(FIRECRAWL_ENDPOINT, json=payload, headers=headers, timeout=request_timeout)
            break
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                raise
            time.sleep(backoff_seconds * (attempt + 1))

    if resp is None:
        raise last_error

    resp.raise_for_status()
    data = resp.json()

    # Firecrawl 返回结构：{ success: true, data: [ { title, url, description, ... } ] }
    raw_items = data.get("data") or data.get("results") or []
    normalized = []
    for idx, item in enumerate(raw_items, 1):
        normalized.append(
            {
                "source_id": f"FC{idx:03d}",
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description") or item.get("snippet", ""),
                "publish_date": item.get("publishedDate") or item.get("date") or "",
                "source_type": "firecrawl",
                "confidence": "medium",
            }
        )
    return normalized


def main():
    parser = argparse.ArgumentParser(description="Firecrawl 深度搜索薄封装")
    parser.add_argument("--query", required=True, help="搜索关键词")
    parser.add_argument("--limit", type=int, default=5, help="返回结果数量 (默认 5)")
    parser.add_argument("--lang", default="en", help="语言 (默认 en，可选 zh)")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP 超时秒数")
    parser.add_argument("--retries", type=int, default=2, help="瞬时网络失败重试次数 (默认 2)")
    args = parser.parse_args()

    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        print(
            "[firecrawl_search] 未检测到 FIRECRAWL_API_KEY 环境变量。\n"
            "请先执行： export FIRECRAWL_API_KEY=your-key",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        results = firecrawl_search(
            query=args.query,
            limit=args.limit,
            lang=args.lang,
            api_key=api_key,
            timeout=args.timeout,
            retries=args.retries,
        )
    except Exception as e:
        # requests.HTTPError / RequestException 都归一处理，避免顶层再 import
        msg = str(e)
        print(f"[firecrawl_search] 请求失败: {msg[:300]}", file=sys.stderr)
        sys.exit(3)

    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
