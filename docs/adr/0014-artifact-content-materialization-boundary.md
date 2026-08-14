# ADR-0014: Artifact content production and materialization boundary

- Status: Accepted
- Date: 2026-08-13
- Accepted baseline: `development` @ `d96c2050046784869e50b97b82e11fa232fe15af`
- Decision issue: #60
- Goal: #48

## Summary

Artifact production and artifact persistence are distinct responsibilities.

A state-owner role binding that declares `produces` owns the complete governed
artifact content and its classification under the applicable artifact contract.
That ownership does **not** imply that the producing agent instance has direct
repository-file write permission.

The producing agent's effective permission profile remains authoritative for the
actions that agent may perform directly. When that profile does not permit the
repository mutation required to place produced content at a concrete path
matching the artifact contract's `pathPattern`, the agent must not bypass or
reinterpret its permission boundary. Instead, it returns the complete
contract-conformant artifact content through the target/framework handoff to a
persistence step performed outside that agent instance's permission profile.

That persistence step is part of the surrounding target execution boundary or
its caller, not a new agentic-workflow-generator runtime service, role binding,
capability, permission profile, or compiler responsibility. It must materialize
the producer-owned content without changing its governed semantics and make the
resulting artifact available to downstream consumers.

Downstream dispatch must remain fail closed. A required produced artifact is
available only after its complete content has been successfully materialized at
a concrete location satisfying its artifact contract and is readable by the
next governed consumer. If the target/framework boundary cannot establish that
materialization, the producing state must not claim `PASS`; the unavailable
materialization prerequisite yields `BLOCKED` under the existing artifact status
semantics unless independently reproducible evidence already requires `FAIL`.

This decision preserves ADR-0013 unchanged: `AIEvaluator` remains read-only and
no-shell. No producer permission is broadened merely to make an
`agent-output/.../*.md` path directly writable.

## Context

Goal #48 requires accepted V1 registry compositions to describe behavior that is
actually validated, compiled and representable in generated targets.

Research #49 found that, across the four default compositions, 15
composition-local state-owner bindings simultaneously:

1. own a produced artifact whose contract has an `agent-output/.../*.md`
   `pathPattern`; and
2. use the effective `read-only` permission profile with `write=false`,
   `edit=false`, and `bash=deny`.

The current target renderers preserve both facts. Generated agent instructions
render the compiled produced-artifact contract and output path pattern, while
OpenCode and VS Code Copilot preserve the effective read-only permission
boundary rather than silently broadening it.

The existing accepted model already establishes several relevant ownership
rules:

- artifact production belongs to role bindings;
- concrete producer identity is resolved in `CompiledComposition`;
- artifact provenance records the producing role binding and agent instance but
  does not create a second ownership authority;
- a concrete input-artifact reference points to a compiled production
  relationship, not to a persisted runtime artifact instance;
- concrete produced paths and revisions are runtime material and are not part of
  the static input-reference identity;
- effective permissions belong to agent instances and must not be silently
  broadened by targets;
- the compiler is a deterministic compiler and target generator, not an
  autonomous workflow runtime.

What remained undefined was the runtime/materialization boundary between
"this role binding produces the artifact" and "a concrete artifact edition is
persisted at a path where downstream consumers can read it."

Without an explicit boundary, one could incorrectly infer either that
`produces` grants repository write authority or that an `agent-output/...` path
can be ignored when the producer is read-only. Both would make accepted V1
semantics dishonest.

## Decision

### 1. `produces` owns artifact content, not implicit write permission

A state-owner role binding that declares an artifact type in `produces` owns:

- constructing the complete artifact content required by the compiled artifact
  contract;
- evaluating the evidence relevant to that artifact;
- selecting the artifact's canonical `PASS`, `FAIL`, or `BLOCKED` status under
  the existing artifact-specific status semantics;
- supplying the provenance identities already derived from the canonical
  compiled production relationship;
