from dataclasses import replace
from pathlib import Path

from jsonschema.exceptions import ValidationError

import agentic_workflow_generator.validation.bundles as bundles_module
from agentic_workflow_generator.infrastructure import (
    JsonObject,
    read_json_object,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.bundles import (
    ARTIFACT_OUTSIDE_BUNDLE_DIAGNOSTIC,
    CONTROLLER_DIAGNOSTIC,
    DUPLICATE_BUNDLE_DIAGNOSTIC,
    DUPLICATE_INSTANCE_DIAGNOSTIC,
    DUPLICATE_ROLE_BINDING_DIAGNOSTIC,
    DUPLICATE_SEPARATION_POLICY_DIAGNOSTIC,
    DUPLICATE_STATE_OWNER_DIAGNOSTIC,
    FILE_NAME_DIAGNOSTIC,
    INPUT_ARTIFACT_CONTROLLER_DIAGNOSTIC,
    INPUT_ARTIFACT_CYCLE_DIAGNOSTIC,
    INPUT_ARTIFACT_OUTSIDE_BUNDLE_DIAGNOSTIC,
    INPUT_ARTIFACT_PRODUCER_MISMATCH_DIAGNOSTIC,
    INPUT_ARTIFACT_SELF_REFERENCE_DIAGNOSTIC,
    MISSING_GATE_ARTIFACT_DIAGNOSTIC,
    MISSING_GATE_CAPABILITY_DIAGNOSTIC,
    MISSING_STATE_OWNER_DIAGNOSTIC,
    OBSOLETE_FIELD_DIAGNOSTIC,
    SCHEMA_DIAGNOSTIC,
    SEPARATION_INSTANCE_DIAGNOSTIC,
    SKILL_OUTSIDE_BUNDLE_DIAGNOSTIC,
    UNASSIGNED_INSTANCE_DIAGNOSTIC,
    UNKNOWN_AGENT_PROFILE_DIAGNOSTIC,
    UNKNOWN_ARTIFACT_DIAGNOSTIC,
    UNKNOWN_INPUT_ARTIFACT_DIAGNOSTIC,
    UNKNOWN_INPUT_ROLE_BINDING_DIAGNOSTIC,
    UNKNOWN_INSTANCE_DIAGNOSTIC,
    UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC,
    UNKNOWN_PRODUCED_ARTIFACT_DIAGNOSTIC,
    UNKNOWN_PROFILE_DIAGNOSTIC,
    UNKNOWN_SELECTED_SKILL_DIAGNOSTIC,
    UNKNOWN_SEPARATION_BINDING_DIAGNOSTIC,
    UNKNOWN_SKILL_DIAGNOSTIC,
    UNKNOWN_TARGET_DIAGNOSTIC,
    UNKNOWN_WORKFLOW_DIAGNOSTIC,
    UNPRODUCED_BUNDLE_ARTIFACT_DIAGNOSTIC,
    UNPRODUCED_CONTRACT_DIAGNOSTIC,
    UNPROVIDED_CAPABILITY_DIAGNOSTIC,
    UNSATISFIED_SKILL_REQUIREMENT_DIAGNOSTIC,
    WORKFLOW_GATE_DIAGNOSTIC,
    WORKFLOW_STATE_DIAGNOSTIC,
    BundleReferenceData,
    BundleValidationResult,
    ProjectedSkill,
    ProjectedWorkflow,
    ProjectedWorkflowGate,
    ProjectedWorkflowState,
    validate_bundle_registry,
)

REPOSITORY_ROOT = Path(__file__).parents[3]
SCHEMA = read_json_object(
    REPOSITORY_ROOT / ".agentic" / "schemas" / "registry" / "bundle.schema.json"
)


def bundle_data() -> JsonObject:
    return {
        "name": "lean-delivery",
        "description": "Lean delivery bundle.",
        "version": "0.2.0",
        "profile": "lean-delivery",
        "workflow": "lean-delivery",
        "agentInstances": [
            {
                "id": "requirements-worker",
                "profile": "Requirements",
                "displayName": "Requirements",
                "permissionProfile": "read-only",
                "sharedContextPolicy": ("shared-with-assigned-bindings"),
            },
            {
                "id": "workflow-controller",
                "profile": "Orchestrator",
                "displayName": "Orchestrator",
                "permissionProfile": "read-only",
                "sharedContextPolicy": ("shared-with-assigned-bindings"),
            },
        ],
        "roleBindings": [
            {
                "roleName": "requirements",
                "bindingType": "state-owner",
                "agentInstance": "requirements-worker",
                "workflowState": "Requirements",
                "workflowGate": "requirements-review",
                "requiredCapabilities": [
                    "requirements.elicit",
                ],
                "selectedSkills": [
                    "requirements-analysis",
                ],
                "produces": [
                    "Requirements",
                ],
                "inputArtifacts": [],
                "responsibilities": [
                    "Clarify requirements",
                ],
                "guardrails": [
                    "Do not implement",
                ],
            },
            {
                "roleName": "workflow-controller",
                "bindingType": "workflow-controller",
                "agentInstance": "workflow-controller",
                "requiredCapabilities": [
                    "workflow.route",
                ],
                "selectedSkills": [
                    "workflow-routing",
                ],
                "produces": [],
                "inputArtifacts": [],
                "responsibilities": [
                    "Route work",
                ],
                "guardrails": [
                    "Do not override gates",
                ],
            },
        ],
        "separationPolicies": [
            {
                "id": "role-independence",
                "mode": "required",
                "roleBindings": [
                    "requirements",
                    "workflow-controller",
                ],
                "requireDistinctInstances": True,
                "reason": ("Routing authority must remain independent."),
            }
        ],
        "skills": [
            "requirements-analysis",
            "workflow-routing",
        ],
        "artifacts": [
            "Requirements",
        ],
        "targets": [
            "opencode",
        ],
    }


def source(
    *,
    data: JsonObject | None = None,
    filename: str = "lean-delivery.bundle.json",
) -> RegistrySource:
    return RegistrySource(
        kind=RegistryKind.BUNDLE,
        source_path=Path(f"registry/bundles/{filename}"),
        data=bundle_data() if data is None else data,
    )


def references(
    *,
    artifact_contracts: tuple[
        tuple[str, str],
        ...,
    ] = (
        (
            "Requirements",
            ("registry/artifacts/Requirements/artifact.json"),
        ),
    ),
) -> BundleReferenceData:
    return BundleReferenceData(
        profiles=frozenset(
            {
                "lean-delivery",
            }
        ),
        workflows=(
            ProjectedWorkflow(
                name="lean-delivery",
                states=(
                    ProjectedWorkflowState(
                        name="Requirements",
                        terminal=False,
                        gate=ProjectedWorkflowGate(
                            name="requirements-review",
                            required_capabilities=(
                                frozenset(
                                    {
                                        "requirements.elicit",
                                    }
                                )
                            ),
                            required_artifacts=(
                                frozenset(
                                    {
                                        "Requirements",
                                    }
                                )
                            ),
                            required_test_evidence=frozenset(),
                        ),
                    ),
                    ProjectedWorkflowState(
                        name="Done",
                        terminal=True,
                        gate=None,
                    ),
                    ProjectedWorkflowState(
                        name="Blocked",
                        terminal=True,
                        gate=None,
                    ),
                ),
            ),
        ),
        agent_profiles=frozenset(
            {
                "Requirements",
                "Orchestrator",
            }
        ),
        skills=(
            ProjectedSkill(
                name="requirements-analysis",
                provides=frozenset(
                    {
                        "requirements.elicit",
                    }
                ),
                requires=frozenset(),
            ),
            ProjectedSkill(
                name="workflow-routing",
                provides=frozenset(
                    {
                        "workflow.route",
                    }
                ),
                requires=frozenset(),
            ),
        ),
        artifact_contracts=artifact_contracts,
        permission_profiles=frozenset(
            {
                "read-only",
            }
        ),
        targets=frozenset(
            {
                "opencode",
            }
        ),
    )


def validate(
    *sources: RegistrySource,
    reference_data: BundleReferenceData | None = None,
) -> BundleValidationResult:
    return validate_bundle_registry(
        tuple(sources),
        SCHEMA,
        (references() if reference_data is None else reference_data),
    )


def diagnostic_codes(
    result: BundleValidationResult,
) -> set[str]:
    return {diagnostic.code for diagnostic in result.diagnostics}


def test_profile_recommendation_does_not_constrain_bundle_workflow() -> None:
    data = bundle_data()
    data["profile"] = "microservice-platform"
    reference_data = replace(
        references(),
        profiles=frozenset(
            {
                "lean-delivery",
                "microservice-platform",
            }
        ),
    )

    result = validate(
        source(data=data),
        reference_data=reference_data,
    )

    assert result.is_valid
    assert not result.diagnostics


def test_valid_bundle_is_parsed() -> None:
    result = validate(source())

    assert result.is_valid
    assert result.diagnostics == ()
    assert len(result.bundles) == 1

    bundle = result.bundles[0]
    assert bundle.name == "lean-delivery"
    assert bundle.profile == "lean-delivery"
    assert bundle.workflow == "lean-delivery"
    assert bundle.agent_instances[0].id == "requirements-worker"
    assert bundle.role_bindings[0].workflow_state == "Requirements"
    assert bundle.role_bindings[0].workflow_gate == "requirements-review"
    assert bundle.role_bindings[0].produces == ("Requirements",)
    assert bundle.role_bindings[0].input_artifacts == ()
    assert bundle.role_bindings[1].input_artifacts == ()
    assert bundle.role_bindings[1].workflow_state is None
    assert bundle.separation_policies[0].role_bindings == (
        "requirements",
        "workflow-controller",
    )




def test_missing_input_artifacts_fails_schema_validation() -> None:
    data = bundle_data()
    binding = _object_entry(data, "roleBindings", 0)
    del binding["inputArtifacts"]
    result = validate(source(data=data))
    assert result.bundles == ()
    assert SCHEMA_DIAGNOSTIC in diagnostic_codes(result)


def test_duplicate_input_artifact_reference_fails_schema_validation() -> None:
    data = bundle_data()
    binding = _object_entry(data, "roleBindings", 0)
    reference: JsonObject = {
        "artifactType": "Requirements",
        "roleBinding": "requirements",
    }
    binding["inputArtifacts"] = [reference, dict(reference)]
    result = validate(source(data=data))
    assert result.bundles == ()
    assert SCHEMA_DIAGNOSTIC in diagnostic_codes(result)


def test_controller_input_artifacts_must_be_empty() -> None:
    data = bundle_data()
    controller = _object_entry(data, "roleBindings", 1)
    controller["inputArtifacts"] = [
        {
            "artifactType": "Requirements",
            "roleBinding": "requirements",
        }
    ]
    result = validate(source(data=data))
    assert result.bundles == ()
    assert SCHEMA_DIAGNOSTIC in diagnostic_codes(result)


def test_input_artifact_unknown_artifact_fails_closed() -> None:
    data = bundle_data()
    binding = _object_entry(data, "roleBindings", 0)
    binding["inputArtifacts"] = [
        {
            "artifactType": "MissingArtifact",
            "roleBinding": "workflow-controller",
        }
    ]
    result = validate(source(data=data))
    codes = diagnostic_codes(result)
    assert UNKNOWN_INPUT_ARTIFACT_DIAGNOSTIC in codes
    assert INPUT_ARTIFACT_OUTSIDE_BUNDLE_DIAGNOSTIC in codes


def test_input_artifact_unknown_role_binding_fails_closed() -> None:
    data = bundle_data()
    binding = _object_entry(data, "roleBindings", 0)
    binding["inputArtifacts"] = [
        {
            "artifactType": "Requirements",
            "roleBinding": "missing-producer",
        }
    ]
    result = validate(source(data=data))
    assert UNKNOWN_INPUT_ROLE_BINDING_DIAGNOSTIC in diagnostic_codes(result)


def test_input_artifact_self_reference_fails_closed() -> None:
    data = bundle_data()
    binding = _object_entry(data, "roleBindings", 0)
    binding["inputArtifacts"] = [
        {
            "artifactType": "Requirements",
            "roleBinding": "requirements",
        }
    ]
    result = validate(source(data=data))
    assert INPUT_ARTIFACT_SELF_REFERENCE_DIAGNOSTIC in diagnostic_codes(result)


def test_input_artifact_controller_and_mismatch_fail_closed() -> None:
    data = bundle_data()
    binding = _object_entry(data, "roleBindings", 0)
    binding["inputArtifacts"] = [
        {
            "artifactType": "Requirements",
            "roleBinding": "workflow-controller",
        }
    ]
    result = validate(source(data=data))
    codes = diagnostic_codes(result)
    assert INPUT_ARTIFACT_CONTROLLER_DIAGNOSTIC in codes
    assert INPUT_ARTIFACT_PRODUCER_MISMATCH_DIAGNOSTIC in codes


def test_input_artifact_dependency_cycle_fails_closed() -> None:
    data = bundle_data()
    requirements = _object_entry(data, "roleBindings", 0)
    requirements["inputArtifacts"] = [
        {
            "artifactType": "Requirements",
            "roleBinding": "peer",
        }
    ]
    instances = data["agentInstances"]
    assert isinstance(instances, list)
    instances.append(
        {
            "id": "peer-worker",
            "profile": "Requirements",
            "displayName": "Peer",
            "permissionProfile": "read-only",
            "sharedContextPolicy": "shared-with-assigned-bindings",
        }
    )
    bindings = data["roleBindings"]
    assert isinstance(bindings, list)
    bindings.insert(
        1,
        {
            "roleName": "peer",
            "bindingType": "state-owner",
            "agentInstance": "peer-worker",
            "workflowState": "Peer",
            "workflowGate": "peer-review",
            "requiredCapabilities": ["requirements.elicit"],
            "selectedSkills": ["requirements-analysis"],
            "produces": ["Requirements"],
            "inputArtifacts": [
                {
                    "artifactType": "Requirements",
                    "roleBinding": "requirements",
                }
            ],
            "responsibilities": ["Peer review requirements"],
            "guardrails": ["Do not implement"],
        },
    )
    base_references = references()
    workflow = base_references.workflows[0]
    peer_state = ProjectedWorkflowState(
        name="Peer",
        terminal=False,
        gate=ProjectedWorkflowGate(
            name="peer-review",
            required_capabilities=frozenset({"requirements.elicit"}),
            required_artifacts=frozenset({"Requirements"}),
            required_test_evidence=frozenset(),
        ),
    )
    reference_data = replace(
        base_references,
        workflows=(
            replace(
                workflow,
                states=(
                    workflow.states[0],
                    peer_state,
                    *workflow.states[1:],
                ),
            ),
        ),
    )
    result = validate(source(data=data), reference_data=reference_data)
    assert INPUT_ARTIFACT_CYCLE_DIAGNOSTIC in diagnostic_codes(result)

def test_file_name_must_match_bundle_name() -> None:
    result = validate(
        source(
            filename="different.bundle.json",
        )
    )

    assert FILE_NAME_DIAGNOSTIC in diagnostic_codes(result)


def test_obsolete_agents_field_is_rejected() -> None:
    data = bundle_data()
    data["agents"] = [
        "Requirements",
    ]

    result = validate(source(data=data))

    assert result.bundles == ()
    assert result.diagnostics[0].code == OBSOLETE_FIELD_DIAGNOSTIC
    assert result.diagnostics[0].location == "agents"


def test_unknown_top_level_references_are_rejected() -> None:
    data = bundle_data()
    data["profile"] = "missing-profile"
    data["workflow"] = "missing-workflow"

    result = validate(source(data=data))

    codes = diagnostic_codes(result)
    assert UNKNOWN_PROFILE_DIAGNOSTIC in codes
    assert UNKNOWN_WORKFLOW_DIAGNOSTIC in codes


def test_unknown_instance_dependencies_are_rejected() -> None:
    data = bundle_data()
    instances = data["agentInstances"]
    assert isinstance(instances, list)

    first = instances[0]
    assert isinstance(first, dict)

    first["profile"] = "MissingAgent"
    first["permissionProfile"] = "missing-permission"

    result = validate(source(data=data))

    codes = diagnostic_codes(result)
    assert UNKNOWN_AGENT_PROFILE_DIAGNOSTIC in codes
    assert UNKNOWN_PERMISSION_PROFILE_DIAGNOSTIC in codes


def test_duplicate_agent_instance_id_is_rejected() -> None:
    data = bundle_data()
    instances = data["agentInstances"]
    assert isinstance(instances, list)

    second = instances[1]
    assert isinstance(second, dict)
    second["id"] = "requirements-worker"

    result = validate(source(data=data))

    assert DUPLICATE_INSTANCE_DIAGNOSTIC in diagnostic_codes(result)


def test_bundle_requires_exactly_one_controller() -> None:
    data = bundle_data()
    bindings = data["roleBindings"]
    assert isinstance(bindings, list)

    data["roleBindings"] = [
        bindings[0],
    ]

    result = validate(source(data=data))

    assert CONTROLLER_DIAGNOSTIC in diagnostic_codes(result)


def test_separation_requires_distinct_instances() -> None:
    data = bundle_data()
    bindings = data["roleBindings"]
    assert isinstance(bindings, list)

    controller = bindings[1]
    assert isinstance(controller, dict)
    controller["agentInstance"] = "requirements-worker"

    result = validate(source(data=data))

    assert SEPARATION_INSTANCE_DIAGNOSTIC in diagnostic_codes(result)


def test_every_artifact_contract_requires_producer() -> None:
    reference_data = references(
        artifact_contracts=(
            (
                "Requirements",
                ("registry/artifacts/Requirements/artifact.json"),
            ),
            (
                "TestReport",
                ("registry/artifacts/TestReport/artifact.json"),
            ),
        )
    )

    result = validate(
        source(),
        reference_data=reference_data,
    )

    diagnostics = [
        diagnostic
        for diagnostic in result.diagnostics
        if (diagnostic.code == UNPRODUCED_CONTRACT_DIAGNOSTIC)
    ]

    assert len(diagnostics) == 1
    assert diagnostics[0].source_path == ("registry/artifacts/TestReport/artifact.json")
    assert diagnostics[0].related_identities == ("TestReport",)


def _object_entry(
    data: JsonObject,
    key: str,
    index: int,
) -> JsonObject:
    values = data[key]
    assert isinstance(values, list)

    value = values[index]
    assert isinstance(value, dict)

    return value


def _append_object(
    data: JsonObject,
    key: str,
    value: JsonObject,
) -> None:
    values = data[key]
    assert isinstance(values, list)
    values.append(value)


def _references_with_test_report() -> BundleReferenceData:
    return references(
        artifact_contracts=(
            (
                "Requirements",
                ("registry/artifacts/Requirements/artifact.json"),
            ),
            (
                "TestReport",
                ("registry/artifacts/TestReport/artifact.json"),
            ),
        )
    )


def test_schema_invalid_bundle_stops_parsing() -> None:
    data = bundle_data()
    del data["description"]

    result = validate(source(data=data))

    assert result.bundles == ()
    assert SCHEMA_DIAGNOSTIC in diagnostic_codes(result)
    assert UNPRODUCED_CONTRACT_DIAGNOSTIC not in diagnostic_codes(result)


def test_unknown_bundle_collections_are_rejected() -> None:
    data = bundle_data()
    data["skills"] = [
        "missing-skill",
    ]
    data["artifacts"] = [
        "MissingArtifact",
    ]
    data["targets"] = [
        "missing-target",
    ]

    result = validate(source(data=data))

    codes = diagnostic_codes(result)
    assert UNKNOWN_SKILL_DIAGNOSTIC in codes
    assert UNKNOWN_ARTIFACT_DIAGNOSTIC in codes
    assert UNKNOWN_TARGET_DIAGNOSTIC in codes


def test_declared_bundle_artifact_requires_producer() -> None:
    data = bundle_data()
    artifacts = data["artifacts"]
    assert isinstance(artifacts, list)
    artifacts.append("TestReport")

    result = validate(
        source(data=data),
        reference_data=(_references_with_test_report()),
    )

    assert UNPRODUCED_BUNDLE_ARTIFACT_DIAGNOSTIC in diagnostic_codes(result)


def test_duplicate_role_binding_name_is_rejected() -> None:
    data = bundle_data()
    duplicate = dict(
        _object_entry(
            data,
            "roleBindings",
            0,
        )
    )
    duplicate["responsibilities"] = [
        "Duplicate assignment",
    ]
    _append_object(
        data,
        "roleBindings",
        duplicate,
    )

    result = validate(source(data=data))

    assert DUPLICATE_ROLE_BINDING_DIAGNOSTIC in diagnostic_codes(result)


def test_selected_skill_must_belong_to_bundle() -> None:
    data = bundle_data()
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["selectedSkills"] = [
        "external-requirements",
    ]

    base_references = references()
    reference_data = replace(
        base_references,
        skills=(
            *base_references.skills,
            ProjectedSkill(
                name="external-requirements",
                provides=frozenset(
                    {
                        "requirements.elicit",
                    }
                ),
                requires=frozenset(),
            ),
        ),
    )

    result = validate(
        source(data=data),
        reference_data=reference_data,
    )

    assert SKILL_OUTSIDE_BUNDLE_DIAGNOSTIC in diagnostic_codes(result)


def test_selected_skill_must_be_registered() -> None:
    data = bundle_data()
    skills = data["skills"]
    assert isinstance(skills, list)
    skills.append("missing-skill")

    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["selectedSkills"] = [
        "missing-skill",
    ]

    result = validate(source(data=data))

    assert UNKNOWN_SELECTED_SKILL_DIAGNOSTIC in diagnostic_codes(result)


def test_binding_capabilities_require_selected_provider() -> None:
    data = bundle_data()
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["requiredCapabilities"] = [
        "missing.capability",
    ]

    result = validate(source(data=data))

    assert UNPROVIDED_CAPABILITY_DIAGNOSTIC in diagnostic_codes(result)


def test_selected_skill_requirements_must_be_satisfied() -> None:
    reference_data = replace(
        references(),
        skills=(
            ProjectedSkill(
                name="requirements-analysis",
                provides=frozenset(
                    {
                        "requirements.elicit",
                    }
                ),
                requires=frozenset(
                    {
                        "workflow.route",
                    }
                ),
            ),
            ProjectedSkill(
                name="workflow-routing",
                provides=frozenset(
                    {
                        "workflow.route",
                    }
                ),
                requires=frozenset(),
            ),
        ),
    )

    result = validate(
        source(),
        reference_data=reference_data,
    )

    assert UNSATISFIED_SKILL_REQUIREMENT_DIAGNOSTIC in diagnostic_codes(result)


def test_produced_artifact_must_belong_to_bundle() -> None:
    data = bundle_data()
    data["artifacts"] = [
        "TestReport",
    ]

    result = validate(
        source(data=data),
        reference_data=(_references_with_test_report()),
    )

    assert ARTIFACT_OUTSIDE_BUNDLE_DIAGNOSTIC in diagnostic_codes(result)


def test_produced_artifact_must_be_registered() -> None:
    data = bundle_data()
    data["artifacts"] = [
        "MissingArtifact",
    ]
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["produces"] = [
        "MissingArtifact",
    ]

    result = validate(source(data=data))

    assert UNKNOWN_PRODUCED_ARTIFACT_DIAGNOSTIC in diagnostic_codes(result)


def test_controller_must_not_produce_artifacts() -> None:
    data = bundle_data()
    controller = _object_entry(
        data,
        "roleBindings",
        1,
    )
    controller["produces"] = [
        "Requirements",
    ]

    result = validate(source(data=data))

    assert CONTROLLER_DIAGNOSTIC in diagnostic_codes(result)


def test_every_non_terminal_state_requires_owner() -> None:
    data = bundle_data()
    bindings = data["roleBindings"]
    assert isinstance(bindings, list)
    data["roleBindings"] = [
        bindings[1],
    ]

    result = validate(source(data=data))

    assert MISSING_STATE_OWNER_DIAGNOSTIC in diagnostic_codes(result)


def test_state_owner_must_reference_existing_state() -> None:
    data = bundle_data()
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["workflowState"] = "MissingState"

    result = validate(source(data=data))

    assert WORKFLOW_STATE_DIAGNOSTIC in diagnostic_codes(result)


def test_terminal_state_cannot_have_owner() -> None:
    data = bundle_data()
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["workflowState"] = "Done"

    result = validate(source(data=data))

    assert WORKFLOW_STATE_DIAGNOSTIC in diagnostic_codes(result)


def test_workflow_state_has_exactly_one_owner() -> None:
    data = bundle_data()
    duplicate = dict(
        _object_entry(
            data,
            "roleBindings",
            0,
        )
    )
    duplicate["roleName"] = "requirements-secondary"
    duplicate["agentInstance"] = "workflow-controller"
    duplicate["responsibilities"] = [
        "Secondary ownership",
    ]
    _append_object(
        data,
        "roleBindings",
        duplicate,
    )

    result = validate(source(data=data))

    assert DUPLICATE_STATE_OWNER_DIAGNOSTIC in diagnostic_codes(result)


def test_state_owner_gate_must_match_workflow() -> None:
    data = bundle_data()
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["workflowGate"] = "wrong-gate"

    result = validate(source(data=data))

    assert WORKFLOW_GATE_DIAGNOSTIC in diagnostic_codes(result)


def test_state_owner_requires_every_gate_capability() -> None:
    data = bundle_data()
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["requiredCapabilities"] = [
        "workflow.route",
    ]

    result = validate(source(data=data))

    assert MISSING_GATE_CAPABILITY_DIAGNOSTIC in diagnostic_codes(result)


def test_state_owner_produces_every_gate_artifact() -> None:
    data = bundle_data()
    artifacts = data["artifacts"]
    assert isinstance(artifacts, list)
    artifacts.append("TestReport")

    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["produces"] = [
        "TestReport",
    ]

    result = validate(
        source(data=data),
        reference_data=(_references_with_test_report()),
    )

    assert MISSING_GATE_ARTIFACT_DIAGNOSTIC in diagnostic_codes(result)


def test_separation_policy_ids_are_unique() -> None:
    data = bundle_data()
    duplicate = dict(
        _object_entry(
            data,
            "separationPolicies",
            0,
        )
    )
    duplicate["reason"] = "Duplicate policy declaration."
    _append_object(
        data,
        "separationPolicies",
        duplicate,
    )

    result = validate(source(data=data))

    assert DUPLICATE_SEPARATION_POLICY_DIAGNOSTIC in diagnostic_codes(result)


def test_bundle_names_are_globally_unique() -> None:
    result = validate(
        source(),
        source(
            filename=("duplicate.bundle.json"),
        ),
    )

    assert DUPLICATE_BUNDLE_DIAGNOSTIC in diagnostic_codes(result)


def test_unassigned_agent_instance_is_rejected() -> None:
    data = bundle_data()
    instances = data["agentInstances"]
    assert isinstance(instances, list)

    template = instances[0]
    assert isinstance(template, dict)

    orphan = dict(template)
    orphan["id"] = "orphan-worker"
    orphan["displayName"] = "Orphan Worker"
    instances.append(orphan)

    result = validate(source(data=data))

    assert UNASSIGNED_INSTANCE_DIAGNOSTIC in diagnostic_codes(result)


def test_binding_instance_must_exist() -> None:
    data = bundle_data()
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    binding["agentInstance"] = "missing-instance"

    result = validate(source(data=data))

    assert UNKNOWN_INSTANCE_DIAGNOSTIC in diagnostic_codes(result)


def test_state_owner_requires_workflow_state() -> None:
    data = bundle_data()
    binding = _object_entry(
        data,
        "roleBindings",
        0,
    )
    del binding["workflowState"]

    result = validate(source(data=data))

    assert result.bundles == ()
    assert SCHEMA_DIAGNOSTIC in diagnostic_codes(result)


def test_controller_must_not_own_workflow_state() -> None:
    data = bundle_data()
    controller = _object_entry(
        data,
        "roleBindings",
        1,
    )
    controller["workflowState"] = "Requirements"

    result = validate(source(data=data))

    assert result.bundles == ()
    assert SCHEMA_DIAGNOSTIC in diagnostic_codes(result)


def test_separation_policy_binding_must_exist() -> None:
    data = bundle_data()
    policy = _object_entry(
        data,
        "separationPolicies",
        0,
    )
    role_bindings = policy["roleBindings"]
    assert isinstance(role_bindings, list)
    role_bindings.append("missing-role")

    result = validate(source(data=data))

    assert UNKNOWN_SEPARATION_BINDING_DIAGNOSTIC in diagnostic_codes(result)


def test_bundle_missing_required_field_wrapper_delegates() -> None:
    error = ValidationError(
        "name is required",
        validator="required",
        validator_value=["name"],
        instance={},
    )

    assert (
        bundles_module._missing_required_field(error)
        == "name"
    )
