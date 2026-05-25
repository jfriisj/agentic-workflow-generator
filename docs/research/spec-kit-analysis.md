# Spec Kit Analysis for Agentic Workflow Generator

## 1. Purpose

This document defines how GitHub Spec Kit should be used as a reference architecture for the Agentic Workflow Generator.

Spec Kit should be treated as a reference, not as a direct blueprint.

The goal is to learn from its structure and adapt useful patterns to a more general agentic workflow compiler.

## 2. What Spec Kit Solves

Spec Kit focuses on spec-driven development.

Its core idea is that specifications should drive planning and implementation.

The typical flow is:

~~~text
constitution
  ↓
specify
  ↓
plan
  ↓
tasks
  ↓
implement
~~~

This is useful because it treats written artifacts as active workflow drivers instead of passive documentation.

## 3. What Our Project Solves

The Agentic Workflow Generator focuses on generated agentic workflow infrastructure.

Its core idea is:

~~~text
Artifacts are workflow memory.
Orchestrator is the state machine.
Agents are role-specialized workers.
Skills are capability implementations.
Gates are fail-closed quality boundaries.
Runtime context is compiled, not manually assembled.
~~~

The expected flow is more general:

~~~text
requirements
  ↓
planning
  ↓
architecture
  ↓
security
  ↓
implementation
  ↓
testing
  ↓
code review
  ↓
QA
  ↓
UAT
  ↓
release
  ↓
retrospective
~~~

## 4. Similarities

Spec Kit and Agentic Workflow Generator both need:

- CLI bootstrap
- project initialization
- templates
- target integrations
- project-local overrides
- repeatable generated files
- workflow phases
- governance rules
- structured artifacts
- clear commands

## 5. Key Differences

| Area | Spec Kit | Agentic Workflow Generator |
|---|---|---|
| Primary object | Specification | Agentic workflow |
| Main output | Specs, plans, tasks, commands | Agents, skills, gates, runtime context, validators |
| Workflow model | Spec-driven phases | State machine with gates |
| Reuse model | Templates, presets, extensions | Registry, profiles, capabilities, skills, adapters |
| Governance | Constitution | Gates, artifact contracts, lockfile |
| Target concept | Agent integrations | Target adapters |
| Runtime | Human/agent follows commands | Generated runtime context for agents |

## 6. Useful Patterns to Reuse Conceptually

### CLI Bootstrap

Spec Kit-style bootstrap is useful.

Equivalent:

~~~bash
agentic-gen init --profile orchestrated-delivery --target vscode-copilot
~~~

### Target Integrations

Spec Kit supports different AI coding environments.

Equivalent:

~~~bash
agentic-gen generate --target vscode-copilot
agentic-gen generate --target opencode
agentic-gen generate --target codex
agentic-gen generate --target claude-code
~~~

### Template Hierarchy

Spec Kit-style template layering is highly relevant.

Recommended priority:

~~~text
1. Project overrides
2. Installed presets
3. Installed extensions
4. Target templates
5. Core templates
~~~

### Presets

Presets should customize workflow shape and terminology.

Example presets:

~~~text
orchestrated-delivery
lightweight-code-review
microservice-platform
ai-engineering
regulated-enterprise
research-project
~~~

### Extensions

Extensions should add optional workflow modules.

Example extensions:

~~~text
kafka-diagnostics
k3s-validation
rag-evaluation
security-hardening
performance-review
release-readiness
~~~

### Commands

Spec Kit uses workflow commands.

Agentic Generator can generate commands too, but commands should not be the core model.

Possible commands:

~~~text
/agentic.requirements
/agentic.plan
/agentic.architecture
/agentic.implement
/agentic.test
/agentic.review
/agentic.qa
/agentic.release
~~~

## 7. What We Should Avoid

Do not copy Spec Kit directly.

Avoid:

1. Making feature specs the only central artifact.
2. Hardcoding one development lifecycle.
3. Treating commands as the primary architecture.
4. Ignoring skills and capability resolution.
5. Ignoring target-specific permission models.
6. Ignoring lockfile reproducibility.
7. Generating large agent prompts with all knowledge embedded.
8. Building runtime orchestration before generation is stable.

## 8. Required Changes for Our Direction

Spec Kit-inspired concepts should be translated as follows:

| Spec Kit Concept | Agentic-Gen Equivalent |
|---|---|
| Integration | Target adapter |
| Template | Target/core template |
| Preset | Workflow/profile preset |
| Extension | Optional workflow module |
| Constitution | Governance policy / gate policy |
| Spec | Artifact contract |
| Plan | Planning artifact |
| Tasks | Implementation task artifact |
| Command | Optional target command |
| Agent instructions | Generated agent + runtime context |
| Project override | Project-local template/config override |

## 9. Proposed Agentic-Gen CLI

~~~bash
agentic-gen init
agentic-gen validate
agentic-gen resolve
agentic-gen compile
agentic-gen generate
agentic-gen explain
agentic-gen target list
agentic-gen preset list
agentic-gen extension list
~~~

Example:

~~~bash
agentic-gen init \
  --profile orchestrated-delivery \
  --target vscode-copilot \
  --target opencode

agentic-gen validate

agentic-gen compile

agentic-gen generate

agentic-gen explain --agent CodeReviewer
~~~

## 10. Proposed Registry Structure

~~~text
registry/
  core/
    schemas/
    templates/
    validators/

  agents/
    CodeReviewer/
      agent.json

  skills/
    code-review-clean-code/
      skill.json
      SKILL.md

  workflows/
    orchestrated-delivery.workflow.json

  profiles/
    microservice-platform.profile.json

  targets/
    vscode-copilot/
      adapter.json
      templates/

    opencode/
      adapter.json
      templates/

    codex/
      adapter.json
      templates/

    claude-code/
      adapter.json
      templates/

  presets/
    regulated-enterprise/
      preset.json
      templates/

  extensions/
    kafka-diagnostics/
      extension.json
      gates/
      skills/
      templates/
~~~

## 11. Proposed Project Structure

~~~text
.agentic/
  agentic.json
  agentic-lock.json
  generated/
  templates/
    overrides/

.runtime/
  context/
  resolution/

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
~~~

## 12. Governance Model

Spec Kit has a constitution concept.

Agentic-Gen should support a governance policy, but MVP should express governance mostly through gates.

Example:

~~~json
{
  "governance": {
    "failClosed": true,
    "requireArtifacts": true,
    "requireEvidence": true,
    "allowManualOverride": false
  }
}
~~~

## 13. Artifact Flow

Artifacts should be explicit and schema-validatable.

Example:

~~~text
Requirements.md
Plan.md
ArchitectureDecision.md
SecurityReview.md
ImplementationReport.md
TestReport.md
CodeReview.md
QAReport.md
UATReport.md
ReleaseNote.md
~~~

Each gate should require one or more artifacts.

## 14. Proposed Agentic-Gen Equivalent to Spec Kit Flow

~~~text
agentic-gen init
  creates base config, target config, starter registry references

agentic-gen validate
  validates config, registry references, target compatibility

agentic-gen resolve
  resolves agents -> capabilities -> skills

agentic-gen compile
  builds intermediate representation and runtime context

agentic-gen generate
  writes target-specific files

agentic-gen explain
  explains why agents, skills, gates, and files were generated
~~~

## 15. Open Questions

1. Should project-local overrides use the same priority model as Spec Kit?
2. Should presets and extensions be supported in MVP?
3. Should generated slash commands be part of MVP?
4. Should governance be a standalone file or part of `agentic.json`?
5. Should the compiler emit warnings for unsupported target features?
6. Should each target adapter declare its supported feature set?
7. Should target templates be versioned and locked?
