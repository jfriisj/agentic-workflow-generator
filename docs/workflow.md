# Project workflow

This document is the sole authoritative operational workflow for development of
`agentic-workflow-generator`. It owns the delivery sequence and the concrete
commands used to execute it.

Mandatory rules are defined in `docs/governance.md`. Accepted work is defined in
`docs/scope.md`. Current state and priority are defined in
`docs/project-status.md`. Architecture and technology authority remain in
`docs/architecture.md`, `docs/architecture/workspace.dsl`, `docs/adr/` and
`docs/tech-stack.md`.

## 1. Start from repository truth

Before changing the project, read the current `development` state and the
authority relevant to the work:

- `docs/scope.md`
- `docs/project-status.md`
- `docs/governance.md`
- `docs/architecture.md`
- `docs/core-domain-model.md` when domain structure is affected
- relevant ADRs
- relevant registry, source and tests

Open pull requests, topic branches and chat history are proposals or
coordination, not accepted truth.

## 2. Verify issue planning and readiness

Before creating or continuing a topic branch, verify the active issue from
GitHub:

- issue category/label;
- planning priority;
- `Blocked by #...` and `Blocks #...` dependencies;
- any explicit readiness blocker;
- the accepted repository authority named by the issue.

For a subgoal, also verify:

- `Goal: #...`;
- the parent Goal outcome and acceptance state;
- direct execution dependencies;
- whether sibling work shares an authority or dependency that must be read.

Do not read every sibling by default. Goal membership is planning hierarchy and
does not itself block execution.

Apply progressive decomposition:

- `priority: later` remains outcome-level and must not be pre-designed;
- `priority: next` is re-read against current `development` and decomposed only
  enough to establish required research, decisions, dependencies, ownership and
  scope;
- `priority: now` is executable only when the issue is ready.

An implementation issue is ready only when its outcome is concrete, accepted
scope authorizes it, required decisions are accepted, ownership and exclusions
are explicit, validation is defined and direct dependencies are resolved.

Do not implement `state: blocked` work. Do not rely on a governance-defined
label until that label exists in GitHub.

Normally keep one active Goal or coherent workstream at `priority: now`. Several
ready child issues may be active only when they are genuinely parallel-safe
under `docs/governance.md`.

## 3. Classify the work

Proceed directly only when the requested outcome is already inside
`docs/scope.md`.

Use a dedicated scope-transition pull request first when the work would add a
new product capability, target platform, runtime responsibility, architecture
constraint or other behavior not already accepted.

Create or supersede an ADR when a significant architecture or technology
decision needs durable rationale.

## 4. Define one coherent outcome

Before implementation, state:

1. the exact outcome;
2. why it is inside accepted scope;
3. affected authoritative sources;
4. deliberately excluded related work;
5. acceptance criteria;
6. validation required.

Do not bundle unrelated cleanup, speculative abstractions or neighboring
capabilities.

## 5. Synchronize `development`

The interactive shell may be fish. Use Bash only for fail-fast multi-command
gates; do not set `set -euo pipefail` globally.

```bash
bash -lc '
set -euo pipefail

git switch development
git fetch --prune origin
git pull --ff-only origin development
test -z "$(git status --porcelain=v1 -uall)"
'
```

After a squash merge, synchronize from `origin/development`; do not merge the
old topic branch back into local `development`.

## 6. Create a topic branch

Branch from synchronized `development`.

```text
feat/<purpose>
fix/<purpose>
docs/<purpose>
chore/<purpose>
refactor/<purpose>
test/<purpose>
```

Use `hotfix/<purpose>` only for an accepted production hotfix.

## 7. Implement inside the accepted boundary

Preserve the hard constraints in `docs/scope.md` and
`docs/architecture.md`.

Update only authority affected by the change. If implementation reveals that
scope is insufficient, stop implementation and perform the scope transition
first.

Prepared transformations or patches must be inspectable and fail closed when
their expected preimage does not match repository state.

### Agent gate discipline

Work with one coherent change and one concrete gate at a time.

For multi-command gates use:

```bash
bash -lc 'set -euo pipefail; ...'
```

Negative `grep` checks must distinguish an expected absence from a command
failure. When a gate is expected to be green, `done` is sufficient
acknowledgement. Request command output only for a failure, a required concrete
value or local state that cannot otherwise be verified.

When a gate fails, stop at the failure, identify the cause and give the next
corrective action. Do not hide a failed command behind a later `PASS`.

## 8. Focused validation while developing

Use the strongest relevant focused checks.

Common examples:

```bash
uv run agentic-workflow-generator validate-environment
uv run agentic-workflow-generator validate
uv run agentic-workflow-generator validate-artifacts
uv run agentic-workflow-generator validate-agents
uv run agentic-workflow-generator validate-skills
uv run agentic-workflow-generator validate-workflows
uv run agentic-workflow-generator validate-bundles
uv run agentic-workflow-generator validate-setups
uv run agentic-workflow-generator validate-targets
uv run agentic-workflow-generator validate-lockfile
uv run agentic-workflow-generator validate-generated
uv run agentic-workflow-generator coverage
```

