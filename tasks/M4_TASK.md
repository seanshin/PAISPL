# M4 Task — UML Round-trip Change Controller

## 1. Goal

Implement a controlled reverse path from a user-edited UML projection to a
Solver-validated, human-approvable change. The controller must prove that UML
cannot directly mutate Feature configuration, architecture, code, or deployment
artifacts.

## 2. Required package

Create `paispl-m4/` with at least:

```text
paispl-m4/
  README.md
  M4_IMPLEMENTATION_REPORT.md
  QUALITY_GATE_REPORT.json
  pyproject.toml
  config/roundtrip-policy.yaml
  schemas/change-proposal.schema.json
  examples/
  src/paispl_m4/
    __init__.py
    proposal.py
    differ.py
    controller.py
    approval.py
    cli.py
  tests/
  tools/run_quality_gate.py
  tools/build_package.py
  generated/
```

## 3. Change Proposal contract

The JSON Schema must require at least:

- `version`;
- `proposal_id`;
- `base_configuration_id`;
- `base_architecture_hash`;
- origin UML model and element IDs;
- edit type;
- natural-language rationale;
- requested semantic operations;
- source and target immutable IDs;
- proposer and creation metadata without nondeterministic generated output;
- status;
- required approval policy.

Suggested operation vocabulary:

- `include_feature`;
- `exclude_feature`;
- `replace_feature`;
- `preserve_feature`;
- `add_dependency`;
- `remove_dependency`;
- `unresolved_semantic_edit`.

Structural dependency changes without an owning Feature or approved architecture
rule must become `unresolved_semantic_edit`; they must not be applied silently.

## 4. State model

Implement and test this state machine:

```text
DRAFT
  -> PENDING_VALIDATION
  -> VALIDATED | REJECTED
VALIDATED
  -> PENDING_APPROVAL
  -> APPROVED | REJECTED
APPROVED
  -> APPLIED
```

No transition may be skipped. Rejected proposals are immutable evidence.

## 5. Processing pipeline

1. Validate proposal structure.
2. Verify base configuration and architecture hash to detect stale edits.
3. Resolve UML tagged values to known component, interface, Feature, and test IDs.
4. Produce a Korean natural-language explanation of the proposed semantic delta.
5. Translate supported operations into a Requirement IR delta.
6. Run the existing M1 Solver against the base selected configuration.
7. Reject unsatisfiable or unmapped changes with structured findings.
8. Run M2 Architecture Synthesizer for a preview only.
9. Run M3 Artifact Factory for a preview-only change plan.
10. Bind proposal, base, preview, approval, and result with hashes.
11. Apply only after a valid explicit approval record.

## 6. Required example cases

### M4-CASE-001 — Valid addition

UML adds LIS integration to the architecture. The controller should translate
this into an `include_feature: lis_integration` proposal, validate it, preview
the expected `CMP-LIS`, `CMP-EMR`, and audit impact, and stop at approval.

### M4-CASE-002 — Unsatisfiable removal

UML removes a Feature required by another explicitly preserved Feature. The
Solver must reject the proposal with a constraint-linked explanation.

### M4-CASE-003 — Unknown UML element

An edit references an unknown or missing `componentId`. Reject before Solver
execution.

### M4-CASE-004 — Stale model

The supplied base architecture hash differs from the current canonical graph.
Reject as a stale edit and require rebase.

### M4-CASE-005 — Dependency-only edit

A user draws a new dependency with no Feature or approved architecture rule.
Classify it as unresolved and require semantic clarification; do not mutate the
reference architecture.

### M4-CASE-006 — Approved application

A validated proposal with a matching approval record reaches `APPLIED` and
produces the same canonical result as the equivalent natural-language IR path.

## 7. Approval record

Approval must be a separate document containing:

- proposal ID and proposal hash;
- base configuration ID and base hash;
- preview configuration and architecture hashes;
- approver identity or test fixture identity;
- decision and rationale;
- policy version.

A changed proposal invalidates a prior approval. Tests must demonstrate this.

## 8. Trace and UML requirements

- Preserve `source_quote`, intent, Feature, component, interface, test, and
  artifact path links.
- Add proposal and approval IDs to the trace chain.
- Generate a proposal lifecycle UML state diagram.
- Generate at least one before/after component UML comparison.
- Every generated UML element must retain semantic tagged values.
- A UML edit must never be treated as approved merely because rendering passes.

## 9. Required tests

At minimum, test:

1. schema-valid proposal accepted for validation;
2. invalid state transition rejected;
3. unknown UML ID rejected;
4. stale base hash rejected;
5. valid Feature inclusion reaches `PENDING_APPROVAL`;
6. unsatisfiable Feature delta rejected by M1;
7. unresolved dependency edit cannot reach approval;
8. preview matches direct Requirement IR path;
9. approval hash mismatch rejected;
10. approved proposal reaches `APPLIED`;
11. no generated artifact changes before approval;
12. unaffected artifact hashes remain unchanged;
13. trace chain includes proposal and approval evidence;
14. generated PlantUML contains IDs and round-trip guard.

## 10. Definition of done

M4 is complete only when:

- all M4 tests pass;
- Sprint 0 and M1–M3 quality gates still pass;
- all example cases produce recorded evidence;
- PlantUML validation passes or is explicitly reported as unexecuted;
- ZIP integrity passes;
- SHA-256 is reported;
- `M4_IMPLEMENTATION_REPORT.md` states limitations and threats to validity;
- no M5 functionality is mixed into the milestone.

