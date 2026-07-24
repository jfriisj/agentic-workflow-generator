---
name: "requirements-analysis"
description: "Use when eliciting requirements, resolving scope and constraints, and defining measurable acceptance criteria."
---

# Requirements Analysis Skill

## Purpose

Convert a problem statement into an explicit, bounded, testable requirements contract without designing the implementation.

## Required Inputs

Review the available:

- problem statement or requested outcome
- stakeholder constraints
- existing project context
- upstream decisions and referenced artifacts
- known assumptions, dependencies, and risks

Do not invent missing stakeholder decisions.

## Working Method

1. Restate the problem and intended outcome in concrete terms.
2. Separate in-scope behavior from explicitly out-of-scope behavior.
3. Identify functional requirements.
4. Identify relevant non-functional requirements.
5. Record technical, operational, legal, business, and delivery constraints.
6. Record assumptions separately from confirmed facts.
7. Identify contradictions, missing decisions, and external dependencies.
8. Define acceptance criteria that are observable and independently testable.
9. Ensure every required outcome has at least one acceptance criterion.
10. Ensure acceptance criteria describe outcomes rather than implementation details.

Acceptance criteria must be:

- specific
- measurable or objectively verifiable
- bounded
- testable
- traceable to a requirement
- free of ambiguous terms such as fast, robust, intuitive, or sufficient unless quantified

## Agent Boundaries

The Requirements agent may clarify and structure the requested outcome.

The Requirements agent must not:

- design implementation details
- select an architecture without an approved requirement basis
- approve release
- hide unresolved assumptions
- change workflow routing

## Fail-Closed Rules

Return `PASS` only when:

- scope is explicit
- requirements are internally consistent
- acceptance criteria are testable
- material assumptions and constraints are recorded
- no unresolved issue prevents downstream design

Return `FAIL` when supplied requirements or constraints are demonstrably contradictory or impossible to satisfy as stated.

Return `BLOCKED` when necessary stakeholder decisions, source information, scope boundaries, or acceptance thresholds are missing.

Do not convert missing information into assumptions merely to produce `PASS`.

## Output Requirements

Create the Requirements artifact using exactly these sections:

- `# Requirements`
- `## Status`
- `## Summary`
- `## Scope`
- `## Requirements`
- `## Acceptance Criteria`
- `## Assumptions`
- `## Constraints`
- `## Handoff Target`

The artifact must clearly distinguish confirmed requirements from assumptions and unresolved matters.
