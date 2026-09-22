from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT.parent / "paispl-sprint0"


class UMLContractTests(unittest.TestCase):
    def test_natural_language_to_uml_pipeline_has_semantic_anchors(self):
        mapping = yaml.safe_load((DESIGN / "mappings/nl-uml-trace-rules.yaml").read_text(encoding="utf-8"))
        self.assertEqual("natural_language", mapping["pipeline"][0])
        self.assertIn("requirement_ir", mapping["pipeline"])
        self.assertIn("solver_validated_configuration", mapping["pipeline"])
        self.assertIn("architecture_graph", mapping["pipeline"])
        self.assertEqual("uml_projection", mapping["pipeline"][-1])

    def test_uml_edits_cannot_bypass_solver(self):
        mapping = yaml.safe_load((DESIGN / "mappings/nl-uml-trace-rules.yaml").read_text(encoding="utf-8"))
        policy = mapping["edit_policy"]
        self.assertTrue(policy["user_edits_create_change_proposal"])
        self.assertTrue(policy["require_natural_language_explanation"])
        self.assertTrue(policy["require_solver_revalidation"])

    def test_every_architecture_component_has_feature_grounding(self):
        architecture = yaml.safe_load((DESIGN / "architecture/reference-architecture.yaml").read_text(encoding="utf-8"))
        for component in architecture["components"]:
            self.assertTrue(component["realizes"], component["id"])


if __name__ == "__main__":
    unittest.main()

