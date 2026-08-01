# Project Governance

This document defines the authoritative delivery governance for
`agentic-workflow-generator`.

The repository is the authoritative project record. Chat history, AI
conversations, issues, local notes, generated summaries and other coordination
tools may assist the work, but they do not override accepted repository state.

## Core invariants

The following rules are mandatory unless changed through a reviewed governance
pull request.

1. Repository state is authoritative.
2. Scope precedes implementation.
3. Normal work is never committed directly to permanent branches.
4. One pull request has one coherent purpose.
5. Architecture and ownership changes are explicit.
6. New technologies require an accepted need and an explicit decision.
7. Future possibilities may influence boundaries but do not justify speculative
   implementation.
8. Validation is fail-fast. Missing or broken requirements must not silently
   degrade.
9. Humans, AI agents and automation follow the same repository workflow.

## Project configuration

| Setting | Value |
| --- | --- |
| Project | `agentic-workflow-generator` |
| Repository | `jfriisj/agentic-workflow-generator` |
| Stable/release branch | `main` |
| Integration branch | `dev` |
| Main validation gate | `PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict` |
| Accepted scope | `docs/scope.md` |
| Current project state | `project-status.md` |
| Governance | `docs/governance.md` |
| Architecture principles | `docs/architecture.md` |
| Core domain documentation | `docs/core-domain-model.md` |
| Architecture model | authoritative PlantUML sources under `docs/diagrams/domain/` as defined by `docs/architecture.md` |
| Architectural decisions | `docs/adr/` |
| Operational developer commands | `docs/developer-workflow.md` |

`main` and `dev` correspond to the stable/release and integration roles from
the governed delivery model. Their names are project-specific; their semantics
must remain distinct.

## Source-of-truth matrix

| Concern | Authoritative source |
| --- | --- |
| Accepted scope | `docs/scope.md` |
| Current project state and next accepted priority | `project-status.md` |
| Delivery governance | `docs/governance.md` |
| Architecture principles and authority rules | `docs/architecture.md` |
| Core domain model documentation | `docs/core-domain-model.md` |
| Detailed domain entities, relationships and cardinalities | authoritative PlantUML sources identified by `docs/architecture.md` |
| Architectural rationale | accepted ADRs under `docs/adr/` |
| Registry contracts | `registry/` and their version-controlled schemas |
| Typed domain and compiler behavior | `src/agentic_workflow_generator/` |
| Runtime behavior | source code and automated tests |
| Build and dependency wiring | version-controlled project configuration |
| Generated output ownership and integrity | `.agentic/generated/output-manifest.json` and canonical renderer behavior |
| Compiler-input provenance | `.agentic/agentic-lock.json` |
| Release state | `main` and release tags |
| Local validation procedure | `docs/developer-workflow.md` |

Supporting or historical documents may summarize these sources but must not
redefine competing truth.

`docs/engineering-discovery.md` and documents under `docs/research/` are
non-authoritative unless an accepted decision explicitly promotes a proposal
into current scope or architecture.

## Permanent branches

### `main`

`main` represents stable, release-ready or released state.

Ordinary feature, refactoring, documentation and test work does not start from
or commit directly to `main`.

### `dev`

`dev` represents the accepted next state and is the integration baseline for
normal work.

Normal topic branches originate from the latest accepted `dev`.

## Topic branches

Use short purpose-oriented branches:

~~~text
feat/<short-purpose>
fix/<short-purpose>
docs/<short-purpose>
chore/<short-purpose>
refactor/<short-purpose>
test/<short-purpose>
~~~

Emergency production fixes may use:

~~~text
hotfix/<short-purpose>
~~~

Do not introduce additional permanent branches without a concrete workflow need
and an accepted governance decision.

## Normal delivery flow

Normal work follows:

~~~text
dev
 ↓
topic branch
 ↓
local validation
 ↓
pull request
 ↓
review and required checks
 ↓
squash merge
 ↓
dev
~~~

After merge, the merged `dev` branch becomes the accepted state. The topic
branch is no longer authoritative.

### 1. Synchronize

Start from the latest integration branch:

~~~bash
git switch dev
git pull --ff-only
~~~

### 2. Inspect authoritative state

Before deciding what to change, inspect:

- `docs/scope.md`;
- `project-status.md`;
- relevant architecture documentation and diagrams;
- relevant ADRs;
- relevant registry contracts, schemas, source code and tests.

Do not rely on prior chat context or memory as project authority.

### 3. Run the scope gate

Before implementation, determine:

1. Is the requested change explicitly inside accepted scope?
2. Does it introduce a new capability?
3. Does it introduce a new technology or infrastructure dependency?
4. Does it change architecture, dependency direction or ownership?
5. Does it require an authoritative artifact to change?

