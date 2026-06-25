# Agentic Configuration

This directory contains the source configuration and generated metadata for the Agentic Workflow Generator.

## Intended Files

~~~text
.agentic/
  agentic.json
  setup-profile.json
  agentic-lock.json
  generated/
  templates/
    overrides/
~~~

## Rules

1. `agentic.json` is the canonical project configuration.
2. `setup-profile.json` captures the guided setup decisions that shape the project.
3. `agentic-lock.json` is used for reproducible generation.
4. `.agentic/generated/` contains generated metadata.
5. `.runtime/` contains generated runtime context and should normally not be committed.
6. Target-specific generated files may be committed depending on project policy.

## Core Principle

~~~text
Platform-neutral workflow spec
  ↓
Agentic workflow compiler
  ↓
Target-specific generated agent system
~~~

## Target Platforms

Planned targets:

1. VS Code Copilot
2. OpenCode
3. OpenAI Codex
4. Claude Code

## MVP Direction

The MVP should focus on:

1. Generator/compiler.
2. Validator.
3. Capability-to-skill resolution.
4. Runtime context generation.
5. VS Code Copilot target.
6. OpenCode target.

The MVP should not include a runtime orchestrator.
