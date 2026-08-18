# ADR-0015: Canonical model-assignment ownership

- Status: Accepted
- Date: 2026-08-18
- Accepted baseline: `development` @ `f25507966f8ebc327dc2899698864987b1ae2dd7`
- Decision issue: #96
- Goal: #86
- Scope transition: #94 / PR #95

## Summary

Explicit supported per-agent model assignment is owned by the concrete
`AgentInstance` and represented by one bounded typed `ModelAssignment` value
containing `provider` and `model`.

`ModelAssignment` is not a separate registry entity, provider catalogue, routing
layer, service or target-specific configuration object.

Model assignment is optional across bundles but all-or-none within an adopting
bundle:

- zero assigned instances means the bundle does not govern model choice;
- if any instance declares an assignment, every instance must declare one.

The Goal #86 Agent Factory composition adopts the capability and therefore
requires an explicit assignment for every concrete agent instance.

`CompiledAgentInstance` preserves the value unchanged. `.agentic/agentic.json`
serializes the structured provider/model value. OpenCode only translates it to
its target-native per-agent `model` syntax and must not infer, default, merge or
reinterpret it.

Existing bundles with no assignments remain valid. Their omission is
non-adoption, not compiler fallback.

## Context

Current authority already separates concrete worker configuration from workflow
responsibility:

- `AgentInstance` owns concrete worker identity/configuration;
- `RoleBinding` owns workflow-role semantics;
- one agent instance may serve multiple role bindings;
- `CompiledAgentInstance` is the canonical resolved worker consumed by targets;
- targets translate canonical compiled semantics and do not re-resolve raw
  registry input.

OpenCode can express an agent-specific model value. The unresolved question is
where that value becomes canonical and how requiredness behaves without a second
semantic authority.

## Decision

### 1. Ownership

`AgentInstance` owns `modelAssignment`.

It does not belong to `AgentProfile`: profiles remain advisory.

It does not belong to `RoleBinding`: binding ownership would allow conflicting
values for one concrete generated agent when one instance serves several
bindings and would require new merge/precedence semantics.

### 2. Bounded value object

The canonical value contains exactly:

~~~text
provider
model
~~~

Both are non-empty validated identities.

The value has no independent lifecycle, registry collection, lookup authority,
aliasing or resolution mechanism. No model registry, provider catalogue, routing
table or dynamic discovery is introduced.

### 3. All-or-none bundle adoption

A bundle is non-adopting when all agent instances omit `modelAssignment`.

If any instance declares it, every instance must declare it. Partial adoption is
statically invalid.

This avoids a separate feature flag, bundle-name hardcoding and silent target
inheritance for missing values.

### 4. Compilation and serialization

Validated registry input constructs the typed value on `AgentInstance`.
Compilation copies it to `CompiledAgentInstance` without provider mapping,
alias resolution, runtime lookup or fallback.

For adopting bundles, active configuration preserves:

~~~json
{
  "modelAssignment": {
    "provider": "<provider>",
    "model": "<model>"
  }
}
~~~

For non-adopting bundles the field is absent.

The later implementation must perform the normal active-config schema-version
transition and synchronize canonical lock/generated state where required.

### 5. Target boundary

OpenCode joins/translates the canonical provider/model identity into the
target-native per-agent `model` field.

The renderer must not:

- choose a model;
- substitute provider/model values;
- inherit a primary-agent model to fill a missing canonical assignment;
- consult raw registry input;
- treat unmanaged target configuration as canonical authority.

If required canonical assignment cannot be preserved, generation fails
explicitly.

This decision does not generalize model routing to other targets.

### 6. Static validity versus runtime availability

Static validation rejects malformed values and partially assigned bundles.

The compiler does not query live model catalogues, credentials or provider
availability. A statically valid model may still be unavailable in a concrete
OpenCode runtime; Goal #86 acceptance therefore requires OpenCode runtime
validation.

Runtime unavailability must not trigger compiler fallback or substitution.

### 7. Existing bundles

Existing bundles with zero assignments remain semantically unchanged. Their
meaning is that model selection is not governed by the composition.

No profile, target default, previous generated output or runtime model becomes
canonical fallback authority.

### 8. Current-state authority

This ADR accepts semantics before implementation.

`docs/architecture.md`, `docs/architecture/workspace.dsl` and
`docs/core-domain-model.md` remain current-state documents and are not changed by
this decision PR. The implementation slice updates detailed domain authority when
the typed semantics become executable.

The architecture model changes only if implementation changes a modeled
responsibility boundary or dependency direction; this decision intentionally
keeps ownership inside existing bundle/agent-instance and compiler boundaries.

## Alternatives considered

### `RoleBinding` owns model assignment

Rejected. Multiple bindings may share one agent instance, producing conflicts and
requiring new precedence/merge semantics.

### Opaque target-native string on `AgentInstance`

Rejected as canonical form. It would store target syntax in the platform-neutral
core. The bounded provider/model value preserves the same minimal information.

### Separate model registry or routing entity

Rejected. The use case is explicit static assignment, not provider discovery,
routing, aliases, model hosting or dynamic selection.

### `AgentProfile` owns a default

Rejected. Profiles are advisory and must not become implicit runtime authority.

### Partial assignments with OpenCode inheritance

Rejected. Once a bundle adopts governed explicit assignment, a missing value must
fail closed rather than be completed by target runtime defaults.

### Require assignments for all existing bundles

Rejected. That would widen scope and alter accepted V1 behavior without a
demonstrated need.

## Consequences

The later implementation adds one small typed value and one optional
agent-instance field across the existing registry -> validation -> compiler ->
active-config path.

Bundle validation gains one all-or-none invariant.

OpenCode rendering gains deterministic preservation of the canonical assignment.

No provider SDK, model API, credential integration, runtime selection algorithm,
plugin mechanism, model registry or new target is introduced.

## Acceptance scenarios

1. A bundle with zero assignments remains valid and gains no implicit canonical
   model.
2. An adopting bundle with assignments on every instance validates.
3. A partially assigned bundle fails closed.
4. Empty provider or model identities fail validation.
5. `CompiledAgentInstance` preserves the exact validated pair.
6. `.agentic/agentic.json` preserves structured canonical assignment.
7. OpenCode output preserves the corresponding explicit per-agent model value.
8. OpenCode runtime validation accepts the materialized Agent Factory
   composition.
9. Repeat generation is idempotent and manifest ownership remains canonical.
10. No target, profile, role binding, previous output or runtime default supplies
    a missing canonical assignment.
11. Existing non-adopting bundles remain valid.
12. Deterministic compilation requires no live provider/model lookup.
