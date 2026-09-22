from __future__ import annotations

import argparse
import json
from pathlib import Path

from .generator import ArtifactGenerator
from .planner import IncrementalPlanner


SEQUENCE = ["BASE-HOSP-001", "CHG-HOSP-001", "CHG-HOSP-002", "CHG-HOSP-003"]


def generate_sequence(args) -> int:
    generator = ArtifactGenerator.load(args.policy)
    planner = IncrementalPlanner(generator.policy["deletion_policy"])
    previous = None
    summaries = []
    for scenario_id in SEQUENCE:
        source = args.architecture_root / f"{scenario_id}.architecture.json"
        architecture = json.loads(source.read_text(encoding="utf-8"))
        artifacts = generator.generate(architecture)
        scenario_root = args.output / scenario_id
        snapshot_root = scenario_root / "snapshot"
        manifest = generator.materialize(artifacts, snapshot_root)
        plan = planner.plan(artifacts, previous, architecture)
        (scenario_root / "artifact-manifest.json").write_text(
            json.dumps({
                "generator": generator.marker,
                "request_id": scenario_id,
                "artifacts": manifest,
            }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (scenario_root / "change-plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summaries.append({"scenario_id": scenario_id, **plan["summary"]})
        previous = artifacts
    (args.output / "sequence-summary.json").write_text(
        json.dumps({"status": "PASS", "scenarios": summaries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "scenarios": summaries}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(prog="paispl-m3")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate-sequence")
    generate.add_argument("--architecture-root", type=Path, required=True)
    generate.add_argument("--policy", type=Path, default=root / "config/generator-policy.yaml")
    generate.add_argument("--output", type=Path, default=root / "generated")
    generate.set_defaults(func=generate_sequence)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

