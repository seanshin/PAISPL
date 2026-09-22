from __future__ import annotations

from dataclasses import dataclass

from .generator import Artifact


@dataclass(frozen=True)
class IncrementalPlanner:
    deletion_policy: str = "manifest_owned_only"

    def plan(
        self,
        current: dict[str, Artifact],
        previous: dict[str, Artifact] | None,
        architecture: dict,
    ) -> dict:
        old = previous or {}
        create = sorted(set(current) - set(old))
        delete = sorted(set(old) - set(current))
        update = sorted(
            path for path in set(current).intersection(old)
            if current[path].sha256 != old[path].sha256
        )
        noop = sorted(
            path for path in set(current).intersection(old)
            if current[path].sha256 == old[path].sha256
        )
        changed_components = set(architecture["impact"]["add_or_modify"])
        disabled_components = set(architecture["impact"]["remove_or_disable"])
        changed_paths = set(create) | set(update) | set(delete)
        artifact_components = {
            artifact.owner_component_id
            for path, artifact in current.items()
            if path in changed_paths and artifact.owner_component_id
        }
        artifact_components.update(
            artifact.owner_component_id
            for path, artifact in old.items()
            if path in changed_paths and artifact.owner_component_id
        )
        review_only = sorted((changed_components | disabled_components) - artifact_components)
        return {
            "request_id": architecture["request_id"],
            "configuration_id": architecture["configuration_id"],
            "deletion_policy": self.deletion_policy,
            "operations": {
                "create": create,
                "update": update,
                "delete": delete,
                "no_op": noop,
            },
            "review_only_component_ids": review_only,
            "regression_test_ids": architecture["test_scope"],
            "summary": {
                "create": len(create),
                "update": len(update),
                "delete": len(delete),
                "no_op": len(noop),
                "review_only": len(review_only),
            },
        }
