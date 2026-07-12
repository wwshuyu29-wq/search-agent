"""Deterministic routing for curated internal specialists."""
from pathlib import Path
from .specialist_registry import SpecialistRegistry


def route_specialists(query, node_id, domain=None, limit=3, root=None):
    registry = SpecialistRegistry(Path(root or Path(__file__).resolve().parents[1]))
    query_l = (query or "").lower()
    ranked = []
    for item in registry.list_specialists(domain):
        if node_id not in item["nodes"]:
            # Mixed-domain orchestration may ask from either specialist node.
            if node_id not in {"finance_specialist", "marketing_specialist"}:
                continue
        score = sum(1 for term in item["trigger_terms"] if str(term).lower() in query_l)
        if score:
            ranked.append((score, item["id"], item))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [item for _, _, item in ranked[:max(0, limit)]]
