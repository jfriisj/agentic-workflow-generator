---
name: "ai-evaluation"
description: "Use when evaluating an AI application against measurable quality, safety, failure-mode, and operational-risk evidence."
---

# AI Evaluation Skill

## Purpose

Evaluate whether an AI application has sufficient evidence for its claimed quality, safety, and operational behavior.

## Evaluation Rules

The evaluation must be based on declared requirements and reproducible evidence.

Check whether:

1. The AI use case and expected behavior are explicitly defined.
2. Evaluation datasets or scenarios represent the intended operating conditions.
3. Quality metrics and acceptance thresholds are measurable.
4. Results are compared with a declared baseline when a meaningful baseline exists.
5. Important failure modes, uncertain outputs, and edge cases are tested.
6. Safety, misuse, privacy, and harmful-output risks are considered when relevant.
7. Human oversight and escalation behavior are defined when required.
8. Latency, cost, throughput, and resource evidence are included when they affect acceptance criteria.
9. Known limitations and unsupported operating conditions are documented.
10. Evaluation evidence can be reproduced from recorded inputs, commands, configuration, or referenced artifacts.

## Fail-Closed Rules

Return `FAIL` when evidence demonstrates that a required criterion is not satisfied.

Return `BLOCKED` when required evidence, datasets, baselines, thresholds, or evaluation conditions are missing.

Do not:

- invent measurements
- infer a pass from a demonstration alone
- replace missing evidence with confidence statements
- ignore failed scenarios because aggregate results look acceptable
- approve behavior outside the declared evaluation scope

## Output Requirements

The report must state:

- evaluation scope
- datasets and scenarios reviewed
- metrics, thresholds, and baselines
- observed results
- safety and failure findings
- operational evidence
- known limitations
- required fixes
- pass, fail, or blocked decision
