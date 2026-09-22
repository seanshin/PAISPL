# M2 Implementation Report

## Objective

Transform validated feature configurations into architecture graphs while
computing minimal change impact, regression-test scope, and trace links.

## Implemented semantics

1. A component is active only when at least one selected feature realizes it.
2. A dependency is emitted only when both endpoints are active.
3. Feature additions and removals produce component-level change actions.
4. Newly activated components propagate review to immediate API, event, and
   policy dependencies; deployment links do not automatically expand scope.
5. Domain-semantic couplings are explicit and versioned in the impact policy.
6. Trace links preserve `intent -> feature -> component -> interface -> test`.
7. UML is a generated, tagged projection. Direct edits remain proposals until
   converted into Requirement IR and revalidated by the Solver.

## Completion criteria

- Gold component-impact expectations pass for all three change scenarios.
- Imaging components remain outside the first change's impact boundary.
- Every active component carries Feature evidence.
- Every emitted dependency resolves to active endpoints.
- Generated UML contains `componentId`, `featureIds`, and the round-trip guard.

