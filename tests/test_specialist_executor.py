import importlib
import sys
import unittest
from pathlib import Path
from unittest import mock
from lib.specialist_executor import SpecialistRequest, execute_specialist
from lib.specialist_router import route_specialists

ROOT=Path(__file__).resolve().parents[1]

class SpecialistExecutorTest(unittest.TestCase):
 def test_specialist_router_imports_as_package_and_top_level_module(self):
  package_module=importlib.import_module('lib.specialist_router')
  sys.path.insert(0,str(ROOT/'lib'))
  try:
   sys.modules.pop('specialist_router',None)
   top_level_module=importlib.import_module('specialist_router')
  finally:
   sys.path.pop(0)
  self.assertTrue(package_module.route_specialists)
  self.assertTrue(top_level_module.route_specialists)
 def test_mixed_routing_is_deterministic(self):
  ids=[x['id'] for x in route_specialists('pricing and valuation dcf', 'finance_specialist', root=ROOT, limit=4)]
  self.assertIn('pricing',ids); self.assertIn('company-valuation',ids)
  self.assertEqual(ids,[x['id'] for x in route_specialists('pricing and valuation dcf','finance_specialist',root=ROOT,limit=4)])
 def test_request_validation(self):
  with self.assertRaises(ValueError): SpecialistRequest('', '', '', [], [], [], '')
 def test_missing_dependency_setup_required(self):
  req=SpecialistRequest('funda-data','x','decide',[],[],[],'finance_data_hunter')
  self.assertEqual(execute_specialist(req,root=ROOT,env={}).status,'setup_required')
 def test_default_method_adapter_is_setup_required_method_reference(self):
  req=SpecialistRequest('pricing','x','decide',[],[],[],'marketing_specialist')
  result=execute_specialist(req,root=ROOT)
  self.assertEqual(result.status,'setup_required')
  self.assertTrue(result.method_references)
  self.assertEqual(result.claim_graph_patch,[])
  self.assertTrue(any('method' in str(note).lower() for note in result.notes))
 def test_rejects_direct_report_output(self):
  req=SpecialistRequest('pricing','x','decide',[],[],[],'marketing_specialist')
  with self.assertRaises(ValueError): execute_specialist(req,root=ROOT,adapters={'method_prompt':lambda r,e:{'status':'completed','ReportDraft':'bad'}})
 def test_marketing_method_cannot_claim_without_sources(self):
  req=SpecialistRequest('pricing','x','decide',[],[],[],'marketing_specialist')
  with self.assertRaises(ValueError): execute_specialist(req,root=ROOT,adapters={'method_prompt':lambda r,e:{'status':'completed','claim_graph_patch':[{'claim':'fact'}]}})
 def test_executor_rejects_specialist_at_disallowed_node(self):
  req=SpecialistRequest('pricing','x','decide',[],[],[],'report_writer')
  with self.assertRaises(ValueError): execute_specialist(req,root=ROOT)
 def test_structured_data_rejects_missing_provenance(self):
  req=SpecialistRequest('yfinance-data','x','decide',[],[{'source_id':'S1'}],[],'finance_data_hunter')
  with mock.patch('lib.specialist_executor._dependency_ready',return_value=True):
   with self.assertRaises(ValueError): execute_specialist(req,root=ROOT,adapters={'yfinance':lambda r,e:{'claim_graph_patch':[{'claim':'revenue','source_ids':['S1']}]}})
 def test_structured_data_accepts_complete_provenance(self):
  req=SpecialistRequest('yfinance-data','x','decide',[],[{'source_id':'S1'}],[],'finance_data_hunter')
  patch={'claim':'revenue','provider':'yfinance','retrieved_at':'2026-07-12T00:00:00Z','period':'FY2025','currency':'USD','metric_definition':'GAAP revenue','source_url':'https://example.com','source_ids':['S1']}
  with mock.patch('lib.specialist_executor._dependency_ready',return_value=True):
   result=execute_specialist(req,root=ROOT,adapters={'yfinance':lambda r,e:{'claim_graph_patch':[patch]}})
  self.assertEqual(result.claim_graph_patch,[patch])

 def test_injected_adapter_patch_enters_result_with_source_boundary(self):
  """P1 Fix #5: injected adapter patch must produce a result with source/boundary."""
  req=SpecialistRequest('pricing','豆包','analyze',[],[{'source_id':'OFF001'}],[],'marketing_specialist')
  patch={'claim_id':'SP001','dimension':'定价','claim_type':'fact','text':'豆包采用免费增值定价','source_ids':['OFF001'],'confidence':'medium','reasoning_basis':'specialist analysis','evidence_text':'豆包采用免费增值定价','evidence_boundary':'仅覆盖定价维度','boundary_status':'provided'}
  result=execute_specialist(req,root=ROOT,adapters={'method_prompt':lambda r,e:{'status':'completed','claim_graph_patch':[patch]}})
  self.assertEqual(result.status,'completed')
  self.assertEqual(len(result.claim_graph_patch),1)
  self.assertEqual(result.claim_graph_patch[0]['source_ids'],['OFF001'])
  self.assertEqual(result.claim_graph_patch[0]['evidence_boundary'],'仅覆盖定价维度')

 def test_injected_adapter_patch_without_source_ids_rejected(self):
  """P1 Fix #5: patch without source_ids must be rejected."""
  req=SpecialistRequest('pricing','豆包','analyze',[],[{'source_id':'OFF001'}],[],'marketing_specialist')
  with self.assertRaises(ValueError):
   execute_specialist(req,root=ROOT,adapters={'method_prompt':lambda r,e:{'status':'completed','claim_graph_patch':[{'claim_id':'SP001','source_ids':[]}]}})

 def test_injected_adapter_patch_with_unapproved_source_rejected(self):
  """P1 Fix #5: patch referencing unapproved source must be rejected."""
  req=SpecialistRequest('pricing','豆包','analyze',[],[{'source_id':'OFF001'}],[],'marketing_specialist')
  with self.assertRaises(ValueError):
   execute_specialist(req,root=ROOT,adapters={'method_prompt':lambda r,e:{'status':'completed','claim_graph_patch':[{'claim_id':'SP001','source_ids':['UNKNOWN']}]}})

 def test_method_reference_adapter_produces_no_claims(self):
  """P1 Fix #5: default method adapter returns setup_required with method reference, no claims."""
  req=SpecialistRequest('pricing','豆包','analyze',[],[],[],'marketing_specialist')
  result=execute_specialist(req,root=ROOT)
  self.assertEqual(result.status,'setup_required')
  self.assertEqual(result.claim_graph_patch,[])
  self.assertTrue(result.method_references)
  self.assertTrue(any('method' in str(note).lower() for note in result.notes))

if __name__=='__main__': unittest.main()
