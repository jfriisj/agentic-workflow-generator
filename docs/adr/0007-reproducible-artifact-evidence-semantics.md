# ADR-0007: Reproducible artifact evidence semantics

- Status: Accepted
- Date: 2026-08-03

## Context

The current governed artifact contracts already define:

- canonical provenance;
- revision;
- shared status invariants from ADR-0005; and
- artifact-specific status semantics from ADR-0006.

Those decisions make evidence outcome-determining. `PASS` requires complete
required evidence, `FAIL` requires demonstrated nonconformance, and `BLOCKED`
requires an unavailable, missing, or unverifiable prerequisite.

The repository does not yet define what makes evidence reproducible at the
existing artifact-production boundary.

Some artifact formats already expose evidence-oriented sections. `TestReport`
records test commands and results, `QAReport` records evidence reviewed, and
`AIEvaluationReport` records evaluation data, scenarios, metrics, thresholds,
results, safety analysis, and operational evidence. Other artifacts express
their supporting material through their domain-specific sections.

Leaving reproducibility entirely to free-form producer prose creates three
problems:

1. a status claim can cite an observation without identifying what was
   evaluated;
2. another evaluator may be unable to repeat the evaluation from the recorded
   information; and
3. target output can preserve the status rules while still losing the evidence
   needed to justify the selected status.

The decision must strengthen the existing artifact contract without introducing
produced-artifact persistence, execution history, runtime validation, input
lineage, cryptographic attestation, or a generic evidence platform.

## Decision

Every governed artifact has one canonical reproducible-evidence contract in
addition to provenance, revision, status invariants, and artifact-specific
status semantics.

### Meaning of reproducible evidence

Evidence is reproducible when its record contains enough concrete information
for another competent evaluator, with access to the same referenced source and
materially relevant conditions, to repeat the evaluation and establish the same
status-relevant observation.

Reproducibility does not require byte-identical logs or output. It requires the
status-relevant observation to be independently re-establishable.

The contract records how an observation can be reproduced. It does not create a
repository responsibility to persist external sources, execution history, test
environments, model invocations, or produced artifacts.

If a status-determining source or condition is materially ambiguous,
unavailable, or not identifiable well enough to repeat the evaluation, that
evidence is unverifiable for the claim it is meant to support.

### Canonical evidence record

The future implementation must add one typed evidence contract with the
canonical heading:

~~~text
## Evidence
~~~

Every status-determining evidence record has exactly these required semantic
fields:

~~~text
claim
source
reproduction
result
~~~

The `## Evidence` section contains one or more evidence records. The record
set must cover every status-determining condition used to classify the artifact.
Materially independent conditions must not be collapsed into a summary that
prevents each status-relevant observation from being reproduced independently.

Their meanings are:

- `claim` identifies the requirement, criterion, contract condition, or
  prerequisite whose evaluation the record supports.
- `source` identifies the concrete material evaluated. It may identify code,
  configuration, a requirement, a file, a dataset, a scenario, an environment,
  an upstream result, or another evidence source. Where a version, revision,
  dataset identity, model/configuration identity, or other stable qualifier is
  material and available, it belongs in this field.
- `reproduction` states the concrete procedure needed to repeat the
  evaluation. It is an executable command when execution is the evidence
  method, and a deterministic inspection, comparison, or review procedure when
  the evidence is non-executable. Material tool versions, environment
  conditions, seeds, thresholds, or evaluation conditions belong here when
  they affect the observation.
- `result` records the observed outcome. It records the observation rather than
  re-defining the artifact status policy.

The evidence record deliberately has no `status`, `pass`, `fail`, `blocked`, or
policy-expression member.

ADR-0005 and ADR-0006 remain the only artifact-status authorities. Evidence
records supply observations to that classification contract; they do not become
a second classifier.

### Artifact representation

The canonical artifact contract representation is:

~~~text
evidence.heading = "## Evidence"
evidence.requiredFields = [
  "claim",
  "source",
  "reproduction",
  "result"
]
~~~

The heading and required field set are canonical policy, not configurable
artifact variants.

The later implementation must preserve this contract through the existing
artifact registry, typed domain representation, generated artifact schemas,
active configuration, both existing target renderers, generated output, and
canonical lock/manifest state where affected.

Existing artifact-specific sections such as `## Test Commands`, `## Test
Results`, `## Evidence Reviewed`, or AI-evaluation sections remain useful
domain-specific report structure. They do not replace the common evidence
contract and must not define conflicting evidence semantics.

Because the evidence object and heading become required artifact-contract
members, all existing governed artifact contract versions must evolve
explicitly when the implementation is introduced.

### Status interaction

The evidence contract preserves ADR-0005 and ADR-0006.

For `PASS`:

- every status-determining condition required by the artifact-specific
  `passDefinition` must be supported by reproducible evidence;
- missing, ambiguous, or unverifiable required evidence forbids `PASS`; and
- absence of a known failure is not evidence.

For `FAIL`:

- at least one reproducible evidence record must positively establish the
  demonstrated nonconformance required by the artifact-specific
  `failDefinition`;
- a missing source or procedure alone does not become `FAIL`; and
- the ADR-0006 mixed-condition rule still makes demonstrated required
  nonconformance outcome-determining when another prerequisite is unavailable.

For `BLOCKED`:

- the evidence record must identify the required prerequisite that cannot be
  established;
- `source` identifies the prerequisite or evidence source that is required;
- `reproduction` identifies how the prerequisite would be evaluated or how its
  availability is checked; and
