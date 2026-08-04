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
Gate
AgentProfile
AgentInstance
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
~~~

Each agent instance has exactly one effective permission profile.

One agent instance may serve several role bindings when the bundle's separation
policies allow it.

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

Transitions and failure routing belong to the workflow, not to agents or target
renderers.

## Gate

A gate is a blocking workflow quality boundary.

A gate owns:

~~~text
name
blocking policy
required capabilities
required artifacts and accepted statuses
~~~

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

## Permission profile

A permission profile is a platform-neutral effective permission definition.

Each concrete agent instance explicitly selects one permission profile.

Every enabled target adapter must provide a valid mapping for each effective
permission profile used by the compiled composition.

Permission mappings must never silently broaden permissions.

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
workflow gates
artifact production
separation constraints
~~~

`CompiledComposition` is the compiler's only internal intermediate
representation.

The active `.agentic/agentic.json` is its persistent serialization.

There is no separate persisted resolution model.

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
selected skills belong to the bundle
selected skills cover binding-required capabilities
produced artifacts belong to the bundle
gate-required artifacts are produced by the state owner
each agent instance has one effective permission profile
every effective permission maps through every enabled target
separation policies reference valid bindings
required distinct bindings use distinct instances
target output remains inside declared owned paths
target-owned paths do not overlap
~~~

There is no fallback, compatibility projection or silent degradation.

## Current non-goals

The current breaking migration does not introduce:

~~~text
additional target platforms
runtime-context generation
autonomous workflow execution
dynamic plugins
template engines
target feature negotiation
generic target DSLs
model hosting
~~~
