"""Explicit target rendering from canonical compiled composition."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from agentic_workflow_generator.compiler import (
    CompiledAgentInstance,
    CompiledComposition,
)
from agentic_workflow_generator.domain import (
    RoleBindingType,
    TargetAdapter,
    WorkflowRoutingResult,
    WorkflowTestEvidenceRequirement,
    WorkflowTransition,
)
from agentic_workflow_generator.domain.targets import (
    TargetPermissionValue,
)
from agentic_workflow_generator.registry import ProjectPaths


class TargetRenderingError(ValueError):
    """Raised when typed target output cannot be rendered."""


@dataclass(frozen=True, slots=True)
class RenderedFile:
    """One deterministic repository-relative generated file."""

    path: Path
    content: bytes


@dataclass(frozen=True, slots=True)
class RenderedTarget:
    """All rendered files owned by one enabled target."""

    name: str
    owned_paths: tuple[str, ...]
    files: tuple[RenderedFile, ...]


@dataclass(frozen=True, slots=True)
class _Handoff:
    label: str
    agent_instance: str
    prompt: str


_TEST_EVIDENCE_MEANINGS = {
    WorkflowTestEvidenceRequirement.CHANGED_BEHAVIOR_TESTS: (
        "repository-authoritative validation directly exercises the approved "
        "changed behavior"
    ),
    WorkflowTestEvidenceRequirement.PROJECT_VALIDATION_SUITE: (
        "repository-authoritative broader regression/validation suite "
        "applicable to the project"
    ),
}
_TEST_REPORT_EVIDENCE_FIELDS = (
    "claim",
    "source",
    "reproduction",
    "result",
)
_TEST_REPORT_STATUSES = ("PASS", "FAIL", "BLOCKED")


def render_enabled_targets(
    paths: ProjectPaths,
    composition: CompiledComposition,
) -> tuple[RenderedTarget, ...]:
    """Render every enabled target in compiler priority order."""

    _validate_routing_representation(composition)
    _validate_test_evidence_representation(composition)
    rendered: list[RenderedTarget] = []

    for target in composition.targets:
        name = target.adapter.name

        if name == "opencode":
            rendered.append(
                _render_opencode(
                    paths,
                    composition,
                    target.adapter,
                )
            )
        elif name == "vscode-copilot":
            rendered.append(
                _render_vscode_copilot(
                    paths,
                    composition,
                    target.adapter,
                )
            )
        else:
            raise TargetRenderingError(
                f"Unsupported compiled target: {name!r}"
            )

    return tuple(rendered)


def _render_opencode(
    paths: ProjectPaths,
    composition: CompiledComposition,
    adapter: TargetAdapter,
) -> RenderedTarget:
    output_paths = _required_output_paths(
        adapter,
        {
            "agents",
            "skills",
            "instructions",
            "config",
        },
    )
    files: dict[Path, bytes] = {}

    for instance in composition.agent_instances:
        relative_path = (
            Path(output_paths["agents"])
            / f"{_slugify(instance.id)}.md"
        )
        files[relative_path] = _render_opencode_agent(
            composition,
            instance,
            adapter,
        ).encode("utf-8")

    files.update(
        _render_skill_files(
            paths,
            composition,
            output_paths["skills"],
        )
    )
    files[Path(output_paths["instructions"])] = (
        _render_project_instructions(
            composition,
            heading="AGENTS.md",
        ).encode("utf-8")
    )
    files[Path(output_paths["config"])] = (
        _serialize_json(
            {
                "$schema": "https://opencode.ai/config.json",
                "default_agent": _slugify(
                    _controller_instance(composition)
                ),
            }
        ).encode("utf-8")
    )

    return _rendered_target(adapter, files)


def _render_vscode_copilot(
    paths: ProjectPaths,
    composition: CompiledComposition,
    adapter: TargetAdapter,
) -> RenderedTarget:
    output_paths = _required_output_paths(
        adapter,
        {
            "agents",
            "skills",
            "instructions",
        },
    )
    files: dict[Path, bytes] = {}

    for instance in composition.agent_instances:
        relative_path = (
            Path(output_paths["agents"])
            / f"{_slugify(instance.id)}.agent.md"
        )
        files[relative_path] = _render_vscode_agent(
            composition,
            instance,
            adapter,
        ).encode("utf-8")

    files.update(
        _render_skill_files(
            paths,
            composition,
            output_paths["skills"],
        )
    )
    files[Path(output_paths["instructions"])] = (
        _render_project_instructions(
            composition,
            heading="Copilot Instructions",
        ).encode("utf-8")
    )

    return _rendered_target(adapter, files)


def _rendered_target(
    adapter: TargetAdapter,
    files: dict[Path, bytes],
) -> RenderedTarget:
    if not files:
        raise TargetRenderingError(
            f"Target {adapter.name!r} produced no files"
        )

    for path in files:
        _require_owned_file(adapter, path)

    return RenderedTarget(
        name=adapter.name,
        owned_paths=adapter.owned_paths,
        files=tuple(
            RenderedFile(path=path, content=content)
            for path, content in sorted(
                files.items(),
                key=lambda item: item[0].as_posix(),
            )
        ),
    )


def _render_opencode_agent(
    composition: CompiledComposition,
    instance: CompiledAgentInstance,
    adapter: TargetAdapter,
) -> str:
    settings = _permission_settings(
        adapter,
        instance.permission_profile.name,
    )
    edit = _required_permission_string(
        settings,
        "edit",
        adapter.name,
        instance.permission_profile.name,
    )
    bash = _required_permission_string(
        settings,
        "bash",
        adapter.name,
        instance.permission_profile.name,
    )

    allowed = {"allow", "ask", "deny"}

    if edit not in allowed:
        raise TargetRenderingError(
            f"Target {adapter.name!r} permission profile "
            f"{instance.permission_profile.name!r} has invalid "
            f"edit value {edit!r}"
        )

    if bash not in allowed:
        raise TargetRenderingError(
            f"Target {adapter.name!r} permission profile "
            f"{instance.permission_profile.name!r} has invalid "
            f"bash value {bash!r}"
        )

    mode = (
        "primary"
        if instance.id == _controller_instance(composition)
        else "subagent"
    )

    return (
        "---\n"
        f"description: {_yaml_string(instance.profile.description)}\n"
        f"mode: {mode}\n"
        "permission:\n"
        f"  edit: {edit}\n"
        f"  bash: {bash}\n"
        "---\n\n"
        + _render_agent_body(
            composition,
            instance,
        )
    )


def _render_vscode_agent(
    composition: CompiledComposition,
    instance: CompiledAgentInstance,
    adapter: TargetAdapter,
) -> str:
    settings = _permission_settings(
        adapter,
        instance.permission_profile.name,
    )
    tools = settings.get("tools")

    if (
        not isinstance(tools, tuple)
        or not tools
        or any(not item for item in tools)
    ):
        raise TargetRenderingError(
            f"Target {adapter.name!r} permission profile "
            f"{instance.permission_profile.name!r} must provide "
            "a non-empty tools list"
        )

    handoffs = _render_vscode_handoffs(
        _handoffs_for_instance(
            composition,
            instance.id,
        )
    )

    return (
        "---\n"
        f"name: {_yaml_string(instance.id)}\n"
        f"description: {_yaml_string(instance.profile.description)}\n"
        f"tools: {json.dumps(list(tools), ensure_ascii=False)}\n"
        f"{handoffs}"
        "---\n\n"
        + _render_agent_body(
            composition,
            instance,
        )
    )


def _render_agent_body(
    composition: CompiledComposition,
    instance: CompiledAgentInstance,
) -> str:
    return f"""# {instance.display_name}

