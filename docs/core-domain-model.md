# Agentic Workflow Generator — Core Domain Model

## Purpose

This document defines and owns the detailed platform-neutral core-domain
semantics used by `agentic-workflow-generator`.

It records the stable domain concepts, ownership rules and invariants that the
registry schemas, typed models, semantic validators, compiler and target
renderers must preserve.

The sole semantic architecture model is separate:

~~~text
docs/architecture/workspace.dsl
~~~

That workspace owns system boundaries, architectural responsibilities and
dependency directions. It intentionally does not duplicate the detailed entity
attributes, domain relationships and workflow/artifact semantics documented
here and enforced by contracts, source and tests.

The compiler pipeline and current architecture narrative are authoritative in:

~~~text
docs/architecture.md
~~~

The core model must not depend on OpenCode, VS Code Copilot or another target
platform. Target-specific translation belongs to target renderers and their
contract tests.

## Domain boundary

The stable conceptual entities are:

~~~text
Project
Setup
SetupQuestion
SetupOption
Bundle
Profile
Workflow
WorkflowState
Transition
WorkflowRoutingResult
WorkflowTestEvidenceRequirement
Gate
AgentProfile
AgentInstance
ModelAssignment
RoleBinding
SeparationPolicy
Capability
Skill
ArtifactContract
PermissionProfile
TargetAdapter
~~~

Compiler implementation types such as `CompiledComposition` and its compiled
children are not separate registry entities. They are immutable derived
representations of a validated bundle composition.

Lockfiles and output manifests are compiler outputs rather than registry domain
entities.

## Project

A project contains the metadata preserved in the active configuration:

~~~text
name
type
description
language profiles
runtime profiles
architecture profile
~~~

An initialized project selects exactly one active bundle and one or more enabled
targets.

Project metadata does not own agent assignments, workflow ownership, skills,
permissions or artifact production.

## Setup

A setup provides guided selection of:

~~~text
bundle
targets
~~~

A setup has one default selection and may contain questions with options that
override the selected bundle or targets.

Each question has exactly one default option.

A setup must not independently select profile, workflow, agent instances, role
bindings, capabilities, skills, permissions or artifacts. Those concrete values
belong to the selected bundle.

## Profile

A profile is advisory project metadata.

It may recommend:

~~~text
workflow
agent profiles
capabilities
language profiles
runtime profiles
~~~

Profile recommendations must never become fallback runtime authority.

## Bundle

A bundle owns the complete concrete composition:

~~~text
profile
workflow
agent instances
role bindings
separation policies
skills
artifacts
targets
~~~

A bundle is the only registry entity that assembles these concrete runtime
choices.

## Agent profile

An agent profile is a reusable advisory definition.

It contains recommendations and defaults such as:

~~~text
role
responsibilities
guardrails
capabilities
default permission profile
~~~

An agent profile is not a generated worker and does not own workflow state,
artifact production or effective permissions.

## Agent instance

An agent instance is a concrete worker owned by one bundle.

It explicitly selects:

~~~text
agent profile
display name
permission profile
shared-context policy
optional model assignment
~~~

Each agent instance has exactly one effective permission profile.

One agent instance may serve several role bindings when the bundle's separation
policies allow it.

## Model assignment

`ModelAssignment` is a bounded value owned by one concrete `AgentInstance`.

It contains exactly:

~~~text
provider
model
~~~

Both identities are non-empty. The value has no independent registry lifecycle,
provider catalogue, alias resolution or runtime routing authority.

A bundle either omits model assignment from every instance or declares it on
every instance. Once a bundle adopts explicit assignment, partial assignment is
invalid and must fail closed.

Compilation preserves the exact value on `CompiledAgentInstance`; active
configuration serializes the structured pair. A target may translate the pair to
target-native syntax only where accepted target semantics support it. It must not
choose, substitute, inherit or reinterpret a missing assignment.

A non-adopting bundle remains valid and gains no implicit canonical model.
Runtime provider/model unavailability is an acceptance concern and must not
trigger compiler fallback.

## Role binding

A role binding is the authoritative assignment of workflow responsibility to an
agent instance.

A binding owns:

~~~text
binding type
assigned agent instance
workflow state and gate when state-owned
required capabilities
selected skills
produced artifacts
responsibilities
guardrails
~~~

The supported binding types are:

~~~text
state-owner
workflow-controller
~~~

A state-owner binding owns exactly one non-terminal workflow state and its gate.

A workflow-controller binding owns routing authority and must not own a workflow
state or gate.

## Separation policy

A separation policy declares whether selected role bindings must use distinct
agent instances.

Separation is bundle-specific. It must not be inferred from agent profile names,
skills or global conventions.

## Capability

