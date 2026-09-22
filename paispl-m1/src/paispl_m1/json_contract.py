from __future__ import annotations

import json
import re
from datetime import datetime


def _resolve_ref(root_schema: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local references are supported: {ref}")
    node = root_schema
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def _matches_type(value, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def validate(value, rule: dict, root_schema: dict | None = None, path: str = "$") -> list[str]:
    root_schema = root_schema or rule
    findings: list[str] = []
    if "$ref" in rule:
        return validate(value, _resolve_ref(root_schema, rule["$ref"]), root_schema, path)
    if "const" in rule and value != rule["const"]:
        findings.append(f"{path}: expected constant {rule['const']!r}")
    if "enum" in rule and value not in rule["enum"]:
        findings.append(f"{path}: {value!r} is not in enum {rule['enum']}")
    expected = rule.get("type")
    if expected:
        options = expected if isinstance(expected, list) else [expected]
        if not any(_matches_type(value, option) for option in options):
            findings.append(f"{path}: invalid type {type(value).__name__}, expected {options}")
            return findings
    if isinstance(value, dict):
        for key in rule.get("required", []):
            if key not in value:
                findings.append(f"{path}: missing required property {key}")
        properties = rule.get("properties", {})
        if rule.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    findings.append(f"{path}: unexpected property {key}")
        for key, child_rule in properties.items():
            if key in value:
                findings.extend(validate(value[key], child_rule, root_schema, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < rule.get("minItems", 0):
            findings.append(f"{path}: requires at least {rule['minItems']} items")
        if rule.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            findings.append(f"{path}: items must be unique")
        if "items" in rule:
            for index, item in enumerate(value):
                findings.extend(validate(item, rule["items"], root_schema, f"{path}[{index}]"))
    if isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            findings.append(f"{path}: string shorter than {rule['minLength']}")
        if "pattern" in rule and not re.search(rule["pattern"], value):
            findings.append(f"{path}: value does not match {rule['pattern']}")
        if rule.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                findings.append(f"{path}: invalid date-time")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in rule and value < rule["minimum"]:
            findings.append(f"{path}: below minimum {rule['minimum']}")
        if "maximum" in rule and value > rule["maximum"]:
            findings.append(f"{path}: above maximum {rule['maximum']}")
    return findings