- supplying the artifact revision under the existing revision contract;
- returning the complete artifact content as the result of its governed
  production responsibility.

`produces` does not grant, imply, or synthesize `write`, `edit`, shell, or any
other target operation.

The producing `AgentInstance.permissionProfile` remains the sole canonical
authority for actions performed directly by that agent instance.

### 2. Persistence/materialization is a separate execution responsibility

Materialization means taking the producer-owned complete artifact content and
making one concrete artifact edition available at a location satisfying the
artifact contract's `pathPattern`.

Materialization is an execution concern of the surrounding target framework or
its caller. It is outside the producing agent instance's permission profile when
the producer lacks the direct repository mutation required to perform that step.

This boundary does not introduce a new domain entity or runtime component in
`agentic-workflow-generator`. In particular, this ADR does not add a
`Materializer` agent, persistence service, artifact store, workflow engine,
compiler-side filesystem writer, or target-registry capability.

The target/framework boundary may satisfy materialization through whatever
mechanism is already available in that execution environment or its caller,
provided that mechanism:

- does not broaden the producer's effective permissions;
- does not alter producer ownership of the artifact content;
- does not reinterpret artifact status, provenance, revision, evidence, or
  required headings;
- writes or otherwise persists only a concrete edition that satisfies the
  compiled artifact contract and its `pathPattern`;
- makes that concrete edition readable to the governed downstream consumer.

The mechanism itself is deliberately not standardized by this ADR because the
product does not own runtime orchestration and the two supported targets have
different execution hosts.

### 3. Read-only producers use a mediated artifact handoff

When a producing state owner lacks direct repository mutation permission, its
governed completion sequence is:

~~~text
compiled production responsibility
    -> state owner constructs complete artifact content
    -> state owner returns that content through the target/framework handoff
    -> target/framework caller materializes one concrete artifact edition
    -> materialized edition is confirmed available to the governed consumer
    -> state result may be returned to the workflow controller
~~~

The handoff carries the artifact content governed by the existing contract and
compiled production relationship. This ADR does not introduce a second artifact
envelope, metadata schema, status record, or persistence manifest.

The artifact's existing provenance block remains the durable producer identity.
The existing compiled production relation remains the static ownership
authority.

### 4. Materialized availability is required before downstream dispatch

A compile-time input-artifact reference proves only that the referenced
production relationship exists in the accepted composition. ADR-0010 remains
unchanged: the compiler does not prove that a concrete runtime artifact edition
has already been produced or persisted.

At runtime, a required governed input artifact is available only when a concrete
edition:

- has complete content satisfying its governing artifact contract;
- has been materialized at a concrete location satisfying the contract's
  `pathPattern`;
- is readable by the consuming state owner through its effective target
  permissions; and
- can be identified with the existing provenance/revision/evidence semantics
  when those details are required by the consuming responsibility.

A response containing proposed artifact content is therefore not, by itself,
proof that downstream materialized input is available.

The workflow controller must not dispatch a downstream state whose required
input artifact has not crossed this materialization boundary.

This rule does not make the controller the artifact writer. The controller
remains routing-only under the accepted workflow model.

### 5. Fail-closed materialization behavior

Failure to materialize required produced content is an unavailable prerequisite,
not permission to claim success.

If the target/framework boundary cannot persist the complete artifact content at
a contract-conformant location or cannot make it readable to the governed
consumer, the producing state must not return `PASS`.

Under the existing shared and artifact-specific status contracts:

- unavailable materialization prevents `PASS`;
- absent independently demonstrated nonconformance, the state returns
  `BLOCKED`;
- independently demonstrated outcome-determining nonconformance remains `FAIL`
  under `FAIL_ON_DEMONSTRATED_NONCONFORMANCE` even if materialization is also
  unavailable.

A target must not silently continue with conversation-only content, an invented
fallback path, an ungoverned temporary file, or a stale earlier artifact edition
when the required current edition has not been materialized.

