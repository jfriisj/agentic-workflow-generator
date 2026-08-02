# ADR-0004: Artifact revision contract semantics

- Status: Accepted
- Date: 2026-08-03

## Context

The project is in post-migration hardening. Accepted scope explicitly includes
artifact revision as one of the remaining artifact-contract gaps.

The current artifact contract already distinguishes:

- `version` as the version of the reusable artifact contract;
- `status` as the state of produced artifact evidence;
- `provenance` as the canonical contract and producer identity carried by a
  produced artifact.

Revision is not currently defined.

Without explicit revision semantics, two successive editions of the same logical
artifact can carry the same contract identity, producer provenance and path while
providing different content. A downstream reader cannot state which edition is
being handed off without relying on timestamps, Git history, filenames,
free-form prose or target-specific conventions.

The revision gap must be closed without turning artifact contracts into a
history store, adding runtime orchestration, inventing timestamps, conflating
revision with contract version, or absorbing the separately deferred
reproducible-evidence and input-artifact-reference concerns.

## Decision

A produced artifact governed by an artifact contract has one explicit revision
marker.

The canonical revision heading is:

~~~text
## Revision
~~~

The canonical revision entry is:

~~~text
revision: <N>
~~~

where `<N>` is a positive base-10 integer using the canonical lexical form:

~~~text
[1-9][0-9]*
~~~

`0`, negative values, signs, decimal values, leading zeroes and free-form
revision labels are invalid.

### Revision meaning

Revision is the ordinal edition of one logical produced artifact.

The logical artifact identity is the tuple:

~~~text
artifactType
artifactVersion
workflow
roleBinding
concrete artifact path
~~~

The concrete `agentInstance` remains provenance evidence about who produced the
edition, but an agent-instance reassignment does not by itself create a new
logical artifact lineage when the governing contract, workflow, role binding
and concrete path are unchanged.

For one logical artifact identity:

1. the first persisted edition has revision `1`;
2. a persisted content change produces the next revision by incrementing the
   previous revision by exactly `1`;
3. re-emitting revision-neutral artifact content unchanged may retain the same
   revision;
4. changing only the revision marker is not a valid reason to advance revision.

For revision comparison, the canonical revision heading and revision entry are
excluded from the compared artifact content. All other artifact content remains
part of the comparison. This revision-neutral comparison prevents the revision
marker itself from being treated as evidence that a new revision was justified.

A revision value therefore identifies an edition. It is not an acceptance
result, a timestamp, a contract version, a Git/VCS revision, a content hash or a
globally unique identifier.

### Contract responsibility

The reusable artifact contract defines the revision requirement, not a concrete
revision number.

The implementation slice must add one typed revision contract to
`ArtifactContract` and one corresponding required `revision` member to the
artifact registry schema. The revision contract must define:

~~~text
heading = "## Revision"
pattern = "^[1-9][0-9]*$"
~~~

`## Revision` must be part of the artifact contract's required headings.

Generated artifact-schema projection, active-config serialization and target
rendering must preserve the same revision requirement deterministically.
Targets must not rename, omit or weaken it.

Because revision becomes a new required contract member, existing artifact
contracts must evolve explicitly to a new contract version when the
implementation is introduced.

### Validation boundary

Validation is fail-closed for revision shape:

- the canonical `## Revision` heading is required;
- exactly one canonical revision entry is present;
- the value matches the canonical positive-integer form.

The compiler must not fabricate a revision value when required evidence is
missing.

The lifecycle rules for first revision and monotonic increment are normative,
but proving them requires a prior edition of the same logical artifact. The
current project does not gain a persistence service, execution-history store or
runtime state solely to perform that comparison.

Where a previous edition is available to an existing validation boundary, a
changed edition must increment by exactly one and unchanged content must not
require an increment. Where no previous edition is available, validation can
prove only the current revision marker's presence and shape.

This limitation must be explicit. A syntactically valid revision number is not
proof of revision history.

## Explicitly deferred

This decision does not define or implement:

- artifact revision history storage;
- a list of prior revisions;
- `supersedes` or predecessor references;
- input-artifact references or dependency lineage;
- evidence hashes or reproducibility attestations;
- timestamps or wall-clock metadata;
- repository commit SHA or VCS revision semantics;
- artifact invalidation;
- retry or escalation semantics;
- workflow-routing changes;
- runtime workflow orchestration;
- new target platforms;
- a generic metadata extension mechanism.

Those concerns require their own accepted need and slice.

## Alternatives considered

### Reuse artifact contract `version` as revision

Rejected. Contract version identifies the reusable evidence contract. Revision
identifies successive produced editions under one specific contract and producer
context. Combining them would destroy both meanings.

### Put revision inside provenance

Rejected. ADR-0002 deliberately fixed provenance to contract and producer
identity. Revision describes edition lifecycle and must not silently expand the
provenance identity set.

### Use a timestamp

Rejected. Timestamps are nondeterministic, do not prove edit order reliably
across producers, and introduce time semantics not required by the accepted
gap.

### Use a content hash as revision

Rejected for this slice. A hash is content identity and belongs to the separate
reproducible-evidence concern. It does not express ordinal revision semantics.

### Use Git commit SHA

Rejected. Artifact semantics must remain target- and VCS-independent. A produced
artifact may exist before commit, outside Git, or be revised without a one-to-one
commit relationship.

### Add persistent revision history now

Rejected. The accepted gap is revision, not a history service. Adding stateful
history solely to validate monotonicity would expand the architecture beyond the
minimum required contract.

### Allow arbitrary revision labels

Rejected. Values such as `draft-2`, `vFinal` or timestamps create weak semantics,
sorting ambiguity and producer-specific conventions.

## Consequences

Produced artifacts gain an explicit, target-independent edition identity.

Contract version remains the reusable contract identity. Status remains the
artifact result. Provenance remains producer evidence. Revision has one separate
responsibility.

A changed artifact can be handed off as a specific ordinal edition without
requiring timestamps, VCS metadata or target-specific filename conventions.

The compiler can validate revision presence and syntax deterministically.
Monotonic history validation remains conditional on an existing prior edition;
the project does not pretend to prove history it does not possess.

Existing artifact contracts require explicit contract-version evolution when the
new required revision contract is implemented.

No new technology, service, datastore, target abstraction or runtime engine is
required.

## Acceptance scenarios

An implementation conforming to this decision must satisfy at least these
scenarios:

1. Every artifact contract carries the canonical revision requirement.
2. A produced artifact missing `## Revision` is invalid.
3. A produced artifact missing the canonical `revision:` entry is invalid.
4. Revision `1` is valid.
5. Revision `0`, `-1`, `+1`, `01`, `1.0` and free-form labels are invalid.
6. Contract version and artifact revision remain separate values.
7. Artifact status changes do not redefine revision semantics; a persisted
   content change advances revision regardless of whether status becomes
   `PASS`, `FAIL` or `BLOCKED`.
8. When a prior edition of the same logical artifact is available, changed
   content advances revision by exactly one.
9. Re-emitting unchanged revision-neutral artifact content may retain the same
   revision.
10. A change only to the revision heading or revision entry does not justify a
    new revision.
11. Reassigning the concrete agent instance does not reset revision when the
    contract version, workflow, role binding and concrete artifact path remain
    unchanged.
12. Changing artifact contract version creates a new logical artifact identity
    for revision purposes.
13. Targets cannot invent different revision formats or weaker requirements.
14. No revision-history store, timestamp, VCS identity, evidence hash or
    input-artifact lineage is introduced by this slice.
