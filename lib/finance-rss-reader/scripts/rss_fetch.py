#!/usr/bin/env python3
"""
finance-rss-reader: 财经 RSS 拉取与关键词过滤脚本
依赖：标准库 urllib (无外部依赖)
"""
import argparse
import json
import sys
import re
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl

def load_sources(config_path):
    """加载 RSS 源配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_rss(url, timeout=10):
    """
    拉取 RSS XML，返回原始文本

    改进:
    - 增加 SSL 上下文处理
    - 更详细的错误日志
    - 支持重定向
    """
    try:
        # 创建 SSL 上下文，允许未验证证书 (某些 RSS 源需要)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        })

        with urlopen(req, timeout=timeout, context=ctx) as resp:
            content_type = resp.headers.get('Content-Type', '')
            encoding = 'utf-8'

            # 尝试从 Content-Type 提取编码
            if 'charset=' in content_type:
                try:
                    encoding = content_type.split('charset=')[-1].split(';')[0].strip()
                except:
                    pass

            return resp.read().decode(encoding, errors='replace')

    except HTTPError as e:
        print(f"[WARN] HTTP {e.code} for {url}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"[WARN] URL error for {url}: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[WARN] Fetch error for {url}: {str(e)}", file=sys.stderr)
        return None

def parse_rss_simple(xml_text, source_name=""):
    """
    简单解析 RSS/Atom，不依赖 feedparser

    改进:
    - 支持更多日期格式
    - 更健壮的 URL 提取
    - 处理 CDATA 和 HTML 实体
    """
    items = []

    # 提取 <item> 或 <entry>
    blocks = re.findall(r'<(?:item|entry)>(.*?)</(?:item|entry)>', xml_text, re.DOTALL | re.IGNORECASE)

    for block in blocks:
        try:
            def extract(tag, text):
                # 支持多种标签格式
                patterns = [
                    rf'<{tag}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>',
                    rf'<{tag}[^>]*>(.*?)</{tag}>'
                ]
                for pattern in patterns:
                    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                    if m:
                        return m.group(1).strip()
                return ''

            # 提取标题
            title = extract('title', block)
            title = re.sub(r'<[^>]+>', '', title)  # 去除 HTML 标签
            title = re.sub(r'&[a-z]+;', '', title)  # 去除 HTML 实体
            title = title.strip()

            # 提取链接
            link = extract('link', block)
            if not link or '<' in link:
                # 尝试从属性中提取
                link_match = re.search(r'<link[^>]+href=["\']([^"\']+)["\']', block)
                if link_match:
                    link = link_match.group(1)

            # 提取发布日期
            pub = (extract('pubDate', block) or
                   extract('published', block) or
                   extract('updated', block) or
                   extract('dc:date', block))

            # 提取摘要
            summary = (extract('description', block) or
                      extract('summary', block) or
                      extract('content', block))
            summary = re.sub(r'<[^>]+>', '', summary)  # 去除 HTML
            summary = re.sub(r'&[a-z]+;', '', summary)  # 去除实体
            summary = summary.strip()[:300]

            if title and link and link.startswith('http'):
                items.append({
                    'title': title,
                    'url': link,
                    'published': pub[:25] if pub else '',
                    'summary': summary
                })

        except Exception as e:
            print(f"[WARN] Parse error in block from {source_name}: {str(e)[:100]}", file=sys.stderr)
            continue

    return items

def relevance_score(item, keywords):
    """
    关键词匹配打分 0-1

    改进:
    - 支持部分匹配
    - 标题权重更高
    """
    title = item.get('title', '').lower()
    summary = item.get('summary', '').lower()

    title_hits = sum(1 for kw in keywords if kw.lower() in title)
    summary_hits = sum(1 for kw in keywords if kw.lower() in summary)

    # 标题匹配权重 2x
    total_hits = title_hits * 2 + summary_hits
    max_possible = len(keywords) * 3  # 假设标题和摘要都匹配

    return min(total_hits / max(max_possible, 1), 1.0)

def is_within_days(pub_str, days):
    """
    检查文章是否在 N 天内

    改进:
    - 支持更多日期格式
    - 时区处理
    """
    if not pub_str:
        return True  # 无日期则保留

    try:
        # 移除时区缩写 (如 GMT, EST)
        pub_str_clean = re.sub(r'\s+[A-Z]{3,4}$', '', pub_str.strip())

        # 尝试多种格式
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%a, %d %b %Y %H:%M:%S',
            '%d %b %Y %H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d'
        ]

        pub_date = None
        for fmt in formats:
            try:
                pub_date = datetime.strptime(pub_str_clean[:len(fmt)], fmt)
                break
            except ValueError:
                continue

        if pub_date:
            # 设置时区 (假设 UTC)
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)

            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            return pub_date >= cutoff

    except Exception as e:
        print(f"[WARN] Date parse error for '{pub_str}': {e}", file=sys.stderr)

    return True  # 解析失败则保留

def build_seekingalpha_url(ticker):
    """构建 SeekingAlpha RSS URL"""
    return f"https://seekingalpha.com/api/sa/combined/{ticker.upper()}.xml"

def main():
    parser = argparse.ArgumentParser(description='财经 RSS 拉取与过滤')
    parser.add_argument('--keywords', required=True, help='关键词，逗号分隔')
    parser.add_argument('--ticker', default='', help='股票代码，用于 SeekingAlpha')
    parser.add_argument('--days', type=int, default=14, help='拉取最近 N 天')
    parser.add_argument('--sources-config', required=True, help='RSS 源配置 JSON 路径')
    parser.add_argument('--min-score', type=float, default=0.3, help='最低相关性分数')
    parser.add_argument('--max-sources', type=int, default=0, help='最大源数量 (0=无限制)')
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]
    sources = load_sources(args.sources_config)

    # 限制源数量 (避免超时)
    if args.max_sources > 0:
        sources = sources[:args.max_sources]
        print(f"[INFO] Limited to {len(sources)} sources", file=sys.stderr)

    # 如果有 ticker，动态添加 SeekingAlpha
    if args.ticker:
        sources.append({
            "name": "SeekingAlpha",
            "url": build_seekingalpha_url(args.ticker),
            "region": "en",
            "type": "分析"
        })

    results = []
    success_count = 0

    for idx, source in enumerate(sources, 1):
        source_name = source.get('name', 'Unknown')
        print(f"[{idx}/{len(sources)}] Fetching {source_name}...", file=sys.stderr)

        xml = fetch_rss(source['url'])
        if not xml:
            continue

        items = parse_rss_simple(xml, source_name)
        print(f"  -> Parsed {len(items)} items", file=sys.stderr)

        success_count += 1

        for item in items:
            if not is_within_days(item['published'], args.days):
                continue

            score = relevance_score(item, keywords)
            if score >= args.min_score:
                item['source'] = source_name
                item['region'] = source.get('region', 'unknown')
                item['source_type'] = source.get('type', '媒体')
                item['relevance_score'] = round(score, 2)
                results.append(item)

    # 按相关性降序
    results.sort(key=lambda x: x['relevance_score'], reverse=True)

    print(f"[INFO] Fetched from {success_count}/{len(sources)} sources, {len(results)} relevant items", file=sys.stderr)
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
