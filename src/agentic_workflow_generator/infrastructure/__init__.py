"""Infrastructure adapters without domain policy."""

from .errors import (
    AtomicWriteError,
    HashReadError,
    JsonDecodeFailure,
    JsonFileNotFoundError,
    JsonReadError,
    JsonRootTypeError,
    JsonSerializationError,
    ProcessExecutionError,
    TransactionRollbackError,
)
from .filesystem import (
    atomic_write_bytes,
    atomic_write_text,
    transactional_update_files,
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
from .processes import (
    ProcessResult,
    resolve_executable,
    run_process,
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
    "ProcessExecutionError",
    "ProcessResult",
    "TransactionRollbackError",
    "atomic_write_bytes",
    "atomic_write_text",
    "read_json",
    "read_json_object",
    "resolve_executable",
    "run_process",
    "serialize_json",
    "sha256_bytes",
    "sha256_file",
    "transactional_update_files",
    "transactional_write_bytes",
    "write_json",
]
