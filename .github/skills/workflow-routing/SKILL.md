---
name: "workflow-routing"
description: "Use when the Orchestrator must route work through workflow states, gates, failures, and handoffs without bypassing evidence requirements."
---

# Workflow Routing Skill

## Purpose

Route work through a fail-closed agentic workflow.

## Rules

1. Never skip a required gate.
2. Never mark work as passed without required artifacts.
3. If evidence is missing, return BLOCKED.
4. If a gate fails, route to the configured fail route.
5. If a gate passes, route to the configured pass route.
6. If routing is missing or ambiguous, return `BLOCKED` and perform no transition.
7. Never invent a route or route back to the Orchestrator merely because no unique transition exists.

## Output Requirements

Routing decisions must include:

- current state
- gate result
- required artifacts checked
- decision: transition or no transition
- next state when a unique transition exists
- blocked reason when no transition is performed
- reason
