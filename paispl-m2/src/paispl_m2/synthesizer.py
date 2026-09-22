from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import yaml


@dataclass(frozen=True)
class SynthesisResult:
    configuration_id: str
    request_id: str
    components: tuple[dict, ...]
    dependencies: tuple[dict, ...]
    interfaces: tuple[dict, ...]
    component_delta: dict
    impact: dict
    test_scope: tuple[str, ...]
    trace_links: tuple[dict, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class ArchitectureSynthesizer:
    def __init__(self, reference: dict, policy: dict, acceptance_tests: list[dict]):
        self.reference = reference
        self.policy = policy
        self.acceptance_tests = acceptance_tests
        self.components = {item["id"]: item for item in reference["components"]}
        self.feature_to_components: dict[str, set[str]] = {}
        for component in reference["components"]:
            for feature_id in component.get("realizes", []):
                self.feature_to_components.setdefault(feature_id, set()).add(component["id"])

    @classmethod
    def load(
        cls,
        architecture_path: str | Path,
        policy_path: str | Path,
        acceptance_tests_path: str | Path,
    ) -> "ArchitectureSynthesizer":
        reference = yaml.safe_load(Path(architecture_path).read_text(encoding="utf-8"))
        policy = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
        tests = yaml.safe_load(Path(acceptance_tests_path).read_text(encoding="utf-8"))["tests"]
        return cls(reference, policy, tests)

    def synthesize(
        self,
        request_id: str,
        configuration_id: str,
        selected: Iterable[str],
        added: Iterable[str],
        removed: Iterable[str],
        intent_links: Iterable[dict],
        previous_selected: Iterable[str] | None = None,
    ) -> SynthesisResult:
        current = set(selected)
        previous = set(previous_selected or [])
        added_set = set(added)
        removed_set = set(removed)
        active = self._active_components(current)
        previous_active = self._active_components(previous)
        component_delta = self._component_delta(active, previous_active)
        impact = self._impact(component_delta, added_set, removed_set, active)
        dependencies = tuple(
            dict(item)
            for item in self.reference["dependencies"]
            if item["source"] in active and item["target"] in active
        )
        components = tuple(self._component_projection(cid, current) for cid in sorted(active))
        interfaces = tuple(
            {
                "id": interface_id,
                "owner_component_id": component["id"],
                "feature_ids": list(component["feature_ids"]),
            }
            for component in sorted(components, key=lambda item: item["id"])
            for interface_id in component["interfaces"]
        )
        test_scope = self._test_scope(added_set, removed_set, impact)
        trace_links = self._trace_links(intent_links, active, interfaces, test_scope)
        return SynthesisResult(
            configuration_id=configuration_id,
            request_id=request_id,
            components=components,
            dependencies=dependencies,
            interfaces=interfaces,
            component_delta=component_delta,
            impact=impact,
            test_scope=tuple(sorted(test_scope)),
            trace_links=tuple(trace_links),
        )

    def _active_components(self, selected: set[str]) -> set[str]:
        return {
            component["id"]
            for component in self.reference["components"]
            if selected.intersection(component.get("realizes", []))
        }

    def _component_projection(self, component_id: str, selected: set[str]) -> dict:
        source = self.components[component_id]
        return {
            "id": component_id,
            "name": source["name"],
            "type": source["type"],
            "feature_ids": sorted(selected.intersection(source.get("realizes", []))),
            "interfaces": list(source.get("interfaces", [])),
        }

    def _component_delta(self, active: set[str], previous_active: set[str]) -> dict:
        added_components = active - previous_active
        removed_components = previous_active - active
        return {
            "added": sorted(added_components),
            "removed": sorted(removed_components),
            "preserved": sorted(active.intersection(previous_active)),
        }

    def _impact(
        self,
        component_delta: dict,
        added_features: set[str],
        removed_features: set[str],
        active: set[str],
    ) -> dict:
        added_components = set(component_delta["added"])
        add_or_modify: set[str] = set(added_components)
        remove_or_disable: set[str] = set(component_delta["removed"])
        reasons: dict[str, list[str]] = {}

        def mark(target: str, reason: str, bucket: set[str]) -> None:
            bucket.add(target)
            reasons.setdefault(target, []).append(reason)

        for feature_id in sorted(added_features):
            for component_id in sorted(self.feature_to_components.get(feature_id, set())):
                mark(component_id, f"feature_added:{feature_id}", add_or_modify)
            for component_id in self.policy.get("feature_propagation", {}).get(feature_id, []):
                if component_id in active:
                    mark(component_id, f"semantic_coupling:{feature_id}", add_or_modify)

        for feature_id in sorted(removed_features):
            owners = self.feature_to_components.get(feature_id, set())
            for component_id in sorted(owners):
                if component_id not in add_or_modify:
                    mark(component_id, f"feature_removed:{feature_id}", remove_or_disable)

        allowed_kinds = set(self.policy.get("activation_dependency_kinds", []))
        for dependency in self.reference["dependencies"]:
            if (
                dependency["source"] in added_components
                and dependency["target"] in active
                and dependency["kind"] in allowed_kinds
            ):
                mark(
                    dependency["target"],
                    f"new_dependency:{dependency['source']}:{dependency['kind']}",
                    add_or_modify,
                )

        remove_or_disable.difference_update(add_or_modify)
        impacted = add_or_modify | remove_or_disable
        return {
            "add_or_modify": sorted(add_or_modify),
            "remove_or_disable": sorted(remove_or_disable),
            "preserve": sorted(active - impacted),
            "reasons": {key: sorted(set(value)) for key, value in sorted(reasons.items())},
        }

    def _test_scope(self, added: set[str], removed: set[str], impact: dict) -> set[str]:
        changed = added | removed
        selected_tests = {
            test["id"]
            for test in self.acceptance_tests
            if changed.intersection(test.get("feature_ids", []))
        }
        selected_tests.update(self.policy.get("always_include_tests", []))
        impacted_components = set(impact["add_or_modify"]) | set(impact["remove_or_disable"])
        impacted_features = {
            feature_id
            for component_id in impacted_components
            for feature_id in self.components[component_id].get("realizes", [])
        }
        selected_tests.update(
            test["id"]
            for test in self.acceptance_tests
            if impacted_features.intersection(test.get("feature_ids", []))
        )
        return selected_tests

    def _trace_links(
        self,
        intent_links: Iterable[dict],
        active: set[str],
        interfaces: tuple[dict, ...],
        test_scope: set[str],
    ) -> list[dict]:
        interface_by_component: dict[str, list[str]] = {}
        for interface in interfaces:
            interface_by_component.setdefault(interface["owner_component_id"], []).append(interface["id"])
        tests_by_feature: dict[str, list[str]] = {}
        for test in self.acceptance_tests:
            if test["id"] not in test_scope:
                continue
            for feature_id in test.get("feature_ids", []):
                tests_by_feature.setdefault(feature_id, []).append(test["id"])

        output: list[dict] = []
        for link in intent_links:
            feature_id = link["feature_id"]
            owners = sorted(self.feature_to_components.get(feature_id, set()))
            if not owners:
                output.append({**link, "component_id": None, "interface_ids": [], "test_ids": []})
                continue
            for component_id in owners:
                output.append({
                    **link,
                    "component_id": component_id,
                    "component_active": component_id in active,
                    "interface_ids": sorted(interface_by_component.get(component_id, [])),
                    "test_ids": sorted(tests_by_feature.get(feature_id, [])),
                })
        return output
