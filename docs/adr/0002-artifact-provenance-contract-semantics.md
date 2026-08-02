# ADR-0002: Artifact provenance contract semantics

- Status: Proposed
- Date: 2026-08-02

## Context

The current project phase is post-migration hardening. Accepted scope explicitly
includes strengthening the existing artifact model for provenance while
preserving the current deterministic, fail-fast compiler boundary.

An artifact contract currently defines artifact type, contract version,
description, output path pattern, status contract, allowed statuses and required
headings. Artifact production is owned by role bindings, and the compiled
composition already identifies the workflow, concrete role binding and concrete
agent instance participating in artifact production.

The current artifact contract does not define how a produced artifact records
its own origin. This means a downstream reader can see an artifact's content and
status but cannot reliably prove, from the artifact itself, which accepted
contract and compiled workflow identity produced that evidence.

The provenance gap must be closed without introducing a second ownership model,
runtime orchestration, target-specific semantics, timestamps, generic metadata
bags or input-artifact dependency semantics.

This decision is intentionally limited to provenance. The separately accepted
artifact-hardening gaps for revision, reproducible evidence requirements,
input-artifact references and artifact-specific status semantics remain separate
slices.

## Decision

A produced artifact governed by an artifact contract must carry one canonical,
target-independent provenance block.

The canonical provenance heading is:

~~~text
## Provenance
~~~

The provenance block contains exactly these required identities:

~~~text
artifactType
artifactVersion
workflow
workflowVersion
roleBinding
agentInstance
~~~

Their semantics are:

1. `artifactType` identifies the artifact contract type.
2. `artifactVersion` identifies the version of that artifact contract.
3. `workflow` identifies the compiled workflow in which the artifact is
   produced.
4. `workflowVersion` identifies the compiled workflow version.
5. `roleBinding` identifies the concrete compiled role binding that owns
   production of the artifact.
6. `agentInstance` identifies the concrete compiled agent instance assigned to
   that role binding.

These values are provenance evidence, not a new ownership authority. Artifact
production continues to belong to role bindings. The artifact contract defines
what provenance must be recorded; the compiled composition remains authoritative
for the concrete workflow, role-binding and agent-instance identities.

The provenance identities must be derived from the canonical compiled
composition and the artifact-production relationship already represented there.
A target renderer, agent profile, free-form user value or fallback rule must not
invent or reinterpret them.

The artifact contract registry representation must make provenance explicit.
The implementation slice must add one typed provenance contract to
`ArtifactContract` and one corresponding required `provenance` member to the
artifact registry schema. That member must define the canonical provenance
heading and the fixed required identity set above. It is not an open-ended
metadata extension point.

The generated artifact-schema projection must preserve the same provenance
contract deterministically, and active-config serialization must carry the
provenance contract as part of the canonical compiled artifact representation.

Target rendering must present the provenance requirement from the canonical
compiled artifact contract. Targets must not define different provenance fields
or weaker provenance requirements.

When produced artifact content is validated against its contract, provenance is
fail-closed:

* the `## Provenance` heading is required;
* every required provenance identity is present exactly once;
* `artifactType` and `artifactVersion` match the governing artifact contract;
* `workflow` and `workflowVersion` match the canonical compiled workflow;
* `roleBinding` and `agentInstance` match the compiled artifact-production
  relationship;
* missing, duplicated, conflicting or mismatched provenance is invalid.

No compatibility fallback is introduced for artifacts that omit provenance.
Existing artifact contracts must evolve explicitly to a new contract version
when provenance becomes required. The implementation must keep registry
contracts, generated artifact schemas, typed domain models, active-config schema,
serialization, target rendering and affected tests synchronized.

## Explicitly deferred

This decision does not define or implement:

* artifact revision or revision history;
* input-artifact references or dependency lineage;
* evidence hashes, evidence payload schemas or reproducibility attestations;
* timestamps, wall-clock creation metadata or execution duration;
* repository commit SHA or VCS revision semantics;
* retry, escalation or artifact invalidation;
* workflow-routing changes;
* new target platforms;
* runtime workflow orchestration;
* a generic metadata or plugin extension mechanism.

Those concerns require their own accepted slices when reached.

## Alternatives considered

### Keep provenance implicit in role bindings and generated agent identity

Rejected. The compiled composition knows the producer relationship, but the
produced artifact itself would remain non-self-describing. That does not close
the accepted artifact provenance gap.

### Put producer ownership inside the artifact contract

Rejected. Artifact production already belongs to role bindings. Moving producer
ownership into the artifact contract would create competing authority and
contradict the existing domain boundary.

### Record only artifact type and version

Rejected. Contract identity alone identifies the format but not the concrete
workflow production context. It cannot distinguish which compiled producer
created the evidence.

### Record arbitrary provenance key-value metadata

Rejected. An open-ended metadata bag would create weak semantics, target drift
and speculative extensibility. The current requirement needs a small fixed
identity contract.

### Require timestamps as provenance

Rejected. Wall-clock values are not required to identify the accepted producer
relationship and introduce nondeterministic data. Time semantics may be admitted
later only through a concrete requirement.

### Include input-artifact references in provenance

Rejected for this slice. Input-artifact references are a separately identified
artifact-contract gap with different validation and lifecycle semantics.
Combining them would make this decision larger than the minimum coherent
provenance slice.

### Include repository revision or evidence hashes now

Rejected for this slice. Revision and reproducible evidence are separately
identified hardening concerns. Their semantics must not be guessed while closing
the provenance identity gap.

## Consequences

Produced artifacts become self-describing with respect to the contract and
compiled producer identity that created them.

The compiler remains the single semantic authority. Provenance values are
carried from canonical compiled identities rather than re-derived by targets.

Artifact production ownership remains unchanged: role bindings own production,
while artifact contracts define the evidence shape that produced artifacts must
satisfy.

All existing artifact contracts will require explicit version evolution when
the provenance requirement is implemented. This is intentional; provenance is a
new required contract and must not be introduced as a silent compatibility
change.

The implementation will touch several synchronized representations, but it does
not require a new service, datastore, runtime engine, target abstraction or
technology.

The fixed provenance identity set is deliberately narrow. New provenance fields
require a concrete accepted need and explicit contract evolution rather than
being added through an untyped extension mechanism.

## Acceptance scenarios

A provenance implementation conforming to this decision must satisfy at least
these scenarios:

1. The same canonical compiled artifact-production relationship produces the
   same provenance requirement for every enabled target.
2. A produced artifact missing `## Provenance` fails artifact validation.
3. A produced artifact missing any required provenance identity fails
   validation.
4. A produced artifact whose artifact type or contract version disagrees with
   the governing contract fails validation.
5. A produced artifact whose workflow identity disagrees with the canonical
   compiled workflow fails validation.
6. A produced artifact whose role binding or agent instance disagrees with the
   compiled artifact-production relationship fails validation.
7. A target cannot omit, rename or weaken provenance fields independently.
8. Artifact production ownership remains defined only by the existing
   role-binding relationship.
9. Revision, input-artifact references and evidence-hash semantics remain absent
   until separately accepted.
