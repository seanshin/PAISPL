from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
PACKAGE = WORKSPACE / "PAISPL_M4_UML_Roundtrip_Controller_v0.4.0.zip"
REPORT = ROOT / "QUALITY_GATE_REPORT.json"
env = dict(os.environ)
env["PYTHONPATH"] = os.pathsep.join([
    str(ROOT / "src"),
    str(WORKSPACE / "paispl-m3" / "src"),
    str(WORKSPACE / "paispl-m2" / "src"),
    str(WORKSPACE / "paispl-m1" / "src"),
    env.get("PYTHONPATH", ""),
])


def execute(name: str, command: list[str]) -> tuple[dict, subprocess.CompletedProcess[str]]:
    completed = subprocess.run(
        command,
        cwd=WORKSPACE,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    record = {
        "name": name,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "returncode": completed.returncode,
    }
    if name == "M4 unit tests":
        match = re.search(r"Ran (\d+) tests", completed.stderr)
        record["test_count"] = int(match.group(1)) if match else None
    if completed.returncode != 0:
        record["stdout"] = completed.stdout
        record["stderr"] = completed.stderr
    return record, completed


def write_report(report: dict) -> None:
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


checks = []
commands = [
    (
        "M4 unit tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "paispl-m4/tests", "-v"],
    ),
    (
        "M4 required examples",
        [sys.executable, "-m", "paispl_m4.cli", "run-examples"],
    ),
    (
        "Sprint 0 validation",
        [sys.executable, "paispl-sprint0/tools/validate_sprint0.py"],
    ),
    (
        "M1 quality gate",
        [sys.executable, "paispl-m1/tools/run_quality_gate.py"],
    ),
    (
        "M2 quality gate",
        [sys.executable, "paispl-m2/tools/run_quality_gate.py"],
    ),
    (
        "M3 quality gate",
        [sys.executable, "paispl-m3/tools/run_quality_gate.py"],
    ),
]

for name, command in commands:
    record, completed = execute(name, command)
    checks.append(record)
    print(f"{name}: {record['status']}")
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        report = {
            "milestone": "M4",
            "version": "0.4.0",
            "status": "FAIL",
            "checks": checks,
            "plantuml": {"status": "NOT_EXECUTED", "reason": "earlier quality check failed"},
            "package": {"status": "NOT_EXECUTED"},
        }
        write_report(report)
        raise SystemExit(1)

plantuml_jar = WORKSPACE / "plantuml.jar"
uml_files = sorted(
    list((WORKSPACE / "paispl-sprint0" / "uml").glob("*.puml"))
    + list((WORKSPACE / "paispl-m2" / "generated").glob("*.puml"))
    + list((WORKSPACE / "paispl-m3" / "generated").glob("*/snapshot/uml/*.puml"))
    + list((ROOT / "generated" / "uml").glob("*.puml"))
)
if plantuml_jar.is_file():
    command = ["java", "-jar", str(plantuml_jar), "-checkonly", *map(str, uml_files)]
    plantuml_record, completed = execute("PlantUML syntax validation", command)
    plantuml = {
        "status": plantuml_record["status"],
        "file_count": len(uml_files),
    }
    if completed.returncode != 0:
        plantuml["stderr"] = completed.stderr
else:
    plantuml = {
        "status": "NOT_EXECUTED",
        "file_count": len(uml_files),
        "reason": "plantuml.jar is absent",
    }

case_summary = json.loads(
    (ROOT / "generated/case-summary.json").read_text(encoding="utf-8")
)
report = {
    "milestone": "M4",
    "version": "0.4.0",
    "status": "PASS" if plantuml["status"] in {"PASS", "NOT_EXECUTED"} else "FAIL",
    "checks": checks,
    "required_cases": case_summary,
    "plantuml": plantuml,
    "package": {
        "status": "PENDING",
        "integrity": "PENDING",
        "reproducible": "PENDING",
        "target": PACKAGE.name,
        "sha256_sidecar": PACKAGE.name + ".sha256",
    },
}
write_report(report)

build_script = ROOT / "tools/build_package.py"
with tempfile.TemporaryDirectory() as directory:
    first = Path(directory) / "first.zip"
    second = Path(directory) / "second.zip"
    for target in (first, second):
        completed = subprocess.run(
            [sys.executable, str(build_script), "--target", str(target), "--no-sidecar"],
            cwd=WORKSPACE,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            print(completed.stdout)
            print(completed.stderr)
            raise SystemExit(completed.returncode)
    first_hash = hashlib.sha256(first.read_bytes()).hexdigest()
    second_hash = hashlib.sha256(second.read_bytes()).hexdigest()
    if first_hash != second_hash:
        raise SystemExit("reproducible ZIP check failed")
    with zipfile.ZipFile(first) as archive:
        if archive.testzip() is not None:
            raise SystemExit("ZIP integrity check failed")

report["package"].update({
    "status": "PASS",
    "integrity": "PASS",
    "reproducible": "PASS",
})
write_report(report)

final_hashes = []
for _ in range(2):
    completed = subprocess.run(
        [sys.executable, str(build_script), "--target", str(PACKAGE)],
        cwd=WORKSPACE,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        raise SystemExit(completed.returncode)
    final_hashes.append(hashlib.sha256(PACKAGE.read_bytes()).hexdigest())
if final_hashes[0] != final_hashes[1]:
    raise SystemExit("final reproducible ZIP check failed")
with zipfile.ZipFile(PACKAGE) as archive:
    if archive.testzip() is not None:
        raise SystemExit("final ZIP integrity check failed")

print("M4 quality gate: " + report["status"])
print(f"M4 tests: {checks[0].get('test_count')} passed")
print(f"Required cases: {len(case_summary['cases'])} passed")
print(f"PlantUML: {plantuml['status']}")
print(f"Package integrity: PASS")
print(f"Package reproducibility: PASS")
print(f"Package SHA-256: {final_hashes[-1]}")
raise SystemExit(0 if report["status"] == "PASS" else 1)
