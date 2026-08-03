# ADR-0005: Artifact status invariant contract semantics

- Status: Accepted
- Date: 2026-08-03

## Context

The project is in post-migration hardening. Accepted scope explicitly includes
status-dependent artifact invariants as one of the remaining artifact-contract
gaps.

Every current artifact contract already uses the same status domain:

~~~text
PASS
FAIL
BLOCKED
~~~

The contracts also require the canonical `## Status` heading and constrain the
status value through the existing status pattern and `allowedStatuses`.

Current skills contain artifact- and role-specific rules explaining when their
work may return `PASS`, `FAIL` or `BLOCKED`. Those concrete criteria are not
uniform. For example, requirements analysis evaluates requirements completeness,
while test execution evaluates executed validation.

The architecture already establishes the cross-cutting fail-closed rule that
missing required evidence must not become `PASS`, and generated target
instructions preserve the same rule.

What remains undefined is the common contract-level relationship between a
claimed artifact status and the evidence state supporting that claim.

This decision must define only the invariants shared by all artifact contracts.
It must not absorb the separately identified artifact-specific status-semantics
gap, workflow routing, reproducible evidence, input-artifact references or
runtime orchestration.

## Decision

Every governed artifact status is subject to one shared fail-closed status
invariant contract.

The existing canonical status values remain unchanged:

~~~text
PASS
FAIL
BLOCKED
~~~

The status invariant contract defines necessary conditions for each status. It
does not define a complete artifact-specific classification algorithm.

### PASS invariant

`PASS` is valid only when:

1. every prerequisite required to make the artifact claim is available or has
   been validly evaluated;
2. no required evidence is missing or unverifiable; and
3. no known evidence demonstrates nonconformance with a requirement, criterion
   or contract applicable to the artifact.

Missing required information, evidence, validation or prerequisites therefore
forbids `PASS`.

Confidence, assumptions, silence, skipped required validation or absence of
known failure are not substitutes for required evidence.

### FAIL invariant

`FAIL` requires positive evidence of nonconformance.

At least one applicable requirement, criterion or contract must be demonstrably
unsatisfied.

A producer must not return `FAIL` merely because required information or
evidence is unavailable.

The concrete condition that constitutes nonconformance remains defined by the
artifact-specific producer responsibility and is not standardized by this
decision.

### BLOCKED invariant

`BLOCKED` requires at least one required prerequisite for a complete artifact
claim to be unavailable, missing or unverifiable.

A prerequisite may include evidence, an input, a decision, a dependency, a tool,
an environment, a credential, a fixture, a baseline, a threshold or another
condition required by the artifact-specific responsibility.

`BLOCKED` represents inability to establish the complete required claim. It is
not a weaker form of `PASS` and must not be converted into `PASS` through
assumption or inferred confidence.

### Mixed conditions

This decision intentionally does not define precedence when more than one
status condition exists simultaneously.

For example, an artifact may have both:

- demonstrated evidence of one concrete failure; and
- another required prerequisite that is unavailable.

Both the `FAIL` and `BLOCKED` necessary conditions can then be true.

Choosing the canonical status for such an artifact depends on
artifact-specific status semantics and remains outside this decision.

The shared invariant contract therefore constrains invalid status claims without
pretending to define artifact-specific status precedence that the repository
does not yet specify.

### Contract responsibility

The reusable artifact contract owns the shared status invariants.

The implementation slice must add one typed status-invariant contract to the
artifact domain model and one corresponding required contract member to the
artifact registry schema.

The canonical invariant members are:

~~~text
passRequiresCompleteEvidence = true
passForbidsDemonstratedNonconformance = true
failRequiresDemonstratedNonconformance = true
blockedRequiresUnavailablePrerequisite = true
~~~

All four members are mandatory and canonical. Artifact contracts and targets
must not omit, rename or weaken them.

These values are policy invariants, not configurable feature switches. `false`
is not a supported artifact-contract variant.

Generated artifact-schema projection, active-config serialization and target
rendering must preserve the same invariant contract deterministically.

Because this introduces a new required artifact-contract member, existing
artifact contracts must evolve explicitly to a new contract version when the
implementation is introduced.

### Validation boundary

Compiler validation is fail-closed for the status-invariant contract itself:

- the invariant object is required;
- all four canonical members are required;
- every member must be `true`;
- no weaker or alternative invariant shape is valid;
- generated artifact-contract schemas must remain canonical with their source
  contracts;
- active configuration and target output must preserve the invariant contract.

The current compiler does not ingest and validate arbitrary produced Markdown
artifacts as runtime state.