If the work is outside accepted scope, implementation stops and the Scope
Transition Workflow is used first.

### 4. Define the smallest coherent change

Before implementation, identify:

- purpose;
- in-scope work;
- explicit out-of-scope work;
- acceptance criteria;
- affected authoritative artifacts.

If these cannot be stated clearly, the change is not ready for implementation.

### 5. Create a topic branch

~~~bash
git switch -c <type>/<short-purpose>
~~~

### 6. Implement only the accepted change

Do not:

- add speculative abstractions;
- implement adjacent features;
- introduce unrelated cleanup;
- add dependencies because they may be useful later;
- weaken fail-fast validation;
- create compatibility or fallback behavior unless explicitly accepted by
  scope and architecture.

Keep authoritative documentation synchronized with material changes.

### 7. Validate locally

Use the strongest relevant focused checks while developing.

Before a change is considered ready for commit or review, run the project
quality gate defined in `docs/developer-workflow.md`.

The final repository-level gate is:

~~~bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict
~~~

Only claim validation that was actually performed.

### 8. Review the local diff

Before committing:

~~~bash
git status
git diff
~~~

Verify:

- every changed file belongs to the stated purpose;
- no private, local or unintended generated files leaked in;
- no hidden scope expansion occurred;
- architecture and documentation impacts are represented;
- no unrelated cleanup was added.

### 9. Commit and push

Use concise intent-oriented commits.

Working commits are allowed on topic branches because normal topic pull
requests are squash-merged.

### 10. Pull request

Normal pull requests target `dev`.

A pull request must state:

- one purpose;
- scope impact;
- architecture impact;
- ownership impact;
- technology impact;
- explicit exclusions;
- validation actually performed.

### 11. Review

Review the actual repository diff, not only the pull request description.

Review must consider:

- scope consistency;
- architecture consistency;
- ownership;
- dependency and technology changes;
- tests and validation;
- authoritative documentation;
- generated and lockfile impact;
- unintended files;
- unresolved review conversations.

### 12. Merge and resynchronize

Normal topic pull requests are squash-merged to `dev`.

After merge:

~~~bash
git switch dev
git pull --ff-only
git status
~~~

Delete the topic branch unless there is a concrete reason to retain it.

Before starting the next change, re-read accepted repository state.

## Scope Transition Workflow

If the logical next implementation is outside accepted scope:

~~~text
new requirement
      ↓
scope decision
      ↓
docs/<scope-purpose>
      ↓
update scope and project status
      ↓
pull request to dev
      ↓
review and merge
      ↓
new scope becomes accepted
      ↓
separate implementation branch
~~~

A scope-transition pull request should contain only the authority changes needed
to admit the next work. It must not hide the full implementation in the same
change.

Before accepting a scope transition:

- the previous accepted phase is accurately represented;
- `project-status.md` reflects reality;
- new in-scope work is explicit;
- out-of-scope work is explicit;
- acceptance criteria are testable;
- the next implementation can be bounded by the new scope.

## Capability admission

Before adding a new domain or product capability, establish:

1. Which concrete accepted use case requires it?
2. Why are current accepted capabilities insufficient?
3. What does the capability own?
4. What does it explicitly not own?
5. What independent lifecycle, rules, invariants or responsibilities justify
   the boundary?
6. What is the smallest required public contract?

A separable technical concept is not by itself sufficient reason to create a
new module, service, registry concept or capability.

## Technology admission

Technology follows the requirement:

~~~text
problem
  ↓
accepted requirement
  ↓
reasonable alternatives
  ↓
decision
  ↓
technology
~~~

Before introducing a new framework, runtime, service, datastore, provider,
queue, tool or infrastructure component, establish:

- the accepted requirement;
- why the current baseline is insufficient;
- reasonable alternatives;
- operational consequences;
- architectural consequences;
- whether an ADR is required.

Do not select a technology first and invent the requirement afterward.

## Architecture changes

A change has architecture impact when it changes, for example:

- bounded-context or component boundaries;
- dependency direction;
- ownership;
- persistence ownership;
- cross-cutting execution behavior;
- deployment topology;
- external contracts;
- compiler authority or canonical representations.

When architecture is affected:

1. identify the affected boundary;
2. update the authoritative architecture source;
3. update all affected rendered diagrams in the same change;
4. create an ADR when the rationale is significant or long-lived;
5. update ownership documentation where required;
6. ensure implementation matches the accepted decision.

Planned or exploratory architecture must not be presented as implemented
current state.

## Architectural Decision Records

