# Project Workflow

## Authority

This document defines the authoritative operational workflow for development of
`agentic-workflow-generator`.

It explains how accepted project intent moves from scope and status into a topic
branch, implementation, validation, pull request, accepted `development` state, and
eventually a release on `production`.

Governance rules are defined in [`governance.md`](governance.md).

Accepted implementation scope is defined in
[`scope.md`](scope.md).

Current project state and next accepted priority are defined in
[`docs/project-status.md`](project-status.md).

Detailed local commands and validation procedures are defined in
[`developer-workflow.md`](developer-workflow.md).

This document applies those sources as one repeatable development sequence.

If this document conflicts with an authoritative concern-specific source, the
concern-specific source wins.

## Core principle

Work proceeds from accepted repository state, not from assumptions, chat
history, local notes, deferred ideas, generated summaries, or AI memory.

The normal flow is:

```text
accepted development state
      |
      v
read scope + status
      |
      v
scope decision required?
   |             |
  yes            no
   |             |
scope PR         |
   |             |
   +--------> topic branch
                  |
                  v
              implement
                  |
                  v
         pre-commit validate
                  |
                  v
                commit
                  |
                  v
       clean-tree doctor-strict
                  |
                  v
                push
                  |
                  v
             pull request
                  |
                  v
          CI + review
                  |
                  v
           squash to development
                  |
                  v
          sync local state
                  |
                  v
          next scope gate
```

No implementation begins merely because a future direction appears reasonable.

## 1. Start from authoritative state

Before planning or changing code, inspect at minimum:

* [`scope.md`](scope.md) for accepted scope and exclusions.
* [`docs/project-status.md`](project-status.md) for current state and next
  accepted priority.
* [`governance.md`](governance.md) for delivery and change-control rules.
* [`architecture.md`](architecture.md) for architecture principles and authority.
* [`core-domain-model.md`](core-domain-model.md) when domain structure is
  affected.
* Relevant ADRs under [`adr/`](adr/).
* Relevant registry definitions and schemas.
* Relevant compiler source and tests.
* Relevant target adapters, generated-output contracts, lockfile rules, and
  manifests when affected.

Repository state on `development` is the accepted next-state baseline.

Repository state on `production` is the accepted stable/release baseline.

Topic branches and open pull requests are proposals, not accepted truth.

Chat conversations, AI output, local notes, issues, generated summaries, and
other coordination artifacts are not authoritative unless their result is
accepted into the repository through the normal change process.

## 2. Classify the proposed work

Before creating a branch, determine which category the work belongs to.

### Work inside accepted scope

Proceed to a topic branch when the requested outcome is already authorized by
`docs/scope.md`.

Examples include:

* Implementing an existing post-migration hardening acceptance criterion.
* Hardening existing artifact contracts.
* Completing accepted workflow semantics.
* Correcting existing profiles, bundles, setups, agents, skills, or registry
  contracts.
* Fixing defects in the existing compiler.
* Correcting semantic loss in an existing target adapter.
* Strengthening fail-fast validation.
* Refactoring without changing accepted ownership or architecture.
* Adding tests for accepted behavior.
* Updating authoritative documentation to match accepted implementation.

### Scope change required

A dedicated scope decision is required before implementation when the work
would introduce something not authorized by `docs/scope.md`.

Examples include:

* A new target platform.
* Autonomous runtime workflow orchestration.
* Runtime-context generation.
* Remote registry or marketplace behavior.
* Dynamic plugin discovery.
* Generic plugin infrastructure.
* A template engine acting as another rendering authority.
* A generic target DSL.
* Model hosting or model-training infrastructure.
* Distributed workflow execution.
* Replay functionality.
* A web UI.
* New retry, escalation, or artifact-invalidation semantics not already
  accepted.
* A new product capability outside the current compiler boundary.
* A change to a hard architectural constraint.

The scope decision must be accepted into `development` before implementation begins.

### Architecture decision required

Create or update an ADR when the work makes a significant architectural
decision that needs durable rationale, especially when:

* reasonable alternatives exist;
* dependency direction changes;
* ownership changes;
* compiler authority changes;
* canonical representations change;
* deployment or runtime topology changes materially;
* an existing accepted architectural decision is replaced.

