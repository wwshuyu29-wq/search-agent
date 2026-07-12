"""Typed execution boundary for internal specialists."""
import importlib.util
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
from .specialist_registry import SpecialistRegistry
from .specialist_router import is_specialist_allowed_at_node

STATUSES={"completed","partial","setup_required","blocked"}
FORBIDDEN={"ReportDraft","FinalReport","report_draft","final_report"}

@dataclass
class SpecialistRequest:
 specialist_id:str; topic:str; decision:str; frameworks:List[Any]; clean_sources:List[Dict[str,Any]]; approved_claims:List[Dict[str,Any]]; node_id:str
 def __post_init__(self):
  if not all((self.specialist_id,self.topic,self.decision,self.node_id)): raise ValueError("required SpecialistRequest field is empty")

@dataclass
class SpecialistResult:
 specialist_id:str; status:str; notes:List[Any]=field(default_factory=list); claim_graph_patch:List[Any]=field(default_factory=list); evidence_gaps:List[Any]=field(default_factory=list); search_plan_patch:List[Any]=field(default_factory=list); method_references:List[Any]=field(default_factory=list)


def _method_adapter(request,entry):
 return {"status":"completed","notes":[{"specialist_id":request.specialist_id,"prompt_path":entry["prompt_path"]}],"method_references":[entry["prompt_path"]]}

def _dependency_ready(dep,env):
 if dep.endswith("_API_KEY"): return bool(env.get(dep))
 return importlib.util.find_spec(dep) is not None

def execute_specialist(request,adapters=None,root=None,env=None):
 if not isinstance(request,SpecialistRequest): raise ValueError("request must be SpecialistRequest")
 registry=SpecialistRegistry(Path(root or Path(__file__).resolve().parents[1])); entry=registry.get_specialist(request.specialist_id); env=dict(os.environ if env is None else env)
 if not is_specialist_allowed_at_node(entry,request.node_id): raise ValueError(f"specialist {request.specialist_id} is not allowed at node {request.node_id}")
 missing=[d for d in entry["dependencies"] if not _dependency_ready(d,env)]
 if missing: return SpecialistResult(request.specialist_id,"setup_required",evidence_gaps=[{"missing_dependencies":missing}])
 adapter_map={"method_prompt":_method_adapter,"yfinance":_method_adapter,"funda":_method_adapter}; adapter_map.update(adapters or {})
 if entry["adapter"] not in adapter_map: return SpecialistResult(request.specialist_id,"setup_required",evidence_gaps=[{"missing_adapter":entry["adapter"]}])
 payload=adapter_map[entry["adapter"]](request,entry)
 if FORBIDDEN.intersection(payload): raise ValueError("specialists cannot emit report artifacts")
 status=payload.get("status","completed")
 if status not in STATUSES: raise ValueError("invalid specialist status")
 patches=payload.get("claim_graph_patch",[])
 allowed_source_ids={item.get("source_id") or item.get("id") for item in request.clean_sources+request.approved_claims}
 allowed_source_ids.discard(None)
 for patch in patches:
  source_ids=patch.get("source_ids")
  if not isinstance(source_ids,list) or not source_ids: raise ValueError("claims require source_ids and Citation Audit")
  if not set(source_ids).issubset(allowed_source_ids): raise ValueError("claim source_ids must reference approved request evidence")
  if entry["evidence_role"]=="structured_data":
   required={"provider","retrieved_at","period","currency","metric_definition","source_url","source_ids"}
   missing=[field for field in sorted(required) if patch.get(field) in (None,"")]
   if missing: raise ValueError(f"structured_data claim missing provenance: {missing}")
 return SpecialistResult(request.specialist_id,status,payload.get("notes",[]),patches,payload.get("evidence_gaps",[]),payload.get("search_plan_patch",[]),payload.get("method_references",[]))
