from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
DESIGN = WORKSPACE / "paispl-sprint0"
M1 = WORKSPACE / "paispl-m1"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(M1 / "src"))

from paispl_m1.engine import ConfigurationEngine
from paispl_m1.requirement_ir import RequirementIRValidator
from paispl_m2.synthesizer import ArchitectureSynthesizer
from paispl_m2.uml import component_plantuml


class ArchitectureSynthesizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = RequirementIRValidator(DESIGN / "schemas/requirement-ir.schema.json")
        cls.engine = ConfigurationEngine.load(
            DESIGN / "models/healthcare-feature-model.yaml",
            M1 / "config/solver-policy.yaml",
        )
        cls.synthesizer = ArchitectureSynthesizer.load(
            DESIGN / "architecture/reference-architecture.yaml",
            ROOT / "config/impact-policy.yaml",
            DESIGN / "tests/acceptance-tests.yaml",
        )
        cls.scenarios = yaml.safe_load(
            (DESIGN / "scenarios/base-and-changes.yaml").read_text(encoding="utf-8")
        )["sequence"]
        cls.expected = yaml.safe_load(
            (DESIGN / "architecture/reference-architecture.yaml").read_text(encoding="utf-8")
        )["expected_impacts"]

    def run_sequence(self):
        selected = None
        output = {}
        for scenario in self.scenarios:
            previous = set(selected or [])
            ir = self.validator.load(DESIGN / scenario["expected_ir"])
            solved = self.engine.solve(ir, selected)
            selected = set(solved.selected)
            output[scenario["id"]] = self.synthesizer.synthesize(
                request_id=scenario["id"],
                configuration_id=solved.configuration_id,
                selected=solved.selected,
                added=solved.added,
                removed=solved.removed,
                intent_links=solved.trace_links,
                previous_selected=previous,
            )
        return output

    def test_all_active_components_have_feature_evidence(self):
        for result in self.run_sequence().values():
            for component in result.components:
                self.assertTrue(component["feature_ids"], component["id"])

    def test_dependencies_never_reference_inactive_components(self):
        for result in self.run_sequence().values():
            active = {item["id"] for item in result.components}
            for dependency in result.dependencies:
                self.assertIn(dependency["source"], active)
                self.assertIn(dependency["target"], active)

    def test_interfaces_retain_owner_feature_evidence(self):
        for result in self.run_sequence().values():
            component_features = {
                item["id"]: set(item["feature_ids"]) for item in result.components
            }
            for interface in result.interfaces:
                self.assertEqual(
                    component_features[interface["owner_component_id"]],
                    set(interface["feature_ids"]),
                    interface["id"],
                )

    def test_change_impacts_match_gold_expectations(self):
        results = self.run_sequence()
        for scenario_id, expected in self.expected.items():
            actual = results[scenario_id].impact
            self.assertEqual(set(expected["add_or_modify"]), set(actual["add_or_modify"]), scenario_id)
            self.assertEqual(set(expected["remove_or_disable"]), set(actual["remove_or_disable"]), scenario_id)
            self.assertTrue(set(expected["preserve"]).issubset(actual["preserve"]), scenario_id)

    def test_change_one_preserves_imaging_without_impact(self):
        result = self.run_sequence()["CHG-HOSP-001"]
        self.assertIn("CMP-DICOM-GW", result.impact["preserve"])
        self.assertNotIn("CMP-DICOM-GW", result.impact["add_or_modify"])
        self.assertNotIn("CMP-DICOM-GW", result.impact["remove_or_disable"])

    def test_trace_chain_reaches_component_interface_and_test(self):
        result = self.run_sequence()["CHG-HOSP-001"]
        mobile = [item for item in result.trace_links if item["feature_id"] == "patient_mobile"]
        self.assertEqual(1, len(mobile))
        self.assertEqual("CMP-PATIENT-BFF", mobile[0]["component_id"])
        self.assertIn("API-PATIENT", mobile[0]["interface_ids"])
        self.assertIn("AT-MOB-001", mobile[0]["test_ids"])

    def test_removed_feature_trace_remains_auditable(self):
        result = self.run_sequence()["CHG-HOSP-001"]
        removed = [item for item in result.trace_links if item["feature_id"] == "ai_diagnosis"]
        self.assertEqual("CMP-CLINICAL-AI", removed[0]["component_id"])
        self.assertFalse(removed[0]["component_active"] is False)
        self.assertIn("AT-AI-003", result.test_scope)

    def test_uml_projection_contains_semantic_anchors_and_guard(self):
        result = self.run_sequence()["CHG-HOSP-003"].to_dict()
        uml = component_plantuml(result)
        for component in result["components"]:
            self.assertIn(f'componentId={component["id"]}', uml)
            self.assertIn("featureIds=", uml)
        self.assertIn("Change Proposal", uml)
        self.assertIn("Solver revalidation", uml)

    def test_serialized_result_is_json_safe(self):
        result = self.run_sequence()["CHG-HOSP-003"]
        json.dumps(result.to_dict(), ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
