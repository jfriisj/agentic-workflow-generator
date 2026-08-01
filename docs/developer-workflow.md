# Developer workflow

This document describes the daily development workflow for `agentic-workflow-generator`.

The goal is to keep every change deterministic, validated, and fail-fast.

Delivery governance, accepted scope, branch semantics, pull-request rules and
release policy are defined by `docs/governance.md` and `docs/scope.md`.

This document is the operational command guide. If it conflicts with
`docs/governance.md`, governance is authoritative.

## Core rule

This project does not use fallback behavior.

If a required tool, file, schema, generated artifact, lockfile entry, or registry contract is missing or broken, the command must fail with a clear error.

```text
No silent degradation.
No skipped validation.
No fallback paths.
Fail fast with an explicit error.
```

## Recommended environment command prefix

On some machines, `node` from another environment can appear before the system `node` in `PATH`.

For this repository, use the known-good system path when running validation:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator <command>
```

Example:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict
```

This is not a fallback. It is an explicit environment choice.

## Environment validation

Validate the required local tools explicitly:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-environment
```

This is a fail-fast preflight.

The public top-level CLI routes directly to the typed environment boundary. The application service owns the six required command contracts, while the policy-free process adapter resolves each command through the explicitly supplied `PATH` and runs its version command in the repository root.

Each version command has a fixed 30-second timeout. Validation fails with stable `AWG-ENVIRONMENT-*` diagnostics if a required executable is missing, cannot execute, times out or returns a non-zero exit code.

It does not install tools, repair `PATH`, search alternative locations, or fall back to another implementation.

Expected checked commands:

```text
bash
git
python
node
npx
```

## Daily loop

Use this loop while developing:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
uv run pytest -q
git status --short
```

During development, run the happy-path and pytest checks before committing:

~~~bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
uv run pytest -q
~~~

A completed change must end with:

```text
pytest reports all tests passed
PASS: Working tree is clean.
```

## Safe log pattern

Some commands produce a lot of output.

Use log redirection instead of flooding the terminal:

```bash
LOG="/tmp/agentic-doctor.log"

PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
echo "Log: $LOG"
tail -80 "$LOG"
```

Do not add `exit "$STATUS"` to copy/paste blocks. It can close an interactive terminal session.

## Common commands

### Validate active config

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate
```

Validates `.agentic/agentic.json` against `.agentic/schemas/agentic.schema.json`.

This requires working `node` and `npx`.

### Initialize from bundle

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator init --bundle orchestrated-delivery
```

Materializes `.agentic/agentic.json` from the selected bundle.

### Validate init idempotency

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-init-idempotency --bundle orchestrated-delivery
```

Ensures repeated `init --bundle` runs do not create config drift.

### Validate bundle registry

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-bundles
```

Checks that registered bundles are valid and complete.

### Check capability coverage

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator coverage
```

Healthy output should include:

```text
Missing skill coverage:
  none

Unused skill capabilities:
  none

Duplicate skill capabilities:
  none
```

### Generate everything

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
```

Runs the full happy-path pipeline.

### Validate generated output

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-generated
```

Checks target output for enabled targets.

### Generate and validate lockfile

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator lock
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-lockfile
```

Run this when tracked generator inputs change. The public top-level CLI routes to the typed lockfile generation and validation boundaries; lockfile semantics remain in the application layer.

### Materialize and validate target output

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator generate
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-generated
```

Materialization writes all enabled target files and the manifest transactionally. The manifest records the canonical composition hash, target ownership, file hashes, and byte sizes.

### Run the typed test suite

```bash
uv run pytest -q
```

The focused pytest suites exercise success paths and domain-owned fail-closed contracts directly.

## Preferred check sequence

For a normal code or registry change before commit:

~~~bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
uv run pytest -q
~~~

After committing, run `doctor-strict` on the clean topic branch before
push or pull request. `verify` and `doctor-strict` intentionally reject
any tracked or staged working-tree changes.

For noisy runs:

```bash
LOG="/tmp/agentic-all.log"
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"
```

Then:

```bash
LOG="/tmp/agentic-pytest.log"
uv run pytest -q > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"
```

Then:

```bash
LOG="/tmp/agentic-doctor.log"
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"
```

## Commit workflow

Normal work must already be on a topic branch created from the latest `dev`.
Do not use this section to commit ordinary work directly to `main` or `dev`.

Before committing:

```bash
git status --short
```

Regenerate lockfile if needed:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator lock
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-lockfile
```

Run pre-commit validation:

~~~bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
uv run pytest -q
~~~

Commit only when the pre-commit validation completes successfully.

```bash
git add <intentional-files>
git commit -m "<clear commit message>"
```

After commit:

```bash
LOG="/tmp/agentic-post-commit-doctor.log"
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"

git status --short
```

The final `git status --short` should be empty.

After the topic branch is validated and pushed, open a pull request targeting
`dev`. Review and merge rules are defined by `docs/governance.md`.

After merge, resynchronize from the accepted integration state before starting
new work:

~~~bash
git switch dev
git pull --ff-only
git status --short --branch
~~~

## Handling generated output drift

If `doctor-strict` reports generated output drift, run:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
```

Then check status:

```bash
git status --short
```

Review the changed generated files.

Commit them only if the drift is intentional.

## Handling lockfile drift

If the lockfile changes after a valid source change:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator lock
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-lockfile
```

Commit `.agentic/agentic-lock.json` with the source change that caused it.

Do not commit unexplained lockfile drift.

## Handling target-output drift

If manifest validation fails, regenerate and validate it:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator generate
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-generated
```

If it still fails, inspect the specific error.

Common causes:

```text
generated file hash changed
generated file byte size changed
generated file missing
target owned path contains unmanaged file
committed manifest differs from the canonical materialization plan
```

## Handling config schema validation failures

Config validation is fail-fast.

If `node` or `npx` is broken, validation should fail clearly.

Check the selected commands:

```bash
command -v node
node --version

command -v npx
npx --version
```

The project should not skip schema validation or switch to syntax-only validation.

## Working with bundles

After changing a bundle:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-bundles
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator init --bundle orchestrated-delivery
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-init-idempotency --bundle orchestrated-delivery
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
```

Then run the typed pytest suite and doctor:

```bash
uv run pytest -q
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict
```

## Working with workflows

After changing a workflow:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-workflows
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-bundles
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
```

Workflow changes may affect:

```text
gates
routes
artifact requirements
bundle completeness
generated agent instructions
lockfile
output manifest
```

## Working with agents and skills

After changing an agent or skill:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-agents
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-skills
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator coverage
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
```

Agent capability changes must be covered by skill capabilities.

Skill capability duplicates must fail validation.

## Working with targets

After changing a target adapter:

```bash
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-targets
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator all
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator validate-generated
```

Target adapters define generated output ownership.

Owned paths must be safe relative paths.

## Done criteria

A change is done when:

```text
all passes
pytest reports all tests passed
doctor-strict passes
lockfile is valid
generated target output is canonical
working tree is clean after commit
```

After committing, use this final clean-tree check:

```bash
LOG="/tmp/agentic-done.log"
PATH="/usr/bin:/bin:$PATH" uv run agentic-workflow-generator doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"

git status --short
```