## Runtime Identity

- agent instance: `{instance.id}`
- profile: `{instance.profile.name}`
- role bindings: {", ".join(instance.role_bindings)}

## Role

{instance.profile.role}

## Description

{instance.profile.description}

## Operating Rules

1. Stay inside the assigned role bindings.
2. Do not invent missing workflow state or evidence.
3. Missing required evidence alone must result in `BLOCKED`; demonstrated nonconformance remains governed by the artifact contract.
4. Do not override fail-closed workflow gates.
5. Respect all separation-of-duties constraints.

## Permission Profile

`{instance.permission_profile.name}`

## Required Capabilities

{_markdown_list(instance.required_capabilities)}

## Selected Skills

{_markdown_list(skill.name for skill in instance.selected_skills)}

## Responsibilities

{_markdown_list(instance.responsibilities)}

## Guardrails

{_markdown_list(instance.guardrails)}

{_render_required_input_artifacts(composition, instance)}
{_render_produced_artifacts(composition, instance)}
{_render_workflow_gate_requirements(composition, instance)}
## Workflow Authority

The canonical active composition is:

~~~text
.agentic/agentic.json
~~~

Workflow: `{composition.workflow.name}`

{_render_workflow_authority(composition, instance)}
"""


def _render_workflow_gate_requirements(
    composition: CompiledComposition,
    instance: CompiledAgentInstance,
) -> str:
    gates = tuple(
        sorted(
            (
                gate
                for gate in composition.workflow_gates
                if gate.owner_agent_instance == instance.id
            ),
            key=lambda gate: (
                gate.workflow_state,
                gate.name,
            ),
        )
    )
    lines = [
        "## Workflow Gate Requirements",
        "",
        (
            "Gate requirements are rendered directly from the canonical "
            "compiled workflow gate."
        ),
    ]

    if not gates:
        lines.extend(
            [
                "",
                "This agent instance owns no workflow gate.",
            ]
        )
        return "\n".join(lines) + "\n\n"

    for gate in gates:
        artifact_types = tuple(
            artifact.type
            for artifact in gate.required_artifacts
        )
        lines.extend(
            [
                "",
                f"### {gate.name}",
                "",
                f"- workflow state: `{gate.workflow_state}`",
                (
                    "- gate owner: role binding "
                    f"`{gate.owner_role_binding}`; agent instance "
                    f"`{gate.owner_agent_instance}`"
                ),
                f"- blocking: `{str(gate.blocking).lower()}`",
                (
                    "- required artifacts: "
                    + ", ".join(
                        f"`{artifact_type}`"
                        for artifact_type in artifact_types
                    )
                ),
            ]
        )

        if not gate.required_test_evidence:
            lines.append("- required test evidence: none")
            continue

        lines.append(
            "- required test evidence: every category below is "
            "independently required"
        )

        for requirement in gate.required_test_evidence:
            lines.append(
                "  - "
                f"`{requirement.value}`: "
                f"{_test_evidence_meaning(requirement)}; provide "
                "independently reproducible `TestReport` evidence using "
                "the existing `claim`, `source`, `reproduction`, and "
                "`result` fields"
            )

        lines.extend(
            [
                (
                    "- static/runtime boundary: required categories come "
                    "only from this compiled gate; resolve "
                    "repository-authoritative validation commands or "
                    "procedures at runtime"
                ),
                (
                    "- do not infer required categories from skill or "
                    "project prose; the compiler and target adapter do not "
                    "discover or execute tests"
                ),
                (
                    "- do not invent required observations; classify "
                    "`TestReport` only under its compiled `PASS`, `FAIL`, "
                    "and `BLOCKED` evidence/status contract"
                ),
                (
                    "- routing boundary: the state owner returns the "
                    "already-classified canonical result to the workflow "
                    "controller; only the controller selects the route"
                ),
            ]
        )

    return "\n".join(lines) + "\n\n"


def _test_evidence_meaning(
    requirement: WorkflowTestEvidenceRequirement,
) -> str:
    try:
        return _TEST_EVIDENCE_MEANINGS[requirement]
    except KeyError as exc:
        identity = getattr(requirement, "value", repr(requirement))
        raise TargetRenderingError(
            "Target rendering does not support canonical test-evidence "
            f"requirement {identity!r}"
        ) from exc


def _render_workflow_authority(
    composition: CompiledComposition,
    instance: CompiledAgentInstance,
) -> str:
    controller = _controller_instance(composition)

    if instance.id == controller:
        routes = tuple(
            (
                f"- `{transition.source}` + "
                f"`{transition.result.name}` (`{transition.result.value}`) "
                f"-> `{transition.target}`"
            )
            for transition in _canonical_transitions(composition)
        )
        return "\n".join(
            (
                "### Controller-Owned Routing",
                "",
                "This controller is the sole routing authority.",
                "",
                f"- start state: `{composition.workflow.start_state}`",
                "- terminal states: "
                + ", ".join(
                    f"`{state}`"
                    for state in composition.workflow.terminal_states
                ),
                "- default failure state: "
                f"`{composition.workflow.default_failure_state}`",
                "- canonical gate results: `PASS` (`pass`), "
                "`FAIL` (`fail`), `BLOCKED` (`blocked`)",
                "",
                "Canonical routing table:",
                "",
                *routes,
                "",
                "Receive the state owner's already-classified canonical result, "
                "select only the unique matching route, and stop without "
                "transition if routing is unavailable or inconsistent. Do not "
                "reinterpret results or use declaration order as priority.",
            )
        )

    owned_states = tuple(
        ownership.workflow_state
        for ownership in composition.state_ownership
        if ownership.agent_instance == instance.id
    )

    if not owned_states:
        return ""

    return "\n".join(
        (
            "### State-Owner Routing Boundary",
            "",
            "Classify the governed gate outcome as exactly one canonical result: "
            "`PASS`, `FAIL`, or `BLOCKED`. Return that result and control to the "
            "workflow controller. Do not select or execute a workflow route.",
        )
    )



def _render_required_input_artifacts(
    composition: CompiledComposition,
    instance: CompiledAgentInstance,
) -> str:
    bindings_by_name = {
        binding.role_name: binding
        for binding in composition.role_bindings
    }
    assigned_bindings = []

    for role_name in instance.role_bindings:
        try:
            assigned_bindings.append(
                bindings_by_name[role_name]
            )
        except KeyError as exc:
            raise TargetRenderingError(
                "Compiled agent instance references missing role binding "
                f"{role_name!r}: {instance.id!r}"
            ) from exc

    lines = [
        "## Required Input Artifacts",
        "",
        (
            "Static governed inputs are resolved from the canonical "
            "compiled composition."
        ),
    ]

    for binding in assigned_bindings:
        lines.extend(
            [
                "",
                f"### {binding.role_name}",
                "",
            ]
        )

        if not binding.input_artifacts:
            lines.append(
                "This role binding has no required static input artifacts."
            )
            continue

        for production in binding.input_artifacts:
            lines.append(
                "- "
                f"`artifactType`: `{production.artifact.type}`; "
                f"producer `roleBinding`: `{production.role_binding}`; "
                f"resolved `agentInstance`: `{production.agent_instance}`"
            )

    return "\n".join(lines) + "\n\n"


def _render_produced_artifacts(
    composition: CompiledComposition,
    instance: CompiledAgentInstance,
) -> str:
    productions = tuple(
        production
        for production in composition.artifact_production
        if production.agent_instance == instance.id
    )

    if not productions:
        return """## Produced Artifacts

