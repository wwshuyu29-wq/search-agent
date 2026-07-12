#!/usr/bin/env python3
"""Deterministically lock the curated vendor snapshot."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.specialist_registry import vendor_tree_sha256


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_lock(root=ROOT):
    catalog = json.loads((root / "specialists/catalog.json").read_text())
    repositories = {
        "marketing": "https://github.com/coreyhaines31/marketingskills.git",
        "finance": "https://github.com/himself65/finance-skills.git",
    }
    vendors = []
    for vendor_id in sorted(repositories):
        vendor_root = root / "vendor" / vendor_id
        files = {}
        for entry in catalog["specialists"]:
            relative = Path(entry["upstream_path"])
            if relative.parts[:2] == ("vendor", vendor_id):
                files[relative.as_posix()] = sha256(root / relative)
        vendors.append({
            "id": vendor_id,
            "repository": repositories[vendor_id],
            "revision": "immutable local snapshot",
            "path": f"vendor/{vendor_id}",
            "tree_sha256": vendor_tree_sha256(vendor_root),
            "files": dict(sorted(files.items())),
            "license": "MIT",
            "sync_policy": "manual-review",
        })
    return {"version": 2, "vendors": vendors}


if __name__ == "__main__":
    destination = ROOT / "specialists/vendor.lock.json"
    destination.write_text(json.dumps(build_lock(), indent=2, ensure_ascii=False) + "\n")
