import sys
import unittest
from pathlib import Path


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
                "step1_source_qa",
                "step2_analysis_and_specialists",
                "step2_citation_audit",
                "step3_report_draft",
                "step3_humanizer_final",
            ],
        )
        for validation in result["validations"]:
            self.assertTrue(validation["valid"], validation)

        final_report = result["artifacts"]["FinalReport"]
        self.assertIn("markdown", final_report)
        self.assertIn("source_count", final_report)
        self.assertGreaterEqual(final_report["source_count"], 3)

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


if __name__ == "__main__":
    unittest.main()
