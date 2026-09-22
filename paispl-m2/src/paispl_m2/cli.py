from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .synthesizer import ArchitectureSynthesizer
from .uml import write_component_plantuml


def _load_m1(m1_root: Path):
    sys.path.insert(0, str(m1_root / "src"))
    from paispl_m1.engine import ConfigurationEngine
    from paispl_m1.requirement_ir import RequirementIRValidator

    return ConfigurationEngine, RequirementIRValidator


def synthesize_sequence(args) -> int:
    ConfigurationEngine, RequirementIRValidator = _load_m1(args.m1_root)
    validator = RequirementIRValidator(args.design_root / "schemas/requirement-ir.schema.json")
    engine = ConfigurationEngine.load(
        args.design_root / "models/healthcare-feature-model.yaml",
        args.m1_root / "config/solver-policy.yaml",
    )
    synthesizer = ArchitectureSynthesizer.load(
        args.design_root / "architecture/reference-architecture.yaml",
        args.policy,
        args.design_root / "tests/acceptance-tests.yaml",
    )
    scenarios = yaml.safe_load(
        (args.design_root / "scenarios/base-and-changes.yaml").read_text(encoding="utf-8")
    )["sequence"]
    args.output.mkdir(parents=True, exist_ok=True)
    selected: set[str] | None = None
    results: list[dict] = []
    for scenario in scenarios:
        previous = set(selected or [])
        ir = validator.load(args.design_root / scenario["expected_ir"])
        solved = engine.solve(ir, selected)
        selected = set(solved.selected)
        synthesis = synthesizer.synthesize(
            request_id=scenario["id"],
            configuration_id=solved.configuration_id,
            selected=solved.selected,
            added=solved.added,
            removed=solved.removed,
            intent_links=solved.trace_links,
            previous_selected=previous,
        ).to_dict()
        output_json = args.output / f"{scenario['id']}.architecture.json"
        output_json.write_text(json.dumps(synthesis, ensure_ascii=False, indent=2), encoding="utf-8")
        write_component_plantuml(synthesis, args.output / f"{scenario['id']}.component.puml")
        results.append(synthesis)
    summary = {"status": "PASS", "results": results}
    (args.output / "sequence-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "status": "PASS",
        "scenarios": len(results),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(prog="paispl-m2")
    sub = parser.add_subparsers(dest="command", required=True)
    synth = sub.add_parser("synthesize-sequence")
    synth.add_argument("--design-root", type=Path, required=True)
    synth.add_argument("--m1-root", type=Path, required=True)
    synth.add_argument("--policy", type=Path, default=root / "config/impact-policy.yaml")
    synth.add_argument("--output", type=Path, default=root / "generated")
    synth.set_defaults(func=synthesize_sequence)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

