"""Rust runner for the parity gate — the model a compiled runner copies.

The gate finds a target's runner by module name, `taut.corpus.parity_<target>`,
and calls its `run(forward_compat: bool = False) -> TargetReport` (see
`parity._RUNNERS`): once as the target, and once with `forward_compat=True` as its
`<target>/fc` variant, whose name the report carries (`parity.variant`). The steps:

  1. find the toolchain (`toolchains`); a missing one is the only skip;
  2. generate the fixture's code (`parity.generate`, which generates the `/fc` variant
     with forward_compat); a refusal is RED;
  3. write a runner whose row tables come from `parity.int_rows()` and
     `parity.decode_rows()` (the malformed rows, then the bounds rows) and whose
     dispatch comes from `parity.fixture_dispatch()`, never from hard-coded message
     names;
  4. build it (`parity.build`); a failure is RED;
  5. run it (`parity.run_runner`), which parses and judges its report.

The runner prints `name<TAB>outcome<TAB>detail` per row. It checks int rows
itself; for a malformed or bounds row it only reports what happened (`ok` with the
hex of the re-encoding; `err` with the tag and payload; `untyped` for a panic) and
the gate judges it. It speaks the bounds protocol (`parity`'s docstring): it prints
the `#constants` line from the runtime's `DEFAULT_MAX_DEPTH` and `MAX_DEPTH_CEILING`;
a raw row with `limits` calls `try_decode_with` with them; a from_cbor row decodes
through its message's typed entry point, `X::decode`, and its line adds the bounds
that entry point applies, `X::MAX_DEPTH` and `X::MAX_ENCODED_LEN`; and it expands a
row's segments itself, reporting an expansion that is not the row's `len` as
`untyped`.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import parity, toolchains

TARGET = "rust"

_MAIN = r'''
#![allow(warnings)]
extern crate alloc;
#[path = "@CBOR@"]
mod cbor;
#[path = "@API@"]
mod api;

use cbor::{encode, try_decode, try_decode_with, Cbor, DecodeError};
use std::collections::BTreeMap;

struct IntRow { name: &'static str, cbor: &'static str, n: &'static str, by_id: &'static [(&'static str, &'static str)] }
struct EncFail { name: &'static str, value: &'static str }
/// A malformed or bounds row: its bytes as `(hex, count)` segments, which `expand`
/// joins; `len`, the expanded length it states, if any; and what a raw row's call
/// passes, its `limits`.
struct Row {
    name: &'static str,
    stage: &'static str,
    schema: &'static str,
    segments: &'static [(&'static str, usize)],
    len: Option<usize>,
    max_depth: Option<usize>,
    max_encoded_len: Option<usize>,
}

static ROUND_TRIP: &[IntRow] = &[
@ROUND_TRIP@
];
static ENCODE_FAIL: &[EncFail] = &[
@ENCODE_FAIL@
];
static DECODE_ROWS: &[Row] = &[
@DECODE_ROWS@
];

fn unhex(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect()
}

fn hexof(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

fn pi(s: &str) -> i64 {
    s.parse::<i64>().unwrap()
}

/// One report line; a from_cbor row's adds `resolved`, the bounds its entry point applied.
fn emit(name: &str, outcome: &str, detail: &str, resolved: Option<&str>) {
    let detail = detail.replace(&['\t', '\n', '\r'][..], " ");
    match resolved {
        Some(bounds) => println!("{name}\t{outcome}\t{detail}\t{bounds}"),
        None => println!("{name}\t{outcome}\t{detail}"),
    }
}

/// A row's input: each segment's bytes, `count` times, in order.
fn expand(row: &Row) -> Vec<u8> {
    let mut out = Vec::new();
    for (hex, count) in row.segments {
        let piece = unhex(hex);
        for _ in 0..*count {
            out.extend_from_slice(&piece);
        }
    }
    out
}

/// A bounds column: `max_depth=<n>;max_encoded_len=<n>`, the length empty for none.
fn bounds(max_depth: usize, max_encoded_len: Option<usize>) -> String {
    let len = max_encoded_len.map(|n| n.to_string()).unwrap_or_default();
    format!("max_depth={max_depth};max_encoded_len={len}")
}

/// A from_cbor row's typed entry point from bytes, by message name (from the fixture
/// schema): `X::decode`, under the message's bounds; the decoded value's own encoding.
fn typed(message: &str, bytes: &[u8]) -> Result<Vec<u8>, DecodeError> {
    match message {
@TYPED@
        _ => panic!("no typed entry point for {message}"),
    }
}

/// The bounds a message's typed entry point applies: `X::MAX_DEPTH`, `X::MAX_ENCODED_LEN`.
fn resolved(message: &str) -> String {
    match message {
@RESOLVED@
        _ => panic!("no typed entry point for {message}"),
    }
}

/// A from_wire row's typed entry point, by enum name (from the fixture schema).
fn from_wire(name: &str, v: i64) -> Result<(), DecodeError> {
    match name {
@FROM_WIRE@
        _ => panic!("no from_wire entry point for {name}"),
    }
}

/// A raw row's decode: with `limits`, `try_decode_with` them, at the default depth
/// where they give none; without, `try_decode`.
fn raw(row: &Row, bytes: &[u8]) -> Result<Cbor, DecodeError> {
    if row.max_depth.is_none() && row.max_encoded_len.is_none() {
        return try_decode(bytes);
    }
    try_decode_with(bytes, row.max_depth.unwrap_or(cbor::DEFAULT_MAX_DEPTH), row.max_encoded_len)
}

/// A decoded row's re-encoding: the tree for raw_decode, the typed value for
/// from_cbor, and nothing for from_wire (an enum row never accepts). An enum is a
/// root that is not a message, so it is decoded under the file's bounds.
fn decode_row(row: &Row, bytes: &[u8]) -> Result<Vec<u8>, DecodeError> {
    match row.stage {
        "raw_decode" => raw(row, bytes).map(|c| encode(&c)),
        "from_cbor" => typed(row.schema, bytes),
        "from_wire" => {
            let c = try_decode_with(bytes, api::MAX_DEPTH, api::MAX_ENCODED_LEN)?;
            from_wire(row.schema, c.try_int()?).map(|_| Vec::new())
        }
        other => panic!("unknown stage {other}"),
    }
}

/// An `err` detail: the runtime's canonical tag (`DecodeError::tag`), then
/// `;field=value` for each payload field it carries; a `DuplicateMapKey` key is its
/// text (`MapKey`'s `Display`). Exhaustive on purpose: a new variant fails the build
/// until its payload is reported here.
fn describe(e: &DecodeError) -> String {
    let payload = match e {
        DecodeError::Truncated
        | DecodeError::TrailingBytes
        | DecodeError::InvalidUtf8
        | DecodeError::NonIntegerMapKey
        | DecodeError::IntOverflow => String::new(),
        DecodeError::UnsupportedInfo(info) => format!(";info={info}"),
        DecodeError::UnsupportedMajor(major) => format!(";major={major}"),
        DecodeError::DuplicateMapKey(key) => format!(";key={key}"),
        DecodeError::NonCanonicalInt(value) => format!(";value={value}"),
        DecodeError::NegativeMapKey(key) => format!(";key={key}"),
        DecodeError::MissingKey(key) => format!(";key={key}"),
        DecodeError::WrongType { expected } => format!(";expected={expected}"),
        DecodeError::UnknownEnum { enum_name, value } => format!(";enum={enum_name};value={value}"),
        DecodeError::TooDeep { limit } => format!(";limit={limit}"),
        DecodeError::TooLarge { len, limit } => format!(";len={len};limit={limit}"),
    };
    format!("{}{payload}", e.tag())
}

fn panic_text(payload: &(dyn std::any::Any + Send)) -> String {
    if let Some(text) = payload.downcast_ref::<&str>() {
        return text.to_string();
    }
    if let Some(text) = payload.downcast_ref::<String>() {
        return text.clone();
    }
    "non-string panic payload".to_string()
}

fn main() {
    // The runtime's own constants, once, before any row.
    println!(
        "{}\tdefault_max_depth={};max_depth_ceiling={}",
        @CONSTANTS@,
        cbor::DEFAULT_MAX_DEPTH,
        cbor::MAX_DEPTH_CEILING
    );
    for row in ROUND_TRIP {
        let by_id: BTreeMap<i64, i64> = row.by_id.iter().map(|(k, v)| (pi(k), pi(v))).collect();
        // `..Default::default()` fills the forward-compat `wire_residual`.
        let built = api::IntBox { n: pi(row.n), by_id: by_id.clone(), ..Default::default() };
        let enc = hexof(&encode(&built.to_cbor()));
        if enc != row.cbor {
            emit(row.name, "fail", &format!("encode {} != {}", enc, row.cbor), None);
            continue;
        }
        match api::IntBox::decode(&unhex(row.cbor)) {
            Err(e) => emit(row.name, "fail", &format!("decode {e:?}"), None),
            Ok(d) => {
                let re = hexof(&encode(&d.to_cbor()));
                if d.n == pi(row.n) && d.by_id == by_id && re == row.cbor {
                    emit(row.name, "pass", "", None);
                } else {
                    emit(row.name, "fail", &format!("reencode {re}"), None);
                }
            }
        }
    }
    for row in ENCODE_FAIL {
        // i64 is the encode-side subset guard: an out-of-subset value is
        // unrepresentable, so this is satisfied by the type system.
        if row.value.parse::<i64>().is_err() {
            emit(row.name, "type-satisfied", "unrepresentable in i64", None);
        } else {
            emit(row.name, "fail", "value fits i64 but expected out-of-subset", None);
        }
    }
    for row in DECODE_ROWS {
        let fourth = if row.stage == "from_cbor" { Some(resolved(row.schema)) } else { None };
        let bytes = expand(row);
        if let Some(len) = row.len {
            if bytes.len() != len {
                let why = format!("bytes expand to {} bytes, len is {len}", bytes.len());
                emit(row.name, "untyped", &why, fourth.as_deref());
                continue;
            }
        }
        match std::panic::catch_unwind(|| decode_row(row, &bytes)) {
            Ok(Ok(again)) => emit(row.name, "ok", &hexof(&again), fourth.as_deref()),
            Ok(Err(e)) => emit(row.name, "err", &describe(&e), fourth.as_deref()),
            Err(payload) => {
                let why = format!("panic: {}", panic_text(payload.as_ref()));
                emit(row.name, "untyped", &why, fourth.as_deref());
            }
        }
    }
}
'''


def _rs(value: str) -> str:
    """A Rust string literal (row names and hex are ASCII)."""
    return json.dumps(value)


def _opt(value: int | None) -> str:
    """A Rust `Option<usize>` literal."""
    return "None" if value is None else f"Some({value})"


def _row(row: Mapping[str, Any]) -> str:
    """One malformed or bounds row: its segments as the runner expands them (the bounds
    protocol, item 5), its `len`, and its `limits`."""
    segments = ", ".join(f"({_rs(hexed)}, {count})" for hexed, count in parity.segments(row))
    limits = row.get("limits", {})
    return (f"    Row {{ name: {_rs(row['name'])}, stage: {_rs(row['stage'])}, "
            f"schema: {_rs(row.get('schema', ''))}, segments: &[{segments}], len: {_opt(row.get('len'))}, "
            f"max_depth: {_opt(limits.get('max_depth'))}, "
            f"max_encoded_len: {_opt(limits.get('max_encoded_len'))} }},")


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail = [], []
    for row in parity.int_rows():
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"({_rs(k)}, {_rs(v)})" for k, v in row["value"]["by_id"])
            round_trip.append(f"    IntRow {{ name: {_rs(row['name'])}, cbor: {_rs(row['cbor'])}, "
                              f"n: {_rs(row['value']['n'])}, by_id: &[{pairs}] }},")
        else:
            encode_fail.append(f"    EncFail {{ name: {_rs(row['name'])}, value: {_rs(row['value']['n'])} }},")
    decode = [_row(row) for row in parity.decode_rows()]
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(decode)


def _dispatch() -> tuple[str, str, str]:
    """The `match` arms for every message (its typed `decode`, and the bounds it applies)
    and every enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    typed = [f"        {_rs(name)} => api::{name}::decode(bytes).map(|v| encode(&v.to_cbor())),"
             for name in dispatch.messages]
    resolved = [f"        {_rs(name)} => bounds(api::{name}::MAX_DEPTH, api::{name}::MAX_ENCODED_LEN),"
                for name in dispatch.messages]
    from_wire = [f"        {_rs(name)} => api::{name}::from_wire(v).map(|_| ()),"
                 for name in dispatch.enums]
    return "\n".join(typed), "\n".join(resolved), "\n".join(from_wire)


def _source(generated: Path) -> str:
    round_trip, encode_fail, decode = _tables()
    typed, resolved, from_wire = _dispatch()
    return (_MAIN
            .replace("@CBOR@", (generated / "cbor.rs").as_posix())
            .replace("@API@", (generated / "api.rs").as_posix())
            .replace("@CONSTANTS@", _rs(parity.CONSTANTS))
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@DECODE_ROWS@", decode)
            .replace("@TYPED@", typed)
            .replace("@RESOLVED@", resolved)
            .replace("@FROM_WIRE@", from_wire))


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The rust gate, or with `forward_compat` its `rust/fc` variant."""
    name = parity.variant(TARGET, forward_compat)
    rustc = toolchains.find_rustc()
    if rustc is None:
        return parity.skipped(name, "rustc not found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(name, work, runtime=True)
        if failed is not None:
            return failed
        runner = work / "parity_runner.rs"
        runner.write_text(_source(work / TARGET))
        binary = work / "parity_runner"
        failed = parity.build(name, [rustc, "--edition", "2021", str(runner), "-o", str(binary)], cwd=work)
        if failed is not None:
            return failed
        return parity.run_runner(name, [str(binary)], cwd=work)
