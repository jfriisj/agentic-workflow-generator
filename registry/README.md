# Agentic Registry

This registry contains reusable, platform-neutral definitions used by the
Agentic Workflow Generator compiler.

The registry is the source for:

- agent profiles
- skills
- capabilities
- workflows
- bundles
- profiles
- setups
- artifact contracts
- target adapters

The active project configuration is materialized under:

~~~text
.agentic/agentic.json
~~~

## Registry principle

The project selects a validated composition.

The registry defines reusable building blocks.

The compiler resolves and materializes:

~~~text
Setup
  -> Bundle
  -> Profile and workflow
  -> Agent instances
  -> Role bindings
  -> Capabilities and skills
  -> Permissions and guardrails
  -> Gates and artifact contracts
  -> Target adapters
  -> Generated output
~~~

## Architecture and domain model

The current-state architecture narrative is owned by `docs/architecture.md`. The
sole semantic architecture model is `docs/architecture/workspace.dsl`, and
detailed platform-neutral domain semantics are owned by
`docs/core-domain-model.md`. Stakeholder-facing SVG views under
`docs/architecture/diagrams/` are reproducible derived output rather than semantic
authority.

The central target-model distinction is:

~~~text
Agent profile
  -> Agent instance
  -> Role binding
  -> Workflow state and gate
~~~

An agent profile contains reusable defaults and recommendations.

An agent instance is a concrete worker generated for a bundle. It owns one
effective permission profile and materializes the combined requirements of
all role bindings assigned to it.

A role binding owns role-specific capabilities, selected skills, artifact
responsibility, responsibilities, and guardrails.

A state-owner binding owns exactly one non-terminal workflow state and its
gate. A workflow-controller binding owns routing authority but no state or
gate. Every workflow has exactly one controller binding.

A separation policy declares when two or more role bindings must use distinct
agent instances.

## Composition rules

Skills are composable capability providers.

A skill may recommend common agent profiles, but recommendations must not
prevent another agent instance from receiving the skill through a validated
composition.

Profiles provide recommendations and compatibility metadata.

Bundles select the effective workflow and concrete composition.

Setups select registered bundles through validated guided choices.

Hard restrictions are reserved for explicit safety invariants:

- fail-closed execution
- validated and unambiguous transitions
- required gate evidence
- explicit separation of duties
- target-compatible permissions
- no implicit fallback

## Current implementation status

The registry is migrated to the authoritative composition model:

~~~text
AgentProfile
  -> AgentInstance
  -> RoleBinding
  -> CompiledComposition
  -> TargetAdapter
~~~

Agent profiles contain reusable recommendations and defaults only.

Bundles own concrete agent instances, role bindings, selected skills,
artifact production, effective permission profiles, workflow ownership and
separation policies.

Target adapters are immutable typed registry entities containing only:

~~~text
name
version
description
outputPaths
ownedPaths
permissionMapping
~~~

Every registered target adapter must map every registered permission profile
exactly once. Output paths must be safe, deterministic and contained within
the adapter's non-overlapping owned paths.

The typed registry snapshot and compiler consume validated `TargetAdapter`
objects directly. There is no compatibility projection, fallback target model
or separate semantic target validator.

Target renderers consume canonical `CompiledComposition` semantics directly.
Both supported V1 targets preserve applicable canonical semantics through typed
target rendering and fail-closed validation without introducing a second target
semantic authority.

## Registry scope

The registry is local and committed to this repository.

Later versions may support:

- global registries
- Git-based registries
- remote registries
- versioned registry packages
