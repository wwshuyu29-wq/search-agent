# Codex-Native Execution Model

这份文档回答一个核心问题：search-agent 的多 agent workflow 在 Codex 里到底怎么调用 LLM。

## LLM 调用方式

在 Codex 中，节点 LLM 默认由当前 Codex 会话承担。search-agent skill 不在节点内部另行隐藏调用 OpenAI API；Codex 读取节点 prompt、执行判断、调用工具、写入 artifact。

不需要为节点 LLM 另配 OpenAI API Key。团队成员安装 skill 后，只要在 Codex 中触发 `search-agent`，Codex 自身就是 Intent Router、Search Planner、Source QA、Framework Analyst、Report Writer 等节点的 LLM 执行环境。

需要配置的是外部检索工具的 key，例如：

- `FIRECRAWL_API_KEY`：用于 Firecrawl 深度搜索。
- 浏览器/平台登录态：用于 OpenCLI、agent-reach、B 站等平台。
- 可能的内部搜索权限：用于企业内网或知识库。

## 节点 Prompt 从哪里来

可执行节点 prompt 由 `lib/workflow_contracts.py` 生成：

```python
from workflow_contracts import build_agent_prompt

prompt = build_agent_prompt("source_qa")
```

这个 prompt 会包含：

- 节点角色
- Input Artifact
- LLM Judgment
- Tool/Skill Use
- Output Artifact
- Output Schema
- Quality Gate
- Hard Constraints

Codex-native 执行时，Codex 读这个 contract，用当前会话的 LLM 完成判断；工具和 skill 只负责检索、解析、计算、结构化检查，不替代 LLM 判断。

## Artifact 和 Gate

artifact schema 来自：

```python
from workflow_contracts import get_artifact_contracts
```

gate 校验来自：

```python
from workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator()
orchestrator.validate_artifact("ClaimGraph", claim_graph)
```

这保证每个节点不是“说完就过”，而是必须产出结构化 artifact，字段齐全后才能进入下一步。

## 并行策略

优先策略：如果当前 Codex 环境有 multi-agent/subagent 工具，Source Hunter 类节点可以并行：

- Official Source Hunter
- Media Source Hunter
- RSS/News Hunter
- UGC/Social Hunter
- Finance Data Hunter
- Marketing Intelligence Hunter

兜底策略：如果没有 multi-agent 工具，同一个 Codex 会话按同样的 node prompt 顺序执行。输出 artifact 和 gate 不变，所以结果仍然可审计。

## 团队安装后怎么跑

安装目标路径：

```bash
~/.codex/skills/search-agent
```

推荐安装方式：

```bash
bash install.sh
```

安装后先跑工具环境检查：

```bash
python scripts/search_agent_doctor.py
```

再跑 workflow 自检：

```bash
python bin/search_agent.py "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示" --workflow-dry-run
```

看到 `Multi-Agent Workflow Dry Run`、`status: complete`，并且所有 artifact validations 都是 `ok`，说明本地多 agent 骨架可跑通。

想查看每个子 agent 怎么推进：

```bash
python bin/search_agent.py --workflow-playbook
```

想验证正式 gate-driven 状态机：

```bash
python bin/search_agent.py "高德地图最近三个月上新，对百度地图市场组有什么启示" --workflow-start --state-file search_agent_state.json
python bin/search_agent.py --workflow-resume 确认 --state-file search_agent_state.json
python bin/search_agent.py --workflow-resume 通过 --state-file search_agent_state.json
```

CLI 的 gate runner 用来验证状态流转；Codex 里的真实调研会用同一套节点契约，但 Source Hunter 阶段应替换为真实检索和工具调用结果。

## 真实检索竖切

`真实检索竖切` 的意思是：先不追求所有平台、所有子 agent 一次性全自动，而是先把一条真实链路跑到底。它必须满足四件事：

1. 输入来自 `SearchPlan`，不是临时手写关键词。
2. 执行者是明确的 Source Hunter 子 agent，例如 `official_source_hunter`。
3. 中间调用真实工具，例如 Firecrawl、RSS、agent-reach 或金融/营销 skill，不用占位数据冒充。
4. 输出写成标准 `SourceListFragment`，下一步可以交给 SourceList Merger 和 Source QA。

已接入的执行链包括：