### 6. Effective permissions remain unchanged

This decision does not broaden any current permission profile.

For read-only state owners:

~~~text
read  = true
write = false
edit  = false
bash  = deny
~~~

continues to mean that the agent itself cannot directly perform repository
mutation or shell execution.

A target/framework persistence operation performed outside that agent instance
must not be exposed back to the agent as an undeclared write/edit/shell tool.

Writable producers may continue to use operations already granted by their
effective permission profile, but direct self-materialization is not required by
the meaning of `produces` and must not become a hidden condition of artifact
ownership.

### 7. ADR-0013 remains authoritative for AIEvaluator

`AIEvaluator` remains an evidence-review boundary with the accepted read-only,
no-shell permission profile.

It may construct complete `AIEvaluationReport` content from governed inputs and
available reproducible evidence, but this ADR does not authorize it to:

- write repository files directly;
- invoke shell commands;
- execute evaluation jobs;
- mutate project state; or
- request broader permissions merely to persist its report.

Its produced report crosses the same mediated materialization boundary as any
other read-only producer.

If required report materialization cannot be established, the AI-evaluation
state cannot return `PASS`.

### 8. Compiler responsibility remains static and deterministic

The compiler continues to validate and preserve:

- artifact contracts;
- role-binding `produces` relationships;
- resolved `CompiledArtifactProduction` ownership;
- input-artifact references;
- effective permission profiles;
- workflow gate ownership and required artifacts; and
- enabled target mappings.

The compiler does not:

- execute artifact-producing agents;
- persist runtime artifact content;
- select a concrete runtime path for an artifact edition;
- verify that a runtime edition has been materialized;
- broaden permissions to make a path writable; or
- create runtime state/history solely to track materialization.

No new member is added to `CompiledComposition`, artifact contracts, role
bindings, permission profiles, target adapters, or active-config serialization
by this decision alone.

### 9. Target preservation requirement

Both current targets must represent the complete boundary from canonical
compiled data and contracts.

For an artifact-producing agent they must preserve at minimum:

- the producer role binding and agent-instance identity;
- the produced artifact type and complete artifact contract requirements;
- the artifact `pathPattern`;
- the effective permission profile;
- that artifact content production does not override the permission profile;
- for a producer without direct repository mutation permission, that the agent
  returns complete artifact content for target/framework-mediated
  materialization rather than attempting a forbidden write;
- that downstream dispatch requires confirmed materialized availability; and
- that unavailable materialization prevents `PASS` and fails closed as
  `BLOCKED` unless independently demonstrated nonconformance requires `FAIL`.

Targets may express the handoff in platform-appropriate instructions. They must
not invent a different ownership model or weaker fallback semantics.

If an enabled target cannot preserve this boundary, generation must fail
explicitly rather than silently broaden permissions or omit the materialization
requirement.

The current renderers already preserve producer identity, artifact contract,
`pathPattern`, and effective permissions separately. They do not yet state the
mediated materialization/handoff rule explicitly. A later implementation slice
is therefore required before Goal #48 can claim complete target preservation of
this decision.

### 10. Static invalidity versus runtime `BLOCKED`

These failure classes remain distinct.

Static invalidity includes malformed or inconsistent accepted composition, for
example:

- an unresolved produced artifact contract;
- inconsistent gate/artifact ownership;
- an invalid permission profile or target mapping; or
- a target that cannot represent a required compiled semantic.

Those failures stop compilation or generation and do not become runtime
artifacts.

Runtime `BLOCKED` includes a statically valid composition in which the produced
artifact content cannot be materialized or made available to the governed
consumer during execution.

The compiler must not reject a state owner merely because its accepted effective
permission profile is read-only while it owns artifact content production. That
combination is valid under the mediated materialization boundary defined here.

## Alternatives considered

### Broaden every artifact producer to repository-write permissions

