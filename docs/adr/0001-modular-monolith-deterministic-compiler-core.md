# ADR-0001: Modular monolith with deterministic compiler core and explicit boundaries

- Status: Accepted
- Date: 2026-08-02

## Context

`agentic-workflow-generator` is a platform-neutral compiler for agentic software delivery workflows. The current product responsibility is deterministic compilation of validated registry configuration into one canonical internal composition and target-specific generated artifacts.

The implementation is currently a local Python package and CLI with filesystem-based inputs and outputs. The codebase already separates domain models, validation, compilation, application orchestration, target generation and infrastructure concerns, but the architectural style and rationale have not previously been recorded as a durable decision.

The architecture must preserve the project's highest-priority qualities:

* one canonical semantic authority;
* fail-fast and fail-closed behavior;
* deterministic compilation and generation;
* reproducible input and output provenance;
* target independence at the semantic level;
* testable, maintainable responsibility boundaries;
* low operational complexity.

Likely future change vectors may influence boundaries, but they do not authorize implementation. Examples include additional accepted target adapters, alternative delivery interfaces and alternative registry acquisition mechanisms. Remote registries, runtime orchestration, hosted services, dynamic plugins and distributed execution remain outside current accepted scope unless separately admitted.

## Decision

The current architecture is a **modular monolith with a deterministic compiler core and explicit responsibility boundaries**.

The modular monolith is the current implementation and deployment form. Logical bounded contexts and module boundaries are not independently deployable services. The system remains one coherent application while current requirements are satisfied by that model.

The deterministic compiler core is the stable architectural center. It resolves validated typed input into exactly one canonical `CompiledComposition`.

`CompiledComposition` is the sole canonical resolved internal composition. Downstream target rendering, serialization and validation consume it rather than independently reinterpreting raw registry data or maintaining parallel semantic resolution models.

The principal architectural responsibilities are:

1. **Delivery interfaces** — parse user/tool interaction, invoke application use cases and render results.
2. **Input acquisition and validation** — load external representations, validate schemas and construct typed input.
3. **Application orchestration** — coordinate accepted use cases, compiler invocation and transactional operations.
4. **Compiler core** — resolve domain semantics into one canonical `CompiledComposition`.
5. **Target rendering** — translate canonical semantics into an accepted target representation without weakening or re-resolving semantics.
6. **Materialization and infrastructure** — perform filesystem, hashing and process effects without owning domain decisions.

Dependency direction must protect canonical compiler semantics. In particular:

* domain/compiler semantics must not depend on CLI or terminal behavior;
* target adapters must not load or semantically resolve raw registry input;
* infrastructure must not contain domain decisions;
* delivery interfaces must not become a second compiler implementation.

Target rendering is an architectural extension seam because the project already supports multiple concrete targets. This decision does **not** introduce a dynamic plugin architecture. Target registration may remain explicit and static until an accepted requirement demonstrates that another mechanism is necessary.

Persistent artifacts have distinct responsibilities:

* active config serializes the accepted compiled composition;
* the compiler-input lockfile records input provenance;
* the output manifest records generated-output ownership and integrity.

No persistent artifact may become a second semantic resolution authority. Contract and schema versions must identify representation evolution explicitly rather than silently accepting incompatible formats.

Current workflow invariants remain hard constraints for the current accepted compiler/workflow model, including exactly one controller per workflow and exactly one state owner for each non-terminal state. They are not declared universal constraints for every hypothetical future product. A change to those invariants requires an explicit scope and architecture decision.

The project follows the policy **design for extension, implement only accepted need**. Plausible future change may shape clean boundaries, but speculative services, frameworks, plugins, runtime layers or infrastructure are not created in advance.

## Alternatives considered

### Single undifferentiated CLI application

Rejected. Keeping parsing, semantic resolution, target generation and filesystem effects in one delivery layer would make compiler behavior harder to test, reuse and evolve safely.

### Strict Clean Architecture or hexagonal framework rewrite

Rejected. The project needs enforceable dependency and responsibility boundaries, not a framework-driven reorganization. A broad rewrite would create migration cost and speculative abstraction without an accepted requirement.

### Microservices or distributed services

Rejected. Current product responsibility is a deterministic local compiler. Independent deployment, network boundaries and distributed coordination would increase operational complexity without satisfying a current requirement.

### Generic dynamic plugin architecture

Rejected. Multiple target adapters justify a target extension seam, but do not justify runtime discovery, generic plugin contracts or marketplace infrastructure. Explicit registration remains sufficient for current accepted targets.

### Independent target-specific compilers

Rejected. Allowing each target to resolve registry semantics independently would create multiple semantic authorities and make deterministic cross-target behavior harder to guarantee.

### Runtime-oriented orchestration architecture

Rejected for the current product boundary. The generator compiles workflow configuration; it does not execute autonomous workflow state at runtime. If runtime orchestration is later accepted, it must be modeled as a separate responsibility rather than mutating compiler output into runtime state.

## Consequences

The project keeps a simple single-process implementation and deployment model while gaining explicit architectural boundaries for correctness, testing and controlled evolution.

Compiler semantics remain centralized around one canonical composition, reducing the risk of drift between delivery interfaces or targets.

Target-specific change can remain localized when the platform-neutral semantic model is sufficient. A target that cannot represent required semantics must fail explicitly rather than degrade behavior.

Alternative delivery interfaces or input acquisition mechanisms can be evaluated later without moving domain/compiler semantics into those mechanisms.

The architecture requires discipline: module names alone do not enforce boundaries. Tests, review, import direction and ADRs must continue to protect ownership and dependency rules.

The decision intentionally does not optimize for independent service deployment, dynamic plugin discovery, runtime orchestration or speculative infrastructure. Those capabilities require separate accepted needs and decisions.

This ADR does not authorize new targets, remote registries, runtime orchestration, hosted services, web interfaces, databases, distributed execution, plugin frameworks or new persistence mechanisms.

## Architecture evaluation scenarios

The decision should continue to satisfy these scenarios:

1. The same accepted input and compiler version produce the same canonical composition and generated bytes.
2. Invalid semantic input fails before target/materialization side effects are committed.
3. A target cannot silently weaken or reinterpret canonical semantics.
4. Materialization does not leave an accepted partial generated state after failure.
5. Adding an accepted target primarily changes target rendering, validation, tests and explicit registration unless the platform-neutral semantic model itself must change.
6. An accepted alternative delivery interface can invoke application/compiler behavior without depending on CLI parsing or terminal rendering.
7. An accepted alternative registry acquisition mechanism can feed the validated typed boundary without creating a second compiler semantic path.
8. Incompatible persistent-contract evolution is explicit and version-identifiable rather than silently accepted.
