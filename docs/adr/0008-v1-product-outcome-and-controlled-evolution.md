# ADR-0008: V1 product outcome and controlled evolution

- Status: Accepted
- Date: 2026-08-03

## Context

`agentic-workflow-generator` already has a governed delivery model, a deterministic
compiler core, two supported target adapters, typed registry and composition
boundaries, canonical generated state, and fail-closed validation.

The current repository phase has nevertheless been expressed primarily as
post-migration hardening plus a sequence of technical gaps. That is sufficient
for deciding whether an individual change is allowed, but it does not define a
finite product outcome.

Without a canonical product outcome, locally correct hardening slices can
continue indefinitely without an objective definition of when the project has
reached a usable v1.

The project also operates in a technology area that changes quickly. V1 must not
freeze the implementation around today's exact target, workflow, artifact,
capability, or skill set. At the same time, anticipated change is not sufficient
reason to introduce a generic plugin system, dynamic discovery, a generic target
DSL, or other speculative infrastructure.

This decision therefore establishes:

- the canonical v1 product outcome;
- the compiler/runtime boundary for v1;
- controlled evolution as an architecture driver;
- six finite v1 milestones;
- measurable completion criteria;
- the repository-level v1 exit condition.

This ADR defines product direction and planning authority. It does not itself
expand the implementation scope in `docs/scope.md`.

## Decision

### Canonical v1 product outcome

V1 is a complete, locally executable, deterministic compiler that takes a
validated declarative software-delivery composition and generates complete,
reproducible agent configuration for VS Code Copilot and OpenCode.

The generated configuration preserves the accepted workflow, permission,
artifact, evidence, capability, skill, ownership, and routing semantics of the
canonical compiled composition.

For the same accepted compiler input and compiler version, canonical compilation
and generated output must be deterministic and reproducible.

Invalid, incomplete, inconsistent, or semantically unsupported compositions
must fail explicitly. V1 does not silently degrade requirements, introduce
fallback behavior, or reinterpret intent independently in a target adapter.

### Product boundary

V1 owns:

- validated registry input;
- setup or bundle selection;
- typed agent instances and role bindings;
- one canonical `CompiledComposition`;
- active composition serialization;
- compiler-input provenance;
- deterministic target rendering;
- generated-output ownership and integrity;
- fail-closed validation.

V1 does not own autonomous workflow execution.

It is not:

- a workflow runtime;
- a model host;
- a distributed execution system;
- a replacement for the target coding-agent frameworks.

The supported v1 targets are:

- `vscode-copilot`;
- `opencode`.

Additional targets are not required to prove v1 extensibility.

### Controlled evolution

Controlled evolution is a required v1 architecture driver.

The architecture must allow bounded areas to be added, changed, or removed
later when a concrete accepted requirement justifies the change, without:

- introducing a second compiler authority;
- introducing a parallel semantic resolution path;
- requiring unrelated bounded areas to be rewritten;
- introducing implicit compatibility fallback;
- moving target-specific interpretation into the compiler core.

The most likely evolution areas are:

- targets;
- workflows;
- artifact contract types;
- capabilities;
- skills;
- registry composition concepts;
- later accepted delivery or domain slices.

Controlled evolution means the architecture should be:

~~~text
easy to extend
easy to replace
easy to remove
~~~

It does not mean:

~~~text
everything is a plugin
everything is runtime-configurable
everything is abstracted in advance
~~~

Extension seams remain explicit and narrow. New technology or abstractions are
admitted only after a concrete accepted need.

### V1 architecture invariants

The existing hard architecture constraints remain v1 invariants:

- `CompiledComposition` is the sole canonical internal composition;
- `.agentic/agentic.json` is its persistent active serialization;
- no separate resolution model or parallel compiler authority exists;
- bundles own concrete agent instances and role bindings;
- advisory agent profiles and profiles do not become runtime fallback;
- each non-terminal workflow state has exactly one state-owner binding;
- each workflow has exactly one controller binding;
- controller bindings own routing but no workflow state or gate;
- effective permissions belong to agent instances;
- capabilities, skills, produced artifacts, responsibilities, and guardrails
  belong to role bindings;
