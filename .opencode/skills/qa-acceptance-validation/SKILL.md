---
name: "qa-acceptance-validation"
description: "Use when verifying acceptance criteria against independent test, review, and artifact evidence."
---

# QA Acceptance Validation Skill

## Purpose

Determine whether every required acceptance criterion is supported by complete, current, and internally consistent
evidence.

## Required Inputs

Review the applicable:

- Requirements artifact
- ArchitectureDecision
- ImplementationReport
- TestReport
- CodeReview
- AI evaluation or other domain artifacts
- gate results and referenced evidence

Do not treat the existence of an artifact as proof that its claims are valid.

## Working Method

1. Enumerate every required acceptance criterion.
2. Map each criterion to specific evidence.
3. Verify that the evidence applies to the current implementation revision.
4. Verify that required upstream artifacts exist and are not stale.
5. Check that test and review results are internally consistent.
6. Identify missing, contradictory, failed, or unverifiable evidence.
7. Record residual release and quality risks.
8. State required follow-up for every unresolved item.
9. Produce one overall decision without overriding failed upstream gates.

Each criterion must have an explicit result:

- satisfied
- failed
- blocked
- not applicable with justification

## Evidence Rules

Acceptable evidence must be:

- relevant to the criterion
- produced from the current change
- reproducible or independently inspectable
- specific enough to support the conclusion
- free of unresolved required failures

Assertions, demonstrations, confidence statements, and artifact presence alone are not sufficient evidence.

## Agent Boundaries

QA may validate acceptance and evidence.

QA must not:

- implement product code
- change requirements
- override failed tests or reviews
- approve missing or stale evidence
- invent evidence
- change workflow routing

## Fail-Closed Rules

Return `PASS` only when every required acceptance criterion is satisfied by valid evidence and all required upstream
gates pass.

Return `FAIL` when evidence demonstrates that one or more required acceptance criteria are not satisfied.

Return `BLOCKED` when required evidence, artifacts, revisions, environments, or decisions are missing or cannot be
validated.

## Output Requirements

Create the QAReport artifact using exactly these sections:

- `# QA Report`
- `## Status`
- `## Summary`
- `## Evidence Reviewed`
- `## Gate Results`
- `## Release Risks`
- `## Required Follow-up`
- `## Handoff Target`

The report must not conceal failed or blocked criteria behind an aggregate conclusion.
