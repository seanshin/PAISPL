"""PAISPL M4 controlled UML round-trip change controller."""

import sys
from pathlib import Path


_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
for _source_root in (
    _WORKSPACE_ROOT / "paispl-m3" / "src",
    _WORKSPACE_ROOT / "paispl-m2" / "src",
    _WORKSPACE_ROOT / "paispl-m1" / "src",
):
    if _source_root.is_dir() and str(_source_root) not in sys.path:
        sys.path.insert(0, str(_source_root))

from .approval import ApprovalValidationError, create_approval_record
from .controller import RoundTripController
from .proposal import ProposalStateError, ProposalValidationError

__all__ = [
    "ApprovalValidationError",
    "ProposalStateError",
    "ProposalValidationError",
    "RoundTripController",
    "create_approval_record",
]

__version__ = "0.4.0"
