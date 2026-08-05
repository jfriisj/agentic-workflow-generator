# ADR-0010: Input-artifact reference semantics

- Status: Accepted
- Date: 2026-08-05

## Context

ADR-0008 requires v1 to close the remaining input-artifact reference gap as part
of Milestone 2 — Complete compiler contracts.

The current governed artifact model already defines:

- provenance through ADR-0002;
- revision through ADR-0004;
- shared status invariants through ADR-0005;
- artifact-specific status classification through ADR-0006;
- reproducible evidence through ADR-0007.

Those decisions deliberately defer governed input-artifact lineage.

The current composition model already has the identities needed to express the
minimum dependency contract without introducing a second ownership model:

- a bundle selects one workflow and its artifact contracts;
- state-owner role bindings own artifact production through `produces`;
- workflow-controller bindings do not produce artifacts;
- `CompiledComposition.artifact_production` resolves an artifact contract to the
  concrete producing role binding and agent instance;
- workflow gates require the artifacts produced by their owning state binding.

The reusable `ArtifactContract` deliberately does not own role-binding
production or workflow ownership. Artifact dependency requirements can vary by
composition even when the reusable artifact contract type is unchanged.

A new input-artifact contract must therefore make composition dependencies
explicit without:

- moving composition authority into `ArtifactContract`;
- turning workflow gates into dependency declarations;
- inferring dependencies from workflow order or prose;
- introducing produced-artifact persistence or execution history;
- inventing runtime orchestration;
- duplicating provenance, revision, evidence or status semantics.

## Decision

### Canonical meaning

An input-artifact reference is a required dependency from one consuming
state-owner role binding to one existing artifact-production relationship in the
same selected bundle composition.

It identifies the upstream production relationship by the tuple:

~~~text
artifactType
roleBinding
~~~

The canonical registry representation is:

~~~json
{
  "artifactType": "Requirements",
  "roleBinding": "requirements"
}
~~~

The reference identifies a compiled production relationship, not merely an
artifact contract type and not a persisted runtime artifact instance.

At compilation time it resolves to the existing canonical production authority:

~~~text
CompiledArtifactProduction(
    artifact=<resolved ArtifactContract>,
    role_binding=<referenced state-owner role binding>,
    agent_instance=<currently assigned agent instance>
)
~~~

`agentInstance` is resolved context, not part of the reference identity. Agent
reassignment must not silently change the declared dependency identity.

`workflow`, artifact contract version and artifact path contract are derived
from the selected canonical composition and resolved artifact contract. They are
not repeated in the registry reference.

A concrete produced-artifact path and revision identify runtime artifact
material and are not known from the static dependency declaration. They are
therefore not part of the compile-time reference identity.

### Ownership

The consuming `RoleBinding` owns its required input-artifact declarations.

The canonical role-binding member is:

~~~text
inputArtifacts
~~~

Every role binding must declare `inputArtifacts` explicitly.

For a state-owner binding:

- the list may contain zero or more input-artifact references;
- the references are static prerequisites for that binding's artifact-producing
  responsibility;
- every declared reference is required whenever that binding is invoked;
- the current v1 model applies the declared input set to the binding's production
  responsibility as a whole.

`inputArtifacts` does not model invocation-specific remediation feedback. A
downstream artifact that exists only after the consuming binding's first
invocation cannot be a static required input of that binding, because doing so
would make the first invocation invalid or `BLOCKED` by construction.

Such later feedback remains workflow/handoff evidence under the existing runtime
boundary. This decision does not add phase-specific, transition-specific or
invocation-specific artifact-input declarations.

For a workflow-controller binding:

~~~text
inputArtifacts = []
~~~

is required.

A workflow controller must not declare governed artifact inputs. It remains
routing-only.

The absence of `inputArtifacts` is invalid. Missing data must not be interpreted
as an implicit empty list.

### Why the declaration does not belong to `ArtifactContract`

`ArtifactContract` remains reusable artifact-contract authority.

It continues to own the reusable contract for:

- status;
- provenance;
- revision;
- reproducible evidence;
- status invariants;
- artifact-specific status semantics;
- required headings and output shape.

It does not own which producer relationship a concrete bundle requires as an
input to another producer.

For example, a reusable `QAReport` contract can be used by more than one bundle,
while the exact upstream `TestReport`, `CodeReview` or other required production
relationships are properties of the selected composition.

Moving those relationships into the reusable artifact contract would make the
artifact contract a second composition authority and would couple it to bundle
role names.

### Why the declaration does not belong to workflow gates

Workflow gates continue to define the evidence artifact required for the
current state owner's gate.

