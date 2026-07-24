---
name: "security-review"
description: "Use when reviewing changed code and configuration for concrete security risks, unsafe trust boundaries, and missing mitigations."
---

# Security Review Skill

## Purpose

Review the changed code and configuration for security-relevant defects using the declared scope, trust boundaries, and available evidence.

## Required Inputs

Review:

- changed code and configuration
- approved requirements and architecture decisions
- affected interfaces and data flows
- authentication and authorization behavior
- test evidence relevant to security behavior
- dependency or deployment changes when applicable

Do not claim that the whole system is secure from a limited change review.

## Working Method

1. Identify changed attack surfaces and trust boundaries.
2. Identify data accepted from users, files, networks, tools, models, and external systems.
3. Check validation, normalization, encoding, and output handling.
4. Check authentication and authorization at the point of use.
5. Check for secret, credential, token, and sensitive-data exposure.
6. Check command, query, template, path, prompt, and deserialization injection risks.
7. Check unsafe file, process, network, and tool execution.
8. Check permission scope and least-privilege behavior.
9. Check error handling, logging, and diagnostics for information disclosure.
10. Check dependency, configuration, and default-state changes for insecure behavior.
11. Record concrete findings with evidence and required remediation.
12. State review limitations and unexamined areas.

Prioritize findings by exploitability and impact rather than style preference.

## Finding Rules

Every security finding must include:

- affected component or location
- observed risky behavior
- plausible threat or misuse scenario
- impact
- supporting evidence
- required remediation
- severity or blocking disposition

Do not report a hypothetical weakness as confirmed without evidence.

## Agent Boundaries

The CodeReviewer may identify security defects and required fixes.

The CodeReviewer must not:

- implement feature behavior
- approve release
- change workflow routing
- execute the transition itself
- claim comprehensive security assurance from incomplete evidence

The reviewer produces a disposition. The workflow controller performs routing.

## Fail-Closed Rules

Return `PASS` only when no unresolved blocking security finding exists within the reviewed scope and required evidence is available.

Return `FAIL` when a concrete security defect violates an approved requirement, trust boundary, or required control.

Return `BLOCKED` when the changed scope, required configuration, dependency information, threat context, or validation evidence is unavailable.

## Output Requirements

Record security findings inside the CodeReview artifact using exactly these sections:

- `# Code Review`
- `## Status`
- `## Summary`
- `## Evidence Reviewed`
- `## Findings`
- `## Required Fixes`
- `## Handoff Target`

Security findings must remain distinguishable from clean-code and test-evidence findings.
