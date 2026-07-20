# Guided initialization

Guided initialization shapes a new project from registered, deterministic setup rules.

It does not ask an LLM to invent a workflow. Questions, options, classifications, reasons, and recommendations all come from the setup registry.

## Modes

### Interactive guided initialization

Use this for a human-driven greenfield setup:

~~~bash
scripts/agentic/agentic-gen.sh init --guided
~~~

Interactive mode requires an attached terminal.

The command fails clearly when stdin or stdout is not a TTY:

~~~text
Interactive --guided requires an attached terminal
~~~

The flow is:

~~~text
validate setup registry
select a registered setup
answer registry-defined questions
review the generated setup plan
confirm explicitly
write setup profile and active configuration
~~~

Pressing Enter selects the recommended default when the question has one unambiguous recommended option.

### Deterministic guided initialization

Use this for scripts, CI, repeatable examples, and idempotency validation:

~~~bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup orchestrated-delivery-greenfield
~~~

This mode does not prompt for input.

It selects the registered recommended defaults unless explicit answer overrides are supplied.

### Guided dry-run

Use `--dry-run` to materialize and validate the complete guided result without writing either output file:

~~~bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup orchestrated-delivery-greenfield \
  --dry-run
~~~

Dry-run:

~~~text
materializes the setup profile
materializes the active Agentic configuration
validates both candidates in a temporary directory
prints the complete setup plan
does not request confirmation
does not write or rewrite .agentic/setup-profile.json
does not write or rewrite .agentic/agentic.json
~~~

Answer overrides can be combined with dry-run:

~~~bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup orchestrated-delivery-greenfield \
  --answer target-platforms=opencode-only \
  --dry-run
~~~

Interactive `--guided --dry-run` still requires an attached terminal because the questions must be answered interactively.

`--dry-run` cannot be used with direct `--bundle` initialization.

### Direct bundle initialization

Use direct bundle initialization when no guided project-shaping step is needed:

~~~bash
scripts/agentic/agentic-gen.sh init --bundle orchestrated-delivery
~~~

`--bundle` and `--guided` are mutually exclusive.

## Registered greenfield setups

Three process-oriented greenfield setups are registered.

| Setup | Bundle | Profile | Workflow | Purpose |
|---|---|---|---|---|
| `lean-delivery-greenfield` | `lean-delivery` | `lean-delivery` | `lean-delivery` | Focused lower-risk changes with fewer handoffs |
| `orchestrated-delivery-greenfield` | `orchestrated-delivery` | `microservice-platform` | `orchestrated-delivery` | General delivery with architecture, tests, review, and QA |
| `review-heavy-delivery-greenfield` | `review-heavy-delivery` | `review-heavy-delivery` | `review-heavy-delivery` | High-assurance delivery with review before formal tests |

All three setups default to:

- mode `greenfield`
- targets `opencode` and `vscode-copilot`
- `failFast: true`
- `fallbackAllowed: false`

### Lean delivery flow

`Requirements → Implementer → TestRunner → CodeReviewer → Done`

Failed tests or review return to `Implementer`.

### Orchestrated delivery flow

`Requirements → Architect → Implementer → TestRunner → CodeReviewer → QA → Done`

This is the general process used by the original microservice-platform profile.

### Review-heavy delivery flow

`Requirements → Architect → Implementer → CodeReviewer → TestRunner → QA → Done`

Independent code review occurs before formal test execution.

The registry files are:

- `registry/setups/lean-delivery-greenfield.setup.json`
- `registry/setups/orchestrated-delivery-greenfield.setup.json`
- `registry/setups/review-heavy-delivery-greenfield.setup.json`

For the complete contract and implementation sequence for additional setups,
see [Adding guided setups](adding-guided-setups.md).

## Classification contract

### Recommended

A recommended option is fully represented by the current registered setup and is the default selection.

### Compatible

A compatible option can use the current registered bundle safely, but a more specialized setup, workflow, profile, or capability model may be added later.

