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
                "step3_humanizer",
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
        self.assertEqual(resumed["pending_gate"], "outline_approved_by_user")
        self.assertEqual(resumed["current_phase"], "step3_outline_approval")
        self.assertIn("OutlinePlan", resumed["artifacts"])
        self.assertNotIn("ReportDraft", resumed["artifacts"])

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

        def test_humanizer(draft):
            return {"markdown": draft["markdown"], "change_log": {"changed_sections": [], "style_only": True, "unchanged_fact_confirmation": True}}

        orchestrator = WorkflowOrchestrator(humanizer_adapter=test_humanizer)
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )
        waiting_outline = orchestrator.resume_gate_workflow(state, "确认")
        waiting_final = orchestrator.resume_gate_workflow(waiting_outline, {"selection": "A"})

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

        with patch.object(orchestrator, "source_qa", return_value=(conflict_notes, clean_source_list)):
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

        with patch.object(orchestrator, "source_qa", return_value=(conflict_notes, clean_source_list)):
            waiting_conflict = orchestrator.resume_gate_workflow(state, "确认")

        resumed = orchestrator.resume_gate_workflow(waiting_conflict, "采用官方口径")

        self.assertEqual(resumed["pending_gate"], "outline_approved_by_user")
        self.assertIn("ClaimGraph", resumed["artifacts"])
        self.assertIn("OutlinePlan", resumed["artifacts"])
        self.assertIn("采用官方口径", resumed["artifacts"]["SourceQANotes"]["user_resolution"])

    def test_continue_from_source_fragments_runs_merge_qa_and_report(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow(
            "高德地图最近三个月上了什么新功能，对百度地图市场组有什么启示"
        )
        state["artifacts"]["SearchPlan"] = orchestrator._build_dry_search_plan(state["artifacts"]["AuditCard"])
        state["artifacts"]["SourceListFragment"] = [
            {
                "node_id": "rss_news_hunter",
                "execution_status": "completed",
                "task_ids": ["RSS001"],
                "warnings": [],
                "sources": [
                    {
                        "source_id": "RSS001",
                        "title": "高德地图新功能报道",
                        "publisher": "示例媒体",
                        "source_type": "rss_news",
                        "publish_date": "2026-07-10",
                        "url": "https://example.com/amap",
                        "canonical_url": "https://example.com/amap",
                        "confidence": "medium",
                        "key_facts": ["高德地图上线新功能。"],
                        "full_text_fetched": False,
                        "collected_by": "RSS/News Hunter",
                        "confidence_rationale": "test source",
                    }
                ],
            }
        ]

        continued = orchestrator.continue_from_source_fragments(state)

        self.assertEqual(continued["pending_gate"], "outline_approved_by_user")
        self.assertEqual(continued["artifacts"]["RawSourceList"]["source_count"], 1)
        self.assertIn("CleanSourceList", continued["artifacts"])
        self.assertIn("OutlinePlan", continued["artifacts"])
        self.assertNotIn("ReportDraft", continued["artifacts"])

    def test_confirmed_audit_stops_at_outline_gate_without_writing_prose(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow("高德地图新功能对百度地图的启示")
        source = {
            "source_id": "OFF001", "title": "官方更新", "publisher": "高德",
            "source_type": "official", "publish_date": "2026-07-10",
            "url": "https://example.com/update", "canonical_url": "https://example.com/update",
            "confidence": "high", "key_facts": ["上线车道级导航"],
            "full_text_fetched": True, "collected_by": "Official Source Hunter",
            "confidence_rationale": "official primary source",
        }
        state["artifacts"]["SearchPlan"] = orchestrator.build_search_plan(state["artifacts"]["AuditCard"])
        state["artifacts"]["SourceListFragment"] = [{"node_id": "official_source_hunter", "sources": [source]}]

        waiting = orchestrator.continue_from_source_fragments(state)

        self.assertEqual(waiting["pending_gate"], "outline_approved_by_user")
        self.assertIn("OutlinePlan", waiting["artifacts"])
        self.assertEqual(len(waiting["artifacts"]["OutlinePlan"]["candidates"]), 3)
        self.assertNotIn("ApprovedOutline", waiting["artifacts"])
        self.assertNotIn("ReportDraft", waiting["artifacts"])

    def test_outline_choice_and_override_are_required_before_final_pipeline(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator(humanizer_adapter=lambda draft: {"markdown": draft["markdown"].replace("供x判断下一步行动", "供x确定下一步安排"), "change_log": {"changed_sections": ["all"], "style_only": True, "unchanged_fact_confirmation": True}})
        state = orchestrator.start_gate_workflow("测试")
        state["pending_gate"] = "outline_approved_by_user"
        state["artifacts"]["ApprovedClaimGraph"] = {
            "approved_claim_ids": ["CL001"],
            "claims": [{"claim_id": "CL001", "claim_type": "fact", "text": "事实", "source_ids": ["OFF001"], "audit_status": "passed", "evidence_boundary": "仅覆盖测试来源"}],
        }
        state["artifacts"]["CleanSourceList"] = {"sources": [{"source_id": "OFF001", "title": "来源", "url": "https://example.com"}], "approved_source_ids": ["OFF001"], "excluded_source_ids": [], "source_quality_notes": []}
        state["artifacts"]["OutlinePlan"] = __import__("workflow_contracts").build_outline_candidates(
            state["artifacts"]["IntentBrief"], ["CL001"]
        )
        override = [{"section_id": "S1", "heading": "自定义结论", "purpose": "回答决策", "required_claim_ids": ["CL001"], "word_budget": 53}]

        completed = orchestrator.resume_gate_workflow(state, {"selection": "A", "sections_override": override, "approved_by_user": True})

        self.assertTrue(completed["artifacts"]["ApprovedOutline"]["approved_by_user"])
        self.assertEqual(completed["artifacts"]["ReportDraft"]["sections"][0]["heading"], "自定义结论")
        self.assertEqual(completed["artifacts"]["OutlineComplianceReview"]["status"], "passed")
        self.assertEqual(completed["artifacts"]["IntegrityDiff"]["status"], "passed")
        self.assertEqual(completed["pending_gate"], "final_report_review")

    def test_citation_audit_blocks_missing_and_method_only_sources(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        clean = {"sources": [
            {"source_id": "MKT001", "method_source": True},
            {"source_id": "OFF001", "method_source": False},
        ], "approved_source_ids": ["MKT001", "OFF001"]}
        graph = {"claims": [
            {"claim_id": "CL001", "claim_type": "fact", "text": "市场事实", "source_ids": ["MKT001"], "confidence": "high", "reasoning_basis": "method"},
            {"claim_id": "CL002", "claim_type": "fact", "text": "缺失", "source_ids": ["NOPE"], "confidence": "high", "reasoning_basis": "missing"},
        ]}

        audit, approved = orchestrator.audit_claim_graph(graph, clean)

        self.assertEqual(audit["status"], "failed")
        self.assertEqual(set(audit["blocked_claim_ids"]), {"CL001", "CL002"})
        self.assertEqual(approved["claims"], [])

    def test_real_source_continuation_never_calls_dry_builders(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow("测试")
        state["artifacts"]["SearchPlan"] = orchestrator.build_search_plan(state["artifacts"]["AuditCard"])
        state["artifacts"]["SourceListFragment"] = [{"node_id": "official_source_hunter", "sources": [{
            "source_id": "OFF001", "title": "来源", "publisher": "官方", "source_type": "official",
            "publish_date": "2026-07-10", "url": "https://example.com", "canonical_url": "https://example.com",
            "confidence": "high", "key_facts": ["真实事实"], "full_text_fetched": True,
            "collected_by": "Official Source Hunter", "confidence_rationale": "primary",
        }]}]
        with patch.object(orchestrator, "_build_dry_source_qa", side_effect=AssertionError("dry called")), \
             patch.object(orchestrator, "_build_dry_claim_graph", side_effect=AssertionError("dry called")):
            result = orchestrator.continue_from_source_fragments(state)
        self.assertEqual(result["pending_gate"], "outline_approved_by_user")

    def test_semantic_validation_rejects_unapproved_outline_and_failed_reviews(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        invalid_outline = {"selected_outline_id": "a", "approved_by_user": False, "report_family": "x", "title": "x", "target_reader": "x", "writing_logic": "x", "sections": []}
        self.assertFalse(orchestrator.validate_artifact("ApprovedOutline", invalid_outline)["valid"])
        self.assertFalse(orchestrator.validate_artifact("OutlineComplianceReview", {"status": "failed", "missing_sections": [], "unexpected_sections": [], "order_matches": True, "purpose_gaps": [], "evidence_gaps": []})["valid"])

    def test_outline_gate_rejects_implicit_or_ambiguous_approval(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow("测试")
        state["pending_gate"] = "outline_approved_by_user"
        state["artifacts"]["OutlinePlan"] = __import__("workflow_contracts").build_outline_candidates(
            state["artifacts"]["IntentBrief"], ["CL001"]
        )
        for decision in ["", "不同意", "请修改第二节", "随便选一个"]:
            result = orchestrator.resume_gate_workflow(state, decision)
            self.assertEqual(result["status"], "waiting_for_user")
            self.assertNotIn("ApprovedOutline", result["artifacts"])

    def test_citation_audit_blocks_existing_source_that_does_not_support_fact(self):
        from workflow_orchestrator import WorkflowOrchestrator

        graph = {"claims": [{"claim_id": "CL001", "claim_type": "fact", "text": "收入增长20%", "source_ids": ["OFF001"], "confidence": "high", "reasoning_basis": "analysis"}]}
        clean = {"sources": [{"source_id": "OFF001", "key_facts": ["收入下降5%"], "method_source": False}], "approved_source_ids": ["OFF001"]}
        audit, approved = WorkflowOrchestrator().audit_claim_graph(graph, clean)
        self.assertEqual(audit["status"], "failed")
        self.assertEqual(audit["blocked_claim_ids"], ["CL001"])
        self.assertEqual(approved["claims"], [])

    def test_integrity_diff_blocks_confidence_risk_new_facts_and_bad_change_log(self):
        from workflow_orchestrator import WorkflowOrchestrator

        draft = {"markdown": "置信度：低。风险：样本有限。", "sections": [{"heading": "结论", "claim_ids": ["CL001"], "content": "置信度：低。风险：样本有限。"}]}
        final = {"markdown": "置信度：高。没有风险。市场份额达到30%。", "sections": [{"heading": "结论", "claim_ids": ["CL001"], "content": "置信度：高。没有风险。市场份额达到30%。"}]}
        result = WorkflowOrchestrator().build_integrity_diff(draft, final, {"style_only": False, "unchanged_fact_confirmation": False})
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["changed_confidence"])
        self.assertTrue(result["risk_boundary_changes"])
        self.assertTrue(result["new_factual_sentences"])
        self.assertTrue(result["humanizer_log_violations"])

    def test_outline_compliance_blocks_under_budget_missing_purpose_and_required_claim(self):
        from workflow_contracts import review_outline_compliance

        outline = {"sections": [{"heading": "结论", "purpose": "回答增长策略", "required_claim_ids": ["CL001", "CL002"], "word_budget": 100}]}
        draft = {"sections": [{"heading": "结论", "purpose_addressed": True, "claim_ids": ["CL001"], "content": "事实陈述", "actual_word_count": 4, "word_budget": 100, "budget_variance": -96}]}
        review = review_outline_compliance(outline, draft)
        self.assertEqual(review["status"], "blocked")
        self.assertIn("结论", review["purpose_gaps"])
        self.assertIn("CL002", review["missing_required_claim_ids"])
        self.assertIn("结论", review["needs_expansion"])

    def test_citation_audit_enforces_each_claim_type_and_excludes_unsupported_assumption(self):
        from workflow_orchestrator import WorkflowOrchestrator

        source = {
            "source_id": "OFF001",
            "method_source": False,
            "key_facts": ["收入为120亿元，成本为100亿元，因此利润为20亿元。用户需求增长支持优先投入。"],
            "support_excerpt": "收入为120亿元，成本为100亿元，因此利润为20亿元。用户需求增长支持优先投入。",
        }
        clean = {"sources": [source], "approved_source_ids": ["OFF001"]}
        claims = [
            {"claim_id": "F1", "claim_type": "fact", "text": "收入为120亿元", "source_ids": ["OFF001"], "evidence_text": "收入为120亿元"},
            {"claim_id": "C1", "claim_type": "calculation", "text": "利润为20亿元", "source_ids": ["OFF001"], "evidence_text": "收入为120亿元，成本为100亿元，因此利润为20亿元", "calculation_inputs": {"revenue": 120, "cost": 100}, "formula": "revenue - cost"},
            {"claim_id": "J1", "claim_type": "judgment", "text": "应优先投入", "source_ids": ["OFF001"], "reasoning_basis": "用户需求增长支持优先投入"},
            {"claim_id": "A1", "claim_type": "assumption", "text": "用户需求增长将延续", "source_ids": ["OFF001"], "reasoning_basis": "由用户需求增长外推增长延续", "premise_claim_ids": ["J1"], "inference_rule": "趋势外推", "evidence_boundary": "仅在用户需求继续增长时成立", "confidence": "low"},
            {"claim_id": "A2", "claim_type": "assumption", "text": "无来源假设", "source_ids": [], "evidence_boundary": "仅为情景，不进入批准图"},
        ]

        audit, approved = WorkflowOrchestrator().audit_claim_graph({"claims": claims}, clean)

        self.assertEqual(audit["approved_claim_ids"], ["F1", "C1", "J1"])
        self.assertEqual(audit["blocked_claim_ids"], ["A1", "A2"])
        self.assertEqual([claim["claim_id"] for claim in approved["claims"]], ["F1", "C1", "J1"])

    def test_citation_audit_blocks_invalid_metadata_unknown_type_and_opposite_content(self):
        from workflow_orchestrator import WorkflowOrchestrator

        clean = {"sources": [{"source_id": "OFF001", "method_source": False, "key_facts": ["收入下降5%，不建议投入"]}], "approved_source_ids": ["OFF001"]}
        claims = [
            {"claim_id": "F1", "claim_type": "fact", "text": "收入增长20%", "source_ids": ["OFF001"], "evidence_text": "收入增长20%"},
            {"claim_id": "C1", "claim_type": "calculation", "text": "利润20", "source_ids": ["OFF001"], "evidence_text": "利润20"},
            {"claim_id": "J1", "claim_type": "judgment", "text": "建议投入", "source_ids": ["OFF001"], "reasoning_basis": "建议投入"},
            {"claim_id": "A1", "claim_type": "assumption", "text": "需求延续", "source_ids": ["OFF001"]},
            {"claim_id": "X1", "claim_type": "forecast", "text": "增长", "source_ids": ["OFF001"]},
        ]

        audit, approved = WorkflowOrchestrator().audit_claim_graph({"claims": claims}, clean)

        self.assertEqual(set(audit["blocked_claim_ids"]), {"F1", "C1", "J1", "A1", "X1"})
        self.assertEqual(approved["claims"], [])

    def test_unrelated_or_pending_assumption_is_blocked(self):
        from workflow_orchestrator import WorkflowOrchestrator

        clean = {"sources": [{"source_id": "S1", "key_facts": ["收入增长支持扩产"]}], "approved_source_ids": ["S1"]}
        claims = {"claims": [
            {"claim_id": "A1", "claim_type": "assumption", "text": "天气持续晴朗", "source_ids": ["S1"], "reasoning_basis": "天气持续晴朗", "evidence_boundary": "待验证", "verification_status": "pending"},
            {"claim_id": "A2", "claim_type": "assumption", "text": "收入增长将持续", "source_ids": ["S1"], "reasoning_basis": "收入增长支持趋势外推", "premise_claim_ids": ["F1"], "inference_rule": "趋势外推", "evidence_boundary": "仅限当前趋势", "confidence": "low"},
        ]}
        audit, approved = WorkflowOrchestrator().audit_claim_graph(claims, clean)
        self.assertEqual(audit["blocked_claim_ids"], ["A1", "A2"])
        self.assertEqual(approved["approved_claim_ids"], [])

    def test_formal_workflow_requires_humanizer_before_final_report(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow("测试")
        waiting_outline = orchestrator.resume_gate_workflow(state, "确认")
        waiting_humanizer = orchestrator.resume_gate_workflow(waiting_outline, {"selection": "A"})
        self.assertEqual(waiting_humanizer["pending_gate"], "humanizer_required")
        self.assertNotIn("FinalReport", waiting_humanizer["artifacts"])

    def test_submitted_humanization_runs_integrity_and_blocks_tampering(self):
        from workflow_orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        state = orchestrator.start_gate_workflow("测试")
        state = orchestrator.resume_gate_workflow(state, "确认")
        state = orchestrator.resume_gate_workflow(state, {"selection": "A"})
        draft = state["artifacts"]["ReportDraft"]["markdown"]
        passed = orchestrator.resume_gate_workflow(state, {"humanized_markdown": draft.replace("本节围绕", "本章聚焦", 1), "change_log": {"changed_sections": ["第一节"], "style_only": True, "unchanged_fact_confirmation": True}})
        self.assertEqual(passed["pending_gate"], "final_report_review")
        self.assertEqual(passed["artifacts"]["IntegrityDiff"]["status"], "passed")
        tampered = orchestrator.resume_gate_workflow(state, {"humanized_markdown": draft.replace("2026", "2099", 1), "change_log": {"changed_sections": ["第一节"], "style_only": True, "unchanged_fact_confirmation": True}})
        self.assertEqual(tampered["status"], "blocked")
        self.assertEqual(tampered["artifacts"]["IntegrityDiff"]["status"], "failed")

    def test_integrity_blocks_new_unapproved_strategic_sentence_without_keywords(self):
        from workflow_orchestrator import WorkflowOrchestrator

        draft = {"markdown": "# 报告\n\n## 结论\n\n现有渠道覆盖核心用户。\n"}
        final = {"markdown": "# 报告\n\n## 结论\n\n现有渠道覆盖核心用户。建立壁垒。\n"}

        integrity = WorkflowOrchestrator().build_integrity_diff(draft, final)

        self.assertEqual(integrity["status"], "failed")
        self.assertEqual(integrity["new_unapproved_sentences"], ["建立壁垒。"])

    def test_integrity_allows_punctuation_and_same_group_connective_edits(self):
        from workflow_orchestrator import WorkflowOrchestrator

        draft = {"markdown": "# 报告\n\n## 结论\n\n所以，现有渠道覆盖核心用户。\n"}
        final = {"markdown": "# 报告\n\n## 结论\n\n因此，现有渠道覆盖核心用户！\n"}

        integrity = WorkflowOrchestrator().build_integrity_diff(draft, final)

        self.assertEqual(integrity["status"], "passed")
        self.assertEqual(integrity["new_unapproved_sentences"], [])

    def test_integrity_blocks_adding_a_connective_to_one_side(self):
        from workflow_orchestrator import WorkflowOrchestrator

        draft = {"markdown": "# 报告\n\n## 结论\n\n现有渠道覆盖核心用户。\n"}
        final = {"markdown": "# 报告\n\n## 结论\n\n因此，现有渠道覆盖核心用户！\n"}

        integrity = WorkflowOrchestrator().build_integrity_diff(draft, final)

        self.assertEqual(integrity["status"], "failed")
        self.assertEqual(integrity["new_unapproved_sentences"], ["因此，现有渠道覆盖核心用户！"])

    def test_integrity_blocks_deleting_a_connective_from_one_side(self):
        from workflow_orchestrator import WorkflowOrchestrator

        draft = {"markdown": "# 报告\n\n## 结论\n\n同时，现有渠道覆盖核心用户。\n"}
        final = {"markdown": "# 报告\n\n## 结论\n\n现有渠道覆盖核心用户！\n"}

        integrity = WorkflowOrchestrator().build_integrity_diff(draft, final)

        self.assertEqual(integrity["status"], "failed")
        self.assertEqual(integrity["new_unapproved_sentences"], ["现有渠道覆盖核心用户！"])

    def test_integrity_blocks_cross_group_connective_replacement(self):
        from workflow_orchestrator import WorkflowOrchestrator

        draft = {"markdown": "# 报告\n\n## 结论\n\n不过，现有渠道覆盖核心用户。\n"}
        final = {"markdown": "# 报告\n\n## 结论\n\n此外，现有渠道覆盖核心用户！\n"}

        integrity = WorkflowOrchestrator().build_integrity_diff(draft, final)

        self.assertEqual(integrity["status"], "failed")
        self.assertEqual(integrity["new_unapproved_sentences"], ["此外，现有渠道覆盖核心用户！"])

    def test_integrity_blocks_added_words_within_an_existing_sentence(self):
        from workflow_orchestrator import WorkflowOrchestrator

        draft = {"markdown": "# 报告\n\n## 结论\n\n现有渠道覆盖核心用户。\n"}
        final = {"markdown": "# 报告\n\n## 结论\n\n现有渠道覆盖核心用户，并形成壁垒。\n"}

        integrity = WorkflowOrchestrator().build_integrity_diff(draft, final)

        self.assertEqual(integrity["status"], "failed")
        self.assertEqual(integrity["new_unapproved_sentences"], ["现有渠道覆盖核心用户，并形成壁垒。"])

    def test_integrity_blocks_polarity_flip_and_deleted_outline_section(self):
        from workflow_orchestrator import WorkflowOrchestrator

        draft = {
            "markdown": "# 报告\n\n## 结论\n\n判断依据：应优先投入。\n\n## 风险\n\n事实依据：样本有限。\n",
            "sections": [
                {"section_id": "S1", "heading": "结论", "claim_ids": ["J1"], "content": "判断依据：应优先投入。", "evidence_spans": ["判断依据：应优先投入。"]},
                {"section_id": "S2", "heading": "风险", "claim_ids": ["F1"], "content": "事实依据：样本有限。", "evidence_spans": ["事实依据：样本有限。"]},
            ],
        }
        outline = {"sections": [{"section_id": "S1", "heading": "结论"}, {"section_id": "S2", "heading": "风险"}]}
        orchestrator = WorkflowOrchestrator()
        flipped = {"markdown": "# 报告\n\n## 结论\n\n判断依据：不应优先投入。\n\n## 风险\n\n事实依据：样本有限。\n"}
        deleted = {"markdown": "# 报告\n\n## 结论\n\n判断依据：应优先投入。\n"}

        self.assertEqual(orchestrator.build_integrity_diff(draft, flipped, approved_outline=outline)["status"], "failed")
        self.assertEqual(orchestrator.build_integrity_diff(draft, deleted, approved_outline=outline)["status"], "failed")

    def test_assumption_requires_passed_premises_rule_and_textual_relation(self):
        from workflow_orchestrator import WorkflowOrchestrator

        clean = {"sources": [{"source_id": "S1", "key_facts": ["收入增长"]}], "approved_source_ids": ["S1"]}
        claims = {"claims": [
            {"claim_id": "F1", "claim_type": "fact", "text": "收入增长", "source_ids": ["S1"], "evidence_text": "收入增长"},
            {"claim_id": "A1", "claim_type": "assumption", "text": "收入增长将持续", "source_ids": ["S1"], "reasoning_basis": "由收入增长外推增长持续", "premise_claim_ids": ["F1"], "inference_rule": "趋势外推", "evidence_boundary": "仅为假设", "confidence": "low"},
            {"claim_id": "A2", "claim_type": "assumption", "text": "天气持续晴朗", "source_ids": ["S1"], "reasoning_basis": "由收入增长外推天气", "premise_claim_ids": ["F1"], "inference_rule": "趋势外推", "evidence_boundary": "仅为假设", "confidence": "low"},
        ]}
        audit, approved = WorkflowOrchestrator().audit_claim_graph(claims, clean)
        self.assertIn("A1", audit["approved_claim_ids"])
        self.assertIn("A2", audit["blocked_claim_ids"])
        self.assertEqual(next(c for c in approved["claims"] if c["claim_id"] == "A1")["claim_type"], "assumption")

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
        self.assertIn("skill_invocation_rules", packets[0])
        self.assertTrue(packets[0]["skill_invocation_rules"])
        self.assertEqual(packets[0]["skill_invocation_rules"][0]["node_id"], packets[0]["node_id"])


if __name__ == "__main__":
    unittest.main()