An ADR does not replace a required scope transition.

## 3. Define one coherent outcome

Each topic branch and pull request must have one primary outcome.

Before implementation, establish:

1. What exact outcome is being delivered?
2. Why is it inside accepted scope?
3. Which authoritative sources are affected?
4. What is deliberately out of scope?
5. What acceptance criteria prove completion?
6. How will the change be validated?

Do not bundle unrelated cleanup, speculative abstractions, neighboring
capabilities, future infrastructure, or opportunistic improvements.

Prefer the smallest coherent change that proves the accepted requirement.

## 4. Synchronize the integration branch

Normal work starts from the current remote `development` state.

First ensure there is no uncommitted work that would be lost.

Typical synchronization:

```bash
git switch development
git fetch origin --tags
git pull --ff-only
git status --short --branch
```

The working tree should be understood and clean before creating the topic
branch.

Do not merge a squash-merged topic branch back into local `development`.

After a squash merge, synchronize local `development` from `origin/development`.

## 5. Create a topic branch

Branch from synchronized `development`.

Allowed normal prefixes:

* `feat/` — new accepted behavior.
* `fix/` — defect correction.
* `docs/` — documentation, scope, or governance work.
* `chore/` — repository or build maintenance.
* `refactor/` — behavior-preserving restructuring.
* `test/` — test-only work.
* `hotfix/` — emergency correction based on `production`.

Examples:

```text
docs/artifact-hardening-scope
feat/artifact-provenance
fix/workflow-blocked-routing
refactor/compiler-validation
test/target-routing-contracts
chore/ci-toolchain
```

Use a branch name that describes the intended outcome rather than a temporary
implementation detail.

## 6. Implement within the accepted boundary

During implementation:

* Preserve `CompiledComposition` as the canonical compiler composition.
* Preserve `.agentic/agentic.json` as the persistent active serialization.
* Keep bundle-owned agent instances and role bindings as concrete runtime
  authority.
* Keep effective permissions on agent instances.
* Keep capabilities, skills, produced artifacts, responsibilities, and
  guardrails on role bindings.
* Preserve state-owner and controller invariants.
* Preserve explicit separation of duties.
* Keep target adapters dependent on canonical compiled composition rather than
  independently reinterpreting registry input.
* Keep generated output deterministic and canonical.
* Keep validation fail-fast.
* Do not introduce compatibility projections.
* Do not introduce silent degradation.
* Do not introduce fallback authority.
* Add only dependencies and abstractions required by the accepted outcome.
* Update authoritative documentation when the truth it owns changes.
* Update authoritative PlantUML sources and rendered diagrams when architecture
  changes.
* Add or supersede ADRs when significant architectural rationale changes.
* Add tests for introduced or changed behavior and invariants.

If implementation reveals that accepted scope is insufficient, stop
implementation and return to the scope-transition step.

Do not hide a scope expansion inside an implementation pull request.

## 7. Apply prepared patches safely

When applying a prepared patch, validate it before modifying the working tree:

```bash
git apply --check path/to/change.patch
git apply path/to/change.patch
```

Do not apply a patch that fails `git apply --check`.

After applying a patch, inspect the actual resulting diff.

Generated patches and AI-produced changes are proposals until inspected and
validated.

## 8. Validate while developing

Validation is fail-fast.

A failed required gate blocks progress until its cause is understood and
corrected.

Use focused validation while developing.

The normal full happy-path pre-commit validation is:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
uv run pytest -q
```

The `PATH` prefix selects the project's known-good system toolchain explicitly.
It is not fallback behavior.

Additional focused commands are defined in
[`developer-workflow.md`](developer-workflow.md).

Examples include:

```text
validate-environment
validate
validate-bundles
validate-workflows
validate-agents
validate-skills
validate-targets
coverage
validate-lockfile
validate-generated
```

Use the strongest relevant focused checks for the concern being changed.

Focused checks supplement the full project gates; they do not replace them.

## 9. Review repository hygiene

Before staging or committing, inspect:

```bash
git diff --check
git status --short
git diff
```

Verify that:

* every changed file belongs to the branch purpose;
* no unrelated cleanup is included;
* no local or temporary files leaked into the change;
* generated changes are intentional;
* lockfile changes are understood;
* architecture and documentation impact is represented;
* no hidden scope expansion occurred.

Remember that normal `git diff` does not display untracked file contents.

## 10. Stage only the intended change

Stage explicit paths when practical.

Before commit, inspect the staged surface:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached --name-only
git status --short
```

