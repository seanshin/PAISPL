#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT.parent / "paispl-sprint0"
OUT = ROOT.parent / "PAISPL_M1_Prototype_v0.1.0.zip"
MANIFEST = ROOT / "MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def eligible(root: Path):
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.name != "MANIFEST.json"
    )


code_files = eligible(ROOT)
design_files = eligible(DESIGN)
manifest = {
    "package": "PAISPL M1 Prototype",
    "version": "0.1.0",
    "built_at": datetime.now(timezone.utc).isoformat(),
    "quality_gate": "paispl-m1/QUALITY_GATE_REPORT.json",
    "entries": [
        {
            "archive_path": archive_path,
            "size": source.stat().st_size,
            "sha256": sha256(source),
        }
        for source, archive_path in [
            *((path, (Path("paispl-m1") / path.relative_to(ROOT)).as_posix()) for path in code_files),
            *((path, (Path("paispl-sprint0") / path.relative_to(DESIGN)).as_posix()) for path in design_files),
        ]
    ],
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in code_files:
        archive.write(path, (Path("paispl-m1") / path.relative_to(ROOT)).as_posix())
    archive.write(MANIFEST, "paispl-m1/MANIFEST.json")
    for path in design_files:
        archive.write(path, (Path("paispl-sprint0") / path.relative_to(DESIGN)).as_posix())

print(OUT)
print(f"code_files={len(code_files) + 1} design_files={len(design_files)} size={OUT.stat().st_size}")

