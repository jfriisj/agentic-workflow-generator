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

- Orchestrator
- Requirements
- Architect
- Implementer
- TestRunner
- CodeReviewer
- QA

## Gates

- requirements-review
- implementation-complete
- test-review
- code-review
- qa-review

## Core Rules

1. The workflow is fail-closed.
2. Artifacts are workflow memory.
3. The orchestrator owns routing and state transitions.
4. Agents must stay within their role.
5. Agents must use generated runtime context when available.
6. Missing evidence must result in BLOCKED, not PASS.
7. Generated files should not be manually edited unless the project explicitly allows overrides.

## Generated Context

Runtime context is generated under:

~~~text
.runtime/context/
~~~

Resolution metadata is generated under:

~~~text
.agentic/generated/
~~~
