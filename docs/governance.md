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
| Stable/release branch | `production` |
| Integration branch | `development` |
| Main validation gate | `PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict` |
| Accepted scope | `docs/scope.md` |
| Current project state | `docs/project-status.md` |
| Governance | `docs/governance.md` |
| Operational delivery workflow | `docs/workflow.md` |
| Architecture principles | `docs/architecture.md` |
| Core domain documentation | `docs/core-domain-model.md` |
| Architecture model | authoritative PlantUML sources under `docs/diagrams/domain/` as defined by `docs/architecture.md` |
| Architectural decisions | `docs/adr/` |
| Operational developer commands | `docs/developer-workflow.md` |

`production` and `development` correspond to the stable/release and integration roles from
the governed delivery model. Their names are project-specific; their semantics
must remain distinct.

## Source-of-truth matrix

| Concern | Authoritative source |
| --- | --- |
| Accepted scope | `docs/scope.md` |
| Current project state and next accepted priority | `docs/project-status.md` |
| Delivery governance | `docs/governance.md` |
| Operational delivery sequence | `docs/workflow.md` |
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
| Release state | `production` and release tags |
| Local validation procedure | `docs/developer-workflow.md` |

Supporting or historical documents may summarize these sources but must not
redefine competing truth.

## Authority hierarchy

The project separates delivery concerns deliberately:

- `docs/scope.md` defines what work is currently accepted.
- `docs/project-status.md` defines current state and the next accepted priority.
- `docs/architecture.md`, its authoritative diagrams, and accepted ADRs define
  architectural truth and rationale.
- `docs/governance.md` defines mandatory delivery rules, decision gates, branch
  semantics, merge policy, and release policy.
- `docs/workflow.md` defines the repeatable end-to-end operational sequence that
  applies the governance rules.
- `docs/developer-workflow.md` defines concrete local commands and validation
  procedures used while executing that workflow.

`docs/workflow.md` must not redefine accepted scope, architecture, or governance.

`docs/developer-workflow.md` must not redefine the delivery sequence or weaken a
governance or workflow requirement.

When two documents appear to disagree, the concern-specific authoritative
source in the source-of-truth matrix wins.

`docs/engineering-discovery.md` and documents under `docs/research/` are
non-authoritative unless an accepted decision explicitly promotes a proposal
into current scope or architecture.

## Permanent branches

### `production`

`production` represents stable, release-ready or released state.

Ordinary feature, refactoring, documentation and test work does not start from
or commit directly to `production`.

### `development`

`development` represents the accepted next state and is the integration baseline for
normal work.

Normal topic branches originate from the latest accepted `development`.

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

## Normal delivery rules

The detailed end-to-end delivery sequence is defined in `docs/workflow.md`.

Governance requires that normal work:

- starts from the latest accepted `development`;
- is performed on a purpose-oriented topic branch;
- stays inside accepted scope;
- contains one coherent outcome;
- keeps affected authoritative artifacts synchronized;
- passes the applicable local validation gates;
- is committed before the clean-tree `doctor-strict` gate is run;
- is pushed and reviewed through a pull request targeting `development`;
- passes required remote checks;
- resolves review conversations before merge;
- is squash-merged into `development`;
- treats the resulting `development` state as the new accepted integration state.

Normal work must not be committed directly to `development` or `production`.

The operational commands, ordering and working checklist for these rules are
defined only in `docs/workflow.md`.

## Scope transition rules

Implementation outside accepted `docs/scope.md` is prohibited until a separate
scope transition has been accepted.

A scope transition must:

- use a dedicated topic branch;
- state the concrete problem requiring expansion;
- update `docs/scope.md`;
- update `docs/project-status.md` when current state or next priority changes;
- identify architecture, ownership and technology impact;
- update architecture sources and ADRs when required;
- define explicit in-scope and out-of-scope boundaries;
- define measurable acceptance criteria;
- contain only the authority changes needed to admit the future work;
- be reviewed and merged into `development` before implementation begins.

A scope-transition pull request must not hide the implementation it is intended
to authorize.

The operational scope-transition sequence is defined in `docs/workflow.md`.

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

### Topic branch to `development`

Prefer squash merge.

This keeps one coherent accepted change in permanent integration history while
allowing working commits on the topic branch.

### `development` to `production`

Use a deliberate release pull request.

The release boundary must remain visible and reviewable.

## Release rules

`production` represents stable, release-ready or released state.

A release must:

- promote an accepted `development` state through a deliberate pull request to `production`;
- keep the release boundary explicit and reviewable;
- pass the required project validation gates;
- contain only the intended release state;
- update required release documentation or versioning;
- create the applicable release tag after the release state is accepted.

Normal feature work must not be performed directly on `production`.

The detailed release sequence is defined in `docs/workflow.md`.

## Hotfix rules

A hotfix is permitted only for a real defect in stable or released state that
cannot reasonably wait for the normal integration cycle.

A hotfix must:

- branch from `production`;
- remain narrowly focused on the production defect;
- preserve accepted architecture and fail-fast behavior;
- pass the applicable validation gates;
- be reviewed through a pull request targeting `production`;
- not introduce unrelated feature work or scope expansion;
- reconcile the same logical correction into `development` after the production fix.

A hotfix does not bypass scope, review, tests, documentation, architecture or
validation requirements.

The detailed hotfix sequence is defined in `docs/workflow.md`.

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
- commit normal work directly to `production` or `development`;
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
- check `docs/project-status.md`;
- select the next accepted outcome from current repository state.

## Governance changes

Changes to this document change the project's delivery rules and therefore
require an explicit governance pull request.

A governance change must not be hidden inside unrelated implementation work.
