from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
env = dict(os.environ)
env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), env.get("PYTHONPATH", "")])

commands = [
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    [
        sys.executable,
        "-m",
        "paispl_m3.cli",
        "generate-sequence",
        "--architecture-root",
        str(WORKSPACE / "paispl-m2" / "generated"),
        "--output",
        str(ROOT / "generated"),
    ],
]

records = []
status = "PASS"
for command in commands:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    records.append({
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    })
    if completed.returncode != 0:
        status = "FAIL"
        break

report = {"milestone": "M3", "status": status, "checks": records}
(ROOT / "QUALITY_GATE_REPORT.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"M3 quality gate: {status}")
for record in records:
    print(f"returncode={record['returncode']} command={' '.join(record['command'])}")
    if record["returncode"]:
        print(record["stdout"])
        print(record["stderr"])
raise SystemExit(0 if status == "PASS" else 1)