Verify that:

* every staged file belongs to the coherent branch purpose;
* all intended new files are staged;
* unrelated working-tree changes are not being hidden;
* generated files are included only when intentionally affected;
* `.agentic/agentic-lock.json` changes have an understood source;
* `.agentic/generated/output-manifest.json` and target output changes correspond
  to canonical generation when affected.

Do not use broad staging merely for convenience when it makes the reviewed
change harder to understand.

## 11. Pre-commit validation

Before committing a normal code, registry, schema, compiler, or generated-output
change, run:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
uv run pytest -q
```

If tracked generator inputs changed, ensure the lockfile is regenerated and
valid.

If target materialization is affected, ensure generated output is canonical.

Do not run `doctor-strict` while the intended change is still tracked or staged.

`doctor-strict` intentionally requires a clean working tree and therefore acts
as the final post-commit repository validation.

## 12. Commit discipline

Commits on topic branches should describe the coherent outcome.

Typical subjects:

```text
docs: establish project workflow
feat: add artifact provenance contract
fix: preserve blocked workflow routing
refactor: centralize composition validation
test: cover role binding invariants
chore: fix CI tool bootstrap
```

A topic branch may contain multiple development commits while work is in
progress.

Normal topic branches are squash-merged into `development`, so permanent integration
history receives one coherent accepted change.

Never force-push `development` or `production`.

If an already-pushed topic commit must be amended, use:

```bash
git push --force-with-lease
```

and only on the topic branch.

## 13. Run the clean-tree quality gate

After commit, run the final repository-level local gate:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict
```

A successful completed run must include:

```text
PASS: verify-quiet completed successfully.
pytest reports all tests passed.
PASS: Working tree is clean.
```

`doctor-strict` verifies the committed repository state.

If it produces or detects drift, understand the cause before continuing.

Do not weaken the validator or ignore drift merely to obtain a passing result.

## 14. Push and open the pull request

After the clean-tree gate passes:

```bash
git push -u origin <topic-branch>
```

Normal pull requests target `development`.

The pull request must use the repository PR template and explain:

* one clear purpose;
* scope impact;
* architecture impact;
* ownership impact;
* technology impact;
* deliberately excluded related work;
* validation actually performed;
* generated-output impact;
* lockfile impact.

The pull request remains a proposal until merged.

## 15. Review the actual remote change

Review the GitHub PR state, not only the local working tree.

Before merge, verify:

* base branch is `development` for normal work;
* head branch is the intended topic branch;
* commit and file sets match the intended outcome;
* GitHub reports the PR as mergeable;
* required GitHub Actions checks are green;
* local validation evidence is accurate;
* authoritative documentation matches the implementation;
* scope has not expanded silently;
* architecture remains consistent;
* role and ownership boundaries remain valid;
* tests cover introduced or changed invariants;
* generated output is canonical when affected;
* lockfile state is valid when affected;
* all review conversations are resolved.

If the PR head changes after review, review the new head and rerun applicable
checks before merge.

A locally green branch is not sufficient if required remote CI fails.

## 16. Merge normal work

Normal topic branches are squash-merged into `development`.

Typical command:

```bash
gh pr merge <PR_NUMBER> --squash --delete-branch
```

The resulting squash commit on `development` is the accepted repository state.

The original topic-branch commit SHA is not the authoritative integration commit
after squash merge.

Do not continue work from assumptions based on the old topic branch.

## 17. Synchronize after merge

After confirming that the PR is merged:

```bash
git switch development
git fetch origin --tags
git pull --ff-only
git status --short --branch
```

The local `development` branch must reflect the accepted remote integration state before
new work begins.

Delete any remaining local topic branch only after verifying that no unique work
needs to be preserved.

