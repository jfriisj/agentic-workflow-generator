# Project Scope

This document defines the currently accepted implementation scope for
`agentic-workflow-generator`.

It answers:

> What are we allowed to build now?

`docs/project-status.md` records where the project currently is and which accepted
work should be prioritized next. This document determines whether proposed work
is permitted at all.

Changes outside this document require the scope-transition rules defined in
`docs/governance.md` and the operational scope-transition sequence defined in
`docs/workflow.md` before implementation begins.

## Current phase

**Post-V1 controlled product evolution**

ADR-0008 V1 is complete and release-ready on accepted `development`. Its six
milestones, controlled-evolution principle and hard compiler/runtime constraints
remain the baseline for later work.

Post-V1 scope expansion is admitted only through explicit governed transitions.
The current admitted expansion is bounded to Goal #86: a configurable OpenCode
Agent Factory composition with explicit supported per-agent model assignment.

This phase does not authorize unrelated product expansion. Implementation of the
Goal #86 capability remains blocked until the required ownership/architecture
decision is accepted; later implementation must remain inside the product
boundary and hard constraints below.

## Product boundary

`agentic-workflow-generator` is a deterministic, fail-fast compiler for
validated agentic software-delivery configurations.

Its accepted product responsibility is:

~~~text
validated registry
      ↓
setup or bundle selection
      ↓
agent instances and role bindings
      ↓
CompiledComposition
      ↓
.agentic/agentic.json
      ↓
compiler-input lockfile
      ↓
target-specific generated output
      ↓
output manifest
      ↓
validation
~~~

The project generates and validates agentic development environments.

It is not an autonomous workflow runtime, a model host or a replacement for the
target coding-agent frameworks.

## V1 milestone mapping

Accepted work is organized under the ADR-0008 milestones:

1. **Product and architecture clarity** — concise repository authority, one
   canonical architecture model, non-duplicative current-state documentation
   and consistent architecture references.
2. **Complete compiler contracts** — accepted artifact and workflow contract
   gaps plus fail-closed validation and synchronized canonical
   representations.
3. **Honest registry compositions** — profiles, bundles and setups accurately
   represent the composition they materialize.
4. **Canonical target preservation** — `vscode-copilot` and `opencode` preserve
   all applicable canonical compiled semantics.
5. **Consumer acceptance and release readiness** — version-controlled
   consumer-oriented acceptance evidence proves deterministic initialization,
   compilation, materialization and validation.
6. **Controlled evolution** — current boundaries, contracts and tests make
   likely bounded changes explicit without introducing speculative extension
   infrastructure.

The detailed milestone completion criteria remain owned by ADR-0008. This scope
defines which work is authorized to satisfy them.

## In scope

### 1. Artifact contract hardening

The existing artifact model may be strengthened to support the already
identified contract gaps:

- provenance;
- revision;
- status-dependent invariants;
- reproducible evidence requirements;
- artifact-specific status semantics;
- input-artifact references where required by the existing delivery model;
- validation required to enforce these contracts fail-closed.

Changes must extend the existing artifact responsibility rather than introduce
an unrelated artifact platform.

### 2. Workflow hardening

The existing workflow model may be strengthened to complete its already
accepted fail-closed semantics:

- explicit `BLOCKED` routing;
- unambiguous controller and routing semantics;
- preservation of routing semantics in generated target output;
- clear test evidence required by existing workflows;
- clear execution semantics for the existing AI-evaluation flow;
- validation and tests required to enforce these rules.

This scope covers completion of the current workflow model, not introduction of
a general runtime orchestration engine.

### 3. Profiles, bundles and setups hardening

The existing registry composition may be improved where current entries are
stale, misleading, incomplete or placebo-like.

Accepted work includes:

- distinguish generic and domain-specific profile intent where needed;
- correct capability completeness;
- remove stale setup text;
- remove setup choices that do not materially affect the resulting
  composition;
- ensure classifications accurately describe materialized behavior;
- document generalist and specialist compositions;
- strengthen existing registry contracts and validation when required by these
  corrections.

This does not authorize new product capabilities merely because the registry
can represent them.

### 4. Existing target correctness

The supported targets remain:

~~~text
vscode-copilot
opencode
~~~

Changes may correct defects, semantic loss or inconsistent behavior in these
existing target adapters and renderers when required to preserve the canonical
`CompiledComposition`.

