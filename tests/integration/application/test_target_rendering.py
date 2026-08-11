from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agentic_workflow_generator.application.target_materialization import (
    load_active_composition,
)
from agentic_workflow_generator.application.target_rendering import (
    TargetRenderingError,
    render_enabled_targets,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def rendered_files(
    target_name: str,
) -> dict[Path, bytes]:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    targets = render_enabled_targets(
        paths,
        active.composition,
    )
    target = next(
        item
        for item in targets
        if item.name == target_name
    )
    return {
        file.path: file.content
        for file in target.files
    }


def test_opencode_uses_agent_instance_identity() -> None:
    files = rendered_files("opencode")

    assert (
        Path(".opencode/agents/workflow-controller.md")
        in files
    )
    assert (
        Path(".opencode/agents/requirements-worker.md")
        in files
    )
    assert Path(".opencode/agents/orchestrator.md") not in files

    config = json.loads(
        files[Path("opencode.json")].decode("utf-8")
    )
    assert config["default_agent"] == "workflow-controller"

    controller = files[
        Path(".opencode/agents/workflow-controller.md")
    ].decode("utf-8")
    assert "# Orchestrator" in controller
    assert "agent instance: `workflow-controller`" in controller
    assert ".agentic/agentic.json" in controller
    assert "resolution.json" not in controller


def test_vscode_handoffs_use_agent_instance_identity() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    files = rendered_files("vscode-copilot")
    controller_path = Path(
        ".github/agents/workflow-controller.agent.md"
    )

    assert controller_path in files
    assert (
        Path(".github/agents/orchestrator.agent.md")
        not in files
    )

    controller = files[controller_path].decode("utf-8")
    assert 'name: "workflow-controller"' in controller
    assert 'agent: "requirements-worker"' in controller
    assert "resolution.json" not in controller

    state_owner_instances = {
        ownership.agent_instance
        for ownership in active.composition.state_ownership
    }

    for instance in state_owner_instances:
        state_owner = files[
            Path(f".github/agents/{instance}.agent.md")
        ].decode("utf-8")
        assert "handoffs:" not in state_owner


def test_vscode_controller_owns_every_non_terminal_route_handoff() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    files = rendered_files("vscode-copilot")
    controller = files[
        Path(".github/agents/workflow-controller.agent.md")
    ].decode("utf-8")
    owners = {
        ownership.workflow_state: ownership.agent_instance
        for ownership in active.composition.state_ownership
    }
    non_terminal_routes = tuple(
        sorted(
            (
                transition.source,
                transition.result.name,
                transition.result.value,
                transition.target,
                owners[transition.target],
            )
            for transition in active.composition.workflow.transitions
            if transition.target in owners
        )
    )

    labels: list[str] = []

    for source, result_name, result_value, target, owner in non_terminal_routes:
        label = (
            f"Route {source} + {result_name} ({result_value}) -> {target}"
        )
        prompt = (
            f"Current state: {source}. Canonical result: {result_name} "
            f"({result_value}). Dispatch the owner of selected target state "
            f"{target}; do not infer, prioritize, or reclassify the route."
        )
        handoff = (
            f'  - label: "{label}"\n'
            f'    agent: "{owner}"\n'
            f'    prompt: "{prompt}"\n'
            "    send: false"
        )

        assert handoff in controller
        labels.append(label)

    assert controller.count("  - label:") == len(non_terminal_routes) + 1
    assert [controller.index(f'label: "{label}"') for label in labels] == sorted(
        controller.index(f'label: "{label}"') for label in labels
    )

    for transition in active.composition.workflow.transitions:
        if transition.target not in active.composition.workflow.terminal_states:
            continue

        terminal_label = (
            f"Route {transition.source} + {transition.result.name} "
            f"({transition.result.value}) -> {transition.target}"
        )
        assert terminal_label not in controller


def test_both_targets_preserve_controller_owned_routing() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    expected_routes = tuple(
        sorted(
            (
                transition.source,
                transition.result.name,
                transition.result.value,
                transition.target,
            )
            for transition in active.composition.workflow.transitions
        )
    )

    for target_name, controller_path, owner_path in (
        (
            "opencode",
            Path(".opencode/agents/workflow-controller.md"),
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/workflow-controller.agent.md"),
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        files = rendered_files(target_name)
        controller = files[controller_path].decode("utf-8")
        owner = files[owner_path].decode("utf-8")

        assert "This controller is the sole routing authority." in controller
        assert "- start state: `Requirements`" in controller
        assert "- terminal states: `Done`, `Blocked`" in controller
        assert "- default failure state: `Blocked`" in controller
        assert "`PASS` (`pass`), `FAIL` (`fail`), `BLOCKED` (`blocked`)" in controller

        for source, result_name, result_value, target in expected_routes:
            assert (
                f"- `{source}` + `{result_name}` (`{result_value}`) -> `{target}`"
                in controller
            )

        assert "Return that result and control to the workflow controller." in owner
        assert "Do not select or execute a workflow route." in owner
        assert "Canonical routing table:" not in owner


def test_rendering_rejects_incomplete_canonical_routing() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    workflow = active.composition.workflow
    incomplete = replace(
        active.composition,
        workflow=replace(
            workflow,
            transitions=tuple(
                transition
                for transition in workflow.transitions
                if not (
                    transition.source == "Requirements"
                    and transition.result.value == "pass"
                )
            ),
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="must have exactly one 'pass' route",
    ):
        render_enabled_targets(paths, incomplete)


def test_rendering_rejects_missing_state_ownership() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    missing_owner = replace(
        active.composition,
        state_ownership=tuple(
            ownership
            for ownership in active.composition.state_ownership
            if ownership.workflow_state != "Requirements"
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="must have exactly one compiled owner",
    ):
        render_enabled_targets(paths, missing_owner)


def test_rendering_rejects_missing_controller_instance() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    missing_controller = replace(
        active.composition,
        role_bindings=tuple(
            replace(binding, agent_instance="missing-controller")
            if binding.role_name == active.composition.controller_binding
            else binding
            for binding in active.composition.role_bindings
        ),
    )

    with pytest.raises(
        TargetRenderingError,
        match="is not a rendered agent instance",
    ):
        render_enabled_targets(paths, missing_controller)




def test_rendered_required_inputs_use_compiled_production_identity() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    implementation = next(
        binding
        for binding in active.composition.role_bindings
        if binding.role_name == "implementation"
    )

    assert tuple(
        (
            production.artifact.type,
            production.role_binding,
            production.agent_instance,
        )
        for production in implementation.input_artifacts
    ) == (
        (
            "ArchitectureDecision",
            "architecture",
            "architecture-worker",
        ),
        (
            "Requirements",
            "requirements",
            "requirements-worker",
        ),
    )

    expected_lines = tuple(
        (
            f"`artifactType`: `{production.artifact.type}`; "
            f"producer `roleBinding`: `{production.role_binding}`; "
            f"resolved `agentInstance`: `{production.agent_instance}`"
        )
        for production in implementation.input_artifacts
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/implementation-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(
                ".github/agents/"
                "implementation-worker.agent.md"
            ),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        assert "## Required Input Artifacts" in content
        assert "### implementation" in content
        for expected in expected_lines:
            assert expected in content


def test_rendered_controller_has_no_governed_inputs() -> None:
    expected = (
        "### workflow-controller\n\n"
        "This role binding has no required static input artifacts."
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/workflow-controller.md"),
        ),
        (
            "vscode-copilot",
            Path(
                ".github/agents/"
                "workflow-controller.agent.md"
            ),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        assert "## Required Input Artifacts" in content
        assert expected in content


def test_rendered_artifact_headings_are_nested() -> None:
    files = rendered_files("opencode")
    requirements = files[
        Path(".opencode/agents/requirements-worker.md")
    ].decode("utf-8")

    assert (
        "- required headings:\n"
        "  - # Requirements\n"
        "  - ## Status\n"
        "  - ## Provenance\n"
        "  - ## Revision\n"
        "  - ## Evidence\n"
        "  - ## Summary\n"
    ) in requirements
    assert (
        "- required headings:\n\n- # Requirements"
        not in requirements
    )


def test_rendered_targets_copy_compiled_skills() -> None:
    for target_name, skill_root in (
        ("opencode", Path(".opencode/skills")),
        (
            "vscode-copilot",
            Path(".github/skills"),
        ),
    ):
        files = rendered_files(target_name)

        assert (
            skill_root
            / "workflow-routing"
            / "SKILL.md"
        ) in files
        assert (
            skill_root
            / "workflow-routing"
            / "skill.json"
        ) in files


def test_every_rendered_file_is_target_owned() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)

    for target in render_enabled_targets(
        paths,
        active.composition,
    ):
        owned = tuple(
            Path(path)
            for path in target.owned_paths
        )

        assert target.files

        for file in target.files:
            assert any(
                file.path == root
                or file.path.is_relative_to(root)
                for root in owned
            )


def test_rendered_provenance_uses_compiled_production_identity() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    production = next(
        item
        for item in active.composition.artifact_production
        if item.artifact.type == "Requirements"
    )

    expected_lines = (
        "- provenance heading: `## Provenance`",
        "  - `artifactType`: `Requirements`",
        f"  - `artifactVersion`: `{production.artifact.version}`",
        f"  - `workflow`: `{active.composition.workflow.name}`",
        (
            "  - `workflowVersion`: "
            f"`{active.composition.workflow.version}`"
        ),
        f"  - `roleBinding`: `{production.role_binding}`",
        f"  - `agentInstance`: `{production.agent_instance}`",
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        for expected in expected_lines:
            assert expected in content


def test_rendered_revision_uses_compiled_artifact_contract() -> None:
    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        assert "- revision heading: `## Revision`" in content
        assert (
            "- revision entry: `revision: <N>` where `<N>` matches "
            "`^[1-9][0-9]*$`"
        ) in content



def test_rendered_evidence_uses_compiled_artifact_contract() -> None:
    expected_lines = (
        "- evidence heading: `## Evidence`",
        "- evidence required fields:",
        "  - claim",
        "  - source",
        "  - reproduction",
        "  - result",
        "- evidence semantics:",
        (
            "  - record one or more reproducible evidence records "
            "for status-determining conditions"
        ),
        (
            "  - cover every status-determining condition used to "
            "classify the artifact"
        ),
        (
            "  - keep materially independent conditions "
            "independently reproducible"
        ),
        (
            "  - evidence records supply observations; they do not "
            "define artifact status policy"
        ),
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        for expected in expected_lines:
            assert expected in content


def test_rendered_status_invariants_use_compiled_artifact_contract() -> None:
    expected_lines = (
        "- status invariants:",
        "  - `passRequiresCompleteEvidence`: `true`",
        "  - `passForbidsDemonstratedNonconformance`: `true`",
        "  - `failRequiresDemonstratedNonconformance`: `true`",
        "  - `blockedRequiresUnavailablePrerequisite`: `true`",
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        for expected in expected_lines:
            assert expected in content

def test_rendered_status_semantics_use_compiled_artifact_contract() -> None:
    paths = ProjectPaths(REPOSITORY_ROOT)
    active = load_active_composition(paths)
    production = next(
        item
        for item in active.composition.artifact_production
        if item.artifact.type == "Requirements"
    )
    semantics = production.artifact.status_semantics
    expected_lines = (
        "- status semantics:",
        f"  - `PASS`: {semantics.pass_definition}",
        f"  - `FAIL`: {semantics.fail_definition}",
        f"  - `BLOCKED`: {semantics.blocked_definition}",
        (
            "  - `mixedConditionRule`: "
            f"`{semantics.mixed_condition_rule}`"
        ),
    )

    for target_name, path in (
        (
            "opencode",
            Path(".opencode/agents/requirements-worker.md"),
        ),
        (
            "vscode-copilot",
            Path(".github/agents/requirements-worker.agent.md"),
        ),
    ):
        content = rendered_files(target_name)[path].decode("utf-8")

        for expected in expected_lines:
            assert expected in content

        assert (
            "Missing required evidence alone must result in `BLOCKED`; "
            "demonstrated nonconformance remains governed by the artifact contract."
        ) in content