A capability is a stable platform-neutral identity used to connect workflow
requirements with concrete skill implementations.

Capabilities are currently represented by validated string identities. There is
no separate capability registry.

Role bindings own required capabilities. Skills provide capabilities.

## Skill

A skill is a concrete implementation of one or more capabilities.

A role binding explicitly selects the skills used for that role. Advisory agent
or profile recommendations must not install skills implicitly.

A selected skill must provide the capabilities required by its binding.

## Workflow

A workflow is a fail-closed state machine containing:

~~~text
start state
terminal states
states
transitions
gates
default failure state
~~~

Every non-terminal state has exactly one gate and exactly one state-owner
binding.

Terminal states have no gate and no role binding.

Every workflow has exactly one workflow-controller binding.

Each transition contains one source state, one target state and one closed typed
`WorkflowRoutingResult`. The canonical values and their serialized `on` values
are:

~~~text
PASS    -> pass
FAIL    -> fail
BLOCKED -> blocked
~~~

Every non-terminal state has exactly one transition for each canonical result.
There are no other transition events, and declaration order has no semantic
priority. Canonical serialization and rendering order transitions lexically by
`(source, serialized result, target)`.

Every `blocked` transition explicitly targets `defaultFailureState`, which is a
declared terminal state. A `pass` transition must not target
`defaultFailureState`. A `fail` transition may target either an explicit
remediation state or a terminal state, including `defaultFailureState`; that
route remains `FAIL` and is never reclassified as `BLOCKED` because of its target
name.

The workflow-controller binding is the sole route selector. It dispatches the
start state, receives an already-classified canonical result from the current
state owner, selects the unique matching transition and either dispatches the
target owner or stops at a terminal state. Missing, ambiguous or inconsistent
routing stops without transition; `defaultFailureState` is not an implicit
fallback.

State owners classify their governed gate result as `PASS`, `FAIL` or `BLOCKED`,
then return that result and control to the controller. They do not select or
execute transitions. Transitions and failure routing belong to the workflow,
not to agents or target renderers. The compiler does not add runtime execution,
state persistence, retry, escalation, aggregation or policy semantics.

## Gate

A gate is a blocking workflow quality boundary.

A gate owns:

~~~text
name
blocking policy
required capabilities
required artifacts and accepted statuses
required test-evidence categories when TestReport is required
~~~

`WorkflowTestEvidenceRequirement` is a closed typed vocabulary with exactly:

~~~text
changed-behavior-tests
project-validation-suite
~~~

`changed-behavior-tests` means repository-authoritative validation that directly
exercises the approved changed behavior.

`project-validation-suite` means the repository-authoritative broader
regression/validation suite applicable to the project.

A gate whose required artifacts include `TestReport` must own a non-empty
`requiredTestEvidence` set containing only these canonical identities and no
duplicates. A gate that does not require `TestReport` must not declare
`requiredTestEvidence`. Declaration order has no semantic meaning; typed,
compiled and serialized representations order identities lexically.

The workflow gate is the sole canonical owner of the required category set.
Targets derive the complete requirement from `CompiledWorkflowGate`; they do
not infer categories from skills, project prose, package metadata or test
commands.

Each required category maps to independently reproducible `TestReport` evidence
using the existing `claim`, `source`, `reproduction` and `result` fields.
`TestReport` remains the status authority for `PASS`, `FAIL` and `BLOCKED`, and
the state owner returns the already-classified result to the workflow
controller.

The compiler validates and preserves the static requirement set. It does not
discover validation commands, execute tests or invent runtime observations.
Runtime TestRunner behavior resolves repository-authoritative commands or
procedures and records the observations.

Pass, fail and blocked routing belongs to workflow transitions and the
workflow's explicit default failure state. Gates do not own routes, retry
limits or escalation policy.

The state-owner binding must provide the gate's required capabilities and
produce its required artifacts.

## Artifact contract

An artifact contract defines reproducible workflow evidence.

It includes:

~~~text
type
version
description
path pattern
status contract
provenance contract
revision contract
reproducible evidence contract
status invariant contract
artifact-specific status semantics contract
allowed statuses
required headings
schema
~~~

The provenance contract defines the canonical `## Provenance` heading and the
fixed required identities:

~~~text
artifactType
artifactVersion
workflow
workflowVersion
roleBinding
agentInstance
~~~

Concrete provenance values derive from the canonical compiled composition and
the existing artifact-production relationship. Provenance is evidence and does
not create a second ownership authority.

The revision contract defines the canonical `## Revision` heading and the
canonical positive-integer lexical form `^[1-9][0-9]*$`. Revision remains
separate from contract version, status, provenance, timestamps, VCS identity
and evidence hashes. Revision-history proof is not fabricated when no previous
edition is available to an existing validation boundary.

