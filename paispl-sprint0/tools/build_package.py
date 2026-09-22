#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "PAISPL_Sprint0_Design_Package_v0.1.0.zip"
MANIFEST = ROOT / "MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


files = sorted(
    path for path in ROOT.rglob("*")
    if path.is_file()
    and path != MANIFEST
    and "__pycache__" not in path.parts
)
manifest = {
    "package": "PAISPL Sprint 0 Design Package",
    "version": "0.1.0",
    "built_at": datetime.now(timezone.utc).isoformat(),
    "validation_report": "VALIDATION_REPORT.md",
    "files": [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in files
    ],
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted([*files, MANIFEST]):
        archive.write(path, arcname=(Path("paispl-sprint0") / path.relative_to(ROOT)).as_posix())

print(OUT)
print(f"files={len(files) + 1} size={OUT.stat().st_size}")

