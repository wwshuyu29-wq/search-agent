#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow orchestration helpers for the multi-agent research pipeline."""

from copy import deepcopy
from datetime import datetime
import hashlib
import re
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from workflow_contracts import (
    approve_outline,
    build_agent_prompt,
    build_outline_candidates,
    review_outline_compliance,
    get_artifact_contracts,
    get_node_contracts,
    get_orchestration_plan,
    get_skill_invocations_for_node,
)


class WorkflowOrchestrator:
    """Validate handoff artifacts and route workflow phases."""

    def __init__(self, humanizer_adapter: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None):
        self.humanizer_adapter = humanizer_adapter
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

    def build_node_packets(self, phase_id: str, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build constrained execution packets for the sub-agent nodes in a phase."""
        phase = self._phase_by_id(phase_id)
        packets = []
        for node_id in phase["nodes"]:
            node = self._node_by_id(node_id)
            input_payload = {
                artifact_name: deepcopy(artifacts[artifact_name])
                for artifact_name in phase.get("input_artifacts", [])
                if artifact_name in artifacts
            }
            packets.append(
                {
                    "phase_id": phase_id,
                    "node_id": node_id,
                    "node_name": node["name"],
                    "parallel": bool(phase.get("parallel")),
                    "input_artifacts": deepcopy(phase.get("input_artifacts", [])),
                    "input_payload": input_payload,
                    "prompt": build_agent_prompt(node_id),
                    "allowed_tools_or_skills": deepcopy(node["tool_or_skill_use"]),
                    "skill_invocation_rules": get_skill_invocations_for_node(node_id),
                    "output_artifact": deepcopy(node["output_artifact"]),
                    "quality_gate": node["quality_gate"],
                    "hard_constraints": deepcopy(node["hard_constraints"]),
                }
            )
        return packets

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
        source_fragments = self._build_source_fragments(source_list)
        artifacts["SourceListFragment"] = source_fragments
        validations.append(self.validate_artifact("SourceListFragment", source_list))
        phase_results.append(self._phase_result("step1_parallel_source_hunting", ["SourceListFragment"]))

        raw_source_list, merger_log = self.merge_source_fragments(source_fragments)
        artifacts["RawSourceList"] = raw_source_list
        artifacts["MergerLog"] = merger_log
        validations.extend(self._validate_many({"RawSourceList": raw_source_list, "MergerLog": merger_log}))
        phase_results.append(self._phase_result("step1_source_merge", ["RawSourceList", "MergerLog"]))

        source_qa_notes, conflict_register, gap_list, clean_source_list = self._normalize_source_qa_result(
            self.source_qa(raw_source_list["sources"], artifacts.get("IntentBrief", {}).get("research_object", ""))
        )
        artifacts["SourceQANotes"] = source_qa_notes
        artifacts["ConflictRegister"] = conflict_register
        artifacts["GapList"] = gap_list
        artifacts["CleanSourceList"] = clean_source_list
        validations.extend(
            self._validate_many(
                {
                    "SourceQANotes": source_qa_notes,
                    "ConflictRegister": conflict_register,
                    "GapList": gap_list,
                    "CleanSourceList": clean_source_list,
                }
            )
        )
        phase_results.append(
            self._phase_result("step1_source_qa", ["SourceQANotes", "ConflictRegister", "GapList", "CleanSourceList"])
        )

        supplemental_source_list, refetch_notes = self._build_dry_gap_fill(conflict_register, gap_list)
        artifacts["SupplementalSourceList"] = supplemental_source_list
        artifacts["RefetchNotes"] = refetch_notes
        validations.extend(
            self._validate_many({"SupplementalSourceList": supplemental_source_list, "RefetchNotes": refetch_notes})
        )
        phase_results.append(
            self._phase_result("step1_gap_fill_or_pause", ["SupplementalSourceList", "RefetchNotes"])
        )

        claim_graph = self._build_dry_claim_graph(clean_source_list)
        artifacts["ClaimGraph"] = claim_graph
        specialist_notes = self._build_dry_specialist_notes(claim_graph)
        claim_graph_patch = self._build_dry_claim_graph_patch()
        artifacts["SpecialistNotes"] = specialist_notes
        artifacts["ClaimGraphPatch"] = claim_graph_patch
        validations.append(self.validate_artifact("ClaimGraph", claim_graph))
        validations.extend(
            self._validate_many({"SpecialistNotes": specialist_notes, "ClaimGraphPatch": claim_graph_patch})
        )
        phase_results.append(
            self._phase_result("step2_analysis_and_specialists", ["ClaimGraph", "SpecialistNotes", "ClaimGraphPatch"])
        )

        citation_audit, approved_claim_graph = self._build_dry_citation_audit(claim_graph)
        artifacts["CitationAudit"] = citation_audit
        artifacts["ApprovedClaimGraph"] = approved_claim_graph
        validations.extend(self._validate_many({"CitationAudit": citation_audit, "ApprovedClaimGraph": approved_claim_graph}))
        phase_results.append(self._phase_result("step2_citation_audit", ["CitationAudit", "ApprovedClaimGraph"]))

        report_draft = self._build_dry_report_draft(intent_brief, clean_source_list, approved_claim_graph)
        artifacts["ReportDraft"] = report_draft
        validations.append(self.validate_artifact("ReportDraft", report_draft))
        phase_results.append(self._phase_result("step3_report_draft", ["ReportDraft"]))

        final_report, humanizer_change_log = self._build_dry_final_report(report_draft, clean_source_list)
        artifacts["FinalReport"] = final_report
        artifacts["HumanizerChangeLog"] = humanizer_change_log
        validations.extend(self._validate_many({"FinalReport": final_report, "HumanizerChangeLog": humanizer_change_log}))
        phase_results.append(self._phase_result("step3_humanizer", ["FinalReport", "HumanizerChangeLog"]))

        integrity_diff = self.build_integrity_diff(report_draft, final_report)
        artifacts["IntegrityDiff"] = integrity_diff
        validations.append(self.validate_artifact("IntegrityDiff", integrity_diff))
        phase_results.append(self._phase_result("step3_integrity_check", ["IntegrityDiff"]))

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

        intent_brief, audit_card = self._build_formal_step0(user_query)
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
        normalized_decision = (user_decision or "").strip() if isinstance(user_decision, str) else ""

        if pending_gate == "audit_card_confirmed":
            if not self._is_confirmation(normalized_decision):
                revised = deepcopy(state)
                revised["status"] = "revision_requested"
                revised["user_decision"] = normalized_decision
                revised["next_action"] = "已记录修改意见；请先更新 AuditCard，再次输出给用户确认。"
                revised["updated_at"] = self._timestamp()
                return revised
            return self._run_after_audit_confirmation(state, normalized_decision)

        if pending_gate == "source_qa_conflict_resolution":
            return self._run_after_source_qa_resolution(state, normalized_decision)

        if pending_gate == "outline_approved_by_user":
            decision = user_decision if isinstance(user_decision, dict) else {"selection": normalized_decision}
            selection = str(decision.get("selection", "")).strip().upper()
            override = decision.get("sections_override")
            explicitly_approved = decision.get("approved_by_user") is True
            valid_choice = selection in {"A", "B", "C"} and override is None
            valid_override = explicitly_approved and self._valid_sections_override(override)
            if not (valid_choice or valid_override):
                waiting = deepcopy(state)
                waiting["status"] = "waiting_for_user"
                waiting["user_decision"] = normalized_decision or str(user_decision)
                waiting["next_action"] = "请选择 A/B/C；自定义大纲必须提供结构有效的 sections_override 且 approved_by_user=true。"
                waiting["updated_at"] = self._timestamp()
                return waiting
            return self._run_after_outline_approval(state, decision)

        if pending_gate == "humanizer_required":
            if not isinstance(user_decision, dict):
                raise ValueError("humanizer_required expects humanized_markdown and change_log")
            payload = {"markdown": user_decision.get("humanized_markdown"), "change_log": user_decision.get("change_log")}
            return self._complete_humanizer(
                state,
                deepcopy(state["artifacts"]),
                deepcopy(state.get("validations", [])),
                deepcopy(state.get("phase_results", [])),
                payload,
            )

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

    def _valid_sections_override(self, sections: Any) -> bool:
        return bool(sections) and isinstance(sections, list) and all(
            isinstance(section, dict)
            and bool(str(section.get("heading", "")).strip())
            and bool(str(section.get("purpose", "")).strip())
            and isinstance(section.get("required_claim_ids"), list)
            and bool(section.get("required_claim_ids"))
            and isinstance(section.get("word_budget"), int)
            and section.get("word_budget") > 0
            for section in sections
        )

    def _missing_fields(self, artifact_name: str, artifact: Any, required_fields: List[str]) -> List[str]:
        if artifact_name == "SearchPlan":
            return self._missing_search_plan_fields(artifact, required_fields)
        if artifact_name in {"SourceList", "SourceListFragment"}:
            return self._missing_row_fields("sources", artifact, required_fields)
        if artifact_name == "ClaimGraph":
            claims = artifact.get("claims", []) if isinstance(artifact, dict) else []
            return self._missing_row_fields("claims", claims, required_fields)
        if artifact_name == "ApprovedClaimGraph":
            if not isinstance(artifact, dict):
                return list(required_fields)
            missing = [field for field in required_fields if field not in artifact]
            claims = artifact.get("claims", [])
            if not isinstance(claims, list) or not claims:
                missing.append("claims")
            for idx, claim in enumerate(claims if isinstance(claims, list) else []):
                if claim.get("audit_status") != "passed":
                    missing.append(f"claims[{idx}].audit_status=passed")
            return missing
        if artifact_name == "OutlinePlan":
            missing = [field for field in required_fields if field not in artifact]
            if len(artifact.get("candidates", [])) != 3:
                missing.append("candidates.exactly_three")
            return missing
        if artifact_name == "ApprovedOutline":
            missing = [field for field in required_fields if field not in artifact]
            if artifact.get("approved_by_user") is not True:
                missing.append("approved_by_user=true")
            return missing
        if artifact_name in {"OutlineComplianceReview", "IntegrityDiff"}:
            missing = [field for field in required_fields if field not in artifact]
            if artifact.get("status") != "passed":
                missing.append("status=passed")
            return missing

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

    def merge_source_fragments(self, fragments: List[Dict[str, Any]]):
        """Deterministically merge source hunter fragments into RawSourceList and MergerLog."""
        flat_sources: List[Dict[str, Any]] = []
        for fragment in fragments:
            for source in fragment.get("sources", []):
                row = deepcopy(source)
                row.setdefault("channel", fragment.get("node_id", row.get("collected_by", "unknown")))
                row["canonical_url"] = self._canonical_url(row.get("canonical_url") or row.get("url", ""))
                flat_sources.append(row)

        kept_by_key: Dict[str, Dict[str, Any]] = {}
        merged_sources = []
        for row in flat_sources:
            key = row.get("canonical_url") or self._source_fingerprint(row)
            if key not in kept_by_key:
                kept_by_key[key] = row
                continue

            kept = kept_by_key[key]
            winner, loser = self._choose_source_winner(kept, row)
            kept_by_key[key] = winner
            merged_sources.append(
                {
                    "canonical_url": key,
                    "kept_source_id": winner["source_id"],
                    "merged_source_ids": [loser["source_id"]],
                    "reason": "duplicate canonical_url; kept stronger source tier/confidence",
                }
            )

        sources = list(kept_by_key.values())
        raw_source_list = {
            "sources": sources,
            "source_count": len(sources),
            "canonical_url": [source.get("canonical_url") for source in sources],
            "merged_duplicate_count": len(merged_sources),
        }
        merger_log = {
            "input_count": len(flat_sources),
            "output_count": len(sources),
            "deduped_count": len(merged_sources),
            "merged_sources": merged_sources,
            "id_rewrites": [],
            "warnings": [],
        }
        return raw_source_list, merger_log

    def build_integrity_diff(self, report_draft: Dict[str, Any], final_report: Dict[str, Any], humanizer_change_log: Dict[str, Any] = None, approved_outline: Dict[str, Any] = None) -> Dict[str, Any]:
        """Detect evidence-bearing changes between ReportDraft and FinalReport."""
        before = report_draft.get("markdown", "")
        after = final_report.get("markdown", "")
        changed_numbers = self._changed_tokens(before, after, r"\d+(?:\.\d+)?")
        changed_dates = self._changed_tokens(before, after, r"\d{4}-\d{1,2}-\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日")
        changed_source_ids = self._changed_tokens(before, after, r"\b(?:OFF|MED|RSS|NEWS|UGC|FIN|MKT)\d{3}\b")
        changed_claim_ids = self._changed_tokens(before, after, r"\bCLM?\d{3}\b")
        changed_confidence = self._changed_tokens(before, after, r"(?:置信度|confidence)\s*[：:]?\s*(?:高|中|低|high|medium|low)")
        risk_pattern = r"[^。.!?]*(?:风险|不确定|限制|risk|uncertain|limit)[^。.!?]*[。.!?]?"
        risk_boundary_changes = self._changed_tokens(before, after, risk_pattern)
        before_sentences = self._substantive_sentences(before)
        after_sentences = self._substantive_sentences(after)
        sentence_mappings, new_unapproved_sentences = self._map_humanized_sentences(before_sentences, after_sentences)
        new_factual_sentences = list(new_unapproved_sentences)
        before_headings = re.findall(r"^## (.+)$", before, re.M)
        after_headings = re.findall(r"^## (.+)$", after, re.M)
        expected_headings = [section.get("heading") for section in (approved_outline or {}).get("sections", [])]
        structure_changes = [] if before_headings == after_headings and (not expected_headings or after_headings[:len(expected_headings)] == expected_headings) else [{"before": before_headings, "after": after_headings, "expected": expected_headings}]
        deleted_evidence_spans = [span for section in report_draft.get("sections", []) for span in section.get("evidence_spans", []) if span not in after]
        polarity_terms = r"不应|应|不建议|建议|禁止|允许|优先|暂缓|必须|无需|需要"
        changed_polarity = self._changed_tokens(before, after, polarity_terms)
        caveat_pattern = r"[^。.!?]*(?:假设|前提|边界|仅限|除非|assumption|caveat)[^。.!?]*[。.!?]?"
        assumption_caveat_changes = self._changed_tokens(before, after, caveat_pattern)
        log = humanizer_change_log or {}
        log_violations = []
        if humanizer_change_log is not None and log.get("style_only") is not True:
            log_violations.append("style_only must be true")
        if humanizer_change_log is not None and log.get("unchanged_fact_confirmation") is not True:
            log_violations.append("unchanged_fact_confirmation must be true")
        failures = changed_numbers or changed_dates or changed_source_ids or changed_claim_ids or changed_confidence or risk_boundary_changes or new_unapproved_sentences or structure_changes or deleted_evidence_spans or changed_polarity or assumption_caveat_changes or log_violations
        return {
            "status": "failed" if failures else "passed",
            "changed_numbers": changed_numbers,
            "changed_dates": changed_dates,
            "changed_source_ids": changed_source_ids,
            "changed_claim_ids": changed_claim_ids,
            "changed_confidence": changed_confidence,
            "risk_boundary_changes": risk_boundary_changes,
            "new_factual_sentences": new_factual_sentences,
            "new_unapproved_sentences": new_unapproved_sentences,
            "sentence_mappings": sentence_mappings,
            "structure_changes": structure_changes,
            "deleted_evidence_spans": deleted_evidence_spans,
            "changed_polarity": changed_polarity,
            "assumption_caveat_changes": assumption_caveat_changes,
            "humanizer_log_violations": log_violations,
        }

    def _sentences(self, text: str) -> List[str]:
        return [part.strip() for part in re.split(r"(?<=[。.!?])\s*|\n+", text) if part.strip()]

    def _substantive_sentences(self, text: str) -> List[str]:
        return [sentence for sentence in self._sentences(text) if not re.match(r"^#{1,6}\s+", sentence)]

    def _map_humanized_sentences(self, before: List[str], after: List[str]):
        """Conservatively require one-to-one sentence rewrites; additions are blocked."""
        mappings = []
        unapproved = []
        if len(after) != len(before):
            if len(after) > len(before):
                unapproved.extend(after[len(before):])
            else:
                unapproved.append("<deleted sentence>")
        for index, after_sentence in enumerate(after[:len(before)]):
            before_sentence = before[index]
            before_core = self._style_normalized_sentence(before_sentence)
            after_core = self._style_normalized_sentence(after_sentence)
            before_connective = self._leading_connective_group(before_sentence)
            after_connective = self._leading_connective_group(after_sentence)
            connectives_match = before_connective == after_connective
            anchors_match = self._sentence_anchors(before_sentence) == self._sentence_anchors(after_sentence)
            approved = anchors_match and connectives_match and before_core == after_core
            mappings.append({"before": before_sentence, "after": after_sentence, "approved": approved})
            if not approved:
                unapproved.append(after_sentence)
        return mappings, unapproved

    def _style_normalized_sentence(self, sentence: str) -> str:
        text = re.sub(r"^[\s]*(?:所以|因此|因而|于是|同时|此外|不过|然而)[，,：:]?\s*", "", sentence, flags=re.I)
        return re.sub(r"[\s，,。.!！？?；;：:]", "", text).lower()

    def _leading_connective_group(self, sentence: str):
        match = re.match(r"^\s*(所以|因此|因而|于是|同时|此外|不过|然而)(?:[，,：:]?\s*)", sentence, re.I)
        if not match:
            return None
        connective = match.group(1)
        groups = {
            "causal": {"所以", "因此", "因而", "于是"},
            "additive": {"同时", "此外"},
            "contrast": {"不过", "然而"},
        }
        return next(group for group, members in groups.items() if connective in members)

    def _sentence_anchors(self, sentence: str):
        pattern = r"\b(?:OFF|MED|RSS|NEWS|UGC|FIN|MKT)\d{3}\b|\bCLM?\d{3}\b|https?://[^\s)]+|\d+(?:\.\d+)?"
        return re.findall(pattern, sentence, re.I)

    def _canonical_url(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlsplit(url)
        filtered_query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ]
        query = urlencode(filtered_query)
        path = parsed.path.rstrip("/") or parsed.path
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, query, ""))

    def _source_fingerprint(self, source: Dict[str, Any]) -> str:
        return "|".join(
            [
                str(source.get("title", "")).strip().lower(),
                str(source.get("publisher", "")).strip().lower(),
                str(source.get("publish_date", "")).strip(),
            ]
        )

    def _choose_source_winner(self, first: Dict[str, Any], second: Dict[str, Any]):
        prefix_rank = {"OFF": 0, "FIN": 1, "MED": 2, "RSS": 3, "NEWS": 3, "MKT": 4, "UGC": 5}
        confidence_rank = {"high": 0, "medium": 1, "low": 2}

        def rank(source: Dict[str, Any]):
            source_id = source.get("source_id", "")
            prefix = re.match(r"^[A-Z]+", source_id)
            return (
                prefix_rank.get(prefix.group(0) if prefix else "", 99),
                confidence_rank.get(str(source.get("confidence", "")).lower(), 99),
            )

        if rank(second) < rank(first):
            return second, first
        return first, second

    def _changed_tokens(self, before: str, after: str, pattern: str) -> List[Dict[str, Any]]:
        before_tokens = re.findall(pattern, before)
        after_tokens = re.findall(pattern, after)
        if before_tokens == after_tokens:
            return []
        return [{"before": before_tokens, "after": after_tokens}]

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

    def build_search_plan(self, audit_card: Dict[str, Any]) -> Dict[str, Any]:
        """Build a formal SearchPlan without dry-run fixtures or placeholder URLs."""
        tasks = []
        prefixes = {"official": "OFF", "media": "MED", "rss": "RSS", "ugc": "UGC", "finance_data": "FIN", "marketing_intelligence": "MKT"}
        hunter_by_layer = {"official": "official_source_hunter", "media": "media_source_hunter", "rss": "rss_news_hunter", "ugc": "ugc_social_hunter", "finance_data": "finance_data_hunter", "marketing_intelligence": "marketing_intelligence_hunter"}
        topic = audit_card["topic"]
        for dimension_index, dimension in enumerate(audit_card["dimensions"], 1):
            for layer in audit_card["source_scope"]:
                if layer not in hunter_by_layer:
                    continue
                tasks.append({
                    "task_id": f"{prefixes[layer]}-T{dimension_index:03d}",
                    "assigned_hunter": hunter_by_layer[layer],
                    "dimension": dimension["name"],
                    "query_zh": [f"{topic} {dimension['name']}", f"{topic} {dimension['question']}"],
                    "query_en": [f"{topic} {dimension['name']}"],
                    "source_layers": [layer],
                    "expected_evidence": ["发布时间", "原文内容", "与调研主题的直接关系"],
                    "source_id_prefix": prefixes[layer],
                })
        return {"frameworks": audit_card["recommended_frameworks"], "tasks": tasks}

    def source_qa(self, sources: List[Dict[str, Any]], topic: str = ""):
        """Conservatively gate thin, low-confidence, or weakly relevant evidence."""
        approved, excluded, missing = [], [], []
        source_types = set()
        topic_compact = re.sub(r"\s+", "", topic or "")
        topic_terms = {topic_compact}
        for suffix in ("地图", "导航", "公司", "集团", "产品"):
            if topic_compact.endswith(suffix) and len(topic_compact) > len(suffix):
                topic_terms.add(topic_compact[:-len(suffix)])
        for source in sources:
            source_id = source.get("source_id")
            url = source.get("url") or source.get("canonical_url")
            if not source_id or not url:
                excluded.append(source_id or "unknown")
                missing.append({"source_id": source_id, "reason": "missing source_id or URL"})
                continue
            source_types.add(str(source.get("source_type", "")).lower())
            searchable = " ".join(str(source.get(field, "")) for field in ("title", "publisher", "support_excerpt", "evidence_text"))
            searchable += " " + " ".join(str(item) for item in source.get("key_facts", []))
            searchable_compact = re.sub(r"\s+", "", searchable)
            if topic_compact and not any(term and term in searchable_compact for term in topic_terms):
                missing.append({"source_id": source_id, "reason": f"insufficient topic relevance for {topic}"})
            if source.get("confidence") == "low" and not source.get("full_text_fetched"):
                missing.append({"source_id": source_id, "reason": "low-confidence source has no full text"})
            approved.append(source_id)
        has_primary_layer = any("official" in item for item in source_types)
        has_media_layer = any(item in {"media", "news_media", "新闻媒体"} or "media" in item for item in source_types)
        if not has_primary_layer and not has_media_layer:
            missing.append({"source_id": None, "reason": "official/media evidence layers missing"})
        requires_resolution = bool(missing)
        notes = {
            "deduped_count": len(sources), "removed_duplicates": [], "stale_sources": [],
            "paywalled_summaries": [], "number_conflicts": [], "missing_evidence": missing,
            "approved_source_ids": approved, "requires_user_resolution": requires_resolution,
        }
        conflicts = {"conflicts": [], "requires_user_decision": requires_resolution, "recommended_resolution": "refetch official/media evidence or explicitly accept_limited_evidence"}
        gaps = {"gaps": missing, "requires_refetch": requires_resolution, "blocking_gap_count": len(missing)}
        clean = {
            "sources": [s for s in sources if s.get("source_id") in approved],
            "approved_source_ids": approved, "excluded_source_ids": excluded,
            "source_quality_notes": ["Blocking evidence gaps require explicit resolution."] if requires_resolution else [],
            "evidence_mode": "blocked" if requires_resolution else "standard",
        }
        return notes, conflicts, gaps, clean

    def build_claim_graph(self, clean_source_list: Dict[str, Any]) -> Dict[str, Any]:
        """Extract minimal factual claims from approved source key facts."""
        claims = []
        for source in clean_source_list.get("sources", []):
            if source.get("method_source"):
                continue
            for fact in source.get("key_facts", []):
                if fact:
                    normalized = self._normalize_evidence_text(fact)
                    boundary = source.get("evidence_boundary") or source.get("coverage_scope") or source.get("limitations")
                    if not boundary:
                        boundary = "仅覆盖来源 {source_id} 的明确内容，来源类型为 {source_type}，发布日期为 {date}。".format(
                            source_id=source["source_id"], source_type=source.get("source_type", "unknown"),
                            date=source.get("publish_date", "unknown"),
                        )
                    claims.append({"claim_id": f"CL{len(claims)+1:03d}", "dimension": source.get("source_type", "evidence"), "claim_type": "fact", "text": fact, "source_ids": [source["source_id"]], "confidence": source.get("confidence", "medium"), "reasoning_basis": "verbatim source key fact", "evidence_text": fact, "evidence_boundary": boundary, "boundary_status": "provided", "evidence_hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest()})
        return {"claims": claims}

    def audit_claim_graph(self, claim_graph: Dict[str, Any], clean_source_list: Dict[str, Any]):
        """Audit every claim type before it can enter ApprovedClaimGraph."""
        source_map = {s.get("source_id"): s for s in clean_source_list.get("sources", [])}
        approved_source_ids = set(clean_source_list.get("approved_source_ids", source_map))
        approved, blocked, issues = [], [], []
        valid_types = {"fact", "calculation", "assumption", "judgment"}
        for claim in claim_graph.get("claims", []):
            claim_type = claim.get("claim_type")
            cited = claim.get("source_ids", [])
            reason = None
            if claim_type not in valid_types:
                reason = "unknown claim_type"
            elif not cited:
                reason = f"{claim_type} claim has no source and is excluded from ApprovedClaimGraph"
            elif any(sid not in source_map or sid not in approved_source_ids for sid in cited):
                reason = "source_id missing or not approved"
            elif any(source_map[sid].get("method_source") for sid in cited):
                reason = "method source cannot support an approved claim"
            elif not claim.get("evidence_boundary") or claim.get("boundary_status") == "missing":
                reason = "claim requires a real evidence_boundary before Citation Audit"
            else:
                sources = [source_map[sid] for sid in cited]
                if claim_type == "fact" and not self._claim_has_textual_support(claim, sources):
                    reason = "source evidence does not textually support fact"
                elif claim_type == "calculation":
                    if not (claim.get("evidence_text") or claim.get("support_excerpt")):
                        reason = "calculation requires evidence_text/support_excerpt"
                    elif not claim.get("calculation_inputs") or not claim.get("formula"):
                        reason = "calculation requires verifiable inputs and formula"
                    elif not self._claim_has_textual_support(claim, sources):
                        reason = "source evidence does not support calculation"
                elif claim_type == "judgment":
                    if not claim.get("reasoning_basis"):
                        reason = "judgment requires reasoning_basis"
                    elif not self._text_has_source_support(claim["reasoning_basis"], sources):
                        reason = "judgment reasoning_basis is not linked to source evidence"
                elif claim_type == "assumption":
                    support = claim.get("reasoning_basis")
                    premise_ids = claim.get("premise_claim_ids") or []
                    passed_by_id = {row.get("claim_id"): row for row in approved}
                    if not claim.get("evidence_boundary"):
                        reason = "assumption requires explicit evidence_boundary"
                    elif claim.get("confidence") != "low":
                        reason = "assumption must remain low confidence"
                    elif not support or not claim.get("inference_rule"):
                        reason = "assumption requires reasoning_basis and explicit inference_rule"
                    elif not premise_ids or any(pid not in passed_by_id for pid in premise_ids):
                        reason = "assumption premises must exist and already be passed"
                    elif claim.get("verification_status") in {"pending", "unverified", "待验证"} or claim.get("pending_validation") is True:
                        reason = "pending assumption cannot enter writer"
                    elif not self._assumption_terms_relate(claim, [passed_by_id[pid] for pid in premise_ids]):
                        reason = "assumption text is not related to its passed premises and reasoning_basis"
            if reason:
                blocked.append(claim.get("claim_id")); issues.append({"claim_id": claim.get("claim_id"), "reason": reason})
            else:
                row = deepcopy(claim); row["audit_status"] = "passed"; approved.append(row)
        status = "passed" if approved and not blocked else "failed"
        audit = {"status": status, "issues": issues, "required_rewrites": issues, "approved_claim_ids": [c["claim_id"] for c in approved], "blocked_claim_ids": blocked}
        return audit, {"approved_claim_ids": audit["approved_claim_ids"], "claims": approved}

    def _normalize_evidence_text(self, value: Any) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff]+", "", str(value).lower())

    def _text_has_source_support(self, value: Any, sources: List[Dict[str, Any]]) -> bool:
        text = self._normalize_evidence_text(value)
        negation_pairs = (("增长", "下降"), ("建议", "不建议"), ("上升", "下滑"), ("盈利", "亏损"))
        excerpts = []
        for source in sources:
            excerpts.extend(source.get("key_facts", []))
            excerpts.extend([source.get("support_excerpt"), source.get("evidence_text")])
        normalized = [self._normalize_evidence_text(item) for item in excerpts if item]
        for positive, negative in negation_pairs:
            if positive in text and any(negative in item for item in normalized):
                return False
            if negative in text and any(positive in item and negative not in item for item in normalized):
                return False
        return bool(text) and any(text in item or item in text for item in normalized if item)

    def _assumption_terms_relate(self, claim: Dict[str, Any], premises: List[Dict[str, Any]]) -> bool:
        def tokenize(value):
            text = str(value).lower()
            terms = set(re.findall(r"[a-z0-9]+", text))
            for run in re.findall(r"[\u4e00-\u9fff]+", text):
                terms.update(run[index:index + 2] for index in range(max(0, len(run) - 1)))
            return terms
        claim_terms = tokenize(claim.get("text"))
        basis_terms = tokenize(claim.get("reasoning_basis"))
        premise_terms = set().union(*(tokenize(row.get("text")) for row in premises))
        return bool(claim_terms & basis_terms) and bool(claim_terms & premise_terms)

    def _claim_has_textual_support(self, claim: Dict[str, Any], sources: List[Dict[str, Any]]) -> bool:
        claim_text = self._normalize_evidence_text(claim.get("text", ""))
        excerpts = [claim.get("evidence_text"), claim.get("support_excerpt")]
        for source in sources:
            excerpts.extend(source.get("key_facts", []))
            excerpts.append(source.get("support_excerpt"))
        normalized = [self._normalize_evidence_text(text) for text in excerpts if text]
        source_supported = self._text_has_source_support(claim.get("evidence_text") or claim.get("support_excerpt") or claim.get("text"), sources)
        if claim.get("evidence_hash") and source_supported and any(hashlib.sha256(text.encode("utf-8")).hexdigest() == claim["evidence_hash"] for text in normalized):
            return True
        return source_supported and bool(claim_text) and any(claim_text in text or text in claim_text for text in normalized if text)

    def _run_after_audit_confirmation(self, state: Dict[str, Any], user_decision: str) -> Dict[str, Any]:
        artifacts = deepcopy(state["artifacts"])
        validations = deepcopy(state.get("validations", []))
        phase_results = deepcopy(state.get("phase_results", []))

        audit_card = artifacts["AuditCard"]

        search_plan = self.build_search_plan(audit_card)
        artifacts["SearchPlan"] = search_plan
        validations.append(self.validate_artifact("SearchPlan", search_plan))
        phase_results.append(self._phase_result("step1_search_planning", ["SearchPlan"]))
        return self._workflow_state(
            status="ready_for_execution",
            current_phase="step1_parallel_source_hunting",
            pending_gate="source_hunters_required",
            artifacts=artifacts,
            validations=validations,
            phase_results=phase_results,
            next_action="运行 --execute-source-hunters，再运行 --workflow-continue-from-sources。",
            user_decision=user_decision,
        )

    def _run_after_source_qa_resolution(self, state: Dict[str, Any], user_decision: str) -> Dict[str, Any]:
        artifacts = deepcopy(state["artifacts"])
        validations = deepcopy(state.get("validations", []))
        phase_results = deepcopy(state.get("phase_results", []))

        artifacts["SourceQANotes"]["user_resolution"] = user_decision
        accept_limited = user_decision.strip().lower() in {"accept_limited_evidence", "接受有限证据", "接受低证据模式"}
        if artifacts.get("CleanSourceList", {}).get("evidence_mode") == "blocked" and not accept_limited:
            waiting = deepcopy(state)
            waiting["user_decision"] = user_decision
            waiting["next_action"] = "证据缺口仍阻断流程；请补充来源，或明确回复 accept_limited_evidence。"
            waiting["updated_at"] = self._timestamp()
            return waiting
        artifacts["SourceQANotes"]["number_conflicts"] = []
        if accept_limited:
            artifacts["SourceQANotes"]["accepted_evidence_gaps"] = deepcopy(artifacts["SourceQANotes"].get("missing_evidence", []))
            artifacts["SourceQANotes"]["missing_evidence"] = []
            artifacts["CleanSourceList"]["evidence_mode"] = "limited"
            for source in artifacts["CleanSourceList"].get("sources", []):
                source["confidence"] = "low"
                existing = source.get("evidence_boundary") or source.get("coverage_scope") or ""
                source["evidence_boundary"] = f"有限证据模式：{existing or '仅覆盖当前来源明确陈述，缺少 official/media 交叉验证。'}"
        artifacts.setdefault(
            "ConflictRegister",
            {"conflicts": [], "requires_user_decision": False, "recommended_resolution": "user resolved"},
        )
        artifacts["ConflictRegister"]["requires_user_decision"] = False
        artifacts.setdefault("GapList", {"gaps": [], "requires_refetch": False, "blocking_gap_count": 0})
        artifacts["CleanSourceList"].setdefault("source_quality_notes", []).append(
            f"user_resolution: {user_decision}"
        )
        supplemental_source_list, refetch_notes = self._build_formal_gap_fill(
            artifacts["ConflictRegister"], artifacts["GapList"]
        )
        artifacts["SupplementalSourceList"] = supplemental_source_list
        artifacts["RefetchNotes"] = refetch_notes
        validations.extend(
            self._validate_many({"SupplementalSourceList": supplemental_source_list, "RefetchNotes": refetch_notes})
        )
        phase_results.append(
            self._phase_result("step1_gap_fill_or_pause", ["SupplementalSourceList", "RefetchNotes"])
        )

        return self._run_analysis_to_final(
            artifacts=artifacts,
            validations=validations,
            phase_results=phase_results,
            user_decision=user_decision,
        )

    def _run_analysis_to_final(
        self,
        artifacts: Dict[str, Any],
        validations: List[Dict[str, Any]],
        phase_results: List[Dict[str, Any]],
        user_decision: str,
    ) -> Dict[str, Any]:
        intent_brief = artifacts["IntentBrief"]
        clean_source_list = artifacts["CleanSourceList"]

        claim_graph = self.build_claim_graph(clean_source_list)
        artifacts["ClaimGraph"] = claim_graph
        specialist_notes, claim_graph_patch = self._execute_formal_specialists(artifacts, claim_graph)
        artifacts["SpecialistNotes"] = specialist_notes
        artifacts["ClaimGraphPatch"] = claim_graph_patch
        validations.append(self.validate_artifact("ClaimGraph", claim_graph))
        validations.extend(
            self._validate_many({"SpecialistNotes": specialist_notes, "ClaimGraphPatch": claim_graph_patch})
        )
        phase_results.append(
            self._phase_result("step2_analysis_and_specialists", ["ClaimGraph", "SpecialistNotes", "ClaimGraphPatch"])
        )

        citation_audit, approved_claim_graph = self.audit_claim_graph(claim_graph, clean_source_list)
        artifacts["CitationAudit"] = citation_audit
        artifacts["ApprovedClaimGraph"] = approved_claim_graph
        validations.extend(self._validate_many({"CitationAudit": citation_audit, "ApprovedClaimGraph": approved_claim_graph}))
        phase_results.append(self._phase_result("step2_citation_audit", ["CitationAudit", "ApprovedClaimGraph"]))
        if citation_audit["status"] != "passed":
            return self._workflow_state("blocked", "step2_citation_audit", "citation_audit_failed", artifacts, validations, phase_results, "Citation audit failed.", user_decision)
        outline_plan = build_outline_candidates(intent_brief, approved_claim_graph["approved_claim_ids"])
        artifacts["OutlinePlan"] = outline_plan
        validations.append(self.validate_artifact("OutlinePlan", outline_plan))
        phase_results.append(self._phase_result("step3_outline_candidates", ["OutlinePlan"]))
        return self._workflow_state("waiting_for_user", "step3_outline_approval", "outline_approved_by_user", artifacts, validations, phase_results, "请选择 A/B/C，或提供组合及 sections_override。", user_decision)

    def _execute_formal_specialists(self, artifacts: Dict[str, Any], claim_graph: Dict[str, Any]):
        try:
            from specialist_executor import SpecialistRequest, execute_specialist
            from specialist_router import route_specialists
        except ImportError:
            from .specialist_executor import SpecialistRequest, execute_specialist
            from .specialist_router import route_specialists

        query = artifacts.get("RawUserQuery", "")
        intent = artifacts.get("IntentBrief", {})
        clean = artifacts["CleanSourceList"]
        frameworks = artifacts.get("AuditCard", {}).get("recommended_frameworks", [])
        notes, gaps, patches, specialist_ids = [], [], [], []
        for domain, node_id in (("marketing", "marketing_specialist"), ("finance", "finance_specialist")):
            for entry in route_specialists(query, node_id, domain=domain, limit=3):
                specialist_ids.append(entry["id"])
                request = SpecialistRequest(
                    entry["id"], intent.get("research_object", "Research"),
                    intent.get("user_decision", "analyze"), frameworks,
                    clean.get("sources", []), claim_graph.get("claims", []), node_id,
                )
                result = execute_specialist(request)
                notes.extend(result.notes)
                gaps.extend(result.evidence_gaps)
                patches.extend(result.claim_graph_patch)
        if not specialist_ids:
            notes.append({"type": "method_note", "text": "No specialist trigger matched the confirmed topic and frameworks."})
            gaps.append({"type": "specialist_evidence_gap", "text": "No domain-specific specialist method was selected."})
        specialist_notes = {
            "specialist": ", ".join(specialist_ids) or "specialist router",
            "notes": notes, "source_ids": clean.get("approved_source_ids", []),
            "risk_boundaries": gaps or ["Method specialists do not create facts; all claims remain source-bound."],
        }
        claim_graph_patch = {
            "patch_id": "PATCH001", "target_claim_ids": [], "new_claims": patches,
            "source_ids": sorted({sid for patch in patches for sid in patch.get("source_ids", [])}),
            "patch_reason": "Executed routed specialists; method-only outputs remain notes and evidence gaps.",
        }
        return specialist_notes, claim_graph_patch

    def _run_after_outline_approval(self, state: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        artifacts = deepcopy(state["artifacts"])
        validations = deepcopy(state.get("validations", []))
        phase_results = deepcopy(state.get("phase_results", []))
        candidates = artifacts["OutlinePlan"]["candidates"]
        selection = str(decision.get("selection", "")).strip().upper()
        override = decision.get("sections_override")
        if selection in {"A", "B", "C"}:
            selected_id = candidates[ord(selection) - ord("A")]["outline_id"]
        elif decision.get("approved_by_user") is True and self._valid_sections_override(override):
            selected_id = artifacts["OutlinePlan"]["recommended_outline_id"]
        else:
            raise ValueError("大纲选择必须是 A/B/C；自定义大纲必须结构有效且 approved_by_user=true。")
        approved_outline = approve_outline(
            artifacts["OutlinePlan"], selected_id, approved_by_user=True,
            sections_override=override if override is not None else None,
        )
        if override is not None:
            approved_outline["selected_outline_id"] = selected_id + "_custom"
        artifacts["ApprovedOutline"] = approved_outline
        validations.append(self.validate_artifact("ApprovedOutline", approved_outline))
        phase_results.append(self._phase_result("step3_outline_approval", ["ApprovedOutline"]))
        from report_generator import ReportGenerator
        report_draft = ReportGenerator().generate_from_approved_outline(approved_outline, artifacts["ApprovedClaimGraph"]["claims"], artifacts["CleanSourceList"]["sources"], artifacts["IntentBrief"].get("subject", "Research"), artifacts["IntentBrief"].get("user_decision", ""))
        artifacts["ReportDraft"] = report_draft
        validations.append(self.validate_artifact("ReportDraft", report_draft))
        phase_results.append(self._phase_result("step3_report_draft", ["ReportDraft"]))
        compliance = review_outline_compliance(approved_outline, report_draft)
        artifacts["OutlineComplianceReview"] = compliance
        validations.append(self.validate_artifact("OutlineComplianceReview", compliance))
        phase_results.append(self._phase_result("step3_outline_compliance", ["OutlineComplianceReview"]))
        if compliance["status"] != "passed":
            return self._workflow_state("blocked", "step3_outline_compliance", "outline_compliance_failed", artifacts, validations, phase_results, "Outline compliance failed.")
        if self.humanizer_adapter is None:
            return self._workflow_state("waiting_for_user", "step3_humanizer", "humanizer_required", artifacts, validations, phase_results, "请运行真实 Humanizer Editor，并提交 humanized_markdown 与 change_log 后恢复。")
        humanized = self.humanizer_adapter(deepcopy(report_draft))
        return self._complete_humanizer(state, artifacts, validations, phase_results, humanized)

    def _complete_humanizer(self, state, artifacts, validations, phase_results, humanized):
        markdown = humanized.get("markdown") if isinstance(humanized, dict) else None
        change_log = humanized.get("change_log") if isinstance(humanized, dict) else None
        if not markdown or not isinstance(change_log, dict):
            return self._workflow_state("blocked", "step3_humanizer", "humanizer_invalid", artifacts, validations, phase_results, "Humanizer 必须返回改写 markdown 和 change_log。")
        report_draft = artifacts["ReportDraft"]
        final_report = {"markdown": markdown, "report_family": report_draft["report_family"], "source_count": len(report_draft["references"]), "generated_at": self._timestamp(), "humanizer_notes": change_log.get("changed_sections", [])}
        humanized_sections = self._sections_from_markdown(markdown, report_draft.get("sections", []))
        final_report["sections"] = humanized_sections
        post_humanizer_compliance = review_outline_compliance(artifacts["ApprovedOutline"], final_report)
        artifacts["PostHumanizerOutlineComplianceReview"] = post_humanizer_compliance
        artifacts.update({"FinalReport": final_report, "HumanizerChangeLog": change_log})
        phase_results.append(self._phase_result("step3_humanizer", ["FinalReport", "HumanizerChangeLog"]))
        integrity = self.build_integrity_diff(report_draft, final_report, change_log, artifacts["ApprovedOutline"])
        artifacts["IntegrityDiff"] = integrity
        validations.extend(self._validate_many({"FinalReport": final_report, "HumanizerChangeLog": change_log, "IntegrityDiff": integrity}))
        phase_results.append(self._phase_result("step3_integrity_check", ["IntegrityDiff"]))
        valid = all(v["valid"] for v in validations) and post_humanizer_compliance["status"] == "passed" and integrity["status"] == "passed"
        return self._workflow_state("waiting_for_user" if valid else "blocked", "step3_integrity_check", "final_report_review" if valid else "integrity_failed", artifacts, validations, phase_results, "请审核 FinalReport；回复通过完成，或提出具体修订意见。")

    def _sections_from_markdown(self, markdown: str, draft_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks = re.split(r"^## (.+)$", markdown, flags=re.M)
        content_by_heading = {chunks[index].strip(): chunks[index + 1].strip() for index in range(1, len(chunks) - 1, 2)}
        sections = []
        for draft in draft_sections:
            content = content_by_heading.get(draft.get("heading"), "")
            row = deepcopy(draft)
            row["content"] = content
            row["actual_word_count"] = len(content.replace(" ", ""))
            row["budget_variance"] = row["actual_word_count"] - int(row.get("word_budget", 0))
            sections.append(row)
        return sections

    def continue_from_source_fragments(self, state: Dict[str, Any], user_decision: str = "source fragments ready") -> Dict[str, Any]:
        """Continue a workflow using already-executed real SourceListFragment artifacts."""
        artifacts = deepcopy(state.get("artifacts", {}))
        validations = deepcopy(state.get("validations", []))
        phase_results = deepcopy(state.get("phase_results", []))

        if "SearchPlan" not in artifacts:
            raise ValueError("SearchPlan artifact is required before continuing from source fragments")
        if "SourceListFragment" not in artifacts:
            raise ValueError("SourceListFragment artifact is required before continuing from source fragments")

        raw_source_list, merger_log = self.merge_source_fragments(artifacts["SourceListFragment"])
        artifacts["RawSourceList"] = raw_source_list
        artifacts["MergerLog"] = merger_log
        validations.extend(self._validate_many({"RawSourceList": raw_source_list, "MergerLog": merger_log}))
        phase_results.append(self._phase_result("step1_source_merge", ["RawSourceList", "MergerLog"]))

        source_qa_notes, conflict_register, gap_list, clean_source_list = self._normalize_source_qa_result(
            self.source_qa(raw_source_list["sources"], artifacts.get("IntentBrief", {}).get("research_object", ""))
        )
        artifacts["SourceQANotes"] = source_qa_notes
        artifacts["ConflictRegister"] = conflict_register
        artifacts["GapList"] = gap_list
        artifacts["CleanSourceList"] = clean_source_list
        validations.extend(
            self._validate_many(
                {
                    "SourceQANotes": source_qa_notes,
                    "ConflictRegister": conflict_register,
                    "GapList": gap_list,
                    "CleanSourceList": clean_source_list,
                }
            )
        )
        phase_results.append(
            self._phase_result("step1_source_qa", ["SourceQANotes", "ConflictRegister", "GapList", "CleanSourceList"])
        )

        if self._source_qa_requires_user(source_qa_notes):
            return self._workflow_state(
                status="waiting_for_user",
                current_phase="step1_source_qa",
                pending_gate="source_qa_conflict_resolution",
                artifacts=artifacts,
                validations=validations,
                phase_results=phase_results,
                next_action="Source QA 发现真实来源冲突或缺口，请选择口径或要求补充来源。",
                user_decision=user_decision,
            )

        supplemental_source_list, refetch_notes = self._build_formal_gap_fill(conflict_register, gap_list)
        artifacts["SupplementalSourceList"] = supplemental_source_list
        artifacts["RefetchNotes"] = refetch_notes
        validations.extend(
            self._validate_many({"SupplementalSourceList": supplemental_source_list, "RefetchNotes": refetch_notes})
        )
        phase_results.append(
            self._phase_result("step1_gap_fill_or_pause", ["SupplementalSourceList", "RefetchNotes"])
        )

        return self._run_analysis_to_final(
            artifacts=artifacts,
            validations=validations,
            phase_results=phase_results,
            user_decision=user_decision,
        )

    def _source_qa_requires_user(self, source_qa_notes: Dict[str, Any]) -> bool:
        return bool(
            source_qa_notes.get("number_conflicts")
            or source_qa_notes.get("missing_evidence")
            or source_qa_notes.get("requires_user_resolution")
        )

    def _normalize_source_qa_result(self, qa_result):
        if len(qa_result) == 4:
            return qa_result
        if len(qa_result) == 2:
            source_qa_notes, clean_source_list = qa_result
            return (
                source_qa_notes,
                {
                    "conflicts": source_qa_notes.get("number_conflicts", []),
                    "requires_user_decision": bool(source_qa_notes.get("number_conflicts")),
                    "recommended_resolution": "legacy QA result; user should resolve listed conflicts",
                },
                {
                    "gaps": source_qa_notes.get("missing_evidence", []),
                    "requires_refetch": bool(source_qa_notes.get("missing_evidence")),
                    "blocking_gap_count": len(source_qa_notes.get("missing_evidence", [])),
                },
                clean_source_list,
            )
        raise ValueError("Source QA result must contain either 2 or 4 artifacts")

    def _is_confirmation(self, user_decision: str) -> bool:
        return user_decision in {"确认", "同意", "可以", "继续", "ok", "OK", "yes", "Yes", "YES"}

    def _is_final_approval(self, user_decision: str) -> bool:
        return user_decision in {"通过", "确认", "同意", "可以", "ok", "OK", "yes", "Yes", "YES"}

    def _timestamp(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _phase_result(self, phase_id: str, output_artifacts: List[str]) -> Dict[str, Any]:
        phase = self._phase_by_id(phase_id)
        return {
            "id": phase_id,
            "nodes": deepcopy(phase["nodes"]),
            "gate": phase["gate"],
            "output_artifacts": output_artifacts,
        }

    def _phase_by_id(self, phase_id: str) -> Dict[str, Any]:
        for phase in self.orchestration_plan:
            if phase["id"] == phase_id:
                return phase
        raise KeyError(f"Unknown phase: {phase_id}")

    def _node_by_id(self, node_id: str) -> Dict[str, Any]:
        for node in self.node_contracts:
            if node["id"] == node_id:
                return node
        raise KeyError(f"Unknown node: {node_id}")

    def _build_formal_step0(self, user_query: str):
        return self._build_step0_artifacts(user_query)

    def _build_dry_step0(self, user_query: str):
        return self._build_step0_artifacts(user_query)

    def _build_step0_artifacts(self, user_query: str):
        from intent_classifier import build_step0_context, classify_intent

        step0_context = build_step0_context(user_query)
        semantic = deepcopy(step0_context["semantic_fields"])
        relation = re.search(
            r"(?:调研|研究|分析|了解)\s*([^，,。；;]+?)的.+?(?:以及|并|同时)?(?:对|给)\s*([^，,。；;]+?)的(?:竞争)?启示",
            user_query,
        )
        decision_target = ""
        if relation:
            semantic["research_object"] = relation.group(1).strip()
            decision_target = relation.group(2).strip()
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
            "decision_target": decision_target,
            "subject": semantic["research_object"],
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
                "coverage_scope": "仅用于 dry-run 的 2026-07-08 示例记录",
            }
            for source_id, title, publisher, source_type, confidence, rationale, collected_by in source_specs
        ]

    def _build_source_fragments(self, source_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        fragments = []
        by_collector: Dict[str, List[Dict[str, Any]]] = {}
        for source in source_list:
            by_collector.setdefault(source["collected_by"], []).append(source)
        collector_to_node = {
            "Official Source Hunter": "official_source_hunter",
            "Media Source Hunter": "media_source_hunter",
            "RSS/News Hunter": "rss_news_hunter",
            "UGC/Social Hunter": "ugc_social_hunter",
            "Finance Data Hunter": "finance_data_hunter",
            "Marketing Intelligence Hunter": "marketing_intelligence_hunter",
        }
        for collector, sources in by_collector.items():
            fragments.append({"node_id": collector_to_node.get(collector, collector), "sources": sources})
        return fragments

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
        conflict_register = {
            "conflicts": [],
            "requires_user_decision": False,
            "recommended_resolution": "no conflict in dry-run",
        }
        gap_list = {
            "gaps": [],
            "requires_refetch": False,
            "blocking_gap_count": 0,
        }
        clean_source_list = {
            "sources": source_list,
            "approved_source_ids": approved_source_ids,
            "excluded_source_ids": [],
            "source_quality_notes": ["dry-run: all placeholder sources are schema-valid."],
        }
        return source_qa_notes, conflict_register, gap_list, clean_source_list

    def _build_formal_gap_fill(self, conflict_register: Dict[str, Any], gap_list: Dict[str, Any]):
        return self._empty_gap_fill_artifacts(conflict_register, gap_list)

    def _build_dry_gap_fill(self, conflict_register: Dict[str, Any], gap_list: Dict[str, Any]):
        return self._empty_gap_fill_artifacts(conflict_register, gap_list)

    def _empty_gap_fill_artifacts(self, conflict_register: Dict[str, Any], gap_list: Dict[str, Any]):
        return (
            {
                "sources": [],
                "resolved_gap_ids": [],
                "resolved_conflict_ids": [],
            },
            {
                "attempted_gap_ids": [gap.get("gap_id") for gap in gap_list.get("gaps", [])],
                "attempted_conflict_ids": [
                    conflict.get("conflict_id") for conflict in conflict_register.get("conflicts", [])
                ],
                "resolved_items": [],
                "unresolved_items": [],
            },
        )

    def _build_dry_claim_graph(self, clean_source_list: Dict[str, Any]) -> Dict[str, Any]:
        source_ids = [source["source_id"] for source in clean_source_list.get("sources", [])]
        primary_ids = source_ids[:3] or ["NO_SOURCE"]
        secondary_ids = source_ids[-2:] or primary_ids
        return {
            "claims": [
                {
                    "claim_id": "CL001",
                    "dimension": "竞品变化",
                    "claim_type": "fact",
                    "text": "Source Hunter 已产出可进入 QA 和分析阶段的结构化来源清单。",
                    "source_ids": primary_ids,
                    "confidence": "high",
                    "reasoning_basis": "来源清单通过 schema 校验，并保留 source_id、URL、publisher、confidence_rationale。",
                },
                {
                    "claim_id": "CL002",
                    "dimension": "业务启示",
                    "claim_type": "judgment",
                    "text": "该 workflow 可以从真实检索结果继续进入报告生成阶段，但业务判断仍需 Citation Auditor 逐条校验。",
                    "source_ids": secondary_ids,
                    "confidence": "medium",
                    "reasoning_basis": "Source QA 批准的来源可以作为候选证据，但方法型来源不能单独证明市场事实。",
                },
            ]
        }

    def _build_dry_citation_audit(self, claim_graph: Dict[str, Any]) -> Dict[str, Any]:
        approved_claim_ids = [claim["claim_id"] for claim in claim_graph["claims"]]
        citation_audit = {
            "status": "pass",
            "issues": [],
            "required_rewrites": [],
            "approved_claim_ids": approved_claim_ids,
            "blocked_claim_ids": [],
        }
        approved_claim_graph = {
            "approved_claim_ids": approved_claim_ids,
            "claims": [{**deepcopy(claim), "audit_status": "passed"} for claim in claim_graph["claims"]],
        }

        return citation_audit, approved_claim_graph

    def _build_dry_specialist_notes(self, claim_graph: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "specialist": "dry-run-specialists",
            "notes": ["dry-run: finance and marketing specialists did not add new claims."],
            "source_ids": sorted({source_id for claim in claim_graph["claims"] for source_id in claim["source_ids"]}),
            "risk_boundaries": ["dry-run evidence cannot be used as business fact."],
        }

    def _build_dry_claim_graph_patch(self) -> Dict[str, Any]:
        return {
            "patch_id": "PATCH000",
            "target_claim_ids": [],
            "new_claims": [],
            "source_ids": [],
            "patch_reason": "dry-run: no specialist patch needed.",
        }

    def _build_dry_report_draft(
        self,
        intent_brief: Dict[str, Any],
        clean_source_list: Dict[str, Any],
        approved_claim_graph: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_count = len(clean_source_list["sources"])
        core_judgment = "多 agent workflow 已从检索结果推进到报告草稿；最终业务结论仍以引用审计通过的证据为准。"
        supporting_reasons = [claim["text"] for claim in approved_claim_graph["claims"]]
        markdown = "\n".join(
            [
                f"# {intent_brief['research_object']} workflow execution report",
                "",
                f"> {core_judgment}",
                "",
                "## 支撑理由",
                f"1. {supporting_reasons[0]}",
                f"2. {supporting_reasons[1]}",
                "",
                "## 风险",
                "方法型来源不能单独证明市场事实；缺失关键官方/媒体来源时应补搜后再发布业务结论。",
            ]
        )
        return {
            "markdown": markdown,
            "report_family": "Evidence Brief",
            "core_judgment": core_judgment,
            "supporting_reasons": supporting_reasons,
            "risk_section": "方法型来源不能单独证明市场事实；缺失关键官方/媒体来源时应补搜后再发布业务结论。",
            "reference_table": [source["source_id"] for source in clean_source_list["sources"]],
            "source_count": source_count,
            "approved_outline_id": "dry_run_only",
            "reader": intent_brief.get("audience", "test"),
            "decision": intent_brief.get("user_decision", "test"),
            "sections": [{"section_id": "dry", "heading": "支撑理由", "purpose": "dry run", "purpose_addressed": True, "claim_ids": approved_claim_graph["approved_claim_ids"], "word_budget": 100, "content": "\n".join(supporting_reasons)}],
            "references": clean_source_list["sources"],
        }

    def _build_dry_final_report(
        self,
        report_draft: Dict[str, Any],
        clean_source_list: Dict[str, Any],
    ) -> Dict[str, Any]:
        final_report = {
            "markdown": report_draft["markdown"],
            "report_family": report_draft["report_family"],
            "source_count": len(clean_source_list["sources"]),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "humanizer_notes": ["dry-run: no factual edits; style pass preserved citations boundary."],
        }
        humanizer_change_log = {
            "changed_sections": [],
            "style_only": True,
            "unchanged_fact_confirmation": True,
        }
        return final_report, humanizer_change_log