They do not define the upstream inputs that the producer needs in order to create
that artifact.

The two responsibilities remain distinct:

~~~text
roleBinding.inputArtifacts
    = governed artifact inputs required by the producer

workflowState.gate.requiredArtifacts
    = governed artifacts that the current state owner must produce for its gate
~~~

Input dependencies must not be inferred from transition order, state names,
gate names or producer prose.

### Multiplicity and ordering

`inputArtifacts` is semantically an unordered set.

Rules:

- zero references are valid for a state owner with no governed input artifact;
- one or more references are valid where the production responsibility requires
  governed upstream artifacts;
- an exact duplicate `(artifactType, roleBinding)` reference is invalid;
- multiple references to the same `artifactType` from different role bindings
  are allowed when the composition intentionally requires both production
  relationships;
- artifact-type-only references are not allowed.

Canonical compilation and serialization order is lexical by:

~~~text
(artifactType, roleBinding)
~~~

Source ordering must not change semantics or generated output.

### Resolution

Every input-artifact reference must resolve inside the same selected bundle.

A valid reference requires all of the following:

1. `artifactType` identifies a registered artifact contract included by the
   selected bundle;
2. `roleBinding` identifies a role binding in the selected bundle;
3. the referenced role binding is a `state-owner`;
4. the referenced role binding declares the referenced `artifactType` in
   `produces`;
5. the resolved production relationship exists exactly once in the canonical
   composition;
6. the consuming role binding is not the referenced producer role binding.

Unknown role bindings, unknown artifact contracts, artifact types outside the
bundle, controller references, producer/type mismatches and self-references are
invalid composition.

A reference does not resolve by searching for "any producer" of an artifact
type. The producer role binding is part of the canonical identity precisely so
that a composition with more than one producer of the same artifact type remains
unambiguous.

This decision does not require the compiler to infer input availability from
workflow transition order. Workflow routing remains a separate accepted gap.
Static validity proves that the referenced production relationship exists in the
accepted composition, not that a concrete produced edition already exists when
the consumer is invoked.

### Dependency cycles

The input-artifact dependency graph must be acyclic.

For validation, each reference creates a directed dependency edge:

~~~text
referenced producer role binding
    ->
consuming role binding
~~~

A direct or transitive cycle is invalid.

Examples of invalid cycles include:

~~~text
architecture -> implementation
implementation -> architecture
~~~

and:

~~~text
requirements -> architecture
architecture -> implementation
implementation -> requirements
~~~

Workflow transition graphs may contain remediation or failure routing that
returns to an earlier state. That routing is a separate concern and does not
make cyclic artifact-input dependencies valid.

In particular, a later `TestReport`, `CodeReview` or `AIEvaluationReport` created
after an earlier producer invocation may be carried back as remediation evidence
by the workflow/handoff mechanism without becoming a static `inputArtifacts`
requirement of that earlier producer. Static dependency edges and runtime
remediation routing are intentionally different concerns.

This decision does not infer artifact dependencies from workflow transitions and
does not change workflow routing semantics.

### Compile-time versus runtime proof

The compiler can prove the static dependency contract from registry and
composition state.

It can prove:

- the input reference shape is canonical;
- the referenced artifact contract exists;
- the referenced producer role binding exists;
- the producer is a state owner;
- the producer declares that artifact type;
- the reference is not duplicated;
- the reference is not a self-reference;
- the dependency graph is acyclic;
- the dependency is preserved in canonical compilation and serialization.

The compiler cannot prove that a concrete produced upstream artifact exists,
that a particular revision has been materialized, or that its content is true
without that produced artifact being available to an existing validation
boundary.

The compiler must not claim such runtime proof and must not add persistence,
history or artifact parsing solely to obtain it.

### Canonical typed and serialized representation

The later implementation must add one typed input-artifact reference with the
two canonical identity members:

~~~text
artifact_type
role_binding
~~~

The bundle `RoleBinding` domain model must carry a deterministic collection of
those references.

The corresponding compiled role binding inside `CompiledComposition` must carry
the resolved input production relationships while preserving the declared
producer role-binding identity.

`CompiledComposition` remains the sole canonical resolved composition. Input
references must not create a parallel resolution model.

`.agentic/agentic.json` must preserve the canonical resolved input-artifact
semantics as part of the serialized compiled role binding.

The implementation may expose a derived dependency projection for validation or
rendering, but that projection is not a second authority. The authoritative
declaration remains the consuming role binding and the authoritative resolution
remains `CompiledComposition`.

### Interaction with provenance

Input-artifact references do not change ADR-0002 provenance.

