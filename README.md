# agentic-workflow-generator

[![Agentic CI](https://github.com/jfriisj/agentic-workflow-generator/actions/workflows/agentic-ci.yml/badge.svg?branch=development)](https://github.com/jfriisj/agentic-workflow-generator/actions/workflows/agentic-ci.yml)

A deterministic, fail-fast compiler for agentic software-delivery
configurations.

The project validates a declarative registry, compiles one canonical
`CompiledComposition`, persists the active composition, and generates
target-specific coding-agent configuration.

```text
validated registry
      -> setup or bundle
      -> agent instances + role bindings
      -> CompiledComposition
      -> .agentic/agentic.json
      -> compiler-input lockfile
      -> target output
      -> output manifest
      -> validation
```

## Current model

The accepted implementation uses:

- bundle-owned concrete agent instances;
- explicit role bindings for state ownership and workflow control;
- exactly one state owner per non-terminal workflow state;
- exactly one controller per workflow;
- instance-level effective permissions;
- binding-level capabilities, skills, artifacts, responsibilities and guardrails;
- one canonical `CompiledComposition`;
- fail-fast schema, semantic, generated-output and provenance validation.

Agent profiles and project profiles are advisory. They are not runtime fallback
authority.

Supported targets:

```text
vscode-copilot
opencode
```

## Quickstart

Guided initialization:

```bash
uv run agentic-workflow-generator init --guided
```

Explicit guided setup for automation:

```bash
uv run agentic-workflow-generator init   --guided   --setup orchestrated-delivery-greenfield
```

Direct bundle initialization:

```bash
uv run agentic-workflow-generator init --bundle orchestrated-delivery
```

Run the full generator pipeline:

```bash
uv run agentic-workflow-generator all
```

Verify committed repository state:

```bash
uv run agentic-workflow-generator doctor-strict
```

## Canonical generated state

Active composition:

```text
.agentic/agentic.json
```

Compiler-input provenance:

```text
.agentic/agentic-lock.json
```

Generated-output ownership and integrity:

```text
.agentic/generated/output-manifest.json
```

Generated output is deterministic and fail-closed. Target adapters consume the
canonical compiled composition and must not reinterpret raw registry input.

## Architecture and domain model

The current-state architecture narrative is [`docs/architecture.md`](docs/architecture.md).
The sole semantic architecture model is
[`docs/architecture/workspace.dsl`](docs/architecture/workspace.dsl), while detailed
platform-neutral domain semantics are owned by
[`docs/core-domain-model.md`](docs/core-domain-model.md).

Stakeholder-facing architecture views are reproducible derived output:

- [`system-context.svg`](docs/architecture/diagrams/system-context.svg)
- [`compiler-responsibilities.svg`](docs/architecture/diagrams/compiler-responsibilities.svg)

PlantUML and committed SVG files are not semantic architecture authority. Validate
the canonical model with:

```bash
uv run architecture-model check
```

If the pinned local architecture toolchain has not been prepared, run
`uv run architecture-model prepare` explicitly before the check.

## Project authority

| Concern | Document |
| --- | --- |
| Accepted scope | [`docs/scope.md`](docs/scope.md) |
| Current state and priority | [`docs/project-status.md`](docs/project-status.md) |
| Governance | [`docs/governance.md`](docs/governance.md) |
| Operational workflow and commands | [`docs/workflow.md`](docs/workflow.md) |
| Architecture narrative | [`docs/architecture.md`](docs/architecture.md) |
| Semantic architecture model | [`docs/architecture/workspace.dsl`](docs/architecture/workspace.dsl) |
| Core domain | [`docs/core-domain-model.md`](docs/core-domain-model.md) |
| Technology baseline | [`docs/tech-stack.md`](docs/tech-stack.md) |
| Architecture decisions | [`docs/adr/`](docs/adr/) |

Repository state is authoritative. Historical proposals remain available through
Git history rather than parallel current-state documents.

## Development

Normal work starts from `development`, uses a purpose-oriented topic branch,
passes local validation, and is reviewed through a pull request targeting
`development`.

The complete operational sequence and exact commands are in
[`docs/workflow.md`](docs/workflow.md).
