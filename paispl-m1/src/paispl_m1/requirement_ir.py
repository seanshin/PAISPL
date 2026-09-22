from __future__ import annotations

import json
from pathlib import Path

from .json_contract import validate


class RequirementIRValidationError(ValueError):
    def __init__(self, findings: list[str]):
        super().__init__("Requirement IR validation failed")
        self.findings = findings


class RequirementIRValidator:
    def __init__(self, schema_path: str | Path):
        self.schema_path = Path(schema_path)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))

    def load(self, path: str | Path) -> dict:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        findings = validate(value, self.schema)
        if findings:
            raise RequirementIRValidationError(findings)
        return value

