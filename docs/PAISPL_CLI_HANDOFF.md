# PAISPL CLI Handoff

## 1. Project objective

PAISPL is a Prompt-driven AI Software Product Line system. It translates a
natural-language requirement or change request into a validated product
variant, architecture graph, UML review model, and minimal set of generated
code and deployment artifacts.

The research hypothesis is that a controlled hybrid pipeline can improve
semantic traceability and incremental regeneration precision compared with
unconstrained prompt-to-code generation.

## 2. Canonical pipeline

```text
Natural Language
  -> Requirement IR
  -> Feature Intent and Constraints
  -> Solver-validated Configuration
  -> Architecture Graph
  -> UML Projection
  -> Code, Contract, and Deployment Artifacts
  -> Test and Evidence Bundle
```

Reverse UML flow:

```text
UML Edit
  -> Change Proposal
  -> Natural-language Explanation
  -> Requirement IR Delta
  -> Solver Revalidation
  -> Impact Preview
  -> Human Approval
  -> Regeneration
```

## 3. Completed baseline

### Sprint 0 — Design baseline

- 38 healthcare Features;
- 25 Feature constraints;
- 4 sequential scenarios and Gold configurations;
- 20 acceptance tests;
- 11 reference components and 13 dependencies;
- 5 UML models;
- 7 natural-language/UML mapping rules;
- 5 round-trip guards.

Root: `paispl-sprint0/`

### M1 — Requirement IR and Solver

- lightweight Requirement IR validation;
- Feature parent, mandatory, group, requires, and excludes semantics;
- include, exclude, replace, prefer, and preserve intent operations;
- sequential variant derivation;
- selected, added, removed, derived, and intent trace output.

Root: `paispl-m1/`

### M2 — Architecture Synthesizer

- selected Feature to component realization;
- active dependency and interface projection;
- component impact closure;
- regression-test selection;
- `intent -> feature -> component -> interface -> test` links;
- generated component UML.

Root: `paispl-m2/`

### M3 — Incremental Artifact Factory

- component descriptors and executable health scaffolds;
- interface contract stubs;
- Kubernetes Deployment and Service manifests;
- deployment UML and artifact traceability;
- SHA-256 `create/update/delete/no-op` plans;
- `review-only` classification for semantic impact without byte changes;
- manifest-owned deletion policy.

Root: `paispl-m3/`

### M4 — UML Round-trip Change Controller

- versioned Change Proposal schema and guarded state machine;
- stale-base and immutable-ID validation before Solver execution;
- Korean semantic explanation and Requirement IR delta translation;
- M1 Solver, M2 architecture, and M3 artifact previews without pre-approval writes;
- separately hash-bound approval and manifest-owned application;
- proposal and approval evidence in the generated trace chain;
- six recorded positive and negative round-trip cases.

Root: `paispl-m4/`

## 4. Current verified sequence

| Scenario | Meaning | M3 result |
|---|---|---:|
| BASE-HOSP-001 | Initial hospital platform | 40 creates |
| CHG-HOSP-001 | Disable AI diagnosis, add patient mobile | 5 creates, 10 updates, 30 no-op, 2 review-only |
| CHG-HOSP-002 | Move to on-premise and local AI | 9 updates, 36 no-op, 1 review-only |
| CHG-HOSP-003 | Add LIS and ABAC | 4 creates, 6 updates, 39 no-op, 3 review-only |

## 5. Important files

| Purpose | File |
|---|---|
| Requirement IR schema | `paispl-sprint0/schemas/requirement-ir.schema.json` |
| Feature Model | `paispl-sprint0/models/healthcare-feature-model.yaml` |
| Gold configurations | `paispl-sprint0/gold/gold-configurations.yaml` |
| Reference architecture | `paispl-sprint0/architecture/reference-architecture.yaml` |
| NL–UML rules | `paispl-sprint0/mappings/nl-uml-trace-rules.yaml` |
| Acceptance tests | `paispl-sprint0/tests/acceptance-tests.yaml` |
| M1 Solver | `paispl-m1/src/paispl_m1/engine.py` |
| M2 Synthesizer | `paispl-m2/src/paispl_m2/synthesizer.py` |
| M3 Generator | `paispl-m3/src/paispl_m3/generator.py` |
| M3 Planner | `paispl-m3/src/paispl_m3/planner.py` |
| Final product blueprint | `paispl-m3/docs/FINAL_PRODUCT_BLUEPRINT.md` |

## 6. Research-quality constraints

- Keep Gold expectations separate from implementation logic.
- Retain raw scenario input, canonical intermediate output, final output, and
  quality evidence.
- Report failures and rejected proposals, not only successful examples.
- Measure accuracy and preservation using stable, script-computable metrics.
- Document threats to validity: domain specificity, scenario size, human Gold
  labeling, LLM variability, and contract-stub limitations.
- Any LLM-dependent experiment must record model ID, prompt-template version,
  temperature or decoding policy, input hash, output hash, and repetition count.

## 7. Final target

The final deliverable consists of:

1. PAISPL Workbench: web UI, API, CLI, authentication, and project history.
2. Core engines: IR, Solver, architecture, impact, and artifact generation.
3. UML Digital Twin with controlled reverse changes.
4. Healthcare Domain Pack plus extension interface for other domains.
5. Evaluation and replication package.
6. Paper manuscript and appendices.

Milestones after the completed M4 checkpoint:

- M5: natural-language intent compiler and ambiguity calibration;
- M6: benchmark, mutation, ablation, and statistical evaluation;
- M7: integrated Workbench UI/API/CLI;
- M8: security, operations, governance, and paper hardening.
