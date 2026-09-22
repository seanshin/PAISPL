# Start PAISPL with Codex CLI

## 1. Clone and enter the repository

```bash
git clone https://github.com/seanshin/PAISPL.git
cd PAISPL
```

The root must contain `AGENTS.md`, `tasks/`, and `paispl-sprint0` through
`paispl-m4`.

## 2. Verify the completed M4 checkpoint

```bash
python3 --version
python3 -c 'import yaml; print(yaml.__version__)'
python3 paispl-m4/tools/run_quality_gate.py
```

The quality gate must report M4 tests, all six examples, Sprint 0, M1–M3,
package integrity, and package reproducibility as passing. If `plantuml.jar` is
absent, PlantUML validation must be reported as `NOT_EXECUTED`.

## 3. Inspect M4 evidence

```bash
python3 -m json.tool paispl-m4/QUALITY_GATE_REPORT.json
python3 -m json.tool paispl-m4/generated/case-summary.json
shasum -a 256 PAISPL_M4_UML_Roundtrip_Controller_v0.4.0.zip
```

## 4. Run the controller

```bash
export PYTHONPATH=paispl-m4/src
python3 -m paispl_m4.cli preview-proposal \
  paispl-m4/examples/M4-CASE-001.proposal.json
```

Use the separate approval fixture and an explicit output path to exercise the
approved application case; see `README.md` or `paispl-m4/README.md`.

## 5. Continue development

`AGENTS.md` remains authoritative for repository invariants. M4 is the current
verified checkpoint. The next planned milestone is M5, but implementation must
not begin until an explicit M5 task specification is added and approved.
