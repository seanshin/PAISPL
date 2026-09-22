from __future__ import annotations

import json
from pathlib import Path

from .controller import RoundTripController
from .uml import comparison_plantuml, lifecycle_plantuml


EXPECTED = {
    "M4-CASE-001": ("PENDING_APPROVAL", None),
    "M4-CASE-002": ("REJECTED", "UNSATISFIABLE_FEATURE_DELTA"),
    "M4-CASE-003": ("REJECTED", "UNKNOWN_UML_ELEMENT_ID"),
    "M4-CASE-004": ("REJECTED", "STALE_BASE_ARCHITECTURE"),
    "M4-CASE-005": ("REJECTED", "UNRESOLVED_SEMANTIC_EDIT"),
    "M4-CASE-006": ("APPLIED", None),
}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_required_cases(
    controller: RoundTripController,
    examples_root: str | Path,
    output_root: str | Path,
) -> dict:
    examples = Path(examples_root)
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    case_one_preview = None
    for case_id in EXPECTED:
        proposal = controller.load_json(examples / f"{case_id}.proposal.json")
        if case_id == "M4-CASE-006":
            approval = controller.load_json(examples / "M4-CASE-006.approval.json")
            result = controller.apply(
                proposal,
                approval,
                output / case_id / "application",
            )
        else:
            result = controller.preview(proposal)
        expected_outcome, expected_code = EXPECTED[case_id]
        actual_codes = [item["code"] for item in result["findings"]]
        if result["outcome"] != expected_outcome:
            raise RuntimeError(
                f"{case_id}: expected {expected_outcome}, got {result['outcome']}"
            )
        if expected_code is not None and expected_code not in actual_codes:
            raise RuntimeError(f"{case_id}: missing finding {expected_code}")
        if case_id == "M4-CASE-001":
            case_one_preview = result
            impact = set(result["architecture_preview"]["impact"]["add_or_modify"])
            required_impact = {"CMP-LIS", "CMP-EMR", "CMP-AUDIT"}
            if not required_impact <= impact:
                raise RuntimeError(f"{case_id}: incomplete impact {sorted(impact)}")
        write_json(output / case_id / "evidence.json", result)
        summaries.append({
            "case_id": case_id,
            "outcome": result["outcome"],
            "finding_codes": actual_codes,
            "state_history": result["state_history"],
        })

    uml_root = output / "uml"
    uml_root.mkdir(parents=True, exist_ok=True)
    (uml_root / "proposal-lifecycle.puml").write_text(lifecycle_plantuml(), encoding="utf-8")
    if case_one_preview is None:
        raise RuntimeError("M4-CASE-001 preview evidence was not produced")
    base = controller.base_architecture("GOLD-CHG-HOSP-002")
    (uml_root / "M4-CASE-001.before-after.puml").write_text(
        comparison_plantuml(
            base,
            case_one_preview["architecture_preview"],
            case_one_preview["proposal"]["proposal_id"],
        ),
        encoding="utf-8",
    )
    summary = {"status": "PASS", "cases": summaries}
    write_json(output / "case-summary.json", summary)
    return summary
