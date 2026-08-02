# Project workflow

This document is the sole authoritative operational workflow for development of
`agentic-workflow-generator`. It owns the delivery sequence and the concrete
commands used to execute it.

Mandatory rules are defined in `docs/governance.md`. Accepted work is defined in
`docs/scope.md`. Current state and priority are defined in
`docs/project-status.md`. Architecture and technology authority remain in
`docs/architecture.md`, `docs/adr/` and `docs/tech-stack.md`.

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

## 2. Classify the work

Proceed directly only when the requested outcome is already inside
`docs/scope.md`.

Use a dedicated scope-transition pull request first when the work would add a
new product capability, target platform, runtime responsibility, architecture
constraint or other behavior not already accepted.

Create or supersede an ADR when a significant architecture or technology
decision needs durable rationale.

## 3. Define one coherent outcome

Before implementation, state:

1. the exact outcome;
2. why it is inside accepted scope;
3. affected authoritative sources;
4. deliberately excluded related work;
5. acceptance criteria;
6. validation required.

Do not bundle unrelated cleanup, speculative abstractions or neighboring
capabilities.

## 4. Synchronize `development`

Use Bash for fail-fast command blocks:

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

## 5. Create a topic branch

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

## 6. Implement inside the accepted boundary

Preserve the hard constraints in `docs/scope.md` and
`docs/architecture.md`.

Update only authority affected by the change. If implementation reveals that
scope is insufficient, stop implementation and perform the scope transition
first.

Prepared transformations or patches must be inspectable and fail closed when
their expected preimage does not match repository state.

## 7. Focused validation while developing

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

For domain diagrams:

```bash
uv run render-domain-diagrams
uv run render-domain-diagrams --check
```

Focused checks supplement the full project gates.

## 8. Review repository hygiene

Before staging:

```bash
git diff --check
git status --short --untracked-files=all
git diff
```

Verify every changed file belongs to the branch purpose and that generated or
lockfile changes are understood.

## 9. Full pre-commit validation

For a normal repository change, run:

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

When authoritative domain diagrams are affected, also run:

```bash
uv run render-domain-diagrams --check
```

If tracked compiler inputs changed, ensure `.agentic/agentic-lock.json` is
regenerated and valid. If target materialization changed, ensure generated
output and the output manifest are canonical.

Do not run `doctor-strict` before committing an intentional tracked change;
`doctor-strict` requires a clean working tree.

## 10. Stage and commit

Stage explicit intended paths when practical.

Inspect staged state:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
git status --short --untracked-files=all
```

Commit only the coherent outcome.

## 11. Clean-tree validation

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

## 12. Push and open the pull request

Push the topic branch:

```bash
git push -u origin <topic-branch>
```

Normal pull requests target `development` and use the repository PR template.

The PR must accurately describe scope, architecture, ownership, technology,
deliberately excluded work, validation, generated-output impact and lockfile
impact.

## 13. Verify remote state

Before merge, verify the actual GitHub state:

- base is `development`;
- head is the intended topic branch;
- commit and file sets match the intended outcome;
- the PR is mergeable;
- required checks are green;
- all review conversations are resolved;
- documentation matches implementation.

If the PR head changes, review and validate the new head.

## 14. Squash merge and synchronize

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

## 15. Stop at the next scope gate

After every merge:

1. re-read `docs/scope.md`;
2. re-read `docs/project-status.md`;
3. inspect the accepted `development` state;
4. choose the next authorized outcome;
5. perform a scope transition first if required.

Completion of one change does not authorize the next deferred capability.

## Scope-transition workflow

A scope transition uses a dedicated `docs/<purpose>` branch and pull request.
It updates only authority required to admit future work: scope, status and, when
needed, architecture or ADRs.

Implementation begins on a separate branch only after the scope transition is
merged into `development`.

## Release workflow

Release through a deliberate pull request from accepted `development` state to
`production`. Run the required project validation, keep the release boundary
reviewable and create the applicable release tag only after the release state is
accepted.

## Hotfix workflow

A production hotfix branches from `production`, fixes only the urgent released
defect, passes applicable validation, is reviewed into `production`, and is then
reconciled into `development`.