The reproducible evidence contract defines the canonical `## Evidence` heading
and the fixed required field set:

~~~text
claim
source
reproduction
result
~~~

The evidence section contains one or more records covering every
status-determining condition used to classify the artifact. Materially
independent conditions remain independently reproducible. Evidence records
supply observations to the status contract and do not become a second status
classifier. The compiler validates contract shape and deterministic propagation;
it does not claim to prove arbitrary produced Markdown evidence that it does not
ingest.

The status invariant contract defines the shared fail-closed evidence policy:

~~~text
passRequiresCompleteEvidence
passForbidsDemonstratedNonconformance
failRequiresDemonstratedNonconformance
blockedRequiresUnavailablePrerequisite
~~~

All four invariants are mandatory and true. They remain the shared necessary
conditions for valid status claims.

The artifact-specific status semantics contract defines the canonical meaning of
each status for one artifact type:

~~~text
passDefinition
failDefinition
blockedDefinition
mixedConditionRule
~~~

The three definitions are declarative contract text, not executable policy. For
the current governed artifact set, `mixedConditionRule` is exactly
`FAIL_ON_DEMONSTRATED_NONCONFORMANCE`: demonstrated outcome-determining
nonconformance remains `FAIL` even when another required prerequisite is
unavailable. Missing evidence alone does not become `FAIL`, and absence of known
failure is insufficient for `PASS`.

Artifact contracts own these canonical meanings. The producing role binding
evaluates evidence and chooses the matching status. Workflow controllers route
already-produced results and do not gain classification authority.

Artifact production belongs to role bindings. Agent profiles do not own produced
artifacts.

A producing role binding owns the complete governed artifact content and its
classification under the artifact contract. `produces` does not grant or imply
direct repository write, edit or shell authority. Direct actions remain governed
only by the producing agent instance's effective permission profile.

Artifact content production and materialization are distinct runtime
responsibilities. When the producing agent cannot perform the repository mutation
required by the artifact contract's `pathPattern`, it returns the complete
contract-conformant artifact content through the target/framework handoff.
Persistence/materialization then occurs outside that agent instance's permission
profile at the surrounding target execution boundary or its caller. This does not
introduce a materializer role, persistence service, artifact store, workflow
engine or compiler runtime responsibility.

A governed produced artifact is runtime-available to a downstream consumer only
after one complete edition has been materialized at a concrete location satisfying
the artifact contract's `pathPattern` and is readable by that consumer. Proposed
conversation content alone is not materialized workflow memory. The workflow
controller must not dispatch a downstream state whose required governed input has
not crossed this boundary, and the controller does not become the artifact writer.

Materialization remains fail closed. If required produced content cannot be
materialized or made readable, `PASS` is unavailable. Absent independently
demonstrated nonconformance the producing state returns `BLOCKED`; demonstrated
outcome-determining nonconformance remains `FAIL` under the artifact contract's
existing mixed-condition rule. Targets must not substitute conversation-only
content, an invented path, an ungoverned temporary file or a stale artifact
edition.

## Permission profile

A permission profile is a platform-neutral effective permission definition.

Each concrete agent instance explicitly selects one permission profile.

Every enabled target adapter must provide a valid mapping for each effective
permission profile used by the compiled composition.

Permission mappings must preserve the complete canonical direct-action authority
without silent omission or broadening. Target-native controls may group several
canonical actions only when the grouping does not grant an action that the
canonical profile denies. If a target cannot preserve an applicable permission
distinction, generation must fail explicitly.

The canonical boolean fields are direct-action authority:

- `read=true` permits direct repository reads and `read=false` forbids them;
- `write=true` permits direct file creation/write operations and `write=false`
  forbids them;
- `edit=true` permits direct modification of existing repository content and
  `edit=false` forbids it.

Current V1 profiles use `write` and `edit` together. A future profile that
distinguishes them must fail for a target that cannot preserve that distinction
unless a separately accepted decision changes the target representation.

`bash` has exactly three canonical meanings:

- `deny` — the agent has no direct shell authority;
- `limited` — direct shell invocation is available only through the target
  host's ordinary approval boundary; the generated project must not select,
  synthesize or rely on an auto-approval/bypass mode for that agent;
- `allow` — the project-level profile imposes no additional approval requirement
  on direct shell invocation, although the target host or user may still apply
  stricter approval, sandbox or policy controls.

`limited` is approval-gated shell authority. It is not a hidden command
whitelist, command-discovery mechanism or target-specific rule set. The current
permission profile contains no canonical command-pattern payload, so a target
must not invent one. A future requirement for governed command subsets requires
a separate accepted domain/scope decision.

