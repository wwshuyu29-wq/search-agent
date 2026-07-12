import json
import tempfile
import unittest
from pathlib import Path

from lib.specialist_registry import CatalogError, SpecialistRegistry


ROOT = Path(__file__).resolve().parents[1]


class SpecialistRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = SpecialistRegistry(ROOT)

    def test_catalog_has_exact_curated_core(self):
        marketing = self.registry.list_specialists("marketing")
        finance = self.registry.list_specialists("finance")
        self.assertEqual(len(marketing), 8)
        self.assertEqual(len(finance), 8)
        ids = [item["id"] for item in marketing + finance]
        self.assertEqual(len(ids), len(set(ids)))

    def test_entries_have_valid_paths_and_roles(self):
        for item in self.registry.list_specialists():
            self.assertTrue((ROOT / item["upstream_path"]).is_file())
            self.assertIn(item["evidence_role"], {"method_reference", "structured_data"})
            self.assertTrue(item["nodes"])
            self.assertTrue(item["trigger_terms"])

    def test_lookup_and_unknown_id(self):
        self.assertEqual(self.registry.get_specialist("pricing")["domain"], "marketing")
        with self.assertRaises(KeyError):
            self.registry.get_specialist("not-curated")

    def test_prompts_are_internal_resources_with_contract_headings(self):
        for item in self.registry.list_specialists():
            text = self.registry.resolve_prompt(item["id"]).read_text(encoding="utf-8")
            self.assertFalse(text.startswith("---"))
            self.assertNotIn("\nname:", text)
            self.assertNotIn("\ndescription:", text)
            for heading in ("## Purpose", "## Accepted Inputs", "## Permitted Outputs", "## Evidence Role", "## Forbidden Behavior"):
                self.assertIn(heading, text)

    def test_rejects_malformed_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specialists").mkdir()
            (root / "specialists" / "catalog.json").write_text(
                json.dumps({"specialists": [{"id": "broken"}]}), encoding="utf-8"
            )
            with self.assertRaises(CatalogError):
                SpecialistRegistry(root)


if __name__ == "__main__":
    unittest.main()
