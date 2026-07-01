#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索引擎调度模块 - 多源多层搜索策略
基于财报分析 Workflow v2.0 Step 2 设计
集成 RSS 聚合信息流
"""

import json
import subprocess
import os
import re
from typing import List, Dict, Tuple
from collections import defaultdict
from datetime import datetime


class SearchEngine:
    """多源多层搜索引擎调度器 + RSS 聚合"""

    # 高质量深度分析网站列表
    DEEP_ANALYSIS_SITES = [
        "seekingalpha.com",
        "ft.com",
        "reuters.com",
        "bloomberg.com",
        "wsj.com",
        "fool.com",
        "benzinga.com"
    ]

    def __init__(self):
        self.results_cache = {}
        self.source_id_counter = 0
        self.rss_reader_path = self._find_finance_rss_reader()

    def _find_finance_rss_reader(self) -> str:
        """查找 finance-rss-reader skill 路径"""
        # 首先尝试本地嵌入路径
        embedded_path = os.path.join(os.path.dirname(__file__), "finance-rss-reader")
        if os.path.exists(embedded_path):
            return embedded_path

        # 其次尝试标准 skill 路径
        possible_paths = [
            "/home/gem/.claude/skills/finance-rss-reader",
            "/home/gem/workspace/.claude/skills/finance-rss-reader"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return ""

    def multi_source_search(
        self,
        keywords: List[str],
        framework_name: str,
        params: dict,
        max_results_per_keyword: int = 10,
        enable_layered_search: bool = True
    ) -> Tuple[List[Dict], Dict[str, str]]:
        """
        多层搜索策略 - 基于财报分析 Workflow v2.0

        Args:
            keywords: 关键词列表
            framework_name: 当前框架名称
            params: 提取的参数 (公司名、期间等)
            max_results_per_keyword: 每个关键词返回的最大结果数
            enable_layered_search: 是否启用分层搜索策略

        Returns:
            Tuple[content_pool, citations]: (内容池, 引文映射)
        """
        content_pool = []
        citations = {}

        if enable_layered_search:
            # 分层搜索策略
            print(f"[SearchEngine] 启用分层搜索策略")

            # 第一层: 官方原始来源 (必须有)
            layer1_content = self._search_layer1_official_sources(params, framework_name)
            content_pool.extend(layer1_content)

            # 第二层: 业绩会 Transcript / 深度材料 (必须有)
            layer2_content = self._search_layer2_transcripts(params, framework_name)
            content_pool.extend(layer2_content)

            # 第三层: 深度分析文章
            layer3_content = self._search_layer3_deep_analysis(keywords, params, framework_name)
            content_pool.extend(layer3_content)

            # 第四层: 同行交叉验证
            if params.get("竞争对手"):
                layer4_content = self._search_layer4_competitors(params, framework_name)
                content_pool.extend(layer4_content)

            # 第五层: RSS 聚合信息流 (新增)
            if self.rss_reader_path:
                print(f"[Layer RSS] 启用 RSS 聚合信息流...")
                rss_content = self._search_rss_feeds(params, framework_name)
                content_pool.extend(rss_content)
            else:
                print(f"[Layer RSS] finance-rss-reader skill 未找到，跳过 RSS 聚合")
        else:
            # 传统并行搜索
            all_results = []
            for keyword in keywords:
                baidu_results = self._call_baidu_search(keyword, max_results_per_keyword)
                all_results.extend(baidu_results)

                realtime_results = self._call_realtime_search(keyword, max_results_per_keyword)
                all_results.extend(realtime_results)

            deduplicated_results = self._deduplicate_and_rank(all_results)

            # 转换为统一格式
            for result in deduplicated_results[:max_results_per_keyword * len(keywords)]:
                content_data = self._build_source_metadata(
                    url=result.get("url"),
                    title=result.get("title"),
                    snippet=result.get("snippet"),
                    source_type="web_search",
                    framework=framework_name
                )
                content_pool.append(content_data)

        # 构建引文映射
        for item in content_pool:
            citations[item["source_id"]] = item["url"]

        return content_pool, citations

    def _search_layer1_official_sources(self, params: dict, framework: str) -> List[Dict]:
        """
        第一层: 官方原始来源 (财报PDF、10-K等)

        使用 Brave Search 定向查询官方文档
        """
        print(f"[Layer 1] 搜索官方原始来源...")
        results = []

        company = params.get("公司名", params.get("主题", ""))
        period = params.get("期间", "")

        if not company:
            return results

        # 构造精准查询
        # 例如: "百度 2026Q1 财报 site:ir.baidu.com filetype:pdf"
        queries = [
            f"{company} {period} 财报 PDF",
            f"{company} {period} earnings report filetype:pdf",
            f"{company} {period} 10-K site:sec.gov",
            f"{company} {period} investor relations"
        ]

        for query in queries:
            # 调用 realtime-search (支持 Brave Search)
            brave_results = self._call_brave_search(query, max_results=3, search_type="official", framework=framework)
            results.extend(brave_results)

        print(f"[Layer 1] 找到 {len(results)} 条官方来源")
        return results

    def _search_layer2_transcripts(self, params: dict, framework: str) -> List[Dict]:
        """
        第二层: 业绩会 Transcript (必须有)

        搜索业绩会电话会议记录
        """
        print(f"[Layer 2] 搜索业绩会 Transcript...")
        results = []

        company = params.get("公司名", params.get("主题", ""))
        period = params.get("期间", "")

        if not company:
            return results

        queries = [
            f"{company} {period} earnings call transcript",
            f"{company} {period} 业绩会 实录",
            f"{company} {period} conference call"
        ]

        for query in queries:
            brave_results = self._call_brave_search(query, max_results=2, search_type="transcript", framework=framework)
            results.extend(brave_results)

        print(f"[Layer 2] 找到 {len(results)} 条业绩会记录")
        return results

    def _search_layer3_deep_analysis(self, keywords: List[str], params: dict, framework: str) -> List[Dict]:
        """
        第三层: 深度分析文章

        定向搜索高质量分析网站
        """
        print(f"[Layer 3] 搜索深度分析文章...")
        results = []

        for keyword in keywords[:3]:  # 限制关键词数量
            for site in self.DEEP_ANALYSIS_SITES[:3]:  # 只搜索前3个网站
                query = f"{keyword} site:{site}"
                site_results = self._call_brave_search(query, max_results=2, search_type="deep_analysis", framework=framework)
                results.extend(site_results)

        print(f"[Layer 3] 找到 {len(results)} 条深度分析")
        return results

    def _search_layer4_competitors(self, params: dict, framework: str) -> List[Dict]:
        """
        第四层: 同行交叉验证

        搜索竞争对手的相关信息
        """
        print(f"[Layer 4] 同行交叉验证...")
        results = []

        competitors = params.get("竞争对手", [])
        if isinstance(competitors, str):
            competitors = [competitors]

        period = params.get("期间", "")

        for competitor in competitors[:2]:  # 限制竞争对手数量
            query = f"{competitor} {period} 财报"
            comp_results = self._call_brave_search(query, max_results=2, search_type="competitor", framework=framework)
            results.extend(comp_results)

        print(f"[Layer 4] 找到 {len(results)} 条竞争对手信息")
        return results

    def _search_rss_feeds(self, params: dict, framework: str) -> List[Dict]:
        """
        RSS 聚合信息流搜索

        调用 finance-rss-reader skill 获取财经 RSS 聚合
        """
        print(f"[Layer RSS] 从财经 RSS 源聚合信息...")
        results = []

        company = params.get("公司名", params.get("主题", ""))
        ticker = params.get("股票代码", params.get("ticker", ""))
        period = params.get("期间", "")

        if not company:
            return results

        # 提取关键词
        keywords = [company]
        if ticker:
            keywords.append(ticker)

        # 构造调用参数
        rss_script = os.path.join(self.rss_reader_path, "scripts/rss_fetch.py")
        rss_config = os.path.join(self.rss_reader_path, "references/rss_sources.json")

        if not os.path.exists(rss_script) or not os.path.exists(rss_config):
            print(f"[Layer RSS] RSS 脚本或配置文件不存在，跳过")
            return results

        try:
            # 调用 RSS 拉取脚本
            cmd = [
                "python3", rss_script,
                "--keywords", ",".join(keywords),
                "--ticker", ticker if ticker else "",
                "--days", "14",
                "--sources-config", rss_config,
                "--min-score", "0.4",
                "--max-sources", "15"  # 限制源数量，避免超时
            ]

            print(f"[Layer RSS] 执行: {' '.join(cmd)}")
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 增加超时时间到 60 秒
            )

            if proc.returncode != 0:
                print(f"[Layer RSS] RSS 拉取失败: {proc.stderr}")
                return results

            # 解析返回的 JSON
            rss_items = json.loads(proc.stdout)
            print(f"[Layer RSS] 找到 {len(rss_items)} 条 RSS 条目")

            # 转换为统一格式 (只取前 10 条高相关结果)
            for item in rss_items[:10]:
                source_data = self._build_source_metadata(
                    url=item["url"],
                    title=item["title"],
                    snippet=item.get("summary", ""),
                    source_type="rss_feed",
                    framework=framework,
                    publish_date=item.get("published", ""),
                    confidence="medium",
                    notes=f"来自 RSS: {item.get('source', 'Unknown')}, 相关性: {item.get('relevance_score', 0)}"
                )

                # 将 RSS 原始数据附加到 notes
                source_data["rss_metadata"] = {
                    "source_name": item.get("source", "Unknown"),
                    "relevance_score": item.get("relevance_score", 0),
                    "region": item.get("region", "unknown"),
                    "source_type_rss": item.get("source_type", "媒体")
                }

                results.append(source_data)

            print(f"[Layer RSS] 转换完成，返回 {len(results)} 条结果")

        except subprocess.TimeoutExpired:
            print(f"[Layer RSS] RSS 拉取超时")
        except json.JSONDecodeError as e:
            print(f"[Layer RSS] JSON 解析失败: {e}")
        except Exception as e:
            print(f"[Layer RSS] RSS 拉取异常: {e}")

        return results

    def _call_brave_search(self, query: str, max_results: int = 5, search_type: str = "general", framework: str = "") -> List[Dict]:
        """
        调用 Brave Search (通过 realtime-search skill)

        Args:
            query: 搜索查询
            max_results: 最大结果数
            search_type: 搜索类型标签 (official/transcript/deep_analysis/competitor/general)
            framework: 框架名称

        Returns:
            List[Dict]: 结构化源数据列表
        """
        try:
            print(f"[Brave Search] 查询: {query} (类型: {search_type})")

            # 实际使用时调用: skill realtime-search "{query}" --engine brave
            # 这里先返回模拟数据

            results = []

            # 模拟返回结果
            mock_result = {
                "title": f"{query} - Brave搜索结果",
                "url": f"https://example.com/brave/{query.replace(' ', '-')}",
                "snippet": f"关于{query}的搜索结果...",
                "publish_date": "2026-06-30"
            }

            # 构建结构化源元数据
            source_data = self._build_source_metadata(
                url=mock_result["url"],
                title=mock_result["title"],
                snippet=mock_result["snippet"],
                source_type=self._map_search_type_to_source_type(search_type),
                framework=framework,
                publish_date=mock_result.get("publish_date"),
                confidence=self._calculate_confidence(search_type),
                notes=f"来自 Brave Search - {search_type}"
            )

            results.append(source_data)

            return results
        except Exception as e:
            print(f"[Brave Search] 调用失败: {e}")
            return []

    def _map_search_type_to_source_type(self, search_type: str) -> str:
        """映射搜索类型到源类型"""
        mapping = {
            "official": "official_report",
            "transcript": "earnings_call",
            "deep_analysis": "analysis_article",
            "competitor": "competitor_data",
            "rss": "rss_feed",
            "general": "web_search"
        }
        return mapping.get(search_type, "web_search")

    def _calculate_confidence(self, search_type: str) -> str:
        """根据搜索类型计算置信度"""
        confidence_map = {
            "official": "high",
            "transcript": "high",
            "deep_analysis": "medium",
            "competitor": "medium",
            "general": "low"
        }
        return confidence_map.get(search_type, "low")

    def _build_source_metadata(
        self,
        url: str,
        title: str,
        snippet: str = "",
        source_type: str = "web_search",
        framework: str = "",
        publish_date: str = None,
        confidence: str = "medium",
        notes: str = ""
    ) -> Dict:
        """
        构建结构化源元数据

        字段说明 (来自 Step 2):
        - source_id: 唯一标识符
        - title: 标题
        - publisher: 发布者/来源网站
        - source_type: 来源类型 (official_report/earnings_call/analysis_article等)
        - publish_date: 发布日期
        - data_period: 数据期间
        - url_or_path: URL或本地路径
        - confidence: 置信度 (high/medium/low)
        - notes: 备注
        """
        self.source_id_counter += 1
        source_id = f"source_{framework}_{self.source_id_counter}" if framework else f"source_{self.source_id_counter}"

        # 提取发布者 (域名)
        publisher = self._extract_publisher_from_url(url)

        return {
            "id": source_id,  # 兼容旧字段
            "source_id": source_id,
            "title": title,
            "publisher": publisher,
            "source_type": source_type,
            "publish_date": publish_date or "N/A",
            "data_period": "N/A",  # 需要从内容中提取
            "url": url,
            "url_or_path": url,
            "confidence": confidence,
            "notes": notes,
            "snippet": snippet,
            "content": "",  # 延迟加载
            "framework": framework,
            "dimension": ""  # 框架维度,延迟填充
        }

    def _extract_publisher_from_url(self, url: str) -> str:
        """从URL提取发布者域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # 去掉 www. 前缀
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "Unknown"

    def _call_baidu_search(self, keyword: str, max_results: int) -> List[Dict]:
        """
        调用 baidu-search skill

        返回格式:
        [
            {
                "title": "标题",
                "url": "链接",
                "snippet": "摘要",
                "source": "baidu-search"
            }
        ]
        """
        try:
            print(f"[SearchEngine] 调用 baidu-search: {keyword}")

            # 通过 Skill 工具调用 (这里先返回模拟数据,实际应调用skill)
            # 实际使用时需要调用: skill baidu-search --query "{keyword}" --num {max_results}

            results = [
                {
                    "title": f"{keyword} - 搜索结果示例",
                    "url": f"https://example.com/baidu/{keyword.replace(' ', '-')}",
                    "snippet": f"关于{keyword}的搜索结果摘要...",
                    "source": "baidu-search",
                    "keyword": keyword
                }
            ]

            return results
        except Exception as e:
            print(f"[SearchEngine] baidu-search 调用失败: {e}")
            return []

    def _call_realtime_search(self, keyword: str, max_results: int) -> List[Dict]:
        """
        调用 realtime-search skill

        返回格式: 与 baidu-search 相同
        """
        try:
            print(f"[SearchEngine] 调用 realtime-search: {keyword}")

            # 实际使用时需要调用: skill realtime-search "{keyword}"

            results = [
                {
                    "title": f"{keyword} - 实时资讯",
                    "url": f"https://example.com/realtime/{keyword.replace(' ', '-')}",
                    "snippet": f"关于{keyword}的最新资讯...",
                    "source": "realtime-search",
                    "keyword": keyword
                }
            ]

            return results
        except Exception as e:
            print(f"[SearchEngine] realtime-search 调用失败: {e}")
            return []

    def _call_enterprise_search(self, keyword: str, max_results: int) -> List[Dict]:
        """
        调用 enterprise-search skill (企业内部知识)

        仅在百度内网环境可用
        """
        try:
            print(f"[SearchEngine] 调用 enterprise-search: {keyword}")

            # 检查是否在内网环境
            if not self._is_internal_network():
                print("[SearchEngine] 非内网环境,跳过 enterprise-search")
                return []

            # 实际使用时需要调用: skill enterprise-search --query "{keyword}"

            results = []
            return results
        except Exception as e:
            print(f"[SearchEngine] enterprise-search 调用失败: {e}")
            return []

    def _is_internal_network(self) -> bool:
        """检查是否在内网环境"""
        # 简化判断: 检查环境变量或网络连通性
        return os.getenv("BAIDU_INTERNAL_NETWORK") == "true"

    def _deduplicate_and_rank(self, results: List[Dict]) -> List[Dict]:
        """
        去重和排序

        去重规则: 相同 URL 只保留一个
        排序规则: 优先级 baidu-search > realtime-search > enterprise-search
        """
        seen_urls = set()
        unique_results = []

        # 排序优先级
        source_priority = {
            "baidu-search": 1,
            "realtime-search": 2,
            "enterprise-search": 3
        }

        # 按优先级排序
        sorted_results = sorted(results, key=lambda x: source_priority.get(x["source"], 99))

        for result in sorted_results:
            url = result.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results

    def extract_content_from_url(self, url: str, content_type: str = "html") -> Dict:
        """
        从 URL 提取内容

        Args:
            url: 目标URL
            content_type: 内容类型 (html/pdf/ku_doc)

        Returns:
            Dict: {
                "url": "...",
                "content": "...",
                "content_type": "...",
                "title": "..."
            }
        """
        if content_type == "pdf":
            return self._extract_pdf_content(url)
        elif content_type == "ku_doc":
            return self._extract_ku_doc(url)
        else:
            return self._extract_html_content(url)

    def _extract_pdf_content(self, url: str) -> Dict:
        """调用 pdf skill 提取PDF内容"""
        print(f"[SearchEngine] 提取 PDF 内容: {url}")

        # 实际使用时需要调用: skill pdf --extract "{url}"

        return {
            "url": url,
            "content": "PDF内容提取结果...",
            "content_type": "pdf",
            "title": "PDF文档标题"
        }

    def _extract_ku_doc(self, url: str) -> Dict:
        """调用 ku-doc-manage skill 提取知识库文档"""
        print(f"[SearchEngine] 提取知识库文档: {url}")

        # 实际使用时需要调用: skill ku-doc-manage query-content --url "{url}"

        return {
            "url": url,
            "content": "知识库文档内容...",
            "content_type": "ku_doc",
            "title": "知识库文档标题"
        }

    def _extract_html_content(self, url: str) -> Dict:
        """提取HTML正文"""
        print(f"[SearchEngine] 提取 HTML 内容: {url}")

        # 简化实现: 实际应使用正文提取工具

        return {
            "url": url,
            "content": "HTML正文内容...",
            "content_type": "html",
            "title": "网页标题"
        }


if __name__ == "__main__":
    # 测试用例
    search_engine = SearchEngine()

    keywords = ["高德地图 新功能", "高德地图 2026"]
    params = {"公司名": "高德地图", "期间": "2026Q1"}

    content_pool, citations = search_engine.multi_source_search(
        keywords=keywords,
        framework_name="财报快评",
        params=params,
        max_results_per_keyword=5,
        enable_layered_search=True
    )

    print(f"\n搜索结果数: {len(content_pool)}")
    for idx, item in enumerate(content_pool, 1):
        print(f"\n结果 {idx}:")
        print(f"  标题: {item['title']}")
        print(f"  来源类型: {item['source_type']}")
        print(f"  置信度: {item['confidence']}")
        print(f"  URL: {item['url']}")
