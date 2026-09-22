from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT.parent / "paispl-sprint0"
sys.path.insert(0, str(ROOT / "src"))

from paispl_m1.engine import ConfigurationEngine, UnsatisfiableConfiguration
from paispl_m1.requirement_ir import RequirementIRValidationError, RequirementIRValidator


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = RequirementIRValidator(DESIGN / "schemas/requirement-ir.schema.json")
        cls.engine = ConfigurationEngine.load(
            DESIGN / "models/healthcare-feature-model.yaml",
            ROOT / "config/solver-policy.yaml",
        )
        cls.scenarios = yaml.safe_load((DESIGN / "scenarios/base-and-changes.yaml").read_text(encoding="utf-8"))["sequence"]
        cls.gold = {
            item["scenario_id"]: set(item["selected"])
            for item in yaml.safe_load((DESIGN / "gold/gold-configurations.yaml").read_text(encoding="utf-8"))["configurations"]
        }

    def test_sequence_matches_all_gold_configurations(self):
        base = None
        for scenario in self.scenarios:
            ir = self.validator.load(DESIGN / scenario["expected_ir"])
            result = self.engine.solve(ir, base)
            self.assertEqual(set(result.selected), self.gold[scenario["id"]], scenario["id"])
            base = set(result.selected)

    def test_every_result_is_model_valid(self):
        base = None
        for scenario in self.scenarios:
            ir = self.validator.load(DESIGN / scenario["expected_ir"])
            result = self.engine.solve(ir, base)
            self.assertEqual([], self.engine.model.findings(set(result.selected)))
            base = set(result.selected)

    def test_change_one_preserves_imaging_components(self):
        base_ir = self.validator.load(DESIGN / "examples/BASE-HOSP-001.requirement-ir.json")
        base = self.engine.solve(base_ir)
        change_ir = self.validator.load(DESIGN / "examples/CHG-HOSP-001.requirement-ir.json")
        changed = self.engine.solve(change_ir, set(base.selected))
        for feature in {"pacs_integration", "dicom_gateway", "mri_adapter", "ct_adapter"}:
            self.assertIn(feature, changed.selected)
            self.assertNotIn(feature, changed.added)
            self.assertNotIn(feature, changed.removed)

    def test_on_premise_switches_ai_model(self):
        base = None
        results = []
        for scenario in self.scenarios[:3]:
            ir = self.validator.load(DESIGN / scenario["expected_ir"])
            result = self.engine.solve(ir, base)
            results.append(result)
            base = set(result.selected)
        self.assertIn("local_model", results[-1].selected)
        self.assertNotIn("cloud_model", results[-1].selected)

    def test_explicit_on_premise_and_cloud_model_conflict(self):
        ir = self.validator.load(DESIGN / "examples/BASE-HOSP-001.requirement-ir.json")
        ir["deployment"]["profile"] = "on_premise"
        ir["intents"].append({
            "id": "INT-099",
            "operation": "include",
            "subject": "Cloud model",
            "feature_candidates": [{"feature_id": "cloud_model", "score": 1.0}],
            "confidence": 1.0,
            "source_quote": "Cloud model required",
        })
        with self.assertRaises(UnsatisfiableConfiguration):
            self.engine.solve(ir)

    def test_invalid_requirement_ir_is_rejected(self):
        value = json.loads((DESIGN / "examples/BASE-HOSP-001.requirement-ir.json").read_text(encoding="utf-8"))
        value.pop("domain")
        temp = ROOT / "tests/invalid-ir.json"
        temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        try:
            with self.assertRaises(RequirementIRValidationError):
                self.validator.load(temp)
        finally:
            temp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

