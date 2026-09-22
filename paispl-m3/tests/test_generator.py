from __future__ import annotations

import json
import py_compile
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
M2_GENERATED = WORKSPACE / "paispl-m2" / "generated"
sys.path.insert(0, str(ROOT / "src"))

from paispl_m3.generator import ArtifactGenerator
from paispl_m3.planner import IncrementalPlanner


SEQUENCE = ["BASE-HOSP-001", "CHG-HOSP-001", "CHG-HOSP-002", "CHG-HOSP-003"]


class ArtifactGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = ArtifactGenerator.load(ROOT / "config/generator-policy.yaml")
        cls.planner = IncrementalPlanner(cls.generator.policy["deletion_policy"])
        cls.architectures = {
            scenario_id: json.loads(
                (M2_GENERATED / f"{scenario_id}.architecture.json").read_text(encoding="utf-8")
            )
            for scenario_id in SEQUENCE
        }
        cls.artifacts = {
            scenario_id: cls.generator.generate(cls.architectures[scenario_id])
            for scenario_id in SEQUENCE
        }

    def test_generation_is_deterministic(self):
        for scenario_id in SEQUENCE:
            first = self.artifacts[scenario_id]
            second = self.generator.generate(self.architectures[scenario_id])
            self.assertEqual(
                {path: item.sha256 for path, item in first.items()},
                {path: item.sha256 for path, item in second.items()},
            )

    def test_change_one_preserves_imaging_and_emr_bytes(self):
        base = self.artifacts["BASE-HOSP-001"]
        changed = self.artifacts["CHG-HOSP-001"]
        preserved_prefixes = ("components/dicom-gw/", "components/emr/", "deploy/k8s/dicom-gw", "deploy/k8s/emr")
        paths = [path for path in base if path.startswith(preserved_prefixes)]
        self.assertTrue(paths)
        for path in paths:
            self.assertIn(path, changed)
            self.assertEqual(base[path].content, changed[path].content, path)

    def test_change_plans_distinguish_write_and_review_only(self):
        plans = {}
        previous = None
        for scenario_id in SEQUENCE:
            plans[scenario_id] = self.planner.plan(
                self.artifacts[scenario_id], previous, self.architectures[scenario_id]
            )
            previous = self.artifacts[scenario_id]
        change_one = plans["CHG-HOSP-001"]
        self.assertTrue(any("patient-bff" in path for path in change_one["operations"]["create"]))
        self.assertTrue(any("clinical-ai" in path for path in change_one["operations"]["update"]))
        self.assertIn("CMP-AUDIT", change_one["review_only_component_ids"])
        self.assertIn("CMP-FHIR", change_one["review_only_component_ids"])
        change_two = plans["CHG-HOSP-002"]
        self.assertIn("CMP-POLICY", change_two["review_only_component_ids"])
        change_three = plans["CHG-HOSP-003"]
        for component_id in {"CMP-AUDIT", "CMP-EMR", "CMP-POLICY"}:
            self.assertIn(component_id, change_three["review_only_component_ids"])

    def test_only_manifest_owned_paths_can_be_deleted(self):
        previous = self.artifacts["BASE-HOSP-001"]
        current = dict(previous)
        removed_path = next(iter(current))
        current.pop(removed_path)
        plan = self.planner.plan(current, previous, self.architectures["BASE-HOSP-001"])
        self.assertEqual("manifest_owned_only", plan["deletion_policy"])
        self.assertEqual([removed_path], plan["operations"]["delete"])

    def test_every_artifact_has_safe_relative_path_and_owner_marker(self):
        for artifacts in self.artifacts.values():
            for path, artifact in artifacts.items():
                self.assertFalse(path.startswith("/"))
                self.assertNotIn("..", Path(path).parts)
                self.assertIn(self.generator.marker, artifact.content)

    def test_generated_python_compiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for artifact in self.artifacts["CHG-HOSP-003"].values():
                if artifact.kind != "code_scaffold":
                    continue
                target = root / artifact.path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(artifact.content, encoding="utf-8")
                py_compile.compile(str(target), doraise=True)

    def test_generated_yaml_is_parseable(self):
        for artifact in self.artifacts["CHG-HOSP-003"].values():
            if artifact.path.endswith(".yaml"):
                documents = list(yaml.safe_load_all(artifact.content))
                self.assertTrue(documents, artifact.path)
                self.assertTrue(all(document is not None for document in documents), artifact.path)

    def test_contracts_explicitly_remain_stubs(self):
        contracts = [
            json.loads(item.content)
            for item in self.artifacts["CHG-HOSP-003"].values()
            if item.kind == "interface_contract"
        ]
        self.assertTrue(contracts)
        self.assertTrue(all(item["implementationStatus"] == "stub_requires_domain_contract" for item in contracts))

    def test_natural_language_trace_reaches_generated_paths(self):
        trace = json.loads(self.artifacts["CHG-HOSP-003"]["trace/traceability.json"].content)
        abac = next(item for item in trace["links"] if item["featureId"] == "abac")
        self.assertIn("ABAC", abac["sourceQuote"])
        self.assertEqual("CMP-IDENTITY", abac["componentId"])
        self.assertTrue(any(path.startswith("components/identity/") for path in abac["artifactPaths"]))

    def test_deployment_uml_is_a_tagged_projection(self):
        uml = self.artifacts["CHG-HOSP-003"]["uml/deployment.puml"].content
        architecture = self.architectures["CHG-HOSP-003"]
        for component in architecture["components"]:
            self.assertIn(component["id"], uml)
        self.assertIn("featureIds=", uml)
        self.assertIn("artifactPath=", uml)
        self.assertIn("Requirement IR and Solver revalidation", uml)


if __name__ == "__main__":
    unittest.main()
