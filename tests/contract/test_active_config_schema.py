from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from agentic_workflow_generator.application import (
    load_validated_registry_snapshot,
)
from agentic_workflow_generator.compiler import (
    ProjectMetadata,
    compile_bundle_composition,
    composition_to_json_object,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / ".agentic"
    / "schemas"
    / "agentic.schema.json"
)


def active_config_schema() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        read_json_object(SCHEMA_PATH),
    )


def test_active_config_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        active_config_schema()
    )


def test_all_real_bundles_serialize_against_schema() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    validator = Draft202012Validator(
        active_config_schema()
    )
    project = ProjectMetadata(
        name="consumer-project",
        project_type="agentic-project",
        description="Generated test configuration.",
        language_profiles=("python",),
        runtime_profiles=("python",),
        architecture_profile="typed-composition",
    )

    errors = [
        (
            bundle.name,
            error.json_path,
            error.message,
        )
        for bundle in snapshot.bundles
        for error in validator.iter_errors(
            composition_to_json_object(
                compile_bundle_composition(
                    snapshot,
                    project,
                    bundle.name,
                )
            )
        )
    ]

    assert errors == []


def test_compiled_role_bindings_serialize_canonical_input_artifacts() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    project = ProjectMetadata(
        name="consumer-project",
        project_type="agentic-project",
        description="Generated test configuration.",
        language_profiles=("python",),
        runtime_profiles=("python",),
        architecture_profile="typed-composition",
    )
    config = composition_to_json_object(
        compile_bundle_composition(
            snapshot,
            project,
            "orchestrated-delivery",
        )
    )

    assert config["schemaVersion"] == "0.10.0"

    role_bindings = cast(
        list[Any],
        config["roleBindings"],
    )
    by_name = {
        cast(dict[str, Any], binding)["roleName"]: cast(
            dict[str, Any],
            binding,
        )
        for binding in role_bindings
    }

    assert by_name["requirements"]["inputArtifacts"] == []
    assert by_name["workflow-controller"]["inputArtifacts"] == []
    assert by_name["implementation"]["inputArtifacts"] == [
        {
            "artifactType": "ArchitectureDecision",
            "roleBinding": "architecture",
            "agentInstance": "architecture-worker",
        },
        {
            "artifactType": "Requirements",
            "roleBinding": "requirements",
            "agentInstance": "requirements-worker",
        },
    ]


def test_active_schema_rejects_controller_input_artifacts() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    project = ProjectMetadata(
        name="consumer-project",
        project_type="agentic-project",
        description="Generated test configuration.",
        language_profiles=("python",),
        runtime_profiles=("python",),
        architecture_profile="typed-composition",
    )
    config = composition_to_json_object(
        compile_bundle_composition(
            snapshot,
            project,
            "lean-delivery",
        )
    )
    role_bindings = cast(
        list[Any],
        config["roleBindings"],
    )
    controller = next(
        cast(dict[str, Any], binding)
        for binding in role_bindings
        if cast(dict[str, Any], binding)["bindingType"]
        == "workflow-controller"
    )
    controller["inputArtifacts"] = [
        {
            "artifactType": "Requirements",
            "roleBinding": "requirements",
            "agentInstance": "requirements-worker",
        }
    ]

    errors = list(
        Draft202012Validator(
            active_config_schema()
        ).iter_errors(config)
    )

    assert any(
        error.validator == "maxItems"
        and error.json_path.endswith(".inputArtifacts")
        for error in errors
    )


def test_active_repository_config_matches_schema() -> None:
    validator = Draft202012Validator(
        active_config_schema()
    )
    config = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "agentic.json"
    )

    assert list(validator.iter_errors(config)) == []


def test_all_workflows_preserve_total_canonical_routing() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )

    assert {workflow.version for workflow in snapshot.workflows} == {
        "0.3.0"
    }

    for workflow in snapshot.workflows:
        non_terminal_states = {
            state.name for state in workflow.states if not state.terminal
        }
        routes = {
            (transition.source, transition.result.value): transition.target
            for transition in workflow.transitions
        }

        assert len(routes) == len(non_terminal_states) * 3

        for state in non_terminal_states:
            assert routes[(state, "blocked")] == workflow.default_failure_state
            assert (state, "fail") in routes
            assert routes[(state, "pass")] != workflow.default_failure_state


