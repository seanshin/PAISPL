# PAISPL M3 — Incremental Artifact Factory

M3 converts M2 Solver-validated architecture graphs into deterministic code,
contract, Kubernetes, traceability, and UML artifacts. It also compares
successive variants and emits a minimal change plan.

## Safety and authority model

- Feature Model and Solver remain the validity authority.
- Architecture Graph is the structural authority.
- UML is a generated review projection.
- Generated files are manifest-owned and carry `paispl.generated/v1`.
- Deletion is permitted only for paths owned by the previous manifest.
- Semantically impacted but byte-identical components become `review-only`.
- Interface contracts are explicit stubs until domain schemas are supplied.

## Run

```bash
python3 tools/run_quality_gate.py
```

Direct generation:

```bash
PYTHONPATH=src python3 -m paispl_m3.cli generate-sequence \
  --architecture-root ../paispl-m2/generated \
  --output generated
```

Each scenario contains a complete snapshot, content-addressed artifact
manifest, and `create/update/delete/no-op` change plan.

