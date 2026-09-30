"""Shared codec-parity gate — the leading cross-language conformance corpus.

Phase 0 of `dev-docs/TautCodecParityPlan.md`, hardened by its §8 P1. Three
language-neutral vector files (`corpus/parity/{int,malformed,bounds}.vectors.json`,
produced by `gen_vectors.py`, contract `taut-codec-parity/i64/v1`) are replayed through
**every codec that has a runner**. A target is **gated** (must pass) unless it appears in `allowlist.json`,
in which case it is **allowlisted**: its runner still RUNS and REPORTS observed
failures (xfail-that-runs), it just doesn't fail CI. Governance is the inverse
check too — CI fails if an *allowlisted* target passes fully (a green target must
be de-listed) or a *gated* target fails.

Runners. `python` replays in-process (`run_python`). Any other target has a runner
exactly when the module `taut.corpus.parity_<target>` exists and exposes
`run(forward_compat: bool = False) -> TargetReport`: `_RUNNERS` resolves it, so adding a
target is adding that module and deleting its allowlist entry. `parity_rust.py` is the
model a compiled runner copies: find the toolchain (`toolchains.py`), generate the
fixture's code, build, run. A missing toolchain is the only skip; a failed generation or
build is RED (TautCheckedDecode.md §5.4).

Variants (TautCheckedDecode.md §8 question 10). The seven generated targets
(`FC_TARGETS`) each run twice: as themselves, and as `<target>/fc`, the fixture generated
with `forward_compat=True` (their runner's `run(forward_compat=True)`). `variants()` lists
every name the gate runs; a variant is gated or allowlisted, and governed, like a target,
and has its own summary line. `TARGETS` stays the nine languages.

Unknown fields. Python, TypeScript and every `<target>/fc` keep a message's unknown
fields on re-encode; the seven generated without forward-compat drop them
(`keeps_unknown_fields`). A from_cbor row may add `expect_dropping` beside `expect`: a
codec that drops unknown fields is judged by it, and every other codec by `expect`
(`row_expect`).

Runner protocol (TautCheckedDecode.md CD-C4). A runner prints one line per row,
`name<TAB>outcome<TAB>detail`:
  - an int row: `pass`, `fail` or `type-satisfied`; the runner checks the round
    trip itself;
  - a malformed row: `ok` when it decoded without error, with the detail the hex
    of its re-encoding: for a `raw_decode` row the decoded tree encoded again, for
    a `from_cbor` row the typed value's own encode (`to_cbor` or the language's
    equivalent) encoded, and for a `from_wire` row (an enum, never an accept row)
    an empty detail; `err` with the detail `Tag;field=value...`, one
    `;field=value` for each payload field its DecodeError carries
    (`PAYLOAD_FIELDS`); or `untyped`, with a description, when anything other than
    the language's DecodeError escapes.
The gate, not the runner, judges a malformed row (`judge`), by the expectation that
applies to the runner's codec (`row_expect`). An accept expectation,
`{"accept": true}` or `{"accept": true, "reencode": "<hex>"}`, passes only on `ok`
whose detail equals its expected re-encoding: `reencode` when given, else the row's
own bytes. That is D2's law, decode ok => encode(decode(bytes)) == bytes, and
`reencode` states a declared exception to it (an absent `MISSING_OK` key re-encodes
as null). A `{"tag": ...}` row passes when the tag matches and every payload field
it names matches when compared as a string (`PAYLOAD_EXEMPT` lists the fields a
runtime does not carry). A row never reported fails, and a runner that exits
non-zero fails its target (`parse_report`).

Bounds (TautCheckedDecode.md CD-C1-C4; TautOptions.md OPT-P1). `bounds.vectors.json`
(`bounds_rows`) holds rows B1-B30, judged as malformed rows are; its header records
`default_max_depth` and `max_depth_ceiling`. A row's `bytes` may be a list of segments,
each a hex string or `{"repeat": "<hex>", "count": N}`, with `len` the expanded length
(`segments`, `row_bytes`). A raw row's `limits` are what its call passes, `max_depth`
and/or `max_encoded_len`; every bounds row's `bounds` are what it is decoded under,
`max_depth` always and `max_encoded_len` where a length bound applies. Five additions to
the protocol, which step D1 brings to every runner but Python's:
  1. Once per run, print `#constants<TAB>default_max_depth=<n>;max_depth_ceiling=<n>`
     from the runtime's own constants, which the gate compares with the bounds header;
     a missing, repeated or different line is a target fault (`NO_CONSTANTS`).
  2. A raw_decode row with `limits` calls the raw decode with them.
  3. Every from_cbor row, malformed or bounds, decodes from bytes through its message's
     typed entry point, which applies its effective bounds (CD-B3), not a raw decode
     then from_cbor.
  4. A from_cbor row's line adds a fourth column, the bounds that entry point resolved:
     `max_depth=<n>;max_encoded_len=<n, or empty for none>`. Where the row has `bounds`
     the gate requires and compares it, elsewhere checks its form; no other row has one.
  5. A runner expands segmented bytes itself (a 100,000-deep row is 200 KB of hex,
     beyond a Java string literal) and reports an expansion whose length is not `len`
     as `untyped`.
Python's in-process harness prints the same lines, and the gate parses them
(`run_python`).

This corpus **SUPPLEMENTS** `tautc corpus` / the message golden corpora; it never
replaces them. Entry point: `tautc parity`.

`lead` rows (see `gen_vectors.py`) are replayed by this gate but skipped by the
per-language *baseline* smoke tests in `src/tests/test_{rust,ts,js,go,...}.py`.
"""

from __future__ import annotations

import functools
import importlib
import importlib.util
import json
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..ir.load import load_schema
from ..ir.model import MsgRef
from ..ir.options import DEFAULT_MAX_DEPTH, MAX_DEPTH_CEILING
from ..wire import cbor, codec

ROOT = Path(__file__).resolve().parents[3]
PARITY_DIR = ROOT / "corpus" / "parity"
INT_VECTORS = PARITY_DIR / "int.vectors.json"
MALFORMED_VECTORS = PARITY_DIR / "malformed.vectors.json"
BOUNDS_VECTORS = PARITY_DIR / "bounds.vectors.json"
ALLOWLIST = PARITY_DIR / "allowlist.json"
# The contract every vector file and the allowlist name (TautCheckedDecode.md CD-V1).
CONTRACT = "taut-codec-parity/i64/v1"

INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1

TARGETS = ("rust", "python", "typescript", "js", "cpp", "swift", "go", "kotlin", "java")
# The seven generated targets: each also runs as `<target>/fc`, generated with
# forward_compat (TautCheckedDecode.md §8 question 10).
FC_TARGETS = ("rust", "js", "cpp", "swift", "go", "kotlin", "java")
FC_SUFFIX = "/fc"
# The IR-driven codecs, which keep a message's unknown fields on re-encode without a
# forward-compat build.
KEEP_UNKNOWN = frozenset({"python", "typescript"})
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
    "TooDeep",
    "TooLarge",
}
ENCODE_TAGS = {"IntOutOfSubset"}
# The payload fields a malformed row may name and a runner reports, in report order.
PAYLOAD_FIELDS = ("info", "major", "key", "expected", "enum", "value", "len", "limit")
# The two bounds, in the order a raw row's `limits`, a row's `bounds` and a bounds column name them.
BOUND_FIELDS = ("max_depth", "max_encoded_len")
# The first column of the line a runner prints once per run with its runtime's constants, and
# the fault that labels a runner that printed none (the bounds protocol, item 1).
CONSTANTS = "#constants"
NO_CONSTANTS = "no #constants line"
# A bounds column's form (item 4); `max_encoded_len` is empty where no length bound applies.
_BOUNDS_COLUMN = re.compile(r"max_depth=[0-9]+;max_encoded_len=[0-9]*")
# The row kinds judged by the comparator: malformed.vectors.json's and bounds.vectors.json's.
DECODE_KINDS = ("malformed", "bounds")
# Per target, the (tag, field) payloads its runtime does not carry; the gate does
# not compare them (CD-C4).
PAYLOAD_EXEMPT: dict[str, frozenset[tuple[str, str]]] = {
    "rust": frozenset({("IntOverflow", "value")}),  # DecodeError::IntOverflow has no value
}
BUILD_TIMEOUT = 600  # seconds, per build step
RUN_TIMEOUT = 300    # seconds, per runner


class ParityValidationError(ValueError):
    """A committed parity artifact is malformed or stale."""


@dataclass(frozen=True)
class ParityStatus:
    target: str
    status: str
    reason: str
    phase: str = ""
    owner: str = ""


# --- variants and the unknown-field model ---------------------------------------------

def variant(target: str, forward_compat: bool) -> str:
    """The name of `target`'s variant: `<target>/fc` for its forward-compat build."""
    return target + FC_SUFFIX if forward_compat else target


def split_variant(name: str) -> tuple[str, bool]:
    """A variant name's target, and whether it names that target's forward-compat build."""
    if name.endswith(FC_SUFFIX):
        return name[: -len(FC_SUFFIX)], True
    return name, False


def variants() -> tuple[str, ...]:
    """Every name the gate runs, gates and allowlists, in summary order: each target, and
    after each generated target its `<target>/fc`."""
    names: list[str] = []
    for target in TARGETS:
        names.append(target)
        if target in FC_TARGETS:
            names.append(variant(target, True))
    return tuple(names)


def keeps_unknown_fields(name: str) -> bool:
    """Whether the codec `name` names keeps a message's unknown fields on re-encode:
    python, typescript and every `<target>/fc` do; the generated targets built without
    forward-compat drop them (TautCheckedDecode.md §8 question 10)."""
    target, forward_compat = split_variant(name)
    return forward_compat or target in KEEP_UNKNOWN


def row_expect(name: str, row: Mapping[str, Any]) -> dict[str, Any]:
    """The expectation `name`'s codec is judged by: a row's `expect_dropping` when it has
    one and the codec drops unknown fields, else its `expect`."""
    if "expect_dropping" in row and not keeps_unknown_fields(name):
        return row["expect_dropping"]
    return row["expect"]


# --- artifact validation ------------------------------------------------------

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


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_file(data: Mapping[str, Any], path: Path) -> None:
    """Every parity file, the allowlist included: version 1 of this gate's contract."""
    if data.get("version") != 1:
        raise ParityValidationError(f"{path}: unsupported version {data.get('version')!r}")
    if data.get("contract") != CONTRACT:
        raise ParityValidationError(f"{path}: contract {data.get('contract')!r}, expected {CONTRACT!r}")


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
    return {"n": _as_int(value.get("n"), f"{where}.n"), "by_id": dict(pairs)}


def _check_one_expect(expect: Any, where: str) -> None:
    """`{"accept": true}`, optionally with the expected re-encoding as
    `"reencode": "<hex>"`, or a known decode tag with known payload fields (CD-C2)."""
    if not isinstance(expect, dict):
        raise ParityValidationError(f"{where}: expect must be an object")
    if "accept" in expect:
        if expect.get("accept") is not True or set(expect) - {"accept", "reencode"}:
            raise ParityValidationError(
                f"{where}: an accept row expects {{\"accept\": true}}, optionally with \"reencode\"")
        if "reencode" in expect:
            _hex(expect["reencode"], f"{where}.reencode")
        return
    tag = expect.get("tag")
    if tag not in DECODE_TAGS:
        raise ParityValidationError(f"{where}: unknown decode tag {tag!r}")
    unknown = sorted(set(expect) - {"tag", *PAYLOAD_FIELDS})
    if unknown:
        raise ParityValidationError(f"{where}: unknown payload field(s) {unknown}")


def _check_expect(row: Mapping[str, Any], where: str) -> None:
    """A malformed row's `expect` and, on a from_cbor row, its optional `expect_dropping`:
    what a codec that drops a message's unknown fields must do instead (question 10). Each
    is a well-formed expectation, and `expect_dropping` differs from `expect`."""
    _check_one_expect(row.get("expect"), f"{where}.expect")
    if "expect_dropping" not in row:
        return
    if row.get("stage") != "from_cbor":
        raise ParityValidationError(f"{where}: only a from_cbor row has expect_dropping; "
                                    "unknown fields are a message's")
    _check_one_expect(row["expect_dropping"], f"{where}.expect_dropping")
    if row["expect_dropping"] == row["expect"]:
        raise ParityValidationError(f"{where}: expect_dropping equals expect; leave it out")


