# Copilot Instructions

This repository uses generated agentic workflow infrastructure.

## Project

- name: agentic-workflow-generator
- type: agentic-generator
- architecture profile: platform-neutral-workflow-compiler

## Selection

- bundle: orchestrated-delivery
- profile: microservice-platform
- workflow: orchestrated-delivery

## Workflow

- start state: Requirements
- terminal states: Done, Blocked
- default failure state: Blocked
- fail closed: true
- controller: workflow-controller

## Agent Instances

- `requirements-worker` (Requirements)
- `architecture-worker` (Architect)
- `implementation-worker` (Implementer)
- `test-runner` (TestRunner)
- `code-review-worker` (CodeReviewer)
- `qa-worker` (QA)
- `workflow-controller` (Orchestrator)

## Workflow Gates

- `requirements-review` owned by `requirements-worker`
- `architecture-review` owned by `architecture-worker`
- `implementation-complete` owned by `implementation-worker`
- `test-review` owned by `test-runner`
- `code-review` owned by `code-review-worker`
- `qa-review` owned by `qa-worker`

## Core Rules

1. `.agentic/agentic.json` is the canonical active composition.
2. Workflow gates are fail-closed.
3. Artifact contracts are workflow memory.
4. Runtime routing follows compiled state ownership.
5. Agents must stay inside their role bindings.
6. Missing evidence must result in `BLOCKED`, not `PASS`.
7. Separation-of-duties constraints must be preserved.
8. Generated target files must not be edited manually.
