# Agentic Registry

This registry contains reusable agentic workflow definitions.

The registry is the source for:

- agents
- skills
- workflows
- profiles
- target adapters
- templates
- validators

The project config in `.agentic/agentic.json` references concepts from this registry.

## Registry Principle

The project defines what it wants.

The registry defines reusable building blocks.

The compiler resolves:

```text
Project config
  -> Workflow profile
  -> Agents
  -> Capabilities
  -> Skills
  -> Gates
  -> Target adapters
  -> Generated output
```

## MVP Scope

The MVP registry is local and committed to the repository.

Later versions may support:

* global registry
* Git-based registry
* remote registry
* versioned registry packages
  EOF

cat > registry/targets/vscode-copilot/adapter.json <<'EOF'
{
"name": "vscode-copilot",
"version": "0.1.0",
"description": "Target adapter for generating GitHub Copilot custom agents and skills for VS Code.",
"outputPaths": {
"agents": ".github/agents",
"skills": ".github/skills",
"instructions": ".github/copilot-instructions.md",
"runtimeContext": ".runtime/context",
"resolution": ".runtime/resolution"
},
"templates": {
"agent": "templates/agent.md.hbs",
"skill": "templates/skill.md.hbs",
"instructions": "templates/copilot-instructions.md.hbs",
"runtimeContext": "templates/runtime-context.md.hbs"
},
"supportedFeatures": {
"agents": true,
"skills": true,
"handoffs": true,
"permissionProfiles": "partial",
"runtimeContext": "instruction-reference",
"toolRestrictions": "partial"
},
"permissionMapping": {
"read-only": {
"tools": [
"search",
"read/readFile"
],
"notes": "Read-only agents should not edit files or run destructive commands."
},
"implementation": {
"tools": [
"search",
"read/readFile",
"edit/editFiles",
"execute/runInTerminal",
"execute/testFailure"
],
"notes": "Implementation agents may edit files and run relevant validation commands."
},
"test-runner": {
"tools": [
"search",
"read/readFile",
"execute/runInTerminal",
"execute/testFailure"
],
"notes": "Test runner agents may execute validation commands but should not own product design decisions."
}
}
}
