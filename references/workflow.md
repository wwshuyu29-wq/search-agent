# Search Agent 工作流程图（v3.0 Codex-ready）

对应 SKILL.md 的 Step 0 → Step 1 → Step 2 → Step 3 四段式主流程。

```mermaid
graph TD
    Start[用户输入调研需求] --> Step0[Step 0: 意图识别 & 框架路由]

    Step0 --> Complex{复杂度判断<br/>全面/系统/多维度?}
    Complex -->|是| RouteCombo[从 framework 组合表选组合]
    Complex -->|否| RouteSingle[从 framework 路由表选单框架]

    RouteCombo --> Guide[应用引导性扩框规则<br/>意图单一 → 建议叠加]
    RouteSingle --> Guide

    Guide --> Card[输出审核卡片<br/>主题/框架/维度/关键词/源范围]

    Card --> Review1{⏸ 审核点 ①<br/>用户确认?}
    Review1 -->|修改| Step0
    Review1 -->|确认| Step1[Step 1: 多源全平台信息检索]

    Step1 --> L1[Layer 1 官方/IR/SEC<br/>realtime-search Brave]
    Step1 --> L2[Layer 2 业绩会 Transcript<br/>realtime-search Brave]
    Step1 --> L3[Layer 3 深度分析<br/>Firecrawl 英文]
    Step1 --> L4[Layer 4 中文财经媒体<br/>realtime-search 百度]
    Step1 --> L5[Layer 5 RSS 聚合<br/>finance-rss-reader 65+ 源]

    L1 --> Fetch[URL 全文抓取<br/>realtime-search fetch]
    L2 --> Fetch
    L3 --> Fetch
    L4 --> Fetch
    L5 --> Fetch

    Fetch --> Yaml[产出 YAML 源清单<br/>source_id + confidence + key_facts]

    Yaml --> Step2[Step 2: 结构化分析]
    Step2 --> ByDim[按框架子维度逐一分析]
    ByDim --> Cite[每条结论标 source_id<br/>区分事实/计算/假设/判断]
    Cite --> Cross[关键数字 ≥2 来源交叉验证]

    Cross --> Step3[Step 3: 金字塔报告生成]
    Step3 --> Pyramid[核心结论先行<br/>+ 支撑理由 + 主要风险]
    Pyramid --> Dim[按框架维度展开正文]
    Dim --> RiskTable[风险与不确定性表格]
    RiskTable --> RefTable[参考文献表<br/>原文链接可跳转]

    RefTable --> Review2{⏸ 审核点 ②<br/>校验结论/引文?}
    Review2 -->|引文错误| FixCite[修正 source_id 映射]
    Review2 -->|结论偏差| Step2
    Review2 -->|框架不合| Step0
    Review2 -->|通过| Output[输出最终报告]

    FixCite --> Step3

    Output --> Save[保存到 config.output_dir]
    Save --> End[完成]

    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style Review1 fill:#fff9c4
    style Review2 fill:#fff9c4
    style Step1 fill:#f3e5f5
    style Step3 fill:#ffe0b2
    style Card fill:#ffccbc
```

## 与 CLAUDE.md 的差异（v3.0 融合后）

- **保留 CLAUDE.md 精华**：审核卡片格式、YAML 源清单、金字塔报告、强制引文、质量红线（禁模糊词、数字必带口径）
- **保留 v2.3 优势并扩展**：9 框架 + 7 组合规则、5 层分层搜索、65+ 个财经/产业/AI 媒体源
- **新增 Firecrawl 层**：填补英文深度内容（Seeking Alpha / FT / SEC）短板
- **两条路径**：Codex 原生走 prompt（SKILL.md），脚本党走 `bin/search_agent.py` CLI

## 关键设计原则

1. **框架先于搜索**：先决定要支撑什么判断，再决定查什么资料
2. **官方来源优先**：Layer 1 → Layer 5 按 confidence 排序
3. **引文透明**：每个论断绑定 source_id，报告末尾必须列参考文献表
4. **两个人工闸门**：审核点①（选框架）+ 审核点②（校引文/结论）
5. **可扩展**：新框架加 `references/frameworks.md` + `lib/frameworks.py`；新源加脚本 + 更新 SKILL.md Step 1
