# ADR-0009: Canonical architecture model and rendering contract

- Status: Accepted
- Date: 2026-08-03

## Context

ADR-0008 requires Milestone 1 to establish a concise current-state architecture
narrative and exactly one canonical architecture model. It deliberately leaves
the model notation and toolchain to a separate decision.

ADR-0003 currently makes the detailed PlantUML sources under
`docs/diagrams/domain/` authoritative and defines a reproducible stakeholder SVG
rendering contract based on pinned PlantUML, Smetana and DejaVu inputs.

Issue #27 evaluated Structurizr DSL and the current Structurizr vNext toolchain.
The research established that:

- the legacy Structurizr CLI is end-of-life;
- Structurizr `2026.06.28` exposes consolidated `validate` and `export`
  commands;
- the official Linux/amd64 Docker image was exercised successfully;
- the tested image digest was
  `sha256:251905a1a2d73195e84b784966babc71b329223fdbb25368261a9e3ba39041c4`;
- a modular DSL workspace using local `!include`, hierarchical identifiers,
  explicit view keys and `autoLayout` validates locally;
- an unresolved relationship destination fails validation with a non-zero exit
  status;
- repeated PlantUML textual exports were byte-identical for the research
  fixture;
- repeated JSON exports were byte-identical for the research fixture;
- manually adjusted layout is persisted in `workspace.json`, not solely in DSL;
- native Structurizr PNG/SVG automation introduces a browser/Playwright
  boundary that was not proven as the preferred repository rendering contract;
- retaining ADR-0003 remains a valid lower-footprint alternative.

The project must now select one architecture-model technology and define the
boundary between semantic architecture authority and stakeholder-facing derived
rendering before migration implementation begins.

## Decision

### Canonical architecture model technology

Structurizr DSL is selected as the canonical architecture-model technology for
v1.

The migration will establish:

```text
docs/architecture/workspace.dsl
```

as the root of the canonical architecture model.

Local `.dsl` files included from that workspace may be used to keep the model
maintainable, but they form one Structurizr workspace and one semantic authority.

Generated or exported JSON, PlantUML, SVG, PNG, Mermaid, HTML or other formats
are not architecture authority.

### Transition rule

This ADR selects the replacement technology and target authority structure; it
does not perform the migration.

Until an accepted migration PR establishes a validating
`docs/architecture/workspace.dsl` and updates repository authority references in
the same coherent change, the existing PlantUML sources identified by ADR-0003
remain the operational architecture authority.

The migration PR is the authority cutover point.

At that cutover:

- `docs/architecture/workspace.dsl` and its local included DSL fragments become
  the sole semantic architecture model;
- the existing authoritative PlantUML sources cease to be semantic authority;
- any retained PlantUML becomes ephemeral derived rendering input only;
- repository authority references must no longer identify both models as
  authoritative.

This transition rule prevents an accepted decision from creating an
architecture-authority gap before its implementation exists.

### Model responsibility

The Structurizr model must describe stable architecture concerns needed to
understand the v1 system, including where useful:

- product and system boundary;
- primary actors;
- compiler responsibilities;
- validated registry/input responsibility;
- canonical compilation boundary;
- validation and materialization responsibilities;
- supported target adapters;
- important dependency directions;
- explicitly external or non-owned target frameworks.

It must not become a duplicate source for detailed artifact schemas, workflow
contracts, registry content, CLI usage or source-level implementation details
already owned elsewhere.

### Views and layout

Canonical v1 views must:

- use explicit stable view keys;
- use `autoLayout`;
- keep layout instructions in DSL;
- not depend on manually maintained `workspace.json`.

`workspace.json` may be generated transiently for validation or export, but it
must not become a second repository authority.

### Structurizr tooling boundary

Repository-owned architecture validation will use the consolidated Structurizr
vNext command model, not the end-of-life legacy CLI.

The migration must pin one exact approved Structurizr distribution.

The preferred v1 execution boundary is the official Structurizr Docker image
pinned by content digest.

The migration must resolve and record the exact accepted image tag, digest, OS
and architecture at implementation time and must not rely on an implicit
`latest` tag.

Docker is therefore admitted as a documentation build and validation
technology for the architecture model. It is not a compiler/runtime dependency.

No Docker API, Structurizr library or Java dependency is admitted into the
compiler core by this decision.

### Validation contract

The migration must add repository-owned fail-closed architecture validation
that at minimum proves:

1. the canonical workspace parses and validates;
2. unresolved identifiers or references fail;
3. all expected stable views exist;
4. the canonical workspace requires no remote include, remote theme, remote
   workspace or remote rendering service;
5. any canonical textual export used by validation or rendering is deterministic
   for the pinned tool boundary;
6. committed derived architecture output, if any, is synchronized with the
   canonical workspace.

