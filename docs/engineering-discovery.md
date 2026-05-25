# Agentic Workflow Generator — Engineering Discovery

## 1. Problem Statement

Modern AI coding agents are becoming useful, but each platform defines agents, skills, instructions, permissions, handoffs, and project context differently.

This creates a maintenance problem:

- Agent definitions are duplicated across tools.
- Skills are manually copied and drift over time.
- Gates and workflow rules are not consistently enforced.
- Runtime context is often assembled manually.
- Teams cannot easily reproduce the same agentic workflow across projects or platforms.

The goal of this project is to build a platform-neutral generator/compiler that transforms a declarative agentic workflow specification into target-specific agent configurations, skills, gates, validators, and runtime contexts.

In simple terms:

~~~text
Declarative agentic workflow spec
  ↓
Agentic workflow compiler
  ↓
Generated agent system for one or more targets
~~~

This is similar in spirit to OpenAPI Generator, but instead of generating API clients and servers, it generates agentic software delivery infrastructure.

## 2. Goals

The system should:

1. Define agents, skills, capabilities, gates, workflows, and artifacts in a platform-neutral format.
2. Resolve capabilities to concrete skills.
3. Generate target-specific files for supported AI coding agent platforms.
4. Generate runtime context files for agents.
5. Generate validation metadata and scripts.
6. Support reproducible generation through a lockfile.
7. Support project-local overrides without modifying the core registry.
8. Keep generated agents small and focused.
9. Keep domain knowledge in skills and compiled runtime context.
10. Make gates fail-closed by default.

## 3. Non-Goals

The first version should not try to be everything.

Out of scope for MVP:

1. Runtime workflow execution.
2. Full orchestration engine.
3. Replay engine.
4. Remote registry.
5. Marketplace.
6. Semantic quality scoring.
7. Web UI.
8. Advanced parallel execution.
9. Full support for every feature in every target platform.
10. Automatic agent decision-making.

The MVP is a generator/compiler, not a runtime orchestrator.

## 4. Target Platforms

The system should be designed for multiple targets.

Initial targets:

1. VS Code Copilot
2. OpenCode

Design-compatible later targets:

1. OpenAI Codex
2. Claude Code

The core model must not depend on any single target platform.

Correct mental model:

~~~text
.agentic/agentic.json
        ↓
agentic-gen compile
        ↓
Platform-neutral IR
        ↓
Target adapters
        ↓
Generated files for VS Code, OpenCode, Codex, Claude Code, etc.
~~~

## 5. Core Concepts

### Agent

An agent is a role-specific worker.

An agent owns a narrow responsibility area and should not contain all workflow knowledge.

Example agents:

- Orchestrator
- Requirements
- Planner
- Architect
- Security
- Implementer
- TestRunner
- CodeReviewer
- QA
- UAT
- DevOps
- Retrospective

An agent has:

- name
- role
- description
- responsibilities
- mustNot rules
- allowed tools
- capabilities
- handoffs
- artifact outputs
- gate ownership

### Skill

A skill is a reusable instruction unit.

A skill should be small enough to be reused and versioned.

A skill has:

- name
- version
- description
- provided capabilities
- required skills
- allowed agents
- appliesWhen rules
- context budget
- content path
- checksum

### Capability

A capability is the stable interface between agents and skills.

Agents should not directly depend on skill names.

Correct model:

~~~text
Agent -> Capability -> Skill
~~~

Example:

~~~text
CodeReviewer -> review.clean-code -> code-review-clean-code
~~~

This allows skill implementations to change without changing agent definitions.

### Gate

A gate is a fail-closed quality boundary.

A gate defines:

- owner agent
- required capabilities
- required artifacts
- required evidence
- validation rules
- pass route
- fail route
- blocked route

Example gates:

- requirements-review
- plan-review
- architecture-review
- security-review
- implementation-complete
- test-review
- code-review
- qa-review
- uat-review
- release-approval

### Workflow

A workflow is a state machine.

It defines:

- states
- transitions
- start state
- terminal states
- gate bindings
- handoff rules
- failure rules

The workflow is not owned by individual agents.

The orchestrator owns routing, but the workflow specification is the source of truth.

### Runtime Context

Runtime context is compiled context for a specific agent in a specific workflow run.

Agents should read compiled runtime context instead of loading arbitrary registry content.

Example:

~~~text
.runtime/context/WF-042-CodeReviewer.context.md
.runtime/resolution/WF-042-CodeReviewer.skills.json
~~~

### Artifact

Artifacts are workflow memory.

Examples:

- requirements document
- planning document
- architecture decision record
- implementation note
- test report
- code review report
- QA report
- UAT report
- release note

