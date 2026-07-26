"""Infrastructure adapters without domain policy."""

from .errors import (
    AtomicWriteError,
    HashReadError,
    JsonDecodeFailure,
    JsonFileNotFoundError,
    JsonReadError,
    JsonRootTypeError,
    JsonSerializationError,
    TransactionRollbackError,
)
from .filesystem import (
    atomic_write_bytes,
    atomic_write_text,
    transactional_write_bytes,
)
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
    "TransactionRollbackError",
    "atomic_write_bytes",
    "atomic_write_text",
    "read_json",
    "read_json_object",
    "serialize_json",
    "sha256_bytes",
    "sha256_file",
    "transactional_write_bytes",
    "write_json",
]
