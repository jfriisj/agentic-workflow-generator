# ADR-0006: Artifact-specific status classification semantics

- Status: Accepted
- Date: 2026-08-03

## Context

ADR-0005 defines and the current implementation preserves the shared fail-closed
status invariants for every governed artifact:

- `PASS` requires complete required evidence and forbids demonstrated applicable
  nonconformance;
- `FAIL` requires demonstrated nonconformance;
- `BLOCKED` requires an unavailable, missing, or unverifiable required
  prerequisite.

ADR-0005 deliberately does not define the concrete artifact-specific criteria
that make those conditions true, and it does not define precedence when a
demonstrated failure and an unavailable prerequisite exist at the same time.

The repository currently governs seven artifact types:

- `Requirements`
- `ArchitectureDecision`
- `ImplementationReport`
- `CodeReview`
- `TestReport`
- `QAReport`
- `AIEvaluationReport`

Their producer responsibilities already contain materially different
classification rules. Requirements analysis evaluates completeness,
consistency, and testable acceptance criteria. Architecture evaluates an
architecture decision against approved requirements and constraints.
Implementation evaluates completion of the approved change at the implementer
boundary. Code review combines clean-code, test-evidence, and security review.
Test execution evaluates authoritative validation. QA evaluates acceptance
criteria against upstream evidence. AI evaluation evaluates declared quality,
safety, failure-mode, and operational criteria.

Leaving those rules only as dispersed producer prose keeps the artifact
contract unable to state the complete status meaning that target producers are
expected to preserve.

The decision must therefore make the artifact-specific classification contract
explicit without introducing executable runtime policy evaluation, workflow
routing, persistence, or a generic policy engine.

## Decision

Each governed artifact has one canonical artifact-specific status semantics
contract in addition to the shared invariant contract from ADR-0005.

### Ownership

The artifact contract owns the canonical status definitions that describe the
meaning of `PASS`, `FAIL`, and `BLOCKED` for that artifact type.

The producing role binding remains responsible for evaluating the evidence
available to its existing responsibility and choosing the artifact status that
matches that contract.

The workflow controller remains responsible only for routing an already
produced gate result. This decision does not move artifact classification into
the controller and does not change workflow transitions.

Producer skills may explain how to perform the evaluation, but they must not
define a conflicting status meaning independently from the artifact contract.

### Contract representation

The implementation must add one typed artifact-specific status-semantics
contract with exactly these required members:

~~~text
passDefinition
failDefinition
blockedDefinition
mixedConditionRule
~~~

`passDefinition`, `failDefinition`, and `blockedDefinition` are canonical
artifact-contract statements. They are declarative contract text, not an
executable expression language.

`mixedConditionRule` has one canonical value for the current governed artifact
set:

~~~text
FAIL_ON_DEMONSTRATED_NONCONFORMANCE
~~~

The contract must not introduce generic predicates, boolean expression trees,
threshold evaluators, scripting, plugins, or configurable policy variants.

Generated artifact schemas, active-config serialization, producer-facing target
rendering, and canonical generated output must preserve the exact contract
deterministically.

Because the new object becomes a required artifact-contract member, every
existing artifact contract must evolve explicitly to a new contract version
when implementation is introduced.

### Classification order

For the current seven governed artifacts, classification is fail-closed in this
order:

1. If the artifact-specific `failDefinition` is satisfied by positive evidence,
   return `FAIL`.
2. Otherwise, if the artifact-specific `blockedDefinition` is satisfied because
   a required prerequisite is unavailable, missing, or unverifiable, return
   `BLOCKED`.
3. Otherwise, return `PASS` only when the artifact-specific `passDefinition` and
   every shared ADR-0005 `PASS` invariant are satisfied.
4. If the available evidence establishes neither a valid `FAIL` nor a complete
   `PASS`, the artifact remains `BLOCKED`; uncertainty must not be converted
   into `PASS`.

The first rule resolves mixed `FAIL` / `BLOCKED` conditions for the current
artifact set. A demonstrated nonconformance is outcome-determining because each
current artifact is a conjunctive gate: one demonstrated violation of a
required condition is already sufficient to make its overall acceptance claim
false. An unavailable additional prerequisite cannot erase that demonstrated
failure.

A non-blocking observation, advisory risk, or stylistic preference does not
satisfy a `failDefinition` merely because it is recorded as a finding.

## Canonical artifact semantics

### Requirements

`PASS` means:

> Scope is explicit; requirements are internally consistent; acceptance
> criteria are testable; material assumptions and constraints are recorded; and
> no unresolved issue prevents downstream design.

`FAIL` means:

> Supplied requirements or constraints are demonstrably contradictory or
> impossible to satisfy as stated.

`BLOCKED` means:

> A stakeholder decision, required source information, scope boundary, or
> acceptance threshold necessary to complete the requirements contract is
> unavailable, missing, or unverifiable.

