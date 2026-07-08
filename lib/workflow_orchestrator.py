#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow orchestration helpers for the multi-agent research pipeline."""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List

from workflow_contracts import get_artifact_contracts, get_node_contracts, get_orchestration_plan


class WorkflowOrchestrator:
    """Validate handoff artifacts and route workflow phases."""

    def __init__(self):
        self.artifact_contracts = get_artifact_contracts()
        self.node_contracts = get_node_contracts()
        self.orchestration_plan = get_orchestration_plan()

    def validate_artifact(self, artifact_name: str, artifact: Any) -> Dict[str, Any]:
        """Validate that an artifact contains its required fields."""
        if artifact_name not in self.artifact_contracts:
            raise KeyError(f"Unknown artifact: {artifact_name}")

        required_fields = self.artifact_contracts[artifact_name]["required_fields"]
        missing_fields = self._missing_fields(artifact_name, artifact, required_fields)

        return {
            "artifact": artifact_name,
            "valid": not missing_fields,
            "missing_fields": missing_fields,
            "quality_rules": deepcopy(self.artifact_contracts[artifact_name]["quality_rules"]),
        }

    def next_phase_after_gate(self, completed_gate: str) -> Dict[str, Any]:
        """Return the phase that follows a completed gate."""
        for idx, phase in enumerate(self.orchestration_plan):
            if phase.get("gate") == completed_gate:
                if idx + 1 >= len(self.orchestration_plan):
                    return {}
                return deepcopy(self.orchestration_plan[idx + 1])
        raise KeyError(f"Unknown gate: {completed_gate}")

    def validate_contract_consistency(self) -> Dict[str, Any]:
        """Check that the orchestration plan can be satisfied by declared artifacts."""
        issues = []
        produced = {"RawUserQuery"}
        known_nodes = {node["id"] for node in self.node_contracts}
        known_artifacts = set(self.artifact_contracts.keys()) | {"RawUserQuery"}

        for artifact_name, contract in self.artifact_contracts.items():
            for node_id in contract.get("producer_nodes", []):
                if node_id != "user" and node_id not in known_nodes:
                    issues.append(f"{artifact_name} declares unknown producer node {node_id}")
            for node_id in contract.get("consumer_nodes", []):
                if node_id != "user" and node_id not in known_nodes:
                    issues.append(f"{artifact_name} declares unknown consumer node {node_id}")

        for phase in self.orchestration_plan:
            phase_nodes = set(phase.get("nodes", []))
            for node_id in phase_nodes:
                if node_id not in known_nodes:
                    issues.append(f"{phase['id']} references unknown node {node_id}")

            for artifact_name in phase.get("input_artifacts", []):
                if artifact_name not in known_artifacts:
                    issues.append(f"{phase['id']} uses unknown input artifact {artifact_name}")
                elif artifact_name not in produced:
                    issues.append(f"{phase['id']} requires {artifact_name} before it is produced")

            for artifact_name in phase.get("output_artifacts", []):
                if artifact_name not in known_artifacts:
                    issues.append(f"{phase['id']} produces unknown artifact {artifact_name}")
                elif artifact_name in self.artifact_contracts:
                    producer_nodes = set(self.artifact_contracts[artifact_name].get("producer_nodes", []))
                    if phase_nodes and phase_nodes.isdisjoint(producer_nodes):
                        issues.append(f"{phase['id']} outputs {artifact_name} but no phase node produces it")
                produced.add(artifact_name)

            if phase.get("parallel") and len(phase.get("nodes", [])) < 2:
                issues.append(f"{phase['id']} is marked parallel but has fewer than two nodes")

        return {
            "valid": not issues,
            "issues": issues,
            "checked_nodes": len(known_nodes),
            "checked_artifacts": sorted(self.artifact_contracts.keys()),
        }

    def run_dry_workflow(self, user_query: str) -> Dict[str, Any]:
        """Run a deterministic artifact-only workflow to prove the pipeline is coherent."""
        artifacts: Dict[str, Any] = {"RawUserQuery": user_query}
        validations: List[Dict[str, Any]] = []
        phase_results: List[Dict[str, Any]] = []

        intent_brief, audit_card = self._build_dry_step0(user_query)
        artifacts["IntentBrief"] = intent_brief
        artifacts["AuditCard"] = audit_card
        validations.extend(self._validate_many({"IntentBrief": intent_brief, "AuditCard": audit_card}))
        phase_results.append(self._phase_result("step0_intent_and_audit", ["IntentBrief", "AuditCard"]))

        search_plan = self._build_dry_search_plan(audit_card)
        artifacts["SearchPlan"] = search_plan
        validations.append(self.validate_artifact("SearchPlan", search_plan))
        phase_results.append(self._phase_result("step1_search_planning", ["SearchPlan"]))

        source_list = self._build_dry_source_list()
        artifacts["SourceList"] = source_list
        validations.append(self.validate_artifact("SourceList", source_list))
        phase_results.append(self._phase_result("step1_parallel_source_hunting", ["SourceList"]))

        source_qa_notes, clean_source_list = self._build_dry_source_qa(source_list)
        artifacts["SourceQANotes"] = source_qa_notes
        artifacts["CleanSourceList"] = clean_source_list
        validations.extend(
            self._validate_many(
                {"SourceQANotes": source_qa_notes, "CleanSourceList": clean_source_list}
            )
        )
        phase_results.append(self._phase_result("step1_source_qa", ["SourceQANotes", "CleanSourceList"]))

        claim_graph = self._build_dry_claim_graph(clean_source_list)
        artifacts["ClaimGraph"] = claim_graph
        validations.append(self.validate_artifact("ClaimGraph", claim_graph))
        phase_results.append(self._phase_result("step2_analysis_and_specialists", ["ClaimGraph"]))

        citation_audit = self._build_dry_citation_audit(claim_graph)
        artifacts["CitationAudit"] = citation_audit
        validations.append(self.validate_artifact("CitationAudit", citation_audit))
        phase_results.append(self._phase_result("step2_citation_audit", ["CitationAudit"]))

        report_draft = self._build_dry_report_draft(intent_brief, clean_source_list, claim_graph)
        artifacts["ReportDraft"] = report_draft
        validations.append(self.validate_artifact("ReportDraft", report_draft))
        phase_results.append(self._phase_result("step3_report_draft", ["ReportDraft"]))

        final_report = self._build_dry_final_report(report_draft, clean_source_list)
        artifacts["FinalReport"] = final_report
        validations.append(self.validate_artifact("FinalReport", final_report))
        phase_results.append(self._phase_result("step3_humanizer_final", ["FinalReport"]))

        valid = all(validation["valid"] for validation in validations)
        return {
            "status": "complete" if valid else "blocked",
            "valid": valid,
            "phase_results": phase_results,
            "validations": validations,
            "artifacts": artifacts,
        }

    def start_gate_workflow(self, user_query: str) -> Dict[str, Any]:
        """Start the formal gate-driven workflow and stop after the Step 0 audit card."""
        artifacts: Dict[str, Any] = {"RawUserQuery": user_query}
        validations: List[Dict[str, Any]] = []
        phase_results: List[Dict[str, Any]] = []

        intent_brief, audit_card = self._build_dry_step0(user_query)
        artifacts["IntentBrief"] = intent_brief
        artifacts["AuditCard"] = audit_card
        validations.extend(self._validate_many({"IntentBrief": intent_brief, "AuditCard": audit_card}))
        phase_results.append(self._phase_result("step0_intent_and_audit", ["IntentBrief", "AuditCard"]))

        valid = all(validation["valid"] for validation in validations)
        return self._workflow_state(
            status="waiting_for_user" if valid else "blocked",
            current_phase="step0_intent_and_audit",
            pending_gate="audit_card_confirmed" if valid else "audit_card_invalid",
            artifacts=artifacts,
            validations=validations,
            phase_results=phase_results,
            next_action=(
                "请审核 AuditCard；回复确认进入 Search Planner，或说明要修改的框架、关键词、来源范围。"
            ),
        )

    def resume_gate_workflow(self, state: Dict[str, Any], user_decision: str) -> Dict[str, Any]:
        """Resume a gate-driven workflow from the user's decision."""
        pending_gate = state.get("pending_gate")
        normalized_decision = (user_decision or "").strip()

        if pending_gate == "audit_card_confirmed":
            if not self._is_confirmation(normalized_decision):
                revised = deepcopy(state)
                revised["status"] = "revision_requested"
                revised["user_decision"] = normalized_decision
                revised["next_action"] = "已记录修改意见；请先更新 AuditCard，再次输出给用户确认。"
                revised["updated_at"] = self._timestamp()
                return revised
            return self._run_after_audit_confirmation(state, normalized_decision)

        if pending_gate == "final_report_review":
            reviewed = deepcopy(state)
            reviewed["user_decision"] = normalized_decision
            reviewed["updated_at"] = self._timestamp()
            if self._is_final_approval(normalized_decision):
                reviewed["status"] = "complete"
                reviewed["pending_gate"] = None
                reviewed["next_action"] = "FinalReport 已通过，可以归档或进入后续行动。"
            else:
                reviewed["status"] = "revision_requested"
                reviewed["next_action"] = "已记录终稿修订意见；Report Writer/Humanizer 只能按修订清单改。"
            return reviewed

        raise ValueError(f"Cannot resume workflow from pending_gate={pending_gate!r}")

    def _missing_fields(self, artifact_name: str, artifact: Any, required_fields: List[str]) -> List[str]:
        if artifact_name == "SearchPlan":
            return self._missing_search_plan_fields(artifact, required_fields)
        if artifact_name == "SourceList":
            return self._missing_row_fields("sources", artifact, required_fields)
        if artifact_name == "ClaimGraph":
            claims = artifact.get("claims", []) if isinstance(artifact, dict) else []
            return self._missing_row_fields("claims", claims, required_fields)

        if not isinstance(artifact, dict):
            return list(required_fields)

        return [field for field in required_fields if field not in artifact]

    def _missing_search_plan_fields(self, artifact: Any, required_fields: List[str]) -> List[str]:
        if not isinstance(artifact, dict):
            return list(required_fields)

        top_level_fields = ["frameworks", "tasks"]
        missing = [field for field in top_level_fields if field not in artifact]
        task_fields = [field for field in required_fields if field not in top_level_fields]
        tasks = artifact.get("tasks", [])
        if not isinstance(tasks, list) or not tasks:
            missing.append("tasks")
            return missing

        for idx, task in enumerate(tasks):
            if not isinstance(task, dict):
                missing.append(f"tasks[{idx}]")
                continue
            for field in task_fields:
                if field not in task:
                    missing.append(f"tasks[{idx}].{field}")
        return missing

    def _missing_row_fields(self, row_name: str, rows: Any, required_fields: List[str]) -> List[str]:
        if not isinstance(rows, list) or not rows:
            return [row_name]

        missing = []
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                missing.append(f"{row_name}[{idx}]")
                continue
            for field in required_fields:
                if field not in row:
                    missing.append(f"{row_name}[{idx}].{field}")
        return missing

    def _validate_many(self, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [self.validate_artifact(name, artifact) for name, artifact in artifacts.items()]

    def _workflow_state(
        self,
        status: str,
        current_phase: str,
        pending_gate: str,
        artifacts: Dict[str, Any],
        validations: List[Dict[str, Any]],
        phase_results: List[Dict[str, Any]],
        next_action: str,
        user_decision: str = "",
    ) -> Dict[str, Any]:
        now = self._timestamp()
        return {
            "schema_version": "workflow_state.v1",
            "status": status,
            "current_phase": current_phase,
            "pending_gate": pending_gate,
            "artifacts": artifacts,
            "validations": validations,
            "phase_results": phase_results,
            "next_action": next_action,
            "user_decision": user_decision,
            "created_at": now,
            "updated_at": now,
        }

    def _run_after_audit_confirmation(self, state: Dict[str, Any], user_decision: str) -> Dict[str, Any]:
        artifacts = deepcopy(state["artifacts"])
        validations = deepcopy(state.get("validations", []))
        phase_results = deepcopy(state.get("phase_results", []))

        audit_card = artifacts["AuditCard"]
        intent_brief = artifacts["IntentBrief"]

        search_plan = self._build_dry_search_plan(audit_card)
        artifacts["SearchPlan"] = search_plan
        validations.append(self.validate_artifact("SearchPlan", search_plan))
        phase_results.append(self._phase_result("step1_search_planning", ["SearchPlan"]))

        source_list = self._build_dry_source_list()
        artifacts["SourceList"] = source_list
        validations.append(self.validate_artifact("SourceList", source_list))
        phase_results.append(self._phase_result("step1_parallel_source_hunting", ["SourceList"]))

        source_qa_notes, clean_source_list = self._build_dry_source_qa(source_list)
        artifacts["SourceQANotes"] = source_qa_notes
        artifacts["CleanSourceList"] = clean_source_list
        validations.extend(
            self._validate_many(
                {"SourceQANotes": source_qa_notes, "CleanSourceList": clean_source_list}
            )
        )
        phase_results.append(self._phase_result("step1_source_qa", ["SourceQANotes", "CleanSourceList"]))

        claim_graph = self._build_dry_claim_graph(clean_source_list)
        artifacts["ClaimGraph"] = claim_graph
        validations.append(self.validate_artifact("ClaimGraph", claim_graph))
        phase_results.append(self._phase_result("step2_analysis_and_specialists", ["ClaimGraph"]))

        citation_audit = self._build_dry_citation_audit(claim_graph)
        artifacts["CitationAudit"] = citation_audit
        validations.append(self.validate_artifact("CitationAudit", citation_audit))
        phase_results.append(self._phase_result("step2_citation_audit", ["CitationAudit"]))

        report_draft = self._build_dry_report_draft(intent_brief, clean_source_list, claim_graph)
        artifacts["ReportDraft"] = report_draft
        validations.append(self.validate_artifact("ReportDraft", report_draft))
        phase_results.append(self._phase_result("step3_report_draft", ["ReportDraft"]))

        final_report = self._build_dry_final_report(report_draft, clean_source_list)
        artifacts["FinalReport"] = final_report
        validations.append(self.validate_artifact("FinalReport", final_report))
        phase_results.append(self._phase_result("step3_humanizer_final", ["FinalReport"]))

        valid = all(validation["valid"] for validation in validations)
        return self._workflow_state(
            status="waiting_for_user" if valid else "blocked",
            current_phase="step3_humanizer_final",
            pending_gate="final_report_review" if valid else "artifact_validation_failed",
            artifacts=artifacts,
            validations=validations,
            phase_results=phase_results,
            next_action="请审核 FinalReport；回复通过完成，或提出具体修订意见。",
            user_decision=user_decision,
        )

    def _is_confirmation(self, user_decision: str) -> bool:
        return user_decision in {"确认", "同意", "可以", "继续", "ok", "OK", "yes", "Yes", "YES"}

    def _is_final_approval(self, user_decision: str) -> bool:
        return user_decision in {"通过", "确认", "同意", "可以", "ok", "OK", "yes", "Yes", "YES"}

    def _timestamp(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _phase_result(self, phase_id: str, output_artifacts: List[str]) -> Dict[str, Any]:
        phase = next(phase for phase in self.orchestration_plan if phase["id"] == phase_id)
        return {
            "id": phase_id,
            "nodes": deepcopy(phase["nodes"]),
            "gate": phase["gate"],
            "output_artifacts": output_artifacts,
        }

    def _build_dry_step0(self, user_query: str):
        from intent_classifier import build_step0_context, classify_intent

        step0_context = build_step0_context(user_query)
        semantic = step0_context["semantic_fields"]
        recommendations = classify_intent(user_query, top_k=3, return_complexity=True)
        frameworks = [rec["framework"] for rec in recommendations] or ["同行竞争对比"]

        intent_brief = {
            "research_object": semantic["research_object"],
            "user_decision": semantic["user_decision"],
            "audience": semantic["audience"],
            "time_scope": semantic["time_scope"],
            "output_shape": semantic["output_shape"],
            "evidence_need": semantic["evidence_need"],
            "ambiguity": semantic["ambiguity"],
            "semantic_signals": [
                {"signal": user_query, "meaning": semantic["user_decision"]},
            ],
            "classifier_check": {
                "top_frameworks": frameworks,
                "conflicts": [],
            },
            "preflight_skills": step0_context["preflight_skills"],
        }

        audit_card = {
            "topic": semantic["research_object"],
            "purpose": semantic["user_decision"],
            "llm_semantic_read": semantic,
            "recommended_frameworks": frameworks[:2],
            "dimensions": [
                {"name": "竞品变化", "question": "竞品最近发生了什么变化？"},
                {"name": "业务启示", "question": "这些变化对目标团队意味着什么？"},
            ],
            "keyword_families_zh": [semantic["research_object"], "新功能", "市场动态"],
            "keyword_families_en": [semantic["research_object"], "new features", "market update"],
            "source_scope": ["official", "media", "rss", "ugc", "finance_data", "marketing_intelligence"],
            "planned_expert_skills": step0_context["preflight_skills"],
            "open_assumptions": semantic["ambiguity"],
        }
        return intent_brief, audit_card

    def _build_dry_search_plan(self, audit_card: Dict[str, Any]) -> Dict[str, Any]:
        topic = audit_card["topic"]
        tasks = []
        for idx, dimension in enumerate(audit_card["dimensions"], 1):
            tasks.append(
                {
                    "task_id": f"SP{idx:03d}",
                    "dimension": dimension["name"],
                    "query_zh": [f"{topic} {dimension['name']}", f"{topic} {dimension['question']}"],
                    "query_en": [f"{topic} {dimension['name']}"],
                    "source_layers": audit_card["source_scope"],
                    "expected_evidence": ["发布时间", "来源类型", "关键事实", "对业务决策的影响"],
                    "source_id_prefix": "AUTO",
                }
            )
        return {"frameworks": audit_card["recommended_frameworks"], "tasks": tasks}

    def _build_dry_source_list(self) -> List[Dict[str, Any]]:
        source_specs = [
            ("OFF001", "官方更新记录", "Official", "官方", "high", "一手来源", "Official Source Hunter"),
            ("MED001", "媒体深度报道", "Business Media", "新闻媒体", "medium", "二手报道，需交叉验证", "Media Source Hunter"),
            ("RSS001", "RSS 快讯", "RSS Feed", "RSS快讯", "medium", "时效信号，不作为唯一事实依据", "RSS/News Hunter"),
            ("UGC001", "用户讨论样本", "UGC Platform", "UGC", "low", "用户情绪样本", "UGC/Social Hunter"),
            ("FIN001", "结构化金融数据样例", "Finance Data", "金融数据", "high", "结构化数据源", "Finance Data Hunter"),
            ("MKT001", "营销情报样例", "Marketing Skill", "营销情报", "medium", "营销专家 skill 输出", "Marketing Intelligence Hunter"),
        ]
        return [
            {
                "source_id": source_id,
                "title": title,
                "publisher": publisher,
                "source_type": source_type,
                "publish_date": "2026-07-08",
                "url": f"https://example.com/{source_id.lower()}",
                "confidence": confidence,
                "key_facts": [f"{title} 提供 dry-run 证据占位，用于验证 artifact 流程。"],
                "full_text_fetched": True,
                "collected_by": collected_by,
                "confidence_rationale": rationale,
            }
            for source_id, title, publisher, source_type, confidence, rationale, collected_by in source_specs
        ]

    def _build_dry_source_qa(self, source_list: List[Dict[str, Any]]):
        approved_source_ids = [source["source_id"] for source in source_list]
        source_qa_notes = {
            "deduped_count": len(source_list),
            "removed_duplicates": [],
            "stale_sources": [],
            "paywalled_summaries": [],
            "number_conflicts": [],
            "missing_evidence": [],
            "approved_source_ids": approved_source_ids,
        }
        clean_source_list = {
            "sources": source_list,
            "approved_source_ids": approved_source_ids,
            "excluded_source_ids": [],
            "source_quality_notes": ["dry-run: all placeholder sources are schema-valid."],
        }
        return source_qa_notes, clean_source_list

    def _build_dry_claim_graph(self, clean_source_list: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "claims": [
                {
                    "claim_id": "CL001",
                    "dimension": "竞品变化",
                    "claim_type": "fact",
                    "text": "dry-run 证据池已经覆盖官方、媒体、RSS、UGC、金融和营销情报来源。",
                    "source_ids": ["OFF001", "MED001", "RSS001"],
                    "confidence": "high",
                    "reasoning_basis": "来源类型覆盖完整，且通过 Source QA schema 校验。",
                },
                {
                    "claim_id": "CL002",
                    "dimension": "业务启示",
                    "claim_type": "judgment",
                    "text": "该 workflow 可以进入报告生成阶段，但真实结论必须替换为实搜证据。",
                    "source_ids": ["OFF001", "MKT001"],
                    "confidence": "medium",
                    "reasoning_basis": "当前为 dry-run，占位证据只证明流程可运行，不证明业务事实。",
                },
            ]
        }

    def _build_dry_citation_audit(self, claim_graph: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "pass",
            "issues": [],
            "required_rewrites": [],
            "approved_claim_ids": [claim["claim_id"] for claim in claim_graph["claims"]],
            "blocked_claim_ids": [],
        }

    def _build_dry_report_draft(
        self,
        intent_brief: Dict[str, Any],
        clean_source_list: Dict[str, Any],
        claim_graph: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_count = len(clean_source_list["sources"])
        core_judgment = "dry-run 已跑通多 agent artifact pipeline；真实调研时需替换为实搜证据。"
        supporting_reasons = [claim["text"] for claim in claim_graph["claims"]]
        markdown = "\n".join(
            [
                f"# {intent_brief['research_object']} workflow dry-run report",
                "",
                f"> {core_judgment}",
                "",
                "## 支撑理由",
                f"1. {supporting_reasons[0]}",
                f"2. {supporting_reasons[1]}",
                "",
                "## 风险",
                "dry-run 不代表真实业务结论。",
            ]
        )
        return {
            "markdown": markdown,
            "report_family": "Evidence Brief",
            "core_judgment": core_judgment,
            "supporting_reasons": supporting_reasons,
            "risk_section": "dry-run 不代表真实业务结论。",
            "reference_table": [source["source_id"] for source in clean_source_list["sources"]],
            "source_count": source_count,
        }

    def _build_dry_final_report(
        self,
        report_draft: Dict[str, Any],
        clean_source_list: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "markdown": report_draft["markdown"],
            "report_family": report_draft["report_family"],
            "source_count": len(clean_source_list["sources"]),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "humanizer_notes": ["dry-run: no factual edits; style pass preserved citations boundary."],
        }