def _check_bytes(row: Mapping[str, Any], where: str) -> int:
    """A row's `bytes`, a hex string or a non-empty list of segments, each a hex string or
    `{"repeat": "<hex>", "count": N}` with N > 0 (CD-C2); returns the expanded length."""
    raw = row.get("bytes")
    if isinstance(raw, str):
        return len(bytes.fromhex(_hex(raw, f"{where}.bytes")))
    if not isinstance(raw, list) or not raw:
        raise ParityValidationError(f"{where}.bytes: a hex string or a non-empty list of segments")
    length = 0
    for index, seg in enumerate(raw):
        at = f"{where}.bytes[{index}]"
        if isinstance(seg, str):
            length += len(bytes.fromhex(_hex(seg, at)))
        elif (isinstance(seg, dict) and set(seg) == {"repeat", "count"} and _is_int(seg["count"])
              and seg["count"] > 0 and _hex(seg["repeat"], f"{at}.repeat")):
            length += len(bytes.fromhex(seg["repeat"])) * seg["count"]
        else:
            raise ParityValidationError(
                f'{at}: a segment is a hex string or {{"repeat": "<hex>", "count": N}}, N > 0')
    return length


def _check_limits(row: Mapping[str, Any], where: str) -> None:
    """A raw row's `limits`, what its call passes: `max_depth`, at least 1, and/or
    `max_encoded_len`, at least 0 (a call argument out of range is misuse, not input:
    TautOptions.md OPT-P3). A typed decode takes none (CD-B3)."""
    if "limits" not in row:
        return
    if row.get("stage") != "raw_decode":
        raise ParityValidationError(f"{where}: only a raw_decode row has limits; a typed decode takes none")
    limits = row["limits"]
    if not isinstance(limits, dict) or not limits or set(limits) - set(BOUND_FIELDS):
        raise ParityValidationError(f"{where}.limits: max_depth and/or max_encoded_len, or no limits")
    floors = {"max_depth": 1, "max_encoded_len": 0}
    for name, value in limits.items():
        if not _is_int(value) or value < floors[name]:
            raise ParityValidationError(f"{where}.limits.{name}: an int of at least {floors[name]}, "
                                        f"got {value!r}")


def decoded_under(schema: Any, row: Mapping[str, Any]) -> dict[str, int]:
    """The bounds a raw_decode or from_cbor row is decoded under (TautOptions.md OPT-P1): a
    raw row's `limits`, the depth capped at the ceiling, else the defaults; a from_cbor row's
    message's effective values, as Python resolves them (`codec.bounds`). `max_encoded_len`
    only where a length bound applies."""
    if row["stage"] == "raw_decode":
        limits = row.get("limits", {})
        depth = min(limits.get("max_depth", DEFAULT_MAX_DEPTH), MAX_DEPTH_CEILING)
        length = limits.get("max_encoded_len")
    else:
        depth, length = codec.bounds(schema, MsgRef(row["schema"]))
    return {"max_depth": depth} if length is None else {"max_depth": depth, "max_encoded_len": length}


def _check_bounds(row: Mapping[str, Any], schema: Any, where: str) -> None:
    """A row's `bounds` are `max_depth` and, where a length bound applies, `max_encoded_len`,
    and equal what it is decoded under (`decoded_under`)."""
    bounds = row["bounds"]
    if row.get("stage") == "from_wire":
        raise ParityValidationError(f"{where}: a from_wire row has no bounds")
    if (not isinstance(bounds, dict) or "max_depth" not in bounds or set(bounds) - set(BOUND_FIELDS)
            or not all(_is_int(value) for value in bounds.values())):
        raise ParityValidationError(f"{where}.bounds: max_depth, and max_encoded_len where a length "
                                    "bound applies")
    want = decoded_under(schema, row)
    if bounds != want:
        raise ParityValidationError(f"{where}: bounds {bounds}, but it is decoded under {want}")


def _check_decode_row(row: Mapping[str, Any], schema: Any, where: str, *, bounds_file: bool) -> None:
    """One malformed or bounds row (CD-C2). A bounds row is raw_decode or from_cbor and has
    `len` and `bounds`; any row may have them, and segmented `bytes` and `limits`, which are
    then checked the same way."""
    stage = row.get("stage")
    stages = ("raw_decode", "from_cbor") if bounds_file else ("raw_decode", "from_cbor", "from_wire")
    if stage not in stages:
        raise ParityValidationError(f"{where}: bad stage {stage!r}")
    length = _check_bytes(row, where)
    if "len" in row and not (_is_int(row["len"]) and row["len"] == length):
        raise ParityValidationError(f"{where}: bytes expand to {length} bytes, len is {row['len']!r}")
    if bounds_file and "len" not in row:
        raise ParityValidationError(f"{where}: missing len, the expanded length")
    _check_limits(row, where)
    _check_expect(row, where)
    entrypoint = row.get("schema")
    if stage == "from_cbor" and entrypoint not in schema.messages:
        raise ParityValidationError(f"{where}: unknown message {entrypoint!r}")
    if stage == "from_wire" and entrypoint not in schema.enums:
        raise ParityValidationError(f"{where}: unknown enum {entrypoint!r}")
    if stage == "from_wire" and "accept" in row["expect"]:
        raise ParityValidationError(f"{where}: a from_wire row is an enum and never accepts")
    if "bounds" in row:
        _check_bounds(row, schema, where)
    elif bounds_file:
        raise ParityValidationError(f"{where}: missing bounds, what it is decoded under")
    if not row.get("why"):
        raise ParityValidationError(f"{where}: missing why")


def _validate_decode_rows(path: Path, data: Mapping[str, Any], *, bounds_file: bool) -> int:
    _check_file(data, path)
    schema = load_schema(ROOT / data["schema_path"])
    count = 0
    names: set[str] = set()
    for row in data.get("vectors", []):
        name = row.get("name", "<unnamed>")
        if name in names:
            raise ParityValidationError(f"{path}:{name}: duplicate row name")
        names.add(name)
        _check_decode_row(row, schema, f"{path}:{name}", bounds_file=bounds_file)
        count += 1
    return count


