# Architecture

`agentic-workflow-generator` is a platform-neutral compiler for agentic software delivery workflows.

It takes a registry-based source of truth and generates target-specific agent configuration for coding-agent environments such as VS Code Copilot and OpenCode.

The architecture is intentionally deterministic, fail-fast, and validation-heavy.

## Conceptual domain model

The conceptual model is divided into bounded contexts to avoid one abstract,
densely connected domain diagram.

The navigation overview is:

~~~text
docs/diagrams/domain/agentic-domain-overview.puml
~~~

The overview is not authoritative for attributes or cardinalities.

The detailed Chen diagrams are:

~~~text
docs/diagrams/domain/setup-selection-chen.puml
docs/diagrams/domain/workflow-control-chen.puml
docs/diagrams/domain/agent-composition-chen.puml
docs/diagrams/domain/capabilities-artifacts-targets-chen.puml
~~~

Each detailed diagram is authoritative for the full entities, relationships and
cardinalities owned by its bounded context. Cross-context entities are marked
as references and remain authoritative in the diagram that owns their complete
definition.

JSON schemas, typed domain models, registry validators, compilation and target
generation must remain consistent with these boundaries.

Rendered SVG files are maintained beside every PlantUML source. Diagram
navigation and authority rules are documented in:

~~~text
docs/diagrams/domain/README.md
~~~

The central composition chain is:

~~~text
Agent profile
  -> Agent instance
  -> Role binding
  -> Workflow state and gate
~~~

Agent profiles and skill recommendations are reusable defaults. The active bundle owns concrete agent instances, role bindings, capabilities, selected skills, instance-level permissions, artifacts, guardrails, controller authority, and separation policies.

## High-level flow

~~~text
registry/
  agents/
  artifacts/
  bundles/
  permission-profiles/
  profiles/
  setups/
  skills/
  targets/
  workflows/
        ↓
schema validation
        ↓
registry loading and typed indexing
        ↓
setup or bundle selection
        ↓
compiled composition
  agent instances
  role bindings
  workflow gates
  selected skills
  effective permissions
  artifact production
        ↓
active config
        ↓
lockfile over compiler inputs
        ↓
target-specific generation
        ↓
output manifest over generated files
        ↓
contract, integration and end-to-end validation
~~~

The registry is external compiler input. Raw registry JSON must be validated and converted into typed internal models before compiler or target logic consumes it.

The compiled composition is the canonical internal authority. Target generators must not independently reinterpret raw registry files.

There is no separate persisted resolution model. The active configuration serializes the compiled composition, the lockfile records compiler-input provenance, and the output manifest records generated-file ownership and integrity.

## Documentation consistency gate

A vertical migration slice is not complete until all affected representations
describe the same implemented model:

