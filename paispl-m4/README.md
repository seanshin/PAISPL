# PAISPL M4 — UML Round-trip Change Controller

M4 implements the controlled reverse path from an edited UML projection to a
Solver-validated Change Proposal. UML is review input, not a source of truth.
No Feature configuration, architecture, code, or deployment artifact is
materialized until a separate approval record matches the validated preview.

## Pipeline

```text
UML edit
  -> DRAFT Change Proposal
  -> structural and immutable-ID validation
  -> stale-base check
  -> Korean semantic explanation
  -> Requirement IR delta
  -> M1 Solver
  -> M2 architecture preview
  -> M3 artifact-plan preview
  -> PENDING_APPROVAL
  -> separately hashed approval record
  -> APPROVED -> APPLIED
```

Rejected proposals are immutable. Dependency-only edits without an owning
Feature or approved architecture rule become `unresolved_semantic_edit` and
cannot reach approval.

## Commands

Run from the workspace root:

```bash
export PYTHONPATH=paispl-m4/src
python3 -m paispl_m4.cli validate-proposal paispl-m4/examples/M4-CASE-001.proposal.json
python3 -m paispl_m4.cli preview-proposal paispl-m4/examples/M4-CASE-001.proposal.json
python3 -m paispl_m4.cli approve-proposal paispl-m4/examples/M4-CASE-006.proposal.json \
  --approval paispl-m4/examples/M4-CASE-006.approval.json \
  --output paispl-m4/generated/manual-application
python3 -m paispl_m4.cli run-examples
```

Run all M4 and prior milestone checks and build the reproducible package:

```bash
python3 paispl-m4/tools/run_quality_gate.py
```

Build only the package:

```bash
python3 paispl-m4/tools/build_package.py
```

## Required examples

- `M4-CASE-001`: LIS addition reaches `PENDING_APPROVAL`.
- `M4-CASE-002`: removal required by preserved `patient_bff` is rejected by
  constraint `C-024`.
- `M4-CASE-003`: unknown UML `componentId` is rejected before Solver execution.
- `M4-CASE-004`: stale architecture hash requires rebase.
- `M4-CASE-005`: dependency-only edit remains unresolved and unapplied.
- `M4-CASE-006`: matching explicit approval reaches `APPLIED`.

## Bound evidence

Canonical SHA-256 bindings cover the proposal, base configuration and
architecture, Requirement IR delta, preview configuration and architecture,
artifact plan and manifest, approval, and applied result. The applied trace
retains source quote, intent, Feature, component, interface, test, artifact
path, proposal, operation, and approval identifiers.

Generated interface contracts remain explicit stubs and are not
production-ready contracts.
