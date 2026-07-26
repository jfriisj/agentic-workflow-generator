---
name: "architecture-design"
description: "Use when designing system boundaries, evaluating architectural alternatives, and documenting evidence-based tradeoffs."
---

# Architecture Design Skill

## Purpose

Produce an architecture decision that satisfies approved requirements while making boundaries, tradeoffs, consequences,
and risks explicit.

## Required Inputs

Review:

- the approved Requirements artifact
- acceptance criteria
- constraints and assumptions
- existing architecture and interfaces when present
- relevant operational and quality requirements

Stop when the requirements needed for an architecture decision are unresolved.

## Working Method

1. Identify the architectural drivers from the approved requirements.
2. Identify required quality attributes such as availability, security, performance, modifiability, deployability,
   testability, and operability.
3. Define system boundaries and external dependencies.
4. Identify the responsibilities of major components.
5. Define important interfaces, data flows, and ownership boundaries.
6. Identify at least one credible alternative when a meaningful choice exists.
7. Evaluate alternatives against the same drivers and constraints.
8. State the selected decision and why it best satisfies the declared priorities.
9. Record positive and negative consequences.
10. Record unresolved risks and how the decision can be validated.

Do not select an architecture merely because it is familiar or fashionable.

## Tradeoff Rules

Every material decision must identify:

- the requirement or quality attribute it supports
- the cost or disadvantage it introduces
- rejected alternatives
- evidence, assumptions, or constraints behind the choice
- conditions that would invalidate the decision

Prefer the simplest architecture that satisfies the approved requirements.

## Agent Boundaries

The Architect may define boundaries, interfaces, tradeoffs, and technical risks.

The Architect must not:

- implement product code
- replace missing requirements with architectural assumptions
- skip required quality gates
- approve release
- change workflow routing

## Fail-Closed Rules

Return `PASS` only when:

- the decision traces to approved requirements
- system boundaries are explicit
- material alternatives and tradeoffs are evaluated
- consequences and risks are documented
- no unresolved requirement prevents implementation

Return `FAIL` when the proposed architecture demonstrably violates an approved requirement or constraint.

Return `BLOCKED` when required requirements, quality attributes, constraints, or dependency information are missing.

## Output Requirements

Create the ArchitectureDecision artifact using exactly these sections:

- `# Architecture Decision`
- `## Status`
- `## Summary`
- `## Context`
- `## Decision`
- `## Alternatives Considered`
- `## Consequences`
- `## Handoff Target`

The artifact must not contain an unqualified approval of implementation or release.
