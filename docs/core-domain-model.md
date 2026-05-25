# Agentic Workflow Generator — Core Domain Model

## 1. Purpose

This document defines the platform-neutral core model.

The core model must not depend on VS Code Copilot, OpenCode, Codex, Claude Code, or any other target platform.

Target-specific differences must be handled by target adapters.

## 2. Main Entities

~~~text
Project
Workflow
Agent
Capability
Skill
Gate
Artifact
RuntimeContext
PermissionProfile
Target
TargetAdapter
Lockfile
~~~

## 3. Project

A project is the root configuration for generation.

Example:

~~~json
{
  "project": {
    "name": "real-time-speech-translation",
    "type": "microservice-platform",
    "languageProfiles": ["python", "typescript"],
    "runtimeProfiles": ["docker", "k3s", "kafka"],
    "architectureProfile": "event-driven-microservices"
  }
}
~~~

## 4. Workflow

A workflow is a state machine.

Example:

~~~json
{
  "workflow": {
    "profile": "orchestrated-delivery",
    "start": "Requirements",
    "terminalStates": ["Done", "Blocked"],
    "failClosed": true
  }
}
~~~

A workflow contains:

- states
- transitions
- gates
- handoff rules
- failure rules

## 5. Agent

An agent is a role-specific worker.

Example:

~~~json
{
  "name": "CodeReviewer",
  "role": "code-quality-gate",
  "description": "Reviews code for correctness, maintainability, tests, and security risks.",
  "responsibilities": [
    "Review changed code",
    "Run lightweight validation",
    "Create code review artifact",
    "Reject unsafe or unmaintainable implementation"
  ],
  "mustNot": [
    "Implement feature behavior",
    "Change workflow routing",
    "Approve release"
  ],
  "capabilities": [
    "review.clean-code",
    "review.tests",
    "review.security"
  ],
  "permissionProfile": "read-only"
}
~~~

## 6. Capability

A capability is a stable interface.

Example:

~~~json
{
  "name": "review.clean-code",
  "description": "Ability to review code for readability, naming, duplication, and maintainability."
}
~~~

Capabilities decouple agents from concrete skill implementations.

Correct dependency:

~~~text
Agent -> Capability -> Skill
~~~

## 7. Skill

A skill is a concrete implementation of one or more capabilities.

Example:

~~~json
{
  "name": "code-review-clean-code",
  "version": "1.0.0",
  "description": "Clean-code review guidance.",
  "provides": [
    "review.clean-code",
    "review.naming",
    "review.readability"
  ],
  "requires": [
    "code-review-standards"
  ],
  "allowedAgents": [
    "CodeReviewer"
  ],
  "contentPath": "SKILL.md",
  "contextBudget": {
    "maxTokens": 1800
  }
}
~~~

## 8. Gate

A gate is a quality boundary.

Example:

~~~json
{
  "name": "code-review",
  "owner": "CodeReviewer",
  "requiredCapabilities": [
    "review.clean-code",
    "review.tests"
  ],
  "requiredArtifacts": [
    {
      "type": "CodeReview",
      "pathPattern": "agent-output/code-review/*.md"
    }
  ],
  "passRoute": "QA",
  "failRoute": "Implementer",
  "blockedRoute": "Orchestrator",
  "blocking": true
}
~~~

## 9. Artifact

Artifacts are workflow memory.

Example artifact types:

~~~text
Requirements
Plan
ArchitectureDecision
SecurityReview
ImplementationReport
TestReport
CodeReview
QAReport
UATReport
ReleaseNote
Retrospective
~~~

Artifacts should have:

- type
- schema
- path pattern
- owner
- required sections
- status field
- evidence section

## 10. Runtime Context

Runtime context is generated for a specific agent and workflow run.

Example:

~~~json
{
  "workflowId": "WF-042",
  "agent": "CodeReviewer",
  "contextPath": ".runtime/context/WF-042-CodeReviewer.context.md",
  "resolutionPath": ".runtime/resolution/WF-042-CodeReviewer.skills.json",
  "resolvedCapabilities": [
    {
      "capability": "review.clean-code",
      "skill": "code-review-clean-code",
      "version": "1.0.0"
    }
  ]
}
~~~

## 11. Permission Profile

Permission profiles are platform-neutral.

Example:

~~~json
{
  "name": "read-only",
  "read": true,
  "write": false,
  "edit": false,
  "bash": "deny"
}
~~~

Target adapters translate permission profiles to platform-specific output.

## 12. Target

A target is an output platform.

Example:

~~~json
{
  "name": "vscode-copilot",
  "enabled": true
}
~~~

## 13. Target Adapter

A target adapter maps the core model to platform files.

Example:

~~~json
{
  "name": "vscode-copilot",
  "version": "0.1.0",
  "templates": {
    "agent": "templates/agent.md.hbs",
    "skill": "templates/skill.md.hbs"
  },
  "outputPaths": {
    "agents": ".github/agents",
    "skills": ".github/skills"
  }
}
~~~

## 14. Lockfile

The lockfile makes generation reproducible.

Example:

~~~json
{
  "lockfileVersion": 1,
  "registry": {
    "type": "local",
    "path": "~/.agentic/registry",
    "revision": "local"
  },
  "skills": {
    "code-review-clean-code": {
      "version": "1.0.0",
      "checksum": "sha256:..."
    }
  },
  "templates": {
    "vscode-copilot/agent.md.hbs": {
      "checksum": "sha256:..."
    }
  }
}
~~~

## 15. Compilation Pipeline

~~~text
agentic.json
  ↓
validate config
  ↓
load registry
  ↓
resolve workflow profile
  ↓
resolve agents
  ↓
resolve capabilities
  ↓
resolve skills
  ↓
build intermediate representation
  ↓
generate runtime context
  ↓
generate target output
  ↓
validate generated output
~~~

## 16. Intermediate Representation

The IR is the compiled, platform-neutral model.

It should include:

- resolved agents
- resolved capabilities
- resolved skills
- resolved gates
- resolved workflows
- resolved permission profiles
- target compatibility warnings
- runtime context paths
- generated output plan

## 17. Open Questions

1. Should IR be saved to `.agentic/generated/ir.json`?
2. Should runtime context be generated during compile or generate?
3. Should gates be represented as JSON, YAML, or both?
4. Should artifact schemas be part of registry or project config?
5. Should each target adapter generate validation warnings?
