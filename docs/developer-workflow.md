# Developer workflow

This document describes the daily development workflow for `agentic-workflow-generator`.

The goal is to keep every change deterministic, validated, and fail-fast.

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
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh <command>
```

Example:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict
```

This is not a fallback. It is an explicit environment choice.

## Environment validation

Validate the required local tools explicitly:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-environment
```

This is a fail-fast preflight.

It checks the selected commands from `PATH` and fails if any required command is missing or cannot run.

It does not install tools, repair `PATH`, or fall back to another implementation.

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
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh test-negative
git status --short
```

Use `doctor-strict` before committing:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict
```

A completed change must end with:

```text
PASS: All negative gate tests passed.
PASS: Working tree is clean.
```

## Safe log pattern

Some commands produce a lot of output.

Use log redirection instead of flooding the terminal:

```bash
LOG="/tmp/agentic-doctor.log"

PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
echo "Log: $LOG"
tail -80 "$LOG"
```

Do not add `exit "$STATUS"` to copy/paste blocks. It can close an interactive terminal session.

## Common commands

### Validate active config

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate
```

Validates `.agentic/agentic.json` against `.agentic/schemas/agentic.schema.json`.

This requires working `node` and `npx`.

### Initialize from bundle

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh init --bundle orchestrated-delivery
```

Materializes `.agentic/agentic.json` from the selected bundle.

### Validate init idempotency

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-init-idempotency --bundle orchestrated-delivery
```

Ensures repeated `init --bundle` runs do not create config drift.

### Validate bundle registry

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-bundles
```

Checks that registered bundles are valid and complete.

### Check capability coverage

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh coverage
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
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all
```

Runs the full happy-path pipeline.

### Validate generated output

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-generated
```

Checks target output for enabled targets.

### Generate and validate lockfile

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh lock
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-lockfile
```

Run this when tracked generator inputs change.

### Generate and validate output manifest

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh manifest
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-manifest
```

The manifest records generated files, hashes, byte sizes, target ownership, and active bundle metadata.

### Run negative gates

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh test-negative
```

The negative gate suite intentionally breaks contracts to prove that validators fail closed.

## Preferred check sequence

For a normal code or registry change:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh test-negative
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict
```

For noisy runs:

```bash
LOG="/tmp/agentic-all.log"
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"
```

Then:

```bash
LOG="/tmp/agentic-negative.log"
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh test-negative > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"
```

Then:

```bash
LOG="/tmp/agentic-doctor.log"
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"
```

## Commit workflow

Before committing:

```bash
git status --short
```

Regenerate lockfile if needed:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh lock
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-lockfile
```

Run strict doctor:

```bash
LOG="/tmp/agentic-final-doctor.log"
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"
```

Commit only when `Status: 0`.

```bash
git add <intentional-files>
git commit -m "<clear commit message>"
```

After commit:

```bash
LOG="/tmp/agentic-post-commit-doctor.log"
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"

git status --short
```

The final `git status --short` should be empty.

## Handling generated output drift

If `doctor-strict` reports generated output drift, run:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all
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
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh lock
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-lockfile
```

Commit `.agentic/agentic-lock.json` with the source change that caused it.

Do not commit unexplained lockfile drift.

## Handling manifest drift

If manifest validation fails, regenerate and validate it:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh manifest
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-manifest
```

If it still fails, inspect the specific error.

Common causes:

```text
generated file hash changed
generated file byte size changed
generated file missing
target owned path contains unmanaged file
manifest bundle metadata no longer matches registry bundle
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
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-bundles
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh init --bundle orchestrated-delivery
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-init-idempotency --bundle orchestrated-delivery
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all
```

Then run negative gates and doctor:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh test-negative
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict
```

## Working with workflows

After changing a workflow:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-workflows
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-bundles
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all
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
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-agents
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-skills
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh coverage
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all
```

Agent capability changes must be covered by skill capabilities.

Skill capability duplicates must fail validation.

## Working with targets

After changing a target adapter:

```bash
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-targets
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh all
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh validate-manifest
```

Target adapters define generated output ownership.

Owned paths must be safe relative paths.

## Done criteria

A change is done when:

```text
all passes
negative gates pass
doctor-strict passes
lockfile is valid
manifest is valid
working tree is clean after commit
```

Use this final check:

```bash
LOG="/tmp/agentic-done.log"
PATH="/usr/bin:/bin:$PATH" scripts/agentic/agentic-gen.sh doctor-strict > "$LOG" 2>&1
STATUS="$?"

echo "Status: $STATUS"
tail -80 "$LOG"

git status --short
```
