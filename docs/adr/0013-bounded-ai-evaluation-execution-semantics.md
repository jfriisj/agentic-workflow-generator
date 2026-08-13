# ADR-0013: Bounded AI-evaluation execution semantics

- Status: Accepted
- Date: 2026-08-13
- Accepted baseline: `development` @ `a4150fdd18dd4e36153cce7a006b707d11870a0f`
- Decision issue: #56
- Goal: #44

## Summary

The existing V1 AI-evaluation flow is an evidence-review boundary, not an
evaluation-execution runtime.

The current `AIEvaluator / ai-evaluation-review` gate already owns the static
required evaluation dimensions through its existing gate-level
`requiredCapabilities`:

- `ai.evaluate-quality`
- `ai.evaluate-safety`
- `ai.evaluate-operational-risks`

No second AI-evaluation category declaration is introduced.

The current `ai-evaluation` state-owner binding supplies the concrete owner,
governed inputs, selected skill, responsibilities, guardrails and
`AIEvaluationReport` production. `Requirements` supplies the governed
project-specific acceptance context. `ImplementationReport` supplies the
implemented-system context. `AIEvaluationReport` remains the sole evidence and
PASS/FAIL/BLOCKED status authority.

At runtime the AIEvaluator reviews available reproducible evidence against the
required gate capabilities and applicable acceptance criteria. It may use
read-only access to governed inputs and referenced evidence, but the accepted V1
contract does not grant shell-based evaluation execution, repository mutation,
external model/evaluation-job invocation, or compiler-side discovery/execution.

If a required criterion cannot be evaluated because required evidence, data,
scenario, baseline, threshold, environment or another prerequisite is missing or
unverifiable, the result is `BLOCKED` unless independently reproducible evidence
already demonstrates required nonconformance, in which case the existing
`FAIL_ON_DEMONSTRATED_NONCONFORMANCE` rule produces `FAIL`.

Both current targets must preserve this complete semantic from canonical
compiled data and compiled artifact/permission contracts. Skill prose may
support execution guidance but is not a competing source of required
AI-evaluation obligations.

## Context

The current repository already contains an explicit AI-evaluation flow.

`ai-application-delivery` contains an `AIEvaluator` state whose
`ai-evaluation-review` gate is blocking, requires `AIEvaluationReport`, and
requires the three AI-evaluation capabilities listed above. Routing is already
total and canonical under ADR-0011:

- `PASS` routes to `TestRunner`;
- `FAIL` routes to `Implementer`;
- `BLOCKED` routes to the workflow `defaultFailureState`.

The `ai-application` bundle binds the state to the concrete `ai-evaluation`
role. That binding:

- consumes `Requirements`;
- consumes `ImplementationReport`;
- requires the same three AI-evaluation capabilities;
- selects the `ai-evaluation` skill;
- produces `AIEvaluationReport`;
- owns explicit responsibilities and guardrails;
- is distinct from the workflow controller.

`AIEvaluationReport` already defines:

- reproducible evidence fields `claim`, `source`, `reproduction`, and `result`;
- required report sections for evaluation scope, data/scenarios,
  metrics/thresholds/baselines, results, safety/failure analysis, operational
  evidence, limitations and fixes;
- `PASS`, `FAIL`, and `BLOCKED` status semantics;
- `FAIL_ON_DEMONSTRATED_NONCONFORMANCE`;
- fail-closed status invariants.

`Requirements` already requires testable acceptance criteria and records scope,
assumptions and constraints. Its `BLOCKED` semantics already cover a missing
acceptance threshold necessary to complete the requirements contract.

The unresolved gap is therefore not the existence of an evaluator, report,
status model, routing model or high-level evaluation dimensions. The gap is the
execution boundary: which existing canonical sources determine required
evaluation work, what is static compiler truth, what the AIEvaluator may resolve
or observe at runtime, and what both targets must preserve.

The current permission contract is material to that boundary. The concrete
`ai-evaluation-worker` uses the accepted `read-only` permission profile:

~~~text
read  = true
write = false
edit  = false
bash  = deny
~~~

By contrast, the separate TestRunner uses the `test-runner` permission profile
with restricted shell execution. The AI-evaluation decision must not silently
convert the AIEvaluator into a second test/evaluation executor or broaden
permission semantics owned elsewhere.

