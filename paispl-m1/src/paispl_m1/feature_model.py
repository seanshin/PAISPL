from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Group:
    id: str
    parent: str
    minimum: int
    maximum: int
    members: tuple[str, ...]


@dataclass(frozen=True)
class Constraint:
    id: str
    type: str
    source: str
    target: str


class FeatureModel:
    def __init__(self, raw: dict):
        self.raw = raw
        self.root = raw["root"]
        self.features = {item["id"]: item for item in raw["features"]}
        self.groups = {
            item["id"]: Group(
                id=item["id"],
                parent=item["parent"],
                minimum=item["cardinality"]["min"],
                maximum=item["cardinality"]["max"],
                members=tuple(item["members"]),
            )
            for item in raw["groups"]
        }
        self.constraints = tuple(Constraint(**item) for item in raw["constraints"])
        self.member_to_group = {
            member: group.id
            for group in self.groups.values()
            for member in group.members
        }
        self._validate_structure()

    @classmethod
    def load(cls, path: str | Path) -> "FeatureModel":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(raw)

    def _validate_structure(self):
        ids = set(self.features)
        if self.root not in ids:
            raise ValueError("Root feature does not exist")
        for feature in self.features.values():
            parent = feature.get("parent")
            if parent and parent not in ids:
                raise ValueError(f"Unknown parent {parent}")
        for group in self.groups.values():
            if group.parent not in ids or not set(group.members) <= ids:
                raise ValueError(f"Invalid group {group.id}")
        for constraint in self.constraints:
            if constraint.source not in ids or constraint.target not in ids:
                raise ValueError(f"Invalid constraint {constraint.id}")

    def findings(self, selected: set[str]) -> list[str]:
        findings: list[str] = []
        unknown = selected - set(self.features)
        if unknown:
            findings.append(f"unknown features: {sorted(unknown)}")
        if self.root not in selected:
            findings.append(f"root {self.root} is missing")
        for feature in self.features.values():
            fid = feature["id"]
            parent = feature.get("parent")
            if fid in selected and parent and parent not in selected:
                findings.append(f"{fid} selected without parent {parent}")
            if feature["kind"] == "mandatory" and parent in selected and fid not in selected:
                findings.append(f"mandatory feature {fid} is missing")
        for group in self.groups.values():
            count = len(selected.intersection(group.members))
            minimum = group.minimum if group.parent in selected else 0
            maximum = group.maximum if group.parent in selected else 0
            if not minimum <= count <= maximum:
                findings.append(f"group {group.id} has {count}, expected {minimum}..{maximum}")
        for constraint in self.constraints:
            if constraint.type == "requires" and constraint.source in selected and constraint.target not in selected:
                findings.append(f"{constraint.source} requires {constraint.target}")
            if constraint.type == "excludes" and constraint.source in selected and constraint.target in selected:
                findings.append(f"{constraint.source} excludes {constraint.target}")
        return findings

