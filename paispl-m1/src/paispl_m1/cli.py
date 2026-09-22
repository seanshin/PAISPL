from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .engine import ConfigurationEngine, UnsatisfiableConfiguration
from .requirement_ir import RequirementIRValidationError, RequirementIRValidator


def paths(design_root: Path, policy_path: Path | None):
    schema = design_root / "schemas/requirement-ir.schema.json"
    model = design_root / "models/healthcare-feature-model.yaml"
    policy = policy_path or Path(__file__).resolve().parents[2] / "config/solver-policy.yaml"
    return schema, model, policy


def validate_ir(args) -> int:
    schema, _, _ = paths(args.design_root, args.policy)
    validator = RequirementIRValidator(schema)
    try:
        value = validator.load(args.ir)
    except RequirementIRValidationError as exc:
        print(json.dumps({"status": "FAIL", "findings": exc.findings}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "request_id": value["request_id"]}, ensure_ascii=False, indent=2))
    return 0


def solve_sequence(args) -> int:
    schema, model, policy = paths(args.design_root, args.policy)
    validator = RequirementIRValidator(schema)
    engine = ConfigurationEngine.load(model, policy)
    scenarios = yaml.safe_load((args.design_root / "scenarios/base-and-changes.yaml").read_text(encoding="utf-8"))
    base: set[str] | None = None
    outputs = []
    for scenario in scenarios["sequence"]:
        ir = validator.load(args.design_root / scenario["expected_ir"])
        try:
            result = engine.solve(ir, base)
        except UnsatisfiableConfiguration as exc:
            print(json.dumps({"status": "FAIL", "scenario": scenario["id"], "findings": exc.findings}, ensure_ascii=False, indent=2))
            return 1
        base = set(result.selected)
        outputs.append({"scenario_id": scenario["id"], **result.to_dict()})
    print(json.dumps({"status": "PASS", "results": outputs}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="paispl-m1")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-ir")
    validate.add_argument("ir", type=Path)
    validate.add_argument("--design-root", type=Path, required=True)
    validate.add_argument("--policy", type=Path)
    validate.set_defaults(func=validate_ir)
    solve = sub.add_parser("solve-sequence")
    solve.add_argument("--design-root", type=Path, required=True)
    solve.add_argument("--policy", type=Path)
    solve.set_defaults(func=solve_sequence)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