The normal validation path must be locally executable after the pinned tool
artifact is available.

### Network policy

The canonical v1 model must not require:

- remote `!include`;
- remote themes;
- remote Structurizr workspace storage;
- remote rendering;
- network access during normal validation after the pinned tool artifact is
  locally available.

### Stakeholder rendering

Stakeholders must continue to have repository-viewable architecture diagrams
without installing Structurizr.

Native Structurizr browser/Playwright PNG/SVG export is not admitted as the v1
canonical rendering boundary by this decision.

If committed SVG remains required during migration, the accepted derived
pipeline is:

```text
workspace.dsl
    ↓
pinned Structurizr textual PlantUML export
    ↓
pinned PlantUML renderer
    ↓
committed SVG
```

In that pipeline:

- exported `.puml` is ephemeral derived state;
- SVG is stakeholder-facing derived state;
- neither is semantic architecture authority;
- rendering must remain reproducible and fail closed;
- the applicable PlantUML/Smetana/DejaVu requirements from ADR-0003 remain in
  force until the migration explicitly replaces or narrows them.

A later bounded decision may remove the PlantUML rendering stage if an equally
reproducible and simpler stakeholder-rendering boundary is proven.

### Relationship to ADR-0003

This ADR supersedes ADR-0003 as the technology-selection decision for the future
canonical architecture source.

ADR-0003 remains operationally authoritative for the current PlantUML
source/rendering implementation until the migration cutover defined above.

After cutover:

- ADR-0009 owns semantic architecture-model authority and Structurizr validation;
- ADR-0003 no longer makes `.puml` files semantic architecture authority;
- ADR-0003's reproducible stakeholder-rendering requirements remain applicable
  only to any retained derived PlantUML/SVG stage until explicitly replaced.

This split is intentional: semantic model authority and derived rendering are
separate responsibilities.

## Alternatives considered

### Retain ADR-0003 PlantUML as the canonical architecture model

Rejected for the v1 target state.

It has the smallest technology footprint and already provides reproducible SVG
rendering, but architecture semantics remain distributed across detailed
diagram sources and depend on repository-specific conventions rather than one
first-class architecture model with explicit model/view validation.

PlantUML remains acceptable as a derived rendering technology.

### Structurizr DSL with native Structurizr PNG/SVG rendering

Rejected for the initial v1 contract.

The semantic model is suitable, but native image export introduces a
browser/Playwright boundary whose rendered-byte reproducibility was not proven
by the accepted research.

### Structurizr DSL with deterministic textual export and derived rendering

Accepted.

It gives the repository one semantic architecture model and fail-closed
validation while preserving a separately replaceable stakeholder-rendering
stage.

### Manually maintain both Structurizr DSL and PlantUML architecture models

Rejected.

That would introduce parallel architecture authorities and contradict ADR-0008.

### Store manual layout in committed `workspace.json`

Rejected for v1.

That would make important layout state depend on a second maintained
representation. Explicit view keys plus DSL-owned `autoLayout` keep the
canonical model self-contained.

## Consequences

V1 architecture migration now has an accepted target state and can be planned as
a bounded implementation issue.

The migration will add one new mandatory documentation technology boundary:
pinned Structurizr vNext execution through Docker.

The compiler/runtime technology baseline does not change.

The repository will gain stronger semantic architecture validation and one
canonical model, but migration must preserve current architecture authority
until the replacement exists and validates.

PlantUML may temporarily remain in the documentation build solely as a derived
renderer. This does not create a second architecture authority.

Architecture/documentation consolidation remains separate from the technology
migration except for authority references that must change atomically at
cutover.

No new compiler capability, target, workflow runtime, generic documentation
plugin system or remote architecture service is authorized.

## Acceptance scenarios

A conforming migration must satisfy all of the following:

1. `docs/architecture/workspace.dsl` exists and validates with the pinned
   Structurizr vNext distribution.
2. The exact accepted Structurizr artifact identity is recorded and verified.
3. An invalid workspace with an unresolved reference fails validation.
4. Expected stable view keys are validated.
5. The workspace has no required remote include, theme, storage or rendering
   dependency.
6. Repeated textual export used by repository validation/rendering is
   deterministic under the pinned tool boundary.
7. No manually maintained `workspace.json` is required as architecture
   authority.
8. Repository authority identifies the Structurizr workspace as the sole
   semantic architecture model after cutover.
9. Current authoritative PlantUML source files are removed or explicitly
   converted to derived/non-authoritative state at cutover.
10. Stakeholder-facing diagrams remain viewable from the repository.
11. Any retained derived PlantUML/SVG rendering remains reproducible and
    fail-closed.
12. No Structurizr, Docker or Java dependency enters the compiler core.
13. The migration does not combine unrelated architecture-documentation
    consolidation beyond authority references required for atomic cutover.
