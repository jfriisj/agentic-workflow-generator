# Architecture

`agentic-workflow-generator` is a platform-neutral compiler for agentic software-delivery configurations. It consumes validated registry input and produces
reproducible target-specific configuration for VS Code Copilot and OpenCode.

The architecture is intentionally deterministic, fail-fast and validation-heavy.
This document owns the concise current-state architecture narrative. The sole
semantic architecture model is `docs/architecture/workspace.dsl`; detailed
platform-neutral domain semantics are owned by `docs/core-domain-model.md`.
Executable behavior remains authoritative in contracts, source and tests.

## Architecture style and decision authority

The current implementation and deployment model is a modular monolith with a
deterministic compiler core. Module boundaries are architectural responsibility
boundaries, not independently deployable services.

The deterministic compiler core is the stable center of the system. Delivery
interfaces, registry acquisition and validation, target rendering, and
filesystem/process effects remain outside canonical compiler semantics.

Significant changes to long-lived boundaries, dependency direction, canonical
representations, persistence responsibilities, external contracts or deployment
topology require an ADR. ADRs preserve rationale; this document describes the
current accepted architecture.

The modular-monolith rationale is recorded in
`docs/adr/0001-modular-monolith-deterministic-compiler-core.md`.

## Architecture drivers

### P0 — correctness and trust

The architecture prioritizes:

~~~text
one canonical compilation authority
fail-fast and fail-closed behavior
deterministic results
reproducible compiler inputs and generated outputs
semantic target independence
~~~

For the same accepted compiler input and compiler version, canonical compilation
and generated output must not depend on execution order, hidden state or
target-specific reinterpretation.

### P1 — controlled change

Expected change is localized through explicit responsibility boundaries rather
than speculative extension infrastructure:

- an accepted target primarily affects target rendering, target validation and
  registration rather than canonical compiler semantics;
- an accepted delivery interface reuses application/compiler behavior rather
  than moving domain logic into the interface;
- an accepted registry acquisition mechanism must still produce validated typed
  input before compilation and must not introduce a second semantic resolution
  authority.

### P2 — portability and operational simplicity

The compiler core must not depend on one delivery interface, deployment
mechanism or target platform. The current local single-process deployment is
preferred while it satisfies accepted requirements.

Performance and scalability are measured concerns, not assumed architecture
drivers. Distributed execution, hosted services and additional infrastructure
require measured or accepted requirements before they influence implementation.

## Canonical semantic boundary

`CompiledComposition` is the sole canonical resolved internal composition.
Downstream generation and validation consume that composition rather than
re-resolving registry semantics.

The stable responsibility boundaries are:

~~~text
delivery interfaces
  parse interaction and render diagnostics

registry input and validation
  load external representation and produce validated typed compiler input

application orchestration
  coordinate accepted use cases and transactional operations

compiler core
  resolve one canonical CompiledComposition

target rendering
  translate canonical semantics into accepted target representations

materialization and infrastructure
  own filesystem, hashing, process effects and transactional materialization
~~~

The primary dependency direction is:

~~~text
delivery interfaces
  ↓
application orchestration
  ↓
validation and compiler
  ↓
domain
~~~

Registry input and infrastructure are supporting boundaries. They provide
validated input and technical adapters without becoming semantic authorities.

The stable dependency constraints are:

- domain code does not depend on delivery interfaces, registry I/O, targets or
  infrastructure;
- validation does not depend on delivery interfaces or concrete target
  renderers;
- targets do not load raw registry input or implement independent composition
  rules;
- registry loading does not invoke target generation;
- infrastructure does not contain domain decisions;
- application services orchestrate accepted use cases without duplicating domain
  rules.

Delivery and infrastructure concerns must not become semantic resolution
authorities, and target rendering must not reinterpret raw registry input.

## Persistent representations

The persistent compiler representations have separate responsibilities:

- `.agentic/agentic.json` serializes the active compiled composition;
- `.agentic/agentic-lock.json` records compiler-input provenance;
- `.agentic/generated/output-manifest.json` records generated-output ownership
  and integrity.

None of these representations creates a second semantic resolution authority.
Detailed fields, validation behavior and command contracts are owned by their
schemas, source and tests rather than duplicated here.

## External registry boundary

Registry JSON is untrusted external compiler input. The architectural boundary is:

~~~text
filesystem
→ JSON parsing
→ schema validation
→ typed model construction
→ registry indexing
→ semantic validation
→ canonical compilation
~~~

Raw external representation must be converted into validated typed input before
compiler or target logic consumes it. Later layers must not compensate with
fallback behavior for invariants guaranteed by an earlier boundary.

## Target boundary

The accepted target frameworks are VS Code Copilot and OpenCode.

Target rendering consumes canonical compiled semantics and may translate them
into target-specific syntax. A target must fail explicitly when accepted
semantics cannot be represented; it must not weaken, omit or independently
reinterpret canonical semantics.

Target-specific file formats, output paths, permission mappings and validation
contracts are implementation authority and are not duplicated in this narrative.

## Materialization and side effects

Filesystem, hashing and process effects belong to infrastructure/materialization
responsibilities outside the deterministic compiler core. Multi-file writes use
transactional materialization where partial output could otherwise leave an
inconsistent repository state.

Repository-relative path safety and concrete process/tool policies are enforced
by executable implementation and tests.

## Evolution policy

The project designs boundaries for plausible change but implements only accepted
need. Future possibilities are not current capabilities.

The current extension seams are intentionally narrow:

- target rendering is an architectural extension seam, but no dynamic plugin
  system is implied;
- alternative delivery interfaces may reuse application/compiler behavior, but
  no API, service or web interface is implied;
- alternative registry acquisition may feed the validated typed boundary, but
  no remote registry is implied;
- runtime orchestration, if ever accepted, must be a separate responsibility and
  must not turn compiler output into mutable runtime state.

Current workflow invariants and domain contracts are detailed in
`docs/core-domain-model.md` and executable authorities. Changing accepted hard
constraints still requires the applicable scope and architecture decision.

## Canonical architecture model

The sole semantic architecture model is:

~~~text
docs/architecture/workspace.dsl
~~~

It owns the stable system boundary, architectural responsibility boundaries,
supported external target frameworks and important dependency directions. Its
canonical views use explicit stable keys and DSL-owned `autoLayout`.

Stakeholder-facing derived views are committed as:

~~~text
docs/architecture/diagrams/system-context.svg
docs/architecture/diagrams/compiler-responsibilities.svg
~~~

Those SVG files are reproducible derived output. Structurizr-exported PlantUML
is ephemeral rendering input; neither PlantUML nor SVG is semantic architecture
authority.

## High-level compiler flow

~~~text
validated registry input
        ↓
typed registry/domain model
        ↓
selected setup or bundle
        ↓
canonical CompiledComposition
        ↓
active configuration
        ↓
compiler-input lockfile
        ↓
target-specific generated output
        ↓
generated-output manifest
        ↓
validation
~~~

This flow has one semantic compilation authority. Persistent and target-specific
representations preserve canonical semantics rather than re-resolving them.

## Documentation and authority boundaries

A change is not complete until the affected authoritative representations agree
with the implemented model.

The principal current authorities are:

- `docs/scope.md` — accepted implementation scope;
- `docs/project-status.md` — current project status and priority;
- `docs/governance.md` — governance and change control;
- `docs/workflow.md` — operational Git/PR/release flow;
- `docs/architecture.md` — concise current-state architecture narrative;
- `docs/architecture/workspace.dsl` — sole semantic architecture model;
- `docs/core-domain-model.md` — detailed platform-neutral core-domain semantics;
- `docs/adr/` — accepted architecture rationale;
- contracts, schemas, source and tests — executable implementation truth.

Only affected authority files should change. Scope and governance must not be
rewritten merely because implementation changed. Superseded proposals and
migration history remain in Git history rather than parallel current-state
documentation.

## Architectural summary

~~~text
Validated external registry input enters through one typed boundary.
One deterministic compiler produces one canonical CompiledComposition.
Application services orchestrate accepted use cases without duplicating domain rules.
Targets translate canonical semantics without reinterpreting registry input.
Infrastructure owns filesystem, hashing and process effects.
Active config, lockfile and manifest have distinct persistence responsibilities.
All invalid or unsupported required states fail explicitly; there is no silent fallback.
~~~

The result is a reproducible, target-independent compiler for agentic
software-delivery configurations with explicit authority boundaries and
controlled evolution.
