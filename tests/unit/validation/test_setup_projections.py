import re
from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure import (
    JsonObject,
    JsonValue,
)
from agentic_workflow_generator.registry import (
    RegistryKind,
    RegistrySource,
)
from agentic_workflow_generator.validation.setups import (
    SetupDependencyProjectionError,
    project_setup_bundles,
    project_target_names,
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


def bundle_source(
    *,
    name: JsonValue = "lean-delivery",
    targets: JsonValue = None,
    filename: str = "lean-delivery.bundle.json",
) -> RegistrySource:
    data: JsonObject = {
        "name": name,
        "targets": (
            [
                "opencode",
                "vscode-copilot",
            ]
            if targets is None
            else targets
        ),
    }

    return registry_source(
        RegistryKind.BUNDLE,
        f"registry/bundles/{filename}",
        data,
    )


def target_source(
    *,
    name: JsonValue = "opencode",
    folder: str = "opencode",
) -> RegistrySource:
    return registry_source(
        RegistryKind.TARGET,
        f"registry/targets/{folder}/adapter.json",
        {
            "name": name,
        },
    )


def test_bundle_projection_is_sorted_and_preserves_targets() -> None:
    projected = project_setup_bundles(
        (
            bundle_source(
                name="review-heavy-delivery",
                targets=[
                    "vscode-copilot",
                ],
                filename="review-heavy-delivery.bundle.json",
            ),
            bundle_source(),
        )
    )

    assert tuple(bundle.name for bundle in projected) == (
        "lean-delivery",
        "review-heavy-delivery",
    )
    assert projected[0].targets == frozenset(
        {
            "opencode",
            "vscode-copilot",
        }
    )


@pytest.mark.parametrize(
    ("sources", "message"),
    [
        (
            (
                bundle_source(),
                bundle_source(
                    filename="duplicate.bundle.json",
                ),
            ),
            "bundle identity 'lean-delivery' is duplicated",
        ),
        (
            (
                bundle_source(
                    targets=[],
                ),
            ),
            "targets must be a non-empty list",
        ),
        (
            (
                bundle_source(
                    targets=[
                        "",
                    ],
                ),
            ),
            "targets[0] must be a non-empty string",
        ),
        (
            (
                bundle_source(
                    targets=[
                        "opencode",
                        "opencode",
                    ],
                ),
            ),
            "target 'opencode' is duplicated",
        ),
    ],
)
def test_bundle_projection_failures_are_explicit(
    sources: tuple[RegistrySource, ...],
    message: str,
) -> None:
    with pytest.raises(
        SetupDependencyProjectionError,
        match=re.escape(message),
    ):
        project_setup_bundles(sources)


def test_target_projection_returns_registered_names() -> None:
    assert project_target_names(
        (
            target_source(),
            target_source(
                name="vscode-copilot",
                folder="vscode-copilot",
            ),
        )
    ) == frozenset(
        {
            "opencode",
            "vscode-copilot",
        }
    )


@pytest.mark.parametrize(
    ("sources", "message"),
    [
        (
            (
                target_source(
                    name="",
                ),
            ),
            "name must be a non-empty string",
        ),
        (
            (
                target_source(),
                target_source(
                    folder="duplicate",
                ),
            ),
            "target identity 'opencode' is duplicated",
        ),
    ],
)
def test_target_projection_failures_are_explicit(
    sources: tuple[RegistrySource, ...],
    message: str,
) -> None:
    with pytest.raises(
        SetupDependencyProjectionError,
        match=re.escape(message),
    ):
        project_target_names(sources)