- target renderers consume canonical typed semantics and do not reinterpret raw
  registry input;
- missing or invalid required semantics fail explicitly;
- generated output remains deterministic and canonical.

These rules are v1 constraints, not claims that every future product version
must preserve the same domain model forever.

Changing one requires an explicit scope and architecture decision. A roadmap
implementation issue must not weaken one indirectly.

## V1 milestones

### Milestone 1 — Product and architecture clarity

The product and architecture are understandable from repository authority
without reconstructing intent from Git history or chat.

Complete when:

1. the canonical v1 product outcome and non-ownership boundary are recorded in
   repository authority;
2. controlled evolution is recorded as an architecture driver;
3. `docs/architecture.md` is a concise current-state architecture narrative
   rather than a duplicate domain/registry/CLI manual;
4. exactly one canonical architecture model is identified;
5. redundant current-state architecture documentation has been removed or
   reduced to non-competing supporting material;
6. README, governance, scope, status, ADR, and architecture authority references
   do not contradict each other.

The technology and notation used by the canonical architecture model require a
separate decision. This ADR does not choose Structurizr DSL or supersede
ADR-0003.

### Milestone 2 — Complete compiler contracts

All known contract gaps required for v1 have explicit accepted semantics and
fail-closed implementation through every affected canonical representation.

At minimum the roadmap must resolve:

- input-artifact references;
- explicit `BLOCKED` workflow routing;
- unambiguous controller and routing semantics;
- required test-evidence semantics in existing workflows;
- execution semantics for the existing AI-evaluation flow.

Complete when:

1. each required concern has an accepted decision where semantics are not
   already authoritative;
2. typed domain, registry/schema validation, compiler serialization, target
   preservation, generated state, and tests are synchronized where affected;
3. no required v1 contract remains only as prose or an identified gap;
4. full project validation passes on accepted `development`.

Retry, escalation, artifact invalidation, runtime orchestration, and unrelated
future capabilities are not required for this milestone unless separately
admitted through scope.

### Milestone 3 — Honest registry compositions

Profiles, bundles, setups, workflows, skills, artifacts, and related
classifications accurately describe the composition that is actually compiled.

Complete when:

1. the current registry has been audited against materialized behavior;
2. stale or misleading recommendations and descriptions are removed;
3. setup choices that imply different behavior produce materially different
   accepted compositions or are explicitly blocked;
4. required capabilities are covered by selected skills;
5. classifications match actual materialized behavior;
6. no advisory profile value becomes implicit runtime authority;
7. registry validators and focused tests fail closed on the audited invariants.

The audit may produce multiple bounded implementation or defect issues. It does
not authorize unrelated new compositions merely because the registry can
represent them.

### Milestone 4 — Canonical target preservation

Both supported targets preserve every v1 semantic they are required to
represent.

Complete when:

1. VS Code Copilot and OpenCode output preserve applicable role ownership,
   permissions, capabilities, skills, artifact requirements, evidence
   requirements, workflow routing, and identity;
2. target adapters do not independently reinterpret raw registry input;
3. unsupported required semantics fail generation instead of degrading output;
4. target-owned paths remain explicit and non-overlapping;
5. contract/integration tests demonstrate equivalent preservation of canonical
   semantics across both supported targets.

### Milestone 5 — Consumer acceptance and release readiness

V1 is proven from the perspective of a clean consumer project rather than only
through isolated internal unit tests.

Complete when a version-controlled acceptance matrix demonstrates, for the
supported v1 compositions and targets:

~~~text
select composition
    -> compile
    -> validate
    -> materialize targets
    -> validate generated state
    -> repeat
    -> canonical deterministic result
~~~

The acceptance boundary must prove:

1. clean initialization from supported input;
2. deterministic active configuration;
3. canonical compiler-input lock state;
4. valid target output;
5. canonical output manifest;
6. fail-closed rejection of representative invalid input;
7. repeated execution without drift;
8. no unmanaged output under target-owned paths;
9. full repository validation on the final accepted integration state.

Historical test counts are not a release criterion.

### Milestone 6 — Controlled evolution

