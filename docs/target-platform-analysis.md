# Target Platform Analysis

## 1. Purpose

This document analyzes how the Agentic Workflow Generator can target multiple AI coding agent platforms.

The goal is not to make the core model depend on any one platform.

The goal is to define a platform-neutral model and generate platform-specific outputs through target adapters.

## 2. Supported Targets

Initial target candidates:

1. VS Code Copilot
2. OpenCode
3. OpenAI Codex
4. Claude Code

Recommended MVP order:

~~~text
1. VS Code Copilot
2. OpenCode
3. Codex
4. Claude Code
~~~

## 3. Common Concepts Across Targets

Most target platforms support some form of:

- project instructions
- agent/persona definitions
- skills or reusable instructions
- tool permissions
- local configuration
- global configuration
- project-level overrides
- task-specific context

The naming and file formats differ.

Therefore, these concepts should exist in the core model:

~~~text
Agent
Skill
Capability
Workflow
Gate
Artifact
RuntimeContext
PermissionProfile
TargetAdapter
TargetTemplate
~~~

## 4. Feature Matrix

| Feature | VS Code Copilot | OpenCode | OpenAI Codex | Claude Code |
|---|---|---|---|---|
| Project agents | `.github/agents/*.agent.md` | `.opencode/agents/*.md` | `.codex/agents/*.toml` | `.claude/agents/*.md` |
| Global agents | Supported | Supported | Supported | Supported |
| Main instruction file | Copilot instructions / AGENTS.md | AGENTS.md / rules | AGENTS.md | CLAUDE.md |
| Skill format | SKILL.md | SKILL.md | SKILL.md | SKILL.md / skills config |
| Agent file format | Markdown + YAML frontmatter | Markdown + YAML frontmatter | TOML | Markdown + YAML frontmatter |
| Tool restrictions | Tool list | Permissions | Sandbox/config | Tools, disallowed tools, permission mode |
| Handoffs | Supported/agent-oriented | Limited/manual | Subagent-oriented | Subagent/team-oriented |
| Runtime context | Indirect/manual | Indirect/manual | Indirect/manual | Indirect/manual |
| Best fit | Team workflows in VS Code | Local CLI workflows | Codex CLI/cloud workflows | Advanced subagent workflows |

## 5. Target: VS Code Copilot

### Best Use

VS Code Copilot is a strong first target because it fits markdown-based agent definitions and project-local workflows.

### Expected Output