def test_workflow_pass_and_fail_targets_are_preserved() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    expected = {
        "lean-delivery": {
            ("Requirements", "pass"): "Implementer",
            ("Requirements", "fail"): "Blocked",
            ("Implementer", "pass"): "TestRunner",
            ("Implementer", "fail"): "Blocked",
            ("TestRunner", "pass"): "CodeReviewer",
            ("TestRunner", "fail"): "Implementer",
            ("CodeReviewer", "pass"): "Done",
            ("CodeReviewer", "fail"): "Implementer",
        },
        "orchestrated-delivery": {
            ("Requirements", "pass"): "Architect",
            ("Requirements", "fail"): "Blocked",
            ("Architect", "pass"): "Implementer",
            ("Architect", "fail"): "Blocked",
            ("Implementer", "pass"): "TestRunner",
            ("Implementer", "fail"): "Blocked",
            ("TestRunner", "pass"): "CodeReviewer",
            ("TestRunner", "fail"): "Implementer",
            ("CodeReviewer", "pass"): "QA",
            ("CodeReviewer", "fail"): "Implementer",
            ("QA", "pass"): "Done",
            ("QA", "fail"): "Blocked",
        },
        "review-heavy-delivery": {
            ("Requirements", "pass"): "Architect",
            ("Requirements", "fail"): "Blocked",
            ("Architect", "pass"): "Implementer",
            ("Architect", "fail"): "Blocked",
            ("Implementer", "pass"): "CodeReviewer",
            ("Implementer", "fail"): "Blocked",
            ("CodeReviewer", "pass"): "TestRunner",
            ("CodeReviewer", "fail"): "Implementer",
            ("TestRunner", "pass"): "QA",
            ("TestRunner", "fail"): "Implementer",
            ("QA", "pass"): "Done",
            ("QA", "fail"): "Implementer",
        },
        "ai-application-delivery": {
            ("Requirements", "pass"): "Architect",
            ("Requirements", "fail"): "Blocked",
            ("Architect", "pass"): "Implementer",
            ("Architect", "fail"): "Blocked",
            ("Implementer", "pass"): "AIEvaluator",
            ("Implementer", "fail"): "Blocked",
            ("AIEvaluator", "pass"): "TestRunner",
            ("AIEvaluator", "fail"): "Implementer",
            ("TestRunner", "pass"): "CodeReviewer",
            ("TestRunner", "fail"): "Implementer",
            ("CodeReviewer", "pass"): "QA",
            ("CodeReviewer", "fail"): "Implementer",
            ("QA", "pass"): "Done",
            ("QA", "fail"): "Blocked",
        },
    }

    for workflow in snapshot.workflows:
        actual = {
            (transition.source, transition.result.value): transition.target
            for transition in workflow.transitions
            if transition.result.value in {"pass", "fail"}
        }
        assert actual == expected[workflow.name]


def test_active_transition_serialization_is_canonical() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    project = ProjectMetadata(
        name="consumer-project",
        project_type="agentic-project",
        description="Generated test configuration.",
        language_profiles=("python",),
        runtime_profiles=("python",),
        architecture_profile="typed-composition",
    )
    config = composition_to_json_object(
        compile_bundle_composition(
            snapshot,
            project,
            "orchestrated-delivery",
        )
    )
    workflow = cast(dict[str, Any], config["workflow"])
    transitions = cast(list[dict[str, str]], workflow["transitions"])
    routing_keys = [
        (transition["from"], transition["on"], transition["to"])
        for transition in transitions
    ]

    assert routing_keys == sorted(routing_keys)
    assert {transition["on"] for transition in transitions} == {
        "pass",
        "fail",
        "blocked",
    }


def test_active_schema_rejects_unsupported_routing_result() -> None:
    config = read_json_object(
        REPOSITORY_ROOT / ".agentic" / "agentic.json"
    )
    workflow = cast(dict[str, Any], config["workflow"])
    transitions = cast(list[dict[str, str]], workflow["transitions"])
    transitions[0]["on"] = "approve"

    errors = list(
        Draft202012Validator(
            active_config_schema()
        ).iter_errors(config)
    )

    assert any(
        error.validator == "enum"
        and error.json_path == "$.workflow.transitions[0].on"
        for error in errors
    )


def test_schema_rejects_obsolete_runtime_authority() -> None:
    config = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "agentic.json"
    )
    config["agents"] = []
    config["gates"] = []

    errors = list(
        Draft202012Validator(
            active_config_schema()
        ).iter_errors(config)
    )

    assert len(errors) == 1
    assert errors[0].validator == (
        "additionalProperties"
    )
    assert "agents" in errors[0].message
    assert "gates" in errors[0].message


