# ADR-0015: Fail-closed target permission preservation

- Status: Accepted
- Date: 2026-08-14
- Accepted baseline: `development` @ `8fa112bbbe7887a52d530421ce70b9ce22b57e4d`
- Decision issue: #70
- Goal: #50

## Summary

The canonical `PermissionProfile` is platform-neutral direct-action authority.
Both supported targets must preserve every applicable permission without
target-side omission, broadening or fallback.

The existing `BashPermission` vocabulary keeps exactly three values:

~~~text
deny
limited
allow
~~~

`limited` means approval-gated shell authority. It does not mean an unspecified
command whitelist.

For the current targets:

- OpenCode preserves `limited` with per-agent `bash: ask` in normal permission
  mode.
- VS Code Copilot preserves `limited` by exposing its terminal tool while the
  agent runs under the host's normal `Default Approvals` execution mode.
  `Bypass Approvals` and `Autopilot` are not supported preservation modes for a
  limited-shell agent.

Explicit user/host modes that intentionally bypass approval controls are outside
the generated project's permission-preservation contract. The generator must
not emit, enable or recommend such a bypass as a way to satisfy canonical
permissions.

The current target-adapter/domain schema is sufficient for the bounded V1 repair.
No new permission vocabulary, command-policy DSL or generic target feature model
is introduced.

## Context

Goal #50 requires both current V1 targets to preserve every applicable canonical
`CompiledComposition` semantic or fail generation.

Research #69 found a concrete permission-preservation defect around the current
`test-runner` profile:

~~~text
read  = true
write = true
edit  = true
bash  = limited
~~~

The generated OpenCode agent currently renders `bash: allow`, which removes the
canonical distinction between `limited` and `allow`.

The generated VS Code Copilot agent currently exposes terminal execution but
omits the edit tool even though the canonical profile has `write=true` and
`edit=true`.

The accepted core model already requires that target permission mappings never
silently broaden effective permissions, but it does not define the normative
meaning of `bash=limited`. Repository source likewise validates the closed enum
and basic read prerequisites without defining a command subset or approval
contract.

A durable decision is therefore required before repairing mappings or renderers.

## External target evidence

The decision uses current primary target documentation verified on 2026-08-14.

OpenCode documents that permission rules resolve to `allow`, `ask` or `deny`;
that `ask` requires approval before the action runs; that permissions may be
overridden per agent; and that shell rules may additionally be pattern-based.
OpenCode also provides an explicit auto-approve mode that converts ordinary
approval requests into automatic approvals while continuing to enforce explicit
denials.

VS Code documents that custom-agent `tools` controls tool availability. Approval
behavior is governed separately by the host's session permission level and
approval settings. `Default Approvals` applies normal approval rules, while
`Bypass Approvals` and `Autopilot` auto-approve tool calls. Terminal commands have
their own approval rules. Agent-scoped hooks can influence approvals but remain
Preview functionality and require explicit enablement, so they are not adopted
as the stable V1 permission-preservation boundary.

This ADR depends on these documented target surfaces but does not make either
target's terminology canonical domain authority.

## Decision

### 1. Permission profiles define direct-action authority

`PermissionProfile` remains the sole canonical authority for direct actions
available to a concrete agent instance.

The boolean fields mean:

- `read=true` permits direct repository reads;
- `write=true` permits direct file creation/write operations;
- `edit=true` permits direct modification of existing repository content.

A false value forbids the corresponding direct action.

Target-native tools may combine canonical action classes. Such a combined tool
is acceptable only when enabling it preserves every relevant canonical boolean.
If a target-native tool would grant an action whose canonical value is false, the
profile is not representable by that mapping and generation must fail.

The current V1 profiles do not distinguish `write` from `edit`: both are false
for `read-only` and both are true for `implementation` and `test-runner`. This
ADR does not add a target abstraction for a hypothetical future split.

### 2. Canonical bash meanings

`BashPermission` keeps its existing closed values.

#### `deny`

The agent has no direct shell authority.

The target must not expose usable shell execution to that agent.

#### `limited`

The agent may invoke shell execution only through the target host's ordinary
approval boundary.

This is an approval constraint, not a command whitelist. The current
`PermissionProfile` has no canonical allowed-command or denied-command payload.
Targets must not infer such a subset from skills, responsibilities, repository
files or target defaults.

A limited-shell mapping must not select or generate an auto-approval/bypass mode.

#### `allow`

The project-level profile imposes no additional approval requirement on shell
invocation.

A target host may still apply its own stricter user, organization, sandbox or
security controls. Such host controls do not weaken canonical project
permissions; they are an outer execution boundary.

`allow` therefore does not require the generator to disable host safeguards or
force an auto-approval mode.

### 3. Explicit host overrides are outside the generated contract

A user or host may explicitly select a mode that is more permissive than the
normal generated-project contract.

Examples include OpenCode auto-approve operation and VS Code `Bypass Approvals`
or `Autopilot`.

Those are explicit execution-host overrides, not target mappings produced by
`agentic-workflow-generator`.

For a limited-shell agent, the generator must not:

- emit such a bypass mode;
- instruct the user to enable it;
- treat it as equivalent to the canonical profile;
- rely on it to make generation succeed.

Running a limited-shell agent under such an explicit bypass is outside the
supported permission-preservation mode.

### 4. OpenCode V1 mapping

For the three current effective profiles, the target mapping is:

| Canonical profile | `edit` | `bash` |
| --- | --- | --- |
| `read-only` | `deny` | `deny` |
| `implementation` | `allow` | `allow` |
| `test-runner` | `allow` | `ask` |

OpenCode's `edit` permission gates file modification operations. Because current
writable V1 profiles have both `write=true` and `edit=true`, this target-native
grouping preserves the current canonical boolean combinations.

`test-runner -> bash: ask` preserves `limited` without inventing command rules.

This ADR does not add granular bash patterns. If future scope requires a
canonical command subset, that requires a separate accepted decision and a
domain representation for the subset.

### 5. VS Code Copilot V1 mapping

VS Code custom-agent `tools` is an availability boundary, not a complete approval
policy.

For current profiles:

- read tools must be available when `read=true`;
- edit/write capability must be available when the profile has current V1
  `write=true` and `edit=true`;
- terminal execution must be absent when `bash=deny`;
- terminal execution must be available when `bash=limited` or `bash=allow`.

For `bash=limited`, the supported execution contract additionally requires the
host's `Default Approvals` mode. The generated limited-shell agent guidance must
state that prerequisite and must state that `Bypass Approvals` and `Autopilot`
are unsupported for preserving that agent's canonical permission profile.

The generator does not attempt to force a session permission level from custom
agent frontmatter because the target does not expose that stable contract there.

Agent-scoped hooks are not adopted for this purpose in V1 because the current
VS Code documentation marks custom-agent hooks as Preview and requires explicit
enablement.

### 6. Preservation is checked against canonical profiles

Target rendering must compare the effective canonical `PermissionProfile` with
the target-native representation.

Validation must reject at least:

- a denied canonical action exposed by the target mapping;
- a required current canonical action omitted by the mapping;
- `bash=limited` rendered as unrestricted OpenCode `allow`;
- `bash=deny` with usable target shell execution;
- a VS Code writable current V1 profile without edit/write tool capability;
- a VS Code limited-shell representation that omits the required host-mode
  guidance;
- any future canonical permission combination that the target cannot represent
  without omission or broadening.

Failure is explicit `TargetRenderingError` or the existing deterministic
validation boundary appropriate to the mapping. There is no degraded output.

### 7. Existing domain and adapter schema remain sufficient

No new canonical permission enum, target feature flag, command-policy entity,
permission DSL or generic capability negotiation layer is introduced.

The existing objects remain authoritative:

~~~text
PermissionProfile
TargetAdapter.permission_mappings
CompiledAgentInstance.permission_profile
target renderer
target rendering/integration tests
~~~

The implementation may strengthen target-specific validation and rendering using
these existing objects.

If implementation demonstrates that the existing target adapter representation
cannot carry the required current-target mapping without a new canonical domain
concept, work must stop and return to decision/scope rather than extending the
model opportunistically.

## Consequences

### Positive

- `limited` gains one explicit platform-neutral meaning.
- OpenCode no longer needs to broaden `limited` to unrestricted shell access.
- VS Code's distinction between tool availability and host approvals is made
  explicit rather than silently conflated.
- Current writable `test-runner` semantics require VS Code edit/write capability
  instead of silently omitting it.
- Unsupported future permission combinations remain fail closed.
- No command whitelist or generic permission DSL is invented without an accepted
  requirement.

### Tradeoffs

- Limited-shell preservation depends on the target host's normal approval mode,
  so an explicit user/session bypass can run outside the supported generated
  contract.
- VS Code cannot encode the entire limited-shell contract in the custom-agent
  `tools` field alone; deterministic generated guidance is part of the V1 target
  representation.
- Current V1 does not standardize granular shell-command subsets.

## Implementation boundary

A follow-up implementation child under Goal #50 may:

- change the OpenCode `test-runner` mapping from `bash: allow` to `bash: ask`;
- restore VS Code edit/write tool capability for `test-runner`;
- render deterministic limited-shell host-mode guidance where applicable;
- add fail-closed semantic permission-preservation validation;
- add focused and cross-target tests;
- regenerate canonical target output and output manifest when required.

That implementation must not:

- add a new permission vocabulary;
- add command patterns to canonical `PermissionProfile`;
- adopt Preview VS Code hooks as required V1 infrastructure;
- add a third target or generic target DSL;
- weaken host security controls;
- alter artifact materialization ownership from ADR-0014.

## Acceptance

This decision is accepted when:

- this ADR exists on accepted `development`;
- `docs/core-domain-model.md` carries the same canonical permission semantics;
- the accepted result resolves #70 without implementation changes;
- the permission-repair implementation can be specified without unresolved
  semantic choices.

After merge, re-read `development`, #70, Goal #50 and #71 before creating or
promoting the bounded permission-repair implementation child.
