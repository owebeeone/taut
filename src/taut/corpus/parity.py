"""Shared codec-parity corpus validation and target status.

This is the Phase-0 scaffold: it validates the language-neutral vector files and
reports which targets are still allowlisted while per-language replay harnesses
are being brought online.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..ir.load import load_schema
from ..wire import codec

ROOT = Path(__file__).resolve().parents[3]
PARITY_DIR = ROOT / "corpus" / "parity"
INT_VECTORS = PARITY_DIR / "int.vectors.json"
MALFORMED_VECTORS = PARITY_DIR / "malformed.vectors.json"
ALLOWLIST = PARITY_DIR / "allowlist.json"

INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1

TARGETS = ("rust", "python", "typescript", "js", "cpp", "swift", "go", "kotlin", "java")
DECODE_TAGS = {
    "Truncated",
    "TrailingBytes",
    "InvalidUtf8",
    "UnsupportedInfo",
    "UnsupportedMajor",
    "NonIntegerMapKey",
    "IntOverflow",
    "DuplicateMapKey",
    "MissingKey",
    "WrongType",
    "UnknownEnum",
    "NonCanonicalInt",
    "NegativeMapKey",
}
ENCODE_TAGS = {"IntOutOfSubset"}


class ParityValidationError(ValueError):
    """A committed parity artifact is malformed or stale."""


@dataclass(frozen=True)
class ParityStatus:
    target: str
    status: str
    reason: str


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ParityValidationError(f"missing parity artifact: {path}") from exc


def _as_int(value: Any, where: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise ParityValidationError(f"{where}: expected integer string, got {value!r}") from exc
    raise ParityValidationError(f"{where}: expected integer string, got {type(value).__name__}")


def _hex(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise ParityValidationError(f"{where}: hex value must be a string")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ParityValidationError(f"{where}: invalid hex {value!r}") from exc
    return value


def _native_intbox(value: dict[str, Any], where: str) -> dict[str, Any]:
    by_id = value.get("by_id")
    if not isinstance(by_id, list):
        raise ParityValidationError(f"{where}: by_id must be a list of [key, value] pairs")
    pairs: list[tuple[int, int]] = []
    seen_keys: set[int] = set()
    for index, pair in enumerate(by_id):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ParityValidationError(f"{where}.by_id[{index}]: expected [key, value]")
        key = _as_int(pair[0], f"{where}.by_id[{index}].key")
        val = _as_int(pair[1], f"{where}.by_id[{index}].value")
        if key in seen_keys:
            raise ParityValidationError(f"{where}.by_id[{index}]: duplicate key {key}")
        seen_keys.add(key)
        pairs.append((key, val))
    return {
        "n": _as_int(value.get("n"), f"{where}.n"),
        "by_id": dict(pairs),
    }


def validate_int_vectors(path: Path = INT_VECTORS) -> int:
    data = _load_json(path)
    if data.get("version") != 1:
        raise ParityValidationError(f"{path}: unsupported version {data.get('version')!r}")
    schema_path = ROOT / data["schema_path"]
    schema = load_schema(schema_path)
    count = 0
    for row in data.get("vectors", []):
        name = row.get("name", "<unnamed>")
        kind = row.get("kind")
        message = row.get("message")
        if message not in schema.messages:
            raise ParityValidationError(f"{path}:{name}: unknown message {message!r}")
        value = _native_intbox(row.get("value", {}), f"{path}:{name}.value")
        if kind == "round_trip":
            expected = _hex(row.get("cbor"), f"{path}:{name}.cbor")
            actual = codec.encode(schema, message, value).hex()
            if actual != expected:
                raise ParityValidationError(f"{path}:{name}: cbor mismatch {actual} != {expected}")
        elif kind == "encode_fail":
            tag = row.get("expect", {}).get("tag")
            if tag not in ENCODE_TAGS:
                raise ParityValidationError(f"{path}:{name}: unknown encode tag {tag!r}")
            ints = [value["n"], *value["by_id"].keys(), *value["by_id"].values()]
            if all(INT_MIN <= item <= INT_MAX for item in ints):
                raise ParityValidationError(f"{path}:{name}: encode_fail value is inside i64 range")
        else:
            raise ParityValidationError(f"{path}:{name}: unknown kind {kind!r}")
        count += 1
    return count


def validate_malformed_vectors(path: Path = MALFORMED_VECTORS) -> int:
    data = _load_json(path)
    if data.get("version") != 1:
        raise ParityValidationError(f"{path}: unsupported version {data.get('version')!r}")
    schema_path = ROOT / data["schema_path"]
    schema = load_schema(schema_path)
    count = 0
    for row in data.get("vectors", []):
        name = row.get("name", "<unnamed>")
        stage = row.get("stage")
        if stage not in {"raw_decode", "from_cbor", "from_wire"}:
            raise ParityValidationError(f"{path}:{name}: bad stage {stage!r}")
        _hex(row.get("bytes"), f"{path}:{name}.bytes")
        tag = row.get("expect", {}).get("tag")
        if tag not in DECODE_TAGS:
            raise ParityValidationError(f"{path}:{name}: unknown decode tag {tag!r}")
        entrypoint = row.get("schema")
        if stage == "from_cbor" and entrypoint not in schema.messages:
            raise ParityValidationError(f"{path}:{name}: unknown message {entrypoint!r}")
        if stage == "from_wire" and entrypoint not in schema.enums:
            raise ParityValidationError(f"{path}:{name}: unknown enum {entrypoint!r}")
        if not row.get("why"):
            raise ParityValidationError(f"{path}:{name}: missing why")
        count += 1
    return count


def target_statuses(path: Path = ALLOWLIST) -> list[ParityStatus]:
    data = _load_json(path)
    if data.get("version") != 1:
        raise ParityValidationError(f"{path}: unsupported version {data.get('version')!r}")
    entries: dict[str, dict[str, Any]] = {}
    for row in data.get("targets", []):
        target = row.get("target")
        if target in entries:
            raise ParityValidationError(f"{path}: duplicate target {target}")
        entries[target] = row
    unknown = sorted(set(entries) - set(TARGETS))
    if unknown:
        raise ParityValidationError(f"{path}: unknown target(s) {unknown}")
    statuses: list[ParityStatus] = []
    for target in TARGETS:
        row = entries.get(target)
        if row is None:
            statuses.append(ParityStatus(target, "gated", "shared replay harness enforced"))
            continue
        reason = row.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ParityValidationError(f"{path}: {target} has no allowlist reason")
        statuses.append(ParityStatus(target, "allowlisted", reason))
    return statuses


def validate_all(*, target: str | None = None) -> list[str]:
    if target is not None and target not in TARGETS:
        raise ParityValidationError(f"unknown target {target!r}; known: {', '.join(TARGETS)}")
    int_count = validate_int_vectors()
    malformed_count = validate_malformed_vectors()
    statuses = [s for s in target_statuses() if target is None or s.target == target]
    lines = [
        f"int vectors: {int_count}",
        f"malformed vectors: {malformed_count}",
    ]
    for status in statuses:
        lines.append(f"{status.target}: {status.status} - {status.reason}")
    return lines
