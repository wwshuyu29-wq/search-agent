"""Validated access to curated internal specialist resources."""
import hashlib
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
        self._vendor_lock = self._load_vendor_lock()
        entries = payload.get("specialists")
        if not isinstance(entries, list):
            raise CatalogError("catalog specialists must be a list")
        self._entries = {}
        for entry in entries:
            self._validate(entry)
            if entry["id"] in self._entries:
                raise CatalogError(f"duplicate specialist id: {entry['id']}")
            self._entries[entry["id"]] = entry

    def _load_vendor_lock(self):
        path = self.root / "specialists" / "vendor.lock.json"
        try:
            lock = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CatalogError(f"cannot load vendor lock: {exc}") from exc
        if lock.get("version") != 2 or not isinstance(lock.get("vendors"), list):
            raise CatalogError("vendor lock must use version 2")
        repositories = {
            "marketing": "https://github.com/coreyhaines31/marketingskills.git",
            "finance": "https://github.com/himself65/finance-skills.git",
        }
        files = {}
        self._vendor_trees = {}
        for vendor in lock["vendors"]:
            if repositories.get(vendor.get("id")) != vendor.get("repository"):
                raise CatalogError(f"unexpected vendor repository: {vendor.get('id')}")
            if not vendor.get("tree_sha256") or not isinstance(vendor.get("files"), dict):
                raise CatalogError(f"incomplete vendor lock: {vendor.get('id')}")
            vendor_root = (self.root / vendor.get("path", "")).resolve()
            if self.root not in vendor_root.parents or not vendor_root.is_dir():
                raise CatalogError(f"invalid vendor path: {vendor.get('id')}")
            digest = hashlib.sha256()
            for item in sorted(path for path in vendor_root.rglob("*") if path.is_file()):
                digest.update(item.relative_to(vendor_root).as_posix().encode())
                digest.update(b"\0")
                digest.update(hashlib.sha256(item.read_bytes()).digest())
            if digest.hexdigest() != vendor["tree_sha256"]:
                raise CatalogError(f"vendor tree checksum mismatch: {vendor.get('id')}")
            files.update(vendor["files"])
        return files

    def _validate(self, entry):
        if not isinstance(entry, dict) or self.REQUIRED - set(entry):
            missing = self.REQUIRED - set(entry or {})
            raise CatalogError(f"malformed specialist entry; missing {sorted(missing)}")
        if entry["domain"] not in self.DOMAINS or entry["evidence_role"] not in self.ROLES:
            raise CatalogError(f"invalid domain or evidence role for {entry['id']}")
        for field in ("nodes", "trigger_terms", "dependencies"):
            if not isinstance(entry[field], list):
                raise CatalogError(f"{entry['id']}.{field} must be a list")
        upstream = self.resolve_upstream_path(entry["upstream_path"])
        if upstream is None:
            raise CatalogError(f"invalid upstream path for {entry['id']}: {entry['upstream_path']}")
        expected = self._vendor_lock.get(entry["upstream_path"])
        if expected is None:
            raise CatalogError(f"upstream path is not vendor-locked: {entry['upstream_path']}")
        actual = hashlib.sha256(upstream.read_bytes()).hexdigest()
        if actual != expected:
            raise CatalogError(f"vendor checksum mismatch: {entry['upstream_path']}")

    def resolve_upstream_path(self, relative_path):
        path = (self.root / relative_path).resolve()
        candidates = [path]
        if path.name == "SKILL.md":
            candidates.append(path.with_name("upstream-skill.md"))
        for candidate in candidates:
            if self.root in candidate.parents and candidate.is_file():
                return candidate
        return None

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
