from pathlib import Path

import pytest

from agentic_workflow_generator.infrastructure import (
    HashReadError,
    sha256_bytes,
    sha256_file,
)


def test_sha256_bytes_returns_raw_lowercase_hex() -> None:
    assert sha256_bytes(b"agentic") == (
        "c247e9808f5e81b86fef7da1aeb81d92b8e7adc18c46ee83b946efa3cb8df673"
    )


def test_sha256_file_matches_byte_hash(
    tmp_path: Path,
) -> None:
    content = b"a" * (1024 * 1024 + 17)
    target = tmp_path / "large.bin"
    target.write_bytes(content)

    assert sha256_file(target) == sha256_bytes(content)


def test_sha256_file_wraps_read_failure(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.bin"

    with pytest.raises(
        HashReadError,
        match="could not read file for hashing",
    ) as captured:
        sha256_file(missing)

    assert captured.value.path == missing