The upstream artifact's producing role binding is already part of its canonical
provenance.

The input reference deliberately uses that stable producer identity but does not
copy the full provenance block into the bundle declaration.

The consuming artifact's own provenance continues to identify its own producer.
An input reference must not replace or alter that provenance.

### Interaction with revision

Input-artifact references do not change ADR-0004 revision semantics.

A compile-time input declaration does not pin a revision.

Revision identifies a concrete produced edition and is only meaningful when an
upstream produced artifact is available.

When a producer actually evaluates a concrete upstream artifact edition and its
revision is material to reproducibility, that edition identity belongs in the
producer's recorded evidence source under ADR-0007.

The compiler must not fabricate a revision or create revision-history storage in
order to satisfy an input declaration.

### Interaction with reproducible evidence

Input-artifact references and reproducible evidence remain separate contracts.

The input reference says:

> this producer requires this governed upstream production relationship.

ADR-0007 evidence says:

> this is the concrete source and procedure used to establish this
> status-relevant observation.

When a referenced governed artifact is actually used as evidence, the producer
must identify the concrete source with enough provenance/revision detail to make
the evaluation reproducible when those details are material and available.

The input-artifact contract does not introduce another `## Evidence` format,
evidence classifier, hash requirement or attestation mechanism.

### Interaction with PASS, FAIL and BLOCKED

Input-artifact references do not create a second status classifier.

ADR-0005 and ADR-0006 remain authoritative.

At compile time:

- an invalid or unresolvable declared input reference is invalid composition;
- the compiler fails closed;
- the compiler does not convert a malformed composition into a runtime
  `BLOCKED` artifact.

At artifact-production time:

- a required referenced artifact that is unavailable, missing or unverifiable is
  an unavailable prerequisite under ADR-0005;
- therefore it forbids `PASS`;
- absent independently demonstrated nonconformance, that condition supports
  `BLOCKED` under the existing artifact-specific semantics;
- the status value of an available referenced artifact does not itself define
  the consuming artifact's status;
- an available declared static input with `FAIL` or `BLOCKED` status may be
  relevant evidence for the consuming responsibility, but ADR-0006 remains
  authoritative for whether that evidence makes the consuming artifact `PASS`,
  `FAIL` or `BLOCKED`;
- downstream failure artifacts returned only for a later remediation invocation
  are workflow/handoff evidence, not retroactive static input requirements.

A referenced artifact with `PASS` is therefore not by itself sufficient for the
consuming artifact to return `PASS`, and a referenced artifact with `FAIL` does
not create a new generic downstream `FAIL` rule.

Workflow routing based on artifact status remains outside this decision.

### Target preservation

Both existing targets must preserve input-artifact requirements from the
canonical compiled composition.

Producer-facing target output must make each state owner's required governed
input artifacts explicit, including at least:

~~~text
artifactType
producer roleBinding
~~~

Targets may render those canonical semantics in target-appropriate syntax, but
must not:

- omit required inputs;
- replace the producer role binding with an inferred producer;
- reduce a reference to artifact type alone;
- invent target-specific dependency relationships;
- weaken missing-input behavior into optional guidance.

If an enabled target cannot preserve the required semantics, generation must
fail explicitly.

### Current v1 declaration scope

The current four accepted bundles use one governed output artifact per
state-owner role binding. The v1 input declaration therefore belongs to the role
binding's artifact-production responsibility as a whole.

This decision does not introduce per-output dependency variants within one role
binding. It also does not introduce per-invocation or remediation-specific input
variants.

If a later accepted composition requires one binding to produce several artifact
types with materially different input sets, or requires phase-specific governed
inputs for repeated invocations of one binding, that is a concrete future
requirement and can admit a bounded refinement then.

### Initial declarations for the current bundles

The current four accepted bundles have the following canonical static
`inputArtifacts` declarations.

These declarations are part of this decision. The implementation issue must
encode them; it must not choose a different dependency graph from workflow order,
gate order, handoff order or skill prose.

Each entry below uses the canonical identity:

~~~text
(artifactType, roleBinding)
~~~

#### `lean-delivery`

~~~text
requirements:
  []

implementation:
  (Requirements, requirements)

test-execution:
  (ImplementationReport, implementation)
  (Requirements, requirements)

code-review:
  (Requirements, requirements)
  (TestReport, test-execution)

workflow-controller:
  []
~~~

The lean composition has no architecture or QA producer. Code review occurs
after test execution, so its governed test-evidence dependency is the
`TestReport`, not a synthetic architecture or QA dependency.

#### `orchestrated-delivery`

~~~text
requirements:
  []

architecture:
  (Requirements, requirements)