## Decision

### 1. No new AI-evaluation obligation declaration

V1 does not introduce a new member such as:

~~~text
requiredAIEvaluationEvidence
requiredAIEvaluationCriteria
requiredAIEvaluationScenarios
~~~

and does not add a new evaluation registry, policy DSL or resolver.

For the existing AI-evaluation gate, the gate's current
`requiredCapabilities` are the canonical static required evaluation dimensions.

The current V1 set is:

| Gate capability | Required evaluation dimension |
| --- | --- |
| `ai.evaluate-quality` | Evaluate required quality criteria within the governed scope. |
| `ai.evaluate-safety` | Evaluate required safety, misuse and failure-mode criteria within the governed scope. |
| `ai.evaluate-operational-risks` | Evaluate required operational criteria such as latency, cost, throughput or resource behavior when applicable to acceptance. |

These are gate requirements already present in the workflow model. A second
parallel list would duplicate authority and create drift risk.

This interpretation is bounded to the existing AI-evaluation flow and does not
change the general meaning of capabilities into a generic evidence language.
Capabilities remain stable platform-neutral identities connecting gate
requirements, role bindings and selected skills.

### 2. Canonical ownership map

Each concern has exactly one canonical owner.

#### Workflow gate

The workflow gate owns:

- that AI evaluation is a blocking workflow boundary;
- the gate identity;
- the required AI-evaluation capabilities;
- the required `AIEvaluationReport`;
- the workflow state to which the gate belongs.

It does not own project-specific thresholds, datasets, commands, observations or
status policy.

#### Role binding

The `ai-evaluation` role binding owns:

- the concrete state owner;
- governed input-artifact references;
- the concrete required capabilities;
- selected skill;
- responsibilities;
- guardrails;
- produced `AIEvaluationReport`.

The role binding must continue to satisfy the gate's required capabilities and
artifact-production relationship under existing composition validation.

#### Requirements

`Requirements` is the governed source for project-specific scope, requirements,
acceptance criteria, assumptions and constraints.

The compiler preserves the resolved `Requirements` producer relation. It does
not parse produced Requirements Markdown to discover evaluation criteria,
thresholds or datasets.

At runtime the AIEvaluator uses the governed Requirements artifact to determine
which concrete criteria within each required evaluation dimension apply to the
current project.

#### ImplementationReport

`ImplementationReport` is the governed implementation-context input for the
AIEvaluator.

It identifies the delivered implementation context that the available
evaluation evidence must correspond to. This ADR does not add a new revision
resolver or runtime state model.

#### AIEvaluationReport

`AIEvaluationReport` remains the sole authority for:

- evaluation evidence shape;
- required report sections;
- evidence completeness;
- PASS/FAIL/BLOCKED classification;
- status invariants;
- mixed-condition behavior.

No second evidence record, AI-evaluation status or gate-specific status
classifier is introduced.

#### Permission profile

The effective permission profile remains the sole authority for what the
concrete agent instance may do in a target.

This ADR does not use workflow or skill prose to override `read-only`.

#### Skill

The `ai-evaluation` skill is execution guidance for the selected role. It is not
canonical composition authority for deciding which evaluation dimensions are
required.

Targets must not infer additional required obligations from skill prose.

### 3. Static compiler responsibility

The compiler remains a deterministic compiler.

For the existing AI-evaluation flow it validates and preserves the existing
canonical relationships:

~~~text
AIEvaluator workflow state
    -> ai-evaluation-review gate
        -> requiredCapabilities
        -> required AIEvaluationReport
    -> ai-evaluation state-owner binding
        -> governed Requirements input
        -> governed ImplementationReport input
        -> selected ai-evaluation skill
        -> produced AIEvaluationReport
        -> effective read-only permission profile
    -> CompiledComposition
    -> .agentic/agentic.json
    -> enabled targets
~~~

The compiler does not:

- inspect produced Requirements or ImplementationReport Markdown to discover
  evaluation criteria;
