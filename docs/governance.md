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
| Current architecture | `docs/architecture.md` |
| Core domain model | `docs/core-domain-model.md` |
| Detailed domain entities and relationships | authoritative PlantUML sources under `docs/diagrams/domain/` |
| Architectural rationale | accepted ADRs under `docs/adr/` |
| Accepted technology baseline | `docs/tech-stack.md` |
| Registry contracts | `registry/` and version-controlled schemas |
| Compiler behavior | `src/agentic_workflow_generator/` and automated tests |
| Compiler-input provenance | `.agentic/agentic-lock.json` |
| Generated-output integrity | `.agentic/generated/output-manifest.json` and canonical rendering |
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

1. update `docs/architecture.md`;
2. update affected authoritative PlantUML sources and rendered SVGs;
3. create or supersede an ADR when durable rationale is required;
4. update ownership documentation where needed;
5. ensure implementation matches the accepted decision.

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
scope, project status, relevant architecture and ADRs, work on an appropriate
topic branch, produce a bounded reviewable change, run applicable validation and
submit through the normal pull-request flow.

They must not invent fallback behavior, weaken validation, introduce speculative
capabilities, or treat conversational history as repository truth.

## Governance changes

Changes to this document change mandatory delivery rules and therefore require
an explicit governance/documentation pull request.
