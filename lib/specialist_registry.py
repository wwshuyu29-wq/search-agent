"""Validated access to curated internal specialist resources."""
import json
from copy import deepcopy
from pathlib import Path


class CatalogError(ValueError):
    """Raised when the internal specialist catalog violates its contract."""


class SpecialistRegistry:
    REQUIRED = {"id", "domain", "nodes", "trigger_terms", "evidence_role", "adapter", "prompt_path", "dependencies", "upstream_path"}
    ROLES = {"method_reference", "structured_data"}
    DOMAINS = {"marketing", "finance"}

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        path = self.root / "specialists" / "catalog.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogError(f"cannot load specialist catalog: {exc}") from exc
        entries = payload.get("specialists")
        if not isinstance(entries, list):
            raise CatalogError("catalog specialists must be a list")
        self._entries = {}
        for entry in entries:
            self._validate(entry)
            if entry["id"] in self._entries:
                raise CatalogError(f"duplicate specialist id: {entry['id']}")
            self._entries[entry["id"]] = entry

    def _validate(self, entry):
        if not isinstance(entry, dict) or self.REQUIRED - set(entry):
            missing = self.REQUIRED - set(entry or {})
            raise CatalogError(f"malformed specialist entry; missing {sorted(missing)}")
        if entry["domain"] not in self.DOMAINS or entry["evidence_role"] not in self.ROLES:
            raise CatalogError(f"invalid domain or evidence role for {entry['id']}")
        for field in ("nodes", "trigger_terms", "dependencies"):
            if not isinstance(entry[field], list):
                raise CatalogError(f"{entry['id']}.{field} must be a list")
        upstream = (self.root / entry["upstream_path"]).resolve()
        if self.root not in upstream.parents or not upstream.is_file():
            raise CatalogError(f"invalid upstream path for {entry['id']}: {entry['upstream_path']}")

    def list_specialists(self, domain=None):
        if domain is not None and domain not in self.DOMAINS:
            return []
        return [deepcopy(value) for value in self._entries.values() if domain is None or value["domain"] == domain]

    def get_specialist(self, specialist_id):
        if specialist_id not in self._entries:
            raise KeyError(f"unknown specialist: {specialist_id}")
        return deepcopy(self._entries[specialist_id])

    def resolve_prompt(self, specialist_id):
        entry = self.get_specialist(specialist_id)
        path = (self.root / entry["prompt_path"]).resolve()
        specialists_root = (self.root / "specialists").resolve()
        if specialists_root not in path.parents or not path.is_file():
            raise CatalogError(f"prompt missing or outside specialists/: {entry['prompt_path']}")
        return path