- `result` records that the prerequisite is unavailable, missing, stale, or
  otherwise unverifiable.

Recording a blocked prerequisite does not fabricate the missing underlying
evidence.

Advisory observations may be recorded as evidence but do not independently
force `FAIL` unless they satisfy the artifact-specific `failDefinition`.

### Source identity and input-artifact references

Evidence source identity and governed input-artifact lineage are separate
concerns.

This decision requires a source to be identified concretely enough for the
recorded evaluation to be repeated. It does not define:

- a typed `inputArtifact` relationship;
- dependency lineage between governed artifacts;
- predecessor/supersedes relationships;
- a graph of artifact dependencies; or
- persistence used to resolve such references.

If a governed artifact is used as evidence, the evidence record may identify it
using information already available to the producer. A later input-artifact
reference decision may formalize lineage separately without changing the
meaning of reproducible evidence.

### Hashes, attestations, and timestamps

Cryptographic hashes are not mandatory evidence fields.

A digest can help identify immutable bytes when one is already available, but a
digest alone does not say what claim was evaluated, how the evaluation was
performed, or what result was observed. Mandating hashes would also imply
content capture and verification responsibilities that the current compiler
does not own.

Signatures, attestations, PKI, timestamps, execution IDs, and VCS identities are
not introduced by this decision.

They may appear as source detail when already available and materially useful,
but they are not new canonical evidence-contract members.

### Validation boundary

Compiler validation is fail-closed for the reproducible-evidence contract
itself:

- the evidence object is required;
- the canonical heading is required;
- all four canonical required fields are required;
- fields may not be omitted, renamed, weakened, or replaced with a target-
  specific variant;
- generated artifact schemas must preserve the source contract;
- active configuration must preserve the source contract; and
- enabled target output must preserve producer-facing evidence semantics.

The current compiler does not ingest arbitrary produced Markdown artifacts as
runtime state.

Therefore this decision does not claim that compiler validation can prove the
truth, completeness, or reproducibility of actual evidence text that is not
available at an existing validation boundary.

Producer-facing target instructions must require status-determining evidence to
follow the canonical record semantics and must fail closed when the producer
cannot establish the required source, reproduction procedure, or result.

Adding a parser, persistence service, execution-history store, remote evidence
store, or runtime evidence validator requires a separate accepted need.

## Acceptance scenarios

The later implementation must make at least these scenarios unambiguous:

1. A `TestReport` records the tested claim, concrete code/configuration source,
   exact required validation command, material execution conditions, and the
   observed passing result. The evidence can support `PASS`.
2. A required test executes and the record identifies the source, command, and
   observed failing result. That positive evidence can satisfy the
   artifact-specific `FAIL` definition.
3. A `QAReport` says only that "tests passed" without identifying the source or
   reproduction procedure. The evidence is insufficient for `PASS`.
4. An AI evaluation records a metric result but omits a materially required
   dataset, model/configuration identity, threshold, seed, or evaluation
   condition needed to repeat the observation. The affected criterion remains
   unverifiable and cannot support `PASS`.
5. Requirements contain a demonstrated contradiction whose source statements
   and comparison procedure are recorded reproducibly. That evidence remains
   `FAIL` even when another required requirements input is unavailable.
6. A hash is recorded without a claim, reproduction procedure, and observed
   result. The hash alone is not sufficient reproducible evidence.
7. A `CodeReview` records an advisory observation reproducibly. The evidence
   remains advisory unless it satisfies the artifact-specific blocking
   `failDefinition`.
8. A required prerequisite is unavailable. The record identifies the
   prerequisite, how availability or applicability would be checked, and the
   observed unavailability without fabricating the missing evidence. The
   artifact can be `BLOCKED`.
9. Compiler validation proves the canonical evidence contract is preserved
   through registry/schema/config/target boundaries but does not claim to prove
   arbitrary produced Markdown evidence that it does not ingest.

## Alternatives considered

### Require only free-form evidence prose

Rejected. Free-form prose cannot guarantee that a claim, source, reproduction
procedure, and observed result are all present, and target adapters could
silently lose one of those semantics.

### Require commands for every evidence record

Rejected. Requirements analysis, architecture decisions, code review, and QA
may rely on deterministic inspection or comparison rather than executable
commands. `reproduction` therefore represents the repeatable evaluation
procedure, not necessarily shell execution.

### Make cryptographic hashes mandatory

Rejected. Hashes establish byte identity, not evaluation meaning or outcome,
and mandatory hashing would create content-capture and verification
responsibilities not owned by the current compiler.

### Add input-artifact lineage at the same time

Rejected. Evidence source identification is required for reproducibility, but
typed dependency lineage is the separate remaining artifact-contract gap and
must be decided independently.

### Add runtime artifact validation or persistence

Rejected. The current product is a deterministic compiler for validated agentic
development configurations, not an autonomous artifact runtime or evidence
store. No accepted requirement justifies a new runtime boundary for this slice.

## Consequences

Reproducible evidence becomes a canonical artifact-contract concern rather than
target- or skill-specific prose.

The later implementation can remain within the existing compiler boundary:
typed contract, fail-closed registry/schema validation, deterministic
serialization, target preservation, generated-output synchronization, and
tests.

Status classification remains owned by the existing artifact contract plus
producing role binding. Workflow controllers remain routing-only.

Input-artifact references remain the next separate artifact-hardening concern.
No persistence, execution history, signing infrastructure, runtime validator,
generic evidence engine, or new target is authorized.
