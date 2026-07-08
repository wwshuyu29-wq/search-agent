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
11. Humanizer Editor Agent 只做表达层去 AI 味，保留事实、数字、引用和风险边界。

## 默认不采用

- 不默认在 skill 内部为每个节点隐藏调用 OpenAI API。
- 不让 CLI 关键词分类器替代 Codex LLM 的语义判断。
- 不因为 prompt 看起来合理就跳过 artifact gate。
- 不把 dry-run 的占位证据当成真实业务结论。
