"""Validate deterministic typed initialization."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from agentic_workflow_generator.application import (
    InitializationPlan,
    InitializationService,
    RegistrySnapshotError,
    load_initialization_service,
)
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths


class InitIdempotencyError(ValueError):
    """Raised when repeated typed initialization creates drift."""


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Validate deterministic direct or guided initialization."""

    args = _parse_args(argv)

    try:
        service = load_initialization_service(
            ProjectPaths(Path.cwd().resolve())
        )
        first_plan = _plan(service, args)
        service.commit(first_plan)
        first_snapshot = _snapshot_outputs(
            service,
            first_plan,
        )

        second_plan = _plan(service, args)
        second_result = service.commit(second_plan)
        second_snapshot = _snapshot_outputs(
            service,
            second_plan,
        )

        if (
            second_result.changed
            or first_snapshot != second_snapshot
        ):
            changed_paths = sorted(
                str(path.relative_to(service.paths.root))
                for path in set(first_snapshot)
                | set(second_snapshot)
                if first_snapshot.get(path)
                != second_snapshot.get(path)
                or path in second_result.written_paths
            )
            raise InitIdempotencyError(
                "repeated initialization changed output: "
                + ", ".join(changed_paths)
            )

        print(_success_message(args))
        return 0
    except (
        InfrastructureError,
        OSError,
        RegistrySnapshotError,
        ValueError,
    ) as exc:
        print(f"FAIL: {exc}")
        return 1


def _parse_args(
    argv: Sequence[str] | None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate deterministic direct or guided "
            "typed initialization."
        )
    )
    parser.add_argument(
        "--bundle",
        help="Registered bundle name.",
    )
    parser.add_argument(
        "--guided",
        action="store_true",
        help="Validate non-interactive guided initialization.",
    )
    parser.add_argument(
        "--setup",
        help="Registered guided setup name.",
    )
    args = parser.parse_args(argv)

    if args.guided:
        if args.bundle:
            parser.error(
                "--guided cannot be combined with --bundle"
            )
        if not args.setup:
            parser.error("--guided requires --setup")
    else:
        if args.setup:
            parser.error("--setup requires --guided")
        if not args.bundle:
            parser.error(
                "one of --bundle or --guided --setup is required"
            )

    return args


def _plan(
    service: InitializationService,
    args: argparse.Namespace,
) -> InitializationPlan:
    if args.guided:
        setup_name = args.setup

        if not isinstance(setup_name, str):
            raise InitIdempotencyError(
                "guided idempotency requires a setup name"
            )

        return service.plan_setup(setup_name)

    bundle_name = args.bundle

    if not isinstance(bundle_name, str):
        raise InitIdempotencyError(
            "direct idempotency requires a bundle name"
        )

    return service.plan_bundle(bundle_name)


def _snapshot_outputs(
    service: InitializationService,
    plan: InitializationPlan,
) -> dict[Path, bytes]:
    paths = [service.paths.active_config]

    if plan.setup_profile_json is not None:
        paths.append(service.paths.setup_profile)

    snapshot: dict[Path, bytes] = {}

    for path in paths:
        if not path.is_file():
            raise InitIdempotencyError(
                f"required initialization output is missing: {path}"
            )

        snapshot[path] = path.read_bytes()

    return snapshot


def _success_message(
    args: argparse.Namespace,
) -> str:
    if args.guided:
        return (
            "PASS: Guided init is idempotent for setup "
            f"{args.setup!r}. Checked "
            ".agentic/setup-profile.json and "
            ".agentic/agentic.json."
        )

    return (
        "PASS: Init from bundle is idempotent for bundle "
        f"{args.bundle!r}. Checked .agentic/agentic.json."
    )


if __name__ == "__main__":
    raise SystemExit(main())