This agent instance does not own artifact production.

"""

    lines = [
        "## Produced Artifacts",
        "",
        (
            "Produced output must satisfy each compiled artifact "
            "contract."
        ),
    ]

    for production in productions:
        artifact = production.artifact
        provenance_values = {
            "artifactType": artifact.type,
            "artifactVersion": artifact.version,
            "workflow": composition.workflow.name,
            "workflowVersion": composition.workflow.version,
            "roleBinding": production.role_binding,
            "agentInstance": production.agent_instance,
        }

        try:
            provenance_lines = tuple(
                (
                    f"  - `{identity}`: "
                    f"`{provenance_values[identity]}`"
                )
                for identity
                in artifact.provenance.required_identities
            )
        except KeyError as exc:
            raise TargetRenderingError(
                "Compiled artifact provenance contains unsupported "
                f"identity: {exc.args[0]!r}"
            ) from exc

        lines.extend(
            [
                "",
                f"### {artifact.type}",
                "",
                f"- output path pattern: `{artifact.path_pattern}`",
                (
                    "- allowed statuses: "
                    + ", ".join(artifact.allowed_statuses)
                ),
                "- required headings:",
                _markdown_list(
                    artifact.required_headings,
                    indent="  ",
                ),
                (
                    "- provenance heading: "
                    f"`{artifact.provenance.heading}`"
                ),
                "- provenance identities:",
                *provenance_lines,
                (
                    "- revision heading: "
                    f"`{artifact.revision.heading}`"
                ),
                (
                    "- revision entry: `revision: <N>` where `<N>` matches "
                    f"`{artifact.revision.pattern}`"
                ),
                (
                    "- evidence heading: "
                    f"`{artifact.evidence.heading}`"
                ),
                "- evidence required fields:",
                _markdown_list(
                    artifact.evidence.required_fields,
                    indent="  ",
                ),
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
                "- status invariants:",
                (
                    "  - `passRequiresCompleteEvidence`: `"
                    f"{str(artifact.status_invariants.pass_requires_complete_evidence).lower()}`"
                ),
                (
                    "  - `passForbidsDemonstratedNonconformance`: `"
                    f"{str(artifact.status_invariants.pass_forbids_demonstrated_nonconformance).lower()}`"
                ),
                (
                    "  - `failRequiresDemonstratedNonconformance`: `"
                    f"{str(artifact.status_invariants.fail_requires_demonstrated_nonconformance).lower()}`"
                ),
                (
                    "  - `blockedRequiresUnavailablePrerequisite`: `"
                    f"{str(artifact.status_invariants.blocked_requires_unavailable_prerequisite).lower()}`"
                ),
                "- status semantics:",
                (
                    "  - `PASS`: "
                    f"{artifact.status_semantics.pass_definition}"
                ),
                (
                    "  - `FAIL`: "
                    f"{artifact.status_semantics.fail_definition}"
                ),
                (
                    "  - `BLOCKED`: "
                    f"{artifact.status_semantics.blocked_definition}"
                ),
                (
                    "  - `mixedConditionRule`: `"
                    f"{artifact.status_semantics.mixed_condition_rule}`"
                ),
            ]
        )

    return "\n".join(lines) + "\n\n"


def _render_project_instructions(
    composition: CompiledComposition,
    *,
    heading: str,
) -> str:
    instances = tuple(
        f"`{instance.id}` ({instance.display_name})"
        for instance in composition.agent_instances
    )
    gates = tuple(
        (
            f"`{gate.name}` owned by "
            f"`{gate.owner_agent_instance}`; required test evidence: "
            + (
                ", ".join(
                    f"`{requirement.value}`"
                    for requirement in gate.required_test_evidence
                )
                if gate.required_test_evidence
                else "none"
            )
        )
        for gate in composition.workflow_gates
    )

    return f"""# {heading}