implementation:
  (ArchitectureDecision, architecture)
  (Requirements, requirements)

test-execution:
  (ImplementationReport, implementation)
  (Requirements, requirements)

code-review:
  (ArchitectureDecision, architecture)
  (Requirements, requirements)
  (TestReport, test-execution)

quality-assurance:
  (ArchitectureDecision, architecture)
  (CodeReview, code-review)
  (ImplementationReport, implementation)
  (Requirements, requirements)
  (TestReport, test-execution)

workflow-controller:
  []
~~~

#### `review-heavy-delivery`

~~~text
requirements:
  []

architecture:
  (Requirements, requirements)

implementation:
  (ArchitectureDecision, architecture)
  (Requirements, requirements)

code-review:
  (ArchitectureDecision, architecture)
  (ImplementationReport, implementation)
  (Requirements, requirements)

test-execution:
  (ImplementationReport, implementation)
  (Requirements, requirements)

quality-assurance:
  (ArchitectureDecision, architecture)
  (CodeReview, code-review)
  (ImplementationReport, implementation)
  (Requirements, requirements)
  (TestReport, test-execution)

workflow-controller:
  []
~~~

`review-heavy-delivery` performs code review before independent test execution.
Its pre-test review therefore cannot require a `TestReport` that does not yet
exist. The existing implementation responsibility records implementation-level
validation in `ImplementationReport`, so that report is the governed upstream
artifact available to the pre-test review. Later independent `TestReport`
evidence remains a QA input.

#### `ai-application`

~~~text
requirements:
  []

architecture:
  (Requirements, requirements)

implementation:
  (ArchitectureDecision, architecture)
  (Requirements, requirements)

ai-evaluation:
  (ImplementationReport, implementation)
  (Requirements, requirements)

test-execution:
  (ImplementationReport, implementation)
  (Requirements, requirements)

code-review:
  (ArchitectureDecision, architecture)
  (Requirements, requirements)
  (TestReport, test-execution)

quality-assurance:
  (AIEvaluationReport, ai-evaluation)
  (ArchitectureDecision, architecture)
  (CodeReview, code-review)
  (ImplementationReport, implementation)
  (Requirements, requirements)
  (TestReport, test-execution)

workflow-controller:
  []
~~~

AI evaluation is tied to the declared requirements and the implemented change.
Its own report is independent governed acceptance evidence consumed by QA. The
test and code-review responsibilities do not acquire an AI-evaluation dependency
merely because the workflow places AI evaluation earlier.

For all four bundles:

- the declarations are static prerequisites, not transition edges;
- every listed reference must resolve through the canonical production
  relationship;
- omission of a listed reference is invalid;
- addition of a different required static artifact relationship changes the
  accepted composition semantics and requires an explicit reviewed change;
- later failure artifacts routed back for remediation remain runtime
  workflow/handoff evidence and are not added to these static sets.

## Acceptance scenarios

A later implementation must make at least these scenarios unambiguous.

### 1. No-input producer

A Requirements state owner declares:

~~~json
"inputArtifacts": []
~~~

The composition is valid when its other existing requirements are satisfied.

### 2. One valid upstream production

An Architecture state owner declares:

~~~json
"inputArtifacts": [
  {
    "artifactType": "Requirements",
    "roleBinding": "requirements"
  }
]
~~~

The `requirements` state-owner binding produces `Requirements`.

The reference resolves deterministically to that production relationship.

### 3. Several valid upstream productions

An implementation or QA responsibility may declare several required governed
inputs.

Each reference resolves independently and canonical serialization orders them by
`(artifactType, roleBinding)` regardless of source ordering.

### 4. Artifact type alone

A declaration such as:

~~~json
"inputArtifacts": [
  "Requirements"
]
~~~

is invalid.

The producer identity is required.

### 5. Unknown producer

A reference names a missing role binding.

Validation fails closed.

### 6. Producer/type mismatch

A reference names:

~~~text
artifactType = Requirements
roleBinding = architecture
~~~

but the `architecture` binding produces only `ArchitectureDecision`.

Validation fails closed.

### 7. Controller as producer

A reference names the workflow-controller binding.

Validation fails closed because controllers do not own artifact production.

### 8. Self-reference

A state-owner binding references its own production relationship as an input.

Validation fails closed.

### 9. Dependency cycle

Two or more role bindings form a direct or transitive input-artifact dependency
cycle.

Validation fails closed even if the workflow transition graph has remediation
loops.

### 10. Same artifact type, different producers

Two state-owner bindings both produce the same artifact type.

A consumer must identify the required producer role binding explicitly.

A reference to one producer does not silently bind to the other.

