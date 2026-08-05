# Project governance

This document defines mandatory delivery governance for
`agentic-workflow-generator`.

The repository is the authoritative project record. Chat history, local notes,
issues, generated summaries and AI memory may support the work but do not
override accepted repository state.

## Authority

| Concern | Authoritative source |
| --- | --- |
| Accepted implementation scope | `docs/scope.md` |
| Current state and next accepted priority | `docs/project-status.md` |
| Delivery governance | `docs/governance.md` |
| Operational workflow and development commands | `docs/workflow.md` |
| Current architecture narrative | `docs/architecture.md` |
| Semantic architecture model | `docs/architecture/workspace.dsl` |
| Core domain model | `docs/core-domain-model.md` |
| Architectural rationale | accepted ADRs under `docs/adr/` |
| Accepted technology baseline | `docs/tech-stack.md` |
| Registry contracts | `registry/` and version-controlled schemas |
| Active compiled composition | `.agentic/agentic.json` |
| Compiler behavior | `src/agentic_workflow_generator/` and automated tests |
| Compiler-input provenance | `.agentic/agentic-lock.json` |
| Generated-output integrity | `.agentic/generated/output-manifest.json` and canonical rendering |
| Planning, dependencies and readiness | GitHub issues and governed labels, constrained by accepted repository authority |
| Stable/release state | `production` and release tags |

Supporting documents must not create competing authority.

## Core rules

1. Repository truth wins over conversational or local assumptions.
2. Scope is accepted before implementation.
3. Normal work starts from `development` and is performed on a topic branch.
4. Normal work is not committed directly to `development` or `production`.
5. One pull request has one coherent purpose.
6. Architecture and ownership changes are explicit.
7. New technologies require an accepted need and an explicit decision.
8. Future possibilities may shape boundaries but do not justify speculative implementation.
9. Validation is fail-fast; missing requirements must not silently degrade.
10. Humans, AI agents and automation follow the same repository workflow.
11. Issue planning, labels and Goal membership never override accepted scope,
    architecture or ADR authority.
12. Planning hierarchy and execution dependencies are separate concerns.

## Issue planning, Goals and readiness

GitHub issues own planning, tracking, dependency and readiness state. They do not
replace `docs/scope.md`, accepted ADRs, contracts, source or tests as accepted
product authority.

### Issue categories

The repository uses these executable/reviewable categories:

- `type: decision` — a decision required before downstream work can proceed;
- `type: scope` — a candidate or accepted change to project scope;
- `type: research` — investigation without implementation commitment;
- `type: implementation` — authorized implementation with accepted scope and
  defined validation;
- `bug` — a defect in accepted behavior or authority;
- `documentation` — bounded documentation/governance work.

The governance model defines `type: goal` as the planning-only category for one
observable outcome. It is not an executable work type.

A governance-defined label must exist in GitHub before any issue relies on it.
Label creation is repository administration, not scope or implementation
authority.

### Goal and Subgoal semantics

A Goal is a planning/tracking container. It does not:

- authorize implementation;
- change accepted scope;
- accept a bounded context, capability hypothesis, technology or architecture
  change;
- make exploratory statements authoritative.

A Goal must define at minimum:

- a concrete outcome or use case;
- the accepted repository baseline;
- explicit non-goals;
- objective end-to-end acceptance evidence;
- a `Subgoals` checklist;
- relevant execution dependencies;
- known parallel-safe subgoals where applicable.

Executable or reviewable child issues use the existing categories above and
declare their planning parent in the issue body:

```text
Goal: #<issue-number>
```

Goal membership is hierarchy only. It is never an execution blocker.

### Execution dependencies and blocking

Execution dependencies are declared independently:

```text
Blocked by #...
Blocks #...
```

The governance model defines `state: blocked` for an issue with at least one
unresolved execution dependency or another explicit readiness blocker. The
label must exist in GitHub before it is used. Removing or adding Goal membership
must not change blocking state by itself.

Blocked executable work must not be implemented.

### Priority

Planning priority is governed by:

- `priority: now` — the active coherent workstream;
- `priority: next` — the next candidate, which must be re-read against current
  `development` before decomposition or execution;
- `priority: later` — deferred outcome-level planning without speculative
  pre-design.

`priority: now` already exists in the repository. Any governance-defined
priority label that is not yet present must be created before first use after
this governance change is accepted.

Normally only one Goal or coherent workstream is `priority: now`.

Several child issues may be `priority: now` at the same time only when they:

- belong to the same active Goal or coherent workstream;
- have resolved prerequisites;
- are authorized by applicable accepted scope when executable;
- have explicit ownership and non-ownership;
- have independently verifiable outcomes;
- do not depend on unresolved sibling results;
- do not make uncontrolled competing changes to the same authoritative truth.

### Progressive decomposition

`priority: later` stays at outcome level.

Before promoting work to `priority: next`, re-read the candidate against
`development` and decompose only enough to establish necessary research,
decisions, dependencies, ownership and scope.

`priority: now` executes only work that is ready.

### Executable readiness

An implementation issue is ready only when:

- its outcome is concrete;
- accepted scope authorizes the work;
- relevant decisions and ADRs are accepted;
- ownership and non-ownership are explicit;
- exclusions are explicit;
- validation is defined;
- direct execution dependencies are resolved.

