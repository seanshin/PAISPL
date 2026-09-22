from __future__ import annotations

import copy

from .proposal import document_hash


REQUIRED_FIELDS = {
    "version",
    "approval_id",
    "proposal_id",
    "proposal_hash",
    "base_configuration_id",
    "base_architecture_hash",
    "preview_configuration_hash",
    "preview_architecture_hash",
    "approver",
    "decision",
    "rationale",
    "policy_version",
}


class ApprovalValidationError(ValueError):
    def __init__(self, findings: list[dict]):
        super().__init__("Approval validation failed")
        self.findings = findings


def create_approval_record(
    preview: dict,
    approval_id: str,
    approver_id: str,
    rationale: str,
    actor_type: str = "human",
    decision: str = "APPROVE",
) -> dict:
    binding = preview["binding"]
    return {
        "version": "0.4.0",
        "approval_id": approval_id,
        "proposal_id": preview["proposal"]["proposal_id"],
        "proposal_hash": binding["proposal_hash"],
        "base_configuration_id": preview["proposal"]["base_configuration_id"],
        "base_architecture_hash": binding["base_architecture_hash"],
        "preview_configuration_hash": binding["preview_configuration_hash"],
        "preview_architecture_hash": binding["preview_architecture_hash"],
        "approver": {"id": approver_id, "type": actor_type},
        "decision": decision,
        "rationale": rationale,
        "policy_version": preview["proposal"]["required_approval_policy"],
    }


def approval_hash(approval: dict) -> str:
    return document_hash(approval)


class ApprovalValidator:
    def __init__(self, policy_version: str):
        self.policy_version = policy_version

    def validate(self, approval: dict, preview: dict) -> dict:
        findings: list[dict] = []
        missing = sorted(REQUIRED_FIELDS - set(approval))
        extra = sorted(set(approval) - REQUIRED_FIELDS)
        if missing:
            findings.append(self._finding("APPROVAL_FIELDS_MISSING", f"missing fields: {missing}"))
        if extra:
            findings.append(self._finding("APPROVAL_FIELDS_UNKNOWN", f"unknown fields: {extra}"))
        if findings:
            raise ApprovalValidationError(findings)

        binding = preview["binding"]
        expected = {
            "version": "0.4.0",
            "proposal_id": preview["proposal"]["proposal_id"],
            "proposal_hash": binding["proposal_hash"],
            "base_configuration_id": preview["proposal"]["base_configuration_id"],
            "base_architecture_hash": binding["base_architecture_hash"],
            "preview_configuration_hash": binding["preview_configuration_hash"],
            "preview_architecture_hash": binding["preview_architecture_hash"],
            "policy_version": self.policy_version,
        }
        for key, value in expected.items():
            if approval.get(key) != value:
                findings.append(self._finding(
                    "APPROVAL_BINDING_MISMATCH",
                    f"{key} does not match the validated preview",
                    [approval.get("approval_id", "UNKNOWN"), preview["proposal"]["proposal_id"]],
                ))
        if approval.get("decision") not in {"APPROVE", "REJECT"}:
            findings.append(self._finding(
                "APPROVAL_DECISION_INVALID",
                "approval decision must be APPROVE or REJECT",
                [approval.get("approval_id", "UNKNOWN")],
            ))
        if not isinstance(approval.get("approval_id"), str) or not approval["approval_id"].strip():
            findings.append(self._finding("APPROVAL_ID_INVALID", "approval ID is required"))
        approver = approval.get("approver")
        if not isinstance(approver, dict) or set(approver) != {"id", "type"}:
            findings.append(self._finding("APPROVER_INVALID", "approver identity is invalid"))
        elif approver["type"] not in {"human", "test_fixture"} or not approver["id"]:
            findings.append(self._finding("APPROVER_INVALID", "approver identity is invalid"))
        if not isinstance(approval.get("rationale"), str) or not approval["rationale"].strip():
            findings.append(self._finding("APPROVAL_RATIONALE_MISSING", "approval rationale is required"))
        if findings:
            raise ApprovalValidationError(findings)
        return copy.deepcopy(approval)

    @staticmethod
    def _finding(code: str, message: str, source_ids: list[str] | None = None) -> dict:
        return {
            "code": code,
            "stage": "approval",
            "message": message,
            "source_ids": source_ids or [],
            "constraint_ids": [],
        }