### 11. Referenced artifact unavailable at production time

The static composition is valid, but the required concrete upstream artifact is
not available to the producer.

The producer must not return `PASS` by assumption.

The missing or unverifiable required prerequisite is handled through existing
ADR-0005/0006 `BLOCKED` semantics unless separate positive failure evidence is
already outcome-determining.

### 12. Available upstream non-PASS artifact

A required upstream artifact exists and is verifiable but has status `FAIL` or
`BLOCKED`.

The input reference itself remains satisfied as an availability/lineage
reference. The consuming responsibility evaluates that artifact as evidence
under its existing ADR-0006 status semantics. No generic status propagation is
introduced.

### 13. Concrete upstream revision used as evidence

A producer evaluates a concrete referenced upstream artifact edition.

Where the edition identity is material to reproducing the evaluation, the
producer records the relevant provenance/revision identity in the ADR-0007
evidence `source`.

The compile-time input declaration itself remains revision-neutral.

### 14. Downstream failure returned for remediation

A workflow first invokes `implementation`, then a later test, review or AI
evaluation state produces a failing artifact and routes work back to
`implementation`.

That later failure artifact is not a static `implementation.inputArtifacts`
requirement because it did not exist on the first implementation invocation.

The workflow/handoff may carry that artifact as remediation evidence. The static
input-artifact graph remains acyclic and unchanged.

## Alternatives considered

### Put required input artifacts in `ArtifactContract`

Rejected.

The reusable artifact contract does not own concrete bundle production
relationships. Doing so would couple artifact contracts to role-binding names
and create a second composition authority.

### Reference only the artifact type

Rejected.

The current model can represent more than one production relationship for an
artifact type. Artifact type alone cannot identify which producer relationship
is required.

### Include `agentInstance` in the reference identity

Rejected.

Agent assignment is resolved composition context and provenance evidence.
Reassigning the worker must not silently change the declared dependency identity.

### Include artifact version, path and revision in the bundle declaration

Rejected.

Artifact contract version and path contract are already resolved from canonical
registry state. Concrete path and revision belong to produced runtime material.
Repeating or inventing them in the static declaration would create stale or
unprovable parallel state.

### Infer dependencies from workflow order or gate requirements

Rejected.

Workflow routing and output gate requirements do not state which upstream
artifacts a producer needs. Inference would create hidden semantics and would
couple this decision to the still-separate workflow-routing gap.

### Infer dependencies from responsibilities or skill prose

Rejected.

Free-form instructions are advisory presentation, not canonical composition
authority.

### Add a generic artifact-lineage graph

Rejected.

The accepted need is the smallest governed input dependency required by the
existing delivery model. A generic lineage platform, history graph or artifact
store is outside v1 scope.

### Add produced-artifact persistence to resolve references

Rejected.

The compiler can validate the static production relationship without owning
runtime artifact storage. Persistence, runtime parsing and history remain
separate capabilities requiring their own accepted need.

## Consequences

The composition gains an explicit, target-independent artifact dependency
contract.

The dependency declaration stays with the role binding that owns the consuming
production responsibility.

Artifact contracts remain reusable and composition-independent.

Workflow gates remain output evidence gates rather than upstream dependency
models.

`CompiledComposition` remains the only resolved semantic authority.

The later implementation will require synchronized changes to the existing
bundle/role-binding schema, typed role-binding model, bundle validation,
composition compilation, active-config schema/serialization, both current target
renderers, generated canonical state and focused/integration tests.

Existing role bindings must declare `inputArtifacts` explicitly, including an
empty list where no governed input artifact is required. No compatibility
fallback may treat a missing member as empty.

The implementation does not require an artifact contract version change solely
because the dependency is composition-owned. An artifact contract version must
change only if that implementation separately changes the reusable artifact
contract itself.

The decision does not introduce:

- produced-artifact persistence;
- execution history;
- runtime artifact parsing;
- runtime artifact validation;
- predecessor/supersedes relationships;
- artifact invalidation;
- revision pinning;
- a generic lineage graph;
- hashes, signing, PKI or attestations;
- remote artifact storage;
- workflow-runtime behavior;
- retry or escalation semantics;
- a generic dependency or policy engine;
- a new target platform.

## Implementation boundary

This ADR records semantics only.

A separate implementation issue must define the exact affected repository files,
schema-version consequences, target rendering details, diagnostics and validation
tests.

The implementation must apply the initial `inputArtifacts` declarations defined
by this ADR for the four current bundles. Choosing a different initial dependency
graph is not an implementation detail.

That issue is ready only after this ADR is accepted into `development`.
