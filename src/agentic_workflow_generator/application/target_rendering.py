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
    ArtifactContract,
    TargetAdapter,
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


def render_enabled_targets(
    paths: ProjectPaths,
    composition: CompiledComposition,
) -> tuple[RenderedTarget, ...]:
    """Render every enabled target in compiler priority order."""

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
3. Missing required evidence must result in `BLOCKED`.
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

{_render_produced_artifacts(instance.produces)}
## Workflow Authority

The canonical active composition is:

~~~text
.agentic/agentic.json
~~~

Workflow: `{composition.workflow.name}`
"""


def _render_produced_artifacts(
    artifacts: tuple[ArtifactContract, ...],
) -> str:
    if not artifacts:
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

    for artifact in artifacts:
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
            f"`{gate.owner_agent_instance}`"
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

        return (
            _Handoff(
                label=f"Start {start_state}",
                agent_instance=target,
                prompt=(
                    f"Begin the workflow at state {start_state}. "
                    "Follow its compiled gate and artifact requirements."
                ),
            ),
        )

    owned_states = {
        state
        for state, owner in state_owners.items()
        if owner == agent_instance
    }
    handoffs: list[_Handoff] = []
    seen: set[tuple[str, str, str]] = set()

    for transition in composition.workflow.transitions:
        if transition.source not in owned_states:
            continue

        target_owner = state_owners.get(transition.target)

        if target_owner is not None:
            target = target_owner
            prompt = (
                f"Continue after state {transition.source} returned "
                f"{transition.event}. Enter state {transition.target} "
                "and follow its compiled gate and artifact requirements."
            )
        elif transition.target in composition.workflow.terminal_states:
            if transition.event.lower() == "pass":
                continue

            target = controller
            prompt = (
                f"State {transition.source} returned "
                f"{transition.event} and routed to terminal state "
                f"{transition.target}. Review the blocked outcome "
                "and decide the next fail-closed action."
            )
        else:
            raise TargetRenderingError(
                f"Transition target {transition.target!r} has no "
                "compiled owner and is not terminal"
            )

        identity = (
            transition.event,
            transition.target,
            target,
        )

        if identity in seen:
            continue

        seen.add(identity)
        handoffs.append(
            _Handoff(
                label=(
                    f"{transition.event.upper()} to {target}"
                ),
                agent_instance=target,
                prompt=prompt,
            )
        )

    return tuple(handoffs)


def _controller_instance(
    composition: CompiledComposition,
) -> str:
    for binding in composition.role_bindings:
        if binding.role_name == composition.controller_binding:
            return binding.agent_instance

    raise TargetRenderingError(
        "Compiled controller binding has no role binding"
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
