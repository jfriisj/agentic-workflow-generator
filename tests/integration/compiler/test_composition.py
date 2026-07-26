from dataclasses import replace
from pathlib import Path

import pytest

from agentic_workflow_generator.application import (
    ValidatedRegistrySnapshot,
    load_validated_registry_snapshot,
)
from agentic_workflow_generator.compiler import (
    CompositionError,
    ProjectMetadata,
    compile_bundle_composition,
)
from agentic_workflow_generator.domain import (
    Bundle,
    RoleBindingType,
    Workflow,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def project_metadata() -> ProjectMetadata:
    return ProjectMetadata(
        name="consumer-project",
        project_type="agentic-project",
        description="Generated test configuration.",
        language_profiles=("python",),
        runtime_profiles=("python",),
        architecture_profile="typed-composition",
    )


def test_all_real_bundles_compile_to_complete_runtime_authority() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    expected_counts = {
        "ai-application": (8, 8, 7, 7),
        "lean-delivery": (5, 5, 4, 4),
        "orchestrated-delivery": (7, 7, 6, 6),
        "review-heavy-delivery": (7, 7, 6, 6),
    }

    for bundle_name, counts in expected_counts.items():
        composition = compile_bundle_composition(
            snapshot,
            project_metadata(),
            bundle_name,
        )
        (
            instance_count,
            binding_count,
            state_owner_count,
            gate_count,
        ) = counts

        assert composition.bundle == bundle_name
        assert len(composition.agent_instances) == instance_count
        assert len(composition.role_bindings) == binding_count
        assert len(composition.state_ownership) == state_owner_count
        assert len(composition.workflow_gates) == gate_count
        assert composition.controller_binding == "workflow-controller"
        assert tuple(
            target.name
            for target in composition.targets
        ) == (
            "opencode",
            "vscode-copilot",
        )
        assert tuple(
            target.priority
            for target in composition.targets
        ) == (
            1,
            2,
        )
        assert all(
            binding.binding_type
            in {
                RoleBindingType.STATE_OWNER,
                RoleBindingType.WORKFLOW_CONTROLLER,
            }
            for binding in composition.role_bindings
        )
        assert len(composition.artifact_production) == gate_count
        assert composition.runtime_context.enabled is False
        assert composition.runtime_context.fail_if_missing is False
        assert composition.validation.fail_closed is True


def test_orchestrated_bundle_preserves_authoritative_binding_semantics() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    composition = compile_bundle_composition(
        snapshot,
        project_metadata(),
        "orchestrated-delivery",
    )

    requirements_binding = next(
        binding
        for binding in composition.role_bindings
        if binding.role_name == "requirements"
    )
    requirements_instance = next(
        instance
        for instance in composition.agent_instances
        if instance.id == "requirements-worker"
    )
    requirements_gate = next(
        gate
        for gate in composition.workflow_gates
        if gate.workflow_state == "Requirements"
    )

    assert requirements_binding.agent_instance == (
        "requirements-worker"
    )
    assert requirements_binding.required_capabilities == (
        "requirements.elicit",
        "requirements.define-acceptance-criteria",
    )
    assert tuple(
        skill.name
        for skill in requirements_binding.selected_skills
    ) == ("requirements-analysis",)
    assert tuple(
        artifact.type
        for artifact in requirements_binding.produces
    ) == ("Requirements",)
    assert requirements_instance.profile.name == "Requirements"
    assert requirements_instance.role_bindings == ("requirements",)
    assert requirements_instance.required_capabilities == (
        "requirements.elicit",
        "requirements.define-acceptance-criteria",
    )
    assert requirements_instance.permission_profile.name == "read-only"
    assert requirements_gate.owner_role_binding == "requirements"
    assert requirements_gate.owner_agent_instance == (
        "requirements-worker"
    )
    assert tuple(
        artifact.type
        for artifact in requirements_gate.required_artifacts
    ) == ("Requirements",)


def test_selected_targets_can_narrow_bundle_targets() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    composition = compile_bundle_composition(
        snapshot,
        project_metadata(),
        "orchestrated-delivery",
        selected_targets=("opencode",),
    )

    assert tuple(
        target.name
        for target in composition.targets
    ) == ("opencode",)
    assert composition.targets[0].priority == 1


@pytest.mark.parametrize(
    "selected_targets",
    [
        ("codex",),
        ("opencode", "opencode"),
        (),
    ],
)
def test_invalid_target_selection_fails_closed(
    selected_targets: tuple[str, ...],
) -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )

    with pytest.raises(CompositionError):
        compile_bundle_composition(
            snapshot,
            project_metadata(),
            "orchestrated-delivery",
            selected_targets=selected_targets,
        )


def replace_bundle(
    snapshot: ValidatedRegistrySnapshot,
    bundle_name: str,
    replacement: Bundle,
) -> ValidatedRegistrySnapshot:
    return replace(
        snapshot,
        bundles=tuple(
            replacement
            if bundle.name == bundle_name
            else bundle
            for bundle in snapshot.bundles
        ),
    )


def replace_workflow(
    snapshot: ValidatedRegistrySnapshot,
    workflow_name: str,
    replacement: Workflow,
) -> ValidatedRegistrySnapshot:
    return replace(
        snapshot,
        workflows=tuple(
            replacement
            if workflow.name == workflow_name
            else workflow
            for workflow in snapshot.workflows
        ),
    )


