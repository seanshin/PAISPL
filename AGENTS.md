# PAISPL CLI Agent Instructions

## Mission

Build PAISPL (Prompt-driven AI Software Product Line) as a reproducible research
prototype and an implementation-ready product. Continue milestones in order.
M4, defined in `tasks/M4_TASK.md`, is the current verified checkpoint. The next
planned milestone is M5; do not begin it until an explicit M5 task is present.

## Read first

Before changing code, read these files in order:

1. `docs/PAISPL_CLI_HANDOFF.md`
2. `tasks/M4_TASK.md`
3. `docs/COMMANDS.md`
4. `paispl-sprint0/docs/03-natural-language-uml-relationship.md`
5. `paispl-sprint0/mappings/nl-uml-trace-rules.yaml`
6. `paispl-m3/docs/FINAL_PRODUCT_BLUEPRINT.md`

Do not redesign completed milestones unless a failing test or M4 requirement
demonstrates that a minimal backward-compatible correction is necessary.

## Authority hierarchy

Use this semantic authority order without exception:

1. approved natural-language intent;
2. Requirement IR;
3. Feature Model and Solver-validated configuration;
4. Architecture Graph;
5. generated UML projection;
6. generated code and deployment artifacts.

UML is not a second source of truth. A UML edit creates a Change Proposal. It
must be translated into Requirement IR, checked by the Solver, presented for
human approval, and only then applied to downstream artifacts.

## Non-negotiable invariants

- Never permit a UML edit to bypass Requirement IR or Solver validation.
- Preserve immutable IDs across Requirement, Intent, Feature, Component,
  Interface, Test, UML element, proposal, and generated artifact links.
- Reject unmapped UML elements, unknown IDs, hidden Feature changes, stale base
  configurations, and unsatisfiable proposals.
- Preserve unaffected generated artifacts byte-for-byte.
- Generate deterministically: identical canonical input must produce identical
  bytes and SHA-256 hashes.
- Delete only files owned by the previous generated-artifact manifest.
- Do not claim that generated contract stubs are production-ready contracts.
- Do not deploy, push, publish, or modify external systems without explicit
  user authorization.
- Do not weaken an existing test merely to make a new implementation pass.

## Working protocol

1. Run all baseline quality gates before editing.
2. Record any baseline failure without masking it.
3. Implement the smallest coherent milestone slice.
4. Add tests before declaring the slice complete.
5. Run M4 tests and all earlier milestone quality gates.
6. Validate every generated PlantUML file with PlantUML when the JAR is
   available; otherwise retain a clear unexecuted validation note.
7. Produce `M4_IMPLEMENTATION_REPORT.md`, `QUALITY_GATE_REPORT.json`, and a
   reproducible ZIP package.
8. Update the task checklist only after evidence exists.

## Engineering conventions

- Python 3.11 or later; standard library and PyYAML unless a dependency is
  explicitly justified.
- UTF-8, deterministic serialization, stable sorting, and newline-terminated
  text files.
- Keep policy in versioned YAML, schemas in JSON Schema, and execution logic in
  testable Python modules.
- No timestamp, random UUID, absolute machine path, or environment-dependent
  value may enter canonical generated output.
- Keep domain-specific rules in the healthcare domain pack, not in generic
  orchestration code.
- Errors must be structured, actionable, and traceable to source IDs.

## Required final response from a CLI agent

Report only evidence-backed results:

- implemented scope;
- files or package produced;
- tests and quality gates executed;
- known limitations or unexecuted checks;
- exact next milestone.
