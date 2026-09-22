from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from paispl_m1.engine import ConfigurationEngine, UnsatisfiableConfiguration
from paispl_m1.json_contract import validate as validate_json
from paispl_m2.synthesizer import ArchitectureSynthesizer
from paispl_m3.generator import Artifact, ArtifactGenerator
from paispl_m3.planner import IncrementalPlanner

from .approval import ApprovalValidationError, ApprovalValidator, approval_hash
from .proposal import (
    ChangeProposalValidator,
    ProposalStateMachine,
    canonical_json,
    document_hash,
)


class RoundTripController:
    def __init__(self, workspace_root: str | Path):
        self.workspace = Path(workspace_root)
        self.root = self.workspace / "paispl-m4"
        self.design = self.workspace / "paispl-sprint0"
        self.m1 = self.workspace / "paispl-m1"
        self.m2 = self.workspace / "paispl-m2"
        self.m3 = self.workspace / "paispl-m3"
        self.policy = yaml.safe_load(
            (self.root / "config/roundtrip-policy.yaml").read_text(encoding="utf-8")
        )
        self.proposal_validator = ChangeProposalValidator(
            self.root / "schemas/change-proposal.schema.json"
        )
        self.state_machine = ProposalStateMachine(self.root / "config/roundtrip-policy.yaml")
        self.approval_validator = ApprovalValidator(self.policy["approval_policy_id"])
        self.engine = ConfigurationEngine.load(
            self.design / "models/healthcare-feature-model.yaml",
            self.m1 / "config/solver-policy.yaml",
        )
        self.synthesizer = ArchitectureSynthesizer.load(
            self.design / "architecture/reference-architecture.yaml",
            self.m2 / "config/impact-policy.yaml",
            self.design / "tests/acceptance-tests.yaml",
        )
        self.generator = ArtifactGenerator.load(self.m3 / "config/generator-policy.yaml")
        self.planner = IncrementalPlanner(self.generator.policy["deletion_policy"])
        self.requirement_schema = json.loads(
            (self.design / "schemas/requirement-ir.schema.json").read_text(encoding="utf-8")
        )
        gold = yaml.safe_load(
            (self.design / "gold/gold-configurations.yaml").read_text(encoding="utf-8")
        )
        self.configurations = {item["id"]: item for item in gold["configurations"]}
        reference = yaml.safe_load(
            (self.design / "architecture/reference-architecture.yaml").read_text(encoding="utf-8")
        )
        self.reference_components = {item["id"]: item for item in reference["components"]}
        self.interface_ids = {
            interface_id
            for component in reference["components"]
            for interface_id in component.get("interfaces", [])
        }
        tests = yaml.safe_load(
            (self.design / "tests/acceptance-tests.yaml").read_text(encoding="utf-8")
        )
        self.test_ids = {item["id"] for item in tests["tests"]}

    def load_json(self, path: str | Path) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def base_architecture(self, configuration_id: str) -> dict:
        configuration = self.configurations.get(configuration_id)
        if configuration is None:
            raise KeyError(f"unknown base configuration: {configuration_id}")
        path = self.m2 / "generated" / f"{configuration['scenario_id']}.architecture.json"
        return self.load_json(path)

    def base_architecture_hash(self, configuration_id: str) -> str:
        return document_hash(self.base_architecture(configuration_id))

    def validate_proposal(self, proposal: dict) -> dict:
        working = self.proposal_validator.validate(proposal, required_status="DRAFT")
        history = ["DRAFT"]
        working = self.state_machine.transition(working, "PENDING_VALIDATION")
        history.append("PENDING_VALIDATION")
        return {
            "outcome": "ACCEPTED_FOR_VALIDATION",
            "proposal": working,
            "state_history": history,
            "findings": [],
        }

    def preview(self, proposal: dict) -> dict:
        accepted = self.validate_proposal(proposal)
        working = accepted["proposal"]
        history = accepted["state_history"]
        explanation = self._explain_ko(working)
        findings, context = self._pre_solver_findings(working)
        if findings:
            return self._rejected(working, history, findings, explanation, context)

        requirement_ir = self._to_requirement_ir(working)
        ir_violations = validate_json(requirement_ir, self.requirement_schema, self.requirement_schema)
        if ir_violations:
            findings = [
                self._finding(
                    "REQUIREMENT_IR_INVALID",
                    "requirement_ir",
                    item,
                    [working["proposal_id"]],
                )
                for item in ir_violations
            ]
            return self._rejected(working, history, findings, explanation, context)

        try:
            solved = self.engine.solve(requirement_ir, set(context["configuration"]["selected"]))
        except UnsatisfiableConfiguration as error:
            findings = [self._solver_finding(item, working) for item in error.findings]
            return self._rejected(working, history, findings, explanation, context)

        working = self.state_machine.transition(working, "VALIDATED")
        history.append("VALIDATED")
        architecture = self.synthesizer.synthesize(
            request_id=working["request_id"],
            configuration_id=solved.configuration_id,
            selected=solved.selected,
            added=solved.added,
            removed=solved.removed,
            intent_links=solved.trace_links,
            previous_selected=context["configuration"]["selected"],
        ).to_dict()
        architecture = self._bind_architecture_trace(architecture, working)
        preview_artifacts = self._bound_artifacts(architecture, working, approval_id=None)
        base_artifacts = self.generator.generate(context["architecture"])
        change_plan = self.planner.plan(preview_artifacts, base_artifacts, architecture)
        artifact_manifest = [
            artifact.manifest_entry() for _, artifact in sorted(preview_artifacts.items())
        ]
        configuration = solved.to_dict()
        working = self.state_machine.transition(working, "PENDING_APPROVAL")
        history.append("PENDING_APPROVAL")
        binding = {
            "proposal_hash": document_hash(working),
            "base_configuration_hash": document_hash({
                "id": context["configuration"]["id"],
                "selected": sorted(context["configuration"]["selected"]),
            }),
            "base_architecture_hash": context["architecture_hash"],
            "requirement_ir_hash": document_hash(requirement_ir),
            "preview_configuration_hash": document_hash(configuration),
            "preview_architecture_hash": document_hash(architecture),
            "preview_change_plan_hash": document_hash(change_plan),
            "preview_artifact_manifest_hash": document_hash(artifact_manifest),
        }
        return {
            "outcome": "PENDING_APPROVAL",
            "proposal": working,
            "state_history": history,
            "explanation_ko": explanation,
            "requirement_ir_delta": requirement_ir,
            "configuration_preview": configuration,
            "architecture_preview": architecture,
            "artifact_change_plan": change_plan,
            "artifact_manifest_preview": artifact_manifest,
            "binding": binding,
            "findings": [],
        }

    def apply(self, proposal: dict, approval: dict, output_root: str | Path) -> dict:
        preview = self.preview(proposal)
        if preview["outcome"] != "PENDING_APPROVAL":
            raise ApprovalValidationError([
                self._finding(
                    "PROPOSAL_NOT_APPROVABLE",
                    "approval",
                    "proposal did not reach PENDING_APPROVAL",
                    [proposal.get("proposal_id", "UNKNOWN")],
                )
            ])
        checked_approval = self.approval_validator.validate(approval, preview)
        if checked_approval["decision"] == "REJECT":
            rejected = self.state_machine.transition(preview["proposal"], "REJECTED")
            return {
                "outcome": "REJECTED",
                "proposal": rejected,
                "state_history": preview["state_history"] + ["REJECTED"],
                "approval": checked_approval,
                "findings": [self._finding(
                    "APPROVAL_DECISION_REJECTED",
                    "approval",
                    "approver rejected the proposal",
                    [checked_approval["approval_id"]],
                )],
            }
        approved = self.state_machine.transition(preview["proposal"], "APPROVED")
        history = preview["state_history"] + ["APPROVED"]
        architecture = preview["architecture_preview"]
        artifacts = self._bound_artifacts(
            architecture,
            approved,
            approval_id=checked_approval["approval_id"],
        )
        base_artifacts = self.generator.generate(
            self.base_architecture(approved["base_configuration_id"])
        )
        change_plan = self.planner.plan(artifacts, base_artifacts, architecture)
        manifest = [artifact.manifest_entry() for _, artifact in sorted(artifacts.items())]
        self._materialize_application(
            Path(output_root), artifacts, manifest, change_plan, checked_approval
        )
        applied = self.state_machine.transition(approved, "APPLIED")
        history.append("APPLIED")
        result_binding = {
            **preview["binding"],
            "approval_hash": approval_hash(checked_approval),
            "applied_proposal_hash": document_hash(applied),
            "result_configuration_hash": document_hash(preview["configuration_preview"]),
            "result_architecture_hash": document_hash(architecture),
            "result_artifact_manifest_hash": document_hash(manifest),
            "result_change_plan_hash": document_hash(change_plan),
        }
        result = {
            "outcome": "APPLIED",
            "proposal": applied,
            "state_history": history,
            "approval": checked_approval,
            "explanation_ko": preview["explanation_ko"],
            "requirement_ir_delta": preview["requirement_ir_delta"],
            "configuration_result": preview["configuration_preview"],
            "architecture_result": architecture,
            "artifact_change_plan": change_plan,
            "artifact_manifest": manifest,
            "binding": result_binding,
            "findings": [],
        }
        (Path(output_root) / "application-result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result

    def _pre_solver_findings(self, proposal: dict) -> tuple[list[dict], dict]:
        findings: list[dict] = []
        configuration = self.configurations.get(proposal["base_configuration_id"])
        if configuration is None:
            findings.append(self._finding(
                "BASE_CONFIGURATION_UNKNOWN",
                "base",
                f"unknown base configuration {proposal['base_configuration_id']}",
                [proposal["base_configuration_id"]],
            ))
            return findings, {}
        architecture = self.base_architecture(configuration["id"])
        architecture_hash = document_hash(architecture)
        context = {
            "configuration": configuration,
            "architecture": architecture,
            "architecture_hash": architecture_hash,
        }
        if proposal["base_architecture_hash"] != architecture_hash:
            findings.append(self._finding(
                "STALE_BASE_ARCHITECTURE",
                "base",
                "base architecture hash differs from the current canonical graph; rebase is required",
                [proposal["origin_uml"]["model_id"], proposal["base_configuration_id"]],
            ))

        known_semantic_ids = (
            set(self.engine.model.features)
            | set(self.reference_components)
            | self.interface_ids
            | self.test_ids
        )
        for element_id in proposal["origin_uml"]["element_ids"]:
            if element_id not in known_semantic_ids:
                findings.append(self._finding(
                    "UNKNOWN_UML_ELEMENT_ID",
                    "mapping",
                    f"UML element {element_id} does not resolve to a known immutable ID",
                    [element_id],
                ))
        operation_ids = [item["operation_id"] for item in proposal["operations"]]
        if len(operation_ids) != len(set(operation_ids)):
            findings.append(self._finding(
                "DUPLICATE_OPERATION_ID",
                "mapping",
                "operation IDs must be unique",
                operation_ids,
            ))
        supported = set(self.policy["supported_semantic_operations"])
        for operation in proposal["operations"]:
            kind = operation["kind"]
            source_id = operation["source_id"]
            target_id = operation["target_id"]
            if kind in supported:
                if target_id not in self.engine.model.features:
                    findings.append(self._finding(
                        "UNKNOWN_FEATURE_ID",
                        "mapping",
                        f"operation target {target_id} is not a known Feature ID",
                        [operation["operation_id"], target_id],
                    ))
                if source_id not in known_semantic_ids:
                    findings.append(self._finding(
                        "UNKNOWN_UML_ELEMENT_ID",
                        "mapping",
                        f"operation source {source_id} is not a known immutable ID",
                        [operation["operation_id"], source_id],
                    ))
                component = self.reference_components.get(source_id)
                if component is not None and target_id not in component.get("realizes", []):
                    findings.append(self._finding(
                        "FEATURE_GROUNDING_MISMATCH",
                        "mapping",
                        f"{source_id} does not realize Feature {target_id}",
                        [operation["operation_id"], source_id, target_id],
                    ))
            elif kind in {"add_dependency", "remove_dependency", "unresolved_semantic_edit"}:
                for component_id in (source_id, target_id):
                    if component_id not in self.reference_components:
                        findings.append(self._finding(
                            "UNKNOWN_COMPONENT_ID",
                            "mapping",
                            f"dependency endpoint {component_id} is unknown",
                            [operation["operation_id"], component_id],
                        ))
                findings.append(self._finding(
                    "UNRESOLVED_SEMANTIC_EDIT",
                    "mapping",
                    "dependency-only UML edits require an owning Feature or approved architecture rule",
                    [operation["operation_id"], source_id, target_id],
                ))
            else:
                findings.append(self._finding(
                    "UNSUPPORTED_OPERATION",
                    "mapping",
                    f"unsupported semantic operation {kind}",
                    [operation["operation_id"]],
                ))
        return findings, context

    def _to_requirement_ir(self, proposal: dict) -> dict:
        operation_map = {
            "include_feature": "include",
            "exclude_feature": "exclude",
            "replace_feature": "replace",
            "preserve_feature": "preserve",
        }
        intents = []
        for index, operation in enumerate(proposal["operations"], start=1):
            if operation["kind"] not in operation_map:
                continue
            intents.append({
                "id": f"INT-{index:03d}",
                "operation": operation_map[operation["kind"]],
                "subject": operation["target_id"],
                "feature_candidates": [{"feature_id": operation["target_id"], "score": 1.0}],
                "confidence": 1.0,
                "source_quote": operation["source_quote"],
            })
        source_text = f"UML 변경 제안 {proposal['proposal_id']}: {proposal['rationale']}"
        return {
            "version": "0.1.0",
            "request_id": proposal["request_id"],
            "domain": "healthcare-platform",
            "source_text": source_text,
            "base_configuration_id": proposal["base_configuration_id"],
            "intents": intents,
            "functional_requirements": [],
            "non_functional_requirements": [],
            "constraints": [],
            "deployment": {"profile": "unchanged", "runtime": "unchanged"},
            "data_classes": [],
            "unresolved_questions": [],
            "metadata": {
                "created_at": proposal["created_at"],
                "producer": "human",
                "model_id": "uml-roundtrip-controller",
                "prompt_template_version": "0.4.0",
            },
        }

    def _bind_architecture_trace(self, architecture: dict, proposal: dict) -> dict:
        bound = copy.deepcopy(architecture)
        operation_by_intent = {
            f"INT-{index:03d}": operation["operation_id"]
            for index, operation in enumerate(proposal["operations"], start=1)
        }
        for link in bound["trace_links"]:
            link["proposal_id"] = proposal["proposal_id"]
            link["operation_id"] = operation_by_intent[link["intent_id"]]
        return bound

    def _bound_artifacts(
        self,
        architecture: dict,
        proposal: dict,
        approval_id: str | None,
    ) -> dict[str, Artifact]:
        artifacts = self.generator.generate(architecture)
        trace_path = "trace/traceability.json"
        trace_artifact = artifacts[trace_path]
        trace = json.loads(trace_artifact.content)
        trace["proposalId"] = proposal["proposal_id"]
        if approval_id is not None:
            trace["approvalId"] = approval_id
        operation_by_intent = {
            link["intent_id"]: link["operation_id"]
            for link in architecture["trace_links"]
        }
        for link in trace["links"]:
            link["proposalId"] = proposal["proposal_id"]
            link["operationId"] = operation_by_intent[link["intentId"]]
            if approval_id is not None:
                link["approvalId"] = approval_id
        artifacts[trace_path] = Artifact(
            path=trace_artifact.path,
            kind=trace_artifact.kind,
            owner_component_id=trace_artifact.owner_component_id,
            content=json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        return dict(sorted(artifacts.items()))

    def _materialize_application(
        self,
        output_root: Path,
        artifacts: dict[str, Artifact],
        manifest: list[dict],
        change_plan: dict,
        approval: dict,
    ) -> None:
        snapshot_root = output_root / "snapshot"
        manifest_path = output_root / "artifact-manifest.json"
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous_paths = {item["path"] for item in previous.get("artifacts", [])}
            current_paths = set(artifacts)
            for relative in sorted(previous_paths - current_paths):
                relative_path = Path(relative)
                if relative_path.is_absolute() or ".." in relative_path.parts:
                    continue
                target = snapshot_root / relative_path
                if target.is_file():
                    target.unlink()
        output_root.mkdir(parents=True, exist_ok=True)
        self.generator.materialize(artifacts, snapshot_root)
        manifest_document = {
            "generator": self.generator.marker,
            "proposal_id": approval["proposal_id"],
            "approval_id": approval["approval_id"],
            "artifacts": manifest,
        }
        manifest_path.write_text(
            json.dumps(manifest_document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_root / "change-plan.json").write_text(
            json.dumps(change_plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_root / "approval.json").write_text(
            json.dumps(approval, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _solver_finding(self, message: str, proposal: dict) -> dict:
        constraint_ids = [
            constraint.id
            for constraint in self.engine.model.constraints
            if constraint.source in message and constraint.target in message
        ]
        return self._finding(
            "UNSATISFIABLE_FEATURE_DELTA",
            "solver",
            message,
            [proposal["proposal_id"]],
            constraint_ids,
        )

    def _rejected(
        self,
        proposal: dict,
        history: list[str],
        findings: list[dict],
        explanation: str,
        context: dict,
    ) -> dict:
        rejected = self.state_machine.transition(proposal, "REJECTED")
        binding = {
            "proposal_hash": document_hash(rejected),
            "base_architecture_hash": context.get("architecture_hash", proposal["base_architecture_hash"]),
        }
        return {
            "outcome": "REJECTED",
            "proposal": rejected,
            "state_history": history + ["REJECTED"],
            "explanation_ko": explanation,
            "findings": findings,
            "binding": binding,
        }

    @staticmethod
    def _finding(
        code: str,
        stage: str,
        message: str,
        source_ids: list[str] | None = None,
        constraint_ids: list[str] | None = None,
    ) -> dict:
        return {
            "code": code,
            "stage": stage,
            "message": message,
            "source_ids": source_ids or [],
            "constraint_ids": constraint_ids or [],
        }

    @staticmethod
    def _explain_ko(proposal: dict) -> str:
        templates = {
            "include_feature": "UML 요소 {source}의 추가는 Feature {target} 선택을 요청합니다.",
            "exclude_feature": "UML 요소 {source}의 제거는 Feature {target} 제외를 요청합니다.",
            "replace_feature": "UML 요소 {source}의 변경은 Feature {target}로 교체를 요청합니다.",
            "preserve_feature": "UML 요소 {source}는 Feature {target} 유지를 명시합니다.",
            "add_dependency": "{source}에서 {target}로의 의존성 추가는 의미 규칙 확인이 필요합니다.",
            "remove_dependency": "{source}에서 {target}로의 의존성 제거는 의미 규칙 확인이 필요합니다.",
            "unresolved_semantic_edit": "{source}에서 {target}로의 UML 변경은 Feature 의미가 해소되지 않았습니다.",
        }
        statements = [
            templates[operation["kind"]].format(
                source=operation["source_id"], target=operation["target_id"]
            )
            for operation in proposal["operations"]
        ]
        return " ".join(statements)
