# Architecture

`agentic-workflow-generator` is a platform-neutral compiler for agentic software delivery workflows.

It takes a registry-based source of truth and generates target-specific agent configuration for coding-agent environments such as VS Code Copilot and OpenCode.

The architecture is intentionally deterministic, fail-fast, and validation-heavy.

## Conceptual domain model

The target domain model is maintained as a Chen entity-relationship diagram:

~~~text
docs/diagrams/agentic-domain-model-chen.puml
~~~

A rendered SVG is maintained beside the source:

~~~text
docs/diagrams/agentic-domain-model-chen.svg
~~~

The diagram is authoritative for entity boundaries and conceptual relationships. JSON schemas, registry validators, materialization, resolution, and target generation must remain consistent with it.

The central composition chain is:

~~~text
Agent profile
  -> Agent instance
  -> Role binding
  -> Workflow state and gate
~~~

Agent profiles and skill recommendations are reusable defaults. The active bundle owns concrete agent instances, role bindings, capabilities, selected skills, instance-level permissions, artifacts, guardrails, controller authority, and separation policies.

## High-level flow

```text
registry/
  agents/
  skills/
  workflows/
  bundles/
  artifacts/
  profiles/
  targets/
        ↓
bundle selection
        ↓
scripts/agentic/agentic-gen.sh init --bundle <bundle>
        ↓
.agentic/agentic.json
        ↓
resolution + lockfile
        ↓
target-specific generation
        ↓
output manifest
        ↓
validation gates + negative gates
```

## Design principle

The project treats agentic workflow setup as a compiler problem.

Instead of manually maintaining several target-specific agent files, the project keeps declarative registry files as the source of truth and compiles them into generated output.

The core design goals are:

```text
single source of truth
deterministic generation
fail-fast validation
no fallback behavior
target independence
reproducible generated output
explicit artifact contracts
gate-based workflow routing
```

## Registry source of truth

The registry contains reusable definitions.

```text
registry/
  agents/
  artifacts/
  bundles/
  profiles/
  skills/
  targets/
  workflows/
```

Each registry area has a specific responsibility.

| Registry area | Responsibility |
|---|---|
| `agents/` | Reusable agent profiles with recommended responsibilities, capabilities, permission defaults, and boundaries |
| `skills/` | Composable capability providers available to validated workflow-role bindings |
| `workflows/` | State machine, transitions, gates, start state, terminal states, and fail-closed routing |
| `bundles/` | Complete deployable composition of workflow, agents, skills, artifacts, profile, and targets |
| `artifacts/` | Output contracts required by gates and produced by agents |
| `profiles/` | Higher-level workflow profile metadata |
| `targets/` | Target adapter ownership rules for generated output |

The registry is validated before generation.

## Bundle composition

A bundle selects a complete configuration.

Example:

```text
registry/bundles/orchestrated-delivery.bundle.json
```

A bundle defines:

```text
workflow
profile
agents
skills
artifacts
targets
```

Bundle validation checks that the selected composition is internally complete:

```text
workflow states are covered by bundle agents
workflow transitions stay inside the selected workflow
agent capabilities are provided by bundle skills
agent produced artifacts are included in bundle artifacts
bundle targets resolve to matching target adapters
profile workflow matches bundle workflow
```

This makes a bundle more than a list of references. It becomes a deployable composition.

## Composition binding direction

The current MVP derives active capabilities, permissions, and produced artifacts directly from static agent definitions. That model is being replaced because it prevents compact setups from assigning several responsibilities to one agent.

The target model introduces concrete agent instances and explicit role bindings.

An agent instance selects:

~~~text
agent profile
effective permission profile
shared-context policy
~~~

A role binding selects:

~~~text
binding type: state owner or workflow controller
assigned agent instance
workflow state when binding type is state owner
required capabilities
selected skills
produced artifacts
role-specific responsibilities
role-specific guardrails
~~~

Every non-terminal workflow state has exactly one state-owner binding.

Every workflow has exactly one controller binding. The controller binding owns
routing authority but does not own a workflow state or gate.

One agent instance may serve several role bindings. Its effective permission
profile must satisfy every assigned binding and must map successfully through
every enabled target adapter.

## Init from bundle

The command:

```bash
scripts/agentic/agentic-gen.sh init --bundle orchestrated-delivery
```

materializes the active `.agentic/agentic.json` from the selected bundle.

The generated config keeps project-level settings from the existing config and derives active workflow, agents, gates, and targets from registry data.

The init step is validated for idempotency:

```bash
scripts/agentic/agentic-gen.sh validate-init-idempotency --bundle orchestrated-delivery
```

This ensures that running init repeatedly does not create drift.

## Active config

The active generated configuration is:

```text
.agentic/agentic.json
```

It contains the project-specific compiled view used by the rest of the pipeline:

```text
project metadata
generator settings
enabled targets
workflow settings
permission profiles
agents
gates
runtime context
validation policy
```

This file is validated against:

```text
.agentic/schemas/agentic.schema.json
```

Schema validation is fail-fast. `node` and `npx` must work. The validator does not fall back to weaker syntax-only validation.