Compatible does not mean fallback. The option is explicitly registered and validated.

### Blocked

A blocked option is intentionally unsupported by the selected setup.

Selecting it fails immediately with the registered reason.

The initializer never silently changes a blocked answer to another option.

## Answer overrides

Overrides use the form:

~~~text
--answer question=value
~~~

The option may be repeated.

Generate only OpenCode output:

~~~bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup orchestrated-delivery-greenfield \
  --answer target-platforms=opencode-only
~~~

Generate only VS Code Copilot output:

~~~bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup orchestrated-delivery-greenfield \
  --answer target-platforms=vscode-copilot-only
~~~

Select compatible AI-application and test-first answers:

~~~bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup orchestrated-delivery-greenfield \
  --answer project-type=ai-application \
  --answer delivery-style=test-first
~~~

An override fails when:

~~~text
the question does not exist
the option does not exist
the option is blocked
the value is not in question=value format
--answer is used without --guided
--answer is used with interactive --guided but without --setup
~~~

## Generated files

Guided initialization writes:

~~~text
.agentic/setup-profile.json
.agentic/agentic.json
~~~

### Setup profile

`.agentic/setup-profile.json` records:

~~~text
schema version
setup name and version
mode
selected answers
classification for every answer
registered reason for every answer
selected bundle
selected profile
selected workflow
selected agents
selected skills
selected artifacts
selected targets
fail-fast policy
~~~

The policy requires:

~~~text
failFast: true
fallbackAllowed: false
~~~

### Active configuration

`.agentic/agentic.json` is materialized from the selected bundle and target recommendation.

It becomes the input to resolution, lockfile generation, target generation, manifest generation, and validation.

## Confirmation and cancellation

Interactive mode displays the complete setup plan before writing files.

The user must confirm with `y`.

Any other response cancels the operation and returns a failure:

~~~text
Interactive guided init was cancelled; no files were written
~~~

Cancellation preserves both existing files byte-for-byte and does not rewrite their timestamps.

## Transactional write behavior

The initializer validates the materialized setup profile after writing the candidate outputs.

If validation fails, the previous versions of these files are restored:

~~~text
.agentic/setup-profile.json
.agentic/agentic.json
~~~

There is no partial-success state and no fallback output.

## Validation

Validate the setup registry:

~~~bash
scripts/agentic/agentic-gen.sh validate-setups
~~~

Validate the materialized setup profile:

~~~bash
scripts/agentic/agentic-gen.sh validate-setup-profile
~~~

Validate deterministic guided-init idempotency:

~~~bash
scripts/agentic/agentic-gen.sh validate-init-idempotency \
  --guided \
  --setup orchestrated-delivery-greenfield
~~~

Run the full pipeline:

~~~bash
scripts/agentic/agentic-gen.sh all
scripts/agentic/agentic-gen.sh test-negative
scripts/agentic/agentic-gen.sh doctor-strict
~~~

## Automated coverage

The negative-gate suite covers:

~~~text
unknown setup
non-TTY interactive execution
--answer without explicit setup
invalid answer format
unknown question
blocked option
setup registry drift
setup profile drift
fallback policy violations
guided-init idempotency
interactive default happy path through a pseudo-TTY
interactive cancellation with no file writes
guided dry-run with default recommendations
guided dry-run with target override
guided dry-run file and timestamp preservation
--dry-run without --guided
interactive --guided --dry-run without a TTY
~~~

## Extending the setup registry

The current setups provide three distinct process-oriented compositions.

Milestone 2 can add domain-oriented setups such as AI applications, data
pipelines, web APIs, and libraries. These must be implemented as explicit,
internally consistent registry compositions rather than aliases or fallback
behavior.

Use [Adding guided setups](adding-guided-setups.md) for:

- architecture and registry contracts
- the required implementation sequence
- questionnaire classification rules
- stable test-fixture rules
- milestone 2 planning questions
- the setup definition of done
