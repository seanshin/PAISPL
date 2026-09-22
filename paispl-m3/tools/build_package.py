from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
TARGET = WORKSPACE / "PAISPL_M3_Incremental_Artifact_Factory_v0.3.0.zip"
INCLUDE_ROOTS = [
    ROOT,
    WORKSPACE / "paispl-m2",
    WORKSPACE / "paispl-m1",
    WORKSPACE / "paispl-sprint0",
]
EXCLUDED = {"__pycache__", ".pytest_cache", ".git"}

files = []
for source_root in INCLUDE_ROOTS:
    for path in source_root.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED for part in path.parts):
            continue
        files.append(path)

manifest = {
    "package": TARGET.name,
    "milestone": "M3",
    "version": "0.3.0",
    "contains": [
        "M3 incremental artifact factory",
        "M2 architecture synthesizer snapshot",
        "M1 solver snapshot",
        "Sprint 0 design snapshot",
    ],
    "file_count": len(files),
}
(ROOT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
if ROOT / "MANIFEST.json" not in files:
    files.append(ROOT / "MANIFEST.json")

with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, path.relative_to(WORKSPACE))

print(TARGET)
print(f"files={len(files)} size={TARGET.stat().st_size}")

