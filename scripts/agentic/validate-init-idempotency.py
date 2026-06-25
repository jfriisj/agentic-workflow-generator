#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path


ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
CONFIG_LABEL = ".agentic/agentic.json"
SETUP_PROFILE_PATH = ROOT / ".agentic" / "setup-profile.json"
SETUP_PROFILE_LABEL = ".agentic/setup-profile.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_init(args: argparse.Namespace) -> tuple[int, str]:
    if args.guided:
        command = [
            "scripts/agentic/agentic-gen.sh",
            "init",
            "--guided",
            "--setup",
            args.setup,
        ]
    else:
        command = [
            "scripts/agentic/agentic-gen.sh",
            "init",
            "--bundle",
            args.bundle,
        ]

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    return result.returncode, result.stdout


def tracked_files(args: argparse.Namespace) -> list[tuple[str, Path]]:
    if args.guided:
        return [
            (SETUP_PROFILE_LABEL, SETUP_PROFILE_PATH),
            (CONFIG_LABEL, CONFIG_PATH),
        ]

    return [
        (CONFIG_LABEL, CONFIG_PATH),
    ]


def collect_snapshot(args: argparse.Namespace) -> dict[str, str]:
    snapshot: dict[str, str] = {}

    for label, path in tracked_files(args):
        snapshot[label] = sha256_file(path)

    return snapshot


def require_tracked_files(args: argparse.Namespace) -> int:
    for label, path in tracked_files(args):
        if not path.is_file():
            print(f"FAIL: Required file not found: {label}")
            return 1

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that init is deterministic and idempotent."
    )
    parser.add_argument("--bundle", help="Bundle name, for example: orchestrated-delivery")
    parser.add_argument("--guided", action="store_true", help="Validate guided init idempotency.")
    parser.add_argument("--setup", help="Guided setup name, for example: orchestrated-delivery-greenfield")
    args = parser.parse_args()

    if args.guided:
        if args.bundle:
            parser.error("--guided cannot be combined with --bundle")
        if not args.setup:
            parser.error("--guided requires --setup")
    else:
        if args.setup:
            parser.error("--setup requires --guided")
        if not args.bundle:
            parser.error("one of --bundle or --guided --setup is required")

    return args


def failure_header(args: argparse.Namespace) -> str:
    if args.guided:
        return "FAIL: Guided init is not idempotent."

    return "FAIL: Init from bundle is not idempotent."


def success_message(args: argparse.Namespace) -> str:
    if args.guided:
        return (
            f"PASS: Guided init is idempotent for setup '{args.setup}'. "
            f"Checked {SETUP_PROFILE_LABEL} and {CONFIG_LABEL}."
        )

    return f"PASS: Init from bundle is idempotent for bundle '{args.bundle}'. Checked {CONFIG_LABEL}."


def main() -> int:
    args = parse_args()

    missing_status = require_tracked_files(args)
    if missing_status != 0:
        return missing_status

    first_status, first_output = run_init(args)
    if first_status != 0:
        print("FAIL: First init run failed.")
        print(first_output)
        return first_status

    try:
        after_first = collect_snapshot(args)
    except Exception as exc:
        print(f"FAIL: Could not collect init idempotency snapshot after first run: {exc}")
        return 1

    second_status, second_output = run_init(args)
    if second_status != 0:
        print("FAIL: Second init run failed.")
        print(second_output)
        return second_status

    try:
        after_second = collect_snapshot(args)
    except Exception as exc:
        print(f"FAIL: Could not collect init idempotency snapshot after second run: {exc}")
        return 1

    changed = [
        label
        for label in after_first
        if after_first[label] != after_second.get(label)
    ]

    if changed:
        print(failure_header(args))
        for label in changed:
            print(f"  - changed after second init: {label}")
        return 1

    print(success_message(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
