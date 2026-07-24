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

## Conceptual domain model

The authoritative conceptual entity and relationship model is:

~~~text
docs/diagrams/agentic-domain-model-chen.puml
~~~

The rendered SVG is:

~~~text
docs/diagrams/agentic-domain-model-chen.svg
~~~

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

The current MVP still materializes capabilities, permission defaults, and
artifact responsibility directly from static agent definitions.

The target composition-binding model is documented but not yet fully
implemented.

Until that migration is complete, validators must continue to fail closed and
must not silently emulate the target model.

## Registry scope

The registry is local and committed to this repository.

Later versions may support:

- global registries
- Git-based registries
- remote registries
- versioned registry packages
