from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.bundles import (
    BundleDependencyProjectionError,
    ProjectedSkill,
    ProjectedWorkflow,
    ProjectedWorkflowGate,
    ProjectedWorkflowState,
    _schema_error_location,
    _schema_error_message,
    _schema_error_sort_key,
    project_agent_profile_names,
    project_artifact_contracts,
    project_permission_profile_names,
    project_profile_names,
    project_skills,
    project_target_names,
    project_workflows,
)


def registry_source(
    kind: RegistryKind,
    path: str,
    data: JsonObject,
) -> RegistrySource:
    return RegistrySource(
        kind=kind,
        source_path=Path(path),
        data=data,
    )


def named_source(
    kind: RegistryKind,
    name: JsonValue,
    *,
    suffix: str,
) -> RegistrySource:
    return registry_source(
        kind,
        f"registry/{kind.directory_name}/{suffix}",
        {
            "name": name,
        },
    )


def skill_source(
    name: JsonValue = "workflow-routing",
    *,
    provides: JsonValue = None,
    requires: JsonValue = None,
    folder: str = "workflow-routing",
) -> RegistrySource:
    if provides is None:
        provides = [
            "workflow.route",
        ]

    if requires is None:
        requires = []

    return registry_source(
        RegistryKind.SKILL,
        f"registry/skills/{folder}/skill.json",
        {
            "name": name,
            "provides": provides,
            "requiresCapabilities": requires,
        },
    )


def artifact_source(
    artifact_type: JsonValue = "Requirements",
    *,
    folder: str = "Requirements",
) -> RegistrySource:
    return registry_source(
        RegistryKind.ARTIFACT,
        f"registry/artifacts/{folder}/artifact.json",
        {
            "type": artifact_type,
        },
    )


def workflow_source(
    *,
    name: JsonValue = "lean-delivery",
    states: JsonValue = None,
    filename: str = "lean-delivery.workflow.json",
) -> RegistrySource:
    if states is None:
        states = [
            {
                "name": "Requirements",
                "gate": {
                    "name": "requirements-review",
                    "requiredCapabilities": [
                        "requirements.elicit",
                    ],
                    "requiredArtifacts": [
                        "Requirements",
                    ],
                },
            },
            {
                "name": "Done",
                "terminal": True,
            },
        ]

    return registry_source(
        RegistryKind.WORKFLOW,
        f"registry/workflows/{filename}",
        {
            "name": name,
            "states": states,
        },
    )


@pytest.mark.parametrize(
    ("projector", "kind", "path"),
    [
        (
            project_profile_names,
            RegistryKind.PROFILE,
            "lean.profile.json",
        ),
        (
            project_agent_profile_names,
            RegistryKind.AGENT,
            "Requirements/agent.json",
        ),
        (
            project_permission_profile_names,
            RegistryKind.PERMISSION_PROFILE,
            "read-only/permission-profile.json",
        ),
        (
            project_target_names,
            RegistryKind.TARGET,
            "opencode/adapter.json",
        ),
    ],
)
def test_identity_projections_return_unique_names(
    projector: Callable[
        [tuple[RegistrySource, ...]],
        frozenset[str],
    ],
    kind: RegistryKind,
    path: str,
) -> None:
    sources = (
        named_source(
            kind,
            "beta",
            suffix=f"beta-{path}",
        ),
        named_source(
            kind,
            "alpha",
            suffix=f"alpha-{path}",
        ),
    )

    assert projector(sources) == frozenset(
        {
            "alpha",
            "beta",
        }
    )


@pytest.mark.parametrize(
    ("projector", "kind", "path"),
    [
        (
            project_profile_names,
            RegistryKind.PROFILE,
            "profile.json",
        ),
        (
            project_agent_profile_names,
            RegistryKind.AGENT,
            "agent.json",
        ),
        (
            project_permission_profile_names,
            RegistryKind.PERMISSION_PROFILE,
            "permission-profile.json",
        ),
        (
            project_target_names,
            RegistryKind.TARGET,
            "adapter.json",
        ),
    ],
)
def test_identity_projections_reject_duplicate_names(
    projector: Callable[
        [tuple[RegistrySource, ...]],
        frozenset[str],
    ],
    kind: RegistryKind,
    path: str,
) -> None:
    sources = (
        named_source(
            kind,
            "duplicate",
            suffix=f"first-{path}",
        ),
        named_source(
            kind,
            "duplicate",
            suffix=f"second-{path}",
        ),
    )

    with pytest.raises(
        BundleDependencyProjectionError,
        match="name 'duplicate' is duplicated",
    ):
        projector(sources)


