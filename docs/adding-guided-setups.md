# Adding Guided Setups

This guide describes how to add a real guided setup to Agentic Workflow Generator.

It captures the architectural contracts, implementation sequence, validation requirements, and testing lessons established while adding:

~~~text
lean-delivery-greenfield
orchestrated-delivery-greenfield
review-heavy-delivery-greenfield
~~~

Use this guide when implementing the domain-oriented setups planned for milestone 2, including AI applications, data pipelines, web APIs, libraries, CLI tools, and frontend applications.

## 1. What makes a setup real?

A guided setup is not only a questionnaire.

A real setup represents a complete, internally consistent delivery composition:

~~~text
setup
  → bundle
    → profile
    → workflow
    → agents
    → skills
    → artifacts
    → targets
~~~

A new setup must create a materially different composition when its delivery model differs.

Do not simulate a specialized setup by:

~~~text
reusing an unrelated workflow
renaming an existing bundle
adding questionnaire options that do not affect materialization
silently falling back to another setup
claiming support for agents or capabilities that are not registered
~~~

The system is fail-closed:

~~~text
failFast: true
fallbackAllowed: false
~~~

Unsupported choices must be classified as blocked and must explain why they cannot be selected.

## 2. Registry composition

A complete setup normally consists of four registry files:

~~~text
registry/workflows/<name>.workflow.json
registry/profiles/<name>.profile.json
registry/bundles/<name>.bundle.json
registry/setups/<name>-greenfield.setup.json
~~~

A domain setup may also require new registry entries under:

~~~text
registry/agents/
registry/skills/
registry/artifacts/
registry/targets/
registry/tool-providers/
~~~

Only add these when the domain composition requires capabilities or contracts that do not already exist.

## 3. Setup contract

The setup controls guided project shaping.

It defines:

~~~text
name
description
version
mode
defaultBundle
questions
finalRecommendation
~~~

Each question contains:

~~~text
id
prompt
recommended
compatible
blocked
options
~~~

Each selectable option must have:

~~~text
value
label
reason
~~~

Recommended and compatible options may also contain a `recommends` object.

The setup validator requires classifications and options to agree.

A value must not appear in more than one classification.

## 4. Classification semantics

### Recommended

A recommended option is fully represented by the setup and is selected by default.

Its reason must explain why the registered composition is the preferred choice.

### Compatible

A compatible option can safely use the exact composition produced by the setup.

Compatible does not mean:

~~~text
approximately supported
planned for later
silently mapped to another design
implemented through fallback
~~~

If an option implies a different workflow, agent set, artifact chain, target set, or policy, it is not compatible unless those differences are actually materialized.

### Blocked

A blocked option is intentionally unsupported by the setup.

Its reason should:

~~~text
state the incompatibility
describe the actual setup behavior
identify another setup when one is appropriate
avoid promising unimplemented behavior
~~~

Blocked options must not contain recommendations that could be materialized.

## 5. Workflow design rules

A workflow defines the actual delivery state machine.

Every non-terminal state must have:

~~~text
name
agent
gate
~~~

Every non-terminal state must have at least one outgoing transition.

Every referenced agent must exist.

Every terminal state must:

~~~text
be listed in terminalStates
be marked terminal
declare no agent
have no outgoing transition
~~~

All registered states and terminal states must be reachable from the start state.

Transitions must use statuses allowed by the artifact produced at the source gate.

### Important: workflow agents and materialized gates

Guided initialization materializes gates for every non-terminal workflow state.

Therefore:

~~~text
every workflow state agent must be selected by the setup
every workflow state agent must be included by the bundle
~~~

Selecting a smaller agent subset while reusing a larger workflow creates invalid gates owned by missing agents.

Create a smaller workflow instead.

### Important: one active bundle per workflow

Generated output resolution identifies the active bundle through the selected workflow.

More than one bundle using the same active workflow is ambiguous and fails.

When a new setup represents a distinct composition, give it a distinct workflow.

## 6. Profile design rules

A profile connects a workflow to the recommended execution capabilities.

It must reference:

~~~text
an existing workflow
existing agents
capabilities provided by registered skills
valid runtime profiles
~~~

