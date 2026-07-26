"""Deterministic active-config serialization."""

from __future__ import annotations

from typing import cast

from agentic_workflow_generator.infrastructure import (
    JsonObject,
)

from .composition import (
    CompiledAgentInstance,
    CompiledArtifactProduction,
    CompiledComposition,
    CompiledRoleBinding,
    CompiledSeparationConstraint,
    CompiledWorkflowGate,
)

ACTIVE_CONFIG_SCHEMA_VERSION = "0.2.0"
GENERATOR_NAME = "agentic-workflow-generator"
GENERATOR_VERSION = "0.1.0"


def composition_to_json_object(
    composition: CompiledComposition,
) -> JsonObject:
    """Serialize canonical composition without legacy authority."""

    return cast(
        JsonObject,
        {
            "$schema": "./schemas/agentic.schema.json",
            "schemaVersion": ACTIVE_CONFIG_SCHEMA_VERSION,
            "project": {
                "name": composition.project.name,
                "type": composition.project.project_type,
                "description": composition.project.description,
                "languageProfiles": list(
                    composition.project.language_profiles
                ),
                "runtimeProfiles": list(
                    composition.project.runtime_profiles
                ),
                "architectureProfile": (
                    composition.project.architecture_profile
                ),
            },
            "generator": {
                "name": GENERATOR_NAME,
                "version": GENERATOR_VERSION,
                "mode": "compiler",
                "runtimeExecution": False,
            },
            "selection": {
                "bundle": {
                    "name": composition.bundle,
                    "version": composition.bundle_version,
                },
                "profile": {
                    "name": composition.profile.name,
                    "version": composition.profile.version,
                },
                "workflow": {
                    "name": composition.workflow.name,
                    "version": composition.workflow.version,
                },
            },
            "targets": [
                {
                    "name": target.name,
                    "enabled": True,
                    "priority": target.priority,
                }
                for target in composition.targets
            ],
            "workflow": {
                "name": composition.workflow.name,
                "version": composition.workflow.version,
                "description": composition.workflow.description,
                "startState": composition.workflow.start_state,
                "terminalStates": list(
                    composition.workflow.terminal_states
                ),
                "defaultFailureState": (
                    composition.workflow.default_failure_state
                ),
                "failClosed": composition.workflow.fail_closed,
                "states": [
                    {
                        "name": state.name,
                        "terminal": state.terminal,
                        "gate": (
                            state.gate.name
                            if state.gate is not None
                            else None
                        ),
                    }
                    for state in composition.workflow.states
                ],
                "transitions": [
                    {
                        "from": transition.source,
                        "to": transition.target,
                        "on": transition.event,
                    }
                    for transition
                    in composition.workflow.transitions
                ],
            },
            "permissionProfiles": [
                {
                    "name": profile.name,
                    "version": profile.version,
                    "description": profile.description,
                    "read": profile.read,
                    "write": profile.write,
                    "edit": profile.edit,
                    "bash": profile.bash.value,
                }
                for profile
                in composition.permission_profiles
            ],
            "skills": [
                {
                    "name": skill.name,
                    "version": skill.version,
                    "description": skill.description,
                    "provides": list(skill.provides),
                    "contentPath": skill.content_path,
                    "contextBudget": {
                        "maxTokens": (
                            skill.context_budget.max_tokens
                        ),
                    },
                    "requiresCapabilities": list(
                        skill.requires_capabilities
                    ),
                }
                for skill in composition.skills
            ],
            "artifacts": [
                {
                    "type": artifact.type,
                    "version": artifact.version,
                    "description": artifact.description,
                    "pathPattern": artifact.path_pattern,
                    "status": {
                        "heading": artifact.status.heading,
                        "pattern": artifact.status.pattern,
                    },
                    "allowedStatuses": list(
                        artifact.allowed_statuses
                    ),
                    "requiredHeadings": list(
                        artifact.required_headings
                    ),
                }
                for artifact in composition.artifacts
            ],
            "agentInstances": [
                _serialize_agent_instance(instance)
                for instance in composition.agent_instances
            ],
            "roleBindings": [
                _serialize_role_binding(binding)
                for binding in composition.role_bindings
            ],
            "stateOwnership": [
                {
                    "workflowState": ownership.workflow_state,
                    "roleBinding": ownership.role_binding,
                    "agentInstance": ownership.agent_instance,
                }
                for ownership in composition.state_ownership
            ],
            "controllerBinding": (
                composition.controller_binding
            ),
            "workflowGates": [
                _serialize_workflow_gate(gate)
                for gate in composition.workflow_gates
            ],
            "artifactProduction": [
                _serialize_artifact_production(production)
                for production
                in composition.artifact_production
            ],
            "separationConstraints": [
                _serialize_separation_constraint(constraint)
                for constraint
                in composition.separation_constraints
            ],
            "runtimeContext": {
                "enabled": composition.runtime_context.enabled,
                "outputDirectory": (
                    composition.runtime_context.output_directory
                ),
                "resolutionDirectory": (
                    composition.runtime_context.resolution_directory
                ),
                "failIfMissing": (
                    composition.runtime_context.fail_if_missing
                ),
            },
            "validation": {
                "failClosed": (
                    composition.validation.fail_closed
                ),
                "requireLockfile": (
                    composition.validation.require_lockfile
                ),
                "requireArtifacts": (
                    composition.validation.require_artifacts
                ),
                "requireEvidence": (
                    composition.validation.require_evidence
                ),
            },
        },
    )


