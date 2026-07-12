import unittest
from pathlib import Path
from lib.specialist_executor import SpecialistRequest, execute_specialist
from lib.specialist_router import route_specialists

ROOT=Path(__file__).resolve().parents[1]

class SpecialistExecutorTest(unittest.TestCase):
 def test_mixed_routing_is_deterministic(self):
  ids=[x['id'] for x in route_specialists('pricing and valuation dcf', 'finance_specialist', root=ROOT, limit=4)]
  self.assertIn('pricing',ids); self.assertIn('company-valuation',ids)
  self.assertEqual(ids,[x['id'] for x in route_specialists('pricing and valuation dcf','finance_specialist',root=ROOT,limit=4)])
 def test_request_validation(self):
  with self.assertRaises(ValueError): SpecialistRequest('', '', '', [], [], [], '')
 def test_missing_dependency_setup_required(self):
  req=SpecialistRequest('funda-data','x','decide',[],[],[],'finance_data_hunter')
  self.assertEqual(execute_specialist(req,root=ROOT,env={}).status,'setup_required')
 def test_rejects_direct_report_output(self):
  req=SpecialistRequest('pricing','x','decide',[],[],[],'marketing_specialist')
  with self.assertRaises(ValueError): execute_specialist(req,root=ROOT,adapters={'method_prompt':lambda r,e:{'status':'completed','ReportDraft':'bad'}})
 def test_marketing_method_cannot_claim_without_sources(self):
  req=SpecialistRequest('pricing','x','decide',[],[],[],'marketing_specialist')
  with self.assertRaises(ValueError): execute_specialist(req,root=ROOT,adapters={'method_prompt':lambda r,e:{'status':'completed','claim_graph_patch':[{'claim':'fact'}]}})

if __name__=='__main__': unittest.main()
