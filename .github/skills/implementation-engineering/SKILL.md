---
name: "implementation-engineering"
description: "Use when implementing or refactoring approved behavior and updating tests while preserving requirement and architecture alignment."
---

# Implementation Engineering Skill

## Purpose

Implement the smallest complete change that satisfies approved requirements and architecture decisions, including the
tests needed to validate the change.

## Required Inputs

Review:

- the approved Requirements artifact
- applicable ArchitectureDecision artifacts
- current source code and tests
- repository conventions and validation commands
- previous failed gate evidence when performing remediation

Do not begin when the required approved artifacts are absent or contradictory.

## Working Method

1. Trace the requested change to approved requirements and acceptance criteria.
2. Inspect the existing implementation before editing.
3. Identify the smallest coherent change set.
4. Preserve established boundaries and interfaces unless an approved decision changes them.
5. Implement behavior with clear names, focused units, and explicit error handling.
6. Remove duplication introduced by the change.
7. Refactor only where necessary to make the requested change safe and maintainable.
8. Add or update tests for changed behavior, boundaries, failures, and regressions.
9. Run the relevant validation available to the Implementer.
10. Record changed files, design deviations, validation performed, and remaining risks.

Do not broaden scope without an updated approved requirement.

## Implementation Rules

The implementation must:

- remain traceable to approved requirements
- preserve unrelated behavior
- fail clearly instead of silently degrading
- avoid hidden fallback behavior
- avoid speculative abstractions
- keep public contracts and error behavior explicit
- update tests when observable behavior changes
- document unavoidable deviations from approved artifacts

Refactoring must preserve behavior unless the approved requirement explicitly changes it.

## Agent Boundaries

The Implementer may modify product code and tests.

The Implementer must not:

- change workflow routing
- self-approve code quality, QA, or release
- claim validation that was not executed
- hide failed commands or known risks
- reinterpret approved requirements without escalation

A `PASS` ImplementationReport means implementation work is complete enough for independent validation. It is not release
approval.

## Fail-Closed Rules

Return `PASS` only when:

- the approved change is implemented
- required tests are updated
- available implementation validation was run
- known risks and unexecuted validation are disclosed

Return `FAIL` when implementation or implementation-level validation demonstrates that the approved behavior is not
satisfied.

Return `BLOCKED` when approved inputs, dependencies, tools, credentials, environments, or required decisions are
unavailable.

## Output Requirements

Create the ImplementationReport artifact using exactly these sections:

- `# Implementation Report`
- `## Status`
- `## Summary`
- `## Files Changed`
- `## Implementation Notes`
- `## Validation Performed`
- `## Known Risks`
- `## Handoff Target`

Do not describe the implementation as independently approved.
