# PAISPL

PAISPL (Prompt-driven AI Software Product Line) is a reproducible research
prototype for translating natural-language product requirements into
Solver-validated configurations, architecture projections, and deterministic
generated artifacts.

The repository currently contains the completed Sprint 0 through M4 pipeline.
M4 adds a controlled UML round trip: a UML edit can only create a Change
Proposal. It cannot mutate Feature configuration, architecture, code, or
deployment artifacts without Requirement IR translation, Solver validation,
impact preview, and a separately bound approval record.

## Authority model

```text
Approved natural-language intent
  -> Requirement IR
  -> Feature Model + Solver-validated configuration
  -> Architecture Graph
  -> generated UML projection
  -> generated code and deployment artifacts
```

Reverse UML flow:

```text
UML edit
  -> Change Proposal
  -> Korean semantic explanation
  -> Requirement IR delta
  -> Solver revalidation
  -> architecture and artifact preview
  -> explicit approval
  -> deterministic application
```

UML is a review projection, not a second source of truth.

## Milestones

| Milestone | Scope | Status |
|---|---|---|
| Sprint 0 | Healthcare Feature Model, Gold scenarios, UML and trace rules | Complete |
| M1 | Requirement IR validation and Feature Solver | Complete |
| M2 | Architecture synthesis, impact closure, component UML | Complete |
| M3 | Incremental code, contract, deployment, trace and UML generation | Complete |
| M4 | UML round-trip Change Controller and approval gate | Complete |
| M5 | Natural-language intent compiler and ambiguity calibration | Next |

## Repository layout

```text
paispl-sprint0/  Design baseline and healthcare domain pack
paispl-m1/       Requirement IR validator and configuration Solver
paispl-m2/       Architecture synthesizer and impact analysis
paispl-m3/       Incremental Artifact Factory
paispl-m4/       UML round-trip Change Controller
docs/            Handoff and command reference
tasks/           Milestone specifications
```

## Requirements

- Python 3.11 or later
- PyYAML 6.0 or later
- Java and `plantuml.jar` at the repository root only when PlantUML syntax
  validation is required

No application framework or external service is required for the verified CLI
pipeline.

## Quick start

```bash
git clone https://github.com/seanshin/PAISPL.git
cd PAISPL
python3 --version
python3 -c 'import yaml; print(yaml.__version__)'
python3 paispl-m4/tools/run_quality_gate.py
```

The M4 quality gate runs 20 controller tests, all six required M4 cases, the
Sprint 0 validator, M1–M3 regression gates, ZIP integrity, and repeated-build
reproducibility. PlantUML validation is recorded as `NOT_EXECUTED` when the JAR
is absent.

## M4 CLI

Run from the repository root:

```bash
export PYTHONPATH=paispl-m4/src

python3 -m paispl_m4.cli validate-proposal \
  paispl-m4/examples/M4-CASE-001.proposal.json

python3 -m paispl_m4.cli preview-proposal \
  paispl-m4/examples/M4-CASE-001.proposal.json

python3 -m paispl_m4.cli approve-proposal \
  paispl-m4/examples/M4-CASE-006.proposal.json \
  --approval paispl-m4/examples/M4-CASE-006.approval.json \
  --output paispl-m4/generated/manual-application
```

Preview is in-memory only. The final command writes generated artifacts only
after the approval record matches the proposal and preview hashes.

## Verified M4 results

- 20 M4 unit tests: PASS
- 6 required round-trip cases: PASS
- Sprint 0 and M1–M3 quality gates: PASS
- Reproducible ZIP and ZIP integrity checks: PASS
- PlantUML syntax validation: not executed because `plantuml.jar` is not
  included

Evidence is recorded in
[`paispl-m4/QUALITY_GATE_REPORT.json`](paispl-m4/QUALITY_GATE_REPORT.json) and
[`paispl-m4/M4_IMPLEMENTATION_REPORT.md`](paispl-m4/M4_IMPLEMENTATION_REPORT.md).

The reproducible research package is
`PAISPL_M4_UML_Roundtrip_Controller_v0.4.0.zip`; its SHA-256 is stored in the
adjacent `.sha256` sidecar.

## Deliberate limitations

- The UML differ accepts structured deltas; arbitrary XMI and free-form
  PlantUML parsing are not part of M4.
- Dependency-only edits have no approved architecture rule in the current
  policy and therefore require semantic clarification.
- Approval identities are local evidence records, not cryptographic signatures.
- Generated interface contracts are explicit stubs, not production-ready
  healthcare contracts.
- The healthcare Gold set is intentionally small; broader evaluation belongs
  to M6.

## Next milestone

M5 will implement the natural-language intent compiler and ambiguity
calibration. No M5 implementation is included in this repository yet.
