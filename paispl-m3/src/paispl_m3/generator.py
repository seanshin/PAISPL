from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Artifact:
    path: str
    kind: str
    content: str
    owner_component_id: str | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def manifest_entry(self) -> dict:
        return {
            "path": self.path,
            "kind": self.kind,
            "owner_component_id": self.owner_component_id,
            "sha256": self.sha256,
            "size_bytes": len(self.content.encode("utf-8")),
        }


def _slug(component_id: str) -> str:
    value = component_id.removeprefix("CMP-").lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _yaml(value: dict) -> str:
    return "# generated-by: paispl.generated/v1\n" + yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


class ArtifactGenerator:
    def __init__(self, policy: dict):
        self.policy = policy
        self.marker = policy["ownership_marker"]

    @classmethod
    def load(cls, policy_path: str | Path) -> "ArtifactGenerator":
        return cls(yaml.safe_load(Path(policy_path).read_text(encoding="utf-8")))

    def generate(self, architecture: dict) -> dict[str, Artifact]:
        artifacts: dict[str, Artifact] = {}
        dependencies_by_source: dict[str, list[dict]] = {}
        for dependency in architecture["dependencies"]:
            dependencies_by_source.setdefault(dependency["source"], []).append(dependency)

        for component in architecture["components"]:
            component_id = component["id"]
            slug = _slug(component_id)
            dependencies = sorted(
                dependencies_by_source.get(component_id, []),
                key=lambda item: (item["target"], item["kind"]),
            )
            descriptor = {
                "apiVersion": "paispl.openai.com/v1alpha1",
                "kind": "GeneratedComponent",
                "metadata": {"id": component_id, "name": slug, "generator": self.marker},
                "spec": {
                    "componentType": component["type"],
                    "featureIds": component["feature_ids"],
                    "interfaceIds": component["interfaces"],
                    "dependencies": dependencies,
                },
            }
            self._add(
                artifacts,
                Artifact(
                    path=f"components/{slug}/component.yaml",
                    kind="component_descriptor",
                    owner_component_id=component_id,
                    content=_yaml(descriptor),
                ),
            )

            if component["type"] == "infrastructure":
                profile = {
                    "apiVersion": "paispl.openai.com/v1alpha1",
                    "kind": "DeploymentProfile",
                    "metadata": {"componentId": component_id, "generator": self.marker},
                    "spec": {"featureIds": component["feature_ids"]},
                }
                self._add(
                    artifacts,
                    Artifact(
                        path="deploy/profile.yaml",
                        kind="deployment_profile",
                        owner_component_id=component_id,
                        content=_yaml(profile),
                    ),
                )
            else:
                self._add(
                    artifacts,
                    Artifact(
                        path=f"components/{slug}/app.py",
                        kind="code_scaffold",
                        owner_component_id=component_id,
                        content=self._app_py(component),
                    ),
                )
                self._add(
                    artifacts,
                    Artifact(
                        path=f"deploy/k8s/{slug}.yaml",
                        kind="kubernetes_manifest",
                        owner_component_id=component_id,
                        content=self._kubernetes(component, slug),
                    ),
                )

        for interface in architecture["interfaces"]:
            interface_id = interface["id"]
            owner = interface["owner_component_id"]
            protocol = self._protocol(interface_id)
            contract = {
                "_generator": self.marker,
                "contractVersion": "0.3.0",
                "id": interface_id,
                "ownerComponentId": owner,
                "protocolFamily": protocol,
                "featureIds": interface["feature_ids"],
                "implementationStatus": "stub_requires_domain_contract",
            }
            self._add(
                artifacts,
                Artifact(
                    path=f"contracts/{interface_id.lower()}.json",
                    kind="interface_contract",
                    owner_component_id=owner,
                    content=json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                ),
            )

        self._add(
            artifacts,
            Artifact(
                path="uml/deployment.puml",
                kind="uml_projection",
                content=self._deployment_uml(architecture, artifacts),
            ),
        )
        trace = self._traceability(architecture, artifacts)
        self._add(
            artifacts,
            Artifact(
                path="trace/traceability.json",
                kind="traceability_manifest",
                content=json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            ),
        )
        return dict(sorted(artifacts.items()))

    def materialize(self, artifacts: dict[str, Artifact], output_root: str | Path) -> list[dict]:
        root = Path(output_root)
        manifest = []
        for path, artifact in sorted(artifacts.items()):
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(artifact.content, encoding="utf-8")
            manifest.append(artifact.manifest_entry())
        return manifest

    def _add(self, artifacts: dict[str, Artifact], artifact: Artifact) -> None:
        if artifact.path in artifacts:
            raise ValueError(f"duplicate generated path: {artifact.path}")
        if artifact.path.startswith("/") or ".." in Path(artifact.path).parts:
            raise ValueError(f"unsafe generated path: {artifact.path}")
        artifacts[artifact.path] = artifact

    def _app_py(self, component: dict) -> str:
        metadata = {
            "component_id": component["id"],
            "component_name": component["name"],
            "component_type": component["type"],
            "feature_ids": component["feature_ids"],
            "interface_ids": component["interfaces"],
        }
        encoded = json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True)
        return f'''"""Generated by {self.marker}; regenerate instead of editing this file."""\n\nimport json\nfrom http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\n\nCOMPONENT = {encoded}\n\n\nclass Handler(BaseHTTPRequestHandler):\n    def do_GET(self):\n        if self.path not in {{"/health", "/metadata"}}:\n            self.send_error(404)\n            return\n        payload = {{"status": "ok"}} if self.path == "/health" else COMPONENT\n        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")\n        self.send_response(200)\n        self.send_header("Content-Type", "application/json; charset=utf-8")\n        self.send_header("Content-Length", str(len(body)))\n        self.end_headers()\n        self.wfile.write(body)\n\n\nif __name__ == "__main__":\n    ThreadingHTTPServer(("0.0.0.0", {int(self.policy["runtime_port"])}), Handler).serve_forever()\n'''

    def _kubernetes(self, component: dict, slug: str) -> str:
        labels = {"app.kubernetes.io/name": slug, "paispl/component-id": component["id"]}
        value = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": slug, "labels": labels},
            "spec": {
                "replicas": int(self.policy["replicas"]),
                "selector": {"matchLabels": {"app.kubernetes.io/name": slug}},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "containers": [{
                            "name": slug,
                            "image": f'{self.policy["container_registry"]}/{slug}:{self.policy["container_tag"]}',
                            "ports": [{"name": "http", "containerPort": int(self.policy["runtime_port"])}],
                            "readinessProbe": {"httpGet": {"path": "/health", "port": "http"}},
                        }]
                    },
                },
            },
        }
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": slug, "labels": labels},
            "spec": {
                "selector": {"app.kubernetes.io/name": slug},
                "ports": [{"name": "http", "port": int(self.policy["runtime_port"]), "targetPort": "http"}],
            },
        }
        return _yaml(value) + "---\n" + yaml.safe_dump(service, sort_keys=False)

    def _traceability(self, architecture: dict, artifacts: dict[str, Artifact]) -> dict:
        paths_by_component: dict[str, list[str]] = {}
        for artifact in artifacts.values():
            if artifact.owner_component_id:
                paths_by_component.setdefault(artifact.owner_component_id, []).append(artifact.path)
        links = []
        for link in architecture["trace_links"]:
            component_id = link.get("component_id")
            links.append({
                "intentId": link["intent_id"],
                "operation": link["operation"],
                "sourceQuote": link.get("source_quote", ""),
                "featureId": link["feature_id"],
                "componentId": component_id,
                "interfaceIds": link.get("interface_ids", []),
                "testIds": link.get("test_ids", []),
                "artifactPaths": sorted(paths_by_component.get(component_id, [])),
            })
        return {
            "_generator": self.marker,
            "configurationId": architecture["configuration_id"],
            "requestId": architecture["request_id"],
            "links": links,
        }

    def _deployment_uml(self, architecture: dict, artifacts: dict[str, Artifact]) -> str:
        deploy_path_by_component = {
            artifact.owner_component_id: path
            for path, artifact in artifacts.items()
            if artifact.kind in {"kubernetes_manifest", "deployment_profile"}
            and artifact.owner_component_id
        }
        aliases: dict[str, str] = {}
        lines = [
            "@startuml",
            "!pragma layout smetana",
            f'title PAISPL Generated Deployment - {architecture["request_id"]}',
            'node "Generated Runtime" {',
        ]
        for index, component in enumerate(architecture["components"], start=1):
            component_id = component["id"]
            path = deploy_path_by_component.get(component_id)
            if not path:
                continue
            alias = f"A{index}"
            aliases[component_id] = alias
            feature_ids = ",".join(component["feature_ids"])
            label = f'{component_id}\\nfeatureIds={feature_ids}\\nartifactPath={path}'
            lines.append(f'  artifact "{label}" as {alias}')
        lines.append("}")
        for dependency in architecture["dependencies"]:
            source = aliases.get(dependency["source"])
            target = aliases.get(dependency["target"])
            if source and target:
                lines.append(f'{source} --> {target} : {dependency["kind"]}')
        lines.extend([
            "note bottom",
            f"Generated by {self.marker}.\\nUML is a projection; edits require Requirement IR and Solver revalidation.",
            "end note",
            "@enduml",
            "",
        ])
        return "\n".join(lines)

    @staticmethod
    def _protocol(interface_id: str) -> str:
        if interface_id.startswith("EVT-"):
            return "event"
        if interface_id.startswith("API-"):
            return "http_or_domain_api"
        if interface_id.startswith("OTEL-"):
            return "telemetry"
        if interface_id.startswith("DEPLOY-"):
            return "deployment"
        return "unspecified"
