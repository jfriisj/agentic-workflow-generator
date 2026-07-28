from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest

from agentic_workflow_generator.domain import (
    TargetAdapter,
    TargetOutputPath,
    TargetPermissionMapping,
    TargetPermissionSetting,
)


def adapter() -> TargetAdapter:
    return TargetAdapter(
        name="opencode",
        version="0.1.0",
        description="OpenCode target adapter.",
        output_paths=(
            TargetOutputPath(
                name="agents",
                path=".opencode/agents",
            ),
            TargetOutputPath(
                name="instructions",
                path="AGENTS.md",
            ),
        ),
        owned_paths=(
            ".opencode/agents",
            "AGENTS.md",
        ),
        permission_mappings=(
            TargetPermissionMapping(
                permission_profile="implementation",
                settings=(
                    TargetPermissionSetting(
                        name="bash",
                        value="allow",
                    ),
                    TargetPermissionSetting(
                        name="tools",
                        value=(
                            "search",
                            "read/readFile",
                        ),
                    ),
                ),
            ),
        ),
    )


def test_target_adapter_preserves_typed_values() -> None:
    target = adapter()

    assert target.name == "opencode"
    assert target.output_paths[0] == TargetOutputPath(
        name="agents",
        path=".opencode/agents",
    )
    assert target.permission_mappings[0].settings[1].value == (
        "search",
        "read/readFile",
    )


@pytest.mark.parametrize(
    ("value", "attribute"),
    [
        (adapter(), "name"),
        (adapter().output_paths[0], "path"),
        (
            adapter().permission_mappings[0],
            "permission_profile",
        ),
        (
            adapter().permission_mappings[0].settings[0],
            "value",
        ),
    ],
)
def test_target_models_are_immutable(
    value: object,
    attribute: str,
) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(
            cast(Any, value),
            attribute,
            "changed",
        )
