from __future__ import annotations


class UMLChangeDiffer:
    """Translate a structured UML delta into a DRAFT Change Proposal."""

    def __init__(self, approved_architecture_rules: list[str] | None = None):
        self.approved_architecture_rules = set(approved_architecture_rules or [])

    def propose(
        self,
        *,
        proposal_id: str,
        request_id: str,
        base_configuration_id: str,
        base_architecture_hash: str,
        origin_uml: dict,
        edits: list[dict],
        rationale: str,
        proposer: dict,
        created_at: str,
    ) -> dict:
        operations = [self._operation(index, edit) for index, edit in enumerate(edits, start=1)]
        edit_types = {edit["edit_type"] for edit in edits}
        if edit_types <= {"add_element"}:
            edit_type = "addition"
        elif edit_types <= {"remove_element"}:
            edit_type = "removal"
        elif edit_types <= {"add_dependency", "remove_dependency"}:
            edit_type = "dependency"
        else:
            edit_type = "compound"
        return {
            "version": "0.4.0",
            "proposal_id": proposal_id,
            "request_id": request_id,
            "base_configuration_id": base_configuration_id,
            "base_architecture_hash": base_architecture_hash,
            "origin_uml": origin_uml,
            "edit_type": edit_type,
            "rationale": rationale,
            "operations": operations,
            "proposer": proposer,
            "created_at": created_at,
            "status": "DRAFT",
            "required_approval_policy": "human-explicit-v1",
        }

    def _operation(self, index: int, edit: dict) -> dict:
        edit_type = edit["edit_type"]
        source_id = edit["source_id"]
        target_id = edit["target_id"]
        kind = "unresolved_semantic_edit"
        if edit_type in {"add_element", "remove_element"} and edit.get("feature_id"):
            kind = "include_feature" if edit_type == "add_element" else "exclude_feature"
            target_id = edit["feature_id"]
        elif edit_type in {"add_dependency", "remove_dependency"}:
            rule_id = edit.get("architecture_rule_id")
            if rule_id in self.approved_architecture_rules:
                kind = "add_dependency" if edit_type == "add_dependency" else "remove_dependency"
        return {
            "operation_id": f"CPO-{index:03d}",
            "kind": kind,
            "source_id": source_id,
            "target_id": target_id,
            "source_quote": edit.get("source_quote", f"UML edit {source_id} -> {target_id}"),
        }