def test_composition_requires_exactly_one_controller() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    bundle = snapshot.bundle_by_name(
        "orchestrated-delivery"
    )
    controller = next(
        binding
        for binding in bundle.role_bindings
        if binding.binding_type
        is RoleBindingType.WORKFLOW_CONTROLLER
    )
    invalid_bundle = replace(
        bundle,
        role_bindings=(
            *bundle.role_bindings,
            replace(
                controller,
                role_name="workflow-controller-copy",
            ),
        ),
    )
    invalid_snapshot = replace_bundle(
        snapshot,
        bundle.name,
        invalid_bundle,
    )

    with pytest.raises(
        CompositionError,
        match="exactly one workflow controller",
    ):
        compile_bundle_composition(
            invalid_snapshot,
            project_metadata(),
            bundle.name,
        )


def test_composition_rejects_unassigned_agent_instance() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    bundle = snapshot.bundle_by_name(
        "lean-delivery"
    )
    orphan = replace(
        bundle.agent_instances[0],
        id="orphan-worker",
        display_name="Orphan worker",
    )
    invalid_bundle = replace(
        bundle,
        agent_instances=(
            *bundle.agent_instances,
            orphan,
        ),
    )

    with pytest.raises(
        CompositionError,
        match="has no role bindings",
    ):
        compile_bundle_composition(
            replace_bundle(
                snapshot,
                bundle.name,
                invalid_bundle,
            ),
            project_metadata(),
            bundle.name,
        )


def test_composition_rejects_unregistered_bundle_target() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    bundle = snapshot.bundle_by_name(
        "lean-delivery"
    )
    invalid_bundle = replace(
        bundle,
        targets=(
            *bundle.targets,
            "codex",
        ),
    )

    with pytest.raises(
        CompositionError,
        match="not registered",
    ):
        compile_bundle_composition(
            replace_bundle(
                snapshot,
                bundle.name,
                invalid_bundle,
            ),
            project_metadata(),
            bundle.name,
            selected_targets=("codex",),
        )


def test_composition_requires_state_owner_workflow_state() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    bundle = snapshot.bundle_by_name(
        "lean-delivery"
    )
    owner = next(
        binding
        for binding in bundle.role_bindings
        if binding.binding_type
        is RoleBindingType.STATE_OWNER
    )
    invalid_bundle = replace(
        bundle,
        role_bindings=tuple(
            replace(
                binding,
                workflow_state=None,
            )
            if binding.role_name == owner.role_name
            else binding
            for binding in bundle.role_bindings
        ),
    )

    with pytest.raises(
        CompositionError,
        match="workflow state must not be missing",
    ):
        compile_bundle_composition(
            replace_bundle(
                snapshot,
                bundle.name,
                invalid_bundle,
            ),
            project_metadata(),
            bundle.name,
        )


def test_composition_rejects_non_terminal_state_without_gate() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    bundle = snapshot.bundle_by_name(
        "lean-delivery"
    )
    workflow = snapshot.workflow_by_name(
        bundle.workflow
    )
    state = next(
        item
        for item in workflow.states
        if not item.terminal
    )
    invalid_workflow = replace(
        workflow,
        states=tuple(
            replace(item, gate=None)
            if item.name == state.name
            else item
            for item in workflow.states
        ),
    )

    with pytest.raises(
        CompositionError,
        match="has no gate",
    ):
        compile_bundle_composition(
            replace_workflow(
                snapshot,
                workflow.name,
                invalid_workflow,
            ),
            project_metadata(),
            bundle.name,
        )


def test_composition_rejects_workflow_state_without_owner() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    bundle = snapshot.bundle_by_name(
        "lean-delivery"
    )
    owner = next(
        binding
        for binding in bundle.role_bindings
        if binding.binding_type
        is RoleBindingType.STATE_OWNER
    )
    invalid_bundle = replace(
        bundle,
        role_bindings=tuple(
            replace(
                binding,
                workflow_state="Unowned",
            )
            if binding.role_name == owner.role_name
            else binding
            for binding in bundle.role_bindings
        ),
    )

    with pytest.raises(
        CompositionError,
        match="has no compiled owner",
    ):
        compile_bundle_composition(
            replace_bundle(
                snapshot,
                bundle.name,
                invalid_bundle,
            ),
            project_metadata(),
            bundle.name,
        )


def test_composition_rejects_unknown_separation_binding() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    bundle = snapshot.bundle_by_name(
        "orchestrated-delivery"
    )
    policy = bundle.separation_policies[0]
    invalid_bundle = replace(
        bundle,
        separation_policies=(
            replace(
                policy,
                role_bindings=(
                    *policy.role_bindings,
                    "missing-binding",
                ),
            ),
            *bundle.separation_policies[1:],
        ),
    )

    with pytest.raises(
        CompositionError,
        match="references unknown role binding",
    ):
        compile_bundle_composition(
            replace_bundle(
                snapshot,
                bundle.name,
                invalid_bundle,
            ),
            project_metadata(),
            bundle.name,
        )


def test_composition_enforces_distinct_separation_instances() -> None:
    snapshot = load_validated_registry_snapshot(
        ProjectPaths(REPOSITORY_ROOT)
    )
    bundle = snapshot.bundle_by_name(
        "orchestrated-delivery"
    )
    policy = bundle.separation_policies[0]
    role_name = policy.role_bindings[0]
    invalid_bundle = replace(
        bundle,
        separation_policies=(
            replace(
                policy,
                role_bindings=(
                    role_name,
                    role_name,
                ),
            ),
            *bundle.separation_policies[1:],
        ),
    )

    with pytest.raises(
        CompositionError,
        match="requires distinct instances",
    ):
        compile_bundle_composition(
            replace_bundle(
                snapshot,
                bundle.name,
                invalid_bundle,
            ),
            project_metadata(),
            bundle.name,
        )
