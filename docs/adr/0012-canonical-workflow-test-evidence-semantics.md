# ADR-0012: Canonical workflow test-evidence semantics

- Status: Accepted
- Date: 2026-08-12
- Accepted baseline: `development` @ `fc78232e2d0cf37a984c4e5976447907b9a19de4`

## Summary

Each workflow gate that requires TestReport will own a non-empty, typed, unordered set named requiredTestEvidence.
One obligation is a closed, named validation category—not a shell command, free-form scenario, external reference, or generic orchestration expression. The two V1 categories are:
- changed-behavior-tests
- project-validation-suite
All four current TestRunner gates declare both categories.
At runtime, the TestRunner resolves repository-authoritative commands for each declared category and records the observation in the existing TestReport evidence format. The compiler validates and preserves only the static contract; it does not discover or execute tests.

## Context

Current workflows require a TestReport but do not canonically state which validation evidence that report must establish. The test-execution skill currently instructs workers to determine commands from repository configuration, run focused tests, and run broader regression or validation suites. That prose is useful execution guidance but is not a validated compiler contract.
A raw command is too project-specific for the reusable, language-agnostic workflows. An untyped scenario name remains ambiguous. A separate validation-contract registry would introduce resolution machinery disproportionate to the two bounded V1 obligations.
The decision must therefore identify the required validation intent statically while leaving command discovery and execution at the existing runtime producer boundary.

## Decision

### 1. Required test-evidence obligation

The registry member is:

~~~json
"requiredTestEvidence": [
  "changed-behavior-tests",
  "project-validation-suite"
]
~~~
Each array member is one typed WorkflowTestEvidenceRequirement value from this closed V1 vocabulary:

| Identity | Canonical meaning |
| --- | --- |
| `changed-behavior-tests` | Execute repository-authoritative validation that directly exercises the approved changed behavior. |
| `project-validation-suite` | Execute the repository-authoritative broader regression or validation suite applicable to the project. |

These values state required evidence intent. They are not executable commands and do not encode command sequencing, environment provisioning, retries, conditional steps, matrices, or dependencies.
The vocabulary is a bounded enum/value type in the workflow domain. It is not an external reference and requires no separate registry or resolver. Any other value is malformed and invalid.

### 2. Canonical owner

The workflow gate is the sole canonical owner.
A required validation applies at one gate boundary and contributes to the TestReport required by that same gate. Gate ownership:
- keeps the declaration adjacent to requiredArtifacts;
- allows different workflow boundaries to require different validation sets;
- avoids workflow-wide ambiguity if a later accepted workflow has multiple test-evidence gates;
- avoids coupling reusable TestReport to one workflow’s validation set;
- avoids duplicating the requirement in role bindings, bundles, skills, or targets.
No other construct may carry a competing required-test-evidence declaration.

### 3. Applicability

A test-evidence gate is a gate whose requiredArtifacts includes TestReport.
Rules:
1. Every test-evidence gate must declare a non-empty requiredTestEvidence.
2. All four current TestRunner gates are test-evidence gates and must declare both V1 categories.
3. A gate that does not require TestReport must not declare requiredTestEvidence in V1.
4. A workflow with no gate requiring TestReport is valid without such a declaration.
5. No workflow state is added or renamed.
6. Optional runtime validation is not declared in this member. The member contains required obligations only.
Using the required artifact rather than a state-name convention keeps applicability attached to the canonical evidence contract.

### 4. Static versus runtime responsibility

#### Compiler responsibility

The compiler validates statically that:
- the member is present and non-empty on every test-evidence gate;
- it is absent from other gates;
- every value belongs to the closed vocabulary;
- no canonical identity is duplicated;
- the collection is canonicalized deterministically;
- the gate requires TestReport;
- the producing state-owner still satisfies existing gate capability and artifact rules;
- CompiledComposition, active configuration, and every enabled target preserve the complete set.
Malformed, duplicate, unsupported, omitted, or semantically misplaced declarations fail closed.

#### Runtime producer responsibility

