"""OpenCode runtime validation against canonical rendered output."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from agentic_workflow_generator.domain import Diagnostic
from agentic_workflow_generator.registry import ProjectPaths

from .target_materialization import (
    TargetMaterializationPlan,
    build_target_materialization_plan,
)
from .target_output_validation import validate_target_output

TARGET_MISSING_DIAGNOSTIC = "AWG-TARGET-RUNTIME-001"
EXECUTABLE_MISSING_DIAGNOSTIC = "AWG-TARGET-RUNTIME-002"
EXECUTION_FAILURE_DIAGNOSTIC = "AWG-TARGET-RUNTIME-003"
RUNTIME_REJECTION_DIAGNOSTIC = "AWG-TARGET-RUNTIME-004"
RUNTIME_CONTRACT_DIAGNOSTIC = "AWG-TARGET-RUNTIME-005"


def validate_opencode_runtime(
    paths: ProjectPaths,
) -> tuple[Diagnostic, ...]:
    """Require OpenCode to parse canonical generated output."""

    output_diagnostics = validate_target_output(paths)

    if output_diagnostics:
        return output_diagnostics

    plan = build_target_materialization_plan(paths)

    try:
        expected_default, expected_modes = (
            _planned_opencode_contract(plan)
        )
    except LookupError as exc:
        return (
            Diagnostic(
                code=TARGET_MISSING_DIAGNOSTIC,
                message=str(exc),
            ),
        )

    executable = shutil.which("opencode")

    if executable is None:
        return (
            Diagnostic(
                code=EXECUTABLE_MISSING_DIAGNOSTIC,
                message=(
                    "OpenCode executable is required for runtime "
                    "validation"
                ),
            ),
        )

    config_result = _run_opencode(
        paths.root,
        executable,
        "config",
    )

    if isinstance(config_result, Diagnostic):
        return (config_result,)

    try:
        effective_config = json.loads(
            config_result.stdout
        )
    except json.JSONDecodeError as exc:
        return (
            Diagnostic(
                code=RUNTIME_CONTRACT_DIAGNOSTIC,
                message=(
                    "OpenCode debug config returned invalid JSON: "
                    f"{exc}"
                ),
            ),
        )

    diagnostics = list(
        _validate_effective_config(
            effective_config,
            expected_default,
            expected_modes,
        )
    )

    skill_result = _run_opencode(
        paths.root,
        executable,
        "skill",
    )

    if isinstance(skill_result, Diagnostic):
        diagnostics.append(skill_result)
        return tuple(diagnostics)

    try:
        effective_skills = _skill_names(
            json.loads(skill_result.stdout)
        )
    except (
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        diagnostics.append(
            Diagnostic(
                code=RUNTIME_CONTRACT_DIAGNOSTIC,
                message=(
                    "OpenCode debug skill returned an invalid "
                    f"contract: {exc}"
                ),
            )
        )
        return tuple(diagnostics)

    expected_skills = {
        skill.name
        for skill in plan.composition.skills
    }
    missing_skills = sorted(
        expected_skills - effective_skills
    )

    if missing_skills:
        diagnostics.append(
            Diagnostic(
                code=RUNTIME_CONTRACT_DIAGNOSTIC,
                message=(
                    "OpenCode did not discover canonical skills: "
                    f"{missing_skills}"
                ),
            )
        )

    return tuple(diagnostics)


def _run_opencode(
    repository_root: Path,
    executable: str,
    debug_area: str,
) -> subprocess.CompletedProcess[str] | Diagnostic:
    try:
        result = subprocess.run(
            [
                executable,
                "debug",
                debug_area,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
            cwd=repository_root,
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        return Diagnostic(
            code=EXECUTION_FAILURE_DIAGNOSTIC,
            message=(
                f"Could not execute OpenCode debug {debug_area}: "
                f"{exc}"
            ),
        )

    if result.returncode != 0:
        return Diagnostic(
            code=RUNTIME_REJECTION_DIAGNOSTIC,
            message=(
                f"OpenCode rejected generated {debug_area} "
                f"output with exit code {result.returncode}: "
                f"{result.stdout.strip()}"
            ),
        )

    return result


def _planned_opencode_contract(
    plan: TargetMaterializationPlan,
) -> tuple[str, dict[str, str]]:
    target = next(
        (
            target
            for target in plan.rendered_targets
            if target.name == "opencode"
        ),
        None,
    )

    if target is None:
        raise LookupError(
            "Compiled composition does not enable the "
            "OpenCode target"
        )

    config_file = next(
        (
            file
            for file in target.files
            if file.path == Path("opencode.json")
        ),
        None,
    )

    if config_file is None:
        raise LookupError(
            "Canonical OpenCode rendering lacks opencode.json"
        )

    config = json.loads(
        config_file.content.decode("utf-8")
    )

    if not isinstance(config, dict):
        raise LookupError(
            "Canonical opencode.json is not an object"
        )

    default_agent = config.get("default_agent")

    if not isinstance(default_agent, str):
        raise LookupError(
            "Canonical opencode.json lacks default_agent"
        )

    modes: dict[str, str] = {}

    for file in target.files:
        if (
            file.path.parent
            != Path(".opencode/agents")
            or file.path.suffix != ".md"
        ):
            continue

        modes[file.path.stem] = _frontmatter_mode(
            file.path,
            file.content.decode("utf-8"),
        )

    if not modes:
        raise LookupError(
            "Canonical OpenCode rendering contains no agents"
        )

    return default_agent, modes


def _frontmatter_mode(
    path: Path,
    content: str,
) -> str:
    lines = content.splitlines()

    if not lines or lines[0] != "---":
        raise LookupError(
            f"Canonical agent lacks frontmatter: {path}"
        )

    for line in lines[1:]:
        if line == "---":
            break

        if line.startswith("mode:"):
            mode = line.split(":", 1)[1].strip()

            if mode:
                return mode

    raise LookupError(
        f"Canonical agent lacks mode: {path}"
    )


def _validate_effective_config(
    effective_config: object,
    expected_default: str,
    expected_modes: dict[str, str],
) -> tuple[Diagnostic, ...]:
    if not isinstance(effective_config, dict):
        return (
            Diagnostic(
                code=RUNTIME_CONTRACT_DIAGNOSTIC,
                message=(
                    "OpenCode debug config must return an object"
                ),
            ),
        )

    diagnostics: list[Diagnostic] = []

    if (
        effective_config.get("default_agent")
        != expected_default
    ):
        diagnostics.append(
            Diagnostic(
                code=RUNTIME_CONTRACT_DIAGNOSTIC,
                message=(
                    "OpenCode effective default_agent differs "
                    f"from canonical output: expected "
                    f"{expected_default!r}, found "
                    f"{effective_config.get('default_agent')!r}"
                ),
            )
        )

    effective_agents = effective_config.get("agent")

    if not isinstance(effective_agents, dict):
        diagnostics.append(
            Diagnostic(
                code=RUNTIME_CONTRACT_DIAGNOSTIC,
                message=(
                    "OpenCode effective configuration lacks "
                    "an agent object"
                ),
            )
        )
        return tuple(diagnostics)

    for agent_name, expected_mode in expected_modes.items():
        effective_agent = effective_agents.get(agent_name)

        if not isinstance(effective_agent, dict):
            diagnostics.append(
                Diagnostic(
                    code=RUNTIME_CONTRACT_DIAGNOSTIC,
                    message=(
                        "OpenCode did not discover canonical "
                        f"agent {agent_name!r}"
                    ),
                )
            )
            continue

        if effective_agent.get("mode") != expected_mode:
            diagnostics.append(
                Diagnostic(
                    code=RUNTIME_CONTRACT_DIAGNOSTIC,
                    message=(
                        f"OpenCode effective mode for "
                        f"{agent_name!r} differs from canonical "
                        f"output: expected {expected_mode!r}, "
                        f"found {effective_agent.get('mode')!r}"
                    ),
                )
            )

    return tuple(diagnostics)


def _skill_names(data: object) -> set[str]:
    if isinstance(data, list):
        return {
            item["name"]
            for item in data
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
        }

    if isinstance(data, dict):
        candidates = data.get("skills", data)

        if isinstance(candidates, list):
            return {
                item["name"]
                for item in candidates
                if isinstance(item, dict)
                and isinstance(item.get("name"), str)
            }

        if isinstance(candidates, dict):
            return {
                name
                for name in candidates
                if isinstance(name, str)
            }

    raise ValueError(
        "unsupported OpenCode debug skill JSON shape"
    )
