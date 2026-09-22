from __future__ import annotations

import argparse
import json
from pathlib import Path

from .approval import ApprovalValidationError
from .controller import RoundTripController
from .proposal import ProposalStateError, ProposalValidationError
from .runner import run_required_cases


def emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    default_workspace = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(prog="paispl-m4")
    parser.add_argument("--workspace", type=Path, default=default_workspace)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-proposal")
    validate.add_argument("proposal", type=Path)

    preview = subparsers.add_parser("preview-proposal")
    preview.add_argument("proposal", type=Path)

    approve = subparsers.add_parser("approve-proposal")
    approve.add_argument("proposal", type=Path)
    approve.add_argument("--approval", type=Path, required=True)
    approve.add_argument("--output", type=Path, required=True)

    cases = subparsers.add_parser("run-examples")
    cases.add_argument("--examples", type=Path)
    cases.add_argument("--output", type=Path)

    args = parser.parse_args()
    controller = RoundTripController(args.workspace)
    try:
        if args.command == "validate-proposal":
            emit(controller.validate_proposal(controller.load_json(args.proposal)))
        elif args.command == "preview-proposal":
            emit(controller.preview(controller.load_json(args.proposal)))
        elif args.command == "approve-proposal":
            emit(controller.apply(
                controller.load_json(args.proposal),
                controller.load_json(args.approval),
                args.output,
            ))
        elif args.command == "run-examples":
            emit(run_required_cases(
                controller,
                args.examples or controller.root / "examples",
                args.output or controller.root / "generated",
            ))
    except (ProposalValidationError, ProposalStateError, ApprovalValidationError, KeyError) as error:
        emit({
            "status": "ERROR",
            "error": type(error).__name__,
            "message": str(error),
            "findings": getattr(error, "findings", []),
        })
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