## Resolution

Resolution turns the active config and registry into a generated resolution file:

```text
.agentic/generated/resolution.json
```

Resolution verifies that agents, targets, capabilities, skills, and produced artifacts can be resolved correctly.

It is generated by:

```bash
scripts/agentic/agentic-gen.sh resolve
```

and validated by:

```bash
scripts/agentic/agentic-gen.sh validate-resolution
```

## Lockfile

The deterministic lockfile is:

```text
.agentic/agentic-lock.json
```

It records input state for the generator.

The lockfile is generated by:

```bash
scripts/agentic/agentic-gen.sh lock
```

and validated by:

```bash
scripts/agentic/agentic-gen.sh validate-lockfile
```

If tracked inputs change, the lockfile must be regenerated and committed intentionally.

## Target generation

The generator currently supports:

```text
vscode-copilot
opencode
```

Target generation is handled through target adapters.

Target adapters define owned paths, for example:

```text
.github/agents
.github/skills
.github/copilot-instructions.md

.opencode/agents
.opencode/skills
AGENTS.md
opencode.json
```

Generation is run by:

```bash
scripts/agentic/agentic-gen.sh generate all
```

or as part of:

```bash
scripts/agentic/agentic-gen.sh all
```

Generated output is validated with:

```bash
scripts/agentic/agentic-gen.sh validate-generated
```

## Output manifest

The output manifest is:

```text
.agentic/generated/output-manifest.json
```

It records:

```text
active bundle metadata
target adapters
owned paths
generated files
sha256 hashes
byte sizes
summary counts
```

The manifest makes generated output auditable.

Validation fails if:

```text
a generated file is missing
a generated file hash has drifted
a generated file size has drifted
a target owns files not declared in the manifest
a declared file is outside the target owned paths
bundle metadata no longer matches the bundle registry
```

Manifest generation:

```bash
scripts/agentic/agentic-gen.sh manifest
```

Manifest validation:

```bash
scripts/agentic/agentic-gen.sh validate-manifest
```

## Capability coverage

Agents declare capabilities.

Skills provide capabilities.

Global capability coverage verifies that every declared capability has exactly one registered skill provider.

Composition validation must separately verify that each workflow-role binding selects the capabilities and skills required by that role. It must not require every setup containing an agent profile to install all capabilities recommended by that profile.

Run:

```bash
scripts/agentic/agentic-gen.sh coverage
```

Healthy output should show:

```text
Missing skill coverage:
  none

Unused skill capabilities:
  none

Duplicate skill capabilities:
  none
```

## Gates and artifacts

Workflow states can have gates.

A gate requires:

```text
owner
required capabilities
required artifacts
pass route
fail route
blocked route
blocking behavior
```

Agents produce artifacts. Artifact contracts define required output structure and accepted statuses.

This makes workflow progress evidence-based instead of implicit.

A gated state must have exactly one produced artifact, and transitions must match allowed artifact statuses.

## Negative gates

The negative gate suite intentionally breaks contracts to verify that validators fail closed.

Run:

```bash
scripts/agentic/agentic-gen.sh test-negative
```

The suite covers failures in areas such as:

```text
agent registry
skill registry
workflow registry
bundle registry
target adapters
artifact contracts
agent artifact bindings
output manifest
lockfile
idempotency
```

Negative gates are important because they prove that invalid configurations are rejected.

## Idempotency

The project validates deterministic behavior.

Generation idempotency:

```bash
scripts/agentic/agentic-gen.sh validate-idempotency
```

Init idempotency:

```bash
scripts/agentic/agentic-gen.sh validate-init-idempotency --bundle orchestrated-delivery
```

These checks prevent hidden drift in generated files and active config materialization.

## Fail-fast and no fallback

The project intentionally avoids fallback behavior.

If a required tool, dependency, file, schema, registry entry, generated output, or artifact contract is missing or broken, validation must fail with a clear error.

The system should not silently degrade.

Examples:

```text
do not skip schema validation if ajv is unavailable
do not switch to weaker syntax-only validation
do not ignore missing bundle references
do not ignore generated output drift
do not allow missing artifact contracts
```

This keeps the generator trustworthy.

## Main verification flow

The full local verification flow is:

```bash
scripts/agentic/agentic-gen.sh all
scripts/agentic/agentic-gen.sh test-negative
scripts/agentic/agentic-gen.sh doctor-strict
```

For noisy runs, redirect output to a log:

```bash
LOG="/tmp/agentic-doctor.log"
scripts/agentic/agentic-gen.sh doctor-strict > "$LOG" 2>&1
tail -80 "$LOG"
```

`doctor-strict` must pass before a change is considered done.

## Architectural summary

The architecture can be summarized as:

```text
Registry defines what exists.
Bundle selects what is active.
Init materializes active config.
Resolution proves references can be resolved.
Lockfile records deterministic input state.
Generators produce target-specific output.
Manifest records generated output and active bundle metadata.
Validators enforce contracts.
Negative gates prove invalid states fail closed.
```

The result is a reproducible, target-independent generator for agentic workflow configurations.
