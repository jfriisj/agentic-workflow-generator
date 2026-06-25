#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path


ROOT = Path.cwd()
CONFIG_PATH = ROOT / ".agentic" / "agentic.json"
CONFIG_LABEL = ".agentic/agentic.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_init(bundle: str) -> tuple[int, str]:
    result = subprocess.run(
        ["scripts/agentic/agentic-gen.sh", "init", "--bundle", bundle],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    return result.returncode, result.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate that init --bundle is deterministic and idempotent.")
    parser.add_argument("--bundle", required=True, help="Bundle name, for example: orchestrated-delivery")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not CONFIG_PATH.is_file():
        print(f"FAIL: Required file not found: {CONFIG_LABEL}")
        return 1

    first_status, first_output = run_init(args.bundle)
    if first_status != 0:
        print("FAIL: First init --bundle run failed.")
        print(first_output)
        return first_status

    try:
        after_first = sha256_file(CONFIG_PATH)
    except Exception as exc:
        print(f"FAIL: Could not collect init idempotency snapshot after first run: {exc}")
        return 1

    second_status, second_output = run_init(args.bundle)
    if second_status != 0:
        print("FAIL: Second init --bundle run failed.")
        print(second_output)
        return second_status

    try:
        after_second = sha256_file(CONFIG_PATH)
    except Exception as exc:
        print(f"FAIL: Could not collect init idempotency snapshot after second run: {exc}")
        return 1

    if after_first != after_second:
        print("FAIL: Init from bundle is not idempotent.")
        print(f"  - changed after second init: {CONFIG_LABEL}")
        return 1

    print(f"PASS: Init from bundle is idempotent for bundle '{args.bundle}'. Checked {CONFIG_LABEL}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