```text
SearchPlan task
  -> SourceHunterExecutor
  -> Firecrawl search wrapper（需要 FIRECRAWL_API_KEY）
  -> normalized SourceListFragment
  -> workflow state file

SearchPlan task
  -> SourceHunterExecutor
  -> finance-rss-reader/scripts/rss_fetch.py（不需要 FIRECRAWL_API_KEY）
  -> normalized SourceListFragment with relevance_score
  -> workflow state file
```

命令入口：

```bash
python bin/search_agent.py --execute-source-hunter official_source_hunter --state-file search_agent_state.json --limit-per-query 5
```

RSS/News Hunter 快速验收命令：

```bash
SEARCH_AGENT_RSS_MAX_SOURCES=5 python bin/search_agent.py --execute-source-hunter rss_news_hunter --state-file search_agent_state.json --limit-per-query 5
```

执行全部 Source Hunter：

```bash
SEARCH_AGENT_RSS_MAX_SOURCES=5 python bin/search_agent.py --execute-source-hunters --state-file search_agent_state.json --limit-per-query 5
```

继续执行后半段 artifact 链路：

```bash
python bin/search_agent.py --workflow-continue-from-sources --state-file search_agent_state.json
```

这一步会把真实 `SourceListFragment` 送入 `SourceList Merger -> Source QA -> Gap Filler -> Framework/Specialist Analysis -> Citation Auditor -> Report Writer -> Humanizer -> IntegrityDiff`。它仍然遵守 gate：如果 Source QA 发现冲突或缺口，会停在 `source_qa_conflict_resolution`。

如果本机没有 `FIRECRAWL_API_KEY`，节点状态会写成 `skipped_missing_tool_config`，并把缺失配置写入 warnings。这样做的原则是宁可明确跳过，也不伪造来源。

当前 Source Hunter 执行路由：

| Node | Real runner | Notes |
|---|---|---|
| `official_source_hunter` | Firecrawl wrapper | Primary/original source discovery; requires `FIRECRAWL_API_KEY`. |
| `media_source_hunter` | Firecrawl wrapper | Deep media/web discovery; requires `FIRECRAWL_API_KEY`. |
| `rss_news_hunter` | `finance-rss-reader` | RSS/news aggregation with `relevance_score`; independent from Firecrawl key. |
| `ugc_social_hunter` | `bili` CLI | Bilibili video discussion signal; low confidence until Source QA corroborates. |
| `finance_data_hunter` | `yfinance_snapshot.py` + `yc-reader` + Funda/opencli adapters | yfinance ticker snapshots; YC public API for startup data; Funda/Twitter/opencli emit setup-aware routing rows when credentials or bridge are missing. |
| `marketing_intelligence_hunter` | marketing skill catalog | Routes to method skills such as `marketing-plan` and `marketing-ideas`; not market evidence by itself. |

需要查看某个 phase 要派发哪些子 Agent 时，导出 node packets：

```bash
python bin/search_agent.py --workflow-packets step1_parallel_source_hunting --state-file search_agent_state.json
```

每个 packet 都包含 node_id、node_name、input_payload、prompt、allowed_tools_or_skills、output_artifact、quality_gate 和 hard_constraints。Codex 可以把这些 packet 作为子 Agent 派发任务；没有多 Agent 工具时，也可以由同一会话逐个执行。

需要查看每个节点能调用哪些 skill/tool、调用方式、输出 artifact 和证据边界：

```bash
python bin/search_agent.py --skill-registry
```

注册表把调用分成四类：`llm_method`（Codex 读取 skill 方法并判断）、`script_cli`（执行本地脚本/CLI）、`api_or_mcp`（外部 API/MCP）、`internal`（本项目内部校验/合并/差异检查）。同时用 `evidence_role` 标明产物用途：`market_evidence`、`structured_data` 可以支撑事实 claim；`method_reference` 只能提供方法和结构；`validator`、`style_only` 不能新增事实。

需要审计本地开源/外部 skill 是否已经被主 workflow 引用：

```bash
python bin/search_agent.py --skill-coverage
```

这个审计会分开显示四件事：

- `discovered`：本地文件夹里确实发现了多少个 `SKILL.md`。
- `registered_or_referenced`：已经被节点注册表、节点契约或 specialist chain 明确引用的 skill。
- `inventory_only`：只是存在于本地，但还没有进入执行链的 skill。
- `scope`：该类 skill 在报告里能扮演什么角色。

