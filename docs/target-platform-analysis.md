# Target Platform Analysis

## Purpose

This document defines the current target-generation boundary for
`agentic-workflow-generator`.

The compiler remains platform-neutral. Target renderers translate one validated
`CompiledComposition` into platform-specific files without reinterpreting raw
registry data.

This document defines the target architecture being implemented by the current
breaking migration. It is not a list of possible future platforms.

## Supported targets

The current migration supports exactly two target contracts:

~~~text
opencode
vscode-copilot
~~~

No additional targets are part of the breaking migration.

Codex, Claude Code and other platforms require a separate future scope decision
after the current compiler is globally green.

## Target-generation input

Migrated target generation must consume the canonical compiled composition
represented by the active `.agentic/agentic.json`.

It must not consume:

- raw agent, bundle, workflow or skill registry JSON directly
- a separate persisted resolution model
- legacy `agents` or workflow-state `agent` fields
- inferred capabilities or artifact ownership
- advisory profile defaults as runtime fallback

Role bindings, agent instances, effective permissions, selected skills,
artifact production, workflow ownership and controller authority are already
resolved before target rendering begins.

## Target adapter contract

A registered target adapter owns only:

~~~text
name
version
description
outputPaths
ownedPaths
permissionMapping
~~~

The adapter does not define:

- generic feature flags
- degraded-output policies
- templates or template paths
- plugin discovery
- runtime-context generation
- warnings that replace required semantics
- target-independent business rules

Target-specific rendering behavior belongs to Python renderer code and contract
tests.

## OpenCode

The OpenCode target contract requires the renderer to generate:

~~~text
.opencode/agents/*.md
.opencode/skills/<skill-name>/SKILL.md
.opencode/skills/<skill-name>/skill.json
AGENTS.md
opencode.json
~~~

The renderer maps effective permission profiles to OpenCode edit and bash
permissions.

Generated files must remain inside the adapter's declared owned paths.

OpenCode runtime parsing is an end-to-end validation of generated output. It is
not runtime-context generation or workflow orchestration.

## VS Code Copilot

The VS Code Copilot target contract requires the renderer to generate:

~~~text
.github/agents/*.agent.md
.github/skills/<skill-name>/SKILL.md
.github/skills/<skill-name>/skill.json
.github/copilot-instructions.md
~~~

The renderer maps effective permission profiles to explicit Copilot tool lists.

Generated files must remain inside the adapter's declared owned paths.

Handoffs are rendered using Copilot-supported output where available and
explicit instructions where required by the target contract. Required workflow
semantics must not be silently removed.

## Compatibility policy

Target generation is fail-closed.

Generation fails when:

- a selected target adapter is missing
- an effective permission profile has no target mapping
- a required target output cannot represent mandatory semantics
- an output path escapes the adapter's owned paths
- target-owned paths overlap
- rendered output fails its target contract
- runtime parsing rejects generated OpenCode output

The compiler does not produce degraded output with warnings as a substitute for
required behavior.

## Output ownership

Each migrated target renderer must produce a deterministic output plan before
filesystem writes.

The generation application service validates the complete plan and commits all
changed target files transactionally.

The output manifest records:

- enabled targets
- owned paths
- generated file paths
- byte sizes
- content hashes

The manifest documents generated-output ownership and integrity. It does not
duplicate the compiled composition.

## Non-goals during migration

The current migration does not introduce:

- new target platforms
- runtime-context files
- autonomous workflow execution
- dynamic plugins
- a template engine
- target feature negotiation
- generic renderer configuration
- fallback or silent degradation

A future target may be added only after the current migration is green and a
concrete target contract, renderer and test boundary have been defined.
