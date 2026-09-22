# PAISPL CLI Commands

Run commands from the extracted workspace root unless a section says otherwise.

## Environment check

```bash
python3 --version
java -version
```

Python 3.11 or later is required. Java is needed only for PlantUML rendering.
PyYAML must be available in the active Python environment.

## Milestone quality gates

```bash
python3 paispl-sprint0/tools/validate_sprint0.py
python3 paispl-m1/tools/run_quality_gate.py
python3 paispl-m2/tools/run_quality_gate.py
python3 paispl-m3/tools/run_quality_gate.py
python3 paispl-m4/tools/run_quality_gate.py
```

The M4 gate also runs Sprint 0 and M1–M3, all six M4 cases, package integrity,
and repeated-build reproducibility.

## Inspect generated results

```bash
python3 -m json.tool paispl-m2/generated/CHG-HOSP-003.architecture.json
python3 -m json.tool paispl-m3/generated/CHG-HOSP-003/change-plan.json
python3 -m json.tool paispl-m3/generated/CHG-HOSP-003/snapshot/trace/traceability.json
python3 -m json.tool paispl-m4/generated/case-summary.json
python3 -m json.tool paispl-m4/QUALITY_GATE_REPORT.json
```

## Run milestone tests directly

```bash
cd paispl-m1 && python3 -m unittest discover -s tests -v
cd ../paispl-m2 && python3 -m unittest discover -s tests -v
cd ../paispl-m3 && python3 -m unittest discover -s tests -v
cd ../paispl-m4 && PYTHONPATH=src python3 -m unittest discover -s tests -v
cd ..
```

## PlantUML validation

If `plantuml.jar` is present at the workspace root:

```bash
java -jar plantuml.jar -checkonly paispl-sprint0/uml/*.puml
java -jar plantuml.jar -checkonly paispl-m2/generated/*.puml
java -jar plantuml.jar -checkonly paispl-m3/generated/*/snapshot/uml/*.puml
java -jar plantuml.jar -checkonly paispl-m4/generated/uml/*.puml
```

Do not silently skip this check. Record `not executed` if the JAR is absent.

## M4 commands

Run from the workspace root:

```bash
python3 paispl-m4/tools/run_quality_gate.py
PYTHONPATH=paispl-m4/src python3 -m paispl_m4.cli validate-proposal PROPOSAL.json
PYTHONPATH=paispl-m4/src python3 -m paispl_m4.cli preview-proposal PROPOSAL.json
PYTHONPATH=paispl-m4/src python3 -m paispl_m4.cli approve-proposal PROPOSAL.json --approval APPROVAL.json --output OUTPUT_DIR
```

`preview-proposal` does not materialize files. `approve-proposal` requires a
separate, hash-bound approval record and an explicit output directory.

## Final verification

Run Sprint 0 and M1–M4 quality gates, verify ZIP integrity, and record the
SHA-256 digest of the completed M4 package.
