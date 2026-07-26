from __future__ import annotations

import shutil
from pathlib import Path

from agentic_workflow_generator.application import (
    load_initialization_service,
)
from agentic_workflow_generator.infrastructure import (
    read_json_object,
)
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


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


def test_all_registered_setups_initialize_clean_consumers(
    tmp_path: Path,
) -> None:
    consumer_root = tmp_path / "consumer-project"
    paths = copy_consumer_repository(consumer_root)
    service = load_initialization_service(paths)

    setup_names = tuple(
        setup.name
        for setup in service.guided_init.setups
    )

    assert setup_names == (
        "ai-application-greenfield",
        "lean-delivery-greenfield",
        "orchestrated-delivery-greenfield",
        "review-heavy-delivery-greenfield",
    )

    for setup_name in setup_names:
        if paths.active_config.exists():
            paths.active_config.unlink()

        if paths.setup_profile.exists():
            paths.setup_profile.unlink()

        first_plan = service.plan_setup(setup_name)
        first_result = service.commit(first_plan)

        assert first_result.changed is True
        assert first_result.written_paths == (
            paths.active_config,
            paths.setup_profile,
        )

        active_config = read_json_object(
            paths.active_config
        )
        setup_profile = read_json_object(
            paths.setup_profile
        )

        assert "agents" not in active_config
        assert "gates" not in active_config
        assert setup_profile["selected"] == {
            "bundle": first_plan.bundle,
            "targets": list(first_plan.targets),
        }

        first_config = paths.active_config.read_bytes()
        first_profile = paths.setup_profile.read_bytes()

        second_plan = service.plan_setup(setup_name)
        second_result = service.commit(second_plan)

        assert second_result.changed is False
        assert second_result.written_paths == ()
        assert paths.active_config.read_bytes() == first_config
        assert paths.setup_profile.read_bytes() == first_profile
