from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from .feature_model import FeatureModel


class UnsatisfiableConfiguration(ValueError):
    def __init__(self, findings: list[str]):
        super().__init__("Configuration is unsatisfiable")
        self.findings = findings


@dataclass(frozen=True)
class SolveResult:
    configuration_id: str
    selected: tuple[str, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]
    explicit_selected: tuple[str, ...]
    explicit_excluded: tuple[str, ...]
    derived: tuple[str, ...]
    trace_links: tuple[dict, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class ConfigurationEngine:
    def __init__(self, model: FeatureModel, policy: dict):
        self.model = model
        self.policy = policy
        self.minimum_confidence = float(policy.get("minimum_intent_confidence", 0.75))

    @classmethod
    def load(cls, model_path: str | Path, policy_path: str | Path) -> "ConfigurationEngine":
        model = FeatureModel.load(model_path)
        policy = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
        return cls(model, policy)

    def solve(self, ir: dict, base_selected: set[str] | None = None) -> SolveResult:
        base = set(base_selected or [])
        selected = set(base) if base else {self.model.root}
        selected.add(self.model.root)
        explicit_selected: set[str] = set()
        explicit_excluded: set[str] = set()
        trace_links: list[dict] = []

        for feature in self.policy.get("default_features", []):
            selected.add(feature)

        for intent in ir["intents"]:
            if intent["confidence"] < self.minimum_confidence:
                raise UnsatisfiableConfiguration([f"{intent['id']} confidence is below threshold"])
            candidate = max(intent["feature_candidates"], key=lambda item: item["score"])
            feature = candidate["feature_id"]
            if feature not in self.model.features:
                raise UnsatisfiableConfiguration([f"{intent['id']} references unknown feature {feature}"])
            operation = intent["operation"]
            if operation in {"include", "prefer"}:
                selected.add(feature)
                explicit_selected.add(feature)
            elif operation == "exclude":
                selected.discard(feature)
                explicit_excluded.add(feature)
            elif operation == "replace":
                self._select_group_member(selected, explicit_excluded, feature)
                explicit_selected.add(feature)
            elif operation == "preserve" and feature in base:
                selected.add(feature)
                explicit_selected.add(feature)
            trace_links.append({
                "intent_id": intent["id"],
                "feature_id": feature,
                "operation": operation,
                "source_quote": intent["source_quote"],
            })

        deployment_map = {
            "cloud": "cloud_deployment",
            "on_premise": "on_premise_deployment",
            "hybrid": "hybrid_deployment",
        }
        runtime_map = {"docker_compose": "docker_compose", "kubernetes": "kubernetes"}
        profile = ir["deployment"]["profile"]
        runtime = ir["deployment"]["runtime"]
        if profile != "unchanged":
            feature = deployment_map[profile]
            self._select_group_member(selected, explicit_excluded, feature)
            explicit_selected.add(feature)
        if runtime != "unchanged":
            feature = runtime_map[runtime]
            self._select_group_member(selected, explicit_excluded, feature)
            explicit_selected.add(feature)

        for feature in explicit_excluded:
            selected.discard(feature)

        self._close_configuration(selected, explicit_selected, explicit_excluded)
        findings = self.model.findings(selected)
        if findings:
            raise UnsatisfiableConfiguration(findings)

        added = selected - base
        removed = base - selected
        derived = selected - explicit_selected - base
        config_id = f"CFG-{ir['request_id']}"
        return SolveResult(
            configuration_id=config_id,
            selected=tuple(sorted(selected)),
            added=tuple(sorted(added)),
            removed=tuple(sorted(removed)),
            explicit_selected=tuple(sorted(explicit_selected)),
            explicit_excluded=tuple(sorted(explicit_excluded)),
            derived=tuple(sorted(derived)),
            trace_links=tuple(trace_links),
        )

    def _select_group_member(self, selected: set[str], excluded: set[str], feature: str):
        group_id = self.model.member_to_group.get(feature)
        if group_id:
            group = self.model.groups[group_id]
            for sibling in group.members:
                if sibling != feature:
                    selected.discard(sibling)
                    excluded.add(sibling)
        selected.add(feature)
        excluded.discard(feature)

    def _close_configuration(self, selected: set[str], explicit_selected: set[str], excluded: set[str]):
        for _ in range(100):
            before = set(selected)
            selected.difference_update(excluded)
            self._add_parents_and_mandatory(selected, excluded)
            self._apply_requires(selected, explicit_selected, excluded)
            self._apply_excludes(selected, explicit_selected, excluded)
            self._fill_groups(selected, excluded)
            if selected == before:
                return
        raise RuntimeError("Feature propagation did not converge")

    def _add_parents_and_mandatory(self, selected: set[str], excluded: set[str]):
        for feature_id in list(selected):
            parent = self.model.features[feature_id].get("parent")
            if parent:
                if parent in excluded:
                    raise UnsatisfiableConfiguration([f"{feature_id} requires excluded parent {parent}"])
                selected.add(parent)
        for feature in self.model.features.values():
            if feature["kind"] == "mandatory" and feature.get("parent") in selected:
                if feature["id"] in excluded:
                    raise UnsatisfiableConfiguration([f"mandatory feature {feature['id']} is excluded"])
                selected.add(feature["id"])

    def _apply_requires(self, selected: set[str], explicit_selected: set[str], excluded: set[str]):
        for constraint in self.model.constraints:
            if constraint.type == "requires" and constraint.source in selected:
                if constraint.target in excluded:
                    raise UnsatisfiableConfiguration([
                        f"{constraint.source} requires explicitly excluded {constraint.target}"
                    ])
                selected.add(constraint.target)

    def _apply_excludes(self, selected: set[str], explicit_selected: set[str], excluded: set[str]):
        for constraint in self.model.constraints:
            if constraint.type != "excludes":
                continue
            if constraint.source in selected and constraint.target in selected:
                if constraint.source in explicit_selected and constraint.target in explicit_selected:
                    raise UnsatisfiableConfiguration([
                        f"explicit selections conflict: {constraint.source} excludes {constraint.target}"
                    ])
                selected.discard(constraint.target)
                excluded.add(constraint.target)

    def _fill_groups(self, selected: set[str], excluded: set[str]):
        conditional = {
            item["group"]: item["member"]
            for item in self.policy.get("conditional_group_defaults", [])
            if item["when_selected"] in selected
        }
        defaults = self.policy.get("group_defaults", {})
        for group in self.model.groups.values():
            if group.parent not in selected:
                selected.difference_update(group.members)
                continue
            active = selected.intersection(group.members)
            if len(active) > group.maximum:
                raise UnsatisfiableConfiguration([f"group {group.id} has too many selections: {sorted(active)}"])
            if len(active) < group.minimum:
                member = conditional.get(group.id, defaults.get(group.id))
                if member not in group.members or member in excluded:
                    alternatives = [item for item in group.members if item not in excluded]
                    if not alternatives:
                        raise UnsatisfiableConfiguration([f"group {group.id} has no available member"])
                    member = alternatives[0]
                selected.add(member)