- inspect arbitrary project files to invent evaluation scope;
- discover datasets, scenarios, metrics, thresholds or baselines;
- execute evaluation commands;
- run models or model-under-test requests;
- provision evaluation environments;
- generate measurements;
- decide whether runtime observations are truthful;
- infer required evaluation dimensions from skill prose.

No second compiled AI-evaluation graph is introduced.

### 4. Runtime AIEvaluator responsibility

The AIEvaluator is an evidence reviewer under the current V1 permission
boundary.

It must:

1. read the governed `Requirements` and `ImplementationReport`;
2. identify the applicable concrete acceptance criteria within every
   gate-required AI-evaluation capability dimension;
3. review available reproducible evidence for those criteria;
4. verify evaluation scope and applicable datasets/scenarios;
5. verify measurable metrics, thresholds and baselines where required;
6. review safety and failure-mode evidence where applicable;
7. review operational evidence where applicable;
8. document unavailable, missing or unverifiable prerequisites honestly;
9. produce one `AIEvaluationReport` classified under the existing artifact
   contract;
10. return the already-classified canonical result to the workflow controller.

The AIEvaluator may use read-only target operations and may inspect
read-accessible evidence referenced by governed inputs.

The accepted V1 contract does not require or authorize the AIEvaluator to:

- run shell commands;
- mutate repository state;
- create or alter product/model behavior;
- execute an external evaluation job;
- invoke a model-under-test merely to generate missing evidence;
- silently substitute subjective judgment for required reproducible evidence.

A recorded command or deterministic procedure may appear in
`AIEvaluationReport.reproduction` as evidence provenance. Recording or reviewing
that procedure does not imply that the AIEvaluator itself executed it.

If a required measurement must be generated but no valid reproducible evidence
is available under the current governed inputs and permission boundary, the
criterion is unavailable for evaluation and therefore prevents `PASS`.

### 5. Applicability of concrete criteria

The three gate-required capability dimensions are always required for the
existing AI-evaluation boundary.

Within each dimension, a concrete dataset, scenario, metric, threshold, baseline,
safety check or operational check may be applicable or non-applicable to the
specific project.

Applicability is determined at runtime from:

- governed Requirements scope and acceptance criteria;
- implemented-system context;
- the `AIEvaluationReport` contract.

A concrete check must not be dismissed as non-applicable solely because evidence
is inconvenient or absent.

When a report treats a normally relevant check as non-applicable, the evaluation
scope and evidence must provide a reproducible justification tied to the
governed requirements or system context.

Missing information needed to determine applicability is a missing prerequisite,
not permission to assume non-applicability.

### 6. Evidence mapping

For every status-determining required criterion, `AIEvaluationReport` uses the
existing reproducible evidence fields:

~~~text
claim
source
reproduction
result
~~~

Evidence must allow an independent reviewer to identify:

- which required capability dimension and concrete criterion the evidence
  supports;
- the governed source/revision or referenced source of the observation;
- the command, deterministic procedure, recorded evaluation method or other
  reproduction information;
- the observed result.

One capability dimension may require multiple evidence records. One evidence
record may support more than one closely related criterion only when the report
makes that relationship unambiguous and independently reproducible.

The artifact contract remains the status classifier; evidence records do not
define a second status policy.

### 7. Status consequences

The existing `AIEvaluationReport` status semantics remain authoritative.

#### PASS

`PASS` requires:

- every gate-required evaluation dimension to be covered;
- every applicable required criterion within the declared scope to have complete
  reproducible evidence;
- required datasets/scenarios, thresholds, baselines, safety/failure checks and
  operational evidence to be present when applicable;
- no required evaluated criterion to demonstrate unacceptable behavior.

#### FAIL

`FAIL` applies when reproducible evidence demonstrates that at least one
required quality, safety, failure-mode or operational criterion is not
satisfied.

#### BLOCKED

`BLOCKED` applies when evaluation of a required criterion cannot be completed
because required evidence, data, scenario, baseline, threshold, evaluation
condition, environment or other prerequisite is unavailable, missing or
unverifiable.

Missing execution permission is not converted into success. If producing a
required measurement would require an action outside the AIEvaluator's accepted
permission boundary and no valid pre-existing evidence is available, the
evaluation is blocked.

#### Mixed conditions