For the canonical architecture model and derived diagrams:

```bash
uv run architecture-model check
```

If the pinned Structurizr image is not yet locally available, preparation is an
explicit prerequisite acquisition step:

```bash
uv run architecture-model prepare
```

Normal architecture validation must not silently prepare, pull or fall back to a
different tool version.

Focused checks supplement the full project gates.

## 9. Review repository hygiene

Before staging:

```bash
git diff --check
git status --short --untracked-files=all
git diff
```

Verify every changed file belongs to the branch purpose and that generated or
lockfile changes are understood.

## 10. Pre-commit validation

For implementation or other build-affecting changes, run the full repository
gate:

```bash
bash -lc '
set -euo pipefail

uv run agentic-workflow-generator all
uv run ruff check src tests
uv run mypy
uv run pytest -q
git diff --check
'
```

For documentation-only changes that do not affect executable build state, run
the relevant documentation/structure checks and `git diff --check`; the full
Python gate is not automatic.

When the semantic architecture model or committed derived architecture diagrams
are affected, also run:

```bash
uv run architecture-model check
```

If tracked compiler inputs changed, ensure `.agentic/agentic-lock.json` is
regenerated and valid. If target materialization changed, ensure generated
output and the output manifest are canonical.

Do not run `doctor-strict` before committing an intentional tracked change;
`doctor-strict` requires a clean working tree.

## 11. Stage and commit

Stage explicit intended paths when practical.

Inspect staged state:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
git status --short --untracked-files=all
```

Commit only the coherent outcome.

## 12. Clean-tree validation

After commit:

```bash
bash -lc '
set -euo pipefail

uv run agentic-workflow-generator doctor-strict
test -z "$(git status --porcelain=v1 -uall)"
'
```

A failure blocks push until its cause is understood. Do not weaken validation to
make the gate pass.

## 13. Push and open the pull request

Push the topic branch:

```bash
git push -u origin <topic-branch>
```

Normal pull requests target `development` and use the repository PR template.

GitHub Actions is not part of the normal `development` pull-request gate.
Applicable validation is run locally before push and merge.

The PR must accurately describe scope, architecture, ownership, technology,
deliberately excluded work, validation, generated-output impact and lockfile
impact.

## 14. Verify remote state

Before merge, verify the actual GitHub state:

- base is `development`;
- head is the intended topic branch;
- commit and file sets match the intended outcome;
- the PR is mergeable;
- applicable local validation has passed;
- no remote CI check is expected for a normal PR targeting `development`;
- all review conversations are resolved;
- documentation matches implementation.

If the PR head changes, review and validate the new head.

## 15. Squash merge and synchronize

Normal topic branches are squash-merged:

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

After GitHub confirms the merge:

```bash
bash -lc '
set -euo pipefail

git switch development
git fetch --prune origin
git pull --ff-only origin development
test -z "$(git status --porcelain=v1 -uall)"
'
```

The squash SHA on `development`, not the old topic-branch SHA, is the accepted
integration commit.

Delete a remaining local topic branch only after verifying the merge and
preserving any unique work. Squash merges may require `git branch -D`.

## 16. Re-read accepted state and planning

After every merge:

1. re-read remote `development`;
2. verify the merge commit and merged issue state;
3. read changed authoritative artifacts;
4. re-read direct dependent issues;
5. re-read the parent Goal when relevant;
6. update Goal checklists, dependencies or readiness when accepted state changed
   the plan;
7. re-read `docs/scope.md` and `docs/project-status.md` as relevant to the next
   action;
8. only then choose the next authorized outcome;
9. perform a scope transition first if required.

Completion of one change does not authorize the next deferred capability or an
unresolved dependent issue.

A Goal is complete only when its required subgoals are complete, objective
end-to-end acceptance evidence is satisfied on `development`, relevant project
status is synchronized and required dependencies are resolved.

## Scope-transition workflow

A scope transition uses a dedicated `docs/<purpose>` branch and pull request.
It updates only authority required to admit future work: scope, status and, when
needed, architecture or ADRs.

Implementation begins on a separate branch only after the scope transition is
merged into `development`.

## Release workflow

Release through a deliberate pull request from accepted `development` state to
`production`. Run the required local project validation before opening the
release pull request.

`Agentic CI` runs only for pull requests targeting `production`. The
`Validate generator` remote check must pass before merge.

Keep the release boundary reviewable and create the applicable release tag only
after the release state is accepted.

## Hotfix workflow

A production hotfix branches from `production`, fixes only the urgent released
defect, passes applicable local validation, is reviewed through a pull request
to `production`, passes the required `Validate generator` remote check, and is
then reconciled into `development`.