Decision, scope, research, defect and documentation issues must likewise have a
bounded outcome, explicit authority, exclusions and validation appropriate to
their category before execution.

### Goal completion

A Goal is complete only when:

- all required subgoals are complete;
- objective end-to-end acceptance evidence is satisfied;
- the complete accepted result exists on `development`;
- `docs/project-status.md` is synchronized when the outcome changes current
  project state;
- no required execution dependency remains unresolved.

## Branch model

Permanent branches:

- `development` — integration branch and accepted next state.
- `production` — stable/release branch.

Normal topic prefixes:

```text
feat/
fix/
docs/
chore/
refactor/
test/
```

Emergency production fixes may use `hotfix/`.

Do not add permanent branches without an accepted governance need.

## Scope changes

Implementation outside `docs/scope.md` requires a dedicated scope-transition
pull request before implementation begins.

A scope transition must state the concrete problem, define in-scope and
out-of-scope boundaries, update `docs/scope.md`, update project status when
needed, identify architecture and technology impact, and define measurable
acceptance criteria.

A scope-transition pull request contains authority changes only. It must not hide
the implementation it is intended to authorize.

## Capability admission

Before adding a new product or domain capability, establish:

- the accepted use case that requires it;
- why current capabilities are insufficient;
- the responsibility it owns;
- what it explicitly does not own;
- the lifecycle or invariants that justify the boundary;
- the smallest required public contract.

A separable technical concept alone is not sufficient reason to add a new
capability, module, service or registry concept.

## Technology admission

Technology follows the requirement:

```text
problem
  -> accepted requirement
  -> reasonable alternatives
  -> decision
  -> technology
```

Before introducing a framework, runtime, service, datastore, provider, queue,
tool or infrastructure component, establish the accepted requirement, why the
current baseline is insufficient, reasonable alternatives, and operational and
architectural consequences.

Significant or long-lived technology decisions require an ADR.

## Architecture changes

An architecture change includes changes to boundaries, dependency direction,
ownership, canonical representations, persistence responsibilities, external
contracts, deployment topology or compiler authority.

When architecture changes:

1. update `docs/architecture.md` when the current-state narrative changes;
2. update `docs/architecture/workspace.dsl` when semantic architecture changes;
3. regenerate affected derived architecture diagrams when the canonical model
   changes;
4. create or supersede an ADR when durable rationale is required;
5. update ownership documentation where needed;
6. ensure implementation matches the accepted decision.

`docs/architecture/workspace.dsl` is the sole semantic architecture model.
Committed SVGs under `docs/architecture/diagrams/` are derived stakeholder
output. PlantUML is retained only inside the accepted derived rendering pipeline
and is not semantic architecture authority.

Planned or exploratory architecture must not be presented as current state.

## Pull requests and merge

Normal pull requests target `development`.

Before merge they must:

- remain inside accepted scope;
- contain one coherent outcome;
- keep affected authoritative artifacts synchronized;
- pass applicable local validation;
- pass required remote checks when the pull request targets `production`;
- resolve review conversations;
- contain no unrelated cleanup or speculative work.

Normal pull requests targeting `development` do not require GitHub Actions.
Their validation is performed locally before push and merge. Remote CI is a
release/hotfix gate for pull requests targeting `production`.

Normal topic branches are squash-merged into `development`.

The resulting squash commit on `development` is the accepted integration state.

## Release

A release is a deliberate pull request from accepted `development` state to
`production`.

GitHub Actions remote validation is required at this boundary. The
`Validate generator` check must pass before a pull request targeting
`production` is merged.

The release boundary must remain explicit, reviewable and validated. Normal
feature work is not performed directly on `production`.

## Hotfixes

A hotfix is permitted only for a real defect in stable/released state that
cannot reasonably wait for the normal integration cycle.

A hotfix branches from `production`, remains narrowly focused, passes applicable
validation, is reviewed through a pull request to `production`, and is then
reconciled into `development`.

A hotfix does not bypass scope, architecture, review, tests or documentation.

## Definition of done

A change is done only when:

- it is inside accepted scope, or scope was changed first;
- it delivers one coherent purpose;
- ownership and architecture remain correct;
- affected authoritative artifacts are synchronized;
- relevant tests and validation pass;
- generated output and lockfile state are canonical when affected;
- required ADRs exist;
- required remote checks pass when the pull request targets `production`;
- review conversations are resolved;
- the change is merged through the approved pull-request workflow.

Local code working by itself is not sufficient.

## AI agents and automation

AI agents and automation have no independent scope or architecture authority.

Before modifying the project they must inspect current repository state, accepted
scope, project status, the active issue and its labels/dependencies, relevant
architecture and ADRs, work on an appropriate topic branch, produce a bounded
reviewable change, run applicable validation and submit through the normal
pull-request flow.

For a subgoal they must also verify its `Goal: #...` parent, direct execution
dependencies and the Goal acceptance state. They should not read every sibling
unless dependency or shared-ownership analysis requires it.

After a merge they must re-read accepted `development`, verify the merge and
issue state, re-read changed authoritative artifacts, direct dependent issues
and the parent Goal when relevant before selecting the next action.

They must not invent fallback behavior, weaken validation, introduce speculative
capabilities, or treat conversational history as repository truth.

## Governance changes

Changes to this document change mandatory delivery rules and therefore require
an explicit governance/documentation pull request.
