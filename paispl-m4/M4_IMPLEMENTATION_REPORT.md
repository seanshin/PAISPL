# M4 Implementation Report

## Implemented scope

M4 provides a deterministic UML round-trip Change Controller without changing
the completed M1–M3 engines. It validates a versioned Change Proposal, enforces
the required state machine, rejects stale or unmapped edits, produces a Korean
semantic explanation, translates supported Feature operations into Requirement
IR, calls the M1 Solver, and creates M2/M3 previews in memory.

Application is gated by a separate approval record bound to the proposal, base,
preview configuration, and preview architecture hashes. Only a matching
`APPROVE` decision can transition `PENDING_APPROVAL -> APPROVED -> APPLIED` and
materialize manifest-owned artifacts.

## Required case evidence

| Case | Expected result |
|---|---|
| M4-CASE-001 | LIS inclusion reaches `PENDING_APPROVAL`; impact contains `CMP-LIS`, `CMP-EMR`, and `CMP-AUDIT` |
| M4-CASE-002 | Solver rejection linked to `C-024` |
| M4-CASE-003 | Unknown UML ID rejected before Solver |
| M4-CASE-004 | Stale architecture hash rejected with rebase finding |
| M4-CASE-005 | Dependency-only edit classified unresolved and rejected |
| M4-CASE-006 | Matching approval reaches `APPLIED` and equals the direct Requirement IR path |

Recorded evidence is under `generated/M4-CASE-*/`, with the lifecycle and
before/after diagrams under `generated/uml/`.

## Trace and preservation

The applied trace binds `sourceQuote`, intent, Feature, component, interface,
test, artifact path, proposal, operation, and approval IDs. Preview does not
write artifacts. M3 SHA-256 planning preserves unaffected paths byte-for-byte;
only manifest-owned stale paths may be removed during repeated application.

## Validation scope

The M4 suite covers all fourteen required checks plus approval invalidation,
rejected-evidence immutability, dependency classification, Korean explanation,
and deterministic preview. The quality gate also reruns Sprint 0 and M1–M3.
PlantUML syntax validation is executed only when `plantuml.jar` is present and
is explicitly recorded otherwise. ZIP integrity and repeated-build SHA-256
identity are checked by the M4 quality gate.

## Limitations and threats to validity

- UML differ input is a structured delta; parsing arbitrary XMI or free-form
  PlantUML edits is outside M4 and belongs to later Workbench integration.
- No architecture rule is approved in the current policy, so dependency-only
  edits intentionally require semantic clarification.
- Healthcare mappings and Gold cases are domain-specific and small; broader
  external validity requires the M6 benchmark and mutation corpus.
- Approval identities are local records, not cryptographic signatures or an
  external identity-provider assertion.
- Generated interface contracts remain scaffolding marked
  `stub_requires_domain_contract`, not production contracts.
- Without a local PlantUML JAR, diagram syntax validation remains unexecuted and
  is reported rather than silently treated as passed.

## Next milestone

M5: natural-language intent compiler and ambiguity calibration.