`FAIL_ON_DEMONSTRATED_NONCONFORMANCE` remains unchanged.

If one required criterion has demonstrated nonconformance and another is
blocked, the report is `FAIL`.

### 8. Routing and state ownership

ADR-0011 remains unchanged.

The AIEvaluator/state owner:

- evaluates the gate under the accepted report semantics;
- classifies the outcome as exactly one of `PASS`, `FAIL`, or `BLOCKED`;
- returns that already-classified result and control.

Only the workflow controller selects the configured transition.

The AIEvaluator does not route to `TestRunner`, `Implementer`, `Blocked`, or any
other state directly.

### 9. Target preservation

Both current targets must preserve the complete AI-evaluation semantic from
canonical compiled data and compiled contracts.

For the AIEvaluator they must preserve at minimum:

- agent-instance identity;
- role-binding identity;
- workflow state and gate identity;
- gate ownership;
- all gate-required AI-evaluation capabilities;
- the fact that those capabilities are required evaluation dimensions for the
  existing AI-evaluation gate;
- governed `Requirements` and `ImplementationReport` input references;
- produced `AIEvaluationReport`;
- `AIEvaluationReport` evidence fields, required headings, status invariants and
  PASS/FAIL/BLOCKED semantics;
- the effective permission profile and its read-only / no-shell boundary;
- the static/compiler versus runtime/evidence-review boundary;
- the rule not to invent missing observations;
- the rule that unavailable required evidence prevents PASS;
- the state-owner/controller routing boundary from ADR-0011.

The renderer may also include selected skill guidance, responsibilities and
guardrails, but those strings must not become the source used to decide which
evaluation dimensions are required.

If an enabled target cannot preserve the required semantic, generation must fail
explicitly rather than omit, weaken or reinterpret it.

### 10. Static incompleteness versus runtime BLOCKED

These are different failure classes.

#### Static invalidity

Generation fails before materialization when existing compiler contracts are
malformed or inconsistent, for example when:

- workflow/bundle references are invalid;
- the state owner cannot satisfy gate-required capabilities;
- required artifact-production ownership is inconsistent;
- governed input-artifact references are invalid;
- the effective permission profile cannot be represented by an enabled target;
- a required compiled semantic cannot be preserved by an enabled target.

No runtime report is invented for a statically invalid composition.

#### Runtime BLOCKED

A statically valid composition may still produce `BLOCKED` at runtime when the
governed project artifacts or available evidence are insufficient to evaluate a
required criterion.

Examples include:

- no required acceptance threshold;
- missing evaluation dataset;
- missing scenario;
- missing or unverifiable baseline;
- unavailable environment;
- unavailable measurement;
- missing safety/failure-mode evidence;
- missing operational evidence;
- reproduction information that cannot be established or verified.

This distinction keeps project-specific evidence availability out of compiler
discovery while remaining fail closed.

### 11. Permission and actionability boundary

This ADR does not broaden the `ai-evaluation-worker` permission profile.

The selected V1 execution semantic is deliberately compatible with the current
`read-only` / `bash: deny` contract.

This ADR also does not decide the generic relationship between artifact
production and repository-file write permission. That concern belongs to the
existing target/permission/materialization authority and any separately accepted
registry-honesty decision.

If later evidence proves that the accepted AI-evaluation use case cannot be
satisfied without new execution permissions, external model invocation, an
evaluation service or another runtime capability, that is a new dependency and
must go through the normal scope/decision flow. It must not be smuggled into the
bounded ADR-0013 implementation.

### 12. Determinism

This decision introduces no new unordered declaration, identifier set, resolver
or runtime state.

Determinism remains governed by the existing canonical composition:

- workflow gate capabilities retain their existing canonical ordering behavior;
- input-artifact references retain existing deterministic compilation;
- artifact contracts retain their existing deterministic serialization;
- target rendering derives only from typed compiled data and compiled contracts.

Runtime observations do not feed back into compilation.

### 13. Version consequences

The decision adds no new registry, workflow, artifact, bundle, active-config or
target-adapter source contract.

Therefore the bounded implementation does not require version changes solely for
ADR-0013:

- `ai-application-delivery` remains `0.4.0`;
- `AIEvaluationReport` remains `0.7.0`;
- `ai-application` bundle remains `0.3.0`;
- active-config schema remains `0.11.0`;
- generator remains `0.1.0`;
- registered target-adapter versions remain unchanged;
- lockfile and output-manifest format versions remain unchanged.

The later renderer/preservation implementation will change generated target
content. Normal generation may therefore change:

- target-owned generated files;
- `.agentic/generated/output-manifest.json` content and hashes;
- `.agentic/agentic-lock.json` content hash where normal compiler-input
  provenance includes changed source.

`.agentic/agentic.json` does not require a new member or schema version solely
for ADR-0013.

If implementation discovers that a schema/domain/registry declaration or
permission change is actually required, stop. That contradicts this selected
decision and requires the decision/version consequences to be revisited before
implementation continues.

## Acceptance scenarios

| # | Scenario | Expected semantic result |
| ---: | --- | --- |
| 1 | Current AI application composition | Static validation succeeds with existing AIEvaluator gate, owner, governed inputs, capabilities, report contract and permission profile. |
| 2 | Required quality dimension | `ai.evaluate-quality` is preserved as a required gate dimension and applicable quality criteria require reproducible evidence. |
| 3 | Required safety dimension | `ai.evaluate-safety` is preserved as a required gate dimension and applicable safety/failure criteria require reproducible evidence. |
| 4 | Required operational dimension | `ai.evaluate-operational-risks` is preserved as a required gate dimension and applicable operational criteria require reproducible evidence. |
| 5 | Complete evidence satisfies all applicable criteria | `AIEvaluationReport` is `PASS`. |
| 6 | Reproducible evidence demonstrates nonconformance | `AIEvaluationReport` is `FAIL`. |
| 7 | Required threshold missing | Runtime `BLOCKED`, absent independently demonstrated failure. |
| 8 | Required dataset/scenario/baseline unavailable | Runtime `BLOCKED`, absent independently demonstrated failure. |
| 9 | Required measurement would require unavailable execution capability | Runtime `BLOCKED`, absent independently demonstrated failure. |
| 10 | Demonstrated failure plus another blocked criterion | `FAIL` under `FAIL_ON_DEMONSTRATED_NONCONFORMANCE`. |
| 11 | Recorded reproduction command exists | The AIEvaluator may review it as evidence; the command does not imply evaluator-owned shell execution. |
| 12 | Skill prose proposes an additional evaluation obligation | It is guidance only; it does not alter the canonical required gate dimensions. |
| 13 | Target omits a required AI capability or evidence/status boundary | Generation fails explicitly. |
| 14 | Target grants shell semantics inconsistent with compiled read-only permission | Existing target permission validation fails; ADR-0013 does not override permissions. |
| 15 | Controller receives AI evaluation result | Controller routes the already-classified PASS/FAIL/BLOCKED result under ADR-0011. |
| 16 | Compiler cannot inspect produced Requirements content | Compilation still succeeds when static references are valid; missing runtime criteria/threshold evidence is classified at runtime, not invented by the compiler. |
| 17 | New AI-evaluation DSL/category list proposed | Rejected unless a new accepted decision proves the existing authority map insufficient. |
| 18 | New execution permission or evaluation service becomes necessary | Separate scope/decision dependency; not part of ADR-0013 implementation. |

## Alternatives considered

### New gate-level `requiredAIEvaluationEvidence` categories

Rejected.

The current gate already requires exactly the AI-evaluation capabilities that
define the three V1 evaluation dimensions. A second category list would duplicate
gate authority, require equality/drift validation, add schema/version cost and
create a second vocabulary without resolving project-specific criteria.

ADR-0012 required a new test-evidence set because `TestReport` plus generic
testing capabilities did not state which validation claims had to execute. The
AI-evaluation flow is different: the existing gate already carries the three
domain-specific evaluation requirements, and `AIEvaluationReport` already
defines the domain-specific evidence/status contract.

### Put required AI-evaluation criteria in `AIEvaluationReport`

Rejected.

The artifact contract is reusable evidence/status authority. It must not own one
project's concrete acceptance criteria or workflow-specific scope.

It already defines the required report structure and classification semantics.

### Put project-specific criteria in the workflow

Rejected.