The implemented v1 architecture demonstrates that likely bounded changes have
clear ownership and do not require a speculative extension platform.

Complete when repository architecture and executable boundaries make it clear
where a later accepted change to a target, workflow, artifact contract, or
capability/skill concern belongs, while preserving:

- one canonical compiler authority;
- explicit ownership;
- deterministic behavior;
- fail-closed validation;
- target-independent core semantics;
- no compatibility fallback;
- no parallel resolution path.

This milestone does not require adding a third target, synthetic plugin, unused
registry kind, or hypothetical abstraction solely to prove extensibility.

The proof is the combination of explicit architecture boundaries, current
versioned contracts, dependency direction, and tests around real existing
extension seams.

## V1 gap classification

The current repository gaps map to v1 as follows.

Required for v1:

- concise and non-duplicative architecture authority;
- one canonical architecture model;
- input-artifact reference semantics and implementation;
- complete workflow routing semantics;
- required test-evidence semantics;
- AI-evaluation execution semantics;
- registry composition audit and bounded corrections;
- canonical semantic preservation across both supported targets;
- consumer-oriented acceptance coverage;
- bounded duplicate-code cleanup where it materially obstructs maintainability
  or v1 validation.

Explicitly deferred unless admitted separately:

- additional target platforms;
- autonomous runtime workflow orchestration;
- remote registry;
- registry marketplace;
- dynamic plugin discovery;
- generic plugin architecture;
- generic target DSL;
- model hosting;
- distributed workflow execution;
- web UI;
- retry semantics beyond the accepted workflow model;
- escalation semantics;
- artifact invalidation.

## Roadmap rule

After this ADR is accepted, planning follows the v1 milestones rather than a
sequence of isolated technical opportunities.

Every new roadmap issue must state:

- which v1 milestone it advances;
- the concrete gap or decision it resolves;
- its dependencies;
- whether it is decision, scope, research, implementation, defect, or
  documentation work;
- its measurable completion condition.

Implementation issues remain blocked until required decisions and scope
authority are accepted.

The immediate next planning work is a separate scope/roadmap alignment slice.
That work may update `docs/scope.md` where needed and create the
dependency-ordered issue set.

Architecture-model technology selection, including a possible migration from
PlantUML to Structurizr DSL, is a separate research and decision sequence.

## V1 exit condition

V1 is release-ready only when all six milestones are complete on accepted
`development`, every required v1 gap is closed or explicitly removed from v1 by
an accepted decision, and the full consumer acceptance and repository validation
gates pass.

The project must be able to determine v1 readiness from repository state and
issue/validation evidence without relying on chat history, informal intent, or
an open-ended hardening backlog.

## Alternatives considered

### Continue with post-migration hardening as the roadmap

Rejected. It identifies areas of work but does not provide a finite product
outcome or objective release condition.

### Define extensibility by adding a generic plugin system in v1

Rejected. The current need is controlled evolution at explicit boundaries, not
runtime plugin discovery or a universal extension mechanism.

### Require additional targets to prove extensibility

Rejected. A synthetic third target would add product scope merely to test an
architecture hypothesis. Existing target adapter boundaries and contract tests
are sufficient evidence when they remain isolated from canonical semantics.

### Make future architecture fully configurable

Rejected. Unlimited configurability weakens ownership and fail-closed semantics
and would introduce abstractions without accepted requirements.

### Include the Structurizr migration in this decision

Rejected. The need for concise architecture authority and one canonical model is
part of v1, but the notation, toolchain, rendering, and migration consequences
require their own research and technology/architecture decision.

## Consequences

The project now has a finite v1 outcome rather than an open-ended hardening
direction.

Future issues can be ordered by milestone and dependency and can be rejected
when they do not advance an accepted v1 criterion or an explicitly admitted
future scope transition.

Controlled evolution becomes a required architecture quality, but it does not
authorize speculative plugins, dynamic discovery, or unused abstractions.

The existing accepted implementation scope remains authoritative until a
separate scope transition changes it.

The existing PlantUML architecture authority and ADR-0003 remain in force until
a separate accepted architecture-model decision supersedes them.