def test_schema_rejects_duplicate_target_entries() -> None:
    config = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "agentic.json"
    )
    targets = cast(list[Any], config["targets"])
    targets.append(dict(cast(dict[str, Any], targets[0])))

    errors = list(
        Draft202012Validator(
            active_config_schema()
        ).iter_errors(config)
    )

    assert any(
        error.validator == "uniqueItems"
        and error.json_path == "$.targets"
        for error in errors
    )


def test_schema_requires_target_enabled_to_be_true() -> None:
    config = read_json_object(
        REPOSITORY_ROOT
        / ".agentic"
        / "agentic.json"
    )
    targets = cast(list[Any], config["targets"])
    first_target = cast(dict[str, Any], targets[0])
    first_target["enabled"] = "true"

    errors = list(
        Draft202012Validator(
            active_config_schema()
        ).iter_errors(config)
    )

    assert any(
        error.validator == "const"
        and error.json_path == "$.targets[0].enabled"
        for error in errors
    )


def test_active_repository_artifacts_carry_canonical_provenance() -> None:
    config = read_json_object(
        REPOSITORY_ROOT / ".agentic" / "agentic.json"
    )
    assert config["schemaVersion"] == "0.10.0"

    artifacts = cast(list[Any], config["artifacts"])
    assert artifacts

    expected = {
        "heading": "## Provenance",
        "requiredIdentities": [
            "artifactType",
            "artifactVersion",
            "workflow",
            "workflowVersion",
            "roleBinding",
            "agentInstance",
        ],
    }

    assert all(
        cast(dict[str, Any], artifact)["provenance"] == expected
        for artifact in artifacts
    )


def test_active_repository_artifacts_carry_canonical_revision() -> None:
    config = read_json_object(
        REPOSITORY_ROOT / ".agentic" / "agentic.json"
    )
    assert config["schemaVersion"] == "0.10.0"

    artifacts = cast(list[Any], config["artifacts"])
    assert artifacts

    expected = {
        "heading": "## Revision",
        "pattern": "^[1-9][0-9]*$",
    }

    assert all(
        cast(dict[str, Any], artifact)["revision"] == expected
        for artifact in artifacts
    )



def test_active_repository_artifacts_carry_status_invariants() -> None:
    config = read_json_object(
        REPOSITORY_ROOT / ".agentic" / "agentic.json"
    )
    assert config["schemaVersion"] == "0.10.0"

    artifacts = cast(list[Any], config["artifacts"])
    assert artifacts

    expected = {
        "passRequiresCompleteEvidence": True,
        "passForbidsDemonstratedNonconformance": True,
        "failRequiresDemonstratedNonconformance": True,
        "blockedRequiresUnavailablePrerequisite": True,
    }

    assert all(
        cast(dict[str, Any], artifact)["statusInvariants"] == expected
        for artifact in artifacts
    )

def test_active_repository_artifacts_carry_status_semantics() -> None:
    config = read_json_object(
        REPOSITORY_ROOT / ".agentic" / "agentic.json"
    )
    assert config["schemaVersion"] == "0.10.0"

    artifacts = cast(list[Any], config["artifacts"])
    assert artifacts

    for artifact in artifacts:
        artifact_object = cast(dict[str, Any], artifact)
        semantics = cast(dict[str, Any], artifact_object["statusSemantics"])
        assert tuple(semantics) == (
            "passDefinition",
            "failDefinition",
            "blockedDefinition",
            "mixedConditionRule",
        )
        assert all(
            isinstance(semantics[field], str) and semantics[field]
            for field in (
                "passDefinition",
                "failDefinition",
                "blockedDefinition",
            )
        )
        assert semantics["mixedConditionRule"] == 'FAIL_ON_DEMONSTRATED_NONCONFORMANCE'

def test_active_repository_artifacts_carry_canonical_evidence() -> None:
    config = read_json_object(
        REPOSITORY_ROOT / ".agentic" / "agentic.json"
    )
    assert config["schemaVersion"] == "0.10.0"

    artifacts = cast(list[Any], config["artifacts"])
    assert artifacts

    expected = {
        "heading": "## Evidence",
        "requiredFields": [
            "claim",
            "source",
            "reproduction",
            "result",
        ],
    }

    assert all(
        cast(dict[str, Any], artifact)["evidence"] == expected
        for artifact in artifacts
    )
