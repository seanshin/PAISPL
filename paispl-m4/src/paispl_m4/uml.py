from __future__ import annotations


def lifecycle_plantuml() -> str:
    return """@startuml
title PAISPL M4 Change Proposal Lifecycle
state DRAFT
state PENDING_VALIDATION
state VALIDATED
state PENDING_APPROVAL
state APPROVED
state REJECTED
state APPLIED
DRAFT --> PENDING_VALIDATION : validate\nproposalId
PENDING_VALIDATION --> VALIDATED : Requirement IR + Solver PASS
PENDING_VALIDATION --> REJECTED : stale, unmapped, unresolved, unsatisfiable
VALIDATED --> PENDING_APPROVAL : preview only\nconfigurationHash + architectureHash
PENDING_APPROVAL --> APPROVED : explicit approvalId + proposalHash
PENDING_APPROVAL --> REJECTED : explicit rejection
APPROVED --> APPLIED : manifest-owned materialization
note bottom
roundTripGuard=UML edits never bypass Requirement IR, Solver validation, and explicit approval.
semanticIds=proposalId,approvalId,featureId,componentId,interfaceId,testId,artifactPath
end note
@enduml
"""


def comparison_plantuml(base: dict, preview: dict, proposal_id: str) -> str:
    base_components = {item["id"]: item for item in base["components"]}
    preview_components = {item["id"]: item for item in preview["components"]}
    component_ids = sorted(set(base_components) | set(preview_components))
    lines = [
        "@startuml",
        "!pragma layout smetana",
        "skinparam componentStyle rectangle",
        f"title PAISPL M4 Before/After - {proposal_id}",
        'package "Before" {',
    ]
    for index, component_id in enumerate(component_ids, start=1):
        component = base_components.get(component_id)
        if component is None:
            continue
        features = ",".join(component["feature_ids"])
        lines.append(
            f'  component "componentId={component_id}\\nfeatureIds={features}\\nproposalId={proposal_id}" as B{index}'
        )
    lines.append("}")
    lines.append('package "After (preview only)" {')
    for index, component_id in enumerate(component_ids, start=1):
        component = preview_components.get(component_id)
        if component is None:
            continue
        features = ",".join(component["feature_ids"])
        stereotype = " <<changed>>" if base_components.get(component_id) != component else ""
        lines.append(
            f'  component "componentId={component_id}\\nfeatureIds={features}\\nproposalId={proposal_id}" as A{index}{stereotype}'
        )
    lines.extend([
        "}",
        "note bottom",
        "roundTripGuard=Preview is not approval. Apply requires Requirement IR, Solver, and approvalId.",
        "end note",
        "@enduml",
        "",
    ])
    return "\n".join(lines)