This decision does not introduce a produced-artifact persistence service,
execution-history store or runtime artifact-validation engine solely to inspect
actual evidence content.

Target rendering must communicate the invariant contract to artifact producers,
but compiler validation must not claim to prove evidence that is not available
at an existing validation boundary.

Where actual artifact evidence becomes available to an already accepted
validation boundary, the shared invariants apply. Adding a new runtime boundary
requires a separate accepted need.

## Explicitly deferred

This decision does not define or implement:

- artifact-specific `PASS`, `FAIL` or `BLOCKED` criteria;
- precedence between simultaneous `FAIL` and `BLOCKED` conditions;
- artifact-specific status transition rules;
- workflow transition or `BLOCKED` routing changes;
- artifact invalidation;
- retry or escalation semantics;
- reproducible evidence hashes or attestations;
- input-artifact references or dependency lineage;
- persistence of produced artifacts;
- execution history or runtime state;
- runtime workflow orchestration;
- a generic policy engine;
- configurable status-policy variants;
- new target platforms.

Those concerns require their own accepted need and slice.

## Alternatives considered

### Keep the rules only in skills

Rejected. Skills already contain useful artifact-specific guidance, but the
cross-cutting fail-closed relationship between evidence state and artifact
status is an artifact-contract invariant. Leaving it only in skill prose makes
the contract weaker than the generated producer behavior.

### Define complete semantics for every artifact now

Rejected. Requirements, architecture decisions, implementation reports, code
reviews, test reports, QA reports and AI evaluation reports have different
domain-specific acceptance criteria.

Standardizing those criteria in this decision would absorb the separately
identified artifact-specific status-semantics gap and make this slice larger
than necessary.

### Define FAIL over BLOCKED precedence globally

Rejected for this decision. The repository does not currently establish a
canonical answer for mixed conditions. Choosing one would introduce new
artifact-specific behavior without evidence that one global precedence is
correct for every artifact type.

### Treat missing evidence as FAIL

Rejected. Existing fail-closed rules consistently distinguish demonstrated
nonconformance from inability to evaluate required evidence.

Missing prerequisites therefore support `BLOCKED`, not an invented `FAIL`.

### Allow PASS when no failure is known

Rejected. Absence of known failure is not evidence that all required conditions
were satisfied.

`PASS` requires complete required evidence and forbids unresolved required
evidence gaps.

### Introduce a runtime artifact validator

Rejected for this slice. The product is a deterministic compiler for validated
agentic configurations, not a workflow-runtime or artifact-history service.

A new runtime validation boundary would expand architectural responsibility
beyond the accepted status-invariant gap.

## Consequences

All artifact contracts gain one explicit, machine-readable shared status
invariant contract.

`PASS`, `FAIL` and `BLOCKED` retain their existing names and remain separate
from revision and provenance semantics.

The compiler can prove that every artifact contract and generated target
preserves the same fail-closed status policy.

Artifact producers receive deterministic instructions that missing required
evidence cannot become `PASS`, `FAIL` requires demonstrated nonconformance, and
`BLOCKED` represents unavailable required prerequisites.

The decision does not pretend that the compiler can inspect evidence it does not
possess.

Artifact-specific classification and mixed-condition precedence remain explicit
future work rather than hidden assumptions in this slice.

Existing artifact contracts require explicit contract-version evolution when
the new required invariant contract is implemented.

No new technology, datastore, runtime service, workflow engine or target
platform is required.

## Acceptance scenarios

An implementation conforming to this decision must satisfy at least these
scenarios:

1. Every artifact contract carries the canonical shared status-invariant
   contract.
2. Omitting the status-invariant contract is invalid.
3. Omitting any canonical invariant member is invalid.
4. Setting any canonical invariant member to `false` is invalid.
5. Renaming or weakening a canonical invariant is invalid.
6. `PASS` is never presented as valid when required evidence or prerequisites
   are missing or unverifiable.
7. `PASS` is never presented as valid when known evidence demonstrates an
   applicable nonconformance.
8. `FAIL` is described as requiring demonstrated nonconformance rather than
   merely missing evidence.
9. `BLOCKED` is described as requiring an unavailable, missing or unverifiable
   required prerequisite.
10. Generated artifact-contract schemas preserve the invariant contract.
11. Active-config serialization preserves the invariant contract.
12. Existing target renderers preserve the invariant contract without
    target-specific weakening.
13. Artifact-specific acceptance criteria are not standardized by this slice.
14. Mixed `FAIL` and `BLOCKED` precedence is not invented by this slice.
15. No workflow-routing change, runtime artifact validator, persistence service,
    evidence-hash mechanism or input-artifact lineage is introduced.
