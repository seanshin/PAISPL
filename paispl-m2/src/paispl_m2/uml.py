from __future__ import annotations

from pathlib import Path


def component_plantuml(result: dict) -> str:
    impact = result["impact"]
    add_or_modify = set(impact["add_or_modify"])
    remove_or_disable = set(impact["remove_or_disable"])
    lines = [
        "@startuml",
        "!pragma layout smetana",
        "skinparam componentStyle rectangle",
        f'title PAISPL Architecture Projection - {result["request_id"]}',
        "legend",
        "  <<changed>> added or modified",
        "  <<disabled>> capability removed or disabled",
        "endlegend",
    ]
    aliases: dict[str, str] = {}
    for index, component in enumerate(result["components"], start=1):
        alias = f"C{index}"
        aliases[component["id"]] = alias
        stereotype = ""
        if component["id"] in add_or_modify:
            stereotype = " <<changed>>"
        elif component["id"] in remove_or_disable:
            stereotype = " <<disabled>>"
        feature_ids = ",".join(component["feature_ids"])
        label = f'{component["name"]}\\ncomponentId={component["id"]}\\nfeatureIds={feature_ids}'
        lines.append(f'component "{label}" as {alias}{stereotype}')
    for dependency in result["dependencies"]:
        lines.append(
            f'{aliases[dependency["source"]]} --> {aliases[dependency["target"]]} : {dependency["kind"]}'
        )
    lines.extend([
        "note bottom",
        "Generated from Solver-validated configuration.\nDirect UML edits create a Change Proposal and require Solver revalidation.",
        "end note",
        "@enduml",
        "",
    ])
    return "\n".join(lines)


def write_component_plantuml(result: dict, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(component_plantuml(result), encoding="utf-8")
    return target

