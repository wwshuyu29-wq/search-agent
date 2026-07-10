import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "lib"))


class WorkflowOrchestratorTest(unittest.TestCase):
    def test_validate_artifact_accepts_complete_source_list(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        result = orchestrator.validate_artifact(
            "SourceList",
            [
                {
                    "source_id": "OFF001",
                    "title": "官方更新",
                    "publisher": "Official",
                    "source_type": "官方",
                    "publish_date": "2026-07-08",
                    "url": "https://example.com",
                    "confidence": "high",
                    "key_facts": ["发布了新功能"],
                    "full_text_fetched": True,
                    "collected_by": "Official Source Hunter",
                    "confidence_rationale": "一手来源",
                }
            ],
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["missing_fields"], [])

    def test_validate_artifact_blocks_incomplete_claim_graph(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        result = orchestrator.validate_artifact(
            "ClaimGraph",
            {
                "claims": [
                    {
                        "claim_id": "CL001",
                        "dimension": "竞品功能变化",
                        "claim_type": "fact",
                        "text": "高德地图上线了新功能。",
                        "confidence": "high",
                    }
                ]
            },
        )

        self.assertFalse(result["valid"])
        self.assertIn("claims[0].source_ids", result["missing_fields"])
        self.assertIn("claims[0].reasoning_basis", result["missing_fields"])
        self.assertEqual(result["artifact"], "ClaimGraph")

    def test_next_phase_after_gate_returns_following_phase(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()

        next_phase = orchestrator.next_phase_after_gate("audit_card_confirmed")

        self.assertEqual(next_phase["id"], "step1_search_planning")
        self.assertEqual(next_phase["nodes"], ["search_planner"])

    def test_orchestration_contract_is_self_consistent(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()

        result = orchestrator.validate_contract_consistency()

        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])
        self.assertGreaterEqual(result["checked_nodes"], 15)
        self.assertIn("SourceList", result["checked_artifacts"])

    def test_dry_run_workflow_executes_all_phases_and_produces_final_report(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        result = orchestrator.run_dry_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "complete")
        self.assertIn("FinalReport", result["artifacts"])
        self.assertIn("ReportDraft", result["artifacts"])
        self.assertEqual(
            [phase["id"] for phase in result["phase_results"]],
            [
                "step0_intent_and_audit",
                "step1_search_planning",
                "step1_parallel_source_hunting",
                "step1_source_merge",
                "step1_source_qa",
                "step1_gap_fill_or_pause",
                "step2_analysis_and_specialists",
                "step2_citation_audit",
                "step3_report_draft",
                "step3_humanizer_final",
                "step3_integrity_check",
            ],
        )
        for validation in result["validations"]:
            self.assertTrue(validation["valid"], validation)

        final_report = result["artifacts"]["FinalReport"]
        self.assertIn("markdown", final_report)
        self.assertIn("source_count", final_report)
        self.assertGreaterEqual(final_report["source_count"], 3)

    def test_source_list_merger_dedupes_urls_and_records_merger_log(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        fragments = [
            {
                "node_id": "official_source_hunter",
                "sources": [
                    {
                        "source_id": "OFF001",
                        "title": "官方更新",
                        "publisher": "高德地图官方",
                        "source_type": "官方",
                        "publish_date": "2026-07-08",
                        "url": "https://example.com/news?a=1&utm_source=x",
                        "canonical_url": "https://example.com/news?a=1",
                        "confidence": "high",
                        "key_facts": ["发布新功能"],
                        "full_text_fetched": True,
                        "collected_by": "Official Source Hunter",
                        "confidence_rationale": "官方来源",
                    }
                ],
            },
            {
                "node_id": "media_source_hunter",
                "sources": [
                    {
                        "source_id": "MED001",
                        "title": "媒体转载",
                        "publisher": "媒体",
                        "source_type": "新闻媒体",
                        "publish_date": "2026-07-08",
                        "url": "https://example.com/news?a=1",
                        "canonical_url": "https://example.com/news?a=1",
                        "confidence": "medium",
                        "key_facts": ["转载官方新功能"],
                        "full_text_fetched": True,
                        "collected_by": "Media Source Hunter",
                        "confidence_rationale": "媒体转载",
                    }
                ],
            },
        ]

        raw_source_list, merger_log = orchestrator.merge_source_fragments(fragments)

        self.assertEqual(len(raw_source_list["sources"]), 1)
        self.assertEqual(raw_source_list["sources"][0]["source_id"], "OFF001")
        self.assertEqual(raw_source_list["sources"][0]["canonical_url"], "https://example.com/news?a=1")
        self.assertEqual(merger_log["input_count"], 2)
        self.assertEqual(merger_log["output_count"], 1)
        self.assertEqual(merger_log["deduped_count"], 1)
        self.assertEqual(merger_log["merged_sources"][0]["kept_source_id"], "OFF001")
        self.assertIn("MED001", merger_log["merged_sources"][0]["merged_source_ids"])

    def test_integrity_diff_detects_fact_changes_after_humanizer(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        report_draft = {
            "markdown": "收入为 100 亿（来源：OFF001）。置信度：高。",
            "report_family": "Evidence Brief",
            "core_judgment": "收入为 100 亿",
            "supporting_reasons": ["收入为 100 亿（来源：OFF001）"],
            "risk_section": "风险边界：样本有限。",
            "reference_table": ["OFF001"],
        }
        final_report = {
            "markdown": "收入为 120 亿（来源：OFF001）。置信度：高。",
            "report_family": "Evidence Brief",
            "source_count": 1,
            "generated_at": "2026-07-10 10:00:00",
            "humanizer_notes": [],
        }

        integrity = orchestrator.build_integrity_diff(report_draft, final_report)

        self.assertEqual(integrity["status"], "failed")
        self.assertIn("100", integrity["changed_numbers"][0]["before"])
        self.assertIn("120", integrity["changed_numbers"][0]["after"])
        self.assertEqual(integrity["changed_source_ids"], [])

    def test_gate_driven_workflow_stops_after_audit_card_until_user_confirms(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )

        self.assertEqual(state["status"], "waiting_for_user")
        self.assertEqual(state["pending_gate"], "audit_card_confirmed")
        self.assertEqual(state["current_phase"], "step0_intent_and_audit")
        self.assertIn("AuditCard", state["artifacts"])
        self.assertNotIn("SearchPlan", state["artifacts"])
        self.assertIn("回复确认", state["next_action"])

    def test_gate_driven_workflow_resumes_after_confirmation_and_waits_for_final_review(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )

        resumed = orchestrator.resume_gate_workflow(state, "确认")

        self.assertEqual(resumed["status"], "waiting_for_user")
        self.assertEqual(resumed["pending_gate"], "final_report_review")
        self.assertEqual(resumed["current_phase"], "step3_humanizer_final")
        self.assertIn("FinalReport", resumed["artifacts"])
        self.assertIn("通过", resumed["next_action"])

    def test_gate_driven_workflow_records_revision_request_instead_of_advancing(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )

        revised = orchestrator.resume_gate_workflow(state, "改成只看车道级导航")

        self.assertEqual(revised["status"], "revision_requested")
        self.assertEqual(revised["pending_gate"], "audit_card_confirmed")
        self.assertNotIn("SearchPlan", revised["artifacts"])
        self.assertEqual(revised["user_decision"], "改成只看车道级导航")

    def test_gate_driven_workflow_can_mark_final_report_complete(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )
        waiting_final = orchestrator.resume_gate_workflow(state, "确认")

        completed = orchestrator.resume_gate_workflow(waiting_final, "通过")

        self.assertEqual(completed["status"], "complete")
        self.assertEqual(completed["pending_gate"], None)
        self.assertIn("FinalReport", completed["artifacts"])

    def test_gate_driven_workflow_stops_when_source_qa_finds_conflicts(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )
        source_list = orchestrator._build_dry_source_list()
        conflict_notes = {
            "deduped_count": len(source_list),
            "removed_duplicates": [],
            "stale_sources": [],
            "paywalled_summaries": [],
            "number_conflicts": [
                {
                    "metric": "MAU",
                    "values": ["4.0亿", "5.0亿"],
                    "source_ids": ["MED001", "RSS001"],
                    "user_decision_needed": "请选择采用官方口径还是媒体估算口径。",
                }
            ],
            "missing_evidence": [],
            "approved_source_ids": [source["source_id"] for source in source_list],
        }
        clean_source_list = {
            "sources": source_list,
            "approved_source_ids": [source["source_id"] for source in source_list],
            "excluded_source_ids": [],
            "source_quality_notes": ["存在数字冲突，暂停等待用户选口径。"],
        }

        with patch.object(orchestrator, "_build_dry_source_qa", return_value=(conflict_notes, clean_source_list)):
            resumed = orchestrator.resume_gate_workflow(state, "确认")

        self.assertEqual(resumed["status"], "waiting_for_user")
        self.assertEqual(resumed["pending_gate"], "source_qa_conflict_resolution")
        self.assertEqual(resumed["current_phase"], "step1_source_qa")
        self.assertIn("SourceQANotes", resumed["artifacts"])
        self.assertNotIn("ClaimGraph", resumed["artifacts"])
        self.assertIn("数字冲突", resumed["next_action"])

    def test_source_qa_conflict_resolution_resumes_analysis_after_user_choice(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )
        source_list = orchestrator._build_dry_source_list()
        conflict_notes = {
            "deduped_count": len(source_list),
            "removed_duplicates": [],
            "stale_sources": [],
            "paywalled_summaries": [],
            "number_conflicts": [{"metric": "MAU", "source_ids": ["MED001", "RSS001"]}],
            "missing_evidence": [],
            "approved_source_ids": [source["source_id"] for source in source_list],
        }
        clean_source_list = {
            "sources": source_list,
            "approved_source_ids": [source["source_id"] for source in source_list],
            "excluded_source_ids": [],
            "source_quality_notes": ["存在数字冲突，暂停等待用户选口径。"],
        }

        with patch.object(orchestrator, "_build_dry_source_qa", return_value=(conflict_notes, clean_source_list)):
            waiting_conflict = orchestrator.resume_gate_workflow(state, "确认")

        resumed = orchestrator.resume_gate_workflow(waiting_conflict, "采用官方口径")

        self.assertEqual(resumed["pending_gate"], "final_report_review")
        self.assertIn("ClaimGraph", resumed["artifacts"])
        self.assertIn("FinalReport", resumed["artifacts"])
        self.assertIn("采用官方口径", resumed["artifacts"]["SourceQANotes"]["user_resolution"])

    def test_build_node_packets_returns_constrained_subagent_prompts_for_a_phase(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )
        search_plan = orchestrator._build_dry_search_plan(state["artifacts"]["AuditCard"])
        packets = orchestrator.build_node_packets(
            "step1_parallel_source_hunting",
            {"SearchPlan": search_plan},
        )

        self.assertEqual(len(packets), 6)
        self.assertEqual(packets[0]["phase_id"], "step1_parallel_source_hunting")
        self.assertTrue(all(packet["parallel"] for packet in packets))
        self.assertIn("official_source_hunter", [packet["node_id"] for packet in packets])
        self.assertIn("SearchPlan", packets[0]["input_payload"])
        self.assertIn("## Hard Constraints", packets[0]["prompt"])
        self.assertIn("output_artifact", packets[0])
        self.assertIn("allowed_tools_or_skills", packets[0])


if __name__ == "__main__":
    unittest.main()
