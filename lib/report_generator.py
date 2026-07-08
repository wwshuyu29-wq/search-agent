#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成模块 - 按框架结构生成分析报告,带引文链接
"""

from datetime import datetime
from collections import Counter
from pathlib import Path
import sys
from typing import Any, List, Dict, Optional

LIB_DIR = Path(__file__).resolve().parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from workflow_contracts import recommend_report_family


class ReportGenerator:
    """分析报告生成器"""

    AI_STYLE_REPLACEMENTS = {
        "值得注意的是，": "",
        "值得注意的是,": "",
        "从多个维度来看，": "",
        "从多个维度来看,": "",
        "综上所述，": "",
        "综上所述,": "",
        "总体而言，": "",
        "总体而言,": "",
        "可以看出，": "",
        "可以看出,": "",
    }

    # 报告模板
    REPORT_TEMPLATES = {
        "财报快评": """# {subject} 财报快评

**分析对象**: {subject}
**分析期间**: {period}
**生成时间**: {timestamp}

---

## 一句话结论

{conclusion}

---

## 三个关键发现

1. {finding_1}
2. {finding_2}
3. {finding_3}

---

## 财务表现

| 指标 | 本期 | 同比 | 环比 | 判断 |
|------|------|------|------|------|
{financial_table}

---

## 增长驱动

{growth_drivers}

---

## 利润变化原因

{profit_changes}

---

## 现金流和资产负债质量

{cashflow_quality}

---

## 管理层指引 vs 实际表现

{guidance_vs_actual}

---

## 同行对比

{peer_comparison}

---

## 主要风险

{risks}

---

## 后续跟踪指标

{tracking_indicators}

---

## 来源

{sources}
""",

        "深度财报分析": """# {subject} {period} 财报分析报告

**分析对象**: {subject}
**分析期间**: {period}
**生成时间**: {timestamp}

---

## 1. 核心结论

- **本期经营表现**: {performance_summary}
- **前瞻变化**: {forward_outlook}
- **投资/经营建议**: {recommendation}

---

## KPI 速览

| 指标 | 本期 | 同比 | 环比 | 解读 |
|------|------|------|------|------|
{kpi_table}

---

## 2. 分析方法及信息来源

{methodology}

---

## 3. 核心财务表现

{financial_performance}

---

## 4. 历史表现对比分析

{historical_comparison}

---

## 5. 增长驱动

{growth_drivers}

---

## 6. 费用与利润质量

{profitability}

---

## 7. 资产负债与现金安全垫

{balance_sheet}

---

## 8. 行业情况

{industry_overview}

---

## 9. 同行/相关业务对比

{peer_comparison}

---

## 10. 风险与反面证据

{risks}

---

## 11. 投资建议/经营建议

{recommendations}

---

## 12. 后续跟踪指标

{tracking_indicators}

---

## 13. 来源

{sources}
""",

        "PEST分析": """# {subject} PEST宏观环境分析

**分析对象**: {subject}
**生成时间**: {timestamp}

---

## 分析摘要

{summary}

---

## 政治因素 (Political)

{political}

---

## 经济因素 (Economic)

{economic}

---

## 社会因素 (Social)

{social}

---

## 技术因素 (Technological)

{technological}

---

## 综合影响评估

{综合评估}

---

## 机会与威胁

**机会**:
{opportunities}

**威胁**:
{threats}

---

## 来源

{sources}
""",

        "通用框架": """# {subject} - {framework_name}分析报告

**分析对象**: {subject}
**分析框架**: {framework_name}
**生成时间**: {timestamp}

---

## 分析摘要

{summary}

---

{dimension_sections}

---

## 结论与建议

{conclusion}

---

## 来源