Because squash merge does not preserve the topic commit as an ancestor, normal
safe branch deletion may refuse. Inspect the situation before forcing local
deletion.

## 18. Stop at the next scope gate

Completing one accepted change does not automatically authorize the next one.

After every merge:

1. Re-read `docs/scope.md`.
2. Re-read `docs/project-status.md`.
3. Inspect the newly accepted repository state.
4. Determine the next authorized outcome.
5. Perform a scope transition first if required.

The sequence is:

```text
accepted implementation
        |
        v
current status
        |
        v
next priority
        |
        v
inside accepted scope?
    |          |
   yes         no
    |          |
 topic      scope PR
 branch        |
    |          v
    |      accepted development
    |          |
    +----------+
        |
        v
next implementation
```

Do not begin a deferred capability merely because the previous task is
complete.

## 19. Scope-transition workflow

When the logical next change lies outside accepted scope:

```text
new requirement
      |
      v
scope analysis
      |
      v
docs/<scope-purpose>
      |
      v
update scope
      |
      +--> update project status
      |
      +--> architecture / ADR if required
      |
      v
pull request -> development
      |
      v
review + validation
      |
      v
squash merge
      |
      v
new accepted development state
      |
      v
separate implementation branch
```

A scope-transition PR should contain the authority changes needed to admit the
future implementation.

It must not hide the implementation itself in the same PR.

Before accepting a scope transition, verify:

* the current phase is represented accurately;
* the concrete problem is stated;
* the new responsibility is explicit;
* in-scope work is explicit;
* out-of-scope work remains explicit;
* architecture impact is understood;
* technology impact is understood;
* acceptance criteria are measurable;
* the proposed implementation can be bounded.

## 20. Architecture and ADR workflow

When an accepted change affects architecture:

1. Identify the affected boundary.
2. Inspect the authoritative architecture source.
3. Determine whether an ADR is required.
4. Update the authoritative PlantUML source when the model changes.
5. Update affected rendered diagrams in the same change.
6. Update architecture documentation.
7. Ensure implementation and tests match the decision.

Significant decisions belong under `docs/adr/`.

Accepted ADR history is not silently rewritten.

A later decision supersedes an earlier accepted ADR.

## 21. Generated output and lockfile discipline

Generated state is part of the compiler contract.

### Lockfile

When compiler inputs change:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator lock
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-lockfile
```

Commit lockfile changes only when they are the deterministic result of an
intentional compiler-input change.

Do not commit unexplained lockfile drift.

### Target output

When target materialization is affected:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator generate
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-generated
```

Generated target output must match the canonical composition and output
manifest.

Do not hand-edit generated output as an alternate source of truth.

## 22. Registry-specific validation

Use focused validation when changing registry concerns.

### Bundles

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-bundles
```

### Workflows

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-workflows
```

### Agents

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-agents
```

### Skills

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-skills
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator coverage
```

### Targets

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-targets
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-generated
```

After focused validation, the full applicable project gates still apply.

## 23. Release workflow

`production` represents stable/release-ready or released state.

A normal release promotes an accepted `development` state through a deliberate pull
request:

```text
accepted development
     |
     v
release-readiness review
     |
     v
pull request: development -> production
     |
     v
required validation
     |
     v
review
     |
     v
production
     |
     v
release tag
```

Before release:

* the intended `development` state must be complete and reviewable;
* required CI and local validation must pass;
* release-related documentation or versioning must be updated when required;
* unrelated future work must not be bundled into the release;
* the release boundary must remain explicit and reviewable.

Normal feature development does not occur directly on `production`.

## 24. Hotfix workflow

Emergency fixes to stable/released state may branch from `production` using
`hotfix/`.

```text
production
 |
 v
hotfix/<purpose>
 |
 v
implement narrowly
 |
 v
validate
 |
 v
pull request -> production
 |
 v
merge / release
 |
 v
