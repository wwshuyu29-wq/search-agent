"""Deterministic routing for curated internal specialists."""
from pathlib import Path

try:
    from .specialist_registry import SpecialistRegistry
except ImportError:  # Support CLI usage with lib/ directly on sys.path.
    from specialist_registry import SpecialistRegistry


def is_specialist_allowed_at_node(entry, node_id):
    if not isinstance(entry, dict) or not node_id:
        return False
    if node_id in entry.get("nodes", []):
        return True
    domain = entry.get("domain")
    return (
        (node_id == "marketing_intelligence_hunter" and domain == "marketing")
        or (node_id == "finance_data_hunter" and domain == "finance")
        or (node_id in {"marketing_specialist", "finance_specialist"} and domain in {"marketing", "finance"})
    )


def route_specialists(query, node_id, domain=None, limit=3, root=None):
    registry = SpecialistRegistry(Path(root or Path(__file__).resolve().parents[1]))
    query_l = (query or "").lower()
    ranked = []
    for item in registry.list_specialists(domain):
        if not is_specialist_allowed_at_node(item, node_id):
            continue
        score = sum(1 for term in item["trigger_terms"] if str(term).lower() in query_l)
        if score:
            ranked.append((score, item["id"], item))
    if domain == "marketing" and node_id == "marketing_intelligence_hunter":
        existing = {item["id"] for _, _, item in ranked}
        for default_id in ("marketing-plan", "marketing-ideas"):
            if default_id not in existing:
                item = registry.get_specialist(default_id)
                if is_specialist_allowed_at_node(item, node_id):
                    ranked.append((0, item["id"], item))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [item for _, _, item in ranked[:max(0, limit)]]
