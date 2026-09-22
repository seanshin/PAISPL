from __future__ import annotations

import json
import zipfile
from pathlib import Path


OVERLAY = Path(__file__).resolve().parents[1]
WORKSPACE = OVERLAY.parent
TARGET = WORKSPACE / "PAISPL_CLI_Workspace_M4_Ready_v0.4.0.zip"
PROJECT_ROOTS = [
    WORKSPACE / "paispl-sprint0",
    WORKSPACE / "paispl-m1",
    WORKSPACE / "paispl-m2",
    WORKSPACE / "paispl-m3",
]
EXCLUDED = {"__pycache__", ".pytest_cache", ".git"}

entries: list[tuple[Path, Path]] = []
for path in OVERLAY.rglob("*"):
    if path.is_file() and path.name != "MANIFEST.json":
        entries.append((path, path.relative_to(OVERLAY)))
for project_root in PROJECT_ROOTS:
    for path in project_root.rglob("*"):
        if path.is_file() and not any(part in EXCLUDED for part in path.parts):
            entries.append((path, path.relative_to(WORKSPACE)))

manifest = {
    "package": TARGET.name,
    "purpose": "CLI-ready PAISPL workspace for M4",
    "version": "0.4.0-handoff",
    "project_state": "Sprint 0 through M3 completed; M4 specified",
    "file_count": len(entries) + 1,
}
(OVERLAY / "MANIFEST.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
)
entries.append((OVERLAY / "MANIFEST.json", Path("MANIFEST.json")))

with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for source, destination in sorted(entries, key=lambda item: str(item[1])):
        archive.write(source, destination)

print(TARGET)
print(f"files={len(entries)} size={TARGET.stat().st_size}")