A demonstrated contradiction or impossibility is outcome-determining and
therefore remains `FAIL` even if another required input is also unavailable.

### ArchitectureDecision

`PASS` means:

> The decision traces to approved requirements; system boundaries are explicit;
> material alternatives and tradeoffs are evaluated; consequences and risks are
> documented; and no unresolved requirement prevents implementation.

`FAIL` means:

> The proposed architecture demonstrably violates an approved requirement or
> constraint.

`BLOCKED` means:

> A requirement, quality attribute, constraint, or dependency fact necessary to
> make the architecture decision is unavailable, missing, or unverifiable.

A demonstrated architectural violation is outcome-determining and therefore
remains `FAIL` even if another decision prerequisite is unavailable.

### ImplementationReport

`PASS` means:

> The approved change is implemented; required tests owned by the implementation
> responsibility are updated; required implementation-level validation
> available at this boundary has been run; and known risks plus validation
> deliberately owned by later independent gates are disclosed.

`FAIL` means:

> The implementation or implementation-level validation positively
> demonstrates that the approved behavior is not satisfied.

`BLOCKED` means:

> An approved input, dependency, tool, credential, environment, or required
> decision necessary to complete the implementation responsibility is
> unavailable, missing, or unverifiable.

Unexecuted validation that is explicitly owned by a later independent gate does
not by itself block an ImplementationReport `PASS`; validation required at the
implementation boundary does.

A demonstrated implementation failure is outcome-determining and therefore
remains `FAIL` even if another implementation prerequisite is unavailable.

### CodeReview

`PASS` means:

> Every required review dimension for the producing role binding has been
> completed with the required evidence, and no unresolved blocking finding or
> required fix remains within the reviewed scope.

For the current review-heavy and AI-application compositions, required review
dimensions include the selected clean-code, test-evidence, and security review
responsibilities where configured.

`FAIL` means:

> At least one reviewed dimension positively demonstrates a blocking defect,
> violated approved requirement or trust boundary, or other required fix that
> prevents the reviewed implementation from passing the code-review gate.

`BLOCKED` means:

> Required changed scope, code, configuration, test evidence, dependency
> information, threat context, or other review evidence is unavailable,
> missing, or unverifiable such that the required review cannot be completed.

Advisory findings that do not require remediation before the gate do not alone
constitute `FAIL`.

A demonstrated blocking review defect is outcome-determining and therefore
remains `FAIL` even if another required review input is unavailable.

### TestReport

`PASS` means:

> All required validation at the test-execution boundary has executed and
> passed, and no required test is missing or skipped.

`FAIL` means:

> At least one required test or validation command executes and positively
> demonstrates that the product does not satisfy the tested contract.

`BLOCKED` means:

> A required tool, dependency, environment, credential, fixture, or test input
> is unavailable, missing, or unverifiable such that required validation cannot
> execute or be established.

A required skipped test prevents `PASS` and is `BLOCKED` unless positive product
failure evidence independently satisfies the `FAIL` definition.

A demonstrated required product failure is outcome-determining and therefore
remains `FAIL` even when another required validation cannot execute.

### QAReport

`PASS` means:

> Every required acceptance criterion is satisfied by valid evidence and all
> required upstream gates pass.

`FAIL` means:

> Valid evidence demonstrates that at least one required acceptance criterion is
> not satisfied, or a required upstream gate has an applicable `FAIL` result
> that QA is not permitted to override.

`BLOCKED` means:

> Required evidence, artifacts, revisions, environments, decisions, or upstream
> gate evidence is unavailable, missing, stale, or unverifiable such that QA
> cannot establish the complete acceptance claim.

A demonstrated failed acceptance criterion or applicable failed upstream gate is
outcome-determining and therefore remains `FAIL` even if another criterion is
blocked.

### AIEvaluationReport

`PASS` means:

> Every required AI evaluation criterion within the declared scope is supported
> by reproducible evidence and satisfies its declared threshold or acceptance
> condition; required datasets, scenarios, baselines, safety checks, failure-mode
> checks, and operational evidence are present when applicable; and no required
> evaluated scenario demonstrates unacceptable behavior.

`FAIL` means:

> Reproducible evidence demonstrates that at least one required quality, safety,
> failure-mode, or operational criterion or threshold is not satisfied.

`BLOCKED` means:

> Required evidence, dataset, scenario, baseline, threshold, evaluation
> condition, environment, or other prerequisite necessary to evaluate a required
> criterion is unavailable, missing, or unverifiable.

A failed required scenario must not be hidden by an aggregate metric that
otherwise passes.

A demonstrated required evaluation failure is outcome-determining and therefore
remains `FAIL` even if another required evaluation prerequisite is unavailable.

## Validation boundary

Compiler validation for the future artifact-specific status-semantics contract
is limited to information already available at the deterministic compiler
boundary.

It must fail closed when:

- the status-semantics object is missing;
- any of the four required members is missing;
- a required definition is empty or invalid for the contract schema;
- `mixedConditionRule` differs from the canonical current value;
- generated artifact schemas do not preserve the source contract;
- active configuration does not preserve the source contract;
- an enabled target omits or changes producer-facing status semantics.

The compiler does not prove that a produced Markdown artifact actually contains
the evidence needed to satisfy a definition unless that evidence is already
available to an accepted validation boundary.

This decision does not introduce a produced-artifact parser, runtime artifact
validator, workflow state store, or evidence persistence service.

## Relationship to ADR-0005

ADR-0005 remains accepted and authoritative for the shared cross-artifact
invariants.

This ADR extends ADR-0005 by defining the artifact-specific classification
contract and the mixed-condition rule for the current seven governed artifacts.

It does not weaken:

- complete-evidence requirements for `PASS`;
- demonstrated-nonconformance requirements for `FAIL`;
- unavailable-prerequisite requirements for `BLOCKED`.

## Explicitly deferred

This decision does not define or implement:

- workflow transitions or explicit `BLOCKED` routing;
- retry or escalation semantics;
- artifact invalidation;
- reproducible evidence hashes or attestations;
- input-artifact references or dependency lineage;
- produced-artifact persistence;
- execution history;
- runtime workflow orchestration;
- runtime artifact validation;
- a generic policy engine;
- configurable status-policy variants;
- new target platforms.

Reproducible evidence and input-artifact references remain separate accepted
artifact-hardening gaps and require their own bounded decisions or implementation
slices.

## Alternatives considered

### Keep artifact-specific status rules only in producer skills

Rejected. Producer skills already contain much of the required domain guidance,
but artifact status is an artifact-contract concern. Leaving the canonical
meaning only in skills allows the declared artifact contract and generated
producer instructions to drift.

### Encode executable status predicates

Rejected. A predicate language, expression tree, rules engine, or configurable
policy system would add a new execution responsibility without a current need.
The compiler only needs a canonical declarative contract that producer-facing
targets preserve.

### Let `BLOCKED` take precedence over demonstrated failure

Rejected. For every current governed artifact, one demonstrated violation of a
required condition already makes the overall acceptance claim false. Missing
additional evidence cannot erase a known failure.

### Keep mixed conditions undefined

Rejected for this decision. The unresolved precedence creates an ambiguous
producer contract precisely when independent evidence contains both a confirmed
failure and a missing prerequisite.

### Treat every finding as `FAIL`

Rejected. Review observations, residual risks, limitations, and advisory
findings may be relevant without independently proving that a required
acceptance condition is violated.

### Add runtime artifact validation now

Rejected. The product boundary remains a deterministic compiler for agentic
delivery configurations. Runtime artifact evidence validation requires a
separate accepted need.

## Consequences

Every governed artifact gains one explicit canonical artifact-specific status
meaning while retaining the shared ADR-0005 invariants.

Current producer responsibilities can be aligned to one contract rather than
carrying independent status definitions.

Mixed failure/blocker evidence becomes deterministic for the current governed
artifact set: demonstrated outcome-determining nonconformance is `FAIL`; absent
such failure, unavailable required evidence is `BLOCKED`.

The future implementation must touch the existing artifact contract, schema,
serialization, target-rendering, generated-output, and validation boundaries,
but it requires no new runtime, datastore, technology, target, or workflow
engine.

Changing an artifact-specific status definition becomes an explicit contract
change and requires corresponding artifact contract version evolution.

## Acceptance scenarios

An implementation conforming to this decision must satisfy at least these
scenarios:

1. Every governed artifact carries the required artifact-specific
   status-semantics contract.
2. Every contract contains non-empty canonical `passDefinition`,
   `failDefinition`, and `blockedDefinition` members.
3. Every contract contains
   `mixedConditionRule = FAIL_ON_DEMONSTRATED_NONCONFORMANCE`.
4. Omitting or renaming a required member is invalid.
5. Generated artifact schemas preserve the canonical contract.
6. Active-config serialization preserves the canonical contract.
7. Both existing target renderers preserve the producer-facing semantics.
8. Producer-facing instructions never describe missing evidence alone as
   `FAIL`.
9. Producer-facing instructions never describe absence of known failure as
   sufficient for `PASS`.
10. A demonstrated required failure is represented as `FAIL` even when another
    required prerequisite is unavailable.
11. A missing required prerequisite produces `BLOCKED` when no demonstrated
    artifact-specific failure exists.
12. Advisory or non-blocking findings do not independently force `CodeReview`
    to `FAIL`.
13. Required skipped validation prevents `TestReport` `PASS`.
14. A failed required QA criterion cannot be overridden by another blocked
    criterion.
15. A failed required AI evaluation scenario cannot be hidden by passing
    aggregate results.
16. Existing artifact contracts evolve versions explicitly when the new
    required member is implemented.
17. No workflow routing, runtime artifact validator, persistence service,
    evidence-hash mechanism, input-artifact lineage, policy engine, or new target
    is introduced.