@pytest.mark.parametrize(
    "invalid_name",
    [
        None,
        1,
        "",
        " ",
    ],
)
def test_identity_projection_requires_non_empty_string(
    invalid_name: JsonValue,
) -> None:
    source = named_source(
        RegistryKind.PROFILE,
        invalid_name,
        suffix="invalid.profile.json",
    )

    with pytest.raises(
        BundleDependencyProjectionError,
        match="name must be a non-empty string",
    ):
        project_profile_names((source,))


def test_skill_projection_is_deterministic() -> None:
    result = project_skills(
        (
            skill_source(
                "workflow-routing",
                provides=[
                    "workflow.route",
                ],
                folder="workflow-routing",
            ),
            skill_source(
                "requirements-analysis",
                provides=[
                    "requirements.elicit",
                ],
                requires=[
                    "workflow.route",
                ],
                folder="requirements-analysis",
            ),
        )
    )

    assert result == (
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
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "provides",
            None,
            "provides must be a list",
        ),
        (
            "provides",
            [],
            "provides must be a non-empty list",
        ),
        (
            "provides",
            [
                "",
            ],
            "provides\\[0\\] must be a non-empty string",
        ),
        (
            "requiresCapabilities",
            "invalid",
            "requiresCapabilities must be a list",
        ),
        (
            "requiresCapabilities",
            [
                None,
            ],
            ("requiresCapabilities\\[0\\] must be a non-empty string"),
        ),
    ],
)
def test_skill_projection_rejects_invalid_capability_lists(
    field: str,
    value: JsonValue,
    message: str,
) -> None:
    data: JsonObject = {
        "name": "workflow-routing",
        "provides": [
            "workflow.route",
        ],
        "requiresCapabilities": [],
    }
    data[field] = value

    source = registry_source(
        RegistryKind.SKILL,
        "registry/skills/workflow-routing/skill.json",
        data,
    )

    with pytest.raises(
        BundleDependencyProjectionError,
        match=message,
    ):
        project_skills((source,))


def test_skill_projection_rejects_duplicate_identity() -> None:
    with pytest.raises(
        BundleDependencyProjectionError,
        match="identity 'duplicate' is duplicated",
    ):
        project_skills(
            (
                skill_source(
                    "duplicate",
                    folder="first",
                ),
                skill_source(
                    "duplicate",
                    folder="second",
                ),
            )
        )


def test_artifact_projection_is_deterministic() -> None:
    result = project_artifact_contracts(
        (
            artifact_source(
                "TestReport",
                folder="TestReport",
            ),
            artifact_source(),
        )
    )

    assert result == (
        (
            "Requirements",
            ("registry/artifacts/Requirements/artifact.json"),
        ),
        (
            "TestReport",
            ("registry/artifacts/TestReport/artifact.json"),
        ),
    )


def test_artifact_projection_rejects_duplicate_identity() -> None:
    with pytest.raises(
        BundleDependencyProjectionError,
        match="identity 'Requirements' is duplicated",
    ):
        project_artifact_contracts(
            (
                artifact_source(
                    folder="first",
                ),
                artifact_source(
                    folder="second",
                ),
            )
        )


def test_workflow_projection_is_deterministic() -> None:
    result = project_workflows(
        (
            workflow_source(
                name="zeta",
                filename="zeta.workflow.json",
            ),
            workflow_source(
                name="alpha",
                filename="alpha.workflow.json",
            ),
        )
    )

    expected_states = (
        ProjectedWorkflowState(
            name="Requirements",
            terminal=False,
            gate=ProjectedWorkflowGate(
                name="requirements-review",
                required_capabilities=frozenset(
                    {
                        "requirements.elicit",
                    }
                ),
                required_artifacts=frozenset(
                    {
                        "Requirements",
                    }
                ),
            ),
        ),
        ProjectedWorkflowState(
            name="Done",
            terminal=True,
            gate=None,
        ),
    )

    assert result == (
        ProjectedWorkflow(
            name="alpha",
            states=expected_states,
        ),
        ProjectedWorkflow(
            name="zeta",
            states=expected_states,
        ),
    )