Reusable workflow definitions must not embed project-specific datasets, metric
thresholds, baselines, prompts, model endpoints or scenarios.

Those belong to the governed project requirements/evidence context.

### Infer required obligations from role responsibilities or skill prose

Rejected.

Responsibilities and skills are useful concrete guidance, but free-form prose is
not the narrow canonical owner for gate requirements and must not create hidden
target-specific obligations.

The gate's typed capability identities are the existing canonical requirements.

### Let the compiler inspect Requirements and discover evaluation criteria

Rejected.

Produced artifact content is runtime workflow evidence, not compiler registry
input. Parsing arbitrary Markdown would create a second dynamic resolution path,
break the static compiler boundary and make compilation depend on runtime
artifacts.

### Make AIEvaluator execute evaluation commands

Rejected for current V1.

The accepted concrete AIEvaluator is `read-only` with `bash: deny`. Silently
granting shell execution would override permission authority and duplicate the
separate TestRunner execution role.

If future accepted use cases require an evaluation executor, that requires a
separate explicit permission/runtime decision.

### Add an evaluation registry or generic AI-evaluation DSL

Rejected.

A dataset/model/metric/scenario registry or policy/execution DSL would add new
product infrastructure and resolution semantics far beyond the bounded V1 gap.

### Delegate AI evaluation to TestRunner

Rejected.

TestRunner owns software test evidence under ADR-0012. It does not own
`AIEvaluationReport`, AI-specific quality/safety/operational classification or
the `AIEvaluator` workflow state.

Collapsing the roles would violate the accepted composition and separation of
duties.

## Consequences

### Positive

- The existing AI-evaluation flow gets an explicit fail-closed execution
  boundary without new schema or registry machinery.
- Required evaluation dimensions have one existing canonical owner: the
  workflow gate.
- Project-specific criteria remain governed by project Requirements rather than
  reusable workflow source.
- `AIEvaluationReport` remains the single evidence/status authority.
- Current read-only permissions remain authoritative.
- Missing evidence or execution prerequisites cannot silently become PASS.
- Targets can preserve the semantic from existing `CompiledComposition` data
  and artifact/permission contracts.
- ADR-0011 routing and ADR-0012 test evidence remain separate and unchanged.
- No autonomous workflow runtime, model host, evaluation service or generic DSL
  is introduced.

### Costs and limitations

- The AIEvaluator does not generate missing measurements under the current V1
  contract.
- Successful evaluation depends on governed inputs and available reproducible
  evidence being sufficient.
- Runtime applicability still requires domain judgment constrained by
  Requirements and report evidence.
- A future requirement for evaluator-owned command/model execution will require
  a separate permission/runtime decision.
- Target-preservation implementation must make relationships currently spread
  across compiled gate, role, artifact and permission data explicit without
  creating a new competing authority.

## Bounded later implementation surface

The later implementation issue is limited to making this already-selected
semantic explicit and fail-closed in the current target-preservation path.

Expected bounded surface:

1. target rendering from existing `CompiledWorkflowGate`,
   `CompiledRoleBinding`, governed input-artifact references,
   `AIEvaluationReport` contract and effective permission profile;
2. fail-closed target-preservation validation for the existing AI-evaluation
   semantic;
3. focused integration/unit tests for both current targets and the static/runtime
   boundary;
4. current core-domain/status documentation where implementation changes
   accepted current behavior;
5. normal regeneration of affected target-owned files, output manifest and
   lockfile provenance.

The implementation must not add:

- a new workflow/schema member;
- a new domain enum or evaluation registry;
- a new active-config member or schema version;
- artifact-contract changes;
- bundle or permission-profile changes;
- compiler-side artifact-content inspection;
- command/model execution;
- runtime workflow state;
- new targets.

## Separate unresolved concerns

This ADR does not resolve:

- generic target/actionability questions about how read-only agents materialize
  their owned output artifacts;
- registry-honesty findings owned by Goal #48;
- consumer release-readiness evidence;
- future external evaluation services or model-under-test execution;
- generic dataset/model/benchmark management.

Those concerns do not change the bounded V1 AI-evaluation evidence-review
semantic selected here unless a later accepted decision explicitly does so.