def validate_int_vectors(path: Path = INT_VECTORS) -> int:
    data = _load_json(path)
    _check_file(data, path)
    schema = load_schema(ROOT / data["schema_path"])
    count = 0
    names: set[str] = set()
    for row in data.get("vectors", []):
        name = row.get("name", "<unnamed>")
        if name in names:
            raise ParityValidationError(f"{path}:{name}: duplicate row name")
        names.add(name)
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
    return _validate_decode_rows(path, _load_json(path), bounds_file=False)


def validate_bounds_vectors(path: Path = BOUNDS_VECTORS) -> int:
    """`bounds.vectors.json` (CD-C1, CD-C2): the parity fixture, a header recording taut's two
    depth numbers (`taut.ir.options`', which every runtime's constants must equal), and rows
    B1-B30, each with `len` and `bounds`, named apart from the other files' rows."""
    data = _load_json(path)
    _check_file(data, path)
    if data.get("schema_path") != _load_json(INT_VECTORS).get("schema_path"):
        raise ParityValidationError(f"{path}: schema_path {data.get('schema_path')!r} is not the "
                                    "fixture int.vectors.json names")
    header = {name: data.get(name) for name in ("default_max_depth", "max_depth_ceiling")}
    if (header != {"default_max_depth": DEFAULT_MAX_DEPTH, "max_depth_ceiling": MAX_DEPTH_CEILING}
            or not all(_is_int(value) for value in header.values())):
        raise ParityValidationError(f"{path}: header {header}, but taut's default_max_depth is "
                                    f"{DEFAULT_MAX_DEPTH} and its max_depth_ceiling {MAX_DEPTH_CEILING}")
    count = _validate_decode_rows(path, data, bounds_file=True)
    elsewhere = {row.get("name") for row in [*int_rows(), *malformed_rows()]}
    shared = sorted(elsewhere & {row.get("name") for row in data.get("vectors", [])})
    if shared:
        raise ParityValidationError(f"{path}: row name(s) {shared} also name int or malformed rows")
    return count