def _serialize_agent_instance(
    instance: CompiledAgentInstance,
) -> JsonObject:
    return cast(
        JsonObject,
        {
            "id": instance.id,
            "profile": {
                "name": instance.profile.name,
                "version": instance.profile.version,
                "role": instance.profile.role,
                "description": instance.profile.description,
            },
            "displayName": instance.display_name,
            "permissionProfile": (
                instance.permission_profile.name
            ),
            "sharedContextPolicy": (
                instance.shared_context_policy.value
            ),
            "roleBindings": list(instance.role_bindings),
            "requiredCapabilities": list(
                instance.required_capabilities
            ),
            "selectedSkills": [
                skill.name
                for skill in instance.selected_skills
            ],
            "produces": [
                artifact.type
                for artifact in instance.produces
            ],
            "responsibilities": list(
                instance.responsibilities
            ),
            "guardrails": list(instance.guardrails),
        },
    )


def _serialize_role_binding(
    binding: CompiledRoleBinding,
) -> JsonObject:
    result = cast(
        JsonObject,
        {
            "roleName": binding.role_name,
            "bindingType": binding.binding_type.value,
            "agentInstance": binding.agent_instance,
            "requiredCapabilities": list(
                binding.required_capabilities
            ),
            "selectedSkills": [
                skill.name
                for skill in binding.selected_skills
            ],
            "providedCapabilities": list(
                binding.provided_capabilities
            ),
            "produces": [
                artifact.type
                for artifact in binding.produces
            ],
            "responsibilities": list(
                binding.responsibilities
            ),
            "guardrails": list(binding.guardrails),
        },
    )

    if binding.workflow_state is not None:
        result["workflowState"] = binding.workflow_state

    if binding.workflow_gate is not None:
        result["workflowGate"] = binding.workflow_gate

    return result


def _serialize_workflow_gate(
    gate: CompiledWorkflowGate,
) -> JsonObject:
    return cast(
        JsonObject,
        {
            "workflowState": gate.workflow_state,
            "name": gate.name,
            "blocking": gate.blocking,
            "ownerRoleBinding": gate.owner_role_binding,
            "ownerAgentInstance": gate.owner_agent_instance,
            "requiredCapabilities": list(
                gate.required_capabilities
            ),
            "requiredArtifacts": [
                artifact.type
                for artifact in gate.required_artifacts
            ],
        },
    )


def _serialize_artifact_production(
    production: CompiledArtifactProduction,
) -> JsonObject:
    return cast(
        JsonObject,
        {
            "artifactType": production.artifact.type,
            "roleBinding": production.role_binding,
            "agentInstance": production.agent_instance,
        },
    )


def _serialize_separation_constraint(
    constraint: CompiledSeparationConstraint,
) -> JsonObject:
    return cast(
        JsonObject,
        {
            "id": constraint.id,
            "mode": constraint.mode.value,
            "roleBindings": list(
                constraint.role_bindings
            ),
            "agentInstances": list(
                constraint.agent_instances
            ),
            "requireDistinctInstances": (
                constraint.require_distinct_instances
            ),
            "reason": constraint.reason,
        },
    )
