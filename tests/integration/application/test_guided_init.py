from pathlib import Path

from agentic_workflow_generator.application import (
    load_guided_init_service,
    parse_answer_overrides,
)
from agentic_workflow_generator.domain import SetupSelection
from agentic_workflow_generator.registry import ProjectPaths

REPOSITORY_ROOT = Path(__file__).parents[3]


def test_real_registry_guided_init_service_materializes_all_setups() -> None:
    service = load_guided_init_service(
        ProjectPaths(REPOSITORY_ROOT.resolve())
    )

    assert tuple(
        setup.name
        for setup in service.setups
    ) == (
        "ai-application-greenfield",
        "lean-delivery-greenfield",
        "orchestrated-delivery-greenfield",
        "review-heavy-delivery-greenfield",
    )

    overrides = parse_answer_overrides(
        (
            "target-platforms=opencode-only",
        )
    )

    for setup in service.setups:
        profile = service.materialize(
            setup.name,
            overrides,
        )

        assert profile.selected == SetupSelection(
            bundle=setup.default_selection.bundle,
            targets=("opencode",),
        )
