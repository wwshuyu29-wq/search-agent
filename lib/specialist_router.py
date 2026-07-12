"""Deterministic routing for curated internal specialists."""
from pathlib import Path
from .specialist_registry import SpecialistRegistry


def route_specialists(query, node_id, domain=None, limit=3, root=None):
    registry = SpecialistRegistry(Path(root or Path(__file__).resolve().parents[1]))
    query_l = (query or "").lower()
    ranked = []
    for item in registry.list_specialists(domain):
        if node_id not in item["nodes"]:
            # Domain hunters and mixed specialist nodes route through the same catalog.
            compatible = (
                node_id in {"finance_specialist", "marketing_specialist"}
                or (node_id == "marketing_intelligence_hunter" and item["domain"] == "marketing")
                or (node_id == "finance_data_hunter" and item["domain"] == "finance")
            )
            if not compatible:
                continue
        score = sum(1 for term in item["trigger_terms"] if str(term).lower() in query_l)
        if score:
            ranked.append((score, item["id"], item))
    if domain == "marketing" and node_id == "marketing_intelligence_hunter":
        existing = {item["id"] for _, _, item in ranked}
        for default_id in ("marketing-plan", "marketing-ideas"):
            if default_id not in existing:
                item = registry.get_specialist(default_id)
                ranked.append((0, item["id"], item))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [item for _, _, item in ranked[:max(0, limit)]]