reconcile same logical fix into development
```

A hotfix must:

1. Address a real stable/release defect.
2. Remain narrowly focused.
3. Be validated against released state.
4. Use the pull-request process.
5. Preserve architecture and fail-fast rules.
6. Be reconciled into `development`.

A hotfix is not a shortcut for normal feature development.

## 25. Tool and AI usage

Humans, coding agents, AI assistants, IDE automation, and other tools follow the
same workflow.

Tools may:

* inspect;
* analyze;
* propose;
* draft;
* generate;
* patch;
* test;
* review.

They do not own project truth.

Rules:

* Inspect current repository state when exact state matters.
* Read scope and status before implementing.
* Treat generated changes as proposals.
* Inspect generated patches before accepting them.
* Validate generated code with the same gates as manually written code.
* Do not accept a capability, dependency, technology, or architecture merely
  because a tool recommends it.
* Do not treat conversation memory as repository authority.
* Do not weaken validation to make generated work pass.
* Do not introduce fallback behavior where the project requires fail-fast
  semantics.

The accepted repository state remains authoritative.

## 26. Fail-fast conditions

Stop the current flow and resolve the issue before continuing when:

* the working tree contains unexplained changes;
* the branch is based on unexpected repository state;
* a patch fails validation;
* `git diff --check` fails;
* required tests fail;
* registry validation fails;
* schema validation fails;
* capability coverage fails;
* lockfile validation fails;
* generated output is non-canonical;
* `doctor-strict` fails;
* the implementation requires something explicitly out of scope;
* a hard architectural constraint would need to change without prior approval;
* authoritative documentation and implementation disagree;
* the PR contains unrelated files;
* CI fails;
* GitHub reports a real merge conflict;
* review reveals that the branch no longer has one coherent purpose.

Do not bypass a failed gate merely to reach commit or merge.

## 27. Working checklist

Use this checklist for normal topic work.

### Before implementation

* [ ] `development` is synchronized with `origin/development`.
* [ ] Working tree is clean or all local work is understood and protected.
* [ ] `docs/scope.md` authorizes the change.
* [ ] `docs/project-status.md` supports the next action.
* [ ] Relevant architecture and ADRs have been inspected.
* [ ] Branch purpose is one coherent outcome.
* [ ] Explicit out-of-scope work is identified.
* [ ] A scope or architecture decision has been made first if required.

### During implementation

* [ ] Work remains inside accepted scope.
* [ ] Canonical compiler authority is preserved.
* [ ] Agent-instance and role-binding ownership remains explicit.
* [ ] Fail-fast behavior is preserved.
* [ ] No compatibility or fallback path is introduced.
* [ ] Only required dependencies and abstractions are introduced.
* [ ] Tests cover new or changed behavior and invariants.
* [ ] Relevant authoritative documentation is updated.
* [ ] Diagrams and ADRs are updated when architecture changes.

### Before commit

* [ ] Focused checks pass.
* [ ] `PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all` passes.
* [ ] `uv run pytest -q` passes.
* [ ] Lockfile is valid when affected.
* [ ] Generated target output is canonical when affected.
* [ ] `git diff --check` passes.
* [ ] Intended files are staged.
* [ ] `git diff --cached --check` passes.
* [ ] Staged stat and filenames match the branch purpose.
* [ ] No unrelated or local-environment files are staged.

### After commit

* [ ] Working tree is clean.
* [ ] `doctor-strict` passes on the committed state.
* [ ] No unexplained generated or lockfile drift exists.

### Before merge

* [ ] PR base/head are correct.
* [ ] Remote PR diff matches the reviewed change.
* [ ] PR is mergeable.
* [ ] Required CI passes.
* [ ] Scope impact is explicit.
* [ ] Architecture impact is explicit.
* [ ] Ownership impact is explicit.
* [ ] Technology impact is explicit.
* [ ] Validation evidence is accurate.
* [ ] Generated and lockfile impact is understood.
* [ ] Review conversations are resolved.
* [ ] Latest PR head has been reviewed.

### After merge

* [ ] PR is confirmed merged.
* [ ] Local `development` is synchronized with `origin/development`.
* [ ] Working tree is clean.
* [ ] Obsolete topic branch is removed safely.
* [ ] `docs/scope.md` is re-read.
* [ ] `docs/project-status.md` is re-read.
* [ ] The next authorized outcome is selected from accepted repository state.
* [ ] No new implementation begins before any required scope decision.
