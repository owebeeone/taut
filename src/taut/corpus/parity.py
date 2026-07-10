"""Shared codec-parity gate — the leading cross-language conformance corpus.

Phase 0 of `dev-docs/TautCodecParityPlan.md`. Two language-neutral vector files
(`corpus/parity/{int,malformed}.vectors.json`, produced by `gen_vectors.py`) are
replayed through **every Wave-1 codec** (rust, python, typescript, js) by the
governed harnesses below. A target is **gated** (must pass) unless it appears in
`allowlist.json`, in which case it is **allowlisted**: its harness still RUNS and
REPORTS observed failures (xfail-that-runs), it just doesn't fail CI. Governance
is the inverse check too — CI fails if an *allowlisted* target passes fully (a
green target must be de-listed) or a *gated* target fails.

This corpus **SUPPLEMENTS** `tautc corpus` / the message golden corpora; it never
replaces them. Entry point: `tautc parity`.

`lead` rows (see `gen_vectors.py`) are replayed by this gate but skipped by the
per-language *baseline* smoke tests in `src/tests/test_{rust,ts,js,go,...}.py`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..ir.load import load_schema
from ..wire import cbor, codec

ROOT = Path(__file__).resolve().parents[3]
PARITY_DIR = ROOT / "corpus" / "parity"
INT_VECTORS = PARITY_DIR / "int.vectors.json"
MALFORMED_VECTORS = PARITY_DIR / "malformed.vectors.json"
ALLOWLIST = PARITY_DIR / "allowlist.json"

INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1

TARGETS = ("rust", "python", "typescript", "js", "cpp", "swift", "go", "kotlin", "java")
WAVE1 = ("rust", "python", "typescript", "js")
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


def _parity_schema() -> Any:
    data = _load_json(INT_VECTORS)
    return load_schema(ROOT / data["schema_path"])


def validate_int_vectors(path: Path = INT_VECTORS) -> int:
    data = _load_json(path)
    if data.get("version") != 1:
        raise ParityValidationError(f"{path}: unsupported version {data.get('version')!r}")
    schema = load_schema(ROOT / data["schema_path"])
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
    schema = load_schema(ROOT / data["schema_path"])
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


def allowlisted_targets(path: Path = ALLOWLIST) -> set[str]:
    return {s.target for s in target_statuses(path) if s.status == "allowlisted"}


# --- replay-harness reports ---------------------------------------------------

PASS, FAIL, TYPE_SATISFIED = "pass", "fail", "type-satisfied"


@dataclass(frozen=True)
class VectorResult:
    name: str
    kind: str          # "round_trip" | "encode_fail" | "malformed"
    expected_tag: str  # tag name, or "" for round_trip
    status: str        # PASS | FAIL | TYPE_SATISFIED
    detail: str
    lead: bool


@dataclass
class TargetReport:
    target: str
    available: bool
    skip_reason: str = ""
    results: list[VectorResult] = field(default_factory=list)

    @property
    def failures(self) -> list[VectorResult]:
        return [r for r in self.results if r.status == FAIL]

    @property
    def green(self) -> bool:
        return self.available and not self.failures

    @property
    def failed_tags(self) -> list[str]:
        return sorted({(r.expected_tag or r.name) for r in self.failures})


def _int_rows() -> list[dict]:
    return _load_json(INT_VECTORS)["vectors"]


def _malformed_rows() -> list[dict]:
    return _load_json(MALFORMED_VECTORS)["vectors"]


# --- Python harness (direct, no subprocess) -----------------------------------

def run_python() -> TargetReport:
    from ..ir.model import EnumRef

    schema = _parity_schema()
    report = TargetReport("python", available=True)

    for row in _int_rows():
        lead = bool(row.get("lead"))
        value = {"n": int(row["value"]["n"]),
                 "by_id": {int(k): int(v) for k, v in row["value"]["by_id"]}}
        if row["kind"] == "round_trip":
            try:
                wire = codec.encode(schema, row["message"], value)
                if wire.hex() != row["cbor"]:
                    status, detail = FAIL, f"encode {wire.hex()} != {row['cbor']}"
                elif codec.decode(schema, row["message"], wire) != value:
                    status, detail = FAIL, "decode mismatch"
                else:
                    status, detail = PASS, ""
            except Exception as exc:  # noqa: BLE001 — fail-closed check
                status, detail = FAIL, f"raised {type(exc).__name__}: {exc}"
            report.results.append(VectorResult(row["name"], "round_trip", "", status, detail, lead))
        else:  # encode_fail
            tag = row["expect"]["tag"]
            try:
                codec.encode(schema, row["message"], value)
                status, detail = FAIL, "encoded, expected IntOutOfSubset"
            except codec.EncodeError as exc:
                status, detail = (PASS, "") if exc.tag == tag else (FAIL, f"tag {exc.tag} != {tag}")
            except Exception as exc:  # noqa: BLE001
                status, detail = FAIL, f"raised {type(exc).__name__}"
            report.results.append(VectorResult(row["name"], "encode_fail", tag, status, detail, lead))

    for row in _malformed_rows():
        lead = bool(row.get("lead"))
        tag = row["expect"]["tag"]
        data = bytes.fromhex(row["bytes"])
        try:
            if row["stage"] == "raw_decode":
                cbor.loads(data)
            elif row["stage"] == "from_cbor":
                codec.decode(schema, row["schema"], data)
            else:  # from_wire
                codec._from_wire(schema, EnumRef(row["schema"]), cbor.loads(data), strict=True)
            status, detail = FAIL, f"decoded ok, expected {tag}"
        except cbor.DecodeError as exc:
            status, detail = (PASS, "") if exc.tag == tag else (FAIL, f"tag {exc.tag} != {tag}")
        except Exception as exc:  # noqa: BLE001 — untyped leak is a fail-closed miss
            status, detail = FAIL, f"untyped {type(exc).__name__}: {exc}"
        report.results.append(VectorResult(row["name"], "malformed", tag, status, detail, lead))

    return report


# --- Rust harness (rustc-driven) ----------------------------------------------

def _rs(value: Any) -> str:
    return json.dumps(value)


def _opt_rs(value: Any) -> str:
    return "None" if value is None else f"Some({_rs(str(value))})"


def _opt_u8(value: Any) -> str:
    return "None" if value is None else f"Some({int(value)}u8)"


_RUST_MAIN = r'''
#![allow(warnings)]
extern crate alloc;
#[path = "@CBOR@"]
mod cbor;
#[path = "@API@"]
mod api;

use api::{IntBox, Mode};
use cbor::{encode, try_decode, DecodeError};
use std::collections::BTreeMap;

struct IntRow { name: &'static str, cbor: &'static str, n: &'static str, by_id: &'static [(&'static str, &'static str)] }
struct EncFail { name: &'static str, value: &'static str }
struct Mal { name: &'static str, stage: &'static str, schema: Option<&'static str>, bytes: &'static str,
             tag: &'static str, key: Option<&'static str>, expected: Option<&'static str>,
             enum_name: Option<&'static str>, value: Option<&'static str>, info: Option<u8>, major: Option<u8> }

static ROUND_TRIP: &[IntRow] = &[
@ROUND_TRIP@
];
static ENCODE_FAIL: &[EncFail] = &[
@ENCODE_FAIL@
];
static MALFORMED: &[Mal] = &[
@MALFORMED@
];

fn unhex(s: &str) -> Vec<u8> { (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i+2], 16).unwrap()).collect() }
fn hexof(b: &[u8]) -> String { use std::fmt::Write as _; b.iter().fold(String::new(), |mut s, x| { let _ = write!(s, "{x:02x}"); s }) }
fn pi(s: &str) -> i64 { s.parse::<i64>().unwrap() }

fn tag_name(e: &DecodeError) -> &'static str {
    match e {
        DecodeError::Truncated => "Truncated",
        DecodeError::TrailingBytes => "TrailingBytes",
        DecodeError::InvalidUtf8 => "InvalidUtf8",
        DecodeError::UnsupportedInfo(_) => "UnsupportedInfo",
        DecodeError::UnsupportedMajor(_) => "UnsupportedMajor",
        DecodeError::NonIntegerMapKey => "NonIntegerMapKey",
        DecodeError::DuplicateMapKey(_) => "DuplicateMapKey",
        DecodeError::IntOverflow => "IntOverflow",
        DecodeError::NonCanonicalInt(_) => "NonCanonicalInt",
        DecodeError::NegativeMapKey(_) => "NegativeMapKey",
        DecodeError::MissingKey(_) => "MissingKey",
        DecodeError::WrongType { .. } => "WrongType",
        DecodeError::UnknownEnum { .. } => "UnknownEnum",
    }
}

fn emit(name: &str, status: &str, detail: &str) { println!("{name}\t{status}\t{detail}"); }

fn main() {
    for row in ROUND_TRIP {
        let by_id: BTreeMap<i64, i64> = row.by_id.iter().map(|(k, v)| (pi(k), pi(v))).collect();
        let built = IntBox { n: pi(row.n), by_id: by_id.clone() };
        let enc = hexof(&encode(&built.to_cbor()));
        if enc != row.cbor { emit(row.name, "fail", &format!("encode {} != {}", enc, row.cbor)); continue; }
        match try_decode(&unhex(row.cbor)) {
            Err(e) => emit(row.name, "fail", &format!("raw decode {:?}", e)),
            Ok(c) => match IntBox::from_cbor(&c) {
                Err(e) => emit(row.name, "fail", &format!("from_cbor {:?}", e)),
                Ok(d) => {
                    let re = hexof(&encode(&d.to_cbor()));
                    if d.n == pi(row.n) && d.by_id == by_id && re == row.cbor { emit(row.name, "pass", ""); }
                    else { emit(row.name, "fail", &format!("reencode {}", re)); }
                }
            }
        }
    }
    for row in ENCODE_FAIL {
        // i64 is the encode-side subset guard: an out-of-subset value is
        // unrepresentable, so this is satisfied by the type system.
        if row.value.parse::<i64>().is_err() { emit(row.name, "type-satisfied", "unrepresentable in i64"); }
        else { emit(row.name, "fail", "value fits i64 but expected out-of-subset"); }
    }
    for row in MALFORMED {
        let observed: Result<(), DecodeError> = match row.stage {
            "raw_decode" => try_decode(&unhex(row.bytes)).map(|_| ()),
            "from_cbor" => match try_decode(&unhex(row.bytes)) {
                Err(e) => Err(e),
                Ok(c) => match row.schema { Some("IntBox") => IntBox::from_cbor(&c).map(|_| ()), _ => { emit(row.name, "fail", "unknown from_cbor schema"); continue; } },
            },
            "from_wire" => match try_decode(&unhex(row.bytes)) {
                Err(e) => Err(e),
                Ok(c) => match c.try_int() {
                    Err(e) => Err(e),
                    Ok(v) => match row.schema { Some("Mode") => Mode::from_wire(v).map(|_| ()), _ => { emit(row.name, "fail", "unknown from_wire schema"); continue; } },
                },
            },
            _ => { emit(row.name, "fail", "unknown stage"); continue; }
        };
        match observed {
            Ok(()) => emit(row.name, "fail", &format!("decoded ok, expected {}", row.tag)),
            Err(e) => { let got = tag_name(&e); if got == row.tag { emit(row.name, "pass", ""); } else { emit(row.name, "fail", &format!("got {} expected {}", got, row.tag)); } }
        }
    }
}
'''


def _rust_tables() -> tuple[str, str, str]:
    rt, ef, mal = [], [], []
    for row in _int_rows():
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"({_rs(k)}, {_rs(v)})" for k, v in row["value"]["by_id"])
            rt.append(f'    IntRow {{ name: {_rs(row["name"])}, cbor: {_rs(row["cbor"])}, '
                      f'n: {_rs(row["value"]["n"])}, by_id: &[{pairs}] }}')
        else:
            ef.append(f'    EncFail {{ name: {_rs(row["name"])}, value: {_rs(row["value"]["n"])} }}')
    for row in _malformed_rows():
        e = row["expect"]
        mal.append(
            f'    Mal {{ name: {_rs(row["name"])}, stage: {_rs(row["stage"])}, '
            f'schema: {_opt_rs(row.get("schema"))}, bytes: {_rs(row["bytes"])}, tag: {_rs(e["tag"])}, '
            f'key: {_opt_rs(e.get("key"))}, expected: {_opt_rs(e.get("expected"))}, '
            f'enum_name: {_opt_rs(e.get("enum"))}, value: {_opt_rs(e.get("value"))}, '
            f'info: {_opt_u8(e.get("info"))}, major: {_opt_u8(e.get("major"))} }}')
    return ",\n".join(rt), ",\n".join(ef), ",\n".join(mal)


def _tag_by_name() -> dict[str, tuple[str, str, bool]]:
    """name -> (kind, expected_tag, lead) for stamping subprocess results."""
    out: dict[str, tuple[str, str, bool]] = {}
    for row in _int_rows():
        tag = row.get("expect", {}).get("tag", "")
        out[row["name"]] = (row["kind"], tag, bool(row.get("lead")))
    for row in _malformed_rows():
        out[row["name"]] = ("malformed", row["expect"]["tag"], bool(row.get("lead")))
    return out


def _parse_report(target: str, stdout: str) -> TargetReport:
    meta = _tag_by_name()
    report = TargetReport(target, available=True)
    for line in stdout.splitlines():
        if "\t" not in line:
            continue
        parts = line.split("\t")
        name, status = parts[0], parts[1]
        detail = parts[2] if len(parts) > 2 else ""
        if name not in meta:
            continue
        kind, tag, lead = meta[name]
        report.results.append(VectorResult(name, kind, tag, status, detail, lead))
    return report


def run_rust() -> TargetReport:
    rustc = shutil.which("rustc")
    if rustc is None:
        return TargetReport("rust", available=False, skip_reason="rustc not on PATH")
    from ..gen import scaffold

    schema = _parity_schema()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        scaffold.emit(schema, tmp, langs=["rust"], services=[], runtime=True, fail_closed=True)
        rust_dir = tmp / "rust"
        rt, ef, mal = _rust_tables()
        src = (_RUST_MAIN
               .replace("@CBOR@", (rust_dir / "cbor.rs").as_posix())
               .replace("@API@", (rust_dir / "api.rs").as_posix())
               .replace("@ROUND_TRIP@", rt).replace("@ENCODE_FAIL@", ef).replace("@MALFORMED@", mal))
        runner = tmp / "parity_runner.rs"
        runner.write_text(src)
        binary = tmp / "parity_runner"
        build = subprocess.run([rustc, "--edition", "2021", str(runner), "-o", str(binary)],
                               capture_output=True, text=True)
        if build.returncode != 0:
            return TargetReport("rust", available=False, skip_reason=f"rustc build failed: {build.stderr[-400:]}")
        run = subprocess.run([str(binary)], capture_output=True, text=True)
        return _parse_report("rust", run.stdout)


# --- TypeScript + JS harnesses (node) -----------------------------------------

_TS_RUNNER = r'''
import { readFileSync } from "node:fs";
import { decode as cborDecode } from "./cbor.ts";
import { decode, decodeRef, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("parity_int.ir.json", "utf8")));
const intVectors = JSON.parse(readFileSync("int.vectors.json", "utf8")).vectors;
const malformed = JSON.parse(readFileSync("malformed.vectors.json", "utf8")).vectors;

function hexToBytes(hex: string): Uint8Array { return Uint8Array.from(Buffer.from(hex, "hex")); }
function bytesToHex(b: Uint8Array): string { return Buffer.from(b).toString("hex"); }
function intBox(v: any) { return { n: BigInt(v.n), by_id: new Map(v.by_id.map(([k, x]: [string, string]) => [BigInt(k), BigInt(x)])) }; }
function emit(name: string, status: string, detail: string) { console.log(`${name}\t${status}\t${detail}`); }

for (const row of intVectors) {
  const native = intBox(row.value);
  if (row.kind === "round_trip") {
    try {
      const enc = bytesToHex(encode(schema, row.message, native));
      if (enc !== row.cbor) { emit(row.name, "fail", `encode ${enc}`); continue; }
      const dec: any = decode(schema, row.message, hexToBytes(row.cbor));
      const ok = dec.n === native.n && bytesToHex(encode(schema, row.message, dec)) === row.cbor;
      emit(row.name, ok ? "pass" : "fail", ok ? "" : "roundtrip mismatch");
    } catch (e: any) { emit(row.name, "fail", `threw ${e && e.tag ? e.tag : e}`); }
  } else {
    try { encode(schema, row.message, native); emit(row.name, "fail", "encoded, expected IntOutOfSubset"); }
    catch (e: any) { emit(row.name, e && e.tag === row.expect.tag ? "pass" : "fail", e && e.tag ? e.tag : String(e)); }
  }
}
for (const row of malformed) {
  const tag = row.expect.tag;
  try {
    const data = hexToBytes(row.bytes);
    if (row.stage === "raw_decode") cborDecode(data);
    else if (row.stage === "from_cbor") decode(schema, row.schema, data);
    else decodeRef(schema, { k: "enum", name: row.schema }, data);
    emit(row.name, "fail", `decoded ok, expected ${tag}`);
  } catch (e: any) { emit(row.name, e && e.tag === tag ? "pass" : "fail", e && e.tag ? e.tag : `untyped ${e}`); }
}
'''

_JS_RUNNER = r'''
"use strict";
const { IntBox, ModeFromCbor } = require("./api.js");
const { DecodeError, EncodeError, decode, encode } = require("./cbor.js");
const intVectors = require("./int.vectors.json").vectors;
const malformed = require("./malformed.vectors.json").vectors;

function bytesFromHex(hex) { const o = new Uint8Array(hex.length / 2); for (let i = 0; i < o.length; i++) o[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16); return o; }
function hexFromBytes(b) { return Array.from(b, (x) => x.toString(16).padStart(2, "0")).join(""); }
function box(row) { return new IntBox({ n: BigInt(row.value.n), by_id: new Map(row.value.by_id.map(([k, v]) => [BigInt(k), BigInt(v)])) }); }
function emit(name, status, detail) { console.log(`${name}\t${status}\t${detail}`); }

for (const row of intVectors) {
  if (row.kind === "round_trip") {
    try {
      const enc = hexFromBytes(encode(box(row).toCbor()));
      if (enc !== row.cbor) { emit(row.name, "fail", `encode ${enc}`); continue; }
      const dec = IntBox.fromCbor(decode(bytesFromHex(row.cbor)));
      const ok = typeof dec.n === "bigint" && dec.n === BigInt(row.value.n) && hexFromBytes(encode(dec.toCbor())) === row.cbor;
      emit(row.name, ok ? "pass" : "fail", ok ? "" : "roundtrip mismatch");
    } catch (e) { emit(row.name, "fail", `threw ${e && e.tag ? e.tag : e}`); }
  } else {
    try { encode(box(row).toCbor()); emit(row.name, "fail", "encoded, expected IntOutOfSubset"); }
    catch (e) { emit(row.name, e && e.tag === row.expect.tag ? "pass" : "fail", e && e.tag ? e.tag : String(e)); }
  }
}
for (const row of malformed) {
  const tag = row.expect.tag;
  try {
    const data = bytesFromHex(row.bytes);
    if (row.stage === "raw_decode") decode(data);
    else if (row.stage === "from_cbor") IntBox.fromCbor(decode(data));
    else ModeFromCbor(decode(data));
    emit(row.name, "fail", `decoded ok, expected ${tag}`);
  } catch (e) { emit(row.name, e && e.tag === tag ? "pass" : "fail", e && e.tag ? e.tag : `untyped ${e}`); }
}
'''


def run_ts() -> TargetReport:
    node = shutil.which("node")
    if node is None:
        return TargetReport("typescript", available=False, skip_reason="node not on PATH")
    from ..gen import scaffold
    from ..ir.export import export_to

    schema = _parity_schema()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        scaffold.emit(schema, tmp, langs=["typescript"], services=[], runtime=True)
        ts_dir = tmp / "typescript"
        export_to(schema, ts_dir / "parity_int.ir.json")
        (ts_dir / "int.vectors.json").write_text(INT_VECTORS.read_text())
        (ts_dir / "malformed.vectors.json").write_text(MALFORMED_VECTORS.read_text())
        (ts_dir / "runner.ts").write_text(_TS_RUNNER)
        run = subprocess.run([node, "--experimental-strip-types", "runner.ts"],
                             cwd=ts_dir, capture_output=True, text=True)
        if run.returncode != 0 and not run.stdout.strip():
            return TargetReport("typescript", available=False, skip_reason=f"node failed: {run.stderr[-400:]}")
        return _parse_report("typescript", run.stdout)


def run_js() -> TargetReport:
    node = shutil.which("node")
    if node is None:
        return TargetReport("js", available=False, skip_reason="node not on PATH")
    from ..gen import scaffold

    schema = _parity_schema()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        scaffold.emit(schema, tmp, langs=["js"], services=[], runtime=True)
        js_dir = tmp / "js"
        (js_dir / "int.vectors.json").write_text(INT_VECTORS.read_text())
        (js_dir / "malformed.vectors.json").write_text(MALFORMED_VECTORS.read_text())
        (js_dir / "runner.js").write_text(_JS_RUNNER)
        run = subprocess.run([node, "runner.js"], cwd=js_dir, capture_output=True, text=True)
        if run.returncode != 0 and not run.stdout.strip():
            return TargetReport("js", available=False, skip_reason=f"node failed: {run.stderr[-400:]}")
        return _parse_report("js", run.stdout)


_RUNNERS = {"python": run_python, "rust": run_rust, "typescript": run_ts, "js": run_js}


def run_wave1(targets: tuple[str, ...] = WAVE1) -> dict[str, TargetReport]:
    return {t: _RUNNERS[t]() for t in targets if t in _RUNNERS}


# --- governance + summary -----------------------------------------------------

def governance(reports: dict[str, TargetReport], allow: set[str]) -> list[str]:
    """Return governance violations. Empty == clean gate."""
    violations: list[str] = []
    for target, rep in reports.items():
        if not rep.available:
            continue  # skip-with-reason: not evaluated, neither pass nor fail
        if rep.green and target in allow:
            violations.append(f"{target}: PASSES fully but is allowlisted — remove it from allowlist.json")
        if not rep.green and target not in allow:
            violations.append(f"{target}: FAILS {rep.failed_tags} and is not allowlisted")
    return violations


def _summary(reports: dict[str, TargetReport], statuses: list[ParityStatus],
             int_count: int, mal_count: int) -> list[str]:
    lines = [
        f"int vectors: {int_count}    malformed vectors: {mal_count}",
        "",
        f"{'target':<11} {'status':<12} {'pass':>4} {'fail':>4} {'skip/type':>9}  observed",
    ]
    status_by = {s.target: s for s in statuses}
    for target in TARGETS:
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
        verdict = "GREEN" if rep.green else "RED " + ",".join(rep.failed_tags)
        lines.append(f"{target:<11} {st.status:<12} {npass:>4} {nfail:>4} {ntype:>9}  {verdict}")
    # per-vector detail for any red target
    for target, rep in reports.items():
        if rep.available and rep.failures:
            lines.append("")
            lines.append(f"{target} failing vectors:")
            for r in rep.failures:
                mark = " (lead)" if r.lead else ""
                lines.append(f"  - {r.name}{mark}: expected {r.expected_tag or 'round-trip'} — {r.detail}")
    return lines


@dataclass
class GateOutcome:
    lines: list[str]
    violations: list[str]
    reports: dict[str, TargetReport]


def run_gate(*, target: str | None = None, run_compiled: bool = True) -> GateOutcome:
    if target is not None and target not in TARGETS:
        raise ParityValidationError(f"unknown target {target!r}; known: {', '.join(TARGETS)}")
    int_count = validate_int_vectors()
    mal_count = validate_malformed_vectors()
    statuses = target_statuses()
    allow = {s.target for s in statuses if s.status == "allowlisted"}

    wanted = (target,) if target else (WAVE1 if run_compiled else ("python",))
    wanted = tuple(t for t in wanted if t in _RUNNERS)
    reports = run_wave1(wanted)

    violations = governance(reports, allow)
    lines = _summary(reports, statuses, int_count, mal_count)
    if violations:
        lines.append("")
        lines.append("GOVERNANCE VIOLATIONS (gate fails):")
        lines += [f"  - {v}" for v in violations]
    else:
        lines.append("")
        lines.append("governance: clean (no gated target failing, no green target allowlisted)")
    return GateOutcome(lines, violations, reports)


# --- back-compat: validate-only view (used by artifact tests) -----------------

def validate_all(*, target: str | None = None) -> list[str]:
    if target is not None and target not in TARGETS:
        raise ParityValidationError(f"unknown target {target!r}; known: {', '.join(TARGETS)}")
    int_count = validate_int_vectors()
    malformed_count = validate_malformed_vectors()
    statuses = [s for s in target_statuses() if target is None or s.target == target]
    lines = [f"int vectors: {int_count}", f"malformed vectors: {malformed_count}"]
    for status in statuses:
        lines.append(f"{status.target}: {status.status} - {status.reason}")
    return lines
