#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT.parent / "paispl-sprint0"
env = dict(os.environ)
env["PYTHONPATH"] = str(ROOT / "src")

commands = [
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    [sys.executable, "-m", "paispl_m1.cli", "validate-ir", "--design-root", str(DESIGN), str(DESIGN / "examples/BASE-HOSP-001.requirement-ir.json")],
    [sys.executable, "-m", "paispl_m1.cli", "solve-sequence", "--design-root", str(DESIGN)],
]
results = []
for command in commands:
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    results.append({
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    })

status = "PASS" if all(item["returncode"] == 0 for item in results) else "FAIL"
report = {"status": status, "results": results}
(ROOT / "QUALITY_GATE_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"M1 quality gate: {status}")
for item in results:
    print(f"returncode={item['returncode']} command={' '.join(item['command'])}")
    if item["returncode"] != 0:
        print(item["stdout"])
        print(item["stderr"])
raise SystemExit(0 if status == "PASS" else 1)

