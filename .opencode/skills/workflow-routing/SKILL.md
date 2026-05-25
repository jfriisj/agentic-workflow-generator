# Workflow Routing Skill

## Purpose

Route work through a fail-closed agentic workflow.

## Rules

1. Never skip a required gate.
2. Never mark work as passed without required artifacts.
3. If evidence is missing, return BLOCKED.
4. If a gate fails, route to the configured fail route.
5. If a gate passes, route to the configured pass route.
6. If routing is ambiguous, route to Orchestrator with BLOCKED status.

## Output Requirements

Routing decisions must include:

- current state
- gate result
- required artifacts checked
- next state
- reason
