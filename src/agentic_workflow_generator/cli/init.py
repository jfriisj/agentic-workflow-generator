"""Typed project initialization command."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from agentic_workflow_generator.application import (
    GuidedInitValidationError,
    InitializationPlan,
    InitializationService,
    InitializationValidationError,
    RegistrySnapshotError,
    load_initialization_service,
    parse_answer_overrides,
)
from agentic_workflow_generator.cli.rendering import render_failure
from agentic_workflow_generator.domain import (
    Setup,
    SetupOptionClassification,
    SetupQuestion,
)
from agentic_workflow_generator.infrastructure.errors import (
    InfrastructureError,
)
from agentic_workflow_generator.registry import ProjectPaths


class InitCommandError(ValueError):
    """Raised when terminal initialization cannot continue."""


@dataclass(frozen=True, slots=True)
class Terminal:
    """Injectable terminal boundary for interactive initialization."""

    input_reader: Callable[[str], str]
    stdin_isatty: bool
    stdout_isatty: bool

    def read(self, prompt: str) -> str:
        """Read one normalized line with explicit cancellation errors."""

        try:
            return self.input_reader(prompt).strip()
        except EOFError as exc:
            raise InitCommandError(
                "interactive guided init received EOF; "
                "no files were written"
            ) from exc
        except KeyboardInterrupt as exc:
            print()
            raise InitCommandError(
                "interactive guided init was cancelled; "
                "no files were written"
            ) from exc


def default_terminal() -> Terminal:
    """Return the process terminal boundary."""

    return Terminal(
        input_reader=input,
        stdin_isatty=sys.stdin.isatty(),
        stdout_isatty=sys.stdout.isatty(),
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    terminal: Terminal | None = None,
) -> int:
    """Initialize active configuration from one bundle or setup."""

    args = _parse_args(argv)
    active_terminal = terminal or default_terminal()

    try:
        service = load_initialization_service(
            ProjectPaths(Path.cwd().resolve())
        )

        if args.guided:
            return _run_guided(
                service,
                args,
                active_terminal,
            )

        plan = service.plan_bundle(args.bundle)
        service.commit(plan)
        print(
            "PASS: Initialized .agentic/agentic.json "
            f"from bundle {plan.bundle!r}."
        )
        return 0
    except InitializationValidationError as exc:
        return render_failure(
            "Initialization",
            exc.diagnostics,
        )
    except GuidedInitValidationError as exc:
        return render_failure(
            "Guided initialization",
            exc.diagnostics,
        )
    except (
        InfrastructureError,
        RegistrySnapshotError,
        ValueError,
    ) as exc:
        print(f"FAIL: {exc}")
        return 1


def _run_guided(
    service: InitializationService,
    args: argparse.Namespace,
    terminal: Terminal,
) -> int:
    interactive = args.setup is None

    if interactive:
        _require_interactive_terminal(terminal)
        setup_name, answers = _collect_interactive_setup(
            service.guided_init.setups,
            terminal,
        )
    else:
        setup_name = args.setup
        answers = parse_answer_overrides(args.answer)

    plan = service.plan_setup(
        setup_name,
        answers,
    )

    if args.dry_run:
        service.validate_plan(plan)
        _print_guided_plan(plan)
        print(
            "PASS: Guided dry-run validated setup "
            f"{setup_name!r}; no files were written."
        )
        return 0

    if interactive:
        _print_guided_plan(plan)
        _confirm_guided_plan(terminal)

    service.commit(plan)
    print(
        "PASS: Initialized .agentic/setup-profile.json "
        f"from guided setup {setup_name!r}."
    )
    print(
        "PASS: Initialized .agentic/agentic.json "
        f"from bundle {plan.bundle!r}."
    )
    return 0


def _parse_args(
    argv: Sequence[str] | None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize Agentic configuration from a registered "
            "bundle or guided setup."
        )
    )
    parser.add_argument(
        "--bundle",
        help="Registered bundle name.",
    )
    parser.add_argument(
        "--guided",
        action="store_true",
        help=(
            "Run interactive guided initialization, or use "
            "--setup for non-interactive execution."
        ),
    )
    parser.add_argument(
        "--setup",
        help="Registered guided setup name.",
    )
    parser.add_argument(
        "--answer",
        action="append",
        default=[],
        help=(
            "Guided setup answer in question=value form. "
            "May be repeated."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate and print a guided setup plan without "
            "writing files."
        ),
    )
    args = parser.parse_args(argv)

    if args.guided:
        if args.bundle:
            parser.error(
                "--guided cannot be combined with --bundle"
            )
        if args.answer and not args.setup:
            parser.error(
                "--answer requires --setup when used with --guided"
            )
    else:
        if args.setup:
            parser.error("--setup requires --guided")
        if args.answer:
            parser.error("--answer requires --guided")
        if args.dry_run:
            parser.error("--dry-run requires --guided")
        if not args.bundle:
            parser.error(
                "one of --bundle or --guided is required"
            )

    return args


def _require_interactive_terminal(
    terminal: Terminal,
) -> None:
    if not terminal.stdin_isatty or not terminal.stdout_isatty:
        raise InitCommandError(
            "interactive --guided requires an attached terminal; "
            "use --guided --setup <setup-name> for "
            "non-interactive execution"
        )


def _collect_interactive_setup(
    setups: tuple[Setup, ...],
    terminal: Terminal,
) -> tuple[str, Mapping[str, str]]:
    while True:
        setup = _choose_interactive_setup(
            setups,
            terminal,
        )
        answers = _collect_interactive_answers(
            setup,
            terminal,
        )

        if answers is not None:
            return setup.name, answers


def _choose_interactive_setup(
    setups: tuple[Setup, ...],
    terminal: Terminal,
) -> Setup:
    if not setups:
        raise InitCommandError(
            "no guided setups are registered"
        )

    registered = tuple(
        sorted(
            setups,
            key=lambda setup: setup.name,
        )
    )

    print("== Guided Agentic Initialization ==")
    print()
    print("Select a registered guided setup:")

    for index, setup in enumerate(registered, start=1):
        default_marker = (
            " [default]"
            if len(registered) == 1
            else ""
        )
        print(
            f"  {index}. {setup.name}{default_marker}"
        )
        print(f"     {setup.description}")

    print()
    raw = terminal.read(
        "Setup number or name"
        + (" [1]" if len(registered) == 1 else "")
        + " (q to cancel): "
    )

    if raw.lower() in {"q", "quit"}:
        raise InitCommandError(
            "interactive guided init was cancelled; "
            "no files were written"
        )

    if not raw:
        if len(registered) != 1:
            raise InitCommandError(
                "a setup selection is required when "
                "multiple setups are registered"
            )
        return registered[0]

    if raw.isdigit():
        index = int(raw)

        if index < 1 or index > len(registered):
            raise InitCommandError(
                f"invalid setup number {raw!r}; expected "
                f"a value from 1 to {len(registered)}"
            )

        return registered[index - 1]

    for setup in registered:
        if setup.name == raw:
            return setup

    raise InitCommandError(
        f"unknown guided setup {raw!r}"
    )


def _collect_interactive_answers(
    setup: Setup,
    terminal: Terminal,
) -> dict[str, str] | None:
    answers: dict[str, str] = {}
    question_index = 0

    while question_index < len(setup.questions):
        question = setup.questions[question_index]
        selected = _interactive_question_selection(
            question,
            question_index,
            len(setup.questions),
            terminal,
        )

        if selected is None:
            if question_index == 0:
                return None

            previous = setup.questions[question_index - 1]
            answers.pop(previous.id, None)
            question_index -= 1
            continue

        answers[question.id] = selected
        question_index += 1

    return answers


def _interactive_question_selection(
    question: SetupQuestion,
    question_index: int,
    question_count: int,
    terminal: Terminal,
) -> str | None:
    print()
    print(
        f"Question {question_index + 1}/{question_count}: "
        f"{question.prompt}"
    )

    for option_index, option in enumerate(
        question.options,
        start=1,
    ):
        default_marker = (
            " [default]"
            if option.value == question.default_option
            else ""
        )
        print(
            f"  {option_index}. {option.label} "
            f"[{option.classification.value}]"
            f"{default_marker}"
        )
        print(f"     {option.value}")
        print(f"     {option.reason}")

    print()
    raw = terminal.read(
        f"Selection [{question.default_option}] "
        "(b to go back, q to cancel): "
    )
    lowered = raw.lower()

    if lowered in {"q", "quit"}:
        raise InitCommandError(
            "interactive guided init was cancelled; "
            "no files were written"
        )

    if lowered in {"b", "back"}:
        return None

    if not raw:
        return question.default_option

    if raw.isdigit():
        index = int(raw)

        if index < 1 or index > len(question.options):
            raise InitCommandError(
                f"invalid option number {raw!r} for question "
                f"{question.id!r}; expected a value from "
                f"1 to {len(question.options)}"
            )

        selected = question.options[index - 1]
    else:
        selected_option = next(
            (
                option
                for option in question.options
                if option.value == raw
            ),
            None,
        )

        if selected_option is None:
            raise InitCommandError(
                f"question {question.id!r} selected option "
                f"{raw!r} does not exist"
            )

        selected = selected_option

    if (
        selected.classification
        is SetupOptionClassification.BLOCKED
    ):
        raise InitCommandError(
            f"question {question.id!r} selected blocked "
            f"option {selected.value!r}"
        )

    return selected.value


def _print_guided_plan(
    plan: InitializationPlan,
) -> None:
    profile = plan.setup_profile

    if profile is None:
        raise InitCommandError(
            "guided plan has no setup profile"
        )

    print()
    print("== Generated Setup Plan ==")
    print(f"Setup: {profile.setup}")
    print(f"Mode: {profile.mode.value}")
    print("Answers:")

    for answer in profile.answers:
        print(
            f"  {answer.question}: {answer.selected} "
            f"[{answer.classification.value}]"
        )

    composition = plan.composition
    print("Selected composition:")
    print(f"  bundle: {composition.bundle}")
    print(f"  profile: {composition.profile.name}")
    print(f"  workflow: {composition.workflow.name}")
    print(
        "  agentInstances: "
        + ", ".join(
            instance.id
            for instance in composition.agent_instances
        )
    )
    print(
        "  roleBindings: "
        + ", ".join(
            binding.role_name
            for binding in composition.role_bindings
        )
    )
    print(
        "  skills: "
        + ", ".join(
            skill.name
            for skill in composition.skills
        )
    )
    print(
        "  artifacts: "
        + ", ".join(
            artifact.type
            for artifact in composition.artifacts
        )
    )
    print(
        "  targets: "
        + ", ".join(plan.targets)
    )
    print("Policy:")
    print(
        "  failFast: "
        f"{str(profile.policy.fail_fast).lower()}"
    )
    print(
        "  fallbackAllowed: "
        f"{str(profile.policy.fallback_allowed).lower()}"
    )


def _confirm_guided_plan(
    terminal: Terminal,
) -> None:
    print()
    answer = terminal.read(
        "Write .agentic/setup-profile.json "
        "and .agentic/agentic.json? [y/N]: "
    ).lower()

    if answer in {"y", "yes"}:
        return

    if answer in {"", "n", "no", "q", "quit"}:
        raise InitCommandError(
            "interactive guided init was cancelled; "
            "no files were written"
        )

    raise InitCommandError(
        f"invalid confirmation {answer!r}; expected "
        "'y' or 'n'; no files were written"
    )