The TestRunner:
- identifies repository-authoritative command or procedure mappings for each required category;
- executes those validations against the declared source/revision;
- records material environment and prerequisite conditions;
- records passing, failing, skipped, unavailable, and missing results honestly;
- classifies the TestReport under the existing artifact-specific contract.
If no authoritative command or procedure can be established for a required category, that required validation cannot be established and prevents PASS.

#### TestReport responsibility

For every required category, TestReport contains an independently reproducible evidence record:
- claim: the exact canonical category identity;
- source: the tested code/configuration/revision and the repository source that establishes the authoritative validation;
- reproduction: the exact command or deterministic procedure plus material execution conditions;
- result: the observed pass, nonconformance, skip, unavailability, or other status-relevant outcome.
The existing ## Test Commands, ## Test Results, ## Failures, and ## Coverage Notes remain domain-specific report sections. They do not replace or redefine the canonical evidence records.

#### Explicit non-responsibilities

The compiler does not:
- search project files to discover tests;
- infer commands from pyproject.toml, package scripts, CI, README text, or another repository file;
- execute commands;
- inspect arbitrary produced Markdown;
- decide whether runtime observations are truthful;
- invent observations when evidence is missing.
Targets must not infer additional required categories from skill or project prose.

### 5. Relationship to TestReport

requiredTestEvidence identifies the status-determining validation claims that the existing TestReport must cover.
It does not introduce a second evidence format, report type, evidence status, or aggregation model. ADR-0005, ADR-0006, and ADR-0007 remain authoritative:
- evidence records provide observations;
- TestReport status semantics classify those observations;
- the producing TestRunner chooses the matching status;
- the workflow controller only routes the resulting PASS, FAIL, or BLOCKED according to ADR-0011.

### 6. Status consequences

1. All required validations execute and pass: PASS, provided every required category has complete reproducible evidence and no required nonconformance exists.
2. Required validation demonstrates product nonconformance: FAIL.
3. Required validation is skipped: BLOCKED, unless another valid record independently demonstrates required nonconformance.
4. Required validation has no produced evidence: BLOCKED, absent independently demonstrated nonconformance.
5. Required environment, tool, dependency, credential, fixture, or input is unavailable: BLOCKED, absent independently demonstrated nonconformance.
6. One required validation fails and another is blocked: FAIL under FAIL_ON_DEMONSTRATED_NONCONFORMANCE.
7. Optional validation is skipped or unavailable: it does not independently prevent PASS.
8. Optional validation fails: it does not independently force FAIL merely because it was run. If its reproducible result nevertheless demonstrates violation of an applicable required product contract, ADR-0006’s demonstrated-nonconformance rule applies and the result is FAIL.
None of these rules changes routing. The controller consumes the already-classified result and follows ADR-0011.

### 7. Identity and determinism

The canonical identity of an obligation is its closed category value.
Rules:
- exact duplicate identities are invalid;
- declaration order has no semantic meaning;
- canonical typed and serialized order is lexical by category identity;
- source-order changes produce no active-configuration or generated-target difference;
- aliases, case folding, inferred equivalence, and target-specific names are not allowed.

### 8. Canonical compilation

The minimum path is:

~~~text
validated WorkflowGate.required_test_evidence
    ↓
CompiledWorkflowGate.required_test_evidence
    ↓
.agentic/agentic.json workflowGates[].requiredTestEvidence
~~~

The typed model contains:

~~~text
WorkflowTestEvidenceRequirement
    CHANGED_BEHAVIOR_TESTS = "changed-behavior-tests"
    PROJECT_VALIDATION_SUITE = "project-validation-suite"

WorkflowGate
    required_test_evidence:
        tuple[WorkflowTestEvidenceRequirement, ...]

CompiledWorkflowGate
    required_test_evidence:
        tuple[WorkflowTestEvidenceRequirement, ...]
~~~

The compiled member remains part of the existing CompiledWorkflowGate within the sole CompiledComposition. No second validation graph, resolution table, or composition authority is introduced.

### 9. Target preservation

