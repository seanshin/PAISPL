# PAISPL M2 — Architecture Synthesizer and Impact Closure

M2 consumes Solver-validated M1 configurations and produces an executable,
traceable architecture graph. UML is generated as a projection; it never
replaces the feature model or bypasses Solver validation.

## Pipeline

`Natural language -> Requirement IR -> Feature Solver -> Architecture Graph -> UML Projection`

An edit originating in UML follows the reverse control path:

`UML edit -> Change Proposal -> natural-language explanation -> Requirement IR -> Solver revalidation`

## Run

From this directory:

```bash
python3 tools/run_quality_gate.py
```

Direct sequence synthesis:

```bash
PYTHONPATH=src:../paispl-m1/src python3 -m paispl_m2.cli synthesize-sequence \
  --design-root ../paispl-sprint0 \
  --m1-root ../paispl-m1 \
  --output generated
```

The `generated` directory contains one JSON architecture graph and one
PlantUML component projection per scenario, plus the sequence summary.

