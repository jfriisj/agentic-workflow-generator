# Agentic Workflow Generator — Core Domain Model

## 1. Purpose

This document defines the platform-neutral core model.

The core model must not depend on VS Code Copilot, OpenCode, Codex, Claude Code, or any other target platform.

Target-specific differences must be handled by target adapters.

## 2. Main Entities

The conceptual relationships are defined in:

~~~text
docs/diagrams/agentic-domain-model-chen.puml
~~~

Main entities:

~~~text
Project
Setup
SetupQuestion
SetupOption
Bundle
Profile
Workflow
WorkflowState
Transition
Gate
AgentProfile
AgentInstance
RoleBinding
SeparationPolicy
Capability
Skill
ArtifactContract
PermissionProfile
TargetAdapter
RuntimeContext
Lockfile
OutputManifest
~~~

The model distinguishes reusable registry definitions from concrete runtime composition:

~~~text
AgentProfile = reusable defaults and recommendations
AgentInstance = concrete generated worker
RoleBinding = authoritative workflow assignment
SeparationPolicy = explicit independence requirement
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

## 5. Agent Profile

An agent profile is a reusable registry definition with safe defaults and
recommendations. It is not a concrete generated worker and does not own an
immutable runtime assignment.

Example:

~~~json
{
  "name": "CodeReviewer",
  "role": "code-quality-gate",
  "description": "Reviews code for correctness, maintainability, tests, and security risks.",
  "recommendedResponsibilities": [
    "Review changed code",
    "Create code review evidence",
    "Reject unsafe or unmaintainable implementation"
  ],
  "defaultGuardrails": [
    "Do not implement feature behavior",
    "Do not change workflow routing",
    "Do not approve release"
  ],
  "recommendedCapabilities": [
    "review.clean-code",
    "review.tests",
    "review.security"
  ],
  "defaultPermissionProfile": "read-only"
}
~~~

Recommendations do not prevent a validated composition from assigning a
different capability, skill, responsibility, or permission profile.

## 5.1 Agent Instance

An agent instance is a concrete worker owned by one bundle.

Example:

~~~json
{
  "id": "delivery-worker",
  "profile": "CodeReviewer",
  "displayName": "Delivery Worker",
  "permissionProfile": "implementation",
  "sharedContextPolicy": "shared-with-assigned-bindings"
}
~~~

One agent instance may serve several role bindings. It materializes the union
of their required capabilities, selected skills, responsibilities, and
guardrails.

Each agent instance has exactly one effective permission profile. The profile
must be selected explicitly and must satisfy every assigned role binding.
Validation must fail rather than silently broaden permissions.

## 5.2 Role Binding

A role binding is the authoritative assignment of workflow responsibility to
an agent instance.

Example:

~~~json
{
  "roleName": "implementation",
  "bindingType": "state-owner",
  "agentInstance": "delivery-worker",
  "workflowState": "Implementer",
  "requiredCapabilities": [
    "implementation.code",
    "implementation.update-tests"
  ],
  "selectedSkills": [
    "implementation-engineering"
  ],
  "produces": [
    "ImplementationReport"
  ],
  "responsibilities": [
    "Implement the approved change"
  ],
  "guardrails": [
    "Do not self-approve implementation"
  ]
}
~~~

A role binding has one of two binding types:

- `state-owner`: owns exactly one non-terminal workflow state and its gate
- `workflow-controller`: owns routing authority but no workflow state or gate

Every non-terminal workflow state has exactly one state-owner binding.

Every workflow has exactly one workflow-controller binding.

A role binding cannot be both a state owner and a workflow controller.

## 5.3 Separation Policy

A separation policy declares when selected role bindings must use distinct
agent instances.

Example:

~~~json
{
  "id": "implementation-review-separation",
  "mode": "required",
  "roleBindings": [
    "implementation",
    "code-review"
  ],
  "requireDistinctInstances": true,
  "reason": "Implementation must not approve its own work."
}
~~~

Separation is bundle-specific. It must not be implemented as a global lock
between agent profile names and skills.
## 6. Capability

A capability is a stable interface.

Example:

~~~json
{
  "name": "review.clean-code",
  "description": "Ability to review code for readability, naming, duplication, and maintainability."
}
~~~

Capabilities decouple workflow roles and agent profiles from concrete skill implementations.

The composition owns the concrete assignment:

~~~text
Setup
  -> Bundle
  -> Agent instance
  -> Role binding
  -> Required capabilities
  -> Selected skills
~~~

An agent's registry capabilities are recommendations and defaults. They must not force every setup containing that agent to install the complete default skill set.

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
  "requiresCapabilities": [
    "requirements.define-acceptance-criteria"
  ],
  "recommendedAgents": [
    "CodeReviewer"
  ],
  "contentPath": "SKILL.md",
  "contextBudget": {
    "maxTokens": 1800
  }
}
~~~

`recommendedAgents` is advisory metadata. It documents the most common specialist assignment but does not prevent another agent from receiving the skill through a validated setup or bundle.

Skills provide working methods and capability implementations. Authorization, artifact ownership, workflow routing, and separation of duties belong to the concrete composition and its gates.

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

An agent profile may recommend a default permission profile. The effective permission profile belongs to the concrete agent instance, because each generated worker has one target-level permission configuration. It must satisfy every role binding assigned to that instance and map successfully through every enabled target adapter.

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