The profile workflow must match the bundle workflow exactly.

Do not copy a profile and only rename it.

Its agents, capabilities, and runtime recommendations must represent the intended setup.

## 7. Bundle design rules

The bundle is the complete composition boundary.

It declares:

~~~text
profile
workflow
agents
skills
artifacts
targets
~~~

The bundle validator proves that:

~~~text
all references exist
all workflow state agents are included
all workflow transitions stay inside the workflow
all agent capabilities are covered by bundle skills
all artifacts produced by bundle agents are included
all target adapter names match their registered targets
the profile workflow matches the bundle workflow
~~~

A bundle should include only the agents, skills, and artifacts needed by its workflow and composition.

## 8. Questionnaire design rules

Questions must shape or explain a real composition.

Good questions distinguish:

~~~text
delivery risk
assurance requirements
workflow behavior
supported target platforms
domain architecture
required quality evidence
tool-provider requirements
~~~

Avoid cosmetic questions whose options all imply different behavior while materializing the same result.

For example, a setup with code review before tests must not classify “review after tests” as compatible unless another actual workflow is selected.

When an option would require a different flow, either:

~~~text
block it and reference the correct setup
or implement a distinct setup, bundle, profile, and workflow
~~~

## 9. Recommended implementation sequence

Add one composition at a time.

### Step 1: Design the composition

Write down:

~~~text
purpose
start state
non-terminal states
terminal states
pass routes
failure routes
agents
capabilities
artifacts
targets
runtime profiles
~~~

Confirm that the setup is materially different from existing setups.

### Step 2: Add the workflow

Create:

~~~text
registry/workflows/<name>.workflow.json
~~~

Validate immediately:

~~~bash
scripts/agentic/agentic-gen.sh validate-registry-schemas
scripts/agentic/agentic-gen.sh validate-workflows
~~~

### Step 3: Add the profile

Create:

~~~text
registry/profiles/<name>.profile.json
~~~

Validate:

~~~bash
scripts/agentic/agentic-gen.sh validate-profiles
~~~

### Step 4: Add the bundle

Create:

~~~text
registry/bundles/<name>.bundle.json
~~~

Validate:

~~~bash
scripts/agentic/agentic-gen.sh validate-bundles
~~~

### Step 5: Add the setup

Create:

~~~text
registry/setups/<name>-greenfield.setup.json
~~~

Validate:

~~~bash
scripts/agentic/agentic-gen.sh validate-setups
~~~

### Step 6: Run guided dry-run

Use the recommended defaults:

~~~bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup <name>-greenfield \
  --dry-run
~~~

Inspect the printed composition.

Confirm that:

~~~text
the expected bundle is selected
the expected profile is selected
the expected workflow is selected
the agent set matches all workflow states
the skill set covers all agent capabilities
the artifact set covers all produced artifacts
the target set matches the selected answer
failFast is true
fallbackAllowed is false
no files are written
~~~

### Step 7: Validate idempotency

Run:

~~~bash
scripts/agentic/agentic-gen.sh validate-init-idempotency \
  --guided \
  --setup <name>-greenfield
~~~

Both generated configuration files must remain deterministic:

~~~text
.agentic/setup-profile.json
.agentic/agentic.json
~~~

### Step 8: Add permanent automated coverage

At minimum, add a success test proving guided-init idempotency for the setup.

Add negative tests when the setup introduces:

~~~text
new schema fields
new semantic rules
new registry types
new materialization logic
new answer combination rules
new tool-provider behavior
~~~

Run:

~~~bash
scripts/agentic/agentic-gen.sh test-negative
~~~

### Step 9: Run the complete pipeline

Run:

~~~bash
scripts/agentic/agentic-gen.sh doctor-strict
~~~

The working tree may be dirty during implementation, but all validators and tests must pass.

### Step 10: Update documentation and status

Update:

~~~text
README.md
docs/guided-init.md
this guide when new architectural lessons are discovered
project-status.md
~~~

`project-status.md` is the authoritative project status and roadmap.

Update it before final validation and push.

### Step 11: Refresh generated state and lockfile