Significant architectural decisions are recorded under `docs/adr/`.

A minimal ADR contains:

~~~markdown
# ADR-NNNN: Decision title

- Status: Proposed
- Date: YYYY-MM-DD

## Context

What problem or constraint requires a decision?

## Decision

What has been decided?

## Alternatives considered

What reasonable alternatives were considered?

## Consequences

What becomes easier, harder, constrained or intentionally deferred?
~~~

Accepted ADRs preserve historical decisions. Do not silently rewrite an
accepted ADR to change history. A later decision supersedes an earlier ADR.

## Branch protection

Both permanent branches should be protected.

Minimum rules:

- require pull requests before merge;
- require review conversations to be resolved;
- block force pushes;
- restrict branch deletion;
- require the real project quality check when configured and reliable.

Do not create required checks for validation systems that do not actually
exist.

## Merge strategy

### Topic branch to `dev`

Prefer squash merge.

This keeps one coherent accepted change in permanent integration history while
allowing working commits on the topic branch.

### `dev` to `main`

Use a deliberate release pull request.

The release boundary must remain visible and reviewable.

## Release workflow

Release promotion follows:

~~~text
accepted dev state
       ↓
release-readiness check
       ↓
pull request: dev → main
       ↓
review and required validation
       ↓
merge
       ↓
release tag
~~~

Normal feature work is not performed directly on `main`.

## Hotfix workflow

Use a hotfix only when a defect in stable/released state cannot wait for the
normal integration cycle.

~~~text
main
 ↓
hotfix/<short-purpose>
 ↓
validate
 ↓
pull request → main
 ↓
merge and release
 ↓
reconcile the same logical fix into dev
~~~

A hotfix does not bypass scope, review, tests, documentation, architecture or
validation rules.

`dev` must contain the same logical correction after the production fix.

## Pull request discipline

One pull request must represent one understandable decision or delivery unit.

Do not accumulate unrelated:

- cleanup;
- refactoring;
- technologies;
- capabilities;
- infrastructure;
- documentation rewrites;
- opportunistic improvements.

Before every pull request, ask:

- Did this branch solve only the stated problem?
- Was anything added because it may be useful later?
- Was a generic abstraction introduced before actual variation exists?
- Was a capability added outside accepted scope?
- Was a technology introduced before an accepted requirement?
- Was a scope decision combined with unrelated implementation?
- Did an exploratory idea become an architectural commitment?
- Does documentation describe planned work as current state?

If scope expanded, remove the change or perform an explicit scope transition.

## Definition of Done

A change is done only when:

- it is inside accepted scope, or scope was explicitly changed first;
- it delivers one coherent purpose;
- ownership is correct;
- architecture boundaries are respected;
- authoritative artifacts are synchronized;
- significant decisions have ADRs where required;
- relevant tests are updated;
- the project validation gate passes;
- generated output and lockfile state are canonical when affected;
- no unrelated technology or capability was introduced;
- review conversations are resolved;
- the change is merged through the approved pull request workflow.

Local code working by itself is not sufficient.

## AI agents, automation and multiple models

Humans, AI coding agents, IDE agents, automation and other models follow the
same repository rules.

No agent gains architectural or scope authority merely because it can generate
changes.

Before modifying the project, an AI agent must:

1. inspect the current integration state;
2. read accepted scope and project status;
3. read relevant architecture and ADRs;
4. determine whether the requested work is accepted;
5. work on an appropriate topic branch;
6. produce a reviewable bounded change;
7. run available validation;
8. submit through the normal pull request flow.

AI agents must not:

- treat chat history as more authoritative than the repository;
- commit normal work directly to `main` or `dev`;
- introduce adjacent features without scope approval;
- create speculative abstractions for possible future needs;
- add technologies without an accepted requirement;
- reinterpret planned or exploratory design as implemented state;
- weaken validation to make a failing change pass;
- invent fallback behavior where the project requires fail-fast behavior.

Different humans or models may design, implement or review the same proposed
change. The repository and accepted PR state determine the final project state.

## Asynchronous collaboration

Persistent chats and project workspaces are coordination tools, not project
storage.

Use this model:

~~~text
discussion / AI / planning
          ↓
proposed repository change
          ↓
topic branch
          ↓
pull request
          ↓
accepted repository state
~~~

After every merge:

- re-read the repository before continuing;
- treat previous conversational assumptions as potentially stale;
- check `docs/scope.md`;
- check `project-status.md`;
- select the next accepted outcome from current repository state.

## Governance changes

Changes to this document change the project's delivery rules and therefore
require an explicit governance pull request.

A governance change must not be hidden inside unrelated implementation work.