This includes maintaining:

- role-binding responsibilities;
- guardrails;
- effective permissions;
- artifact-specific output requirements;
- complete accepted workflow routing;
- agent-instance identity;
- profile and workflow identity;
- canonical output ownership and validation.

### 5. Compiler, validation and consumer acceptance quality

Maintenance of the current typed compiler architecture is in scope.

This includes:

- defect fixes;
- stricter fail-fast validation;
- stable diagnostics;
- deterministic behavior;
- idempotency;
- canonical lockfile behavior;
- canonical output-manifest behavior;
- focused tests;
- integration and end-to-end validation;
- removal of duplication that obscures ownership or weakens maintainability;
- contract and architecture tests that keep existing bounded extension seams
  explicit;
- version-controlled consumer-oriented acceptance coverage.

Consumer acceptance may prove the supported v1 path:

~~~text
select composition
    -> compile
    -> validate
    -> materialize supported targets
    -> validate generated state
    -> repeat
    -> canonical deterministic result
~~~

This acceptance work remains inside the compiler boundary. It does not authorize
runtime workflow orchestration or a new target platform.

The known duplicate-code debt in the test suite may be reduced, but quality
gates must not be disabled or weakened to make the debt disappear.

### 6. Documentation, architecture clarity and governance consistency

Changes required to keep repository authority synchronized and satisfy
ADR-0008 Milestone 1 are in scope, including:

- making `docs/architecture.md` a concise current-state architecture narrative;
- establishing exactly one canonical architecture model through a separately
  accepted architecture/technology decision;
- removing or consolidating redundant current-state architecture and setup
  documentation after its unique authoritative content is preserved elsewhere;
- research and decision work required before changing architecture-model
  notation or rendering technology;
- `docs/scope.md`;
- `docs/project-status.md`;
- `docs/governance.md`;
- `docs/workflow.md`;
- `docs/architecture.md`;
- `docs/core-domain-model.md` while it remains current authority;
- relevant ADRs;
- the canonical `docs/architecture/workspace.dsl` architecture model;
- reproducible derived architecture diagrams;
- registry documentation;
- workflow and technology documentation;
- CI and pull-request workflow configuration.

Documentation must describe implemented current state accurately and must not
present exploratory work as current behavior.

ADR-0009 separately admits Structurizr DSL and the pinned documentation-tool
boundary used by the canonical architecture model. Maintenance of that accepted
model, its validation and its derived rendering is therefore in scope. A future
architecture-model technology change still requires a separate accepted decision.

### 7. Configurable Agent Factory OpenCode composition

Goal #86 admits one bounded post-V1 consumer capability: a clean consumer project
may select a declared Agent Factory composition whose explicit agent/role
composition and supported per-agent model assignments are represented
canonically, compiled deterministically and preserved in generated OpenCode
output.

Accepted work may include only the registry, schema, typed-domain/compiler,
active-configuration, validation, OpenCode rendering, generated-output and test
changes required to support that outcome.

The admitted capability must preserve this sequence:

~~~text
select accepted Agent Factory composition
    -> validated typed input
    -> canonical CompiledComposition
    -> active configuration
    -> OpenCode rendering
    -> generated-state validation
    -> OpenCode runtime validation
    -> repeat
    -> canonical deterministic result
~~~

Explicit model assignment is admitted as a static governed composition concern,
not as model execution, model hosting or provider orchestration. The OpenCode
renderer may translate accepted canonical assignment semantics into target-native
syntax but must not become a second semantic authority.

This scope transition does not decide which existing canonical domain entity owns
model assignment. The current domain model gives `AgentInstance` concrete worker
identity/configuration responsibility and `RoleBinding` workflow-role
responsibility, but neither currently owns model selection. Because adding that
ownership changes a durable canonical representation, a separate accepted
decision/ADR is required before implementation.

The minimum admitted configurability is limited to:

- declaring/selecting the Agent Factory composition required by Goal #86;
- explicit supported model assignment for the concrete generated agents in that
  composition;
- deterministic canonical preservation of those assignments;
- fail-closed rejection of missing, invalid or unsupported required assignments;
- OpenCode target-native preservation and runtime validation;
- canonical output-manifest ownership and idempotent regeneration.

This capability does not admit:

- automatic model selection, recommendation or inference;
- model hosting, execution, provider SDK orchestration or credential management;
- raw OpenCode configuration as canonical semantic authority;
- a generalized cross-target model-routing platform beyond demonstrated need;
- a hard-coded one-off template that bypasses registry and canonical compilation;
- a plugin system, dynamic discovery or generic target DSL;
- a new target platform or unrelated composition/registry redesign.

## Hard architectural constraints

The following existing constraints remain part of accepted scope and must not be
weakened:

- `CompiledComposition` is the compiler's canonical internal composition.
- `.agentic/agentic.json` is the persistent active serialization of that
  composition.
- No separate resolution model or parallel compiler authority may be
  introduced.
- Agent profiles are advisory and must not become implicit runtime fallback
  sources.
- Concrete runtime authority belongs to bundle-owned agent instances and role
  bindings.
- Each non-terminal workflow state has exactly one state-owner binding.
- Each workflow has exactly one controller binding.
- A controller owns routing authority but no workflow state or gate.
- Effective permissions belong to agent instances.
- Concrete capabilities, skills, produced artifacts, responsibilities and
  guardrails belong to role bindings.
- Separation of duties is explicit and fail-closed.
- Target adapters do not reinterpret raw registry input independently.
- Generated output must be canonical and deterministic.
- Missing requirements, references, tools or outputs fail explicitly.
- Compatibility projections, silent degradation and fallback behavior are not
  permitted.

Changing one of these constraints is an architecture and scope change and
requires an explicit reviewed decision before implementation.

## Explicitly out of scope

The following work is not currently authorized:

- new target platforms;
- autonomous runtime workflow orchestration;
- runtime-context generation;
- remote registry;
- registry marketplace;
- dynamic plugin discovery;
- generic plugin architecture introduced for hypothetical future use;
- template engine introduced as a second rendering authority;
- generic target DSL;
- model hosting;
- model training infrastructure;
- automatic self-modification of registry or workflow definitions;
- distributed workflow execution;
- replay engine;
- web UI;
- retry policy not already represented by the accepted workflow model;
- escalation policy not already represented by the accepted workflow model;
- artifact invalidation semantics;
- architecture-model technology change without a separate accepted decision;
- speculative capabilities, abstractions or infrastructure without an accepted
  current requirement.

These items may be considered later through an explicit scope transition. Their
possible future value does not make them current scope.

## Deferred decisions

The following identified possibilities remain deferred until a separate
requirement and decision admit them:

- retry semantics;
- escalation semantics;
- artifact invalidation;
- additional target platforms;
- runtime orchestration;
- plugin discovery;
- template-engine architecture;
- generic target DSL.

A deferred item must not be implemented indirectly as part of another change.

## V1 scope exit criteria

The accepted v1 scope is complete only when all six ADR-0008 milestones are
complete on accepted `development` and repository evidence proves that:

1. product and architecture authority is concise, non-duplicative and
   internally consistent, with exactly one canonical architecture model;
2. all required v1 artifact and workflow contract gaps have explicit accepted
   semantics and synchronized fail-closed implementation;
3. profiles, bundles and setups accurately represent their materialized
   compositions;
4. both supported target outputs preserve all applicable canonical compiler
   semantics without fallback or independent reinterpretation;
5. version-controlled consumer acceptance proves clean initialization,
   deterministic compilation, supported-target materialization, generated-state
   validation and repeat execution without drift;
6. controlled-evolution boundaries are explicit in architecture, contracts and
   tests without speculative plugin or runtime infrastructure;
7. known test duplicate-code debt has been addressed or explicitly bounded
   without weakening quality gates;
8. all affected registry, schema, compiler, generated and documentation
   representations are synchronized;
9. the full project validation gate passes on the accepted integration state;
10. every required v1 gap is closed or explicitly removed from v1 through an
    accepted decision.

Completion of one item does not authorize work on an out-of-scope item.

## Scope admission rule

A proposed change outside this document must answer:

1. What concrete problem requires the change?
2. Which accepted use case needs it?
3. Why is the current model insufficient?
4. What new responsibility or capability would be introduced?
5. What does the proposed change explicitly not own?
6. Does it alter architecture, ownership or technology?
7. What measurable acceptance criteria would make the scope complete?

If the answers justify expansion, create a dedicated scope-transition topic
branch and pull request.

Only after that pull request is reviewed and merged into `development` may
implementation begin on a separate topic branch.