~~~text
.github/agents/*.agent.md
.github/skills/<skill-name>/SKILL.md
.github/copilot-instructions.md
.agentic/generated/*
.runtime/context/*
~~~

### Template Needs

Required templates:

~~~text
targets/vscode-copilot/templates/agent.md.hbs
targets/vscode-copilot/templates/skill.md.hbs
targets/vscode-copilot/templates/copilot-instructions.md.hbs
targets/vscode-copilot/templates/runtime-context.md.hbs
~~~

### Mapping Rules

| Core Concept | VS Code Output |
|---|---|
| Agent | `.github/agents/<agent>.agent.md` |
| Skill | `.github/skills/<skill>/SKILL.md` |
| Project instructions | `.github/copilot-instructions.md` |
| Permission profile | Agent tools list |
| Handoff | Agent handoff metadata/instructions |
| Runtime context | Path referenced from generated agent |

## 6. Target: OpenCode

### Best Use

OpenCode is a strong secondary target because it supports project-local agents, skills, and permissions.

### Expected Output

~~~text
.opencode/agents/*.md
.opencode/skills/<skill-name>/SKILL.md
opencode.json
AGENTS.md
.agentic/generated/*
.runtime/context/*
~~~

### Template Needs

Required templates:

~~~text
targets/opencode/templates/agent.md.hbs
targets/opencode/templates/skill.md.hbs
targets/opencode/templates/opencode.json.hbs
targets/opencode/templates/AGENTS.md.hbs
targets/opencode/templates/runtime-context.md.hbs
~~~

### Mapping Rules

| Core Concept | OpenCode Output |
|---|---|
| Agent | `.opencode/agents/<agent>.md` |
| Skill | `.opencode/skills/<skill>/SKILL.md` |
| Project instructions | `AGENTS.md` |
| Permission profile | OpenCode permission config |
| Runtime context | Path referenced from generated agent |

## 7. Target: OpenAI Codex

### Best Use

Codex is relevant for CLI/cloud coding workflows and subagent-based review or parallel analysis.

### Expected Output

~~~text
AGENTS.md
.codex/config.toml
.codex/agents/*.toml
.agents/skills/<skill-name>/SKILL.md
.agentic/generated/*
.runtime/context/*
~~~

### Template Needs

Required templates:

~~~text
targets/codex/templates/AGENTS.md.hbs
targets/codex/templates/config.toml.hbs
targets/codex/templates/agent.toml.hbs
targets/codex/templates/skill.md.hbs
targets/codex/templates/runtime-context.md.hbs
~~~

### Mapping Rules

| Core Concept | Codex Output |
|---|---|
| Agent | `.codex/agents/<agent>.toml` |
| Skill | `.agents/skills/<skill>/SKILL.md` |
| Project instructions | `AGENTS.md` |
| Permission profile | Sandbox/config |
| Runtime context | Referenced in developer instructions |

## 8. Target: Claude Code

### Best Use

Claude Code is relevant for advanced subagent workflows, agent isolation, worktrees, hooks, and more structured agent behavior.

### Expected Output

~~~text
CLAUDE.md
.claude/agents/*.md
.claude/skills/<skill-name>/SKILL.md
.claude/settings.json
.agentic/generated/*
.runtime/context/*
~~~

### Template Needs

Required templates:

~~~text
targets/claude-code/templates/CLAUDE.md.hbs
targets/claude-code/templates/subagent.md.hbs
targets/claude-code/templates/settings.json.hbs
targets/claude-code/templates/skill.md.hbs
targets/claude-code/templates/runtime-context.md.hbs
~~~

### Mapping Rules

| Core Concept | Claude Code Output |
|---|---|
| Agent | `.claude/agents/<agent>.md` |
| Skill | `.claude/skills/<skill>/SKILL.md` |
| Project instructions | `CLAUDE.md` |
| Permission profile | tools / disallowedTools / permissionMode |
| Runtime context | Referenced in subagent instructions |
| Isolation | Claude-specific agent config |

## 9. Permission Mapping

The core model should define abstract permission profiles.

Example:

~~~json
{
  "permissionProfiles": {
    "read-only": {
      "read": true,
      "write": false,
      "edit": false,
      "bash": "deny"
    },
    "implementation": {
      "read": true,
      "write": true,
      "edit": true,
      "bash": "allow"
    },
    "test-runner": {
      "read": true,
      "write": true,
      "edit": true,
      "bash": "limited"
    }
  }
}
~~~

Each target adapter maps these profiles differently.

| Core Profile | VS Code | OpenCode | Codex | Claude Code |
|---|---|---|---|---|
| read-only | read/search tools only | edit deny, bash deny | read-only sandbox | Read/Grep/Glob only |
| implementation | read/edit/test tools | edit allow, bash allow | workspace-write | Read/Edit/Bash |
| test-runner | read/bash limited | bash allow, edit limited | workspace-write | Read/Bash/Edit limited |

## 10. Runtime Context Mapping

Runtime context should remain generated by the core compiler.

Each target agent should reference the generated runtime context path.

Example instruction:

~~~text
Before performing work, load the generated runtime context:

.runtime/context/{{WORKFLOW_ID}}-{{AGENT_NAME}}.context.md

If the file is missing, stop and report:

BLOCKED: Missing generated runtime context.
~~~

## 11. Unsupported or Degraded Features

Some features will not map cleanly to all platforms.

Examples:

| Feature | Problem |
|---|---|
| Handoffs | Some platforms support explicit handoffs, others require instructions |
| Permissions | Permission models differ significantly |
| Skills | Same SKILL.md idea, but loading behavior differs |
| Runtime context | Usually must be referenced by instruction, not enforced by platform |
| Parallel execution | Platform-specific |
| Worktree isolation | Mostly Claude-specific |
| Sandbox modes | Mostly Codex-specific |

The generator must support degraded output with explicit warnings.

## 12. Adapter Design

Each target adapter should define:

~~~text
name
version
supportedFeatures
outputPaths
templatePaths
permissionMapping
skillMapping
agentMapping
validationRules
warnings
~~~

Example:

~~~json
{
  "name": "vscode-copilot",
  "version": "0.1.0",
  "supportedFeatures": {
    "agents": true,
    "skills": true,
    "handoffs": true,
    "permissionProfiles": "partial",
    "runtimeContext": "instruction-reference"
  }
}
~~~

## 13. MVP Recommendation

MVP should implement:

~~~text
Primary target:
  VS Code Copilot

Secondary target:
  OpenCode

Design-compatible:
  Codex
  Claude Code
~~~

This avoids overbuilding while keeping the architecture portable.

## 14. Open Questions

1. Should skills be generated into target-specific folders or shared `.agents/skills`?
2. Should generated files include a warning header?
3. Should target adapters validate platform-specific schemas?
4. Should unsupported target features fail generation or produce warnings?
5. Should target adapters be user-installable plugins?
6. Should one project support multiple targets at the same time?
7. Should each target have its own lock section?
