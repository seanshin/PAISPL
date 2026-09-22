from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
PACKAGE_NAME = "PAISPL_M4_UML_Roundtrip_Controller_v0.4.0.zip"
DEFAULT_TARGET = WORKSPACE / PACKAGE_NAME
INCLUDE_ROOTS = [
    ROOT,
    WORKSPACE / "paispl-m3",
    WORKSPACE / "paispl-m2",
    WORKSPACE / "paispl-m1",
    WORKSPACE / "paispl-sprint0",
]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".git", "dist"}


def included_files() -> list[Path]:
    files = []
    for source_root in INCLUDE_ROOTS:
        for path in source_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            if path.suffix in {".pyc", ".zip"} or path.name == ".DS_Store":
                continue
            files.append(path)
    return sorted(set(files), key=lambda item: item.relative_to(WORKSPACE).as_posix())


def write_manifest() -> None:
    provisional = [path for path in included_files() if path != ROOT / "MANIFEST.json"]
    manifest = {
        "package": PACKAGE_NAME,
        "milestone": "M4",
        "version": "0.4.0",
        "contains": [
            "M4 UML round-trip change controller and evidence",
            "M3 incremental artifact factory snapshot",
            "M2 architecture synthesizer snapshot",
            "M1 Requirement IR and Solver snapshot",
            "Sprint 0 design baseline snapshot",
        ],
        "file_count": len(provisional) + 1,
    }
    (ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_package(target: Path = DEFAULT_TARGET, write_sidecar: bool = True) -> dict:
    write_manifest()
    files = included_files()
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            relative = path.relative_to(WORKSPACE).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if write_sidecar:
        target.with_suffix(target.suffix + ".sha256").write_text(
            f"{digest}  {target.name}\n",
            encoding="utf-8",
        )
    with zipfile.ZipFile(target) as archive:
        corrupt = archive.testzip()
    if corrupt is not None:
        raise RuntimeError(f"ZIP integrity failure at {corrupt}")
    return {
        "package": target.name,
        "file_count": len(files),
        "size_bytes": target.stat().st_size,
        "sha256": digest,
        "integrity": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--no-sidecar", action="store_true")
    args = parser.parse_args()
    print(json.dumps(
        build_package(args.target, write_sidecar=not args.no_sidecar),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
