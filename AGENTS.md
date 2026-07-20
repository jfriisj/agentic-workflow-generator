# AGENTS.md

This repository uses generated agentic workflow infrastructure.

## Project

- name: agentic-workflow-generator
- type: agentic-generator
- architecture profile: platform-neutral-workflow-compiler

## Workflow

- profile: orchestrated-delivery
- start state: Requirements
- terminal states: Done, Blocked
- fail closed: True

## Agents

- Architect
- CodeReviewer
- Implementer
- Orchestrator
- QA
- Requirements
- TestRunner

## Gates

- requirements-review
- architecture-review
- implementation-complete
- test-review
- code-review
- qa-review

## Core Rules

1. The workflow is fail-closed.
2. Artifacts are workflow memory.
3. The orchestrator owns routing and state transitions.
4. Agents must stay within their role.
5. Missing evidence must result in BLOCKED, not PASS.
6. Generated files should not be manually edited unless the project explicitly allows overrides.

## Generated Metadata

Resolution metadata is generated under:

~~~text
.agentic/generated/
~~~