Artifacts should be schema-validatable.

## 6. MVP Scope

### In Scope

The MVP should include:

1. Local registry.
2. `agentic.json`.
3. JSON Schema validation.
4. Capability to skill resolution.
5. Basic lockfile.
6. Generation of target-specific agent files.
7. Generation of target-specific skill files.
8. Generation of gate metadata.
9. Generation of runtime context files.
10. Generation of basic validation scripts.
11. `explain` command for agents, gates, and capabilities.
12. Support for VS Code Copilot as primary target.
13. Support for OpenCode as secondary target.

### Out of Scope

The MVP should not include:

1. Runtime workflow execution.
2. Remote registry.
3. Marketplace.
4. Web UI.
5. Advanced semantic validation.
6. Full Claude Code feature support.
7. Full Codex feature support.
8. Agent replay.
9. Distributed workflow execution.

## 7. Recommended MVP CLI

~~~bash
agentic-gen init --profile orchestrated-delivery --target vscode-copilot
agentic-gen validate
agentic-gen resolve
agentic-gen generate
agentic-gen explain --agent CodeReviewer
agentic-gen explain --gate code-review
agentic-gen explain --capability review.clean-code
~~~

## 8. Proposed Project Structure

~~~text
.agentic/
  agentic.json
  agentic-lock.json
  generated/
  templates/
    overrides/

.github/
  agents/
  skills/

.opencode/
  agents/
  skills/

.codex/
  agents/

.claude/
  agents/
  skills/

.runtime/
  context/
  resolution/

scripts/
  agentic/

docs/
  engineering-discovery.md
  target-platform-analysis.md
  core-domain-model.md
  research/
    spec-kit-analysis.md
~~~

## 9. Risks

| ID | Risk | Impact | Mitigation |
|---|---|---:|---|
| R-001 | The model becomes too platform-specific | High | Use platform-neutral IR |
| R-002 | MVP becomes too large | High | Support VS Code first, OpenCode second |
| R-003 | Skills become too large | Medium | Use capability-based resolution and context budgets |
| R-004 | Gates become symbolic only | Medium | Add artifact schemas and validation scripts |
| R-005 | Generated files drift from source config | High | Use lockfile and validation |
| R-006 | Runtime context becomes manually edited | Medium | Treat `.runtime/` as generated only |
| R-007 | Target platforms change their formats | Medium | Isolate target templates in adapters |

## 10. Assumptions Log

| ID | Assumption | Risk | Status |
|---|---|---:|---|
| A-001 | The first implementation is a generator/compiler, not a runtime orchestrator | High | Proposed |
| A-002 | VS Code Copilot is the primary MVP target | Medium | Proposed |
| A-003 | OpenCode is the secondary MVP target | Medium | Proposed |
| A-004 | Codex and Claude Code are design-compatible later targets | Medium | Proposed |
| A-005 | JSON is the first canonical config format | Low | Proposed |
| A-006 | Skills are resolved through capabilities | Low | Proposed |
| A-007 | Gates are fail-closed by default | Low | Proposed |
| A-008 | Runtime context is generated per agent per workflow run | Medium | Proposed |
| A-009 | Local registry is enough for MVP | Low | Proposed |
| A-010 | Lockfile should be mandatory for reproducibility | Medium | Proposed |

## 11. Decision Log

| ID | Decision | Reason | Status |
|---|---|---|---|
| D-001 | Use a platform-neutral core model | Avoid lock-in to one agent platform | Proposed |
| D-002 | Use target adapters for platform output | Keeps platform differences isolated | Proposed |
| D-003 | Use capabilities as the stable interface between agents and skills | Avoid direct agent-skill coupling | Proposed |
| D-004 | Generate small agent files and larger runtime context files | Reduces prompt bloat and drift | Proposed |
| D-005 | Treat artifacts as workflow memory | Makes workflow state inspectable and reproducible | Proposed |
| D-006 | Make gates fail-closed by default | Avoid unsafe fallback behavior | Proposed |
| D-007 | Use Spec Kit as reference architecture, not as direct blueprint | Learn from its bootstrap and template model | Proposed |

## 12. Open Questions

1. Should generated target files be committed to the repository?
2. Should `.runtime/` always be ignored?
3. Should skills be copied into projects or referenced from registry?
4. Should lockfile include templates and validators in MVP?
5. Should target adapters be plugins from the beginning?
6. Should workflow profiles support inheritance?
7. Should project-local overrides be allowed in MVP?
8. Should validation scripts be Bash-only in MVP?
9. Should artifact schemas be JSON Schema, Markdown conventions, or both?
10. Should the orchestrator be generated as an agent or only as metadata?
