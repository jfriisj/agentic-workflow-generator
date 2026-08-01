# Project Scope

This document defines the currently accepted implementation scope for
`agentic-workflow-generator`.

It answers:

> What are we allowed to build now?

`project-status.md` records where the project currently is and which accepted
work should be prioritized next. This document determines whether proposed work
is permitted at all.

Changes outside this document require the Scope Transition Workflow defined in
`docs/governance.md` before implementation begins.

## Current phase

**Post-migration hardening**

The atomic migration to the typed `AgentInstance` / `RoleBinding`,
`CompiledComposition` and typed top-level CLI architecture is complete.

The current phase is limited to strengthening the already accepted compiler,
workflow, artifact and registry model and removing known quality gaps.

This phase is not authorization for unrelated product expansion.

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

### 5. Compiler and validation quality

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
- removal of duplication that obscures ownership or weakens maintainability.

The known duplicate-code debt in the test suite may be reduced, but quality
gates must not be disabled or weakened to make the debt disappear.

### 6. Documentation and governance consistency

Changes required to keep repository authority synchronized are in scope,
including:

- `docs/scope.md`;
- `project-status.md`;
- `docs/governance.md`;
- `docs/architecture.md`;
- `docs/core-domain-model.md`;
- relevant ADRs;
- authoritative PlantUML sources;
- rendered architecture diagrams;
- registry documentation;
- developer workflow documentation;
- CI and pull-request workflow configuration.

Documentation must describe implemented current state accurately and must not
present exploratory work as current behavior.

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

## Current phase acceptance criteria

The post-migration hardening phase can be considered complete when:

1. accepted artifact-contract gaps have explicit, validated semantics;
2. accepted workflow-routing gaps have explicit, fail-closed semantics;
3. existing profiles, bundles and setups accurately represent their
   materialized compositions;
4. existing target outputs preserve all accepted compiler semantics;
5. known test duplicate-code debt has been addressed or explicitly bounded
   without weakening quality gates;
6. authoritative documentation and diagrams describe the implemented model;
7. all affected registry, schema, compiler and generated representations are
   synchronized;
8. the full project validation gate passes on the accepted integration state;
9. no compatibility path, fallback authority or obsolete orchestration has
   been reintroduced.

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

Only after that pull request is reviewed and merged into `dev` may
implementation begin on a separate topic branch.