Rejected. Artifact ownership does not imply direct file-write authority, and
permission broadening would violate the existing effective-permission model. It
would also directly contradict ADR-0013 for `AIEvaluator`.

### Treat read-only artifact producers as invalid composition

Rejected. The existing composition intentionally separates role responsibility
from agent permissions. Research #49 found no accepted authority saying that
artifact ownership requires self-materialization, and current targets can
preserve a mediated handoff without weakening permissions.

### Make the workflow controller persist artifacts

Rejected. The controller is routing-only, owns no workflow state or gate, and
must not gain hidden artifact-production or repository-write responsibility.

### Add a generator-owned runtime materialization service

Rejected. `agentic-workflow-generator` is a deterministic compiler and target
generator, not an autonomous workflow runtime. A persistence service, artifact
store, runtime workflow engine, or materialization daemon would be a new product
capability outside this decision and current scope.

### Consider conversation output alone to be the materialized artifact

Rejected. Artifact contracts carry explicit output `pathPattern` semantics and
downstream input-artifact relationships rely on governed workflow memory.
Conversation-only content does not prove that the required concrete edition is
available at the governed artifact boundary.

### Leave the persistence actor unspecified and continue implicitly

Rejected. That is the ambiguity identified by research #49. Accepted V1 target
semantics must state where the producer's responsibility ends, where persistence
occurs, and what happens when persistence is unavailable.

## Consequences

The existing role-binding ownership model remains intact: role bindings own
artifact content production, while effective permissions continue to govern the
actions an agent instance may perform directly.

Read-only artifact producers remain valid without hidden permission broadening.
In particular, ADR-0013's AIEvaluator boundary remains unchanged.

Artifact persistence becomes an explicit target/framework execution boundary
rather than an implied agent capability. This closes the conceptual ambiguity
without adding runtime orchestration to the compiler product.

No artifact contract version changes are required by this decision because the
artifact content schema, status fields, provenance identities, revision syntax,
evidence fields, and `pathPattern` contract are unchanged.

No active-config or registry schema change is required by this decision alone.

The target renderers require a later bounded implementation to state and enforce
the mediated materialization/handoff semantics explicitly. That implementation
must preserve current permission mappings and must not add new target platforms,
roles, capabilities, services, or compiler runtime behavior.

Because this ADR records a decision before that target-rendering implementation,
`docs/architecture.md`, `docs/architecture/workspace.dsl`, and the detailed core
domain current-state narrative are not changed in this decision PR. They must
not present planned renderer behavior as implemented current state. Any later
implementation that changes current semantic architecture must synchronize the
applicable current-state authority under `docs/governance.md`.

## Acceptance scenarios

A conforming implementation of this decision must satisfy at least these
scenarios:

1. A read-only state owner can remain the canonical producer of an artifact
   without gaining write/edit/shell permission.
2. Generated OpenCode output preserves the producer's read-only permission
   mapping and explicitly instructs mediated materialization of the complete
   produced artifact content.
3. Generated VS Code Copilot output preserves the producer's read-only tool set
   and explicitly instructs the same platform-neutral materialization boundary.
4. `AIEvaluator` remains read-only/no-shell and can still own
   `AIEvaluationReport` content production.
5. A producer with insufficient direct write permission is never instructed to
   bypass its permission profile to satisfy `pathPattern`.
6. A materialization failure prevents `PASS` and yields `BLOCKED` unless existing
   evidence independently requires `FAIL`.
7. A downstream state is not dispatched when a required input artifact has only
   been proposed in conversation but has not been materialized and made
   readable.
8. A target cannot silently choose an ungoverned fallback path or stale artifact
   edition when the required current edition is unavailable.
9. The compiler does not acquire runtime persistence, concrete-path selection,
   artifact-history, or workflow-orchestration responsibility.
10. Existing artifact contracts, input-artifact references, provenance,
    revision, evidence, status semantics, role-binding ownership, controller
    routing, and permission profiles remain authoritative without a parallel
    materialization model.