This repository uses generated agentic workflow infrastructure.

## Project

- name: {composition.project.name}
- type: {composition.project.project_type}
- architecture profile: {composition.project.architecture_profile}

## Selection

- bundle: {composition.bundle}
- profile: {composition.profile.name}
- workflow: {composition.workflow.name}

## Workflow

- start state: {composition.workflow.start_state}
- terminal states: {", ".join(composition.workflow.terminal_states)}
- default failure state: {composition.workflow.default_failure_state}
- fail closed: {str(composition.workflow.fail_closed).lower()}
- controller: {_controller_instance(composition)}

## Agent Instances

{_markdown_list(instances)}

## Workflow Gates

{_markdown_list(gates)}

## Core Rules

1. `.agentic/agentic.json` is the canonical active composition.
2. Workflow gates are fail-closed.
3. Artifact contracts are workflow memory.
4. Runtime routing follows compiled state ownership.
5. Agents must stay inside their role bindings.
6. Missing evidence must result in `BLOCKED`, not `PASS`.
7. Separation-of-duties constraints must be preserved.
8. Generated target files must not be edited manually.
"""


def _render_vscode_handoffs(
    handoffs: tuple[_Handoff, ...],
) -> str:
    if not handoffs:
        return ""

    lines = ["handoffs:"]

    for handoff in handoffs:
        lines.extend(
            [
                f"  - label: {_yaml_string(handoff.label)}",
                (
                    "    agent: "
                    f"{_yaml_string(_slugify(handoff.agent_instance))}"
                ),
                f"    prompt: {_yaml_string(handoff.prompt)}",
                "    send: false",
            ]
        )

    return "\n".join(lines) + "\n"


def _handoffs_for_instance(
    composition: CompiledComposition,
    agent_instance: str,
) -> tuple[_Handoff, ...]:
    controller = _controller_instance(composition)
    state_owners = {
        ownership.workflow_state: ownership.agent_instance
        for ownership in composition.state_ownership
    }

    if agent_instance == controller:
        start_state = composition.workflow.start_state
        target = state_owners.get(start_state)

        if target is None:
            raise TargetRenderingError(
                f"Start state {start_state!r} has no compiled owner"
            )

        handoffs = [
            _Handoff(
                label=f"Start {start_state}",
                agent_instance=target,
                prompt=(
                    f"Begin the workflow at state {start_state}. "
                    "Follow its compiled gate and artifact requirements."
                ),
            ),
        ]

        for transition in _canonical_transitions(composition):
            target = state_owners.get(transition.target)

            if target is None:
                if transition.target in composition.workflow.terminal_states:
                    continue

                raise TargetRenderingError(
                    f"Non-terminal transition target {transition.target!r} "
                    "has no compiled owner"
                )

            handoffs.append(
                _Handoff(
                    label=(
                        f"Route {transition.source} + "
                        f"{transition.result.name} "
                        f"({transition.result.value}) -> "
                        f"{transition.target}"
                    ),
                    agent_instance=target,
                    prompt=(
                        f"Current state: {transition.source}. Canonical result: "
                        f"{transition.result.name} "
                        f"({transition.result.value}). Dispatch the owner of "
                        f"selected target state {transition.target}; do not "
                        "infer, prioritize, or reclassify the route."
                    ),
                )
            )

        return tuple(handoffs)

    # State owners return a canonical result to the controller. They must not
    # receive target-native controls that let them select or execute routes.
    return ()


def _canonical_transitions(
    composition: CompiledComposition,
) -> tuple[WorkflowTransition, ...]:
    return tuple(
        sorted(
            composition.workflow.transitions,
            key=lambda transition: (
                transition.source,
                transition.result.value,
                transition.target,
            ),
        )
    )


def _validate_test_evidence_representation(
    composition: CompiledComposition,
) -> None:
    """Fail if target output cannot preserve canonical test-evidence semantics."""

    known_instances = {
        instance.id
        for instance in composition.agent_instances
    }

    for gate in composition.workflow_gates:
        test_reports = tuple(
            artifact
            for artifact in gate.required_artifacts
            if artifact.type == "TestReport"
        )

        if not test_reports:
            if gate.required_test_evidence:
                raise TargetRenderingError(
                    f"Workflow gate {gate.name!r} declares test evidence "
                    "without requiring TestReport"
                )
            continue

        if len(test_reports) != 1:
            raise TargetRenderingError(
                f"Workflow gate {gate.name!r} must resolve exactly one "
                "TestReport artifact for target rendering"
            )

        if gate.owner_agent_instance not in known_instances:
            raise TargetRenderingError(
                f"Workflow gate {gate.name!r} owner "
                f"{gate.owner_agent_instance!r} is not a rendered agent "
                "instance"
            )

        if not gate.required_test_evidence:
            raise TargetRenderingError(
                f"Workflow gate {gate.name!r} requiring TestReport must "
                "preserve non-empty required test evidence"
            )

        canonical = tuple(
            sorted(
                gate.required_test_evidence,
                key=lambda requirement: requirement.value,
            )
        )
        if canonical != gate.required_test_evidence:
            raise TargetRenderingError(
                f"Workflow gate {gate.name!r} test-evidence requirements "
                "are not in canonical lexical order"
            )

        if len(set(gate.required_test_evidence)) != len(
            gate.required_test_evidence
        ):
            raise TargetRenderingError(
                f"Workflow gate {gate.name!r} has duplicate test-evidence "
                "requirements"
            )

        for requirement in gate.required_test_evidence:
            _test_evidence_meaning(requirement)

        test_report = test_reports[0]
        missing_fields = tuple(
            field
            for field in _TEST_REPORT_EVIDENCE_FIELDS
            if field not in test_report.evidence.required_fields
        )
        if missing_fields:
            raise TargetRenderingError(
                "TestReport cannot represent required workflow test "
                f"evidence; missing evidence fields: {missing_fields}"
            )

        missing_statuses = tuple(
            status
            for status in _TEST_REPORT_STATUSES
            if status not in test_report.allowed_statuses
        )
        if missing_statuses:
            raise TargetRenderingError(
                "TestReport cannot preserve workflow test-evidence status "
                f"semantics; missing statuses: {missing_statuses}"
            )


def _validate_routing_representation(
    composition: CompiledComposition,
) -> None:
    """Fail explicitly when a target cannot preserve canonical routing."""

    controller = _controller_instance(composition)
    workflow = composition.workflow
    state_names = {state.name for state in workflow.states}
    non_terminal_names = {
        state.name for state in workflow.states if not state.terminal
    }
    terminal_names = {
        state.name for state in workflow.states if state.terminal
    }

    if workflow.start_state not in non_terminal_names:
        raise TargetRenderingError(
            f"Start state {workflow.start_state!r} must be a compiled "
            "non-terminal state for target rendering"
        )

    if workflow.default_failure_state not in terminal_names:
        raise TargetRenderingError(
            f"defaultFailureState {workflow.default_failure_state!r} must be "
            "a compiled terminal state for target rendering"
        )

    known_instances = {
        instance.id for instance in composition.agent_instances
    }

    if controller not in known_instances:
        raise TargetRenderingError(
            f"Compiled controller {controller!r} is not a rendered agent instance"
        )

    owners_by_state: dict[str, list[str]] = {}

    for ownership in composition.state_ownership:
        owners_by_state.setdefault(
            ownership.workflow_state,
            [],
        ).append(ownership.agent_instance)

    for state_name in sorted(non_terminal_names):
        owners = owners_by_state.get(state_name, [])

        if len(owners) != 1:
            raise TargetRenderingError(
                f"Non-terminal state {state_name!r} must have exactly one "
                "compiled owner for target rendering"
            )

        if owners[0] not in known_instances:
            raise TargetRenderingError(
                f"Compiled owner {owners[0]!r} for state {state_name!r} "
                "is not a rendered agent instance"
            )

    unexpected_owned_states = sorted(
        set(owners_by_state) - non_terminal_names
    )

    if unexpected_owned_states:
        raise TargetRenderingError(
            "Only non-terminal states may have compiled owners for target "
            f"rendering: {unexpected_owned_states}"
        )

    routes: dict[tuple[str, WorkflowRoutingResult], int] = {}

    for transition in _canonical_transitions(composition):
        if transition.source not in state_names:
            raise TargetRenderingError(
                f"Transition source {transition.source!r} is not a compiled state"
            )

        if transition.target not in state_names:
            raise TargetRenderingError(
                f"Transition target {transition.target!r} is not a compiled state"
            )

        if transition.source in terminal_names:
            raise TargetRenderingError(
                f"Terminal state {transition.source!r} cannot own a rendered route"
            )

        identity = (transition.source, transition.result)
        routes[identity] = routes.get(identity, 0) + 1

        if (
            transition.result is WorkflowRoutingResult.BLOCKED
            and transition.target != workflow.default_failure_state
        ):
            raise TargetRenderingError(
                f"Blocked route from {transition.source!r} must target "
                f"defaultFailureState {workflow.default_failure_state!r}"
            )

        if (
            transition.result is WorkflowRoutingResult.PASS
            and transition.target == workflow.default_failure_state
        ):
            raise TargetRenderingError(
                f"Pass route from {transition.source!r} must not target "
                f"defaultFailureState {workflow.default_failure_state!r}"
            )

    for state_name in sorted(non_terminal_names):
        for result in WorkflowRoutingResult:
            count = routes.get((state_name, result), 0)

            if count != 1:
                raise TargetRenderingError(
                    f"State {state_name!r} must have exactly one "
                    f"{result.value!r} route for target rendering; found {count}"
                )


def _controller_instance(
    composition: CompiledComposition,
) -> str:
    controller_bindings = tuple(
        binding
        for binding in composition.role_bindings
        if binding.binding_type is RoleBindingType.WORKFLOW_CONTROLLER
    )

    if (
        len(controller_bindings) == 1
        and controller_bindings[0].role_name
        == composition.controller_binding
    ):
        return controller_bindings[0].agent_instance

    raise TargetRenderingError(
        "Compiled controller binding must resolve to exactly one role binding"
    )


def _render_skill_files(
    paths: ProjectPaths,
    composition: CompiledComposition,
    output_root: str,
) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}

    for skill in composition.skills:
        source_root = (
            paths.registry_root
            / "skills"
            / skill.name
        )

        if source_root.is_symlink() or not source_root.is_dir():
            raise TargetRenderingError(
                f"Skill source directory is unavailable: {source_root}"
            )

        content_path = source_root / skill.content_path

        if (
            content_path.is_symlink()
            or not content_path.is_file()
        ):
            raise TargetRenderingError(
                f"Skill {skill.name!r} content path is unavailable: "
                f"{content_path}"
            )

        source_files = tuple(
            path
            for path in sorted(
                source_root.rglob("*"),
                key=lambda item: item.relative_to(
                    source_root
                ).as_posix(),
            )
            if path.is_file()
        )

        if not source_files:
            raise TargetRenderingError(
                f"Skill {skill.name!r} contains no files"
            )

        for source_path in source_files:
            if source_path.is_symlink():
                raise TargetRenderingError(
                    "Skill source files must not be symlinks: "
                    f"{source_path}"
                )

            relative_source = source_path.relative_to(
                source_root
            )
            output_path = (
                Path(output_root)
                / skill.name
                / relative_source
            )

            if output_path in files:
                raise TargetRenderingError(
                    f"Duplicate rendered skill path: {output_path}"
                )

            try:
                files[output_path] = source_path.read_bytes()
            except OSError as exc:
                raise TargetRenderingError(
                    f"Could not read skill source {source_path}: {exc}"
                ) from exc

    return files


def _required_output_paths(
    adapter: TargetAdapter,
    expected_names: set[str],
) -> dict[str, str]:
    paths = {
        output.name: output.path
        for output in adapter.output_paths
    }

    if set(paths) != expected_names:
        raise TargetRenderingError(
            f"Target {adapter.name!r} output paths must be "
            f"{sorted(expected_names)}, found {sorted(paths)}"
        )

    return paths


def _permission_settings(
    adapter: TargetAdapter,
    permission_profile: str,
) -> dict[str, TargetPermissionValue]:
    for mapping in adapter.permission_mappings:
        if mapping.permission_profile == permission_profile:
            return {
                setting.name: setting.value
                for setting in mapping.settings
            }

    raise TargetRenderingError(
        f"Target {adapter.name!r} has no permission mapping "
        f"for {permission_profile!r}"
    )


def _required_permission_string(
    settings: dict[str, TargetPermissionValue],
    name: str,
    target: str,
    permission_profile: str,
) -> str:
    value = settings.get(name)

    if not isinstance(value, str) or not value:
        raise TargetRenderingError(
            f"Target {target!r} permission profile "
            f"{permission_profile!r} must provide string "
            f"setting {name!r}"
        )

    return value


def _require_owned_file(
    adapter: TargetAdapter,
    path: Path,
) -> None:
    if (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
    ):
        raise TargetRenderingError(
            f"Target {adapter.name!r} rendered unsafe path: {path}"
        )

    if not any(
        path == Path(owned)
        or path.is_relative_to(Path(owned))
        for owned in adapter.owned_paths
    ):
        raise TargetRenderingError(
            f"Target {adapter.name!r} rendered file outside "
            f"owned paths: {path}"
        )


def _slugify(value: str) -> str:
    result = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1-\2",
        value,
    )
    result = result.replace("_", "-").replace(" ", "-")
    result = re.sub(r"[^a-zA-Z0-9-]+", "-", result)
    result = re.sub(r"-+", "-", result)
    result = result.strip("-").lower()

    if not result:
        raise TargetRenderingError(
            f"Runtime identity cannot be slugified: {value!r}"
        )

    return result


def _markdown_list(
    values: Iterable[str],
    *,
    indent: str = "",
) -> str:
    items = tuple(values)

    if not items:
        return f"{indent}- None"

    return "\n".join(
        f"{indent}- {item}"
        for item in items
    )


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _serialize_json(value: object) -> str:
    return (
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