def target_statuses(path: Path = ALLOWLIST) -> list[ParityStatus]:
    """Each variant's status, in `variants()` order: allowlisted when the allowlist names it,
    else gated. An entry names a target or a `<target>/fc` variant, each on its own."""
    data = _load_json(path)
    _check_file(data, path)
    entries: dict[str, dict[str, Any]] = {}
    for row in data.get("targets", []):
        target = row.get("target")
        if target in entries:
            raise ParityValidationError(f"{path}: duplicate target {target}")
        entries[target] = row
    known = variants()
    unknown = sorted(set(entries) - set(known), key=str)
    if unknown:
        raise ParityValidationError(f"{path}: unknown target(s) {unknown}")
    statuses: list[ParityStatus] = []
    for target in known:
        row = entries.get(target)
        if row is None:
            statuses.append(ParityStatus(target, "gated", "shared replay harness enforced"))
            continue
        for key in ("reason", "phase", "owner"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise ParityValidationError(f"{path}: {target} has no allowlist {key}")
        statuses.append(ParityStatus(target, "allowlisted", row["reason"], row["phase"], row["owner"]))
    return statuses


def allowlisted_targets(path: Path = ALLOWLIST) -> set[str]:
    return {s.target for s in target_statuses(path) if s.status == "allowlisted"}


# --- reports --------------------------------------------------------------------

PASS, FAIL, TYPE_SATISFIED = "pass", "fail", "type-satisfied"  # a judged row's status
OK, ERR, UNTYPED = "ok", "err", "untyped"                      # a malformed row's outcome
NO_REPORT = "no report"


@dataclass(frozen=True)
class VectorResult:
    name: str
    kind: str          # "round_trip" | "encode_fail" | "malformed" | "bounds"
    expected_tag: str  # the expected tag; "accept" for an accept row; "" for round_trip
    status: str        # PASS | FAIL | TYPE_SATISFIED
    detail: str
    lead: bool


@dataclass
class TargetReport:
    target: str
    available: bool
    skip_reason: str = ""
    results: list[VectorResult] = field(default_factory=list)
    # A target-level failure (generation, build, exit status, stray report lines);
    # its first line labels it. Any fault makes the target RED.
    fault: str = ""

    @property
    def failures(self) -> list[VectorResult]:
        return [r for r in self.results if r.status == FAIL]

    @property
    def green(self) -> bool:
        return self.available and not self.fault and not self.failures

    @property
    def failed_tags(self) -> list[str]:
        return sorted({(r.expected_tag or r.name) for r in self.failures})


# --- what a runner needs: rows, dispatch, report parsing, the comparator ----------

def parity_schema() -> Any:
    """The fixture the vector files name (`ir/parity_int.taut.py`)."""
    data = _load_json(INT_VECTORS)
    return load_schema(ROOT / data["schema_path"])


def int_rows() -> list[dict]:
    return _load_json(INT_VECTORS)["vectors"]


def malformed_rows() -> list[dict]:
    return _load_json(MALFORMED_VECTORS)["vectors"]


def bounds_rows() -> list[dict]:
    return _load_json(BOUNDS_VECTORS)["vectors"]


def decode_rows() -> list[dict]:
    """The rows the comparator judges: malformed rows, then bounds rows."""
    return [*malformed_rows(), *bounds_rows()]


def segments(row: Mapping[str, Any]) -> list[tuple[str, int]]:
    """A row's `bytes` as `(hex, count)` pairs, in order, for a runner to embed and expand
    (the bounds protocol, item 5): a hex string is one pair, and so is each segment of a
    list, a hex string or `{"repeat": "<hex>", "count": N}`."""
    raw = row["bytes"]
    if isinstance(raw, str):
        return [(raw, 1)]
    return [(seg, 1) if isinstance(seg, str) else (seg["repeat"], seg["count"]) for seg in raw]


def row_bytes(row: Mapping[str, Any]) -> bytes:
    """A row's input: its segments expanded, and checked against its `len` where it has one."""
    data = b"".join(bytes.fromhex(hexed) * count for hexed, count in segments(row))
    if "len" in row and len(data) != row["len"]:
        raise ParityValidationError(f"{row.get('name')}: bytes expand to {len(data)} bytes, "
                                    f"len is {row['len']}")
    return data


def format_constants(default_max_depth: int, max_depth_ceiling: int) -> str:
    """The second column of a runner's `#constants` line (the bounds protocol, item 1)."""
    return f"default_max_depth={default_max_depth};max_depth_ceiling={max_depth_ceiling}"


def expected_constants() -> str:
    """What a runner's `#constants` line must say: the bounds header's two numbers."""
    data = _load_json(BOUNDS_VECTORS)
    return format_constants(data["default_max_depth"], data["max_depth_ceiling"])


def format_bounds(bounds: Mapping[str, Any]) -> str:
    """A bounds column (the bounds protocol, item 4), from a row's `bounds` or a resolution:
    `max_depth=<n>;max_encoded_len=<n>`, the length empty where none applies."""
    length = bounds.get("max_encoded_len")
    return f"max_depth={bounds['max_depth']};max_encoded_len={'' if length is None else length}"


@dataclass(frozen=True)
class Dispatch:
    """The fixture's typed entry points: a `from_cbor` row names a message and a
    `from_wire` row names an enum. Runners build their dispatch from this."""

    messages: tuple[str, ...]
    enums: tuple[str, ...]


def fixture_dispatch(schema: Any | None = None) -> Dispatch:
    schema = parity_schema() if schema is None else schema
    return Dispatch(tuple(schema.messages), tuple(schema.enums))


def write_json_rows(dest: Path, schema: Any | None = None) -> None:
    """For a runner that reads JSON: the three vector files and `dispatch.json`."""
    dispatch = fixture_dispatch(schema)
    for path in (INT_VECTORS, MALFORMED_VECTORS, BOUNDS_VECTORS):
        (dest / path.name).write_text(path.read_text())
    (dest / "dispatch.json").write_text(
        json.dumps({"messages": list(dispatch.messages), "enums": list(dispatch.enums)}))


def format_error(tag: str, payload: Mapping[str, Any]) -> str:
    """An `err` detail: the tag, then `;field=value` for each payload field present."""
    return tag + "".join(f";{name}={payload[name]}" for name in PAYLOAD_FIELDS if name in payload)


def parse_error(detail: str) -> tuple[str, dict[str, str]]:
    tag, *fields = detail.split(";")
    payload: dict[str, str] = {}
    for item in fields:
        name, _, value = item.partition("=")
        payload[name] = value
    return tag, payload


def expected_reencoding(row: Mapping[str, Any], expect: Mapping[str, Any] | None = None) -> str:
    """An accept expectation's re-encoding, as hex: its `reencode`, else the row's own
    bytes, expanded. `expect` is the row's `expect` unless given (`row_expect`)."""
    expect = row["expect"] if expect is None else expect
    if "reencode" in expect:
        return expect["reencode"]
    return row["bytes"] if isinstance(row["bytes"], str) else row_bytes(row).hex()


def _judge_resolved(row: Mapping[str, Any], resolved: str | None) -> tuple[str, str] | None:
    """A decode row's fourth column, the bounds its typed entry point resolved (the bounds
    protocol, item 4): a FAIL, or None when it is as the row requires. Only a from_cbor row
    has one; its form is checked; a row with `bounds` must report them."""
    if row["stage"] != "from_cbor":
        if resolved is None:
            return None
        return FAIL, f"a {row['stage']} row has no fourth column, got {resolved!r}"
    if resolved is not None and not _BOUNDS_COLUMN.fullmatch(resolved):
        return FAIL, f"resolved bounds {resolved!r}, not max_depth=<n>;max_encoded_len=<n or empty>"
    if "bounds" not in row:
        return None
    want = format_bounds(row["bounds"])
    if resolved is None:
        return FAIL, f"no resolved bounds reported, expected {want}"
    if resolved != want:
        return FAIL, f"resolved {resolved}, expected {want}"
    return None


def judge(target: str, row: Mapping[str, Any], outcome: str, detail: str, *,
          resolved: str | None = None) -> tuple[str, str]:
    """The comparator: (PASS or FAIL, why) for one malformed or bounds row's observation by
    `target`, a target or variant, judged by `row_expect(target, row)`. An accept
    expectation's `ok` must carry its re-encoding (D2's law). `resolved` is a from_cbor
    row's fourth column, None when absent: bounds resolved otherwise than the row's fail
    the row whatever its outcome, so a wrong resolution shows as such (OPT-P1)."""
    wrong = _judge_resolved(row, resolved)
    if wrong is not None:
        return wrong
    expect = row_expect(target, row)
    want = "accept" if expect.get("accept") else format_error(expect["tag"], expect)
    if outcome == OK:
        if want != "accept":
            return FAIL, f"decoded ok, expected {want}"
        reencoding = expected_reencoding(row, expect)
        if not detail:
            return FAIL, "no re-encoding reported"
        if detail != reencoding:
            return FAIL, f"re-encoded {detail}, expected {reencoding}"
        return PASS, ""
    if outcome == UNTYPED:
        return FAIL, f"untyped {detail}, expected {want}"
    if outcome != ERR:
        return FAIL, f"unknown outcome {outcome!r}, expected {want}"
    if want == "accept":
        return FAIL, f"got {detail}, expected accept"
    tag, payload = parse_error(detail)
    exempt = PAYLOAD_EXEMPT.get(split_variant(target)[0], frozenset())  # the target's runtime
    drift = [name for name in expect
             if name != "tag" and (tag, name) not in exempt and payload.get(name) != str(expect[name])]
    if tag != expect["tag"] or drift:
        return FAIL, f"got {detail}, expected {want}"
    return PASS, ""


def _row_index() -> dict[str, tuple[str, dict]]:
    """name -> (kind, row), int rows, malformed rows, then bounds rows, in corpus order."""
    index: dict[str, tuple[str, dict]] = {}
    for kind, row in [*((r["kind"], r) for r in int_rows()), *(("malformed", r) for r in malformed_rows()),
                      *(("bounds", r) for r in bounds_rows())]:
        if row["name"] in index:
            raise ParityValidationError(f"row name {row['name']!r} appears twice in the corpus")
        index[row["name"]] = (kind, row)
    return index


def _result(target: str, kind: str, row: Mapping[str, Any], status: str, detail: str) -> VectorResult:
    """One row's result for `target`, naming the expectation it was judged by."""
    expect = row_expect(target, row) if kind in DECODE_KINDS else row.get("expect", {})
    expected = "accept" if expect.get("accept") else expect.get("tag", "")
    return VectorResult(row["name"], kind, expected, status, detail, bool(row.get("lead")))


def _constants_fault(reported: list[str]) -> str:
    """The fault, if any, in the `#constants` lines a runner printed (the bounds protocol,
    item 1): exactly one, saying the bounds header's numbers."""
    want = expected_constants()
    if not reported:
        return f"{NO_CONSTANTS}\nexpected {CONSTANTS}<TAB>{want}, once, from the runtime's own constants"
    if len(reported) > 1:
        return f"{CONSTANTS} printed {len(reported)} times, expected once"
    if reported[0] != want:
        return f"{CONSTANTS} {reported[0]}, expected {want}"
    return ""


def _excerpt(text: str, limit: int = 800) -> str:
    """The start of a tool's output (where compilers and panics put the first error)."""
    text = (text or "").strip()
    if not text:
        return ""
    return "\n" + (text if len(text) <= limit else text[:limit] + " ...")


def parse_report(target: str, stdout: str, *, returncode: int = 0, stderr: str = "") -> TargetReport:
    """Judge a runner's report. Every row is reported exactly once, or it fails;
    a runner that exits non-zero, reports rows the corpus lacks, or does not print its
    `#constants` line once and as the bounds header says, fails its target."""
    rows = _row_index()
    judged: dict[str, VectorResult] = {}
    stray: list[str] = []
    constants: list[str] = []
    for line in stdout.splitlines():
        if "\t" not in line:
            continue
        name, _, rest = line.partition("\t")
        if name == CONSTANTS:
            constants.append(rest)
            continue
        outcome, _, rest = rest.partition("\t")
        detail, fourth, resolved = rest.partition("\t")
        if name not in rows:
            stray.append(name)
            continue
        kind, row = rows[name]
        if name in judged:
            judged[name] = _result(target, kind, row, FAIL, "reported more than once")
        elif kind in DECODE_KINDS:
            judged[name] = _result(target, kind, row, *judge(target, row, outcome, detail,
                                                             resolved=resolved if fourth else None))
        elif fourth:
            judged[name] = _result(target, kind, row, FAIL, f"an int row has no fourth column, got {resolved!r}")
        elif outcome in (PASS, FAIL, TYPE_SATISFIED):
            judged[name] = _result(target, kind, row, outcome, detail)
        else:
            judged[name] = _result(target, kind, row, FAIL, f"unknown outcome {outcome!r}")
    report = TargetReport(target, available=True)
    report.results = [judged.get(name) or _result(target, kind, row, FAIL, NO_REPORT)
                      for name, (kind, row) in rows.items()]
    faults = []
    if returncode != 0:
        faults.append(f"runner exited {returncode}{_excerpt(stderr)}")
    if stray:
        faults.append(f"runner reported rows the corpus lacks: {sorted(set(stray))}")
    constants_fault = _constants_fault(constants)
    if constants_fault:
        faults.append(constants_fault)
    report.fault = "\n".join(faults)
    return report


def skipped(target: str, reason: str) -> TargetReport:
    """A missing toolchain: the only way a target skips."""
    return TargetReport(target, available=False, skip_reason=reason)


def red(target: str, fault: str) -> TargetReport:
    """A target whose rows could not run (generation or build failed): RED, never a skip."""
    report = parse_report(target, "")
    report.fault = fault
    return report


def generate(name: str, out_dir: Path, **emit_options: Any) -> TargetReport | None:
    """Generate the fixture's code for `name`, a target or its `<target>/fc` variant
    (generated with `forward_compat=True`), into `out_dir/<target>`; None on success, else
    the RED report (a generator that refuses the fixture fails its variant)."""
    from ..gen import scaffold

    target, forward_compat = split_variant(name)
    try:
        scaffold.emit(parity_schema(), out_dir, langs=[target], services=[],
                      forward_compat=forward_compat, **emit_options)
    except Exception as exc:  # noqa: BLE001 — any generator failure makes the target RED
        return red(name, f"generation failed\n{type(exc).__name__}: {exc}")
    return None


def _decoded(output: str | bytes | None) -> str:
    if isinstance(output, bytes):
        return output.decode(errors="replace")
    return output or ""


def build(target: str, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None = None,
          timeout: float = BUILD_TIMEOUT) -> TargetReport | None:
    """Run one build step; None on success, else the RED report."""
    try:
        done = subprocess.run(list(argv), cwd=cwd, env=env, capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return red(target, f"build failed\n{exc}")
    if done.returncode != 0:
        return red(target, f"build failed (exit {done.returncode}){_excerpt(done.stderr or done.stdout)}")
    return None


def run_runner(target: str, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None = None,
               timeout: float = RUN_TIMEOUT) -> TargetReport:
    """Run a built runner and judge its report."""
    try:
        done = subprocess.run(list(argv), cwd=cwd, env=env, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        report = parse_report(target, _decoded(exc.stdout))
        report.fault = f"runner timed out after {timeout:g}s"
        return report
    except OSError as exc:
        return red(target, f"runner did not start\n{exc}")
    return parse_report(target, done.stdout, returncode=done.returncode, stderr=done.stderr)


# --- Python harness (in-process, no subprocess) -----------------------------------

def _observe_python(schema: Any, row: Mapping[str, Any]) -> tuple[str, str]:
    """One malformed or bounds row through wire.cbor/wire.codec: (outcome, detail) as a
    runner reports it, `ok` with the hex of the re-encoding (empty for a `from_wire` row).
    A raw row's call passes its `limits`; a from_cbor row decodes through the typed entry
    point from bytes, `codec.decode`, which applies the message's bounds."""
    from ..ir.model import EnumRef

    try:
        data = row_bytes(row)
        if row["stage"] == "raw_decode":
            again = cbor.dumps(cbor.loads(data, **row.get("limits", {})))
        elif row["stage"] == "from_cbor":
            again = codec.encode(schema, row["schema"], codec.decode(schema, row["schema"], data))
        else:  # from_wire: an enum, never an accept row
            codec._from_wire(schema, EnumRef(row["schema"]), cbor.loads(data), strict=True)
            again = b""
    except cbor.DecodeError as exc:
        return ERR, format_error(exc.tag, exc.payload)
    except Exception as exc:  # noqa: BLE001 — anything but DecodeError is untyped
        return UNTYPED, f"{type(exc).__name__}: {exc}"
    return OK, again.hex()


def _check_int_python(schema: Any, row: Mapping[str, Any]) -> tuple[str, str]:
    """An int row's (status, detail): a round trip through `codec`, or an encode that fails."""
    value = {"n": int(row["value"]["n"]),
             "by_id": {int(k): int(v) for k, v in row["value"]["by_id"]}}
    if row["kind"] == "round_trip":
        try:
            wire = codec.encode(schema, row["message"], value)
            if wire.hex() != row["cbor"]:
                return FAIL, f"encode {wire.hex()} != {row['cbor']}"
            if codec.decode(schema, row["message"], wire) != value:
                return FAIL, "decode mismatch"
            return PASS, ""
        except Exception as exc:  # noqa: BLE001 — fail-closed check
            return FAIL, f"raised {type(exc).__name__}: {exc}"
    tag = row["expect"]["tag"]  # encode_fail
    try:
        codec.encode(schema, row["message"], value)
    except codec.EncodeError as exc:
        return (PASS, "") if exc.tag == tag else (FAIL, f"tag {exc.tag} != {tag}")
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"raised {type(exc).__name__}"
    return FAIL, "encoded, expected IntOutOfSubset"


def _line(*columns: str) -> str:
    """A report line, as a runner prints one: tabs and line breaks inside a column are spaces."""
    return "\t".join(re.sub(r"[\t\r\n]+", " ", column) for column in columns)


def python_report() -> list[str]:
    """The Python codec's report, line by line, as a runner prints it: its constants, each
    int row checked here, and each decode row observed (`_observe_python`), a from_cbor
    row's with the bounds `codec.decode` resolves its message to."""
    schema = parity_schema()
    lines = [_line(CONSTANTS, format_constants(cbor.DEFAULT_MAX_DEPTH, cbor.MAX_DEPTH_CEILING))]
    for row in int_rows():
        lines.append(_line(row["name"], *_check_int_python(schema, row)))
    for row in decode_rows():
        outcome, detail = _observe_python(schema, row)
        if row["stage"] == "from_cbor":
            depth, length = codec.bounds(schema, MsgRef(row["schema"]))
            lines.append(_line(row["name"], outcome, detail,
                               format_bounds({"max_depth": depth, "max_encoded_len": length})))
        else:
            lines.append(_line(row["name"], outcome, detail))
    return lines


def run_python() -> TargetReport:
    """The python gate: its report parsed and judged as any runner's is."""
    return parse_report("python", "\n".join(python_report()))


# --- the registry -------------------------------------------------------------------

def _runner_module(target: str) -> str:
    return f"{__package__}.parity_{target}"


class _Runners(Mapping[str, Callable[[], TargetReport]]):
    """variant -> run(): `run_python` in-process, else `taut.corpus.parity_<target>.run`
    when that module exists, called with `forward_compat=True` for `<target>/fc`. A
    variant with neither has no runner and is not run."""

    def __contains__(self, name: object) -> bool:
        if name == "python":
            return True
        if not isinstance(name, str):
            return False
        target, forward_compat = split_variant(name)
        if target not in TARGETS or (forward_compat and target not in FC_TARGETS):
            return False
        return importlib.util.find_spec(_runner_module(target)) is not None

    def __getitem__(self, name: str) -> Callable[[], TargetReport]:
        if name not in self:
            raise KeyError(name)
        if name == "python":
            return run_python
        target, forward_compat = split_variant(name)
        run = importlib.import_module(_runner_module(target)).run
        if forward_compat:
            return functools.partial(run, forward_compat=True)
        return run

    def __iter__(self) -> Iterator[str]:
        return (name for name in variants() if name in self)

    def __len__(self) -> int:
        return sum(1 for _ in self)


_RUNNERS: Mapping[str, Callable[[], TargetReport]] = _Runners()


def run_targets(targets: Iterable[str], *, jobs: int | None = None) -> dict[str, TargetReport]:
    """Run each target or variant that has a runner, up to `jobs` at once (default: one per
    CPU): each builds in its own temporary directory, so they run side by side. One without a
    runner is left out, a runner that raises is RED rather than stopping the others, and the
    reports keep `targets`' order."""
    names = [target for target in targets if target in _RUNNERS]

    def run(target: str) -> TargetReport:
        try:
            return _RUNNERS[target]()
        except Exception as exc:  # noqa: BLE001 — one broken runner must not hide the others
            return red(target, f"runner raised\n{type(exc).__name__}: {exc}")

    workers = max(1, min(len(names), jobs or os.cpu_count() or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(zip(names, pool.map(run, names)))


# --- governance + summary -----------------------------------------------------

def _verdict(rep: TargetReport) -> str:
    if rep.green:
        return "GREEN"
    return "RED " + (rep.fault.splitlines()[0] if rep.fault else ",".join(rep.failed_tags))


def governance(reports: dict[str, TargetReport], allow: set[str]) -> list[str]:
    """Return governance violations. Empty == clean gate."""
    violations: list[str] = []
    for target, rep in reports.items():
        if not rep.available:
            continue  # skip-with-reason: not evaluated, neither pass nor fail
        if rep.green and target in allow:
            violations.append(f"{target}: PASSES fully but is allowlisted — remove it from allowlist.json")
        if not rep.green and target not in allow:
            violations.append(f"{target}: {_verdict(rep)} and is not allowlisted")
    return violations


def unrun(wanted: Iterable[str], reports: dict[str, TargetReport]) -> list[str]:
    """A violation for each variant in `wanted` that did not run: skipped for a missing
    toolchain, or without a runner. A release requires every one (`tautc parity
    --require-all`); otherwise a skip is reported and does not fail the gate."""
    violations: list[str] = []
    for name in wanted:
        rep = reports.get(name)
        if rep is None:
            violations.append(f"{name}: has no runner, but every target must run")
        elif not rep.available:
            violations.append(f"{name}: skipped ({rep.skip_reason}), but every target must run")
    return violations


def governed_variants(run: Callable[..., TargetReport],
                      path: Path = ALLOWLIST) -> tuple[list[TargetReport], list[str]]:
    """A generated target's own test, held to what the gate holds it to: `run`, its runner's
    `run`, as the target and as its `<target>/fc`, and the violations `governance` finds
    for each against the allowlist, with the fault and failing rows behind each. None means
    each report is GREEN, or RED and allowlisted, or skipped (which the test reports)."""
    reports = [run(), run(forward_compat=True)]
    allow = allowlisted_targets(path)
    violations: list[str] = []
    for report in reports:
        for violation in governance({report.target: report}, allow):
            rows = [f"{r.name}: {r.detail}" for r in report.failures
                    if not (report.fault and r.detail == NO_REPORT)]
            violations.append("\n".join(line for line in (violation, report.fault, *rows) if line))
    return reports, violations


def _summary(reports: dict[str, TargetReport], statuses: list[ParityStatus],
             int_count: int, mal_count: int, bounds_count: int) -> list[str]:
    lines = [
        f"int vectors: {int_count}    malformed vectors: {mal_count}    bounds vectors: {bounds_count}",
        "",
        f"{'target':<11} {'status':<12} {'pass':>4} {'fail':>4} {'skip/type':>9}  observed",
    ]
    status_by = {s.target: s for s in statuses}
    for target in variants():  # each variant on its own line
        st = status_by[target]
        rep = reports.get(target)
        if rep is None:
            lines.append(f"{target:<11} {st.status:<12} {'-':>4} {'-':>4} {'not run':>9}  {st.reason}")
            continue
        if not rep.available:
            lines.append(f"{target:<11} {st.status:<12} {'-':>4} {'-':>4} {'skipped':>9}  {rep.skip_reason}")
            continue
        npass = sum(1 for r in rep.results if r.status == PASS)
        nfail = len(rep.failures)
        ntype = sum(1 for r in rep.results if r.status == TYPE_SATISFIED)
        lines.append(f"{target:<11} {st.status:<12} {npass:>4} {nfail:>4} {ntype:>9}  {_verdict(rep)}")
    # per-vector detail for any red target
    for target, rep in reports.items():
        if not rep.available or rep.green:
            continue
        lines.append("")
        lines.append(f"{target} failures:")
        lines += [f"  ! {line}" for line in rep.fault.splitlines()]
        unreported = [r.name for r in rep.failures if r.detail == NO_REPORT]
        for r in rep.failures:
            if r.detail != NO_REPORT:
                mark = " (lead)" if r.lead else ""
                lines.append(f"  - {r.name}{mark}: {r.detail}")
        if unreported and len(unreported) == len(rep.results):
            lines.append(f"  - no row reported ({len(unreported)} rows)")
        elif unreported:
            lines.append(f"  - {len(unreported)} row(s) never reported: {', '.join(unreported)}")
    return lines


@dataclass
class GateOutcome:
    lines: list[str]
    violations: list[str]
    reports: dict[str, TargetReport]


def _selected(target: str) -> tuple[str, ...]:
    """The variants `target` selects: a target's own and its `<target>/fc`, or a variant
    alone. An unknown name is refused."""
    known = variants()
    if target not in known:
        raise ParityValidationError(f"unknown target {target!r}; known: {', '.join(known)}")
    if split_variant(target)[1]:
        return (target,)
    return tuple(name for name in known if split_variant(name)[0] == target)


def run_gate(*, target: str | None = None, run_compiled: bool = True,
             require_all: bool = False, jobs: int | None = None) -> GateOutcome:
    """Validate the artifacts, run the runners and judge governance. By default every
    variant that has a runner; `target` runs a target's variants or one variant, and
    `run_compiled=False` runs Python only. `require_all` also fails the gate for each
    selected variant that did not run (`unrun`), as a release requires. `jobs` bounds how many
    runners run at once (`run_targets`)."""
    if target is not None:
        wanted = _selected(target)
    elif run_compiled:
        wanted = variants()
    else:
        wanted = ("python",)
    int_count = validate_int_vectors()
    mal_count = validate_malformed_vectors()
    bounds_count = validate_bounds_vectors()
    statuses = target_statuses()
    allow = {s.target for s in statuses if s.status == "allowlisted"}
    reports = run_targets(wanted, jobs=jobs)

    violations = governance(reports, allow)
    if require_all:
        violations += unrun(wanted, reports)
    lines = _summary(reports, statuses, int_count, mal_count, bounds_count)
    if violations:
        lines.append("")
        lines.append("GOVERNANCE VIOLATIONS (gate fails):")
        lines += [f"  - {v}" for v in violations]
    else:
        lines.append("")
        ran = "; every selected target ran" if require_all else ""
        lines.append(f"governance: clean (no gated target failing, no green target allowlisted{ran})")
    return GateOutcome(lines, violations, reports)


# --- back-compat: validate-only view (used by artifact tests) -----------------

def validate_all(*, target: str | None = None) -> list[str]:
    selected = _selected(target) if target is not None else variants()
    int_count = validate_int_vectors()
    malformed_count = validate_malformed_vectors()
    bounds_count = validate_bounds_vectors()
    statuses = [s for s in target_statuses() if s.target in selected]
    lines = [f"int vectors: {int_count}", f"malformed vectors: {malformed_count}",
             f"bounds vectors: {bounds_count}"]
    for status in statuses:
        lines.append(f"{status.target}: {status.status} - {status.reason}")
    return lines
