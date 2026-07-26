"""Deterministic SHA-256 helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .errors import HashReadError

_READ_CHUNK_SIZE = 1024 * 1024


def sha256_bytes(content: bytes) -> str:
    """Return the lowercase hexadecimal SHA-256 digest."""

    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the raw hexadecimal SHA-256 digest of one file."""

    digest = hashlib.sha256()

    try:
        with path.open("rb") as source:
            for chunk in iter(
                lambda: source.read(_READ_CHUNK_SIZE),
                b"",
            ):
                digest.update(chunk)
    except OSError as exc:
        raise HashReadError(
            path,
            f"could not read file for hashing: {exc}",
        ) from exc

    return digest.hexdigest()