判断原则：发现 `SKILL.md` 只能证明它是库存；进入 registry/chain 才算被 workflow 知道；只有产出 `CleanSourceList`、`ClaimGraph`、`SpecialistNotes` 或 `ApprovedClaimGraph` 的事实/数据型 skill，才能支撑报告结论。营销、写作、Superpowers 这类方法型 skill 可以影响框架、分析角度、表达质量，但不能单独当作市场事实来源。

需要进一步看细分 skill 的适配理由和节点用法：

```bash
python bin/search_agent.py --skill-adapter-matrix marketing
python bin/search_agent.py --skill-adapter-matrix finance
```

这张适配矩阵回答的是另一个问题：不是“本地有没有这个 skill”，而是“当前 workflow 为什么要拿它、在哪个节点拿、拿来产出什么 artifact、怎样才算用得好”。例如 `onboarding` 只在新用户激活/首次使用/留存问题里进入 Marketing Specialist；`twitter-reader` 只作为 UGC/金融情绪来源，不能单独支撑投资判断。

Source QA 如果发现数字冲突、关键证据缺口或来源口径不一致，状态机会停在 `source_qa_conflict_resolution`。用户选择口径或补充来源后，Workflow 才能继续进入 Framework Analyst。

R0 执行层的证据链已经扩展为：

```text
SourceListFragment
  -> SourceList Merger
  -> RawSourceList + MergerLog
  -> Source QA
  -> ConflictRegister + GapList + CleanSourceList
  -> Gap Filler / Conflict Refetch（条件执行）
  -> ClaimGraph + SpecialistNotes + ClaimGraphPatch
  -> CitationAudit + ApprovedClaimGraph
  -> ReportDraft
  -> FinalReport + HumanizerChangeLog
  -> IntegrityDiff
```

这条链路的目的不是增加形式，而是保证 Source Hunter 的候选来源不会直接进入分析，报告也不会在 Humanizer 改写后绕过事实完整性检查。

## 提示词是否必须写 sub agent

不需要。团队成员正常使用时只要写 `用 search-agent`，Codex 会加载 `SKILL.md`，再按节点契约执行多 agent workflow。

推荐提示词：

```text
用 search-agent 帮我调研高德地图最近三个月上了什么新功能，
面向百度地图市场组，先输出审核卡，等我确认后再继续。
```

如果想更强约束 Codex 不要直接跳到搜索或报告，可以补一句：

```text
严格按多 agent workflow 执行：Intent Router 先判断意图，
确认后再进入 Search Planner 和各 Source Hunter。
```

## Codex 里真实执行顺序

1. 用户在 Codex 里提出调研需求，并触发 `search-agent` skill。
2. Codex 加载 `SKILL.md`。
3. Codex 按需读取 `references/agent-nodes.md`、`references/node-playbook.md`、`references/codex-execution.md`。
4. Intent Router Agent 使用当前 Codex LLM 做语义理解，输出 AuditCard，等待用户确认。
5. 用户确认后，Search Planner Agent 生成 SearchPlan。
6. Source Hunter 节点调用 Firecrawl、RSS、agent-reach、finance/marketing skills 等工具，输出 SourceList。
7. Source QA Agent 检查来源质量、冲突、缺口，输出 CleanSourceList。
8. Framework Analyst + Specialist Agents 生成 ClaimGraph。
9. Citation Auditor Agent 校验每条 claim 是否真的被来源支持。
10. Report Writer Agent 选择报告形态并生成 ReportDraft。
11. Humanizer Editor Agent 必须由真实 callable/adapter 或外部改写结果执行，只做表达层去 AI 味，保留事实、数字、引用和风险边界。production 未注入 adapter 时流程停在 `pending_gate=humanizer_required`，不得以 identity copy 生成 `FinalReport`。CLI 可用 `--workflow-resume humanized --humanized-file <report.md> --change-log-file <changes.json>` 提交真实改写并继续 IntegrityDiff。

## 默认不采用

- 不默认在 skill 内部为每个节点隐藏调用 OpenAI API。
- 不让 CLI 关键词分类器替代 Codex LLM 的语义判断。
- 不因为 prompt 看起来合理就跳过 artifact gate。
- 不把 dry-run 的占位证据当成真实业务结论。
