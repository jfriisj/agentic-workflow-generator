# agentic-workflow-generator

[![Agentic CI](https://github.com/jfriisj/agentic-workflow-generator/actions/workflows/agentic-ci.yml/badge.svg?branch=main)](https://github.com/jfriisj/agentic-workflow-generator/actions/workflows/agentic-ci.yml)

A platform-neutral generator for agentic software delivery workflows.

The project turns a declarative registry of agents, skills, workflows, bundles, artifacts, gates, and target adapters into generated configuration for coding-agent environments such as VS Code Copilot and OpenCode.

## Why this exists

Coding-agent setups often become hand-written, duplicated, and hard to validate.

This project treats agent workflows like a compiler problem:

```text
registry source of truth
        ↓
bundle selection
        ↓
.agentic/agentic.json
        ↓
resolution + lockfile
        ↓
target-specific generated output
        ↓
validation gates
```

The goal is to make agentic workflows reproducible, deterministic, and fail-fast.

## Core concepts

| Concept | Purpose |
|---|---|
| Agent | Defines a responsibility, capabilities, permissions, and produced artifacts |
| Skill | Provides one or more capabilities used by agents |
| Workflow | Defines states, transitions, gates, terminal states, and fail-closed routing |
| Bundle | Selects a complete deployable composition of workflow, agents, skills, artifacts, profile, and targets |
| Setup | Defines guided questions, classifications, recommendations, and the default bundle |
| Setup profile | Records the selected guided answers and materialized recommendation |
| Artifact | Defines required output contracts for gates and generated evidence |
| Target adapter | Defines where generated output belongs for a target platform |
| Lockfile | Records deterministic input state |
| Output manifest | Records generated files and active bundle metadata |

## Current supported targets

```text
vscode-copilot
opencode
```

Generated output includes target-specific agents, skills, instructions, and configuration files.

## Quickstart

For a new project, start the interactive guided initializer:

```bash
scripts/agentic/agentic-gen.sh init --guided
```

The initializer:

```text
validates the setup registry
asks registry-defined questions
shows recommended, compatible, and blocked options
shows the final setup plan
requires explicit confirmation
writes .agentic/setup-profile.json and .agentic/agentic.json
```

For deterministic automation or CI, select the registered setup explicitly:

```bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup orchestrated-delivery-greenfield
```

Initialize directly from a registered bundle when guided project shaping is not needed:

```bash
scripts/agentic/agentic-gen.sh init --bundle orchestrated-delivery
```

See [Guided initialization](docs/guided-init.md) for classifications, overrides, generated files, failure behavior, and automation examples. Use [Adding guided setups](docs/adding-guided-setups.md) when implementing new process-oriented or domain-oriented compositions.

Run the full generator pipeline:

```bash
scripts/agentic/agentic-gen.sh all
```

Run strict verification:

```bash
scripts/agentic/agentic-gen.sh doctor-strict
```

A clean result should end with:

```text
PASS: Isolated consumer fixture initialized from a clean state.
PASS: All 364 negative gate tests passed.
PASS: Working tree is clean.
```

## Main commands

```bash
scripts/agentic/agentic-gen.sh validate
scripts/agentic/agentic-gen.sh validate-bundles
scripts/agentic/agentic-gen.sh validate-registry-schemas
scripts/agentic/agentic-gen.sh coverage
scripts/agentic/agentic-gen.sh resolve
scripts/agentic/agentic-gen.sh lock
scripts/agentic/agentic-gen.sh manifest
scripts/agentic/agentic-gen.sh generate all
scripts/agentic/agentic-gen.sh validate-generated
scripts/agentic/agentic-gen.sh validate-idempotency
scripts/agentic/agentic-gen.sh init --guided
scripts/agentic/agentic-gen.sh init --guided --setup orchestrated-delivery-greenfield
scripts/agentic/agentic-gen.sh init --guided --setup orchestrated-delivery-greenfield --dry-run
scripts/agentic/agentic-gen.sh init --guided --setup orchestrated-delivery-greenfield --answer target-platforms=opencode-only
scripts/agentic/agentic-gen.sh validate-init-idempotency --bundle orchestrated-delivery
scripts/agentic/agentic-gen.sh validate-init-idempotency --guided --setup orchestrated-delivery-greenfield
scripts/agentic/agentic-gen.sh test-isolated-e2e
scripts/agentic/agentic-gen.sh test-negative
scripts/agentic/agentic-gen.sh doctor-strict
```

## Guided setup flow

Four greenfield setups are currently registered:

| Setup | Delivery model |
|---|---|
| `ai-application-greenfield` | AI application delivery with explicit quality, safety, failure-mode, and operational evaluation |
| `lean-delivery-greenfield` | Compact fail-closed delivery for focused lower-risk changes |
| `orchestrated-delivery-greenfield` | Architecture, implementation, tests, code review, and final QA |
| `review-heavy-delivery-greenfield` | Architecture and independent code review before formal tests and final QA |

Each setup selects its own validated bundle, profile, workflow, agents, skills,
artifacts, and targets. Domain-oriented setups provide safer guided defaults
without removing direct initialization of registered generic bundles.

Every answer option is classified as:

- `recommended`
- `compatible`
- `blocked`

Recommended and compatible options must accurately represent the materialized
composition. Blocked options fail explicitly and are never replaced through
fallback behavior.

The complete implementation contract for additional setups is documented in
[Adding guided setups](docs/adding-guided-setups.md).

The resulting setup profile is written to:

```text
.agentic/setup-profile.json
```

It records the setup reference, selected answers, classifications, reasons, selected bundle, profile, workflow, agents, skills, artifacts, targets, and fail-fast policy.

The active configuration is written to:

```text
.agentic/agentic.json
```

Interactive `--guided` requires an attached terminal. Non-interactive automation must use an explicit `--setup`.

Add `--dry-run` to materialize, validate, and print the complete guided setup plan without writing or rewriting either Agentic configuration file.

See [Guided initialization](docs/guided-init.md) for the complete contract.

## Bundle flow

The default bundle is:

```text
registry/bundles/orchestrated-delivery.bundle.json
```

It selects:

```text
workflow: orchestrated-delivery
profile: microservice-platform
agents: Architect, CodeReviewer, Implementer, Orchestrator, QA, Requirements, TestRunner
targets: opencode, vscode-copilot
```

The bundle is validated as a complete composition:

```text
workflow states must be covered by bundle agents
workflow transitions must stay inside the selected workflow
agent capabilities must be covered by bundle skills
agent produced artifacts must be included in bundle artifacts
bundle targets must resolve to matching target adapters
profile workflow must match bundle workflow
```

## Generated output manifest

The generated output manifest is written to:

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

Validation fails if generated files drift, target ownership is wrong, or manifest bundle metadata no longer matches the bundle registry.

## Fail-fast policy

This project intentionally avoids fallback behavior.

If a required tool, dependency, registry file, schema, artifact contract, generated file, or environment condition is missing or broken, validation must fail with a clear error message.

Examples:

```text
node/npx must work for JSON Schema validation
bundle references must resolve
generated files must match the manifest
lockfile state must be deterministic
agents must not claim capabilities without skills
gates must not pass without required artifacts
```

No silent degradation. No skipped validation. No fallback paths.

## Development workflow

Recommended local flow:

```bash
scripts/agentic/agentic-gen.sh all
scripts/agentic/agentic-gen.sh test-isolated-e2e
scripts/agentic/agentic-gen.sh test-negative
scripts/agentic/agentic-gen.sh doctor-strict
```

Use log redirection for noisy checks:

```bash
LOG="/tmp/agentic-doctor.log"
scripts/agentic/agentic-gen.sh doctor-strict > "$LOG" 2>&1
tail -80 "$LOG"
```

Commit only when:

```text
doctor-strict passes
negative gates pass
working tree contains only intentional changes
```

## Repository structure

```text
.agentic/
  agentic.json
  agentic-lock.json
  generated/
  schemas/

registry/
  agents/
  artifacts/
  bundles/
  profiles/
  setups/
  skills/
  targets/
  workflows/

scripts/agentic/
  agentic-gen.sh
  validate-*.py
  generate-*.py
  test-isolated-e2e.py
  test-negative-gates.py

docs/
  core-domain-model.md
  developer-workflow.md
  engineering-discovery.md
  guided-init.md
  target-platform-analysis.md
```

## Current quality gates

The project validates:

```text
agent registry
skill registry
workflow registry
profile registry
bundle registry
setup registry
setup profile
target adapters
artifact contracts
agent artifact bindings
registry schemas
registry references
capability coverage
resolution output
lockfile structure
generated output
generation idempotency
init idempotency
isolated clean-consumer end-to-end generation
negative gates
```

The isolated end-to-end test copies only the compiler source payload into a clean temporary consumer project, runs guided init and the complete generation pipeline, validates both targets, and proves repeated execution is byte-identical without modifying the source repository.

The negative gate suite intentionally breaks contracts to prove the validators fail closed.