OpenCode and VS Code Copilot must preserve, from the typed compiled gate:
- gate identity;
- owner state, role binding, and agent instance;
- the complete required category set;
- canonical category identities and meanings;
- the fact that every category is required;
- the mapping from each category identity to one or more TestReport evidence records;
- the existing TestReport status consequences;
- the distinction between static declaration and runtime command resolution;
- the instruction that required observations must not be invented;
- the state-owner/controller boundary from ADR-0011.
Both targets may express these semantics using their supported instruction format, but the renderer must derive them directly from CompiledWorkflowGate. It must not search or interpret skill prose to decide which categories are required.
Target-preservation validation must fail generation if an enabled target omits, changes, weakens, or cannot faithfully represent any required category.

### 10. Version consequences

Only contracts whose source semantics change advance:
- all four current workflow definitions: 0.3.0 → 0.4.0;
- active-config schema version: 0.10.0 → 0.11.0.
The workflow registry schema changes to require and constrain the new gate member but currently has no independent schema-version field to advance.
No version change is required solely for this decision for:
- TestReport artifact contract (0.7.0), because its evidence shape and status semantics do not change;
- bundles, because the declaration is workflow-owned and bundle source semantics do not change;
- generator (0.1.0);
- target adapters, because their registered output ownership and permission mappings do not change;
- output-manifest or lockfile formats.
Generated active configuration, lockfile, target files, and output manifest must be regenerated normally because their content and hashes change.

### 11. Current workflow declarations

Each of these gates declares both canonical categories:
- lean-delivery → TestRunner / test-review
- orchestrated-delivery → TestRunner / test-review
- review-heavy-delivery → TestRunner / test-review
- ai-application-delivery → TestRunner / test-review
No other current gate declares them.

### 12. Acceptance scenarios

| # | Scenario | Expected semantic result |
| ---: | --- | --- |
| 1 | Valid complete TestRunner declaration | Valid when the TestReport gate declares a non-empty, unique typed set; current gates declare both categories. |
| 2 | Required declaration missing | Invalid static workflow; compilation does not proceed. |
| 3 | Duplicate canonical identity | Invalid regardless of source order. |
| 4 | Invalid or unresolved identity | Unknown value is invalid. Values are closed enum members, not external references, so no external resolution fallback exists. |
| 5 | All required validations pass | TestReport: PASS with complete reproducible evidence for every declared identity. |
| 6 | One required validation demonstrates nonconformance | TestReport: FAIL. |
| 7 | One required validation is skipped | TestReport: BLOCKED, absent independent demonstrated failure. |
| 8 | One required validation has no evidence | TestReport: BLOCKED, absent independent demonstrated failure. |
| 9 | Required validation cannot execute due to unavailable prerequisite | TestReport: BLOCKED, absent independent demonstrated failure. |
| 10 | Demonstrated failure plus another blocked validation | TestReport: FAIL. |
| 11 | Optional validation fails or is skipped | No independent status consequence unless valid evidence demonstrates an applicable required nonconformance. |
| 12 | Declaration order changes | No semantic or generated-output change; lexical serialization is canonical. |
| 13 | Active configuration preservation | workflowGates[].requiredTestEvidence contains the complete lexically ordered set; omission or drift fails validation. |
| 14 | Equivalent preservation by both targets | Both render the same required identities, meanings, evidence mapping, and status implications from compiled data. |
| 15 | Target cannot represent the semantic | Generation fails explicitly; no degraded output is materialized. |
| 16 | Non-TestRunner gate or workflow | A gate not requiring TestReport must not declare the member; a workflow without such a gate remains valid. |
| 17 | AI-evaluation evidence encountered | It does not satisfy or replace required TestReport categories and does not alter their classification. |
| 18 | Malformed or missing runtime evidence | The compiler neither executes validation nor invents observations. At runtime it forbids PASS; absent demonstrated failure, the TestReport is BLOCKED. |

### 13. Explicit boundary

This decision excludes:
- AI-evaluation execution semantics;
- consumer release-readiness evidence;
- autonomous workflow execution;
- runtime workflow-state persistence;
- invocation history;
- retry and escalation;
- artifact invalidation;
- generic policy engines;
- generic test-orchestration DSLs;
- project-wide command-discovery contracts;
- new target platforms.

## Alternatives considered

### Workflow-level declaration

