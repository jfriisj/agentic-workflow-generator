"""Infrastructure adapters without domain policy."""

from .errors import (
    AtomicWriteError,
    HashReadError,
    JsonDecodeFailure,
    JsonFileNotFoundError,
    JsonReadError,
    JsonRootTypeError,
    JsonSerializationError,
)
from .filesystem import atomic_write_bytes, atomic_write_text
from .hashing import sha256_bytes, sha256_file
from .json_io import (
    JsonObject,
    JsonValue,
    read_json,
    read_json_object,
    serialize_json,
    write_json,
)

__all__ = [
    "AtomicWriteError",
    "HashReadError",
    "JsonDecodeFailure",
    "JsonFileNotFoundError",
    "JsonObject",
    "JsonReadError",
    "JsonRootTypeError",
    "JsonSerializationError",
    "JsonValue",
    "atomic_write_bytes",
    "atomic_write_text",
    "read_json",
    "read_json_object",
    "serialize_json",
    "sha256_bytes",
    "sha256_file",
    "write_json",
]
