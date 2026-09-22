#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
checks: list[tuple[str, str]] = []


def load_yaml(relative: str):
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def ok(name: str, detail: str):
    checks.append((name, detail))


def fail(message: str):
    errors.append(message)


def resolve_ref(root_schema: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local schema references are supported: {ref}")
    node = root_schema
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def matches_type(value, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def validate_json_schema(value, rule: dict, root_schema: dict, path: str = "$") -> list[str]:
    findings: list[str] = []
    if "$ref" in rule:
        return validate_json_schema(value, resolve_ref(root_schema, rule["$ref"]), root_schema, path)
    if "const" in rule and value != rule["const"]:
        findings.append(f"{path}: expected constant {rule['const']!r}")
    if "enum" in rule and value not in rule["enum"]:
        findings.append(f"{path}: {value!r} is not in enum {rule['enum']}")
    expected = rule.get("type")
    if expected:
        options = expected if isinstance(expected, list) else [expected]
        if not any(matches_type(value, item) for item in options):
            findings.append(f"{path}: invalid type {type(value).__name__}, expected {options}")
            return findings
    if isinstance(value, dict):
        required = rule.get("required", [])
        for key in required:
            if key not in value:
                findings.append(f"{path}: missing required property {key}")
        properties = rule.get("properties", {})
        if rule.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    findings.append(f"{path}: unexpected property {key}")
        for key, child_rule in properties.items():
            if key in value:
                findings.extend(validate_json_schema(value[key], child_rule, root_schema, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < rule.get("minItems", 0):
            findings.append(f"{path}: requires at least {rule['minItems']} items")
        if rule.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            findings.append(f"{path}: items must be unique")
        if "items" in rule:
            for index, item in enumerate(value):
                findings.extend(validate_json_schema(item, rule["items"], root_schema, f"{path}[{index}]"))
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


schema = json.loads((ROOT / "schemas/requirement-ir.schema.json").read_text(encoding="utf-8"))
catalog = load_yaml("catalog/healthcare-features.yaml")
model = load_yaml("models/healthcare-feature-model.yaml")
scenarios = load_yaml("scenarios/base-and-changes.yaml")
gold = load_yaml("gold/gold-configurations.yaml")
architecture = load_yaml("architecture/reference-architecture.yaml")
tests_doc = load_yaml("tests/acceptance-tests.yaml")
mapping = load_yaml("mappings/nl-uml-trace-rules.yaml")

catalog_ids = {item["id"] for item in catalog["features"]}
model_items = {item["id"]: item for item in model["features"]}
model_ids = set(model_items)

if len(catalog_ids) >= 30:
    ok("Feature Catalog", f"{len(catalog_ids)} features")
else:
    fail(f"Feature Catalog has only {len(catalog_ids)} features")

if catalog_ids != model_ids:
    fail(f"Catalog and model feature sets differ: catalog_only={sorted(catalog_ids-model_ids)}, model_only={sorted(model_ids-catalog_ids)}")
else:
    ok("Catalog Model Alignment", "feature identifiers are identical")

if len(model["constraints"]) >= 20:
    ok("Constraint Count", f"{len(model['constraints'])} constraints")
else:
    fail("At least 20 constraints are required")

for feature in model["features"]:
    parent = feature.get("parent")
    if parent is not None and parent not in model_ids:
        fail(f"Unknown parent {parent} for {feature['id']}")

for group in model["groups"]:
    if group["parent"] not in model_ids:
        fail(f"Unknown group parent {group['parent']}")
    for member in group["members"]:
        if member not in model_ids:
            fail(f"Unknown group member {member}")

for constraint in model["constraints"]:
    if constraint["source"] not in model_ids or constraint["target"] not in model_ids:
        fail(f"Constraint {constraint['id']} references unknown feature")

if not errors:
    ok("Feature Model References", "parents, groups and constraints resolve")

test_ids = {item["id"] for item in tests_doc["tests"]}
for test in tests_doc["tests"]:
    unknown = set(test.get("feature_ids", [])) - model_ids
    if unknown:
        fail(f"Test {test['id']} references unknown features {sorted(unknown)}")
ok("Acceptance Tests", f"{len(test_ids)} tests")

example_paths = sorted((ROOT / "examples").glob("*.json"))
for path in example_paths:
    value = json.loads(path.read_text(encoding="utf-8"))
    violations = validate_json_schema(value, schema, schema)
    for violation in violations:
        fail(f"{path.name}: schema violation: {violation}")
    for intent in value["intents"]:
        for candidate in intent["feature_candidates"]:
            if candidate["feature_id"] not in model_ids:
                fail(f"{path.name}: unknown candidate {candidate['feature_id']}")
    for requirement in value["functional_requirements"]:
        for test_id in requirement["acceptance_test_ids"]:
            if test_id not in test_ids:
                fail(f"{path.name}: unknown acceptance test {test_id}")
if len(example_paths) == 4:
    ok("Requirement IR Examples", "4 examples validated")
else:
    fail(f"Expected 4 Requirement IR examples, found {len(example_paths)}")


def validate_configuration(config: dict):
    cid = config["id"]
    selected = set(config["selected"])
    unknown = selected - model_ids
    if unknown:
        fail(f"{cid}: unknown selected features {sorted(unknown)}")
    if model["root"] not in selected:
        fail(f"{cid}: root feature is not selected")
    for feature in model["features"]:
        fid = feature["id"]
        parent = feature.get("parent")
        if fid in selected and parent and parent not in selected:
            fail(f"{cid}: selected child {fid} without parent {parent}")
        if feature["kind"] == "mandatory" and parent in selected and fid not in selected:
            fail(f"{cid}: mandatory feature {fid} is missing")
    for group in model["groups"]:
        count = len(selected.intersection(group["members"]))
        minimum = group["cardinality"]["min"] if group["parent"] in selected else 0
        maximum = group["cardinality"]["max"] if group["parent"] in selected else 0
        if not minimum <= count <= maximum:
            fail(f"{cid}: group {group['id']} count {count} is outside {minimum}..{maximum}")
    for constraint in model["constraints"]:
        source = constraint["source"]
        target = constraint["target"]
        if constraint["type"] == "requires" and source in selected and target not in selected:
            fail(f"{cid}: {source} requires {target}")
        if constraint["type"] == "excludes" and source in selected and target in selected:
            fail(f"{cid}: {source} excludes {target}")


for config in gold["configurations"]:
    validate_configuration(config)
ok("Gold Configurations", f"{len(gold['configurations'])} configurations evaluated")

scenario_ids = {item["id"] for item in scenarios["sequence"]}
gold_by_id = {item["id"]: item for item in gold["configurations"]}
for scenario in scenarios["sequence"]:
    if scenario["gold_configuration"] not in gold_by_id:
        fail(f"Scenario {scenario['id']} references missing Gold Configuration")
    expected_path = ROOT / scenario["expected_ir"]
    if not expected_path.exists():
        fail(f"Scenario {scenario['id']} references missing IR example {scenario['expected_ir']}")
for config in gold["configurations"]:
    if config["scenario_id"] not in scenario_ids:
        fail(f"Gold Configuration {config['id']} references missing scenario")
ok("Scenario Sequence", f"{len(scenario_ids)} linked scenarios")

component_ids = {item["id"] for item in architecture["components"]}
for component in architecture["components"]:
    unknown = set(component["realizes"]) - model_ids
    if unknown:
        fail(f"Component {component['id']} realizes unknown features {sorted(unknown)}")
for dependency in architecture["dependencies"]:
    if dependency["source"] not in component_ids or dependency["target"] not in component_ids:
        fail(f"Unknown component in dependency {dependency}")
for scenario_id, impact in architecture["expected_impacts"].items():
    if scenario_id not in scenario_ids:
        fail(f"Expected impact references unknown scenario {scenario_id}")
    for key in ("add_or_modify", "remove_or_disable", "preserve"):
        unknown = set(impact[key]) - component_ids
        if unknown:
            fail(f"Impact {scenario_id}/{key} has unknown components {sorted(unknown)}")
ok("Reference Architecture", f"{len(component_ids)} components and {len(architecture['dependencies'])} dependencies")

puml_paths = sorted((ROOT / "uml").glob("*.puml"))
for path in puml_paths:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("@startuml") or not text.rstrip().endswith("@enduml"):
        fail(f"Malformed PlantUML envelope in {path.name}")
if len(puml_paths) >= 5:
    ok("UML Assets", f"{len(puml_paths)} PlantUML models")
else:
    fail(f"Expected at least 5 UML models, found {len(puml_paths)}")

if mapping["pipeline"][0] != "natural_language" or mapping["pipeline"][-1] != "uml_projection":
    fail("Natural-language to UML mapping pipeline endpoints are invalid")
if len(mapping["round_trip_guards"]) < 5:
    fail("At least five round-trip guards are required")
ok("Natural Language UML Mapping", f"{len(mapping['rules'])} mappings and {len(mapping['round_trip_guards'])} guards")

with (ROOT / "backlog/mvp-backlog.csv").open(encoding="utf-8", newline="") as handle:
    backlog = list(csv.DictReader(handle))
if len(backlog) >= 20:
    ok("MVP Backlog", f"{len(backlog)} backlog items")
else:
    fail(f"MVP Backlog has only {len(backlog)} items")

status = "PASS" if not errors else "FAIL"
report_lines = [
    "# Sprint 0 Validation Report",
    "",
    f"Status: **{status}**",
    "",
    "## Checks",
    "",
]
for name, detail in checks:
    report_lines.append(f"- PASS: {name} - {detail}")
if errors:
    report_lines += ["", "## Errors", ""]
    report_lines.extend(f"- FAIL: {message}" for message in errors)
report_lines += [
    "",
    "## Gate",
    "",
    "이 보고서가 PASS일 때만 M1 Requirement IR Validator와 Solver Adapter 구현으로 진행한다.",
    "",
]
(ROOT / "VALIDATION_REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")

print(f"Sprint 0 validation: {status}")
for name, detail in checks:
    print(f"PASS {name}: {detail}")
for message in errors:
    print(f"FAIL {message}")
sys.exit(1 if errors else 0)
