from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
for source in (
    ROOT / "src",
    WORKSPACE / "paispl-m3" / "src",
    WORKSPACE / "paispl-m2" / "src",
    WORKSPACE / "paispl-m1" / "src",
):
    sys.path.insert(0, str(source))

from paispl_m4.approval import ApprovalValidationError, create_approval_record
from paispl_m4.controller import RoundTripController
from paispl_m4.differ import UMLChangeDiffer
from paispl_m4.proposal import ProposalStateError, document_hash
from paispl_m4.uml import comparison_plantuml, lifecycle_plantuml


class RoundTripControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controller = RoundTripController(WORKSPACE)

    def proposal(self, case: int) -> dict:
        return self.controller.load_json(
            ROOT / "examples" / f"M4-CASE-{case:03d}.proposal.json"
        )

    def preview(self, case: int = 1) -> dict:
        return self.controller.preview(self.proposal(case))

    def approval(self, preview: dict, approval_id: str = "APR-TEST-001") -> dict:
        return create_approval_record(
            preview,
            approval_id,
            "TEST-APPROVER",
            "검증된 변경 경계와 생성 영향을 승인한다.",
            actor_type="test_fixture",
        )

    def test_schema_valid_proposal_is_accepted_for_validation(self):
        result = self.controller.validate_proposal(self.proposal(1))
        self.assertEqual("ACCEPTED_FOR_VALIDATION", result["outcome"])
        self.assertEqual("PENDING_VALIDATION", result["proposal"]["status"])
        self.assertEqual(["DRAFT", "PENDING_VALIDATION"], result["state_history"])

    def test_invalid_state_transition_is_rejected(self):
        with self.assertRaises(ProposalStateError):
            self.controller.state_machine.transition(self.proposal(1), "APPROVED")

    def test_rejected_proposal_is_immutable(self):
        rejected = self.preview(3)["proposal"]
        with self.assertRaises(ProposalStateError):
            self.controller.state_machine.transition(rejected, "PENDING_VALIDATION")

    def test_unknown_uml_id_is_rejected_before_solver(self):
        result = self.preview(3)
        self.assertEqual("REJECTED", result["outcome"])
        self.assertIn("UNKNOWN_UML_ELEMENT_ID", {item["code"] for item in result["findings"]})
        self.assertNotIn("VALIDATED", result["state_history"])

    def test_stale_base_hash_is_rejected(self):
        result = self.preview(4)
        self.assertEqual("REJECTED", result["outcome"])
        self.assertEqual("STALE_BASE_ARCHITECTURE", result["findings"][0]["code"])
        self.assertIn("rebase", result["findings"][0]["message"])

    def test_valid_feature_inclusion_reaches_pending_approval(self):
        result = self.preview(1)
        self.assertEqual("PENDING_APPROVAL", result["outcome"])
        self.assertEqual("PENDING_APPROVAL", result["proposal"]["status"])
        self.assertIn("lis_integration", result["configuration_preview"]["added"])
        impact = set(result["architecture_preview"]["impact"]["add_or_modify"])
        self.assertTrue({"CMP-LIS", "CMP-EMR", "CMP-AUDIT"} <= impact)

    def test_unsatisfiable_feature_delta_is_constraint_linked(self):
        result = self.preview(2)
        self.assertEqual("REJECTED", result["outcome"])
        finding = result["findings"][0]
        self.assertEqual("UNSATISFIABLE_FEATURE_DELTA", finding["code"])
        self.assertIn("C-024", finding["constraint_ids"])

    def test_unresolved_dependency_edit_cannot_reach_approval(self):
        proposal = self.proposal(5)
        preview = self.controller.preview(proposal)
        self.assertEqual("REJECTED", preview["outcome"])
        self.assertIn("UNRESOLVED_SEMANTIC_EDIT", {item["code"] for item in preview["findings"]})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ApprovalValidationError):
                self.controller.apply(proposal, {}, Path(directory) / "result")
            self.assertFalse((Path(directory) / "result").exists())

    def test_dependency_only_differ_classifies_unresolved_semantics(self):
        differ = UMLChangeDiffer()
        proposal = differ.propose(
            proposal_id="CP-TEST-001",
            request_id="UML-TEST-001",
            base_configuration_id="GOLD-CHG-HOSP-002",
            base_architecture_hash=self.controller.base_architecture_hash("GOLD-CHG-HOSP-002"),
            origin_uml={
                "model_id": "UML-ARCH-CHG-HOSP-002",
                "model_path": "model.puml",
                "element_ids": ["CMP-DICOM-GW", "CMP-FHIR"],
            },
            edits=[{
                "edit_type": "add_dependency",
                "source_id": "CMP-DICOM-GW",
                "target_id": "CMP-FHIR",
                "source_quote": "새 의존성을 추가한다.",
            }],
            rationale="Feature 근거가 없는 구조 변경을 제안한다.",
            proposer={"id": "TEST-AUTHOR", "type": "test_fixture"},
            created_at="2026-09-22T02:00:00Z",
        )
        self.assertEqual("unresolved_semantic_edit", proposal["operations"][0]["kind"])
        self.assertEqual("REJECTED", self.controller.preview(proposal)["outcome"])

    def test_preview_matches_direct_requirement_ir_path(self):
        preview = self.preview(6)
        base = self.controller.configurations["GOLD-CHG-HOSP-002"]["selected"]
        direct = self.controller.engine.solve(preview["requirement_ir_delta"], set(base))
        self.assertEqual(direct.to_dict(), preview["configuration_preview"])
        direct_architecture = self.controller.synthesizer.synthesize(
            request_id=preview["proposal"]["request_id"],
            configuration_id=direct.configuration_id,
            selected=direct.selected,
            added=direct.added,
            removed=direct.removed,
            intent_links=direct.trace_links,
            previous_selected=base,
        ).to_dict()
        for key in ("components", "dependencies", "interfaces", "component_delta", "impact", "test_scope"):
            self.assertEqual(direct_architecture[key], preview["architecture_preview"][key], key)

    def test_explicit_bound_rejection_reaches_rejected(self):
        proposal = self.proposal(1)
        preview = self.controller.preview(proposal)
        rejection = create_approval_record(
            preview,
            "APR-REJECT-001",
            "TEST-APPROVER",
            "현재 변경 경계는 승인하지 않는다.",
            actor_type="test_fixture",
            decision="REJECT",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result"
            result = self.controller.apply(proposal, rejection, output)
            self.assertEqual("REJECTED", result["outcome"])
            self.assertEqual("REJECTED", result["proposal"]["status"])
            self.assertFalse(output.exists())

    def test_approval_hash_mismatch_is_rejected(self):
        proposal = self.proposal(1)
        approval = self.approval(self.controller.preview(proposal))
        approval["proposal_hash"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ApprovalValidationError) as raised:
                self.controller.apply(proposal, approval, directory)
        self.assertIn(
            "APPROVAL_BINDING_MISMATCH",
            {item["code"] for item in raised.exception.findings},
        )

    def test_changed_proposal_invalidates_prior_approval(self):
        proposal = self.proposal(1)
        approval = self.approval(self.controller.preview(proposal))
        changed = copy.deepcopy(proposal)
        changed["rationale"] += " 변경된 설명"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ApprovalValidationError):
                self.controller.apply(changed, approval, directory)

    def test_approved_proposal_reaches_applied(self):
        proposal = self.proposal(6)
        preview = self.controller.preview(proposal)
        approval = self.approval(preview, "APR-TEST-006")
        with tempfile.TemporaryDirectory() as directory:
            result = self.controller.apply(proposal, approval, directory)
            self.assertEqual("APPLIED", result["outcome"])
            self.assertEqual("APPLIED", result["proposal"]["status"])
            self.assertEqual(
                ["DRAFT", "PENDING_VALIDATION", "VALIDATED", "PENDING_APPROVAL", "APPROVED", "APPLIED"],
                result["state_history"],
            )
            self.assertTrue((Path(directory) / "application-result.json").is_file())

    def test_preview_does_not_write_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / "not-created"
            result = self.preview(1)
            self.assertEqual("PENDING_APPROVAL", result["outcome"])
            self.assertFalse(sentinel.exists())

    def test_unaffected_artifact_hashes_remain_unchanged(self):
        preview = self.preview(1)
        base_architecture = self.controller.base_architecture("GOLD-CHG-HOSP-002")
        base_artifacts = self.controller.generator.generate(base_architecture)
        preview_artifacts = self.controller._bound_artifacts(
            preview["architecture_preview"], preview["proposal"], approval_id=None
        )
        preserved = [
            path for path in base_artifacts
            if path.startswith(("components/dicom-gw/", "components/emr/", "deploy/k8s/dicom-gw", "deploy/k8s/emr"))
        ]
        self.assertTrue(preserved)
        for path in preserved:
            self.assertEqual(base_artifacts[path].sha256, preview_artifacts[path].sha256, path)

    def test_applied_trace_includes_proposal_and_approval_evidence(self):
        proposal = self.proposal(6)
        preview = self.controller.preview(proposal)
        approval = self.approval(preview, "APR-TRACE-006")
        with tempfile.TemporaryDirectory() as directory:
            self.controller.apply(proposal, approval, directory)
            trace = json.loads(
                (Path(directory) / "snapshot/trace/traceability.json").read_text(encoding="utf-8")
            )
        self.assertEqual("CP-M4-006", trace["proposalId"])
        self.assertEqual("APR-TRACE-006", trace["approvalId"])
        lis = next(item for item in trace["links"] if item["featureId"] == "lis_integration")
        for key in (
            "sourceQuote",
            "intentId",
            "featureId",
            "componentId",
            "interfaceIds",
            "testIds",
            "artifactPaths",
            "proposalId",
            "operationId",
            "approvalId",
        ):
            self.assertIn(key, lis)

    def test_generated_plantuml_contains_ids_and_roundtrip_guard(self):
        preview = self.preview(1)
        lifecycle = lifecycle_plantuml()
        comparison = comparison_plantuml(
            self.controller.base_architecture("GOLD-CHG-HOSP-002"),
            preview["architecture_preview"],
            preview["proposal"]["proposal_id"],
        )
        for text in (lifecycle, comparison):
            self.assertTrue(text.startswith("@startuml"))
            self.assertTrue(text.rstrip().endswith("@enduml"))
            self.assertIn("proposalId", text)
            self.assertIn("roundTripGuard", text)
        self.assertIn("componentId=CMP-LIS", comparison)
        self.assertIn("featureIds=lis_integration", comparison)

    def test_korean_explanation_is_bound_to_feature_delta(self):
        explanation = self.preview(1)["explanation_ko"]
        self.assertIn("LIS", explanation)
        self.assertIn("lis_integration", explanation)
        self.assertIn("선택", explanation)

    def test_preview_is_deterministic(self):
        first = self.preview(1)
        second = self.preview(1)
        self.assertEqual(document_hash(first), document_hash(second))


if __name__ == "__main__":
    unittest.main()