~~~text
source code
tests and validation gates
JSON schemas and registry contracts
docs/architecture.md
docs/core-domain-model.md
docs/diagrams/domain/README.md
docs/diagrams/domain/*.puml
docs/diagrams/domain/*.svg
project-status.md
~~~

The detailed PlantUML sources are authoritative for their respective bounded
contexts. Every affected rendered SVG must be regenerated in the same slice.

Research and analysis documents must be clearly separated from authoritative
current-state documentation. Historical proposals must not be used as
implementation requirements.

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

The registry contains reusable declarative definitions.

~~~text
registry/
  agents/
  artifacts/
  bundles/
  permission-profiles/
  profiles/
  setups/
  skills/
  targets/
  workflows/
~~~

Each registry area has one responsibility.

| Registry area | Responsibility |
|---|---|
| `agents/` | Reusable advisory agent profiles with recommended responsibilities, guardrails, capabilities and default permission |
| `artifacts/` | Artifact contracts referenced by workflow gates and produced by role bindings |
| `bundles/` | Concrete deployable composition of instances, bindings, workflow, skills, artifacts, permissions, targets and separation policies |
| `permission-profiles/` | Reusable effective permission definitions selected by concrete agent instances |
| `profiles/` | Higher-level advisory workflow and project metadata |
| `setups/` | Guided selection of bundle and enabled targets; the selected bundle owns profile, workflow and concrete runtime composition |
| `skills/` | Composable capability providers selected by role bindings |
| `targets/` | Target adapter ownership and permission-mapping contracts |
| `workflows/` | State machine, transitions, gates, start state, terminal states and fail-closed routing |

The registry is data, not application code.

Python implementation must not be placed under `registry/`. Shared compiler code belongs in the Python package under `src/`.

Schema validation checks the external representation. Semantic validation checks cross-registry invariants and composition safety.

## Bundle composition

A bundle owns the complete concrete runtime composition.

Example:

~~~text
registry/bundles/orchestrated-delivery.bundle.json
~~~

A bundle selects:

~~~text
workflow
profile
agent instances
role bindings
separation policies
skills
artifacts
targets
~~~

An agent instance selects:

~~~text
agent profile
display name
effective permission profile
shared-context policy
~~~

A role binding selects:

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

Bundle validation must enforce:

~~~text
every referenced registry entry exists
every non-terminal workflow state has exactly one state owner
every workflow has exactly one controller
the controller owns no workflow state or gate
selected skills belong to the bundle
selected skills cover binding-required capabilities
produced artifacts belong to the bundle
gate-required artifacts are produced by the state owner
agent instances have one effective permission profile
target adapters map every effective permission
separation policies reference valid bindings
required distinct instances are actually distinct
~~~

Agent profiles and profiles remain advisory. They must not become implicit fallback sources for concrete runtime values.

## Composition binding direction

The active compiler model uses concrete agent instances and explicit role bindings. Static agent profiles remain reusable advisory definitions and are not runtime authority.

This composition model allows one validated agent instance to serve several role bindings while preserving explicit capabilities, permissions, artifact ownership, responsibilities, guardrails and separation constraints.

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
uv run agentic-workflow-generator init --bundle orchestrated-delivery
```

loads a fully validated typed registry snapshot, compiles the selected bundle into one canonical `CompiledComposition`, validates its serialized boundary and materializes `.agentic/agentic.json`.

The active configuration preserves existing project metadata and contains the bundle-owned profile, workflow, targets, agent instances, role bindings, permissions, skills, artifact contracts, state ownership, controller binding, workflow gates, artifact production and separation constraints.

The `validate` command invokes `agentic_workflow_generator.cli.active_config` directly. It validates the serialized active configuration with Draft 2020-12 and structured `AWG-ACTIVE-CONFIG-*` diagnostics. The obsolete shell, Node and AJV validation boundary has been removed.

Guided initialization selects only a bundle and enabled targets. It validates the setup profile and active configuration before side effects, then writes `.agentic/setup-profile.json` and `.agentic/agentic.json` as one transactional operation. Cancellation, dry-run and validation failure write no partial files.

`uv run agentic-workflow-generator init` routes through the typed top-level command boundary to `cli.init`. CLI code owns argument parsing, terminal interaction and rendering, while application and compiler layers own all composition and write semantics.

The init step is validated for idempotency:

```bash
uv run agentic-workflow-generator validate-init-idempotency --bundle orchestrated-delivery
```

This ensures that running init repeatedly does not create drift or rewrite byte-identical outputs.

## Active config

The active generated configuration is:

~~~text
.agentic/agentic.json
~~~

It is a compiled project-specific representation, not a second registry.

The active config must preserve:

~~~text
project metadata
selected bundle identity
enabled targets
workflow identity and fail-closed policy
concrete agent instances
concrete role bindings
state ownership and controller binding
effective permissions
selected skills
materialized workflow gates
artifact contracts and production ownership
separation constraints
~~~

It must not recreate superseded authority from agent-profile recommendations.

The active config is validated against:

~~~text
.agentic/schemas/agentic.schema.json
~~~

Schema and semantic validation are fail-fast. Missing tools, files, references or unsupported runtime state must produce explicit errors without fallback.

The public `validate-references` route delegates to `cli.registry_references` and `application.registry_references`. It loads one `ValidatedRegistrySnapshot`, recompiles the active bundle through the canonical active-composition boundary and rejects any serialized composition drift. It does not maintain a separate active-config reference parser.

The public `validate-registry-schemas` route delegates to `cli.registry_schemas` and `validation.registry_schemas`. Registry paths are discovered deterministically through `RegistryLoader`, while every JSON document is read and validated individually against its Draft 2020-12 schema so document failures can be aggregated without weakening root-type validation.

## Lockfile

The deterministic lockfile is:

```text
.agentic/agentic-lock.json
```

It records canonical compiler-input provenance: the configured input patterns, each input path, SHA-256 hash, byte size, total file count and aggregate content hash.

The authoritative implementation is `application/lockfile.py`. It owns deterministic input collection, document construction, atomic generation and fail-closed validation with stable `AWG-LOCKFILE-*` diagnostics.

The lockfile is generated by:

```bash
uv run agentic-workflow-generator lock
```

and validated by:

```bash
uv run agentic-workflow-generator validate-lockfile
```

The typed top-level CLI routes `lock` and `validate-lockfile` to `cli.lockfile_generation` and `cli.lockfile_validation`; lockfile semantics remain in the application layer.

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
uv run agentic-workflow-generator generate
```

or as part of:

```bash
uv run agentic-workflow-generator all
```

Generated output is validated with:

```bash
uv run agentic-workflow-generator validate-generated
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
a required generated file is missing
generated bytes differ from the canonical typed rendering
an unmanaged file exists under a target-owned path
the committed manifest differs from the canonical materialization plan
obsolete resolution output still exists
```

Transactional target materialization:

```bash
uv run agentic-workflow-generator generate
```

Canonical target-output validation:

```bash
uv run agentic-workflow-generator validate-generated
```

## Capability coverage

Skills provide capabilities.

Role bindings declare the capabilities required by the concrete runtime composition.

Global coverage verifies:

~~~text
every runtime-required capability has a registered skill provider
no registered capability provider is unused by all supported compositions
no capability has multiple providers unless the model explicitly permits it
~~~

Profile and agent-profile recommendations are not runtime requirements and must not be used as fallback authority.

Composition validation separately verifies that each role binding selects skills that provide all capabilities required by that binding and by its workflow gate.

The authoritative global analysis is implemented by `validation/capability_coverage.py` over immutable `Bundle` and `Skill` values. `application/capability_coverage.py` loads the single `ValidatedRegistrySnapshot`, and `cli/capability_coverage.py` owns deterministic report rendering. No raw registry parser, agent-profile capability derivation or fallback authority exists in this boundary.

Run:

~~~bash
uv run agentic-workflow-generator coverage
~~~

Healthy output shows:

~~~text
Missing skill coverage:
  none

Unused skill capabilities:
  none

Duplicate skill capabilities:
  none
~~~

## Gates and artifacts

Every non-terminal workflow state owns an explicit blocking gate.

A workflow gate declares:

~~~text
name
blocking behavior
required capabilities
required artifacts
~~~

The state-owner role binding must:

~~~text
reference the same workflow state
reference the same workflow gate
require every gate capability
produce every gate artifact
~~~

Artifact contracts define:

~~~text
artifact type
path pattern
allowed statuses
required headings
producer policy
~~~

Artifact production belongs to `roleBindings[].produces`, not agent profiles.

The workflow controller owns routing authority but does not own a state, gate or produced artifact.

Workflow transitions and artifact status semantics must remain consistent. Invalid or missing evidence routes the workflow fail-closed to the configured failure state.

## Negative gates

Negative tests intentionally violate one contract at a time and verify that the owning component fails closed.

Negative tests are grouped by domain:

~~~text
agents
artifacts
bundles
permissions
profiles
setups
skills
targets
workflows
compiled composition
active config
lockfile
manifest
target generation
~~~

A component-level negative test must invoke the relevant Python validator or service directly. It must not run the complete compiler pipeline as fixture setup.

Assertions use stable diagnostic codes. Human-readable messages may also be checked when their wording is itself part of the public contract.

Only integration and end-to-end tests may invoke the complete command pipeline.

The former monolithic negative-gate runner has been removed. Fail-closed contracts are owned by focused unit, integration, contract, CLI, and end-to-end pytest suites.

## Idempotency

The project validates deterministic behavior.

Generation idempotency:

```bash
uv run agentic-workflow-generator validate-idempotency
```

Init idempotency:

```bash
uv run agentic-workflow-generator validate-init-idempotency --bundle orchestrated-delivery
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

The final verification hierarchy is:

~~~text
format and lint
type checking
unit tests
schema contract tests
semantic validator tests
negative tests
integration tests
generation idempotency
isolated consumer end-to-end tests
target runtime tests
working-tree drift check
~~~

The stable public command is:

~~~bash
uv run agentic-workflow-generator
~~~

The installed command and `python -m agentic_workflow_generator` share the same `cli.main` boundary. That boundary routes commands without duplicating domain, registry, validation or compiler logic.

A change is complete only when all relevant component tests and the complete fail-fast pipeline pass with a clean working tree.

During the breaking migration, isolated green validators do not imply that the full pipeline is green.

## Compiler code architecture

The implementation is organized as an installable Python package.

~~~text
src/
  agentic_workflow_generator/
    __main__.py

    cli/
      main.py
      init.py
      generate.py
      validate.py
      capability_coverage.py
      environment.py
      lockfile_generation.py
      lockfile_validation.py
      registry_references.py
      registry_schemas.py

    application/
      initialization.py
      generation.py
      capability_coverage.py
      environment.py
      lockfile.py
      registry_references.py
      registry_snapshot.py
      target_materialization.py
      pipeline.py

    domain/
      agents.py
      artifacts.py
      bundles.py
      diagnostics.py
      permission_profiles.py
      profiles.py
      setups.py
      skills.py
      targets.py
      workflows.py

    registry/
      loader.py
      index.py
      paths.py
      sources.py

    validation/
      schema_support.py
      registry_schemas.py
      capability_coverage.py
      common.py
      active_config.py
      agents.py
      artifacts.py
      bundles.py
      permission_profiles.py
      profiles.py
      setups.py
      setup_profiles.py
      skills.py
      targets.py
      workflows.py

    compiler/
      composition.py
      serialization.py
      manifest.py

    targets/
      base.py
      opencode.py
      vscode_copilot.py

    infrastructure/
      json_io.py
      filesystem.py
      hashing.py
      processes.py

tests/
  unit/
  contract/
  integration/
  negative/
  e2e/

~~~

This is a responsibility map, not permission to create empty placeholder modules.

A package or module is created only when an implementation is migrated into it or when it is required by the first active vertical slice.

## Dependency direction

Dependencies point inward toward stable domain concepts.

~~~text
cli
  ↓
application
  ↓
validation and compiler
  ↓
domain
~~~

The supporting boundaries are:

~~~text
registry
  loads and indexes external compiler input

infrastructure
  provides filesystem, JSON, hashing and process adapters

The environment application service owns the six required command contracts, their fail-closed validation policy and a fixed 30-second timeout for each version command. The infrastructure process adapter only resolves explicitly named executables and executes resolved commands while capturing exit code and combined output. It does not select alternatives, repair `PATH`, install tools or contain environment policy.

The installed top-level CLI routes `validate-environment` directly to `cli.environment`; command discovery and process execution remain behind the typed infrastructure boundary.

targets
  consume compiled composition
~~~

The following dependencies are forbidden:

~~~text
domain importing CLI, registry IO, targets or infrastructure
validation importing CLI or concrete target generators
targets loading raw registry files
targets implementing semantic composition rules
registry loaders invoking target generation
infrastructure containing domain decisions
tests importing implementation from deleted legacy launchers
~~~

Application services orchestrate operations but must not duplicate domain rules.

The CLI parses input, invokes an application service, renders diagnostics and returns an exit code. It contains no registry or compiler semantics.

## External registry boundary

Registry JSON is untrusted external compiler input.

The boundary follows this sequence:

~~~text
filesystem
→ JSON parsing
→ schema validation
→ typed model construction
→ registry index construction
→ semantic validation
→ compiled composition
~~~

Raw dictionaries are permitted only during parsing, schema validation and typed model construction.

After model construction, application, validation, compiler and target code use typed domain objects.

A malformed value must fail at the earliest responsible boundary. Later layers must not contain defensive fallback for values that an earlier boundary guarantees.

## Project paths

Repository paths are represented by one injected `ProjectPaths` object.

It owns canonical locations such as:

~~~text
repository root
registry root
schema root
active config
generated directory
lockfile
manifest
target output roots
~~~

Modules must not independently infer the project root through repeated `Path.cwd()` calls.

All paths derived from registry or generated data must be validated as safe repository-relative paths before filesystem access.

Absolute paths, parent traversal and paths outside owned roots are rejected.

## Registry loader and index

`RegistryLoader` owns:

~~~text
registry file discovery
deterministic ordering
JSON loading
schema selection
typed model construction
duplicate identity detection
source-path association
~~~

`RegistryIndex` owns indexed lookup by stable identity.

It provides typed access to:

~~~text
agent profiles
artifact contracts
bundles
permission profiles
profiles
setups
skills
target adapters
workflows
~~~

Validators and compiler services receive a `RegistryIndex`. They must not rediscover or reload registry files independently.

Missing references are reported explicitly. Lookup must not return implicit defaults or silently ignore unknown values.

## Domain models

Domain models describe concepts and invariants without filesystem, CLI or target behavior.

The central types include:

~~~text
AgentProfile
AgentInstance
RoleBinding
SeparationPolicy
PermissionProfile
Skill
ArtifactContract
Workflow
WorkflowState
WorkflowGate
Bundle
Profile
Setup
TargetAdapter
CompiledComposition
Diagnostic
~~~

Models use immutable value semantics where practical.

Identity-bearing collections preserve deterministic ordering but enforce uniqueness through explicit validation.

Recommended or default metadata remains distinguishable from effective runtime values.

## Validation architecture

Each validator owns one bounded set of semantic rules.

Validators receive typed models or a `RegistryIndex` and return diagnostics.

A validator must not:

~~~text
print directly
terminate the process
reload registry files
generate output
repair invalid data
derive fallback values
invoke unrelated validators through shell commands
~~~

Cross-domain rules belong in an explicitly named composition validator rather than being duplicated in several registry validators.

Common primitives may validate generic value properties, but domain-specific policy remains in its owning validator.

## Canonical compiled composition

`CompiledComposition` is the canonical internal compiler representation for one selected setup or bundle.

It contains resolved, validated runtime authority:

~~~text
selected bundle, profile and workflow
enabled targets
agent instances
role bindings
state ownership
controller binding
selected skills
required and provided capabilities
effective permission profiles
workflow gates
artifact contracts and production ownership
separation constraints
~~~

It must not contain unresolved registry references.

It must not infer runtime values from advisory agent-profile or profile metadata.

The same compiled composition is used to materialize:

~~~text
.agentic/agentic.json
lockfile inputs
target-specific output
output manifest metadata
~~~

No downstream generator may create a competing composition model.

## Target adapters

Every target implementation conforms to one target-generator interface.

The interface receives:

~~~text
compiled composition
target adapter contract
owned output root
project paths
~~~

It returns a deterministic set of generated files.

Shared target rendering belongs in target support modules. Target-specific syntax and permission mapping remain in the concrete target adapter.

A target generator must fail when required semantics cannot be represented. It must not omit unsupported responsibilities, routing, gates, artifacts or permissions silently.

## Diagnostics

Every validation or compiler failure is represented by a structured diagnostic.

A diagnostic contains at least:

~~~text
stable code
severity
human-readable message
source path when available
logical location when available
related identities when available
~~~

Example:

~~~text
AWG-BUNDLE-014
registry/bundles/example.bundle.json
roleBindings[2].produces
Artifact contract does not exist
~~~

Diagnostic codes are stable public test contracts.

Messages should remain clear, but tests must not depend exclusively on complete message text unless exact wording is deliberately part of the interface.

The CLI is responsible for deterministic diagnostic ordering and rendering.

Unexpected internal exceptions are not converted into successful or partial output.

## Error handling

Expected invalid input produces diagnostics and a non-zero exit status.

Unexpected programming errors fail visibly with their original cause preserved.

The compiler must not:

~~~text
catch broad exceptions and continue
replace missing values with empty collections
skip broken registry entries
continue after partial generation
retain stale target files after a failed transaction
downgrade a required validation
~~~

Operations that modify several files use transactional materialization where failure could otherwise leave inconsistent output.

## Test architecture

Tests are grouped by responsibility.

### Unit tests

Unit tests cover:

~~~text
domain invariants
value validation
diagnostic construction
path safety
registry indexing
composition rules
serialization
target rendering helpers
~~~

They use in-memory typed objects or minimal temporary files.

### Contract tests

Contract tests cover:

~~~text
JSON schemas
serialized active config
lockfile format
manifest format
target adapter contracts
diagnostic code uniqueness
~~~

### Integration tests

Integration tests cover bounded multi-component flows such as:

~~~text
registry loading and semantic validation
bundle to compiled composition
compiled composition to active config
compiled composition to one target output
manifest generation and validation
~~~

### Negative tests

Each negative test:

~~~text
starts from a minimal valid fixture
introduces one invalid mutation
invokes the owning component directly
asserts the expected diagnostic code
asserts that no invalid output was committed
~~~

Negative tests must not depend on alphabetical selection of an arbitrary registry file.

Fixtures that require a specific composition identify it by stable name.

### End-to-end tests

End-to-end tests cover only complete user-visible compiler workflows:

~~~text
guided setup
direct bundle init
isolated consumer generation
target runtime parsing
idempotent regeneration
fail-fast transactional rollback
~~~

The number of E2E scenarios remains intentionally small because lower layers already prove individual invariants.

## Test fixtures

Reusable fixtures are builders of valid typed objects or minimal registry trees.

Fixture builders must:

~~~text
make defaults explicit
allow focused field overrides
produce deterministic identities
avoid loading repository working-tree output
avoid hidden dependency on file ordering
avoid global mutable state
~~~

A test may copy a complete repository only when repository-level behavior is itself the subject of the test.

## Vertical migration strategy

Architecture hardening is performed through vertical slices.

Each slice contains:

~~~text
typed model support
registry loading support
semantic validator
diagnostic codes
unit tests
negative tests
CLI integration
removal of the replaced script implementation
~~~

The migration order is:

~~~text
permissions
agents
skills
artifacts
workflows
bundles
profiles
setups
targets
compiled composition
active config
targets
target generation
manifest
lockfile
end-to-end flows
~~~

A slice is not complete while both old and new implementations remain authoritative.

Temporary import wrappers may exist only as mechanical launchers to the new implementation. They must contain no compatibility projection or independent logic.

## Code size and responsibility guidelines

Code size is a review signal rather than an automatic correctness metric.

Normal expectations are:

~~~text
one clear responsibility per module
functions normally below 40 to 60 lines
modules normally below 300 to 400 lines
small explicit public interfaces
no generic utility dumping ground
no duplicated registry interpretation
~~~

A larger function or module requires a cohesive reason and focused tests.

When a module grows because it contains unrelated rules, it must be split by domain responsibility rather than by arbitrary line count.

## Quality tooling

The initial enforced Python quality baseline is:

~~~text
ruff format
ruff check
mypy
pytest
pytest with coverage reporting
~~~

`ruff` owns formatting and linting.

`mypy` checks the package and tests at a configured strictness that can be raised intentionally, but errors must not be globally ignored to obtain a green baseline.

`pytest` is the test runner for all new suites.

Coverage is used to locate untested branches. A numerical threshold must not encourage superficial tests or replace mutation and negative testing.

The typed top-level CLI has focused routing, fail-fast pipeline, verify, status and doctor contract tests.

## Review requirements

Every refactor slice is reviewed for:

~~~text
single authority
dependency direction
removed duplication
typed boundaries
deterministic behavior
fail-fast behavior
diagnostic quality
focused tests
deleted superseded implementation
documentation consistency
~~~

A large mechanical move and a semantic behavior change should be separate commits when possible.

Generated output changes are reviewed independently from source-code refactors.

## Definition of done for architecture hardening

Architecture hardening is complete when:

~~~text
the active implementation lives under src/agentic_workflow_generator
scripts/agentic has been removed completely
registry loading and indexing have one implementation
JSON IO, path safety and hashing have one implementation each
all compiler layers use typed internal models
one canonical compiled composition feeds all downstream stages
targets do not load raw registry data
validators return structured diagnostics
diagnostic codes are unique and tested
test-negative-gates.py has been removed
tests are divided by responsibility
component tests do not invoke the full pipeline
pytest, ruff and mypy are enforced
all superseded runtime structures are removed
all generated output is regenerated deterministically
all supported setups pass isolated consumer E2E
all target runtime tests pass
doctor-strict passes
the working tree is clean
project-status.md and architecture documentation match the code
~~~

New product features remain paused until this definition is satisfied.

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