Rejected. A workflow-wide list cannot identify which gate produces the evidence and becomes ambiguous if a later accepted workflow contains multiple test-evidence boundaries. The existing gate is the narrower owner.

### Gate-level executable commands

Rejected. Commands are precise but project-specific. Current workflows and profiles are reusable and language-agnostic. Embedding commands such as uv run pytest -q, npm test, or another repository command would couple reusable workflow semantics to one consumer toolchain.
Commands remain runtime reproduction evidence.

### Gate-level free-form named scenarios

Rejected. Arbitrary strings or prose descriptions do not fail closed on spelling, identity, equivalence, or target preservation.
The selected categories use a closed typed vocabulary.

### Validation category resolved through a new registry

Rejected. A validation-contract registry, resolver, and compiled reference graph would add a second bounded construct for only two current obligations. No accepted need requires reusable external validation definitions or command orchestration.

### Artifact-contract declaration

Rejected. TestReport is reusable across workflows and owns report shape, evidence format, and status classification. It does not own which validation set a particular workflow boundary requires. Moving the set there would make every TestReport use identical workflow obligations and blur artifact and composition authority.

### Role-binding or bundle declaration

Rejected. Role bindings own concrete producer responsibility, capabilities, skills, inputs, and outputs, but the required evidence is a condition of passing a workflow gate. Declaring it in both the binding and gate would duplicate authority; declaring it only in the binding would separate a gate requirement from its quality boundary.

### Reference only to the existing TestReport contract

Rejected. Gates already require TestReport. That reference specifies evidence shape and status meaning but does not identify which validation claims must be established.

### Infer requirements from capabilities

Rejected. test.run, test.report, and test.diagnose-failure describe producer capability, not the set of required validation observations.

### Infer requirements from skill or repository prose

Rejected. Free-form instructions are not canonical composition authority and may differ across targets. They cannot support deterministic fail-closed validation.

### Generic test-orchestration DSL

Rejected. Commands, dependencies, setup steps, matrices, conditions, retries, and environment provisioning would turn the compiler contract into a test runtime design. The bounded V1 gap needs only two named required evidence categories.

## Consequences

### Positive

- Every existing TestRunner boundary gains an explicit, machine-readable required evidence set.
- The declaration has exactly one owner.
- Reusable workflows remain independent of consumer command syntax.
- TestReport evidence and status authorities remain unchanged.
- Missing, skipped, blocked, and failing required validation have deterministic outcomes.
- CompiledComposition, active configuration, and both targets preserve one canonical semantic.
- Source-order changes cannot alter output.
- Unsupported target semantics fail explicitly.
- No runtime, policy engine, resolver registry, or second compiled graph is introduced.

### Costs and limitations

- Runtime TestRunners must still determine project-authoritative commands.
- Static compilation cannot prove that a consumer repository actually supplies an executable mapping.
- The closed category vocabulary requires an explicit workflow-contract change if a future accepted validation category is added.
- Renderer and target-preservation tests must guard against silent omission.
- Workflow and active-config versions must advance.

## Bounded later implementation surface

Implementation is limited to:
1. workflow registry schema;
2. typed workflow requirement vocabulary and WorkflowGate;
3. workflow parser and semantic validation;
4. bundle workflow-gate projection validation;
5. CompiledWorkflowGate and existing composition compilation;
6. active-config schema and serialization;
7. the four current workflow definitions;
8. OpenCode and VS Code Copilot rendering plus preservation validation;
9. focused domain, schema, validation, composition, serialization, determinism, and target-rendering tests;
10. current domain/status documentation;
11. normal regeneration of .agentic/agentic.json, generated target output, lockfile, and output manifest.
It excludes artifact-contract, bundle, skill, capability, permission-profile, routing, and product-runtime changes.

## Separate unresolved repository semantic

The existing ai-application-delivery workflow still lacks canonical AI-evaluation execution semantics. That concern requires its own decision and must not reuse or extend this test-evidence vocabulary implicitly.
No unresolved test-evidence prerequisite prevents implementation of this decision. A future requirement for compile-time project command declarations or additional validation categories would require a separate reviewed workflow-contract decision.
