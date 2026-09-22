from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

from paispl_m1.json_contract import validate as validate_json


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def document_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class ProposalValidationError(ValueError):
    def __init__(self, findings: list[dict]):
        super().__init__("Change Proposal validation failed")
        self.findings = findings


class ProposalStateError(ValueError):
    pass


class ChangeProposalValidator:
    def __init__(self, schema_path: str | Path):
        self.schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))

    def validate(self, proposal: dict, required_status: str | None = None) -> dict:
        violations = validate_json(proposal, self.schema, self.schema)
        findings = [
            {
                "code": "PROPOSAL_SCHEMA_INVALID",
                "stage": "structure",
                "message": violation,
                "source_ids": [proposal.get("proposal_id", "UNKNOWN")],
                "constraint_ids": [],
            }
            for violation in violations
        ]
        if required_status is not None and proposal.get("status") != required_status:
            findings.append({
                "code": "PROPOSAL_STATUS_INVALID",
                "stage": "structure",
                "message": f"expected status {required_status}, got {proposal.get('status')}",
                "source_ids": [proposal.get("proposal_id", "UNKNOWN")],
                "constraint_ids": [],
            })
        if findings:
            raise ProposalValidationError(findings)
        return copy.deepcopy(proposal)


class ProposalStateMachine:
    def __init__(self, policy_path: str | Path):
        policy = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
        self.allowed = {
            state: tuple(targets)
            for state, targets in policy["allowed_transitions"].items()
        }

    def transition(self, proposal: dict, target: str) -> dict:
        current = proposal.get("status")
        if current == "REJECTED":
            raise ProposalStateError("Rejected proposals are immutable evidence")
        if target not in self.allowed.get(current, ()):
            raise ProposalStateError(f"invalid proposal transition: {current} -> {target}")
        transitioned = copy.deepcopy(proposal)
        transitioned["status"] = target
        return transitioned