Explicit host/user/session overrides that intentionally bypass normal approval
controls are outside the generated project's permission-preservation contract.
The generator must not emit, enable or recommend such a bypass to satisfy a
canonical permission profile.

For the current targets, `limited` is preserved as follows:

- OpenCode uses its per-agent `bash: ask` permission in the normal permission
  mode; explicit `--auto`/auto-approve operation is outside the supported
  preservation mode for a limited-shell agent.
- VS Code Copilot exposes the terminal tool to a limited-shell agent but requires
  the normal `Default Approvals` execution mode. `Bypass Approvals` and
  `Autopilot` are outside the supported preservation mode for that agent.
  Generated agent guidance must make this host prerequisite explicit because
  the custom-agent `tools` field controls tool availability rather than the
  session approval level.

A read-only artifact producer remains read-only. Artifact ownership does not
synthesize write/edit/shell authority merely to satisfy an output path. Such a
producer returns complete governed artifact content for mediated materialization
outside its effective permission profile. A target/framework persistence operation
must not be exposed back to that producer as an undeclared mutation tool.

## Target adapter

A target adapter registry entry owns only:

~~~text
name
version
description
output paths
owned paths
permission mapping
~~~

Target-specific file formats, handoff rendering and validation behavior belong
to renderer code and contract tests.

Both current target renderers must preserve the artifact production/materialization
boundary from canonical compiled artifact production, artifact contracts and
effective permissions. A renderer that cannot preserve required content ownership,
mediated handoff, materialized-availability or fail-closed semantics must fail
explicitly rather than broaden permissions or omit the requirement.

Target adapters do not define:

~~~text
generic feature flags
templates
plugin discovery
runtime-context generation
fallback behavior
degraded-output policies
target-independent domain rules
~~~

## Compiler boundary

Validated registry data is compiled into one immutable
`CompiledComposition`.

The compiled composition resolves:

~~~text
project metadata
bundle and version
profile
workflow
enabled targets
agent instances
role bindings
state ownership
controller binding
effective permission profiles
selected skills
artifact contracts
workflow gates including required test-evidence categories
artifact production
separation constraints
~~~

`CompiledComposition` is the compiler's only internal intermediate
representation.

The active `.agentic/agentic.json` is its persistent serialization. Each
serialized workflow gate carries canonical `requiredTestEvidence`: the complete
lexically ordered category set for `TestReport` gates and an empty list for
other compiled gates.

There is no separate persisted resolution model.

The compiler validates and preserves static artifact-production ownership,
contracts, input references and effective permissions. It does not execute
artifact-producing agents, persist runtime artifact content, select concrete
runtime artifact editions, prove runtime materialization, or add workflow runtime
state solely to track materialization.

Target generation must consume the typed active configuration or the in-memory
compiled composition. It must not reinterpret raw registry files.

## Compiler outputs

The lockfile records compiler-input provenance and integrity.

The output manifest records generated-file ownership and integrity:

~~~text
enabled targets
owned paths
generated file paths
byte sizes
content hashes
~~~

Neither file is a second representation of the domain composition.

## Required invariants

Validation and compilation must fail when any of these invariants are broken:

~~~text
all registry references resolve exactly
every non-terminal state has one state-owner binding
every workflow has one controller binding
controller bindings own no state or gate
every transition result is exactly pass, fail or blocked
every non-terminal state has exactly one route for each canonical result
terminal states have no outgoing transitions
every blocked route targets the terminal default failure state
no pass route targets the default failure state
all transition endpoints exist and all states preserve reachability invariants
selected skills belong to the bundle
selected skills cover binding-required capabilities
produced artifacts belong to the bundle
gate-required artifacts are produced by the state owner
every TestReport gate owns non-empty canonical required test evidence
non-TestReport gates do not declare required test evidence
test-evidence identities are known, unique and lexically canonicalized
each agent instance has one effective permission profile
every effective permission maps through every enabled target
separation policies reference valid bindings
required distinct bindings use distinct instances
target output remains inside declared owned paths
target-owned paths do not overlap
targets preserve complete compiled test-evidence semantics or fail explicitly
artifact production ownership never broadens effective agent permissions
read-only artifact producers use mediated target/framework materialization
conversation-only produced content is not treated as materialized governed input
downstream dispatch requires required governed inputs to be materialized and readable
materialization failure forbids PASS and remains fail closed under artifact status semantics
workflow controllers do not gain artifact persistence or materialization ownership
targets preserve the compiled artifact materialization boundary or fail explicitly
~~~

There is no fallback, compatibility projection or silent degradation.

## Current non-goals

The current breaking migration does not introduce:

~~~text
additional target platforms
runtime-context generation
autonomous workflow execution
test-command discovery or compiler-side test execution
dynamic plugins
template engines
target feature negotiation
generic target DSLs
model hosting
~~~