@pytest.mark.parametrize(
    ("states", "message"),
    [
        (
            None,
            "states must be a non-empty list",
        ),
        (
            [],
            "states must be a non-empty list",
        ),
        (
            [
                "invalid",
            ],
            "states\\[0\\] must be an object",
        ),
        (
            [
                {
                    "name": "",
                    "terminal": True,
                },
            ],
            "states\\[0\\]\\.name must be a non-empty string",
        ),
        (
            [
                {
                    "name": "Requirements",
                },
            ],
            "states\\[0\\]\\.gate must be an object",
        ),
        (
            [
                {
                    "name": "Requirements",
                    "gate": {
                        "name": "",
                        "requiredCapabilities": [
                            "requirements.elicit",
                        ],
                        "requiredArtifacts": [
                            "Requirements",
                        ],
                    },
                },
            ],
            ("states\\[0\\]\\.gate\\.name must be a non-empty string"),
        ),
        (
            [
                {
                    "name": "Requirements",
                    "gate": {
                        "name": "requirements-review",
                        "requiredCapabilities": [],
                        "requiredArtifacts": [
                            "Requirements",
                        ],
                    },
                },
            ],
            ("states\\[0\\]\\.gate\\.requiredCapabilities must be a non-empty list"),
        ),
        (
            [
                {
                    "name": "Requirements",
                    "gate": {
                        "name": "requirements-review",
                        "requiredCapabilities": [
                            None,
                        ],
                        "requiredArtifacts": [
                            "Requirements",
                        ],
                    },
                },
            ],
            (
                "states\\[0\\]\\.gate\\.requiredCapabilities"
                "\\[0\\] must be a non-empty string"
            ),
        ),
    ],
)
def test_workflow_projection_rejects_invalid_states(
    states: JsonValue,
    message: str,
) -> None:
    if states is None:
        source = registry_source(
            RegistryKind.WORKFLOW,
            ("registry/workflows/lean-delivery.workflow.json"),
            {
                "name": "lean-delivery",
                "states": None,
            },
        )
    else:
        source = workflow_source(
            states=states,
        )

    with pytest.raises(
        BundleDependencyProjectionError,
        match=message,
    ):
        project_workflows((source,))


def test_workflow_projection_rejects_duplicate_identity() -> None:
    with pytest.raises(
        BundleDependencyProjectionError,
        match="identity 'duplicate' is duplicated",
    ):
        project_workflows(
            (
                workflow_source(
                    name="duplicate",
                    filename="first.workflow.json",
                ),
                workflow_source(
                    name="duplicate",
                    filename="second.workflow.json",
                ),
            )
        )


def validation_error(
    schema: JsonObject,
    instance: JsonValue,
) -> ValidationError:
    return cast(
        ValidationError,
        next(Draft202012Validator(schema).iter_errors(instance)),
    )


@pytest.mark.parametrize(
    ("schema", "instance", "location", "message"),
    [
        (
            {
                "type": "object",
                "required": [
                    "name",
                ],
            },
            {},
            "name",
            "name is required",
        ),
        (
            {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "name",
                            ],
                        },
                    }
                },
            },
            {
                "items": [
                    {},
                ],
            },
            "items.0.name",
            "items.0.name is required",
        ),
        (
            {
                "type": "array",
                "minItems": 1,
            },
            [],
            "",
            " must be a non-empty list",
        ),
        (
            {
                "type": "array",
                "uniqueItems": True,
            },
            [
                "duplicate",
                "duplicate",
            ],
            "",
            " entries must be unique",
        ),
        (
            {
                "type": "string",
                "minLength": 1,
            },
            "",
            "",
            " must be a non-empty string",
        ),
        (
            {
                "type": "array",
            },
            "invalid",
            "",
            " must be a non-empty list",
        ),
        (
            {
                "type": "object",
            },
            [],
            "",
            " must be an object",
        ),
        (
            {
                "type": "boolean",
            },
            "invalid",
            "",
            " must be a boolean",
        ),
        (
            {
                "type": "string",
            },
            1,
            "",
            " must be a non-empty string",
        ),
        (
            {
                "type": "object",
                "properties": {
                    "version": {
                        "type": "string",
                        "pattern": "^x$",
                    }
                },
            },
            {
                "version": "invalid",
            },
            "version",
            "version must be a semantic version",
        ),
    ],
)
def test_schema_errors_have_stable_locations_and_messages(
    schema: JsonObject,
    instance: JsonValue,
    location: str,
    message: str,
) -> None:
    error = validation_error(
        schema,
        instance,
    )

    assert _schema_error_location(error) == location
    assert _schema_error_message(error) == message
    assert _schema_error_sort_key(error) == (
        location,
        error.message,
    )


def test_unmapped_schema_error_uses_jsonschema_message() -> None:
    error = validation_error(
        {
            "const": "expected",
        },
        "actual",
    )

    assert _schema_error_message(error) == ("schema violation: 'expected' was expected")