{sources}
"""
    }

    def __init__(self):
        pass

    def generate_report(
        self,
        framework_name: str,
        subject: str,
        content_pool: List[Dict],
        citations: Dict[str, str],
        **kwargs
    ) -> str:
        """
        生成分析报告

        Args:
            framework_name: 框架名称
            subject: 分析主题
            content_pool: 内容池 (搜索到的所有内容)
            citations: 引文映射 {content_id: url}
            **kwargs: 其他参数 (如 period, dimensions 等)

        Returns:
            str: Markdown格式的报告
        """
        structured_analysis = kwargs.get("structured_analysis") or kwargs.get("analysis")
        structured_sources = kwargs.get("sources")
        if structured_analysis and structured_sources:
            return self.generate_structured_report(
                subject=subject,
                framework_name=framework_name,
                sources=structured_sources,
                analysis=structured_analysis,
                generated_at=kwargs.get("generated_at"),
                report_family=kwargs.get("report_family"),
            )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 选择模板
        template = self.REPORT_TEMPLATES.get(framework_name, self.REPORT_TEMPLATES["通用框架"])

        # 提取各维度内容
        dimension_sections = self._generate_dimension_sections(
            framework_name, content_pool, citations
        )

        # 生成引文列表
        sources = self._generate_sources_list(citations)

        # 填充模板 (简化版,实际应根据content_pool生成内容)
        report_data = {
            "subject": subject,
            "framework_name": framework_name,
            "period": kwargs.get("period", "N/A"),
            "timestamp": timestamp,
            "dimension_sections": dimension_sections,
            "sources": sources,
            # 以下字段需要根据实际内容生成
            "conclusion": "待填充: 基于分析内容生成结论...",
            "finding_1": "待填充: 关键发现1",
            "finding_2": "待填充: 关键发现2",
            "finding_3": "待填充: 关键发现3",
            "financial_table": "待填充: 财务数据表格",
            "growth_drivers": "待填充: 增长驱动因素",
            "profit_changes": "待填充: 利润变化原因",
            "cashflow_quality": "待填充: 现金流质量",
            "guidance_vs_actual": "待填充: 指引与实际对比",
            "peer_comparison": "待填充: 同行对比",
            "risks": "待填充: 风险因素",
            "tracking_indicators": "待填充: 跟踪指标",
            "methodology": "待填充: 分析方法",
            "summary": "待填充: 分析摘要"
        }

        try:
            report = template.format(**report_data)
        except KeyError as e:
            # 缺少某些字段时,使用通用模板
            print(f"[ReportGenerator] 模板字段缺失: {e}, 使用通用模板")
            generic_template = self.REPORT_TEMPLATES["通用框架"]
            report = generic_template.format(**report_data)

        return report

    def generate_structured_report(
        self,
        subject: str,
        framework_name: str,
        sources: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        generated_at: Optional[str] = None,
        report_family: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a source-backed Markdown report from T2/T3 structured data."""
        timestamp = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_map = self._build_source_map(sources)
        selected_report_family = report_family or recommend_report_family(analysis)
        lines = [
            f"# {subject}",
            "",
            f"**生成时间**：{timestamp}",
            f"**分析框架**：{framework_name}",
            f"**报告形态**：{selected_report_family.get('name', 'Deep Research Report')}",
            f"**信息源数量**：{len(sources)} 条",
            "",
            "---",
            "",
            "## 核心结论",
            "",
            f"> **总判断**：{analysis.get('core_judgment', '').strip() or '证据不足，暂不形成总判断。'}",
            "",
        ]

        supporting_reasons = analysis.get("supporting_reasons") or []
        if supporting_reasons:
            lines.append("支撑理由：")
            for idx, reason in enumerate(supporting_reasons, 1):
                claim = reason.get("claim", "").strip()
                confidence = reason.get("confidence", "medium")
                cite = self._format_citations(reason.get("source_ids", []), source_map)
                lines.append(f"{idx}. {claim}（置信度：{confidence}）{cite}")
            lines.append("")

        lines.extend(self._render_source_coverage(sources))

        for section in analysis.get("sections", []):
            heading = section.get("heading", "").strip()
            if not heading:
                continue
            lines.extend(["", f"## {heading}", ""])
            paragraphs = section.get("paragraphs") or []
            for paragraph in paragraphs:
                text = paragraph.get("text", "").strip()
                if not text:
                    continue
                confidence = paragraph.get("confidence")
                confidence_text = f"（置信度：{confidence}）" if confidence else ""
                cite = self._format_citations(paragraph.get("source_ids", []), source_map)
                lines.append(f"{text}{confidence_text}{cite}")
                lines.append("")

        competitor_matrix = analysis.get("competitor_matrix")
        if competitor_matrix:
            lines.extend(self._render_matrix("竞品对比表", competitor_matrix))

        actions = analysis.get("actions") or []
        if actions:
            lines.extend(["", "## 可行动建议", ""])
            lines.append("| 优先级 | 负责人 | 建议 | 来源 |")
            lines.append("|---|---|---|---|")
            for action in actions:
                source_text = self._format_citations(action.get("source_ids", []), source_map, wrap=False)
                lines.append(
                    "| {priority} | {owner} | {text} | {sources} |".format(
                        priority=action.get("priority", ""),
                        owner=action.get("owner", ""),
                        text=self._clean_table_cell(action.get("text", "")),
                        sources=source_text,
                    )
                )

        risks = analysis.get("risks") or []
        if risks:
            lines.extend(["", "## 风险与未验证事项", ""])
            lines.append("| 风险事项 | 触发条件 | 影响程度 | 发生概率 | 来源 |")
            lines.append("|---|---|---|---|---|")
            for risk in risks:
                source_text = self._format_citations(risk.get("source_ids", []), source_map, wrap=False)
                lines.append(
                    "| {item} | {trigger} | {impact} | {likelihood} | {sources} |".format(
                        item=self._clean_table_cell(risk.get("item", "")),
                        trigger=self._clean_table_cell(risk.get("trigger", "")),
                        impact=risk.get("impact", ""),
                        likelihood=risk.get("likelihood", ""),
                        sources=source_text,
                    )
                )

        lines.extend(self._render_references(sources))
        return self._humanize_report_style("\n".join(lines).rstrip() + "\n")

    def _build_source_map(self, sources: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        source_map = {}
        for source in sources:
            source_id = source.get("source_id") or source.get("id")
            if source_id:
                source_map[source_id] = source
        return source_map

    def _format_citations(
        self,
        source_ids: List[str],
        source_map: Dict[str, Dict[str, Any]],
        wrap: bool = True,
    ) -> str:
        if not source_ids:
            return ""
        rendered = []
        for source_id in source_ids:
            source = source_map.get(source_id, {})
            url = source.get("url") or source.get("url_or_path") or ""
            rendered.append(f"[{source_id}]({url})" if url else f"{source_id}（链接待补）")
        joined = ", ".join(rendered)
        return f"（来源：{joined}）" if wrap else joined

    def _render_source_coverage(self, sources: List[Dict[str, Any]]) -> List[str]:
        type_counts = Counter(source.get("source_type") or source.get("channel") or "未标注" for source in sources)
        confidence_counts = Counter(source.get("confidence") or "未标注" for source in sources)
        lines = ["## 信息源覆盖与可信度说明", ""]
        lines.append("| 维度 | 覆盖情况 |")
        lines.append("|---|---|")
        lines.append(f"| 来源类型 | {self._format_counter(type_counts)} |")
        lines.append(f"| 可信度 | {self._format_counter(confidence_counts)} |")
        lines.append(f"| source_id 范围 | {', '.join(self._source_ids(sources)) or '无'} |")
        lines.append("")
        return lines

    def _render_matrix(self, heading: str, matrix: Dict[str, Any]) -> List[str]:
        columns = matrix.get("columns") or []
        rows = matrix.get("rows") or []
        if not columns:
            return []
        lines = ["", f"## {heading}", ""]
        lines.append("| " + " | ".join(self._clean_table_cell(column) for column in columns) + " |")
        lines.append("|" + "|".join("---" for _ in columns) + "|")
        for row in rows:
            padded = list(row) + [""] * max(0, len(columns) - len(row))
            lines.append("| " + " | ".join(self._clean_table_cell(cell) for cell in padded[:len(columns)]) + " |")
        return lines

    def _render_references(self, sources: List[Dict[str, Any]]) -> List[str]:
        lines = ["", "## 参考文献", ""]
        lines.append("| 编号 | 标题 | 发布方 | 日期 | 置信度 | 原文链接 |")
        lines.append("|---|---|---|---|---|---|")
        for source in sorted(sources, key=lambda item: item.get("source_id") or item.get("id") or ""):
            source_id = source.get("source_id") or source.get("id") or ""
            title = self._clean_table_cell(source.get("title", "未命名来源"))
            publisher = self._clean_table_cell(source.get("publisher", source.get("source", "")))
            publish_date = source.get("publish_date") or source.get("date") or "未标注"
            confidence = source.get("confidence") or "未标注"
            url = source.get("url") or source.get("url_or_path") or ""
            link = f"[查看原文]({url})" if url else "链接待补"
            lines.append(f"| {source_id} | {title} | {publisher} | {publish_date} | {confidence} | {link} |")
        return lines

    def _source_ids(self, sources: List[Dict[str, Any]]) -> List[str]:
        return [source_id for source_id in (source.get("source_id") or source.get("id") for source in sources) if source_id]

    def _format_counter(self, counter: Counter) -> str:
        return "；".join(f"{key} {value}" for key, value in counter.items()) if counter else "无"

    def _clean_table_cell(self, value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ").strip()

    def _humanize_report_style(self, report: str) -> str:
        """
        Conservative Humanizer Editor pass.

        Keep citations, numbers, and structure intact. Only remove empty AI-like
        transitions that add no evidence or meaning.
        """
        cleaned = report
        for old, new in self.AI_STYLE_REPLACEMENTS.items():
            cleaned = cleaned.replace(old, new)
        return cleaned

    def _generate_dimension_sections(
        self,
        framework_name: str,
        content_pool: List[Dict],
        citations: Dict[str, str]
    ) -> str:
        """
        生成各维度的内容章节

        返回格式:
        ## 维度1

        内容...[^1]

        ## 维度2

        内容...[^2]
        """
        sections = []

        # 简化版: 模拟生成维度章节
        for idx, content_item in enumerate(content_pool, 1):
            dimension_name = content_item.get("dimension", f"维度{idx}")
            content_text = content_item.get("content", "")
            source_url = citations.get(content_item.get("id", f"source_{idx}"), "")

            # 添加引文标记
            citation_mark = f"[[来源{idx}]]({source_url})" if source_url else ""

            section = f"## {dimension_name}\n\n{content_text[:500]}... {citation_mark}\n"
            sections.append(section)

        return "\n".join(sections)

    def _generate_sources_list(self, citations: Dict[str, str]) -> str:
        """
        生成来源列表

        返回格式:
        - [来源1] 标题 - URL
        - [来源2] 标题 - URL
        """
        sources_list = []

        for idx, (source_id, url) in enumerate(citations.items(), 1):
            # 简化版: 实际应从content_pool中获取标题
            title = f"来源{idx}"
            sources_list.append(f"- [{idx}] {title} - {url}")

        return "\n".join(sources_list) if sources_list else "无外部来源"

    def add_citations_to_text(self, text: str, citations: List[Dict]) -> str:
        """
        在文本中添加引文标记

        Args:
            text: 原始文本
            citations: 引文列表 [{\"text\": \"引用文本\", \"url\": \"来源URL\"}]

        Returns:
            str: 添加引文后的文本
        """
        # 简化实现: 在关键句末尾添加引文
        for citation in citations:
            citation_text = citation.get("text", "")
            citation_url = citation.get("url", "")

            if citation_text in text:
                # 替换为带引文的版本
                marked_text = f"{citation_text} [[来源]]({citation_url})"
                text = text.replace(citation_text, marked_text, 1)

        return text

    def export_to_word(self, markdown_content: str, output_path: str) -> str:
        """
        将Markdown报告导出为Word文档

        Args:
            markdown_content: Markdown内容
            output_path: 输出文件路径

        Returns:
            str: 导出的文件路径
        """
        # 实际使用时需要调用: skill docx --create "{output_path}" --content "{markdown_content}"

        print(f"[ReportGenerator] 导出Word文档: {output_path}")
        return output_path


if __name__ == "__main__":
    # 测试用例
    generator = ReportGenerator()

    content_pool = [
        {
            "id": "source_1",
            "dimension": "政治因素",
            "content": "关于高德地图的政策环境分析...",
        },
        {
            "id": "source_2",
            "dimension": "经济因素",
            "content": "关于高德地图的市场规模分析...",
        }
    ]

    citations = {
        "source_1": "https://example.com/policy-analysis",
        "source_2": "https://example.com/market-size"
    }

    report = generator.generate_report(
        framework_name="PEST分析",
        subject="高德地图",
        content_pool=content_pool,
        citations=citations
    )

    print(report)