After registry or generator changes, regenerate and validate the tracked generated state according to the normal repository workflow.

The lockfile must include all relevant registry inputs and hashes.

Do not manually edit lockfile hashes.

## 10. Stable test fixtures

Tests must not depend on alphabetical registry ordering.

Do not write helpers such as:

~~~text
first setup file
first workflow file
first bundle file
~~~

They become unstable as soon as another registry entry sorts before the original fixture.

Tests that expect a specific composition must use explicit named fixtures:

~~~text
orchestrated-delivery-greenfield.setup.json
orchestrated-delivery.workflow.json
orchestrated-delivery.bundle.json
~~~

Generic validator tests may choose any file only when their mutation and expected error are genuinely independent of the file contents.

### Interactive tests with multiple setups

When only one setup exists, an empty selection may mean the default.

When multiple setups exist, interactive tests must explicitly select a setup by name or deterministic menu number.

Prefer the name when the test is intended to verify a specific setup.

Cancellation tests must send:

~~~text
q
~~~

Do not simulate cancellation with empty input.

### Setup-profile mutation tests

A setup-profile test must materialize the exact setup required by its assertions before mutating:

~~~text
.agentic/setup-profile.json
~~~

Do not rely on whichever setup was last generated in the repository.

## 11. Current process-oriented setups

### lean-delivery-greenfield

Purpose:

~~~text
focused lower-risk software changes
compact fail-closed process
fewer handoffs
implementation retry after failed tests or review
~~~

Flow:

~~~text
Requirements
  → Implementer
  → TestRunner
  → CodeReviewer
  → Done
~~~

### orchestrated-delivery-greenfield

Purpose:

~~~text
general orchestrated delivery
architecture before implementation
tests before code review
final QA acceptance
~~~

Flow:

~~~text
Requirements
  → Architect
  → Implementer
  → TestRunner
  → CodeReviewer
  → QA
  → Done
~~~

### review-heavy-delivery-greenfield

Purpose:

~~~text
high-assurance or release-critical changes
independent code review before formal tests
test evidence
final QA acceptance
~~~

Flow:

~~~text
Requirements
  → Architect
  → Implementer
  → CodeReviewer
  → TestRunner
  → QA
  → Done
~~~

These setups demonstrate that a real setup difference can be process-oriented even when the same underlying agents and skills are reused.

## 12. Milestone 2 domain setup checklist

For each planned domain setup, answer these questions before implementation.

### Domain boundary

~~~text
What concrete project type does the setup support?
What project types are explicitly unsupported?
How is it materially different from existing setups?
~~~

### Architecture

~~~text
What architecture decisions are required?
What runtime profiles are appropriate?
Which tool providers are required?
Which targets should be recommended?
~~~

### Workflow

~~~text
What states are domain-specific?
Which quality gates are mandatory?
Where do failures return?
Which failures block immediately?
~~~

### Agents

~~~text
Do existing agents cover the domain?
Are specialized agents required?
Does each specialized agent have a clear role?
~~~

### Skills

~~~text
Which capabilities are required?
Are existing skills sufficient?
Does every capability have exactly one valid provider?
~~~

### Artifacts

~~~text
What evidence must each gate produce?
Do new artifact contracts need schemas?
Are all transition statuses represented by artifact statuses?
~~~

### Guided questions

~~~text
Which answers actually alter the composition?
Which answers are safe with the same composition?
Which answers must be blocked?
Are all reasons technically accurate?
~~~

### Validation

~~~text
Do all registry validators pass?
Does guided dry-run print the expected composition?
Is initialization idempotent?
Are success and failure paths automated?
Does doctor-strict pass?
~~~

## 13. Definition of done

A new guided setup is complete only when:

~~~text
its setup, bundle, profile, and workflow are registered
its composition is materially meaningful
all references and capabilities validate
all workflow agents are selected
all produced artifacts are included
all questionnaire classifications match actual behavior
blocked choices fail without fallback
guided dry-run passes
guided initialization is idempotent
automated coverage protects the setup
documentation is updated
project-status.md is updated
the lockfile is refreshed
doctor-strict passes
the final working tree contains only intentional changes
~~~
