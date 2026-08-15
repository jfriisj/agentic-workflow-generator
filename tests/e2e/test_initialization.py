from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from agentic_workflow_generator.application import (
    InitializationPlan,
    InitializationService,
    load_initialization_service,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class ConsumerSelection:
    mode: Literal["bundle", "setup"]
    name: str


CONSUMER_ACCEPTANCE_MATRIX = (
    ConsumerSelection("bundle", "ai-application"),
    ConsumerSelection("bundle", "lean-delivery"),
    ConsumerSelection("bundle", "orchestrated-delivery"),
    ConsumerSelection("bundle", "review-heavy-delivery"),
    ConsumerSelection("setup", "ai-application-greenfield"),
    ConsumerSelection("setup", "lean-delivery-greenfield"),
    ConsumerSelection("setup", "orchestrated-delivery-greenfield"),
    ConsumerSelection("setup", "review-heavy-delivery-greenfield"),
)


def copy_consumer_repository(
    consumer_root: Path,
) -> ProjectPaths:
    shutil.copytree(
        REPOSITORY_ROOT / "registry",
        consumer_root / "registry",
    )
    shutil.copytree(
        REPOSITORY_ROOT / ".agentic" / "schemas",
        consumer_root / ".agentic" / "schemas",
    )
    return ProjectPaths(consumer_root)


def repository_files(
    paths: ProjectPaths,
) -> frozenset[Path]:
    return frozenset(
        path.relative_to(paths.root)
        for path in paths.root.rglob("*")
        if path.is_file()
    )


def plan_selection(
    service: InitializationService,
    selection: ConsumerSelection,
) -> InitializationPlan:
    if selection.mode == "bundle":
        return service.plan_bundle(selection.name)

    return service.plan_setup(selection.name)


def test_consumer_acceptance_matrix_matches_registered_selections(
    tmp_path: Path,
) -> None:
    paths = copy_consumer_repository(
        tmp_path / "consumer-project"
    )
    service = load_initialization_service(paths)

    assert tuple(
        selection.name
        for selection in CONSUMER_ACCEPTANCE_MATRIX
        if selection.mode == "bundle"
    ) == tuple(
        bundle.name
        for bundle in service.registry.bundles
    )
    assert tuple(
        selection.name
        for selection in CONSUMER_ACCEPTANCE_MATRIX
        if selection.mode == "setup"
    ) == tuple(
        setup.name
        for setup in service.guided_init.setups
    )


@pytest.mark.parametrize(
    "selection",
    CONSUMER_ACCEPTANCE_MATRIX,
    ids=lambda selection: f"{selection.mode}:{selection.name}",
)
def test_consumer_acceptance_matrix_initializes_clean_consumers(
    tmp_path: Path,
    selection: ConsumerSelection,
) -> None:
    paths = copy_consumer_repository(
        tmp_path / "consumer-project"
    )
    initial_files = repository_files(paths)

    assert initial_files
    assert all(
        relative_path.parts[0] == "registry"
        or relative_path.parts[:2] == (".agentic", "schemas")
        for relative_path in initial_files
    )
    assert not paths.active_config.exists()
    assert not paths.setup_profile.exists()
    assert not paths.lockfile.exists()
    assert not paths.generated_root.exists()

    service = load_initialization_service(paths)
    registered_targets = tuple(
        target.name
        for target in service.registry.targets
    )
    first_plan = plan_selection(service, selection)

    assert first_plan.targets == registered_targets

    first_result = service.commit(first_plan)
    expected_written_paths = frozenset(
        (
            paths.active_config,
            paths.setup_profile,
        )
        if selection.mode == "setup"
        else (paths.active_config,)
    )

    assert first_result.changed is True
    assert frozenset(first_result.written_paths) == expected_written_paths

    active_config = read_json_object(paths.active_config)

    assert "agents" not in active_config
    assert "gates" not in active_config

    if selection.mode == "setup":
        setup_profile = read_json_object(paths.setup_profile)
        assert setup_profile["selected"] == {
            "bundle": first_plan.bundle,
            "targets": list(first_plan.targets),
        }
    else:
        assert not paths.setup_profile.exists()

    expected_new_files = frozenset(
        path.relative_to(paths.root)
        for path in expected_written_paths
    )
    assert repository_files(paths) - initial_files == expected_new_files
    assert not paths.lockfile.exists()
    assert not paths.generated_root.exists()

    first_outputs = {
        path: path.read_bytes()
        for path in expected_written_paths
    }

    second_plan = plan_selection(service, selection)
    second_result = service.commit(second_plan)

    assert second_plan.active_config == first_plan.active_config
    assert second_plan.setup_profile_json == first_plan.setup_profile_json
    assert second_result.changed is False
    assert second_result.written_paths == ()
    assert {
        path: path.read_bytes()
        for path in expected_written_paths
    } == first_outputs
